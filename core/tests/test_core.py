import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from shutil import copy2
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import UUID, uuid4

import psycopg
import pytest
from temporalio.service import RPCError, RPCStatusCode

from conftest import RESOURCE
from mingjing import artifacts, service as service_module, temporal_adapter
from mingjing.catalog import Catalog
from mingjing.contracts import Action, Fault, Model, Result
from mingjing.db import Database
from mingjing.service import Service
from mingjing.temporal_adapter import connect, make_worker


def test_api_lifecycle_grants_schema_idempotency_and_artifacts(rig):
    name = "normalize_text"
    path = f"/v1/capabilities/{name}/1/"
    query = f"/v1/capabilities?resource={RESOURCE}"
    with rig.http() as http:
        assert http.request("POST", path+"register")[0] == 403
        assert http.request("POST", path+"register", who="admin")[0] == 200
        assert http.request("POST", path+"publish", who="admin")[0] == 409
        assert http.request("POST", path+"validate", who="admin")[0] == 200
        assert http.request("POST", path+"publish", who="admin")[0] == 200
        assert http.request("GET", query)[1]["capabilities"] == []
        assert http.submit(name, {"text": "report"})[0] == 403
        for action in ("execute", "read", "artifact"):
            status, _ = http.request("PUT", "/v1/grants", who="admin", body={
                "subject": "author", "capability_id": name, "version": 1, "resource": RESOURCE,
                "action": action, "allowed": True,
            })
            assert status == 200
        discovered = http.request("GET", query)[1]["capabilities"]
        assert discovered[0]["input_schema"]["properties"]["text"]["type"] == "string"
        preview = Catalog(rig.db, "preview", rig.catalog.entries.values())
        assert preview.discover(rig.tokens["author"], RESOURCE) == []
        assert http.submit(name, {"text": 42})[0] == 422
        status, first = http.submit(name, {"text": " report "}, key="stable")
        assert status == 200 and first["receipt"]["value"] == {"text": "report"}
        assert first["run"]["workflow_id"] is None
        assert http.submit(name, {"text": " report "}, key="stable")[1] == first
        assert http.submit(name, {"text": "different"}, key="stable")[0] == 409
        artifact = "/v1/artifacts/" + first["receipt"]["artifact_id"]
        assert http.request("GET", artifact) == (200, b"report")
        assert http.request("GET", artifact, who="other")[0] == 404
        rig.grant(name, "author", Action.ARTIFACT, False)
        assert http.request("GET", artifact)[0] == 403
        assert http.request("POST", path+"deprecate", who="admin")[0] == 200
        assert http.request("GET", query)[1]["capabilities"] == []
        assert http.submit(name, {"text": "a new request"})[0] == 403
        assert http.submit(name, {"text": " report "}, key="stable")[1] == first
        rig.grant(name, "approver", Action.CANCEL)
        assert http.request("GET", "/v1/tasks/" + first["task_id"], who="approver")[0] == 403
        cancelled = http.request("POST", "/v1/tasks/" + first["task_id"] + "/cancel", who="approver")[1]
        assert cancelled == {"schema_version": 1, "task_id": first["task_id"], "cancel_requested": True}
        assert http.request("GET", "/v1/tasks/" + first["task_id"])[1]["state"] == "succeeded"


def test_submit_does_not_grant_task_or_receipt_read_access(rig):
    name = "normalize_text"
    rig.lifecycle(name)
    rig.grant(name, "author", Action.EXECUTE)
    with rig.http() as http:
        status, ack = http.submit(name, {"text": "private result"}, key="execute-only")
        assert status == 200
        assert set(ack) == {"schema_version", "task_id", "run"}
        assert set(ack["run"]) == {"run_id"}
        task = f"/v1/tasks/{ack['task_id']}"
        assert http.request("GET", task)[0] == 403
        rig.grant(name, "author", Action.READ)
        assert http.request("GET", task)[1]["receipt"]["value"] == {"text": "private result"}
        rig.grant(name, "author", Action.READ, False)
        assert http.submit(name, {"text": "private result"}, key="execute-only") == (200, ack)


