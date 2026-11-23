"""Reference-only Temporal coordination with a product-owned claim at the SDK model boundary."""
import asyncio
import json
import os
import uuid
from functools import partial
from urllib.request import Request, urlopen

import openai
from openai import AsyncOpenAI
from psycopg.types.json import Jsonb
from pydantic_ai import (Agent, CallDeferred, DeferredToolRequests, DeferredToolResults,
                         ModelMessagesTypeAdapter, Tool, UsageLimits)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

import worker as frozen
from adapters import adapter_for
from gate_flow import DuplicateEntry, GateRound

SCHEMA = """
ALTER TABLE task ADD COLUMN model_operation text UNIQUE NOT NULL;
CREATE TABLE model_round(
 operation text REFERENCES task(model_operation), round_no int CHECK(round_no IN (1,2)),
 dispatch text UNIQUE NOT NULL, phase text NOT NULL, held int NOT NULL, spent int NOT NULL,
 PRIMARY KEY(operation,round_no),
 CHECK ((phase='confirmed' AND held=0 AND spent=1) OR
        (phase IN ('claimed','unknown') AND held=1 AND spent=0))
);
ALTER TABLE task ADD COLUMN delivery_claim text UNIQUE;
"""


class Claimed(Exception):
    pass


class Revoked(Exception):
    pass


def event(scope, kind, **detail):
    with frozen.db() as c:
        frozen.log(c,scope,kind,detail)


def attempt(scope, kind, **extra):
    info = activity.info()
    event(scope,kind,wf=info.workflow_id,run=info.workflow_run_id,activity=info.activity_id,
          attempt=info.attempt,pid=os.getpid(),queue=info.task_queue,**extra)


def transport(scope, path, data=None):
    req = Request(f"http://provider:8080/{scope}/{path}",
                  data=None if data is None else json.dumps(data).encode(),
                  headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=55) as response:
        return json.load(response)


def reserve(row, number, dispatch):
    with frozen.db() as c:
        task = c.execute("SELECT * FROM task WHERE scope=%s FOR UPDATE",(row["scope"],)).fetchone()
        if not task["active"]:
            return "revoked"
        inserted = c.execute("""INSERT INTO model_round(operation,round_no,dispatch,phase,held,spent)
                VALUES(%s,%s,%s,'claimed',1,0) ON CONFLICT(operation,round_no) DO NOTHING
                RETURNING dispatch""",(task["model_operation"],number,dispatch)).fetchone()
        if not inserted:
            prior = c.execute("SELECT * FROM model_round WHERE operation=%s AND round_no=%s",
                              (task["model_operation"],number)).fetchone()
            frozen.log(c,row["scope"],"duplicate_claim",dict(prior,pid=os.getpid()))
            return "claimed"
        updated = c.execute("""UPDATE task SET model_slots=model_slots+1
            WHERE scope=%s AND model_slots<2 RETURNING model_slots""",(row["scope"],)).fetchone()
        if not updated:
            raise RuntimeError("product model budget exhausted")
        frozen.log(c,row["scope"],"model_claim",{"operation":task["model_operation"],"round":number,
                   "dispatch":dispatch,"held":1,"spent":0,"slots":updated["model_slots"],"pid":os.getpid()})
        return "ok"


def governed_agent(row, number):
    def defer(**kwargs):
        raise CallDeferred
    desc = row["descriptor"]
    tool = Tool.from_schema(defer,name=desc["name"],description=desc["description"],
                            json_schema=desc["input_schema"],takes_ctx=False)
    dispatch = str(uuid.uuid4())
    client = AsyncOpenAI(base_url=f"http://provider:8080/{row['scope']}/v1",api_key="fixture",max_retries=0,
                         default_headers={"X-Gate-Operation":row["model_operation"],"X-Gate-Round":str(number),
                                          "X-Gate-Dispatch":dispatch})

    class ClaimedModel(OpenAIChatModel):
        async def request(self,*args,**kwargs):
            decision = reserve(row,number,dispatch)
            if decision == "claimed":
                raise Claimed
            if decision == "revoked":
                raise Revoked
            return await super().request(*args,**kwargs)

    model = ClaimedModel("fixture",provider=OpenAIProvider(openai_client=client))
    return Agent(model,tools=[tool],output_type=[str,DeferredToolRequests]),client,dispatch


def confirm(c, row, number, dispatch):
    done = c.execute("""UPDATE model_round SET phase='confirmed',spent=1,held=0
      WHERE operation=%s AND round_no=%s AND dispatch=%s AND phase='claimed' RETURNING dispatch""",
                     (row["model_operation"],number,dispatch)).fetchone()
    if not done:
        raise RuntimeError("model confirmation has no owning claim")
    frozen.log(c,row["scope"],"model_confirm",{"dispatch":dispatch,"round":number,"held":0,"spent":1})


