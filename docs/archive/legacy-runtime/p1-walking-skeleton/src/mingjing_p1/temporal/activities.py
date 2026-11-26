"""Temporal Activities and the runner-owned fault barriers."""

import asyncio
import os
from pathlib import Path

from temporalio import activity

from mingjing_p1 import execution, storage
from mingjing_p1.contracts import Job
from mingjing_p1.telemetry import tracer


async def barrier(phase: str, operation: str) -> None:
    control = os.environ.get("MINGJING_PROBE_DIR")
    if not control:
        return
    root = Path(control)
    hold = root / f"{phase}.hold"
    if hold.exists():
        (root / f"{phase}.reached").write_text(operation)
        try:
            while hold.exists():
                activity.heartbeat(phase)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            (root / f"{phase}.cancelled").write_text(operation)
            raise


@activity.defn
async def execute_job(job: Job) -> dict:
    info = activity.info()
    attempt = f"{info.workflow_run_id}:{info.activity_id}:{info.attempt}"
    activity.heartbeat("starting")
    await barrier("before_io", job.operation_id)
    result = await asyncio.to_thread(
        execution.execute, job, attempt, info.workflow_run_id, info.attempt,
    )
    if result["state"] == "succeeded":
        await barrier("after_commit", job.operation_id)
    return result


@activity.defn
async def reject_agent(job: Job, reason: str) -> dict:
    info = activity.info()
    attempt = f"{info.workflow_run_id}:{info.activity_id}:{info.attempt}"

    def record() -> dict:
        with storage.connect() as conn:
            return execution.deny(conn, storage.for_update(conn, job.task_id), attempt, reason)

    return await asyncio.to_thread(record)


async def agent_tool(state: dict) -> dict:
    job = Job(**state["job"])
    with tracer().start_as_current_span("mingjing.agent_tool", attributes={
        "task_id": job.task_id, "operation_id": job.operation_id,
    }):
        return {"result": await execute_job(job)}
