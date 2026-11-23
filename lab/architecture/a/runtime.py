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
            create table agent_evidence(ref uuid primary key,scope text,name text,observed text);
            create table quality_decisions(scope text primary key, reason text,rule text);
            create table operations(scope text primary key,state text,settles int default 0);
            create table pools(scope text primary key,available int default 5,spent int default 0,closed boolean default false, check(available>=0 and spent>=0 and available+spent<=5));
            create table snapshots(scope text,spent int,held int);
            create function budget_snapshot() returns trigger language plpgsql as $$ begin
            insert into snapshots values(new.scope,new.spent,5-new.available-new.spent);return new;end;$$;
            create trigger capture after insert or update on pools for each row execute function budget_snapshot();
            create table holds(scope text,child text,units int,paid int,primary key(scope,child))""")
    owner = Database(os.environ["MINGJING_MIGRATION_DSN"])
    owner.add_identity("outside", "outsider",
                       os.environ["LAB_OUTSIDER"], datetime.now(UTC) + timedelta(hours=2))
    for who, key in (("admin", "LAB_ADMIN_TOKEN"), ("user", "LAB_TOKEN")):
        owner.add_identity("lab", who, os.environ[key], datetime.now(
            UTC) + timedelta(hours=2), administrator=who == "admin")


def authorized_io(case, action, call):
    barrier(case, "agent_" + action)
    with db() as con:
        row = con.execute("select allowed from rights where scope=%s and action=%s for share",
                          (case, action)).fetchone()
        if not row or not row[0]:
            raise PermissionError(action)
        return call()


def capability(spec):
    def handle(data, context, notes):
        return Result(authorized_io(context.resource, "tool_out", lambda: sink(context.resource, "tool", {"name": spec["name"], "args": data.model_dump()})))
    return Capability(spec["name"], 1, Kind.DIRECT, schema(spec), Output, handler=handle)


def entries():
    with db() as c:
        return [r[0] for r in c.execute("select spec from descriptors order by name")]


def services():
    database = Database(os.environ["MINGJING_DB_DSN"])
    cat = Catalog(database, "dev", [capability(s) for s in entries()])
    return cat, Service(database, cat, BlobStore(Path("/tmp/lab-a-blobs")))


def install(spec, published):
    from psycopg.types.json import Jsonb
    with db() as c:
        c.execute("insert into descriptors values(%s,%s) on conflict do nothing", (spec["name"], Jsonb(spec)))
    cat, _ = services()
    for stage in (["register", "validate", "publish"] if published else ["register"]):
        cat.transition(os.environ["LAB_ADMIN_TOKEN"], spec["name"], 1, stage)


def allow_tool(case, name, yes=True):
    cat, _ = services()
    for action in (Action.EXECUTE, Action.READ):
        cat.grant(os.environ["LAB_ADMIN_TOKEN"], "user", name, 1, case, action, yes)


def tool(case, name, args, token):
    _, service = services()
    task = service.submit(token, name, 1, case, args, uuid.uuid4().hex)
    key = uuid.UUID(task["task_id"])
    service.execute(key)
    receipt = service.get(token, key)["receipt"]
    if receipt["state"] != "succeeded":
        raise PermissionError(receipt["state"])
    return receipt["value"]


class Turn(TypedDict):
    messages: list
    decisions: int


def agent(case, cmd):
    specs = {s["name"]: s for s in entries()}
    tools = tool_descriptions([specs[n] for n in cmd["names"]])

    evidence = {}

    def decide(state):
        msg = authorized_io(case, "model", lambda: model_http(case, cmd["backend"], state["messages"], tools))
        return {"messages": state["messages"] + [msg], "decisions": state["decisions"] + 1}

    def dispatch(state):
        msgs = list(state["messages"])
        for call in msgs[-1]["tool_calls"]:
            f = call["function"]
            if f["name"] not in cmd["names"]:
                raise ValueError("outside offered tools")
            data = tool(case, f["name"], json.loads(f["arguments"]), os.environ["LAB_TOKEN"])
            ref = uuid.uuid4()
            with db() as conn:
                conn.execute("insert into agent_evidence values(%s,%s,%s,%s)",
                             (ref, case, f["name"], data["value"]))
            rule = cmd["required"].get(f["name"])
            if rule is None or data["value"] == rule:
                evidence[f["name"]] = str(ref)
            msgs.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(data)})
        return {"messages": msgs}
    graph = StateGraph(Turn)
    graph.add_node("model", decide)
    graph.add_node("tools", dispatch)
    graph.add_edge(START, "model")
    graph.add_conditional_edges(
        "model", lambda s: "tools" if s["messages"][-1].get("tool_calls") and s["decisions"] < 6 else END)
    graph.add_edge("tools", "model")
    result = graph.compile().invoke({"messages": [{"role": "user", "content": cmd["prompt"]}], "decisions": 0})
    return {"turns": result["decisions"], "finished": not bool(result["messages"][-1].get("tool_calls")),
            "version": cmd["version"], "completed": sorted(evidence), "missing": sorted(cmd["required"].keys() - evidence.keys()),
            "evidence": evidence}


def prepare(case):
    with db() as c:
        c.execute("insert into products values(%s,'active',null)", (case,))
        c.execute("insert into pools(scope) values(%s)", (case,))
        for name in ("read", "model", "tool_out", "commit", "deliver"):
            c.execute("insert into rights values(%s,%s,true)", (case, name))


def revoke(case, action):
    with db() as c:
        c.execute("update rights set allowed=false where scope=%s and action=%s", (case, action))


def stage(case, action):
    barrier(case, action)
    with db() as c:
        right = c.execute("select allowed from rights where scope=%s and action=%s for share",
                          (case, action)).fetchone()
        if not right or not right[0]:
            c.execute("update products set state='denied' where scope=%s", (case,))
            return "denied"
        cache = c.execute("select cache from products where scope=%s", (case,)).fetchone()[0]
        if action == "model":
            model_http(case, "controlled", [{"role": "user", "content": cache or ""}], [])
            return "ok"
        if action == "tool_out":
            tool(case, "item_state", {"key": cache or ""}, os.environ["LAB_TOKEN"])
            return "ok"
        result = sink(case, action, {"marker": cache})
        if action == "read":
            c.execute("update products set cache=%s where scope=%s", (result["value"], case))
        return "ok"


def quality(case, options):
    credential = os.environ["LAB_TOKEN"]
    key = tool(case, "read_manifest", {"resource": "bundle"}, credential)["value"]
    evidence = tool(case, "item_state", {"key": key}, credential)
    data = json.loads(evidence["value"])
    from urllib.error import URLError
    try:
        policy = sink(case, "quality_policy")
    except URLError:
        policy = None
    data["validator"] = bool(policy)
    valid = data["validator"] and data["version"] == policy["version"] and set(
        data["items"]) >= set(policy["required"])
    reason = "unavailable" if not policy else (
        "version" if data["version"] != policy["version"] else ("missing" if not valid else "complete"))
    status = "review"
    if valid and stage(case, "commit") == "ok" and stage(case, "deliver") == "ok":
        status = "succeeded"
    with db() as c:
        c.execute("update products set state=%s where scope=%s", (status, case))
        c.execute("insert into quality_decisions values(%s,%s,'v1')", (case, reason))
    return status


def verdict(case):
    with db() as con:
        return con.execute("select reason,rule from quality_decisions where scope=%s", (case,)).fetchone()


def supplier(case):
    with db() as c:
        first = c.execute(
            "insert into operations(scope,state) values(%s,'sending') on conflict do nothing returning scope", (case,)).fetchone()
        if first:
            ok = c.execute(
                "update pools set available=available-3 where scope=%s and available>=3 and not closed returning scope", (case,)).fetchone()
            if not ok:
                raise RuntimeError("reservation denied")
    if first:
        barrier(case, "supplier_gate")
        with db() as con:
            allowed = con.execute(
                "select allowed from rights where scope=%s and action='commit' for share", (case,)).fetchone()
            product = con.execute("select state from products where scope=%s for share", (case,)).fetchone()
            if not allowed or not allowed[0] or product[0] == "cancelled":
                con.execute("update operations set state='denied' where scope=%s", (case,))
                con.execute("update pools set available=available+3 where scope=%s", (case,))
                return "denied"
            reply = sink(case, "supplier_send", {"op": case})
    else:
        reply = sink(case, "lookup", {"op": case})
    if first:
        barrier(case, "after_effect")
    return callback(case, reply["known"])


def callback(case, known):
    with db() as c:
        current = c.execute("select state from operations where scope=%s for update", (case,)).fetchone()[0]
        if known:
            if current != "confirmed":
                c.execute("update pools set spent=spent+2,available=available+1 where scope=%s", (case,))
            c.execute("update operations set state='confirmed',settles=1 where scope=%s", (case,))
        elif current != "confirmed":
            c.execute("update operations set state='unknown' where scope=%s", (case,))
        alive = c.execute("select state from products where scope=%s for update",
                          (case,)).fetchone()[0] != "cancelled"
        if known and alive and current != "confirmed":
            sink(case, "downstream")
    return "confirmed" if known else "unknown"


def late_callback(case):
    reply = sink(case, "lookup", {"op": case})
    return callback(case, reply["known"])


def cancel(case):
    with db() as c:
        c.execute("update pools set closed=true where scope=%s", (case,))
        c.execute("update products set state='cancelled' where scope=%s", (case,))


def child(case, name):
    with db() as c:
        pool = c.execute("select available,closed from pools where scope=%s for update", (case,)).fetchone()
        old = c.execute("select paid from holds where scope=%s and child=%s", (case, name)).fetchone()
        if old and old[0] is not None:
            return "settled"
        if not old and (pool[1] or pool[0] < 3):
            sink(case, "budget_denied", {"child": name})
            return "blocked"
        if not old:
            c.execute("update pools set available=available-3 where scope=%s", (case,))
            c.execute("insert into holds values(%s,%s,3,null)", (case, name))
    barrier(case, "reserved")
    if old:
        response = sink(case, "charge_lookup", {"op": name})
        if not response["known"]:
            return "unknown"
    else:
        with db() as c:
            closed = c.execute("select closed from pools where scope=%s for share", (case,)).fetchone()[0]
            if closed:
                return "held"
            response = sink(case, "charge", {"op": name})
        barrier(case, "charged")
    with db() as c:
        c.execute("select scope from pools where scope=%s for update", (case,))
        units = response["units"]
        if type(units) is not int or not 0 <= units <= 3:
            raise ValueError("receipt exceeds reservation")
        changed = c.execute(
            "update holds set paid=%s,units=0 where scope=%s and child=%s and paid is null returning child", (units, case, name)).fetchone()
        if changed:
            c.execute("update pools set available=available+3-%s,spent=spent+%s where scope=%s", (units, units, case))
    return "settled"


def state(case):
    with db() as c:
        product = c.execute("select state from products where scope=%s", (case,)).fetchone()[0]
        op = c.execute("select state,settles from operations where scope=%s", (case,)).fetchone()
        spent, held = c.execute("select spent,5-available-spent from pools where scope=%s", (case,)).fetchone()
        return dict(product=product, op=op, spent=spent, held=held)