def test_strict_json_contract_matches_temporal_types_at_submission_and_execution(rig):
    class TypedInput(Model):
        day: date
        marker: UUID

    def handler(data, context, notes):
        assert isinstance(data.day, date) and isinstance(data.marker, UUID)
        return Result({"text": data.day.isoformat()})

    name = "normalize_text"
    cap = rig.catalog.implementation(name, 1)
    rig.catalog.entries[name, 1] = replace(cap, input=TypedInput, handler=handler)
    rig.publish(name)
    with rig.http() as http:
        payload = {"day": "2026-11-20", "marker": str(uuid4())}
        status, view = http.submit(name, payload)
        assert status == 200
        assert view["receipt"]["value"] == {"text": "2026-11-20"}
        assert http.submit(name, {**payload, "day": "invalid"})[0] == 422


def test_artifact_sync_failure_leaves_operation_uncommitted(rig, monkeypatch):
    name = "normalize_text"
    rig.publish(name)

    def unavailable(_):
        raise OSError("synthetic disk failure")

    with rig.http() as http:
        with monkeypatch.context() as fault:
            fault.setattr(artifacts.os, "fsync", unavailable)
            assert http.submit(name, {"text": "durable"}, key="fsync-failure") == (
                503, {"schema_version": 1, "code": "artifact_store_unavailable"},
            )
        with rig.db.open() as conn:
            assert not conn.execute("SELECT 1 FROM artifacts WHERE tenant=%s", (rig.tenant,)).fetchone()
            assert not conn.execute("SELECT 1 FROM receipts WHERE tenant=%s", (rig.tenant,)).fetchone()
        status, view = http.submit(name, {"text": "durable"}, key="fsync-failure")
        assert status == 200
        assert view["receipt"]["state"] == "succeeded"
        assert http.request("GET", "/v1/artifacts/" + view["receipt"]["artifact_id"]) == (200, b"durable")


async def get_when(http, task, predicate):
    async with asyncio.timeout(18):
        while True:
            status, view = await asyncio.to_thread(http.request, "GET", f"/v1/tasks/{task}")
            assert status == 200, view
            if predicate(view):
                return view
            await asyncio.sleep(0.15)


def test_actual_temporal_and_langgraph_three_templates(rig):
    async def check():
        for name in ("write_note", "draft_note"):
            rig.publish(name)
        client = await connect()
        async with make_worker(client, rig.queue, rig.service):
            with rig.http() as http:
                for name in ("write_note", "draft_note"):
                    code, task = await asyncio.to_thread(http.submit, name, {"content": "synthetic"})
                    assert code == 202, (code, task)
                    task_id = task["task_id"]
                    await get_when(http, task_id, lambda view: view["state"] == "waiting")
                    approval = f"/v1/tasks/{task_id}/approval"
                    assert http.request("POST", approval, body={"decision": "approved"})[0] == 403
                    rig.grant(name, "author", Action.APPROVE)
                    assert http.request("POST", approval, body={"decision": "approved"}) == (
                        403, {"schema_version": 1, "code": "self_approval_denied"},
                    )
                    accepted = await asyncio.to_thread(http.request, "POST", approval, who="approver",
                                                       body={"decision": "approved"})
                    assert accepted == (200, {"schema_version": 1, "task_id": task_id, "decision": "approved"})
                    assert http.request("GET", f"/v1/tasks/{task_id}", who="approver")[0] == 403
                    result = await get_when(http, task_id, lambda view: view["run"]["engine_state"] == "completed")
                    assert result["state"] == "succeeded"
                    assert result["receipt"]["value"] == {"stored": True}
                    assert result["run"]["run_id"] != result["run"]["temporal_run_id"]
                    assert http.request("GET", f"/v1/tasks/{task_id}/runs")[1]["runs"] == [result["run"]]
                    history = await client.get_workflow_handle(result["run"]["workflow_id"]).fetch_history()
                    activities = [event.activity_task_scheduled_event_attributes.activity_type.name
                                  for event in history.events if event.HasField("activity_task_scheduled_event_attributes")]
                    selected = "mingjing.agent.v1.tool" if name == "draft_note" else "mingjing.execute.v1"
                    assert selected in activities
                    spans = rig.traces.get_finished_spans()
                    submit = next(span for span in spans if span.name == "mingjing.submit"
                                  and span.attributes.get("task_id") == task_id)
                    chain = [span.name for span in spans if span.context.trace_id == submit.context.trace_id]
                    assert "RunWorkflow:MingjingTaskV1" in chain
                    assert f"RunActivity:{selected}" in chain
                    rig.service.execute(UUID(task_id), agent_tool="append_note" if name == "draft_note" else None)
                    with rig.db.open() as conn:
                        assert conn.execute(
                            "SELECT count(*) AS n FROM example_notes WHERE operation_id=%s", (UUID(result["operation_id"]),),
                        ).fetchone()["n"] == 1
    asyncio.run(check())


