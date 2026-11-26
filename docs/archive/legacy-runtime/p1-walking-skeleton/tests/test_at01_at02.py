import asyncio

from conftest import count, evidence
from mingjing_p1 import storage
from mingjing_p1.temporal.workflows import Gateway


def test_at01_shared_capability_and_idempotency(rig):
    async def run():
        await rig.worker()
        api = await rig.api()
        client = await rig.client()
        captures = []
        expected_keys = None
        for kind in ("direct", "workflow", "agent"):
            started = api.submit(kind, value=f"synthetic-{kind}", key=f"at01-{kind}")
            repeated = api.submit(kind, value=f"synthetic-{kind}", key=f"at01-{kind}")
            assert repeated["task_id"] == started["task_id"]
            if kind == "direct":
                final = started
            else:
                handle = client.get_workflow_handle(started["workflow_id"])
                await rig.waiting(handle)
                assert api.approve(started)[0] == 202
                final = await asyncio.wait_for(handle.result(), 25)
            if expected_keys is None:
                expected_keys = set(final)
            assert set(final) == expected_keys
            assert final["schema_version"] == 1 and final["state"] == "succeeded"
            assert count("markers", final["operation_id"]) == count("receipts", final["operation_id"]) == 1
            assert api.task(started)["result"] == final
            captures.append({"kind": kind, "result": final})
        second = api.submit("direct", value="other-capability", capability="record_note@1")
        assert second["state"] == "succeeded"
        status, body = api.request("POST", "/tasks", key="at01-direct",
                                   body={"kind": "direct", "capability": "record_marker@1", "value": "changed"})
        assert (status, body["code"]) == (409, "request_key_conflict")
        evidence("AT01", {"shared_contract": captures, "registered_capability": second})

    asyncio.run(run())


def test_at02_worker_restart_duplicate_and_late_approval(rig):
    async def run():
        control = rig.hold("pause", "before_io")
        old = await rig.worker("old")
        api = await rig.api()
        client = await rig.client()
        task = api.submit()
        handle = client.get_workflow_handle(task["workflow_id"])
        assert await rig.waiting(handle) == {"phase": "waiting", "decision_count": 0}
        old.stop(kill=True)
        await rig.worker("replacement", MINGJING_PROBE_DIR=str(control))
        assert await rig.waiting(handle) == {"phase": "waiting", "decision_count": 0}
        await handle.signal(Gateway.approve, "obsolete-decision")
        first = api.approve(task)
        second = api.approve(task)
        assert first == second and first[0] == 202
        await rig.reached(control, "before_io", task["operation_id"])
        assert (await handle.query(Gateway.state))["decision_count"] == 1
        (control / "before_io.hold").unlink()
        result = await asyncio.wait_for(handle.result(), 25)
        assert result["state"] == "succeeded"
        assert api.task(task)["result"] == result
        with storage.connect() as conn:
            conn.execute("UPDATE approvals SET expires_at=clock_timestamp() WHERE task_id=%s", (task["task_id"],))
            approvals = conn.execute("SELECT COUNT(*) AS n FROM audit WHERE task_id=%s AND code='approval_accepted'",
                                     (task["task_id"],)).fetchone()["n"]
        assert api.approve(task)[0] == 409 and approvals == 1
        history = await handle.fetch_history()
        signals = sum(e.HasField("workflow_execution_signaled_event_attributes") for e in history.events)
        assert signals == 3
        evidence("AT02", {"old_worker_exit": old.process.returncode, "signals": signals,
                          "accepted_decisions": approvals, "result": result})

    asyncio.run(run())
