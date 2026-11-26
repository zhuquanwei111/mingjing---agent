"""Durable product routes. The workflow never reads the business database."""

from dataclasses import asdict, replace
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from temporalio.langgraph import graph

    from mingjing_p1.contracts import Job

RETRY = RetryPolicy(initial_interval=timedelta(milliseconds=400), maximum_attempts=2)


@workflow.defn
class MarkerChild:
    @workflow.run
    async def run(self, job: Job) -> dict:
        return await workflow.execute_activity(
            "execute_job", job, result_type=dict,
            start_to_close_timeout=timedelta(seconds=20),
            schedule_to_close_timeout=timedelta(seconds=30),
            heartbeat_timeout=timedelta(seconds=2),
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
            retry_policy=RETRY,
        )


@workflow.defn
class Gateway:
    @workflow.init
    def __init__(self, job: Job) -> None:
        self.phase = "starting"
        self.decision: str | None = None
        self.decision_count = 0
        self.expected = job.decision_id

    @workflow.signal
    def approve(self, decision_id: str) -> None:
        if decision_id == self.expected and self.decision is None:
            self.decision = decision_id
            self.decision_count += 1

    @workflow.query
    def state(self) -> dict:
        return {"phase": self.phase, "decision_count": self.decision_count}

    @workflow.run
    async def run(self, job: Job) -> dict:
        if job.kind == "agent":
            return await self.run_agent(job)
        self.phase = "waiting"
        await workflow.wait_condition(lambda: self.decision is not None)
        self.phase = "running"
        output = await workflow.execute_child_workflow(
            MarkerChild.run, job, id=f"{workflow.info().workflow_id}-marker",
            cancellation_type=workflow.ChildWorkflowCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        self.phase = "finished"
        return output

    async def run_agent(self, job: Job) -> dict:
        job = replace(job, deadline_epoch=workflow.time() + job.deadline_seconds)
        app = graph("p1-agent").compile(checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": workflow.info().workflow_id}}
        first = await app.ainvoke({"job": asdict(job)}, config)
        if first.get("denial"):
            self.phase = "finished"
            return await self.reject(job, first["denial"])
        if not first.get("__interrupt__"):
            raise RuntimeError("expected one approval interrupt")
        self.phase = "waiting"
        await workflow.wait_condition(lambda: self.decision is not None)
        self.phase = "running"
        state = await app.ainvoke(Command(resume=self.decision), config)
        final = await self.reject(job, state["denial"]) if state.get("denial") else state["result"]
        self.phase = "finished"
        return final

    async def reject(self, job: Job, reason: str) -> dict:
        return await workflow.execute_activity(
            "reject_agent", args=[job, reason], result_type=dict,
            start_to_close_timeout=timedelta(seconds=5), retry_policy=RETRY,
        )
