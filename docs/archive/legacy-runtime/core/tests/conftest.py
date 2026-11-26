import json
import os
import secrets
import threading
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mingjing.artifacts import BlobStore
from mingjing.catalog import Catalog
from mingjing.contracts import Action, Kind
from mingjing.db import Database
from mingjing.examples import FakeProvider, builtins
from mingjing.http_api import API, make_handler
from mingjing.service import Service
from mingjing.temporal_adapter import TemporalAdapter

RESOURCE = "demo-note"


class CountedProvider(FakeProvider):
    def __init__(self, db):
        super().__init__(db)
        self.calls = []
        self.lock = threading.Lock()

    def send(self, data, context):
        with self.lock:
            self.calls.append(context.operation_id)
        return super().send(data, context)


@pytest.fixture(scope="session")
def traces():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


class Rig:
    def __init__(self, temp, traces):
        self.db = Database(os.environ["MINGJING_DB_DSN"])
        self.owner = Database(os.environ["MINGJING_MIGRATION_DSN"])
        self.tenant = f"test-{uuid4().hex}"
        self.other = f"other-{uuid4().hex}"
        self.queue = f"q-{self.tenant}"
        self.provider = CountedProvider(self.db)
        entries = [
            replace(cap, provider=self.provider) if cap.kind == Kind.EXTERNAL else cap
            for cap in builtins(self.db)
        ]
        self.catalog = Catalog(self.db, "dev", entries)
        self.service = Service(self.db, self.catalog, BlobStore(temp))
        self.engine = TemporalAdapter(self.service, self.queue)
        self.api = API(self.service, self.engine)
        self.traces = traces
        expires = datetime.now(UTC) + timedelta(hours=1)
        self.tokens = {who: secrets.token_urlsafe(35) for who in ("admin", "author", "approver", "other")}
        self.credentials = {}
        for who, token in self.tokens.items():
            self.credentials[who] = self.owner.add_identity(
                self.other if who == "other" else self.tenant, who, token, expires,
                administrator=who == "admin",
            )

    def lifecycle(self, name):
        for transition in ("register", "validate", "publish"):
            self.catalog.transition(self.tokens["admin"], name, 1, transition)

    def grant(self, name, who, action, allowed=True):
        self.catalog.grant(self.tokens["admin"], who, name, 1, RESOURCE, action, allowed)

    def publish(self, name):
        self.lifecycle(name)
        for action in (Action.EXECUTE, Action.READ, Action.CANCEL, Action.ARTIFACT):
            self.grant(name, "author", action)
        self.grant(name, "approver", Action.APPROVE)
        self.grant(name, "admin", Action.RECONCILE)

    def budget(self, units=None):
        with self.owner.open() as connection:
            if units is not None:
                connection.execute(
                    "INSERT INTO budgets VALUES (%s,%s) ON CONFLICT (tenant) DO UPDATE SET available=EXCLUDED.available",
                    (self.tenant, units),
                )
            return connection.execute("SELECT available FROM budgets WHERE tenant=%s", (self.tenant,)).fetchone()["available"]

    @contextmanager
    def http(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.api)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield HTTP(server.server_port, self.tokens)
            finally:
                server.shutdown()
                thread.join()


class HTTP:
    def __init__(self, port, tokens):
        self.base = f"http://127.0.0.1:{port}"
        self.tokens = tokens
        self.opener = build_opener(ProxyHandler({}))

    def request(self, method, path, *, who="author", body=None, key=None):
        request = Request(
            self.base + path, json.dumps(body).encode() if body is not None else None, method=method,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.tokens[who]}",
                     "Idempotency-Key": key or str(uuid4())},
        )
        try:
            with self.opener.open(request, timeout=15) as response:
                return response.status, json.load(response) if response.headers.get_content_type() == "application/json" else response.read()
        except HTTPError as error:
            return error.code, json.load(error)

    def submit(self, name, payload, key=None):
        return self.request("POST", "/v1/tasks", key=key, body={
            "capability_id": name, "version": 1, "resource": RESOURCE, "input": payload,
        })


@pytest.fixture
def rig(tmp_path, traces):
    return Rig(tmp_path, traces)