async def call_first(row, duplicate=False):
    scope = row["scope"]
    if scope == "legacy":
        agent,client = frozen.agent_for(row)
        dispatch = None
    else:
        agent,client,dispatch = governed_agent(row,1)
    try:
        result = await agent.run("Request the registered asynchronous operation on " + row["marker"],
                                 usage_limits=UsageLimits(request_limit=1))
    except Claimed:
        if duplicate:
            return "suppressed"
        with frozen.db() as c:
            unknown = c.execute("""UPDATE model_round SET phase='unknown'
                WHERE operation=%s AND round_no=1 AND phase IN ('claimed','unknown') RETURNING dispatch""",
                                (row["model_operation"],)).fetchone()
            if not unknown:
                raise RuntimeError("unexpected model reconciliation state")
            c.execute("UPDATE task SET state='model_unknown' WHERE scope=%s",(scope,))
        return "model_unknown"
    except Exception as exc:
        # The negative control's second charge has already committed; its HTTP reply is also dropped.
        cause = exc
        while cause and not isinstance(cause,openai.APIConnectionError):
            cause = cause.__cause__ or cause.__context__
        if scope != "legacy" or cause is None:
            raise
        event(scope,"transport_loss",exception=type(cause).__name__)
        return frozen.status(scope,"legacy_unknown")
    finally:
        await client.close()
    if duplicate or not isinstance(result.output,DeferredToolRequests):
        raise RuntimeError("initial model response missing deferred request")
    call, = result.output.calls
    assert call.tool_name == row["descriptor"]["name"]
    op = str(uuid.uuid4())
    msg = frozen.RELEASE.encode(1,json.loads(result.all_messages_json()),op,call.tool_call_id)
    with frozen.db() as c:
        confirm(c,row,1,dispatch)
        updated = c.execute("""UPDATE task SET op=%s,call=%s,msg=%s,checkpoint_version=1,held=3,
             state='dispatch_intent' WHERE scope=%s AND active AND op IS NULL RETURNING op""",
                            (op,call.tool_call_id,Jsonb(msg),scope)).fetchone()
        if not updated:
            raise RuntimeError("initial tool intent conflict")
        frozen.log(c,scope,"checkpoint",{"op":op,"call":call.tool_call_id,"sdk_run":result.run_id,
                                        "conversation":result.conversation_id})
    if not frozen.read(scope)["active"]:
        raise Revoked
    adapter = adapter_for(row["descriptor"])
    ack = await asyncio.to_thread(adapter.dispatch,partial(transport,scope),op,call)
    assert ack == {"accepted":True}
    event(scope,"accepted",op=op)
    return frozen.status(scope,"accepted")


@activity.defn
async def gate_initial(scope: str) -> str:
    attempt(scope,"attempt")
    async def heartbeats():
        while True:
            activity.heartbeat()
            await asyncio.sleep(.7)
    beat = asyncio.create_task(heartbeats())
    try:
        return await call_first(frozen.read(scope))
    finally:
        beat.cancel()
        await asyncio.gather(beat,return_exceptions=True)


@activity.defn
async def gate_duplicate(scope: str) -> str:
    attempt(scope,"duplicate_entry")
    return await call_first(frozen.read(scope),duplicate=True)


@activity.defn
async def gate_lookup(scope: str) -> str:
    return await reconcile(scope)


@activity.defn
async def gate_notice(scope: str, notification: str) -> str:
    attempt(scope,"notice",notice=notification)
    return await reconcile(scope)


async def reconcile(scope):
    row = frozen.read(scope)
    receipt = await asyncio.to_thread(adapter_for(row["descriptor"]).lookup,partial(transport,scope),row["op"])
    if not receipt["known"]:
        with frozen.db() as c:
            c.execute("UPDATE task SET state='tool_unknown' WHERE scope=%s AND state IN ('accepted','tool_unknown')",
                      (scope,))
        return "tool_unknown"
    frozen.settle(scope,receipt)
    if not frozen.read(scope)["active"]:
        return frozen.status(scope,"revoked_settled")
    history = frozen.RELEASE.decode(row)
    if history is None:
        raise ValueError("unsupported checkpoint")
    messages = ModelMessagesTypeAdapter.validate_python(history)
    agent,client,dispatch = governed_agent(row,2)
    try:
        result = await agent.run(message_history=messages,
                deferred_tool_results=DeferredToolResults(calls={row["call"]:receipt["receipt"]}),
                usage_limits=UsageLimits(request_limit=1))
    except Claimed:
        return "suppressed"
    except Revoked:
        return frozen.status(scope,"revoked_settled")
    finally:
        await client.close()
    if receipt["receipt"] not in str(result.output):
        raise ValueError("invalid resumed result")
    with frozen.db() as c:
        confirm(c,row,2,dispatch)
        frozen.log(c,scope,"resumed",{"sdk_run":result.run_id,"conversation":result.conversation_id,
                                     "call":row["call"],"messages":json.loads(result.all_messages_json())})
        allowed = c.execute("""UPDATE task SET delivery_claim=%s WHERE scope=%s AND active
            AND delivery_claim IS NULL RETURNING delivery_claim""",(str(uuid.uuid4()),scope)).fetchone()
        if not allowed:
            return "revoked_settled"
    if not frozen.read(scope)["active"]:
        return frozen.status(scope,"revoked_settled")
    ack = await asyncio.to_thread(transport,scope,"deliver",{"op":row["op"],"call":row["call"],
                    "receipt":receipt["receipt"],"delivery":allowed["delivery_claim"],"output":result.output})
    assert ack == {"received":True}
    return frozen.status(scope,"delivered")


async def main():
    client = await Client.connect("temporal:7233",namespace=os.environ["NAMESPACE"])
    await Worker(client,task_queue=os.environ["GATE_QUEUE"],workflows=[GateRound,DuplicateEntry],
                 activities=[gate_initial,gate_duplicate,gate_lookup,gate_notice]).run()


if __name__ == "__main__":
    asyncio.run(main())
