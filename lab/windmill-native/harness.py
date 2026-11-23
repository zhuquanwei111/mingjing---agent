"""Real Windmill public APIs, independent ledgers, and process fault controller."""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
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


def worker():
    global WORKER
    name = "wmn-worker" if WORKER is None else WORKER+"-next"
    cli("docker","run","-d","--name",name,"--hostname",name,"--network","host","-e","DATABASE_URL",
        "-e","BASE_URL","-e","BASE_INTERNAL_URL=http://127.0.0.1:8000","-e","MODE=worker",
        "-e","WORKER_GROUP=default","-e","ALLOW_PRIVATE_AI_BASE_URLS","-e","FAVOR_UNSHARE_PID=false",
        "-e","DISABLE_NSJAIL=true","-e","SLEEP_QUEUE=100",os.environ["CE_DIGEST"])
    WORKER = name
    note("worker_started",container=name,pid=cli("docker","inspect","-f","{{.State.Pid}}",name))


def register():
    global TOKEN, PREFIX
    TOKEN = http(API+"/auth/login", {"email":"admin@windmill.dev","password":"changeme"})
    user = call("/users/whoami")
    PREFIX = "u/"+user["username"]+"/wmn_"
    schema = {"type":"object","properties":{"operation":{"type":"string"}},"required":["operation"]}
    for key in ["tool","deliver"]:
        hashed = call("/scripts/create",{"path":PREFIX+key,"summary":key,"content":Path(key+".bun.ts").read_text(),
            "language":"bun","schema":schema})
        note("registered_script",name=key,hash=str(hashed))
    expr = {"type":"javascript","expr":"flow_input.operation"}
    def step(key):
        return {"type":"script","path":PREFIX+key,"input_transforms":{"operation":expr}}
    def fixed(value):
        return {"type":"static","value":value}
    brain = {"type":"aiagent","tools":[{"id":"t","summary":"async_operation","requires_approval":True,
             "value":step("tool")}],"input_transforms":{
             "provider":fixed({"kind":"customai","model":"fixture","resource":{"base_url":RECEIVER+"/v1"}}),
             "max_iterations":fixed(3),"streaming":fixed(False),"user_message":expr}}
    value = {"modules":[{"id":"agent","value":brain},{"id":"deliver","value":step("deliver")}]}
    spec = {"path":PREFIX+"flow","summary":"Native CE comparison","schema":schema,"value":value}
    (OUT/"registered-flow.json").write_text(json.dumps(spec,indent=2))
    note("registered_flow",response=call("/flows/create",spec))
    wait("deployed scripts and flow dependencies",lambda:pg("select count(*) from v2_job_queue")=="0",100)


def logs(op):
    out={}
    for name, tables in [("product",("ops","entries")),("receiver",("models","events"))]:
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
            "models":len(data["models"]), "held":data["ops"][0]["held"],"spent":data["ops"][0]["spent"],
            "entries":len(data["entries"]), "paired":sum(m["paired"] for m in data["models"])}


def lineage(root):
    query=f"""with recursive branch as (
        select id,parent_job,kind from v2_job where id='{root}' union all
        select j.id,j.parent_job,j.kind from v2_job j join branch b on j.parent_job=b.id)
    select coalesce(json_agg(to_jsonb(t))::text,'[]') from (
        select b.*,q.worker,q.running,q.suspend,c.status,zc.counter
        from branch b left join v2_job_queue q on q.id=b.id left join v2_job_completed c on c.id=b.id
        left join zombie_job_counter zc on zc.job_id=b.id)t"""
    return json.loads(pg(query))


