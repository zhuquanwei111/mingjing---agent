import asyncio
from uuid import uuid4

import psycopg
import pytest

from conftest import count, evidence
from mingjing_p1 import execution, storage
from mingjing_p1.contracts import Job, Principal, Rejected
from mingjing_p1.execution import reconcile_metered


def test_at06_agent_bounds(rig):
    async def run():
        await rig.worker()
        api = await rig.api()
        expired = await rig.api("expired-api", MINGJING_DEADLINE_SECONDS="0")
        client = await rig.client()
        rig.budget(0)
        results = {}
        for scenario, expected, entry, capability in [
            ("test-denied-tool", "agent_tool_denied", api, "record_marker@1"),
            ("test-steps", "agent_step_limit", api, "record_marker@1"),
            ("test-depth", "agent_depth_limit", api, "record_marker@1"),
            ("test-expired", "agent_deadline", expired, "record_marker@1"),
            ("budget-empty", "budget_exhausted", api, "meter_marker@1"),
        ]:
            task = entry.submit("agent", scenario, capability)
            handle = client.get_workflow_handle(task["workflow_id"])
            await rig.waiting(handle)
            assert entry.approve(task)[0] == 202
            result = await asyncio.wait_for(handle.result(), 25)
            assert result["code"] == expected and result["state"] == "denied"
            assert count("markers", task["operation_id"]) == 0
            assert count("attempts", task["operation_id"]) == (1 if expected == "budget_exhausted" else 0)
            results[scenario] = result["code"]
        assert rig.fake.calls == []
        evidence("AT06", {"rejections": results, "provider_calls": 0})

    asyncio.run(run())


def test_at07_parallel_budget_and_unknown_settlement(rig, monkeypatch):
    async def run():
        rig.budget(1)
        folders = [rig.hold(f"gate-{i}", "before_io") for i in range(2)]
        queues = [f"{rig.queue}-{i}" for i in range(2)]
        for i, folder in enumerate(folders):
            await rig.worker(f"worker-{i}", queue=queues[i], MINGJING_PROBE_DIR=str(folder))
        apis = [await rig.api(f"api-{i}", queue=q) for i, q in enumerate(queues)]
        client = await rig.client()
        tasks = [api.submit(capability="meter_marker@1", value=f"race-{i}") for i, api in enumerate(apis)]
        handles = [client.get_workflow_handle(t["workflow_id"]) for t in tasks]
        await asyncio.gather(*(rig.waiting(handle) for handle in handles))
        for api, task in zip(apis, tasks):
            assert api.approve(task)[0] == 202
        await asyncio.gather(*(rig.reached(folder, "before_io", task["operation_id"])
                               for folder, task in zip(folders, tasks)))
        for folder in folders:
            (folder / "before_io.hold").unlink()
        outcomes = await asyncio.wait_for(asyncio.gather(*(handle.result() for handle in handles)), 25)
        assert sorted(result["state"] for result in outcomes) == ["denied", "succeeded"]
        assert rig.budget() == 0 and len(rig.fake.calls) == 1

        rig.budget(1)
        with storage.connect() as connection:
            connection.execute("SELECT tenant FROM accounts WHERE tenant=%s FOR NO KEY UPDATE", (rig.tenant,))
            unavailable = apis[0].submit("direct", "locked-budget", "meter_marker@1")
            assert unavailable["code"] == "gate_unavailable"
        assert len(rig.fake.calls) == 1 and rig.budget() == 1

        unknown = apis[0].submit("direct", "drop-cost", "meter_marker@1", "lost-cost")
        assert unknown["state"] == "unknown" and rig.budget() == 0
        assert apis[0].submit("direct", "drop-cost", "meter_marker@1", "lost-cost") == unknown
        with storage.connect() as connection:
            reserve = connection.execute("SELECT reserved,state FROM attempts WHERE id=%s", (unknown["attempt_id"],)).fetchone()
        assert reserve == {"reserved": 1, "state": "unknown"}
        external_ref = rig.fake.ledger[unknown["operation_id"]]
        settled = reconcile_metered(unknown["task_id"], unknown["attempt_id"], external_ref)
        assert reconcile_metered(unknown["task_id"], unknown["attempt_id"], external_ref) == settled
        assert settled["state"] == "succeeded" and rig.budget() == 0
        assert rig.fake.calls.count(unknown["operation_id"]) == 1

        rig.budget(1)
        send = storage.create_task(
            Principal(rig.tenant, "author"),
            {"kind": "direct", "capability": "meter_marker@1", "value": "synthetic-commit-loss"},
            "meter-commit-loss",
        )
        job = Job(send["id"], send["operation_id"], None, False, kind="direct")
        finish = execution.finish

        def fail_after_dispatch(conn, task, result):
            if result["state"] == "succeeded":
                raise psycopg.OperationalError("synthetic connection failure before settlement commit")
            return finish(conn, task, result)

        with monkeypatch.context() as fault:
            fault.setenv("MINGJING_PROVIDER_URL", rig.fake.url)
            fault.setattr(execution, "finish", fail_after_dispatch)
            attempt = execution.execute(job, str(uuid4()))
        assert attempt["state"] == "unknown" and attempt["code"] == "unconfirmed_dispatch"
        assert apis[0].task(attempt)["result"] == attempt and rig.budget() == 0
        assert execution.execute(job, str(uuid4())) == attempt
        assert rig.fake.calls.count(send["operation_id"]) == 1
        evidence("AT07", {"race_outcomes": [o["state"] for o in outcomes], "race_dispatches": 1,
                          "budget_lock": "gate_unavailable", "unknown_reservation": reserve,
                          "reconciled": settled["state"], "remaining": rig.budget(),
                          "post_send_db_failure": attempt["state"], "post_send_dispatches": 1})

    asyncio.run(run())


def test_at08_artifact_versions_and_current_permissions(rig):
    async def run():
        api = await rig.api()
        result = api.submit("direct", "first-version", key="artifact")
        with storage.connect() as connection:
            task = storage.for_update(connection, result["task_id"])
            version2 = storage.add_artifact(connection, task, 2, "second-version")
        first = api.request("GET", f"/artifacts/{result['artifact_id']}")
        second = api.request("GET", f"/artifacts/{version2}")
        assert first[0] == second[0] == 200
        assert [first[1]["version"], second[1]["version"]] == [1, 2]
        assert first[1]["sha256"] != second[1]["sha256"]
        assert api.submit("direct", "first-version", key="artifact") == result
        with pytest.raises(Rejected, match="artifact_version_conflict"):
            with storage.connect() as connection:
                task = storage.for_update(connection, result["task_id"])
                storage.add_artifact(connection, task, 1, "different-value")
        assert api.request("GET", f"/artifacts/{result['artifact_id']}") == first
        foreign = api.request("GET", f"/artifacts/{result['artifact_id']}", who="other")
        assert foreign[0] == 404
        rig.grant("read", False)
        revoked = api.request("GET", f"/artifacts/{result['artifact_id']}")
        assert revoked[0] == 403
        evidence("AT08", {"versions": [first[1], second[1]], "tenant_denial": foreign[0],
                          "revocation_denial": revoked[0], "same_version_overwrite": "rejected"})

    asyncio.run(run())
