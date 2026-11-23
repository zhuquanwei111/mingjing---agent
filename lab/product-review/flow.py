from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class Round:
    @workflow.run
    async def run(self, scope: str) -> str:
        return await workflow.execute_activity(
            "round_step", scope,
            start_to_close_timeout=timedelta(seconds=45), heartbeat_timeout=timedelta(seconds=6),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=2),
        )


@workflow.defn
class Notice:
    @workflow.run
    async def run(self, scope: str) -> str:
        return await workflow.execute_activity("late_notice", scope, start_to_close_timeout=timedelta(seconds=15),
                                              retry_policy=RetryPolicy(maximum_attempts=1))