def state(op,root,stage):
    doc={"counts":counts(op),"jobs":lineage(root),"ledger":logs(op)}
    (OUT/(op+"-"+stage+".json")).write_text(json.dumps(doc, indent=2))
    note(stage,op=op,root=root,counts=doc["counts"],jobs=doc["jobs"])
    return doc


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
    assert cp["data"]["pending"]["call_id"]==actual_id
    (OUT/(op+"-parked.json")).write_text(json.dumps(cp,indent=2))
    call("/jobs_u/flow/resume_suspended/"+agent,{"approved":True,"payload":{"call_id":actual_id}})
    wait("tool POST/202",lambda:counts(op)["http_post"]==1)
    assert counts(op)["effect"]==counts(op)["simulated_charge"]==0
    state(op,root,"accepted")
    http(RECEIVER+"/complete/"+op,{})
    boundary=state(op,root,"prekill" if tag!="baseline" else "prerelease")
    assert boundary["counts"]["effect"]==boundary["counts"]["simulated_charge"]==1
    assert boundary["counts"]["models"]==1 and boundary["counts"]["delivery"]==0
    assert boundary["ledger"]["ops"][0]["receipt"] is None
    tooljob=boundary["ledger"]["entries"][0]["job"]
    jobrows={j["id"]:j for j in boundary["jobs"]}
    for ident in (agent,tooljob):
        assert jobrows[ident]["running"] and not jobrows[ident]["status"],jobrows
    assert jobrows[tooljob]["parent_job"]==agent
    if tag!="baseline":
        # The sole worker container owns BOTH live job rows, and the only eligible runner is killed.
        assert jobrows[agent]["worker"] and jobrows[agent]["worker"]==jobrows[tooljob]["worker"],jobrows
        old=WORKER
        original_pid=cli("docker","inspect","-f","{{.State.Pid}}",old)
        cli("docker","kill","--signal","KILL",old)
        note("killed",pid=original_pid,container=old,agent=agent,tool=tooljob,
             worker=jobrows[agent]["worker"],exit=cli("docker","inspect","-f","{{.State.ExitCode}}",old))
        worker()
        recovered=wait("new native job attempt or terminal status",
            lambda:next((j for j in lineage(root) if j["id"]==agent and
                         ((j["worker"] and j["worker"]!=jobrows[agent]["worker"]) or j["status"])),None),180)
        state(op,root,"replacement")
        assert recovered["worker"] and recovered["worker"]!=jobrows[agent]["worker"],recovered
        if tag=="cancel":
            before=state(op,root,"unknown")["counts"]
            assert (before["held"],before["spent"],before["models"],before["delivery"])==(3,0,1,0)
            http(PRODUCT+"/cancel/"+op,{})
            call("/jobs_u/queue/cancel/"+root,{"reason":"synthetic cancel"})
            wait("canceled native root",lambda:any(j["id"]==root and j["status"]=="canceled" for j in lineage(root)),90)
    http(RECEIVER+"/open/"+op,{})
    if tag=="cancel":
        for _ in range(2):
            http(PRODUCT+"/reconcile/"+op,{})
        time.sleep(3)
    else:
        wait("real native flow terminal",lambda:any(j["id"]==root and j["status"] for j in lineage(root)),120)
    final=state(op,root,"final")
    c=final["counts"]
    assert (c["http_post"],c["effect"],c["simulated_charge"],c["held"],c["spent"])==(1,1,1,0,1),c
    assert (c["models"],c["paired"],c["delivery"])==((1,0,0) if tag=="cancel" else (2,1,1)),c
    return op


def main():
    subs=[subprocess.Popen([sys.executable,"services.py",name]) for name in ["product","receiver"]]
    try:
        time.sleep(.5)
        assert http(PRODUCT+"/health")=="ready" and http(RECEIVER+"/health")=="ready"
        worker()
        register()
        done={}
        for tag in ["baseline","known","cancel"]:
            try:
                done[tag]={"operation":run_case(tag),"status":"pass"}
            except Exception as exc:
                done[tag]={"status":"error","error":repr(exc)}
                (OUT/"case-results.json").write_text(json.dumps(done,indent=2))
                raise
            (OUT/"case-results.json").write_text(json.dumps(done,indent=2))
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
