import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

@workflow.defn(name="AExecution")
class Execution:
    @workflow.run
    async def run(self,req:dict):
        async def activity(kind,args):
            return await workflow.execute_activity("a_execute",{"case":req["case"],"kind":kind,"args":args},
                start_to_close_timeout=timedelta(seconds=150 if kind=="agent" else 14),
                retry_policy=RetryPolicy(maximum_attempts=3 if kind in ("supplier","child") else 1,
                                         initial_interval=timedelta(seconds=1)))
        cmd,args=req["kind"],req.get("args",{})
        if cmd=="family":
            return await asyncio.gather(*(workflow.execute_child_workflow("AExecution",
                {"case":req["case"],"kind":"child","args":n},id=workflow.info().workflow_id+"-"+n) for n in args))
        if cmd=="staged":
            for action in args:
                answer=await activity("stage",action)
                if answer!="ok":return answer
            return "ok"
        return await activity(cmd,args)

