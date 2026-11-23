import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn(name="BExecution")
class Execution:
    def __init__(self):
        self.paused_at = ""
        self.released = False

    @workflow.signal(name="release")
    def release(self):
        self.released = True

    @workflow.query(name="paused")
    def paused(self) -> str:
        return self.paused_at

    @workflow.run
    async def run(self, request: dict):
        scope = request["case"]
        op = request["kind"]
        params = request.get("args", {})
        if op == "supervise":
            return await workflow.execute_child_workflow("BExecution", {"case": request["case"], "kind": "supplier"}, id=workflow.info().workflow_id + "-supplier")
        if op == "family":
            children = []
            for child in params:
                children.append(await workflow.start_child_workflow("BExecution",
                                                                    {"case": scope, "kind": "child", "args": child}, id=f"{workflow.info().workflow_id}-{child}"))
            return await asyncio.gather(*children)
        operations = [("stage", name) for name in params["steps"]] if op == "staged" else [(op, params)]
        for action, arg in operations:
            if op == "staged" and params.get("pause") == arg:
                self.paused_at = arg
                await workflow.wait_condition(lambda: self.released)
                self.paused_at = ""
            result = await workflow.execute_activity("b_execute", {"case": scope, "kind": action, "args": arg},
                                                     start_to_close_timeout=timedelta(
                                                         seconds=150 if action == "agent" else 14),
                                                     retry_policy=RetryPolicy(maximum_attempts=3 if action in ("supplier", "child") else 1,
                                                                              initial_interval=timedelta(seconds=1)))
            if result == "denied":
                break
        return result
