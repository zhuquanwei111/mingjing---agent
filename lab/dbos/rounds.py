"""Independent DBOS workflow and product protocol for one interrupted tool turn."""
import asyncio
import json
import os
import signal
import sys
import time
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
from dbos import DBOS, SetWorkflowID
from openai import AsyncOpenAI
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic_ai import Agent, CallDeferred, DeferredToolRequests, DeferredToolResults, ModelMessagesTypeAdapter, Tool, UsageLimits
from pydantic_ai.exceptions import UserError
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

SCHEMA = """
CREATE TABLE task(scope text PRIMARY KEY, name text NOT NULL, marker text NOT NULL, version int,
 active bool NOT NULL DEFAULT true, op text UNIQUE, call text, history jsonb, first_run text, conversation text,
 sent bool DEFAULT false, held int DEFAULT 0, spent int DEFAULT 0, receipt text, state text DEFAULT 'new',
 resumed_run text, resumed_conversation text, model_slots int NOT NULL DEFAULT 0);
CREATE TABLE trace(seq bigserial PRIMARY KEY,scope text,kind text,pid int,wf text,step int,detail jsonb);
"""
ROOT = 'http://127.0.0.1:8080'

def product():
    return psycopg.connect(os.environ['PRODUCT_DSN'], row_factory=dict_row)

def task(scope):
    with product() as c:
        return c.execute("SELECT * FROM task WHERE scope=%s",(scope,)).fetchone()

def trace(c, scope, kind, detail=None):
    c.execute("INSERT INTO trace(scope,kind,pid,wf,step,detail) VALUES(%s,%s,%s,%s,%s,%s)",
              (scope,kind,os.getpid(),DBOS.workflow_id,DBOS.step_id,Jsonb(detail or {})))

def http(scope, endpoint, data=None):
    req = Request(f"{ROOT}/{scope}/{endpoint}", headers={'Content-Type':'application/json'},
                  data=json.dumps(data).encode() if data is not None else None)
    with urlopen(req, timeout=5) as res:
        return res.status, json.load(res)

async def sdk(row, *, second=None):
    scope = row['scope']
    def defer(**kwargs):
        raise CallDeferred
    tool = Tool.from_schema(defer, name=row['name'], description='Verify a reference asynchronously',
                            json_schema={'type':'object','properties':{'ref':{'type':'string'}},
                                         'required':['ref'],'additionalProperties':False}, takes_ctx=False)
    class BudgetedModel(OpenAIChatModel):
        async def request(self,*args,**kwargs):
            with product() as c:
                if not c.execute("""UPDATE task SET model_slots=model_slots+1 WHERE scope=%s
                        AND active AND model_slots<2 RETURNING scope""",(scope,)).fetchone():
                    raise PermissionError('model dispatch closed')
            return await super().request(*args,**kwargs)
    async with AsyncOpenAI(base_url=f"{ROOT}/{scope}/v1", api_key='local-test-only',max_retries=0) as client:
        model = BudgetedModel('fixture',provider=OpenAIProvider(openai_client=client))
        agent = Agent(model,tools=[tool],output_type=[str,DeferredToolRequests])
        limits = UsageLimits(request_limit=1)
        if second is None:
            return await agent.run("Verify the registered item " + row['marker'], usage_limits=limits)
        messages = ModelMessagesTypeAdapter.validate_python(row['history']['messages'])
        return await agent.run(message_history=messages,deferred_tool_results=DeferredToolResults(calls=second),usage_limits=limits)

@DBOS.step()
def prepare(scope):
    row = task(scope)
    if row['op']:
        return
    result = asyncio.run(sdk(row))
    assert isinstance(result.output, DeferredToolRequests)
    call, = result.output.calls
    assert call.tool_name == row['name'] and call.args_as_dict() == {'ref':row['marker']}
    version=int(os.environ['WRITER_FORMAT'])
    messages=json.loads(result.all_messages_json())
    operation=str(uuid4())
    payload=(['v0',messages] if version==0 else
             {'version':version,'operation':operation,'call':call.tool_call_id,'messages':messages})
    with product() as c:
        trace(c,scope,'write_checkpoint',{'written_format':version,'worker_release':os.environ['GENERATION']})
        c.execute("""UPDATE task SET op=%s,call=%s,history=%s,version=%s,first_run=%s,conversation=%s,held=3,
                  state='reserved' WHERE scope=%s AND active AND op IS NULL""",
                  (operation,call.tool_call_id,Jsonb(payload),version,
                   str(result.run_id),str(result.conversation_id),scope))

