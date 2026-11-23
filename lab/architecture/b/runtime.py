import json, os, hashlib, uuid
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
          create table agent_observations(id uuid primary key,scope text,capability text,result text);
          create table identities(digest text primary key,tenant text,member text);
          create table licenses(target text,package text,tenant text,member text,primary key(target,package,tenant,member));
          create table jobs(id text primary key,denied text[] default '{}',status text default 'active',memo text,assessment jsonb);
          create table dispatch(id text primary key,ack boolean default false);
          create table budget(id text,worker text,allocated integer,consumed integer,primary key(id,worker));
          create table snapshots(scope text,spent int,held int);
          create function budget_snapshot() returns trigger language plpgsql as $$ begin
          insert into snapshots select new.id,coalesce(sum(consumed),0),coalesce(sum(allocated) filter(where consumed is null),0)
          from budget where id=new.id;return new;end;$$;
          create trigger capture after insert or update on budget for each row execute function budget_snapshot()""")
        for tenant, member, key in (("lab", "user", "LAB_TOKEN"), ("outside", "outsider", "LAB_OUTSIDER")):
            conn.execute("insert into identities values(%s,%s,%s)",
                         (hashlib.sha256(os.environ[key].encode()).hexdigest(), tenant, member))


def install(spec, published):
    with connect() as conn:
        conn.execute("insert into packages values(%s,%s,%s)", (spec["name"], Jsonb(spec), published))


def allow_tool(case, name, yes=True):
    with connect() as conn:
        if yes:
            conn.execute("insert into licenses values(%s,%s,'lab','user') on conflict do nothing", (case, name))
        else:
            conn.execute("delete from licenses where target=%s and package=%s", (case, name))


def tool(case, name, args, token):
    barrier(case, "agent_tool_out")
    with connect() as conn:
        permission = conn.execute("select denied from jobs where id=%s for share", (case,)).fetchone()
        if not permission or "tool_out" in permission[0]:
            raise PermissionError("tool_out")
        found = conn.execute("""select contract from packages join licenses on package=id
                              join identities using (tenant,member) where id=%s and target=%s and live
                              and digest=%s for share""", (name, case, hashlib.sha256(token.encode()).hexdigest())).fetchone()
        if found is None:
            raise PermissionError("unpublished or unauthorized")
        validated = schema(found[0]).model_validate(args)
        result = sink(case, "tool", {"name": name, "args": validated.model_dump()})
        return Output.model_validate(result).model_dump()


def agent(case, cmd):
    with connect() as conn:
        all_specs = dict(conn.execute("select id,contract from packages"))

    satisfied = {}

    def adapt(spec):
        def invoke(**kwargs):
            output = tool(case, spec["name"], kwargs, os.environ["LAB_TOKEN"])
            name = spec["name"]
            reference = uuid.uuid4()
            with connect() as conn:
                conn.execute("insert into agent_observations values(%s,%s,%s,%s)",
                             (reference, case, name, output["value"]))
            if name in cmd["required"] and cmd["required"][name] in (None, output["value"]):
                satisfied[name] = str(reference)
            return output
        return Tool.from_schema(invoke, name=spec["name"], description=spec["description"],
                                json_schema=schema(spec).model_json_schema(), takes_ctx=False)
    provider = OpenAIProvider(base_url=f"{FIXTURE}/{case}/{cmd['backend']}/v1", api_key="fixture-only")

    class AuthorizedModel(OpenAIChatModel):
        async def request(self, *args, **kwargs):
            barrier(case, "agent_model")
            with connect() as conn:
                rules = conn.execute("select denied from jobs where id=%s for share", (case,)).fetchone()
                if not rules or "model" in rules[0]:
                    raise PermissionError("model")
                return await super().request(*args, **kwargs)
    model = AuthorizedModel("qwen2.5:1.5b", provider=provider)
    agent_instance = Agent(model, tools=[adapt(all_specs[n]) for n in cmd["names"]], model_settings={
                           "temperature": 0, "max_tokens": 160})
    result = agent_instance.run_sync(cmd["prompt"], usage_limits=UsageLimits(request_limit=6))
    return {"turns": result.usage.requests, "finished": True, "version": cmd["version"], "evidence": satisfied,
            "completed": sorted(satisfied), "missing": sorted(n for n in cmd["required"] if n not in satisfied)}


def prepare(case):
    with connect() as conn:
        conn.execute("insert into jobs(id) values(%s)", (case,))


def revoke(case, action):
    with connect() as conn:
        conn.execute("update jobs set denied=array_append(denied,%s) where id=%s", (action, case))


def stage(case, action):
    barrier(case, action)
    with connect() as conn:
        refusals, memo = conn.execute("select denied,memo from jobs where id=%s for share", (case,)).fetchone()
        if action in refusals:
            conn.execute("update jobs set status='denied' where id=%s", (case,))
            return "denied"
        if action == "model":
            model_http(case, "controlled", [{"role": "user", "content": memo or ""}], [])
        elif action == "tool_out":
            tool(case, "item_state", {"key": memo or ""}, os.environ["LAB_TOKEN"])
        else:
            outcome = sink(case, action, {"marker": memo})
            if action == "read":
                conn.execute("update jobs set memo=%s where id=%s", (outcome["value"], case))
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
    required = set(policy["required"]) if policy else set()
    reasons = required.difference(data["items"])
    ok = data["validator"] and data["version"] == policy["version"] and not reasons
    if ok:
        for action in ("commit", "deliver"):
            if stage(case, action) != "ok":
                return "denied"
    outcome = "succeeded" if ok else "review"
    code = "complete" if ok else "unavailable" if not policy else "version" if data[
        "version"] != policy["version"] else "missing"
    with connect() as conn:
        conn.execute("update jobs set status=%s,assessment=%s where id=%s",
                     (outcome, Jsonb({"reason": code, "rule": "v1"}), case))
    return outcome


def verdict(case):
    with connect() as conn:
        data = conn.execute("select assessment from jobs where id=%s", (case,)).fetchone()[0]
        return data["reason"], data["rule"]


def supplier(case):
    with connect() as conn:
        inserted = conn.execute(
            "insert into dispatch(id) values(%s) on conflict do nothing returning id", (case,)).fetchone()
        if inserted:
            conn.execute("select id from jobs where id=%s for update", (case,))
            if conn.execute("select coalesce(sum(coalesce(consumed,allocated)),0) from budget where id=%s", (case,)).fetchone()[0] > 2:
                raise RuntimeError("over budget")
            conn.execute("insert into budget values(%s,'supplier',3,null)", (case,))
    if inserted:
        barrier(case, "supplier_gate")
        with connect() as conn:
            status, denied = conn.execute(
                "select status,denied from jobs where id=%s for share", (case,)).fetchone()
            if status == "cancelled" or "commit" in denied:
                conn.execute("delete from budget where id=%s and worker='supplier'", (case,))
                return "denied"
            response = sink(case, "supplier_send", {"op": case})
        barrier(case, "after_effect")
    else:
        response = sink(case, "lookup", {"op": case})
    return callback(case, response["known"])


def callback(case, known):
    with connect() as conn:
        job = conn.execute("select status from jobs where id=%s for update", (case,)).fetchone()[0]
        if known:
            fresh = conn.execute(
                "update dispatch set ack=true where id=%s and not ack returning id", (case,)).fetchone()
            if fresh:
                conn.execute("update budget set consumed=2 where id=%s and worker='supplier'", (case,))
                if job != "cancelled":
                    sink(case, "downstream")
    return "confirmed" if known else "unknown"


def late_callback(case):
    reply = sink(case, "lookup", {"op": case})
    return callback(case, reply["known"])


def cancel(case):
    with connect() as conn:
        conn.execute("update jobs set status='cancelled' where id=%s", (case,))


def child(case, name):
    with connect() as conn:
        job = conn.execute("select status from jobs where id=%s for update", (case,)).fetchone()[0]
        current = conn.execute(
            "select allocated,consumed from budget where id=%s and worker=%s", (case, name)).fetchone()
        if current and current[1] is not None:
            return "settled"
        if current is None:
            total = conn.execute(
                "select coalesce(sum(coalesce(consumed,allocated)),0) from budget where id=%s", (case,)).fetchone()[0]
            if job == "cancelled" or total + 3 > 5:
                sink(case, "budget_denied", {"child": name})
                return "blocked"
            conn.execute("insert into budget values(%s,%s,3,null)", (case, name))
    barrier(case, "reserved")
    if current:
        receipt = sink(case, "charge_lookup", {"op": name})
        if not receipt["known"]:
            return "unknown"
    else:
        with connect() as conn:
            job = conn.execute("select status from jobs where id=%s for share", (case,)).fetchone()[0]
            if job == "cancelled":
                return "held"
            receipt = sink(case, "charge", {"op": name})
        barrier(case, "charged")
    with connect() as conn:
        actual = receipt["units"]
        if type(actual) is not int or actual not in range(4):
            raise ValueError("invalid charge receipt")
        conn.execute("update budget set consumed=%s where id=%s and worker=%s and consumed is null",
                     (actual, case, name))
    return "settled"


def state(case):
    with connect() as conn:
        status = conn.execute("select status from jobs where id=%s", (case,)).fetchone()[0]
        ack = conn.execute("select ack from dispatch where id=%s", (case,)).fetchone()
        used, held = conn.execute(
            "select coalesce(sum(consumed),0),coalesce(sum(allocated) filter(where consumed is null),0) from budget where id=%s", (case,)).fetchone()
        return dict(product=status, op=(("confirmed", 1) if ack[0] else ("unknown", 0)) if ack else None, spent=int(used), held=int(held))
