"""Real Windmill public APIs, independent ledgers, and process fault controller."""
import json
import hashlib
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from model_gate import ALIAS
from services import OUT, PRODUCT, RECEIVER, database, http

API = "http://127.0.0.1:8000/api"
W = API + "/w/admins"
TOKEN = None
PREFIX = None
WORKER = None
HISTORY = []


def note(stage, **data):
    record = {"stage":stage, "time":time.time(), **data}
    HISTORY.append(record)
    print(json.dumps(record,ensure_ascii=False), flush=True)
    (OUT/"observations.json").write_text(json.dumps(HISTORY,indent=2))


def cli(*args):
    return subprocess.check_output(args, text=True).strip()


def pg(query):
    return cli("docker","exec","wmn-pg","psql","-U","postgres","windmill","-XAt","-v","ON_ERROR_STOP=1","-c",query)


def call(path, body=None):
    return http(W+path,body,TOKEN)


def wait(label, fn, seconds=100):
    until = time.monotonic()+seconds
    while time.monotonic()<until:
        value = fn()
        if value:
            return value
        time.sleep(0.6)
    raise TimeoutError(label)


def worker(helper=False):
    global WORKER
    name = "wmn-worker" if WORKER is None else WORKER+"-next"
    if helper:
        name=WORKER+"-helper"
    cli("docker","run","-d","--name",name,"--hostname",name,"--network","host","-e","DATABASE_URL",
        "-e","BASE_URL","-e","BASE_INTERNAL_URL=http://127.0.0.1:8000","-e","MODE=worker",
        "-e","WORKER_GROUP=default","-e","ALLOW_PRIVATE_AI_BASE_URLS","-e","FAVOR_UNSHARE_PID=false",
        "-e","DISABLE_NSJAIL=true","-e","SLEEP_QUEUE=100",os.environ["CE_DIGEST"])
    if not helper:
        WORKER = name
    note("worker_started",container=name,pid=cli("docker","inspect","-f","{{.State.Pid}}",name))
    return name


def register():
    global TOKEN, PREFIX
    TOKEN = http(API+"/auth/login", {"email":"admin@windmill.dev","password":"changeme"})
    user = call("/users/whoami")
    PREFIX = "u/"+user["username"]+"/wmn_"
    schema = {"type":"object","properties":{"operation":{"type":"string"}},"required":["operation"]}
    for key in ["tool","deliver"]:
        script_schema=json.loads(json.dumps(schema))
        if key=="deliver":
            script_schema["properties"]["verdict"]={"type":"string"}
            script_schema["required"].append("verdict")
        hashed = call("/scripts/create",{"path":PREFIX+key,"summary":key,"content":Path(key+".bun.ts").read_text(),
            "language":"bun","schema":script_schema})
        note("registered_script",name=key,hash=str(hashed))
    expr = {"type":"javascript","expr":"flow_input.operation"}
    def step(key):
        return {"type":"script","path":PREFIX+key,"input_transforms":{"operation":expr}}
    def fixed(value):
        return {"type":"static","value":value}
    brain = {"type":"aiagent","tools":[{"id":"t","summary":"async_operation","requires_approval":True,
             "value":step("tool")}],"input_transforms":{
             "provider":fixed({"kind":"customai","model":"fixture","resource":{"base_url":PRODUCT+"/v1"}}),
             "max_iterations":fixed(3),"streaming":fixed(False),"user_message":expr}}
    delivery=step("deliver")
    delivery["input_transforms"]["verdict"]={"type":"javascript","expr":"results.agent.output"}
    value = {"modules":[{"id":"agent","value":brain},{"id":"deliver","value":delivery}]}
    spec = {"path":PREFIX+"flow","summary":"Native CE comparison","schema":schema,"value":value}
    (OUT/"registered-flow.json").write_text(json.dumps(spec,indent=2))
    note("registered_flow",response=call("/flows/create",spec))
    assert re.fullmatch(r"u/[a-zA-Z0-9_-]+/wmn_",PREFIX)
    wait("deployed scripts and flow dependencies",lambda:pg(f"select count(*) from v2_job_queue q join v2_job j using(id) where j.runnable_path like '{PREFIX}%'")=="0",100)


def logs(op):
    out={}
    for name, tables in [("product",("ops","entries","model_attempts","model_intents")),("receiver",("models","events","model_http"))]:
        db=database(name)
        for table in tables:
            rows=[dict(x) for x in db.execute(f"select * from {table} where op=? order by rowid",(op,))]
            if table=="models":
                for row in rows:
                    row["body"]=json.loads(row["body"])
            out[table]=rows
        db.close()
    return out