@DBOS.step()
def send_job(scope, naked):
    # Do not repeat an unknown first handoff. Naked control deliberately ignores the product intent.
    with product() as c:
        trace(c,scope,'send-step')
        row = c.execute("SELECT * FROM task WHERE scope=%s FOR UPDATE",(scope,)).fetchone()
        if not row['active'] or (row['sent'] and not naked):
            return
        c.execute("UPDATE task SET sent=true,state='issued' WHERE scope=%s",(scope,))
    code, ack = http(scope,'submit',{'op':row['op'],'call':row['call'],'name':row['name'],'input':{'ref':row['marker']}})
    assert code == 202 and ack == {'accepted':True}
    with product() as c:
        trace(c,scope,'accepted')
    if os.environ['GENERATION'] == 'one':
        while True:
            time.sleep(1)

@DBOS.step()
def reconcile(scope, settlement_only=False):
    row = task(scope)
    _, answer = http(scope,'lookup/'+row['op'])
    if not answer['known']:
        with product() as c:
            c.execute("UPDATE task SET state='pending' WHERE scope=%s AND active",(scope,))
        return 'pending'
    if (answer['op'],answer['call'],answer['units']) != (row['op'],row['call'],1):
        raise ValueError('unbound receipt')
    with product() as c:
        locked = c.execute("SELECT * FROM task WHERE scope=%s FOR UPDATE",(scope,)).fetchone()
        assert locked['receipt'] in (None,answer['receipt'])
        c.execute("UPDATE task SET spent=1,held=0,receipt=%s WHERE scope=%s",(answer['receipt'],scope))
        trace(c,scope,'settled',{'new': locked['receipt'] is None})
        active=locked['active']
    if settlement_only or not active:
        return 'settled'
    accepted=[int(v) for v in os.environ['READER_FORMATS'].split(',')]
    checkpoint=row['history']
    with product() as c:
        trace(c,scope,'read_checkpoint',{'supported':accepted,'seen':row['version'],'worker_release':os.environ['GENERATION']})
    if (row['version'] not in accepted or not isinstance(checkpoint,dict) or
            (checkpoint.get('version'),checkpoint.get('operation'),checkpoint.get('call')) !=
            (row['version'],row['op'],row['call'])):
        state='quarantine'
    else:
        call_id = 'incorrect-'+row['call'] if scope=='wrong' else row['call']
        try:
            result = asyncio.run(sdk(row,second={call_id:answer['receipt']}))
        except UserError as exc:
            assert scope=='wrong' and 'all deferred tool calls' in str(exc) and call_id in str(exc) and row['call'] in str(exc)
            state='rejected'
        else:
            assert scope!='wrong' and answer['receipt'] in result.output
            with product() as c:
                current = c.execute("SELECT active FROM task WHERE scope=%s FOR UPDATE",(scope,)).fetchone()
                if not current['active']:
                    return 'settled'
                reply = http(scope,'deliver',{'op':row['op'],'call':call_id,'receipt':answer['receipt']})
                assert reply==(200,{'received':True})
                c.execute("UPDATE task SET resumed_run=%s,resumed_conversation=%s WHERE scope=%s",
                          (str(result.run_id),str(result.conversation_id),scope))
            state='delivered'
    with product() as c:
        c.execute("UPDATE task SET state=%s WHERE scope=%s",(state,scope))
    return state

@DBOS.workflow()
def controlled(scope):
    prepare(scope)
    send_job(scope, False)
    state = reconcile(scope)
    while state == 'pending':
        DBOS.recv('receipt', timeout_seconds=300)
        state = reconcile(scope)
    return state

@DBOS.workflow()
def naked_control(scope, marker):
    prepare(scope)
    send_job(scope, True)
    return marker

@DBOS.workflow()
def late_receipt(scope):
    return reconcile(scope, True)

def main():
    action,scope = sys.argv[1:3]
    executor=('receipt-' if action=='late' else 'round-')+scope
    DBOS(config={'name':'round-lab','system_database_url':os.environ['ENGINE_DSN'],
                 'executor_id':executor,'application_version':'fixed-lab-v1','enable_otlp':False})
    DBOS.launch()
    if action == 'start':
        with SetWorkflowID('run-'+scope):
            if scope=='naked':
                DBOS.start_workflow(naked_control,scope,'NAKED_INPUT_MARK_'+scope)
            else:
                DBOS.start_workflow(controlled,scope)
    elif action == 'late':
        for i in range(2):
            with SetWorkflowID('notice-'+scope+'-'+str(i)):
                assert late_receipt(scope)=='settled'
    elif action != 'recover':
        raise ValueError(action)
    print('WORKER_READY',action,scope,os.getpid(),flush=True)
    signal.pause()

if __name__=='__main__':
    main()
