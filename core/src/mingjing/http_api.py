from __future__ import annotations

import asyncio
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Annotated, Literal
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

import psycopg
from opentelemetry import trace
from pydantic import Field, ValidationError
from temporalio.service import RPCError

from .contracts import Action, Fault, Model
from .service import Artifact, Service, TERMINAL
from .temporal_adapter import TemporalAdapter

Text = Annotated[str, Field(min_length=1, max_length=128)]
Version = Annotated[int, Field(gt=0, le=2147483647)]
TRACER = trace.get_tracer("mingjing.api")


class Submission(Model):
    capability_id: Text
    version: Version
    resource: Text
    input: dict


class Grant(Model):
    subject: Text
    capability_id: Text
    version: Version
    resource: Text
    action: Literal["execute", "read", "approve", "cancel", "artifact", "reconcile"]
    allowed: bool


class Approval(Model):
    decision: Literal["approved", "rejected"]


def encode(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unsupported response type {type(value).__name__}")


class API:
    def __init__(self, service: Service, engine: TemporalAdapter):
        self.service = service
        self.engine = engine

    def submit(self, token: str, request: Submission, key: str) -> tuple[int, dict]:
        if not key or len(key) > 128:
            raise Fault("invalid_idempotency_key", 422)
        with TRACER.start_as_current_span("mingjing.submit") as span:
            view = self.service.submit(
                token, request.capability_id, request.version, request.resource, request.input, key,
            )
            task_id = UUID(view["task_id"])
            span.set_attributes({key: view[key] for key in ("task_id", "operation_id")})
            span.set_attribute("run_id", view["run"]["run_id"])
            if view["state"] not in TERMINAL:
                if view["run"]["workflow_id"]:
                    span.set_attribute("workflow_id", view["run"]["workflow_id"])
                    asyncio.run(self.engine.start(view))
                else:
                    self.service.execute(task_id)
            return self.service.submission_response(token, task_id)

    def get(self, token: str, task: UUID) -> dict:
        view = self.service.get(token, task)
        if view["run"]["workflow_id"]:
            try:
                asyncio.run(self.engine.refresh(view))
            except (RPCError, RuntimeError):
                pass
            view = self.service.get(token, task)
        return view


def make_handler(api: API):
    class HTTP(BaseHTTPRequestHandler):
        def log_message(self, format, *args) -> None:
            return

        def respond(self, status: int, value) -> None:
            if isinstance(value, Artifact):
                body, media = value.data, value.media_type
            else:
                body, media = json.dumps(value, default=encode).encode(), "application/json"
            self.send_response(status)
            self.send_header("Content-Type", media)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def model(self, model: type[Model]) -> Model:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise ValueError
                return model.model_validate_json(self.rfile.read(size))
            except (ValueError, ValidationError) as error:
                raise Fault("invalid_request", 422) from error

        def token(self) -> str:
            scheme, _, token = self.headers.get("Authorization", "").partition(" ")
            if scheme.lower() != "bearer" or not 32 <= len(token) <= 512:
                raise Fault("unauthenticated", 401)
            return token

        def route(self):
            url = urlsplit(self.path)
            parts = [unquote(part) for part in url.path.split("/") if part]
            if self.command == "GET" and parts == ["healthz"]:
                return 200, {"service": "mingjing"}
            token = self.token()
            if self.command == "POST" and parts == ["v1", "tasks"]:
                return api.submit(token, self.model(Submission), self.headers.get("Idempotency-Key", ""))
            if self.command == "GET" and parts == ["v1", "capabilities"]:
                resource = parse_qs(url.query).get("resource", [])
                if len(resource) != 1 or not 0 < len(resource[0]) <= 128:
                    raise Fault("invalid_resource", 422)
                return 200, {"schema_version": 1, "capabilities": api.service.catalog.discover(token, resource[0])}
            if self.command == "POST" and len(parts) == 5 and parts[:2] == ["v1", "capabilities"]:
                try:
                    version = int(parts[3])
                except ValueError as error:
                    raise Fault("invalid_capability_version", 422) from error
                return 200, api.service.catalog.transition(token, parts[2], version, parts[4])
            if self.command == "PUT" and parts == ["v1", "grants"]:
                data = self.model(Grant)
                api.service.catalog.grant(token, data.subject, data.capability_id, data.version,
                                          data.resource, Action(data.action), data.allowed)
                return 200, {"changed": True}
            if len(parts) in (3, 4) and parts[:2] in (["v1", "tasks"], ["v1", "artifacts"]):
                try:
                    reference = UUID(parts[2])
                except ValueError as error:
                    raise Fault("invalid_reference", 422) from error
                if parts[1] == "artifacts" and self.command == "GET" and len(parts) == 3:
                    return 200, api.service.artifact(token, reference)
                if parts[1] == "tasks":
                    return self.task_route(parts[3:], token, reference)
            raise Fault("not_found", 404)

        def task_route(self, rest: list[str], token: str, task: UUID):
            if self.command == "GET" and not rest:
                return 200, api.get(token, task)
            if self.command == "GET" and rest == ["runs"]:
                return 200, {"schema_version": 1, "runs": [api.get(token, task)["run"]]}
            if self.command == "POST" and rest == ["approval"]:
                decision = self.model(Approval).decision
                view = api.service.approval(token, task, decision)
                if view["run"]["workflow_id"]:
                    asyncio.run(api.engine.control(view))
                else:
                    api.service.execute(task)
                return 200, {"schema_version": 1, "task_id": task, "decision": decision}
            if self.command == "POST" and rest == ["cancel"]:
                view = api.service.cancel(token, task)
                if view["run"]["workflow_id"]:
                    asyncio.run(api.engine.control(view, cancel=True))
                return 200, {"schema_version": 1, "task_id": task, "cancel_requested": True}
            if self.command == "POST" and rest == ["reconcile"]:
                view = api.service.reconcile(token, task)
                return 200, {"schema_version": 1, "task_id": task, "state": view["state"]}
            raise Fault("not_found", 404)

        def do_GET(self) -> None:
            try:
                self.respond(*self.route())
            except Fault as error:
                self.respond(error.status, {"schema_version": 1, "code": error.code})
            except (psycopg.Error, RPCError, RuntimeError):
                self.respond(503, {"schema_version": 1, "code": "dependency_unavailable"})

        do_POST = do_GET
        do_PUT = do_GET

    return HTTP


def serve(api: API, host: str, port: int) -> None:
    with ThreadingHTTPServer((host, port), make_handler(api)) as server:
        print(f"MINGJING_READY {server.server_port}", flush=True)
        server.serve_forever()
