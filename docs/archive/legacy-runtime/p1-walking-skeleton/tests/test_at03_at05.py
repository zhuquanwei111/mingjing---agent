import asyncio

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import CancelledError

from conftest import child_id, count, evidence, eventually
from mingjing_p1 import storage


def test_at03_commit_before_ack_and_unknown_external(rig):
    async def run():
        control = rig.hold("commit", "after_commit")
        first = await rig.worker("first", MINGJING_PROBE_DIR=str(control))
        api = await rig.api()
        client = await rig.client()
        task = api.submit()
        handle = client.get_workflow_handle(task["workflow_id"])
        await rig.waiting(handle)
        assert api.approve(task)[0] == 202
        operation = task["operation_id"]
        await rig.reached(control, "after_commit", operation)
        assert count("markers", operation) == count("receipts", operation) == 1
        child = client.get_workflow_handle(child_id(task))
        before = await child.fetch_history()
        assert not any(e.HasField("activity_task_completed_event_attributes") for e in before.events)
        first.stop(kill=True)
        await rig.worker("replacement")
        result = await asyncio.wait_for(handle.result(), 25)
        assert api.task(task)["result"] == result
        assert count("markers", operation) == count("receipts", operation) == 1
        assert count("attempts", operation) == 2
        after = await child.fetch_history()
        activity_attempt = next(e.activity_task_started_event_attributes.attempt for e in after.events
                                if e.HasField("activity_task_started_event_attributes"))
        assert activity_attempt == 2

        external = api.submit("direct", "drop-receipt", "external_marker@1", "external-once")
        assert external["state"] == "unknown"
        assert api.submit("direct", "drop-receipt", "external_marker@1", "external-once") == external
        assert rig.fake.calls.count(external["operation_id"]) == 1
        assert api.task(external)["status"] == "unknown"
        evidence("AT03", {"before_ack_marker": 1, "after_recovery_marker": count("markers", operation),
                          "receipt_count": count("receipts", operation), "attempts": count("attempts", operation),
                          "history_attempt": activity_attempt, "killed_worker_status": first.process.returncode,
                          "external_state": external["state"], "external_dispatch_count": 1})

    asyncio.run(run())


def test_at04_approval_revocation_publication_and_store_failure(rig):
    async def run():
        control = rig.hold("io", "before_io")
        await rig.worker(MINGJING_PROBE_DIR=str(control))
        api = await rig.api()
        client = await rig.client()

        task = api.submit()
        handle = client.get_workflow_handle(task["workflow_id"])
        await rig.waiting(handle)
        assert api.approve(task, who="author") == (403, {"code": "authorization_denied"})
        assert api.approve(task)[0] == 202
        await rig.reached(control, "before_io", task["operation_id"])
        rig.grant("write", False)
        (control / "before_io.hold").unlink()
        denied = await asyncio.wait_for(handle.result(), 25)
        assert denied["code"] == "authorization_denied"
        assert count("markers", task["operation_id"]) == 0
        rig.grant("write", True)
        task2 = api.submit()
        handle2 = client.get_workflow_handle(task2["workflow_id"])
        await rig.waiting(handle2)
        with storage.connect() as conn:
            conn.execute("UPDATE published SET enabled=false WHERE tenant=%s AND capability='record_marker@1'",
                         (rig.tenant,))
        assert api.approve(task2)[0] == 202
        disabled = await asyncio.wait_for(handle2.result(), 25)
        assert disabled["code"] == "release_disabled"
        assert count("markers", task2["operation_id"]) == 0
        with storage.connect() as conn:
            conn.execute("UPDATE published SET enabled=true WHERE tenant=%s", (rig.tenant,))
            audit = conn.execute("SELECT code FROM audit WHERE tenant=%s ORDER BY id", (rig.tenant,)).fetchall()

        broken_queue = f"{rig.queue}-broken"
        await rig.worker("unavailable-store", queue=broken_queue, MINGJING_DB_DSN="postgresql://127.0.0.1:2/p1")
        broken = await rig.api("broken-queue-api", queue=broken_queue)
        task3 = broken.submit()
        handle3 = client.get_workflow_handle(task3["workflow_id"])
        await rig.waiting(handle3)
        assert broken.approve(task3)[0] == 202
        unavailable = await asyncio.wait_for(handle3.result(), 25)
        assert unavailable["code"] == "gate_unavailable"
        assert count("markers", task3["operation_id"]) == 0
        evidence("AT04", {"revoked": denied["code"], "disabled": disabled["code"],
                          "db_unavailable": unavailable["code"], "unauthenticated_approval": 403,
                          "audit_codes": [row["code"] for row in audit], "markers": [0, 0, 0]})

    asyncio.run(run())


async def cancelled(handle):
    with pytest.raises(WorkflowFailureError) as closed:
        await asyncio.wait_for(handle.result(), 20)
    assert isinstance(closed.value.cause, CancelledError)


def test_at05_cancellation_before_during_and_after_commit(rig):
    async def run():
        control = rig.hold("execute", "before_io")
        await rig.worker(MINGJING_PROBE_DIR=str(control))
        api = await rig.api()
        client = await rig.client()

        awaiting = api.submit()
        handle = client.get_workflow_handle(awaiting["workflow_id"])
        await rig.waiting(handle)
        api.cancel(awaiting)
        await cancelled(handle)
        assert count("markers", awaiting["operation_id"]) == 0
        assert api.task(awaiting)["status"] == "cancelled"

        active = api.submit()
        running = client.get_workflow_handle(active["workflow_id"])
        await rig.waiting(running)
        assert api.approve(active)[0] == 202
        await rig.reached(control, "before_io", active["operation_id"])
        api.cancel(active)
        await cancelled(running)
        await cancelled(client.get_workflow_handle(child_id(active)))
        await eventually(lambda: (control / "before_io.cancelled").exists(), message="activity cancellation")
        assert count("markers", active["operation_id"]) == 0

        (control / "before_io.hold").unlink()
        (control / "after_commit.hold").touch()
        committed = api.submit()
        final_run = client.get_workflow_handle(committed["workflow_id"])
        await rig.waiting(final_run)
        assert api.approve(committed)[0] == 202
        await rig.reached(control, "after_commit", committed["operation_id"])
        api.cancel(committed)
        await cancelled(final_run)
        await cancelled(client.get_workflow_handle(child_id(committed)))
        final = api.task(committed)
        assert final["cancel_requested"] and final["status"] == "succeeded"
        assert count("markers", committed["operation_id"]) == 1

        (control / "after_commit.hold").unlink()
        (control / "before_io.hold").touch()
        agent = api.submit("agent")
        agent_run = client.get_workflow_handle(agent["workflow_id"])
        await rig.waiting(agent_run)
        assert api.approve(agent)[0] == 202
        await rig.reached(control, "before_io", agent["operation_id"])
        api.cancel(agent)
        await cancelled(agent_run)
        assert count("markers", agent["operation_id"]) == 0
        evidence("AT05", {"waiting": "cancelled", "child": "cancelled",
                          "heartbeat_cancel_observed": True, "after_commit_product_state": final,
                          "agent_default_error_handler": "cancelled"})

    asyncio.run(run())
