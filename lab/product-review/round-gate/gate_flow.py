from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

MAIN = "round-gate-main"
SIDE = "round-gate-side"


@workflow.defn
class GateRound:
    def __init__(self):
        self.notices = 0
        self.ready = False
        self.terminal = ""

    @workflow.signal
    async def notice(self, notification: str):
        self.notices += 1
        queue = MAIN if self.notices % 2 else SIDE
        await workflow.wait_condition(lambda: self.ready)
        result = await workflow.execute_activity(
            "gate_notice", args=[self.scope, notification], task_queue=queue,
            start_to_close_timeout=timedelta(seconds=90),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        if result in ("delivered", "revoked_settled"):
            self.terminal = result

    @workflow.run
    async def run(self, scope: str) -> str:
        self.scope = scope
        outcome = await workflow.execute_activity(
            "gate_initial", scope, start_to_close_timeout=timedelta(seconds=120),
            heartbeat_timeout=timedelta(seconds=12),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=2),
        )
        if outcome == "accepted":
            outcome = await workflow.execute_activity(
                "gate_lookup", scope, start_to_close_timeout=timedelta(seconds=90),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
        if outcome != "tool_unknown":
            return outcome
        self.ready = True
        await workflow.wait_condition(lambda: bool(self.terminal))
        await workflow.wait_condition(workflow.all_handlers_finished)
        return self.terminal


@workflow.defn
class DuplicateEntry:
    @workflow.run
    async def run(self, scope: str) -> str:
        return await workflow.execute_activity(
            "gate_duplicate", scope, task_queue=SIDE,
            start_to_close_timeout=timedelta(seconds=30), retry_policy=RetryPolicy(maximum_attempts=1),
        )
