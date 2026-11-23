"""Neutral runner mounting exactly one submitted route."""
import asyncio, importlib, os
from concurrent.futures import ThreadPoolExecutor
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

route=os.environ["LAB_ROUTE"]
impl=importlib.import_module(route+".runtime")
flow=importlib.import_module(route+".flow")
@activity.defn(name=route+"_execute")
def dispatch(req:dict):
    op,scope,args=req["kind"],req["case"],req["args"]
    if op=="tool":return impl.tool(scope,args["name"],args["data"],os.environ["LAB_TOKEN"])
    if op=="supplier":return impl.supplier(scope)
    if op=="continuous":
        for step in args:
            outcome=impl.stage(scope,step)
            if outcome!="ok":return outcome
        return "ok"
    return getattr(impl,op)(scope,args)
async def main():
    client=await Client.connect("temporal:7233",namespace=os.environ["LAB_NS"])
    with ThreadPoolExecutor(max_workers=12) as pool:
        worker=Worker(client,task_queue=os.environ["LAB_NS"],workflows=[flow.Execution],activities=[dispatch],activity_executor=pool)
        print("WORKER_READY",os.getpid(),flush=True)
        await worker.run()
if __name__=="__main__":asyncio.run(main())

