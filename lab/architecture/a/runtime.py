import json, os, uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict
import psycopg
from langgraph.graph import END, START, StateGraph
from mingjing.artifacts import BlobStore
from mingjing.catalog import Catalog
from mingjing.contracts import Action, Capability, Kind, Result
from mingjing.db import Database
from mingjing.service import Service
from shared_input import Output, schema, tool_descriptions
from ports import barrier, model_http, sink

def db(): return psycopg.connect(os.environ["LAB_APP_DSN"])
def setup():
    with db() as c:
        c.execute("""create table descriptors(name text primary key,spec jsonb);
            create table rights(scope text,action text,allowed boolean,primary key(scope,action));
            create table products(scope text primary key,state text,cache text);
            create table operations(scope text primary key,state text,settles int default 0);
            create table pools(scope text primary key,available int default 5,spent int default 0,closed boolean default false);
            create table holds(scope text,child text,units int,paid int,primary key(scope,child))""")
    owner=Database(os.environ["MINGJING_MIGRATION_DSN"])
    for who,key in (("admin","LAB_ADMIN_TOKEN"),("user","LAB_TOKEN")):
        owner.add_identity("lab",who,os.environ[key],datetime.now(UTC)+timedelta(hours=2),administrator=who=="admin")

def capability(spec):
    def handle(data, context, notes):
        return Result(sink(context.resource,"tool",{"name":spec["name"],"args":data.model_dump()}))
    return Capability(spec["name"],1,Kind.DIRECT,schema(spec),Output,handler=handle)
def entries():
    with db() as c: return [r[0] for r in c.execute("select spec from descriptors order by name")]
def services():
    database=Database(os.environ["MINGJING_DB_DSN"])
    cat=Catalog(database,"dev",[capability(s) for s in entries()])
    return cat,Service(database,cat,BlobStore(Path("/tmp/lab-a-blobs")))
def install(spec,published):
    from psycopg.types.json import Jsonb
    with db() as c:c.execute("insert into descriptors values(%s,%s) on conflict do nothing",(spec["name"],Jsonb(spec)))
    cat,_=services()
    for stage in (["register","validate","publish"] if published else ["register"]):
        cat.transition(os.environ["LAB_ADMIN_TOKEN"],spec["name"],1,stage)
def allow_tool(case,name,yes=True):
    cat,_=services()
    for action in (Action.EXECUTE,Action.READ):
        cat.grant(os.environ["LAB_ADMIN_TOKEN"],"user",name,1,case,action,yes)
def tool(case,name,args,token):
    _,service=services()
    task=service.submit(token,name,1,case,args,uuid.uuid4().hex)
    key=uuid.UUID(task["task_id"])
    service.execute(key)
    receipt=service.system_view(key)["receipt"]
    if receipt["state"]!="succeeded":raise PermissionError(receipt["state"])
    return receipt["value"]

class Turn(TypedDict):
    messages:list
    decisions:int

def agent(case,cmd):
    specs={s["name"]:s for s in entries()}
    tools=tool_descriptions([specs[n] for n in cmd["names"]])
    def decide(state):
        msg=model_http(case,cmd["backend"],state["messages"],tools)
        return {"messages":state["messages"]+[msg],"decisions":state["decisions"]+1}
    def dispatch(state):
        msgs=list(state["messages"])
        for call in msgs[-1]["tool_calls"]:
            f=call["function"]
            if f["name"] not in cmd["names"]:raise ValueError("outside offered tools")
            data=tool(case,f["name"],json.loads(f["arguments"]),os.environ["LAB_TOKEN"])
            msgs.append({"role":"tool","tool_call_id":call["id"],"content":json.dumps(data)})
        return {"messages":msgs}
    graph=StateGraph(Turn)
    graph.add_node("model",decide);graph.add_node("tools",dispatch)
    graph.add_edge(START,"model")
    graph.add_conditional_edges("model",lambda s:"tools" if s["messages"][-1].get("tool_calls") and s["decisions"]<6 else END)
    graph.add_edge("tools","model")
    result=graph.compile().invoke({"messages":[{"role":"user","content":cmd["prompt"]}],"decisions":0})
    return {"turns":result["decisions"],"finished":not bool(result["messages"][-1].get("tool_calls"))}