def test_revocation_after_approval_denies_actual_workflow_io(rig):
    async def check():
        name = "write_note"
        rig.publish(name)
        with rig.http() as http:
            status, view = await asyncio.to_thread(http.submit, name, {"content": "must be denied"})
            assert status == 202
            task = view["task_id"]
            assert http.request("POST", f"/v1/tasks/{task}/approval", who="approver",
                                body={"decision": "approved"})[0] == 200
            rig.grant(name, "author", Action.EXECUTE, False)
            async with make_worker(await connect(), rig.queue, rig.service):
                refused = await get_when(http, task, lambda v: v["run"]["engine_state"] == "completed")
                assert refused["state"] == "denied" and refused["receipt"]["code"] == "permission_denied"
            with rig.db.open() as conn:
                assert not conn.execute("SELECT 1 FROM example_notes WHERE tenant=%s", (rig.tenant,)).fetchone()
    asyncio.run(check())


@pytest.mark.parametrize("expiration", ["approval", "requester", "approver"])
def test_expiration_is_rechecked_after_approval_grant_lock_wait(rig, expiration):
    name = "write_note"
    rig.publish(name)
    task = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"content": "expires"}, "expires")
    task_id = UUID(task["task_id"])
    rig.service.approval(rig.tokens["approver"], task_id, "approved")
    with rig.owner.open() as conn:
        expires_at = conn.execute("SELECT clock_timestamp()+interval '2 seconds' AS until").fetchone()["until"]
        if expiration == "approval":
            conn.execute("UPDATE approvals SET expires_at=%s WHERE task_id=%s", (expires_at, task_id))
        else:
            identifier = rig.credentials["author" if expiration == "requester" else "approver"]
            conn.execute("UPDATE credentials SET expires_at=%s WHERE id=%s", (expires_at, identifier))
    with ThreadPoolExecutor(max_workers=1) as executor:
        with rig.owner.open() as holder, rig.owner.open() as observer:
            observer.autocommit = True
            blocker = holder.execute("SELECT pg_backend_pid() AS pid").fetchone()["pid"]
            holder.execute(
                "SELECT 1 FROM grants WHERE tenant=%s AND subject='approver' AND action='approve' FOR UPDATE",
                (rig.tenant,),
            )
            started = executor.submit(rig.service.execute, task_id)
            deadline = monotonic() + 1.5
            while not observer.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE %s=ANY(pg_blocking_pids(pid))) AS waiting",
                (blocker,),
            ).fetchone()["waiting"]:
                if started.done():
                    pytest.fail(f"executor completed before grant release: {started.result()!r}")
                assert monotonic() < deadline, "executor did not reach the held approval grant"
                sleep(0.025)
            sleep(max(0, (expires_at - datetime.now(UTC)).total_seconds()) + 0.05)
        assert started.result(timeout=4)
    view = rig.service.system_view(task_id)
    assert view["state"] == "denied"
    expected = "approval_unavailable" if expiration == "approval" else "unauthenticated"
    assert view["receipt"]["code"] == expected
    with rig.db.open() as conn:
        assert not conn.execute("SELECT 1 FROM example_notes WHERE tenant=%s", (rig.tenant,)).fetchone()


