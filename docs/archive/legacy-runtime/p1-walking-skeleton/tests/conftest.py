"""Process and database fixtures for the isolated acceptance run."""

import asyncio
import contextlib
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import pytest
from temporalio.client import Client
from temporalio.service import RPCError

from mingjing_p1 import storage
from mingjing_p1.contracts import CAPABILITIES
from mingjing_p1.temporal.workflows import Gateway


def evidence(name: str, value: object) -> None:
    path = Path("/evidence")
    if path.is_dir():
        (path / f"{name}.json").write_text(json.dumps(value, default=str, indent=2) + "\n")
    print(f"{name}: {json.dumps(value, default=str)}")


async def eventually(predicate, *, timeout: float = 12, message: str = "condition") -> object:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := predicate():
            return value
        await asyncio.sleep(0.05)
    raise AssertionError(f"timed out waiting for {message}")


def count(table: str, operation: str) -> int:
    # Table names are selected by the fixture, never taken from an HTTP request.
    assert table in {"markers", "receipts", "attempts"}
    with storage.connect() as conn:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE operation_id=%s",
                            (operation,)).fetchone()["n"]


def child_id(task: dict) -> str:
    return f'{task["workflow_id"]}-marker'


class FakeProvider:
    def __init__(self):
        self.ledger = {}
        self.calls = []
        self.lock = threading.Lock()
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_POST(self):
                assert self.path == "/mark"
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                operation = data["operation_id"]
                with provider.lock:
                    provider.calls.append(operation)
                    reference = provider.ledger.setdefault(operation, f"fake:{operation}")
                if data["value"] in {"drop-receipt", "drop-cost"}:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                body = json.dumps({"reference": reference}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/mark"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class Process:
    def __init__(self, root: Path, name: str, module: str, environment: dict,
                 executable: str = sys.executable):
        self.log = root / f"{name}.log"
        with self.log.open("w") as stream:
            self.process = subprocess.Popen(
                [executable, "-m", module], stdout=stream, stderr=subprocess.STDOUT,
                env=environment,
            )

    async def ready(self, token: str) -> str:
        def line():
            text = self.log.read_text()
            if self.process.poll() is not None:
                raise AssertionError(f"process exited: {text[-5500:]}")
            return next((line for line in text.splitlines() if line.startswith(token)), None)

        try:
            return await eventually(line, timeout=20, message=token)
        except AssertionError as error:
            raise AssertionError(f"{error}; {self.log.read_text()[-5500:]}") from error

    def stop(self, *, kill: bool = False) -> None:
        if self.process.poll() is None:
            self.process.kill() if kill else self.process.terminate()
            try:
                self.process.wait(3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(5)


class API:
    def __init__(self, port: int, tokens: dict[str, str]):
        self.url = f"http://127.0.0.1:{port}"
        self.tokens = tokens

    def request(self, method: str, path: str, *, who: str = "author",
                body: dict | None = None, key: str | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode() if body is not None else None,
            method=method, headers={
                "Authorization": f"Bearer {self.tokens[who]}",
                "Content-Type": "application/json", "Idempotency-Key": key or str(uuid4()),
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def submit(self, kind="workflow", value="marker", capability="record_marker@1", key=None):
        status, payload = self.request(
            "POST", "/tasks", key=key, body={"kind": kind, "value": value, "capability": capability},
        )
        assert status == (200 if kind == "direct" else 202), payload
        return payload

    def approve(self, task: dict, who="approver"):
        return self.request("POST", f"/tasks/{task['task_id']}/approve", who=who, body={})

    def cancel(self, task: dict):
        status, payload = self.request("POST", f"/tasks/{task['task_id']}/cancel", body={})
        assert status == 202, payload

    def task(self, task: dict):
        status, payload = self.request("GET", f"/tasks/{task['task_id']}")
        assert status == 200, payload
        return payload


class Harness:
    def __init__(self, directory: Path):
        self.root = directory
        self.tenant = uuid4().hex
        self.other = uuid4().hex
        self.queue = f"p1-{self.tenant}"
        self.processes = []
        self.fake = FakeProvider()
        self.tokens = {who: secrets.token_urlsafe(24) for who in ("author", "approver", "other")}
        self.credentials = directory / "credentials.json"
        auth = {
            token: {"tenant": self.other if who == "other" else self.tenant,
                    "subject": who, "expiry": time.time() + 240}
            for who, token in self.tokens.items()
        }
        with os.fdopen(os.open(self.credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       "w") as f:
            json.dump(auth, f)
        with storage.connect() as conn:
            for tenant, subject in ((self.tenant, "author"), (self.other, "other")):
                conn.execute("INSERT INTO accounts VALUES (%s,8)", (tenant,))
                for action in ("read", "write", "cancel"):
                    conn.execute("INSERT INTO grants VALUES (%s,%s,'marker',%s,true)",
                                 (tenant, subject, action))
                for code in CAPABILITIES:
                    conn.execute("INSERT INTO published VALUES (%s,%s,true)", (tenant, code))
            conn.execute("INSERT INTO grants VALUES (%s,'approver','marker','approve',true)",
                         (self.tenant,))

    def env(self, queue: str, **extra: str):
        inherit = ("PATH", "HOME", "PYTHONPATH", "TEMPORAL_ADDRESS", "TEMPORAL_NAMESPACE",
                   "MINGJING_DB_DSN")
        return {
            **{key: os.environ[key] for key in inherit if key in os.environ},
            "MINGJING_ENV": "p1", "MINGJING_MODEL": "fake",
            "MINGJING_TEST_CREDENTIALS_FILE": str(self.credentials),
            "MINGJING_ARTIFACT_DIR": str(self.root / "artifacts"),
            "MINGJING_PROVIDER_URL": self.fake.url, "TEMPORAL_TASK_QUEUE": queue,
            "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
            "LANGGRAPH_STRICT_MSGPACK": "true", "OTEL_TRACES_EXPORTER": "none", **extra,
        }

    def launch(self, name: str, module: str, environment: dict,
               executable: str = sys.executable):
        process = Process(self.root, name, module, environment, executable)
        self.processes.append(process)
        return process

    async def api(self, name="api", queue=None, **env):
        process = self.launch(name, "mingjing_p1.api", self.env(queue or self.queue, **env))
        status = await process.ready("API_READY ")
        return API(int(status.split()[1]), self.tokens)

    async def worker(self, name="worker", queue=None, **env):
        process = self.launch(name, "mingjing_p1.temporal.worker", self.env(queue or self.queue, **env))
        await process.ready("WORKER_READY")
        return process

    async def client(self):
        return await Client.connect(os.environ["TEMPORAL_ADDRESS"],
                                    namespace=os.environ["TEMPORAL_NAMESPACE"])

    async def waiting(self, handle, phase="waiting"):
        deadline = time.monotonic() + 16
        while time.monotonic() < deadline:
            try:
                state = await handle.query(Gateway.state, rpc_timeout=timedelta(seconds=1))
                if state["phase"] == phase:
                    return state
            except RPCError:
                pass
            await asyncio.sleep(0.05)
        logs = "\n".join(process.log.read_text()[-2600:] for process in self.processes)
        raise AssertionError(f"workflow did not enter {phase}: {logs}")

    def hold(self, name: str, phase: str) -> Path:
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        (folder / f"{phase}.hold").touch()
        return folder

    async def reached(self, folder: Path, phase: str, op: str):
        path = folder / f"{phase}.reached"
        await eventually(lambda: path.exists() and path.read_text() == op, message=f"{phase} for {op}")

    def grant(self, action: str, allowed: bool):
        with storage.connect() as conn:
            conn.execute("UPDATE grants SET allowed=%s WHERE tenant=%s AND subject='author' AND action=%s",
                         (allowed, self.tenant, action))

    def budget(self, amount: int | None = None):
        with storage.connect() as conn:
            if amount is not None:
                conn.execute("UPDATE accounts SET remaining=%s WHERE tenant=%s", (amount, self.tenant))
            return conn.execute("SELECT remaining FROM accounts WHERE tenant=%s",
                                (self.tenant,)).fetchone()["remaining"]

    def close(self):
        for process in reversed(self.processes):
            process.stop()
        self.fake.close()


@pytest.fixture
def rig(tmp_path, monkeypatch):
    if os.environ.get("MINGJING_ENV") != "p1":
        pytest.fail("Run acceptance inside the isolated P1 environment")
    monkeypatch.setenv("MINGJING_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    with contextlib.closing(Harness(tmp_path)) as harness:
        yield harness
