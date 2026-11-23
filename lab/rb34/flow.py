from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class GovernedRequest:
    def __init__(self):
        self.control = "active"

    @workflow.signal
    def product_control(self, action: str):
        self.control = action

    @workflow.run
    async def run(self, scope: str) -> dict:
        result = await workflow.execute_activity(
            "dispatch", scope, start_to_close_timeout=timedelta(seconds=80),
            retry_policy=RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=1)),
        )
        return {"observed_control": self.control, "result": result}


@workflow.defn
class ReceiptNotice:
    @workflow.run
    async def run(self, scope: str) -> str:
        return await workflow.execute_activity(
            "reconcile_notice", scope, start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