@pytest.mark.parametrize("known_run", [True, False])
def test_retained_start_prevents_restart_when_engine_history_is_gone(rig, monkeypatch, known_run):
    name = "write_note"
    rig.publish(name)
    fields = {"content": "retained product task"}
    task = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, fields, "old")
    task_id = UUID(task["task_id"])
    temporal_run = str(uuid4()) if known_run else None
    rig.service.bind_engine_start(task_id, os.environ["TEMPORAL_NAMESPACE"])
    if temporal_run:
        rig.service.engine(task_id, "running", temporal_run)
    else:
        with rig.owner.open() as conn:
            conn.execute(
                "UPDATE runs SET first_start_at=clock_timestamp()-interval '6 minutes' WHERE task_id=%s",
                (task_id,),
            )

    class AbsentHistory:
        async def describe(self, *, rpc_timeout):
            raise RPCError("synthetic pruned history", RPCStatusCode.NOT_FOUND, b"")

    class ClientWithoutHistory:
        async def start_workflow(self, *args, **kwargs):
            pytest.fail("a known run must not be started again")

        def get_workflow_handle(self, workflow_id, *, run_id):
            assert workflow_id == task["run"]["workflow_id"] and run_id == temporal_run
            return AbsentHistory()

    async def connect():
        return ClientWithoutHistory()

    monkeypatch.setattr(temporal_adapter, "connect", connect)
    with rig.http() as http:
        status, observed = http.submit(name, fields, key="old")
        assert status == 200
        assert observed["state"] == "unknown" and observed["receipt"] is None
        assert observed["run"]["engine_state"] == "history_unavailable"
        assert http.submit(name, fields, key="old") == (200, observed)


@pytest.mark.parametrize("boundary", ["approval_expiry", "activity_deadline"])
def test_slow_preparation_cannot_write_after_authorization_or_deadline(rig, boundary):
    name = "write_note"
    cap = rig.catalog.implementation(name, 1)
    prepared = []
    expires_at: datetime

    def slow(data, context, notes):
        prepared.append(True)
        sleep(max(0, (expires_at - datetime.now(UTC)).total_seconds()) + 0.02)
        return cap.handler(data, context, notes)

    rig.catalog.entries[name, 1] = replace(cap, handler=slow)
    rig.publish(name)
    task = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"content": "late"}, "late-write")
    task_id = UUID(task["task_id"])
    rig.service.approval(rig.tokens["approver"], task_id, "approved")
    expires_at = datetime.now(UTC) + timedelta(seconds=1)
    if boundary == "approval_expiry":
        with rig.owner.open() as conn:
            conn.execute("UPDATE approvals SET expires_at=%s WHERE task_id=%s", (expires_at, task_id))
    if boundary == "activity_deadline":
        with pytest.raises(Fault, match="execution_deadline"):
            rig.service.execute(task_id, deadline=expires_at)
    else:
        rig.service.execute(task_id)
    result = rig.service.system_view(task_id)
    assert prepared == [True]
    with rig.db.open() as conn:
        assert not conn.execute("SELECT 1 FROM example_notes WHERE tenant=%s", (rig.tenant,)).fetchone()
    if boundary == "activity_deadline":
        assert result["receipt"] is None
        rig.catalog.entries[name, 1] = cap
        rig.service.execute(task_id, deadline=datetime.now(UTC) + timedelta(seconds=5))
        assert rig.service.system_view(task_id)["state"] == "succeeded"
    else:
        assert result["state"] == "denied" and result["receipt"]["code"] == "approval_unavailable"


def test_wrong_namespace_does_not_refresh_a_task(rig, monkeypatch):
    rig.publish("write_note")
    task = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, {"content": "note"}, "bound")
    task_id = UUID(task["task_id"])
    rig.service.bind_engine_start(task_id, os.environ["TEMPORAL_NAMESPACE"])
    rig.service.engine(task_id, "running", str(uuid4()))
    monkeypatch.setenv("TEMPORAL_NAMESPACE", "different-namespace")

    async def connect():
        pytest.fail("refresh must not call a different namespace")

    monkeypatch.setattr(temporal_adapter, "connect", connect)
    assert rig.api.get(rig.tokens["author"], task_id)["run"]["engine_state"] == "running"


