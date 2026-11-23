import json, os, hmac
import psycopg
from psycopg.types.json import Jsonb
from pydantic_ai import Agent, Tool, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from ports import FIXTURE, barrier, sink, model_http
from shared_input import Output, schema

def connect(): return psycopg.connect(os.environ["LAB_APP_DSN"])
def setup():
    with connect() as conn:
        conn.execute("""create table packages(id text primary key, contract jsonb, live boolean);
          create table licenses(target text,package text,primary key(target,package));
          create table jobs(id text primary key,denied text[] default '{}',status text default 'active',memo text);
          create table dispatch(id text primary key,ack boolean default false);
          create table budget(id text,worker text,allocated integer,consumed integer,primary key(id,worker))""")
def install(spec,published):
    with connect() as conn:
        conn.execute("insert into packages values(%s,%s,%s)",(spec["name"],Jsonb(spec),published))
def allow_tool(case,name,yes=True):
    with connect() as conn:
        if yes:conn.execute("insert into licenses values(%s,%s) on conflict do nothing",(case,name))
        else:conn.execute("delete from licenses where target=%s and package=%s",(case,name))
def tool(case,name,args,token):
    if not hmac.compare_digest(token,os.environ["LAB_TOKEN"]):raise PermissionError("identity")
    with connect() as conn:
        found=conn.execute("""select contract from packages join licenses on package=id
                              where id=%s and target=%s and live for share""",(name,case)).fetchone()
        if found is None:raise PermissionError("unpublished or unauthorized")
        validated=schema(found[0]).model_validate(args)
        result=sink(case,"tool",{"name":name,"args":validated.model_dump()})
        return Output.model_validate(result).model_dump()
def agent(case,cmd):
    with connect() as conn:all_specs=dict(conn.execute("select id,contract from packages"))
    def adapt(spec):
        def invoke(**kwargs):
            return tool(case,spec["name"],kwargs,os.environ["LAB_TOKEN"])
        return Tool.from_schema(invoke,name=spec["name"],description=spec["description"],
                                json_schema=schema(spec).model_json_schema(),takes_ctx=False)
    provider=OpenAIProvider(base_url=f"{FIXTURE}/{case}/{cmd['backend']}/v1",api_key="fixture-only")
    model=OpenAIChatModel("qwen2.5:1.5b",provider=provider)
    agent_instance=Agent(model,tools=[adapt(all_specs[n]) for n in cmd["names"]],model_settings={"temperature":0,"max_tokens":160})
    result=agent_instance.run_sync(cmd["prompt"],usage_limits=UsageLimits(request_limit=6))
    return {"turns":result.usage.requests,"finished":True}

def prepare(case):
    with connect() as conn:conn.execute("insert into jobs(id) values(%s)",(case,))
def revoke(case,action):
    with connect() as conn:conn.execute("update jobs set denied=array_append(denied,%s) where id=%s",(action,case))
def stage(case,action):
    barrier(case,action)
    with connect() as conn:
        refusals,memo=conn.execute("select denied,memo from jobs where id=%s for update",(case,)).fetchone()
        if action in refusals:
            conn.execute("update jobs set status='denied' where id=%s",(case,));return "denied"
        if action=="model":
            model_http(case,"controlled",[{"role":"user","content":memo or ""}],[])
        elif action=="tool_out":
            tool(case,"item_state",{"key":memo or ""},os.environ["LAB_TOKEN"])
        else:
            outcome=sink(case,action,{"marker":memo})
            if action=="read":conn.execute("update jobs set memo=%s where id=%s",(outcome["value"],case))
        return "ok"
def quality(case,data):
    required={"left","right"}
    reasons=required.difference(data["items"])
    ok=data["validator"] and data["version"]=="v1" and not reasons
    if ok:
        for action in ("commit","deliver"):
            if stage(case,action)!="ok":return "denied"
    outcome="succeeded" if ok else "review"
    with connect() as conn:conn.execute("update jobs set status=%s where id=%s",(outcome,case))
    return outcome
def supplier(case):
    with connect() as conn:
        inserted=conn.execute("insert into dispatch(id) values(%s) on conflict do nothing returning id",(case,)).fetchone()
    if inserted:
        response=sink(case,"supplier_send",{"op":case})
        barrier(case,"after_effect")
    else:response=sink(case,"lookup",{"op":case})
    return callback(case,response["known"])
def callback(case,known):
    with connect() as conn:
        job=conn.execute("select status from jobs where id=%s for update",(case,)).fetchone()[0]
        if known:
            fresh=conn.execute("update dispatch set ack=true where id=%s and not ack returning id",(case,)).fetchone()
            if fresh and job!="cancelled":sink(case,"downstream")
    return "confirmed" if known else "unknown"
def cancel(case):
    with connect() as conn:conn.execute("update jobs set status='cancelled' where id=%s",(case,))
def child(case,name):
    with connect() as conn:
        job=conn.execute("select status from jobs where id=%s for update",(case,)).fetchone()[0]
        current=conn.execute("select allocated,consumed from budget where id=%s and worker=%s",(case,name)).fetchone()
        if current and current[1] is not None:return "settled"
        if current is None:
            total=conn.execute("select coalesce(sum(coalesce(consumed,allocated)),0) from budget where id=%s",(case,)).fetchone()[0]
            if job=="cancelled" or total+3>5:
                sink(case,"budget_denied",{"child":name});return "blocked"
            conn.execute("insert into budget values(%s,%s,3,null)",(case,name))
    barrier(case,"reserved")
    if current:
        if not sink(case,"charge_lookup",{"op":name})["known"]:return "unknown"
    else:
        with connect() as conn:
            job=conn.execute("select status from jobs where id=%s for share",(case,)).fetchone()[0]
            if job=="cancelled":return "held"
            sink(case,"charge",{"op":name})
        barrier(case,"charged")
    with connect() as conn:
        conn.execute("update budget set consumed=2 where id=%s and worker=%s and consumed is null",(case,name))
    return "settled"
def state(case):
    with connect() as conn:
        status=conn.execute("select status from jobs where id=%s",(case,)).fetchone()[0]
        ack=conn.execute("select ack from dispatch where id=%s",(case,)).fetchone()
        used,held=conn.execute("select coalesce(sum(consumed),0),coalesce(sum(allocated) filter(where consumed is null),0) from budget where id=%s",(case,)).fetchone()
        return dict(product=status,op=(("confirmed",1) if ack[0] else ("unknown",0)) if ack else None,spent=int(used),held=int(held))