def counts(op):
    data=logs(op)
    return {**{kind:sum(e["kind"]==kind for e in data["events"]) for kind in
            ["http_post","effect","simulated_charge","delivery"]},
            "models":len(data["model_http"]), "model_test_fees":sum(m["fee"] for m in data["model_http"]), "model_parsed":len(data["models"]), "held":data["ops"][0]["held"],"spent":data["ops"][0]["spent"],
            "gate_attempts":len(data["model_attempts"]), "gate_denials":sum(not a["allowed"] for a in data["model_attempts"]),
            "entries":len(data["entries"]), "paired":sum(m["paired"] for m in data["models"])}


def lineage(root):
    query=f"""with recursive branch as (
        select id,parent_job,kind from v2_job where id='{root}' union all
        select j.id,j.parent_job,j.kind from v2_job j join branch b on j.parent_job=b.id)
    select coalesce(json_agg(to_jsonb(t))::text,'[]') from (
        select b.*,q.worker,q.running,q.suspend,c.status,c.worker as completed_worker,zc.counter
        from branch b left join v2_job_queue q on q.id=b.id left join v2_job_completed c on c.id=b.id
        left join zombie_job_counter zc on zc.job_id=b.id)t"""
    return json.loads(pg(query))


def state(op,root,stage):
    doc={"counts":counts(op),"jobs":lineage(root),"ledger":logs(op)}
    (OUT/(op+"-"+stage+".json")).write_text(json.dumps(doc, indent=2))
    note(stage,op=op,root=root,counts=doc["counts"],jobs=doc["jobs"])
    return doc


def scan_engine(op,call_id,stage):
    # Alphanumeric markers survive PostgreSQL COPY text escaping unchanged.
    # Read all public data without publishing unrelated rows, settings or bearer tokens.
    db=database("product")
    prompt=db.execute("select prompt_private from ops where op=?",(op,)).fetchone()[0]
    db.close()
    db=database("receiver")
    details=db.execute("select result_private from jobs where op=?",(op,)).fetchone()[0]
    models=db.execute("select raw from model_http where op=?",(op,)).fetchall()
    db.close()
    assert prompt and details and any(prompt in r[0] for r in models)
    text=cli("docker","exec","wmn-pg","pg_dump","-U","postgres","--data-only","--schema=public","windmill")
    internal=logs(op)["ops"][0]["engine_call_id"]
    markers={"product_prompt":prompt,"provider_details":details,"original_call_id":call_id,"engine_call_reference":internal}
    table=None
    hits={k:{} for k in markers}
    scanned=0
    for line in text.splitlines():
        if line.startswith("COPY "):
            table=line.split()[1]
            scanned+=1
        elif line==chr(92)+".":
            table=None
        elif table:
            for k,marker in markers.items():
                if marker in line:
                    hits[k][table]=hits[k].get(table,0)+1
    note("engine_scan",operation=op,point=stage,public_tables=scanned,matching_rows=hits)
    assert scanned>30 and not hits["product_prompt"] and not hits["provider_details"] and hits["engine_call_reference"]
    assert bool(hits["original_call_id"]) == (not ALIAS)
    return hits