def test_old_unbound_task_is_not_claimed_by_current_namespace(rig, monkeypatch):
    rig.publish("write_note")
    fields = {"content": "old task"}
    original = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, fields, "migration")
    with rig.owner.open() as conn:
        conn.execute(
            "UPDATE runs SET first_start_at=clock_timestamp()-interval '6 minutes' WHERE task_id=%s",
            (UUID(original["task_id"]),),
        )

    async def connect():
        pytest.fail("legacy routes require a trusted namespace binding")

    monkeypatch.setattr(temporal_adapter, "connect", connect)
    with rig.http() as http:
        status, view = http.submit("write_note", fields, key="migration")
        assert status == 202 and view["run"]["namespace"] is None
        assert http.request("GET", "/v1/tasks/" + view["task_id"]) == (200, view)
        assert view["state"] == "queued"


def test_unavailable_history_cannot_close_an_inflight_start_or_unseen_run(rig):
    rig.publish("write_note")
    fields = {"content": "starting"}
    original = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, fields, "inflight")
    task_id = UUID(original["task_id"])
    rig.service.bind_engine_start(task_id, os.environ["TEMPORAL_NAMESPACE"])
    lock = rig.service.lock_engine_start(task_id)
    assert lock is not None
    try:
        rig.service.engine(task_id, "history_unavailable", None, wait=False)
        assert rig.service.system_view(task_id)["state"] == "queued"
        run_id = str(uuid4())
        rig.service.engine(task_id, "running", run_id)
    finally:
        lock.close()
    rig.service.engine(task_id, "history_unavailable", None, wait=False)
    refreshed = rig.service.system_view(task_id)
    assert refreshed["state"] == "queued"
    assert refreshed["run"]["temporal_run_id"] == run_id and refreshed["run"]["engine_state"] == "running"


def test_concurrent_resubmission_can_retry_a_failed_start(rig, monkeypatch):
    rig.publish("write_note")
    fields = {"content": "start retry"}
    start_entered = Event()
    release_start = Event()

    class FailingClient:
        async def start_workflow(self, *args, **kwargs):
            start_entered.set()
            assert release_start.wait(10), "test did not release the first start"
            raise RPCError("synthetic pre-start failure", RPCStatusCode.UNAVAILABLE, b"")

    async def connect_for_test():
        if start_entered.is_set():
            return await connect()
        return FailingClient()

    monkeypatch.setattr(temporal_adapter, "connect", connect_for_test)
    with rig.http() as http, ThreadPoolExecutor(1) as pool:
        first = pool.submit(http.submit, "write_note", fields, "concurrent-start")
        try:
            assert start_entered.wait(5), "first request did not reach Temporal start"
            status, body = http.submit("write_note", fields, "concurrent-start")
            assert status == 503 and body["code"] == "engine_start_in_progress"
        finally:
            release_start.set()
        assert first.result(timeout=5)[0] == 503

        status, started = http.submit("write_note", fields, "concurrent-start")
        assert status == 202
        run = started["run"]
        assert run["temporal_run_id"] and run["engine_state"] == "running"
        lock = rig.service.lock_engine_start(UUID(started["task_id"]))
        assert lock is not None
        with lock:
            assert http.submit("write_note", fields, "concurrent-start") == (202, started)


@pytest.mark.parametrize("submission", [True, False])
def test_task_reads_retry_serialization_failure_with_fresh_authorization(rig, monkeypatch, submission):
    rig.publish("write_note")
    view = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, {"content": "read"}, "read")
    task_id = UUID(view["task_id"])
    original = service_module.require_task
    observed = []

    def check(connection, *args, **kwargs):
        observed.append(connection)
        if len(observed) == 1:
            raise psycopg.errors.SerializationFailure("synthetic conflict with updated grant")
        return original(connection, *args, **kwargs)

    monkeypatch.setattr(service_module, "require_task", check)
    if submission:
        assert rig.service.submission_response(rig.tokens["author"], task_id) == (202, view)
    else:
        assert rig.service.get(rig.tokens["author"], task_id) == view
    assert len(observed) == 2 and observed[0] is not observed[1]


def test_failed_engine_refresh_does_not_return_a_revoked_read(rig, monkeypatch):
    rig.publish("write_note")
    task = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, {"content": "note"}, "revoked")

    async def unavailable(view):
        rig.grant("write_note", "author", Action.READ, False)
        raise RPCError("synthetic unavailable", RPCStatusCode.UNAVAILABLE, b"")

    monkeypatch.setattr(rig.engine, "refresh", unavailable)
    with rig.http() as http:
        assert http.request("GET", "/v1/tasks/" + task["task_id"]) == (
            403, {"schema_version": 1, "code": "permission_denied"},
        )


