import asyncio
import json
import os
import socket

import pytest

from conftest import count, evidence, eventually
from mingjing_p1 import storage


def test_at11_trace_correlation_and_sink_failure(rig):
    async def run():
        trace = rig.root / "traces.jsonl"
        trace.touch()
        await rig.worker(MINGJING_TRACE_FILE=str(trace))
        api = await rig.api(MINGJING_TRACE_FILE=str(trace))
        client = await rig.client()
        task = api.submit("agent")
        handle = client.get_workflow_handle(task["workflow_id"])
        await rig.waiting(handle)
        assert api.approve(task)[0] == 202
        result = await asyncio.wait_for(handle.result(), 25)

        def spans():
            try:
                return [json.loads(line) for line in trace.read_text().splitlines()]
            except json.JSONDecodeError:
                return []

        await eventually(lambda: any(span["name"] == "mingjing.tool" for span in spans()),
                         message="tool span")
        items = spans()
        api_span = next(span for span in items if span["name"] == "mingjing.api.submit")
        agent_span = next(span for span in items if span["name"] == "mingjing.agent_tool")
        tool_span = next(span for span in items if span["name"] == "mingjing.tool")
        trace_id = api_span["trace_id"]
        assert trace_id == agent_span["trace_id"] == tool_span["trace_id"] != "0" * 32
        chain = [span["name"] for span in items if span["trace_id"] == trace_id]
        assert any("RunWorkflow:Gateway" in name for name in chain), chain
        assert any("RunActivity:p1-agent.tool" in name for name in chain), chain
        for key in ("task_id", "run_id", "workflow_id", "operation_id", "attempt_id", "artifact_id"):
            assert tool_span["attrs"][key] == result[key]
        with storage.connect() as conn:
            audits = conn.execute(
                "SELECT code,attempt_id FROM audit WHERE task_id=%s ORDER BY id", (task["task_id"],),
            ).fetchall()
        assert {"code": "committed", "attempt_id": result["attempt_id"]} in audits

        failing = rig.root / "failed-sink.jsonl"
        bad = await rig.api("failed-sink", MINGJING_TRACE_FILE=str(failing), MINGJING_TRACE_FAIL="1")
        committed = bad.submit("direct", "while-exporter-fails")
        assert committed["state"] == "succeeded"
        assert count("receipts", committed["operation_id"]) == 1
        with storage.connect() as conn:
            asserted = conn.execute(
                "SELECT code FROM audit WHERE operation_id=%s AND code='committed'",
                (committed["operation_id"],),
            ).fetchone()
        assert asserted == {"code": "committed"}
        assert all(not json.loads(line)["exported"] for line in failing.read_text().splitlines())
        assert failing.stat().st_size > 0
        evidence("AT11", {"trace_id": trace_id, "span_chain": chain, "ids": tool_span["attrs"],
                          "audit_codes": [row["code"] for row in audits],
                          "export_failure": "injected", "receipt_persisted": True, "audit_persisted": True})

    asyncio.run(run())


def test_at12_internal_network_and_database_permissions(rig):
    with storage.connect() as conn:
        info = conn.execute(
            "SELECT current_user AS role,current_database() AS database,current_setting('server_version') AS version",
        ).fetchone()
        assert info["role"] == "p1_app" and info["database"] == "mingjing"
        assert info["version"].startswith("17.12")
        denied = conn.execute("SELECT has_database_privilege(current_user,'temporal','CONNECT') AS allowed").fetchone()
        assert not denied["allowed"]
        denied_visibility = conn.execute(
            "SELECT has_database_privilege(current_user,'temporal_visibility','CONNECT') AS allowed",
        ).fetchone()
        assert not denied_visibility["allowed"]
    assert os.getuid() == 10101
    with pytest.raises(OSError):
        # RFC 5737 test address. An internal bridge cannot route it.
        socket.create_connection(("203.0.113.1", 443), timeout=0.4)
    evidence("AT12-network", {"database": info, "temporal_db_connect": False,
                              "temporal_visibility_connect": False, "runner_uid": os.getuid(),
                              "external_route": "blocked"})