def prepare(case):
    with db() as c:
        c.execute("insert into products values(%s,'active',null)",(case,))
        c.execute("insert into pools(scope) values(%s)",(case,))
        for name in ("read","model","tool_out","commit","deliver"):
            c.execute("insert into rights values(%s,%s,true)",(case,name))
def revoke(case,action):
    with db() as c:c.execute("update rights set allowed=false where scope=%s and action=%s",(case,action))
def stage(case,action):
    barrier(case,action)
    with db() as c:
        right=c.execute("select allowed from rights where scope=%s and action=%s for share",(case,action)).fetchone()
        if not right or not right[0]:
            c.execute("update products set state='denied' where scope=%s",(case,));return "denied"
        cache=c.execute("select cache from products where scope=%s",(case,)).fetchone()[0]
        if action=="model":
            model_http(case,"controlled",[{"role":"user","content":cache or ""}],[])
            return "ok"
        if action=="tool_out":
            tool(case,"item_state",{"key":cache or ""},os.environ["LAB_TOKEN"])
            return "ok"
        result=sink(case,action,{"marker":cache})
        if action=="read":c.execute("update products set cache=%s where scope=%s",(result["value"],case))
        return "ok"
def quality(case,data):
    valid=data["validator"] and data["version"]=="v1" and set(data["items"])>={"left","right"}
    status="review"
    if valid and stage(case,"commit")=="ok" and stage(case,"deliver")=="ok":status="succeeded"
    with db() as c:c.execute("update products set state=%s where scope=%s",(status,case))
    return status
def supplier(case):
    with db() as c:
        first=c.execute("insert into operations(scope,state) values(%s,'sending') on conflict do nothing returning scope",(case,)).fetchone()
    reply=sink(case,"supplier_send" if first else "lookup",{"op":case})
    if first:barrier(case,"after_effect")
    return callback(case,reply["known"])
def callback(case,known):
    with db() as c:
        current=c.execute("select state from operations where scope=%s for update",(case,)).fetchone()[0]
        if known:
            c.execute("update operations set state='confirmed',settles=1 where scope=%s",(case,))
        elif current!="confirmed":c.execute("update operations set state='unknown' where scope=%s",(case,))
        alive=c.execute("select state from products where scope=%s for update",(case,)).fetchone()[0]!="cancelled"
        if known and alive and current!="confirmed":sink(case,"downstream")
    return "confirmed" if known else "unknown"
def cancel(case):
    with db() as c:
        c.execute("update pools set closed=true where scope=%s",(case,))
        c.execute("update products set state='cancelled' where scope=%s",(case,))
def child(case,name):
    with db() as c:
        pool=c.execute("select available,closed from pools where scope=%s for update",(case,)).fetchone()
        old=c.execute("select paid from holds where scope=%s and child=%s",(case,name)).fetchone()
        if old and old[0] is not None:return "settled"
        if not old and (pool[1] or pool[0]<3):
            sink(case,"budget_denied",{"child":name});return "blocked"
        if not old:
            c.execute("update pools set available=available-3 where scope=%s",(case,))
            c.execute("insert into holds values(%s,%s,3,null)",(case,name))
    barrier(case,"reserved")
    if old:
        response=sink(case,"charge_lookup",{"op":name})
        if not response["known"]:return "unknown"
    else:
        with db() as c:
            closed=c.execute("select closed from pools where scope=%s for share",(case,)).fetchone()[0]
            if closed:return "held"
            sink(case,"charge",{"op":name})
        barrier(case,"charged")
    with db() as c:
        c.execute("select scope from pools where scope=%s for update",(case,))
        changed=c.execute("update holds set paid=2,units=0 where scope=%s and child=%s and paid is null returning child",(case,name)).fetchone()
        if changed:c.execute("update pools set available=available+1,spent=spent+2 where scope=%s",(case,))
    return "settled"
def state(case):
    with db() as c:
        product=c.execute("select state from products where scope=%s",(case,)).fetchone()[0]
        op=c.execute("select state,settles from operations where scope=%s",(case,)).fetchone()
        spent,held=c.execute("select spent,5-available-spent from pools where scope=%s",(case,)).fetchone()
        return dict(product=product,op=op,spent=spent,held=held)