def test_task_reads_and_engine_refresh_do_not_wait_for_execution_and_terminal_is_preserved(rig, monkeypatch):
    rig.publish("write_note")
    task = rig.service.submit(rig.tokens["author"], "write_note", 1, RESOURCE, {"content": "note"}, "execution")
    task_id, run_id = UUID(task["task_id"]), str(uuid4())
    rig.service.engine(task_id, "running", run_id)

    async def observe(view):
        rig.service.engine(task_id, "completed", run_id, wait=False)

    monkeypatch.setattr(rig.engine, "refresh", observe)
    with rig.owner.open() as held:
        held.execute("SELECT 1 FROM tasks WHERE id=%s FOR UPDATE", (task_id,))
        assert rig.api.get(rig.tokens["author"], task_id)["run"]["engine_state"] == "running"
    assert rig.api.get(rig.tokens["author"], task_id)["run"]["engine_state"] == "completed"
    rig.service.engine(task_id, "running", run_id)
    assert rig.service.get(rig.tokens["author"], task_id)["run"]["engine_state"] == "completed"


def test_credential_revocation_and_cancellation_preserve_committed_receipt(rig):
    name = "normalize_text"
    rig.publish(name)
    previous = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"text": "done"}, "done")
    rig.service.execute(UUID(previous["task_id"]))
    pending = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"text": "pending"}, "pending")
    done = rig.service.cancel(rig.tokens["author"], UUID(previous["task_id"]))
    assert done["state"] == "succeeded" and done["cancel_requested"]
    with rig.owner.open() as conn:
        conn.execute("UPDATE credentials SET revoked=true WHERE id=%s", (rig.credentials["author"],))
    rig.service.execute(UUID(pending["task_id"]))
    rejected = rig.service.system_view(UUID(pending["task_id"]))
    assert rejected["state"] == "denied" and rejected["receipt"]["code"] == "unauthenticated"
    with pytest.raises(Fault, match="unauthenticated"):
        rig.service.get(rig.tokens["author"], UUID(previous["task_id"]))
    expired = "synthetic-expired-token-fixture-000001"
    rig.owner.add_identity(rig.tenant, "author", expired, datetime.now(UTC) - timedelta(seconds=5))
    with pytest.raises(Fault, match="unauthenticated"):
        rig.service.get(expired, UUID(previous["task_id"]))


def test_budget_race_unknown_and_verified_reconciliation(rig):
    name = "fake_delivery"
    rig.publish(name)
    rig.budget(2)
    with rig.http() as http:
        gate = Barrier(2)

        def submit(key):
            gate.wait(timeout=5)
            return http.submit(name, {"mode": "lose_receipt"}, key=key)[1]

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, ("attempt-a", "attempt-b")))
        assert sorted(item["state"] for item in results) == ["denied", "unknown"]
        unknown = next(item for item in results if item["state"] == "unknown")
        assert len(rig.provider.calls) == 1 and rig.budget() == 0
        task = unknown["task_id"]
        assert http.request("POST", f"/v1/tasks/{task}/reconcile")[0] == 403
        status, settled = http.request("POST", f"/v1/tasks/{task}/reconcile", who="admin")
        assert status == 200 and settled["state"] == "succeeded" and rig.budget() == 1
        assert http.request("POST", f"/v1/tasks/{task}/reconcile", who="admin")[1] == settled
        assert len(rig.provider.calls) == 1 and rig.budget() == 1


def test_post_dispatch_commit_loss_is_unknown_and_retriable_as_lookup_only(rig, monkeypatch):
    name = "fake_delivery"
    rig.publish(name)
    rig.budget(2)
    intended = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"mode": "accept"}, "lost-commit")
    task_id = UUID(intended["task_id"])

    def lose_commit(*args):
        raise psycopg.OperationalError("synthetic commit failure")

    with monkeypatch.context() as fault:
        fault.setattr(rig.service, "confirm_external", lose_commit)
        rig.service.execute(task_id)
    assert rig.service.system_view(task_id)["state"] == "unknown"
    assert len(rig.provider.calls) == 1 and rig.budget() == 0
    rig.service.execute(task_id)
    settled = rig.service.reconcile(rig.tokens["admin"], task_id)
    assert settled["state"] == "succeeded"
    assert len(rig.provider.calls) == 1 and rig.budget() == 1