def run_case(tag):
    op=tag+"_"+uuid.uuid4().hex[:12]
    http(PRODUCT+"/init/"+op,{})
    root=str(uuid.UUID(call("/jobs/run/f/"+PREFIX+"flow",{"operation":op})))
    note("submitted",op=op,root=root)
    def checkpoint():
        text=pg(f"select json_build_object('job',c.job_id,'data',c.checkpoint)::text from ai_agent_checkpoint c join v2_job j on j.id=c.job_id where j.parent_job='{root}'")
        if text:
            return json.loads(text)
        rows=lineage(root)
        if any(j["id"]==root and j["status"] for j in rows):
            raise RuntimeError("Root ended before park "+str(call("/jobs_u/get/"+root))[:2600])
        return None
    cp=wait("native approval checkpoint",checkpoint)
    agent=str(uuid.UUID(cp["job"]))
    actual_id=logs(op)["models"][0]["call_id"]
    pending=cp["data"]["pending"]["call_id"]
    assert pending==logs(op)["ops"][0]["engine_call_id"] and ((actual_id!=pending)==ALIAS)
    (OUT/(op+"-parked.json")).write_text(json.dumps(cp,indent=2))
    call("/jobs_u/flow/resume_suspended/"+agent,{"approved":True,"payload":{"call_id":pending}})
    wait("tool POST/202",lambda:counts(op)["http_post"]==1)
    assert counts(op)["effect"]==counts(op)["simulated_charge"]==0
    state(op,root,"accepted")
    http(RECEIVER+"/complete/"+op,{})
    wait("separate provider worker committed effect and fee",lambda:counts(op)["simulated_charge"]==1)
    boundary=state(op,root,"prekill" if tag!="baseline" else "prerelease")
    assert boundary["counts"]["effect"]==boundary["counts"]["simulated_charge"]==1
    assert boundary["counts"]["models"]==1 and boundary["counts"]["delivery"]==0
    assert boundary["ledger"]["ops"][0]["receipt"] is None
    scan_engine(op,actual_id,"effect_before_result")
    tooljob=boundary["ledger"]["entries"][0]["job"]
    jobrows={j["id"]:j for j in boundary["jobs"]}
    for ident in (agent,tooljob):
        assert jobrows[ident]["running"] and not jobrows[ident]["status"],jobrows
    assert jobrows[tooljob]["parent_job"]==agent
    helper=None
    if tag!="baseline":
        # The sole worker container owns BOTH live job rows, and the only eligible runner is killed.
        assert jobrows[agent]["worker"] and jobrows[agent]["worker"]==jobrows[tooljob]["worker"],jobrows
        old=WORKER
        original_pid=cli("docker","inspect","-f","{{.State.Pid}}",old)
        cli("docker","kill","--signal","KILL",old)
        note("killed",pid=original_pid,container=old,agent=agent,tool=tooljob,
             worker=jobrows[agent]["worker"],exit=cli("docker","inspect","-f","{{.State.ExitCode}}",old))
        if tag=="oldversion":
            http(PRODUCT+"/switch_reader/"+op,{})
        worker()
        helper=worker(helper=True)
        recovered=wait("new native job attempt or terminal status",
            lambda:next((j for j in lineage(root) if j["id"]==agent and
                         ((j["worker"] and j["worker"]!=jobrows[agent]["worker"]) or j["status"])),None),180)
        state(op,root,"replacement")
        assert recovered["worker"] and recovered["worker"]!=jobrows[agent]["worker"],recovered
        wait("reentry tool queried the still unknown receipt",
             lambda:counts(op)["entries"]>1 and any(e["kind"]=="query" and e["value"]=="unknown"
                 for e in logs(op)["events"][len(boundary["ledger"]["events"]):]),90)
        if tag=="cancel":
            time.sleep(2)
            before=state(op,root,"unknown")["counts"]
            assert (before["held"],before["spent"],before["models"],before["delivery"])==(3,0,1,0)
            http(PRODUCT+"/cancel/"+op,{})
            call("/jobs_u/queue/cancel/"+root,{"reason":"synthetic cancel"})
            wait("canceled native root",lambda:any(j["id"]==root and j["status"]=="canceled" for j in lineage(root)),90)
    http(RECEIVER+"/open/"+op,{})
    if tag=="oldversion":
        wait("quarantined old run after trusted reconciliation",lambda:counts(op)["spent"]==1)
        doc=state(op,root,"quarantined")
        old=doc["ledger"]["ops"][0]
        assert (old["version"],old["reader"],old["quarantine"])==(1,2,1)
        c=doc["counts"]
        assert (c["held"],c["spent"],c["models"],c["delivery"],c["http_post"],c["effect"],c["simulated_charge"])==(0,1,1,0,1,1,1)
        saved=checkpoint()
        assert saved["data"]==cp["data"] and saved["job"]==agent
        note("older_checkpoint_preserved",op=op,agent=agent,sha256=hashlib.sha256(json.dumps(saved,sort_keys=True).encode()).hexdigest())
        assert old["result_private"] and old["result_private"] not in json.dumps(doc["ledger"]["model_http"])
        scan_engine(op,actual_id,"quarantine")
        return op
    if tag=="cancel":
        for _ in range(2):
            http(PRODUCT+"/reconcile/"+op,{})
        time.sleep(3)
    else:
        wait("real native flow terminal",lambda:any(j["id"]==root and j["status"] for j in lineage(root)),120)
    final=state(op,root,"final")
    c=final["counts"]
    scan_engine(op,actual_id,"terminal")
    assert (c["http_post"],c["effect"],c["simulated_charge"],c["held"],c["spent"])==(1,1,1,0,1),c
    assert (c["models"],c["paired"],c["delivery"])==((1,0,0) if tag=="cancel" else (2,1,1)),c
    root_state=next(j["status"] for j in final["jobs"] if j["id"]==root)
    assert root_state==("canceled" if tag=="cancel" else "success"),root_state
    if tag=="known":
        last=final["ledger"]
        inbound=json.loads(last["model_attempts"][-1]["body"])
        outbound=last["models"][-1]["body"]
        def ids(request):
            messages=request["messages"]
            assistant=[c["id"] for m in messages if m["role"]=="assistant" for c in m.get("tool_calls",[])]
            tools=[m["tool_call_id"] for m in messages if m["role"]=="tool"]
            return assistant,tools
        assert ids(inbound)==([pending],[pending]) and ids(outbound)==([actual_id],[actual_id])
        note("paired_across_boundary",op=op,agent=agent,internal_ids=ids(inbound),
             provider_ids=ids(outbound),original_external=actual_id,engine_reference=pending)
        body=json.loads(final["ledger"]["model_attempts"][-1]["body"])
        bad=json.loads(json.dumps(body))
        next(m for m in bad["messages"] if m["role"]=="tool")["tool_call_id"]="wrong_"+uuid.uuid4().hex
        try:
            http(PRODUCT+"/v1/chat/completions",bad)
        except RuntimeError as exc:
            assert "403" in str(exc)
        else:
            raise AssertionError("wrong ID forwarded")
        tested=state(op,root,"negative_wrong_id")["counts"]
        assert tested["gate_denials"]==c["gate_denials"]+1
        for key in ["models","http_post","effect","simulated_charge","delivery"]:
            assert tested[key]==c[key],tested
    if helper:
        cli("docker","stop","--time","1",helper)
    return op


