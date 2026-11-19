"""Loopback HTTP surface for the three synthetic P1 routes."""

import asyncio
import json
import os
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import psycopg
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from mingjing_p1 import execution, storage
from mingjing_p1.contracts import Job, Principal, Rejected
from mingjing_p1.telemetry import configure, interceptor, tracer
from mingjing_p1.temporal.workflows import Gateway


def job_for(task: storage.Row) -> Job:
    return Job(
        task["id"], task["operation_id"],
        f"{task['id']}:approval" if task["kind"] != "direct" else None,
        task["kind"] != "direct",
        deadline_seconds=int(os.environ.get("MINGJING_DEADLINE_SECONDS", "40")),
        step_limit=int(os.environ.get("MINGJING_MAX_STEPS", "2")),
        depth_limit=int(os.environ.get("MINGJING_MAX_DEPTH", "1")),
        kind=task["kind"], scenario=task["value"],
    )


async def client() -> Client:
    return await Client.connect(
        os.environ["TEMPORAL_ADDRESS"], namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[interceptor()],
    )


async def start_job(task: storage.Row, job: Job) -> None:
    temporal = await client()
    try:
        await temporal.start_workflow(
            Gateway.run, job, id=task["workflow_id"],
            task_queue=os.environ["TEMPORAL_TASK_QUEUE"],
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            execution_timeout=timedelta(minutes=2),
        )
    except WorkflowAlreadyStartedError:
        pass


async def deliver(task: storage.Row, decision: str | None) -> None:
    temporal = await client()
    handle = temporal.get_workflow_handle(task["workflow_id"])
    try:
        if decision is None:
            await handle.cancel()
        else:
            await handle.signal(Gateway.approve, decision)
    except RPCError as error:
        if error.status != RPCStatusCode.NOT_FOUND:
            raise
        if decision is not None:
            # A retry can arrive after a previously accepted decision closed the run.
            description = await handle.describe()
            if description.status.name == "RUNNING":
                raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        # Tokens and request bodies are deliberately excluded from process logs.
        return

    def send_json(self, status: int, value: object) -> None:
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def principal(self) -> Principal:
        scheme, _, token = self.headers.get("Authorization", "").partition(" ")
        credentials = json.loads(Path(os.environ["MINGJING_TEST_CREDENTIALS_FILE"]).read_text())
        entry = credentials.get(token) if scheme == "Bearer" else None
        if entry is None or entry["expiry"] <= time.time():
            raise Rejected("invalid_identity", 401)
        return Principal(entry["tenant"], entry["subject"])

    def body(self) -> storage.Row:
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, UnicodeError) as error:
            raise Rejected("bad_json", 400) from error
        return payload

    def route(self) -> tuple[int, object]:
        parts = [unquote(piece) for piece in urlsplit(self.path).path.split("/") if piece]
        if self.command == "GET" and parts == ["healthz"]:
            return 200, {"ready": True}
        principal = self.principal()
        if self.command == "POST" and parts == ["tasks"]:
            task = storage.create_task(principal, self.body(), self.headers.get("Idempotency-Key", ""))
            job = job_for(task)
            with tracer().start_as_current_span("mingjing.api.submit", attributes={
                "task_id": job.task_id, "run_id": task["run_id"],
                "workflow_id": task["workflow_id"], "operation_id": job.operation_id,
            }):
                if task["kind"] == "direct":
                    output = execution.execute(job, f"api:{uuid4()}")
                    return 200, output
                asyncio.run(start_job(task, job))
                return 202, storage.inspect_task(principal, job.task_id)
        if len(parts) == 2 and self.command == "GET":
            if parts[0] == "tasks":
                return 200, storage.inspect_task(principal, parts[1])
            if parts[0] == "artifacts":
                return 200, storage.read_artifact(principal, parts[1])
        if len(parts) == 3 and parts[0] == "tasks" and self.command == "POST":
            if parts[2] == "approve":
                task, decision = storage.review(principal, parts[1])
                asyncio.run(deliver(task, decision))
                return 202, {"decision_id": decision}
            if parts[2] == "cancel":
                task = storage.request_cancel(principal, parts[1])
                if task["kind"] != "direct":
                    asyncio.run(deliver(task, None))
                return 202, {"cancel_requested": True}
        raise Rejected("not_found", 404)

    def do_GET(self) -> None:
        try:
            self.send_json(*self.route())
        except Rejected as error:
            self.send_json(error.status, {"code": error.code})
        except (psycopg.Error, RPCError):
            self.send_json(503, {"code": "gate_or_engine_unavailable"})

    do_POST = do_GET


def main() -> None:
    if os.environ.get("MINGJING_ENV") != "p1" or os.environ.get("MINGJING_MODEL") != "fake":
        raise SystemExit("P1 fixture configuration required")
    configure()
    with ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("MINGJING_API_PORT", "0"))), Handler) as http:
        print(f"API_READY {http.server_port}", flush=True)
        http.serve_forever()


if __name__ == "__main__":
    main()