def test_unverifiable_external_keeps_hold_without_resend(rig):
    name = "fake_delivery"
    rig.publish(name)
    rig.budget(2)
    with rig.http() as http:
        _, first = http.submit(name, {"mode": "unverifiable"}, key="no-evidence")
        assert first["state"] == "unknown" and rig.budget() == 0
        assert http.submit(name, {"mode": "unverifiable"}, key="no-evidence")[1] == first
        assert http.request("POST", f"/v1/tasks/{first['task_id']}/reconcile", who="admin")[1]["state"] == "unknown"
        assert len(rig.provider.calls) == 1 and rig.budget() == 0


def test_abandoned_reservation_is_unknown_and_live_send_is_not_reconciled(rig, monkeypatch):
    name = "fake_delivery"
    rig.publish(name)
    rig.budget(2)
    pending = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"mode": "accept"}, "abandoned")
    task_id = UUID(pending["task_id"])
    reserved, release = Event(), Event()

    def interrupted_send(*args):
        reserved.set()
        assert release.wait(10)
        raise RuntimeError("synthetic interruption before the dispatch transaction")

    with monkeypatch.context() as fault, ThreadPoolExecutor(max_workers=1) as pool:
        fault.setattr(rig.service, "send", interrupted_send)
        first = pool.submit(rig.service.execute, task_id)
        try:
            assert reserved.wait(10)
            with pytest.raises(Fault, match="dispatch_inflight"):
                rig.service.reconcile(rig.tokens["admin"], task_id)
            assert rig.service.execute(task_id) is False
            assert rig.service.system_view(task_id)["receipt"]["state"] == "dispatching"
        finally:
            release.set()
        with pytest.raises(RuntimeError, match="synthetic interruption"):
            first.result(timeout=10)
    rig.service.execute(task_id)
    assert rig.service.system_view(task_id)["receipt"]["state"] == "unknown"
    assert rig.service.reconcile(rig.tokens["admin"], task_id)["state"] == "unknown"
    assert rig.provider.calls == [] and rig.budget() == 0


def test_reconciliation_requires_pinned_contract_and_environment(rig):
    name = "fake_delivery"
    rig.publish(name)
    rig.budget(2)
    pending = rig.service.submit(rig.tokens["author"], name, 1, RESOURCE, {"mode": "lose_receipt"}, "drift")
    task_id = UUID(pending["task_id"])
    rig.service.execute(task_id)
    replacements = [
        Catalog(rig.db, "preview", rig.catalog.entries.values()),
        Catalog(rig.db, "dev", [replace(rig.catalog.implementation(name, 1), budget=3)]),
    ]
    for catalog in replacements:
        stale = Service(rig.db, catalog, rig.service.blobs)
        with pytest.raises(Fault, match="contract_drift"):
            stale.reconcile(rig.tokens["admin"], task_id)
    assert rig.budget() == 0
    assert rig.service.reconcile(rig.tokens["admin"], task_id)["state"] == "succeeded"
    assert len(rig.provider.calls) == 1 and rig.budget() == 1


def test_audit_and_otel_ids(rig):
    rig.publish("normalize_text")
    with rig.http() as http:
        _, view = http.submit("normalize_text", {"text": "audit"})
    observed = {span.name: span for span in rig.traces.get_finished_spans()
                if span.attributes.get("operation_id") == view["operation_id"]}
    assert observed["mingjing.submit"].context.trace_id == observed["mingjing.execute"].context.trace_id
    assert observed["mingjing.execute"].attributes["attempt_id"] == view["receipt"]["attempt_id"]
    assert observed["mingjing.execute"].attributes["artifact_id"] == view["receipt"]["artifact_id"]
    with rig.db.open() as conn:
        audit = conn.execute(
            "SELECT event FROM audit WHERE operation_id=%s ORDER BY id", (UUID(view["operation_id"]),),
        ).fetchall()
    assert [event["event"] for event in audit] == ["task_submitted", "execution_allowed", "receipt_succeeded"]


