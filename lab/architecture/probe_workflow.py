from temporalio import workflow


@workflow.defn(name="MjLabPreflightV1")
class PreflightWorkflow:
    @workflow.run
    async def run(self, marker: str) -> str:
        return marker
