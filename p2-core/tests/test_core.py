import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import copy2
from threading import Barrier, Event
from uuid import UUID

import psycopg
import pytest

from conftest import RESOURCE
from mingjing.catalog import Catalog
from mingjing.contracts import Action, Fault
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
                      has_table_privilege(current_user,'audit','DELETE') AS audit_delete""",
        ).fetchone()
    assert roles == {"role": "p2_app", "engine": False, "visibility": False, "audit_update": False, "audit_delete": False}


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
    rig.catalog.transition(admin, name, 1, "disable")
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