def test_grant_audit_records_each_decision(rig):
    name = "normalize_text"
    rig.lifecycle(name)
    for allowed in (True, False):
        rig.grant(name, "author", Action.EXECUTE, allowed)
    with rig.db.open() as conn:
        rows = conn.execute(
            "SELECT subject,details FROM audit WHERE tenant=%s AND event='grant_changed' ORDER BY id", (rig.tenant,),
        ).fetchall()
    assert rows == [
        {"subject": "admin", "details": {
            "subject": "author", "capability_id": name, "version": 1, "resource": RESOURCE,
            "action": "execute", "allowed": enabled,
        }}
        for enabled in (True, False)
    ]


def test_migration_checksums_and_database_separation(rig, tmp_path):
    assert rig.owner.migrate(Path("migrations")) == []
    for migration in Path("migrations").glob("*.sql"):
        copy2(migration, tmp_path)
    (tmp_path / "0001_core.sql").write_text("SELECT 1;")
    with pytest.raises(RuntimeError, match="applied migration was edited"):
        rig.owner.migrate(tmp_path)
    with rig.db.open() as conn:
        roles = conn.execute(
            """SELECT current_user AS role,has_database_privilege(current_user,'temporal','CONNECT') AS engine,
                      has_database_privilege(current_user,'temporal_visibility','CONNECT') AS visibility,
                      has_table_privilege(current_user,'audit','UPDATE') AS audit_update,
                      has_table_privilege(current_user,'audit','DELETE') AS audit_delete,
                      has_table_privilege(current_user,'subjects','INSERT, UPDATE') AS subject_write,
                      has_table_privilege(current_user,'credentials','SELECT, INSERT, UPDATE') AS credential_access""",
        ).fetchone()
    assert roles.pop("role") == "p2_app"
    assert not any(roles.values())


def test_contract_versions_and_disable_gate(rig):
    name = "normalize_text"
    base = rig.catalog.implementation(name, 1)
    v2 = replace(base, version=2)
    rig.catalog.entries[name, 2] = v2
    rig.publish(name)
    admin, author = rig.tokens["admin"], rig.tokens["author"]
    for action in ("register", "validate", "publish"):
        rig.catalog.transition(admin, name, 2, action)
    assert [item["version"] for item in rig.catalog.discover(author, RESOURCE)] == [1]
    pending = rig.service.submit(author, name, 1, RESOURCE, {"text": "before disable"}, "before")
    emergency_catalog = Catalog(rig.db, "dev", ())
    assert emergency_catalog.transition(admin, name, 1, "disable")["state"] == "disabled"
    rig.service.execute(UUID(pending["task_id"]))
    refused = rig.service.system_view(UUID(pending["task_id"]))
    assert refused["state"] == "denied" and refused["receipt"]["code"] == "release_unavailable"
    assert rig.catalog.discover(author, RESOURCE) == []
    rig.catalog.grant(admin, "author", name, 2, RESOURCE, Action.EXECUTE, True)
    assert [item["version"] for item in rig.catalog.discover(author, RESOURCE)] == [2]
    allowed = rig.service.submit(author, name, 2, RESOURCE, {"text": "version two"}, "after")
    rig.service.execute(UUID(allowed["task_id"]))
    assert rig.service.system_view(UUID(allowed["task_id"]))["state"] == "succeeded"


def test_execution_store_unavailable_prevents_provider_io(rig):
    rig.publish("fake_delivery")
    rig.budget(2)
    staged = rig.service.submit(rig.tokens["author"], "fake_delivery", 1, RESOURCE,
                                {"mode": "accept"}, "database-unavailable")
    unreachable = Database("postgresql://127.0.0.1:1/mingjing")
    failed = Service(unreachable, rig.catalog, rig.service.blobs)
    with pytest.raises(psycopg.OperationalError):
        failed.execute(UUID(staged["task_id"]))
    assert not rig.provider.calls and rig.budget() == 2
    assert rig.service.system_view(UUID(staged["task_id"]))["receipt"] is None
