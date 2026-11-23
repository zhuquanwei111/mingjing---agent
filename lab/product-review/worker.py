"""Reference-only Temporal activity and versioned external-tool checkpoint adapter."""
import asyncio
import hashlib
import importlib
import json
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg
from openai import AsyncOpenAI
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic_ai import (Agent, CallDeferred, DeferredToolRequests, DeferredToolResults,
                         ModelMessagesTypeAdapter, Tool, UsageLimits)
from pydantic_ai.exceptions import UserError
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from flow import Notice, Round

RELEASE = importlib.import_module(os.environ["BUILD_MODULE"])


def db():
    return psycopg.connect(os.environ["PRODUCT_DSN"], row_factory=dict_row)


def log(c, scope, kind, detail):
    c.execute("INSERT INTO events(scope,kind,detail) VALUES (%s,%s,%s)", (scope,kind,Jsonb(detail)))


def read(scope):
    with db() as c:
        return c.execute("SELECT * FROM task WHERE scope=%s",(scope,)).fetchone()


def http(scope, path, data=None):
    req = Request(f"http://provider:8080/{scope}/{path}",
                  data=json.dumps(data).encode() if data is not None else None,
                  headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=4) as reply:
        return json.load(reply)


def agent_for(row):
    def defer(**kwargs):
        raise CallDeferred
    desc = row["descriptor"]
    tool = Tool.from_schema(defer, name=desc["name"], description=desc["description"],
                            json_schema=desc["input_schema"], takes_ctx=False)
    client = AsyncOpenAI(base_url=f"http://provider:8080/{row['scope']}/v1",
                         api_key="local-test-only",max_retries=0)
    class MeteredModel(OpenAIChatModel):
        async def request(self,*args,**kwargs):
            charge_model_slot(row["scope"])
            return await super().request(*args,**kwargs)
    model = MeteredModel("fixture", provider=OpenAIProvider(openai_client=client))
    return Agent(model,tools=[tool],output_type=[str, DeferredToolRequests]),client


def charge_model_slot(scope):
    with db() as c:
        row = c.execute("""UPDATE task SET model_slots=model_slots+1
                  WHERE scope=%s AND active AND model_slots<2 RETURNING model_slots""",(scope,)).fetchone()
        if row is None:
            raise PermissionError("product model limit or cancellation")


async def checkpoint_first(scope):
    row = read(scope)
    agent,client = agent_for(row)
    try:
        result = await agent.run("Request the registered asynchronous operation on " + row["marker"],
                                 usage_limits=UsageLimits(request_limit=1))
    finally:
        await client.close()
    assert isinstance(result.output,DeferredToolRequests) and len(result.output.calls)==1
    call, = result.output.calls
    assert call.tool_name == row["descriptor"]["name"] and call.args_as_dict() == {"ref":row["marker"]}
    history = json.loads(result.all_messages_json())
    op = str(uuid.uuid4())
    serialized = RELEASE.encode(row["writer_format"], history, op, call.tool_call_id)
    with db() as c:
        changed = c.execute("""UPDATE task SET op=%s,call=%s,msg=%s,checkpoint_version=%s,
                 held=3,state='dispatch_intent' WHERE scope=%s AND op IS NULL AND active RETURNING op""",
                            (op,call.tool_call_id,Jsonb(serialized),row["writer_format"],scope)).fetchone()
        if not changed:
            raise RuntimeError("conflicting initial intent")
        log(c,scope,"checkpoint",{"version":row["writer_format"],"op":op,"call":call.tool_call_id,
                                  "sdk_run":result.run_id,"conversation":result.conversation_id})
    ack = http(scope,"submit",{"op":op,"call":call.tool_call_id,"name":call.tool_name,"input":call.args_as_dict()})
    assert ack == {"accepted":True}
    with db() as c:
        c.execute("UPDATE task SET state='accepted' WHERE scope=%s",(scope,))
    while True:
        activity.heartbeat()
        await asyncio.sleep(.2)


def settle(scope, receipt):
    with db() as c:
        row = c.execute("SELECT * FROM task WHERE scope=%s FOR UPDATE",(scope,)).fetchone()
        if (receipt["op"],receipt["call"],receipt["units"]) != (row["op"],row["call"],1):
            raise ValueError("unbound receipt")
        if row["settled"] is None:
            c.execute("UPDATE task SET settled=%s,spent=%s,held=0 WHERE scope=%s",
                      (receipt["receipt"],receipt["units"],scope))
        elif row["settled"] != receipt["receipt"]:
            raise ValueError("conflicting business receipt")
        log(c,scope,"settle",{"new":row["settled"] is None,"active":row["active"]})


def status(scope, name):
    with db() as c:
        c.execute("UPDATE task SET state=%s WHERE scope=%s",(name,scope))
    return name


async def resume(scope, notice=False):
    row = read(scope)
    receipt = http(scope,"lookup/"+row["op"])
    if not receipt["known"]:
        return status(scope,"unknown")
    settle(scope,receipt)
    if not read(scope)["active"]:
        return status(scope,"cancelled_settled")
    if notice:
        raise ValueError("late notice has no authority to dispatch")
    decoded = RELEASE.decode(row)
    if decoded is None:
        return status(scope,"version_quarantine")
    messages = ModelMessagesTypeAdapter.validate_python(decoded)
    call = row["call"] if not row["wrong_pair"] else "invalid_" + uuid.uuid4().hex
    agent,client = agent_for(row)
    try:
        result = await agent.run(message_history=messages,
                                 deferred_tool_results=DeferredToolResults(calls={call:receipt["receipt"]}),
                                 usage_limits=UsageLimits(request_limit=1))
    except UserError as exc:
        if not row["wrong_pair"]:
            raise
        with db() as c:
            log(c,scope,"rejected_pair",{"exception":type(exc).__name__,"reason":str(exc)})
        return status(scope,"rejected_pair")
    finally:
        await client.close()
    if row["wrong_pair"] or receipt["receipt"] not in str(result.output):
        raise ValueError("invalid resumed result")
    with db() as c:
        log(c,scope,"resumed",{"sdk_run":result.run_id,"conversation":result.conversation_id,"call":call,
                               "messages":json.loads(result.all_messages_json())})
    http(scope,"deliver",{"op":row["op"],"call":call,"receipt":receipt["receipt"]})
    return status(scope,"delivered")


@activity.defn(name="round_step")
async def round_step(scope: str) -> str:
    info = activity.info()
    with db() as c:
        log(c,scope,"attempt",{"attempt":info.attempt,"pid":os.getpid(),"build":os.environ["BUILD_MODULE"],"release_hash":hashlib.sha256(Path(RELEASE.__file__).read_bytes()).hexdigest(),
                               "wf":info.workflow_id,"run":info.workflow_run_id,"activity":info.activity_id})
    if not read(scope)["op"]:
        await checkpoint_first(scope)
    return await resume(scope)


@activity.defn
async def late_notice(scope: str) -> str:
    return await resume(scope,notice=True)


async def main():
    client = await Client.connect("temporal:7233",namespace=os.environ["NAMESPACE"])
    worker = Worker(client,task_queue="product-lab",workflows=[Round,Notice],activities=[round_step,late_notice])
    await worker.run()



if __name__=="__main__":
    asyncio.run(main())
