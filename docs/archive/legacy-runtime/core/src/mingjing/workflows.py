from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporalio.langgraph import graph

OPTIONS = {
    "start_to_close_timeout": timedelta(seconds=20),
    "schedule_to_close_timeout": timedelta(seconds=60),
    "retry_policy": RetryPolicy(maximum_attempts=3),
}


@dataclass(frozen=True)
class TaskJob:
    task_id: str
    agent: bool


@workflow.defn(name="MingjingTaskV1")
class TaskWorkflow:
    def __init__(self) -> None:
        self.notified = False

    @workflow.signal
    def notify(self) -> None:
        self.notified = True

    @workflow.run
    async def run(self, job: TaskJob) -> None:
        while True:
            self.notified = False
            phase = await workflow.execute_activity("mingjing.check.v1", job.task_id, result_type=str, **OPTIONS)
            if phase == "ready":
                break
            if phase == "done":
                return
            try:
                await workflow.wait_condition(lambda: self.notified, timeout=timedelta(seconds=3))
            except TimeoutError:
                pass
        if job.agent:
            await graph("mingjing.agent.v1").compile().ainvoke({"task_id": job.task_id})
        else:
            await workflow.execute_activity("mingjing.execute.v1", job.task_id, **OPTIONS)