def retry_probe(tag):
    op=tag+"_"+uuid.uuid4().hex[:12]
    http(PRODUCT+"/init/"+op,{})
    root=str(uuid.UUID(call("/jobs/run/f/"+PREFIX+"flow",{"operation":op})))
    wait("model retry probe terminal",lambda:any(j["id"]==root and j["status"] for j in lineage(root)),90)
    outcome=state(op,root,"model_retry")
    expected=4 if tag in ("retrydefault","lossraw") else 1
    raw=outcome["ledger"]["model_http"]
    assert len(raw)==sum(m["fee"] for m in raw)==expected
    if tag=="lossguarded":
        assert outcome["counts"]["gate_attempts"]==2 and outcome["counts"]["gate_denials"]==1
        assert [t["state"] for t in outcome["ledger"]["model_intents"]]==["unknown"]
    assert outcome["counts"]["http_post"]==outcome["counts"]["delivery"]==0
    assert next(j["status"] for j in outcome["jobs"] if j["id"]==root)=="failure"
    return op


def main():
    subs=[subprocess.Popen([sys.executable,"services.py",name]) for name in ["product","receiver"]]
    try:
        time.sleep(.5)
        assert http(PRODUCT+"/health")=="ready" and http(RECEIVER+"/health")=="ready"
        subs.append(subprocess.Popen([sys.executable,"services.py","completer"]))
        note("independent_service_pids",product=subs[0].pid,receiver=subs[1].pid,async_worker=subs[2].pid)
        worker()
        register()
        done={}
        for tag in ["baseline","retrydefault","retryprotected","lossraw","lossguarded","known","cancel","oldversion"]:
            try:
                run=retry_probe if tag.startswith(("retry","loss")) else run_case
                done[tag]={"operation":run(tag),"test_expectation":"observed"}
            except Exception as exc:
                done[tag]={"status":"error","error":repr(exc)}
                (OUT/"case-results.json").write_text(json.dumps(done,indent=2))
                raise
            (OUT/"case-results.json").write_text(json.dumps(done,indent=2))
        db=database("receiver")
        unattributed=db.execute("select count(*) from model_http where op is null").fetchone()[0]
        db.close()
        note("unattributed_model_http",count=unattributed)
        assert unattributed==0
        (OUT/"requirement-outcomes.json").write_text(json.dumps({
            "native_direct_cancel_no_model":"failed in runs 45190773511 and 45191055874",
            "guarded_known_unknown_cancel_pairing":"matched in observed cases",
            "engine_excludes_two_private_markers_observed_public_text_dump":True,
            "engine_excludes_original_tool_call_id":ALIAS,
            "real_binary_rolling_upgrade":"unverified",
            "provider_default_503_after_charge_zero_resend":False,
            "provider_tcp_closed_after_charge_durable_claim":"verified for this two-turn protocol"
        },indent=2))
    finally:
        for proc in subs:
            proc.terminate()
            proc.wait(timeout=10)
        print("Windmill job diagnostics",pg("select j.kind,j.runnable_path,q.worker,q.running,c.status,left(c.result::text,800) from v2_job j left join v2_job_queue q using(id) left join v2_job_completed c using(id) order by j.created_at desc limit 15"))
        for name in cli("docker","ps","-a","--format","{{.Names}}").splitlines():
            if name.startswith("wmn-worker"):
                Path(OUT/(name+".log")).write_bytes(subprocess.check_output(["docker","logs",name],stderr=subprocess.STDOUT))


if __name__=="__main__":
    main()
