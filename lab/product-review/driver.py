"""Drive the real cloud services. Assertions read independent, durable receiving records."""
import asyncio
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from temporalio.client import Client
from flow import Notice, Round

OUT = Path("/out")
CASES = ["known","unknown","cancel","incompatible","wrong_pair"]
SCHEMA = """
CREATE TABLE task(scope text PRIMARY KEY, descriptor jsonb NOT NULL, marker text NOT NULL,
  reader_versions int[] NOT NULL, wrong_pair boolean NOT NULL, active boolean DEFAULT true,
  op text UNIQUE, call text, msg jsonb, checkpoint_version int, held int DEFAULT 0,
  spent int DEFAULT 0, settled text, state text DEFAULT 'new', model_slots int DEFAULT 0);
CREATE TABLE events(id bigserial PRIMARY KEY, scope text, kind text, detail jsonb);
"""


def connection(name):
    return psycopg.connect(os.environ[name],row_factory=dict_row)


def subset(c,query,args=()):
    return list(c.execute(query,args).fetchall())


def record(case,stage,data):
    with (OUT/"raw.jsonl").open("a") as f:
        print(json.dumps({"case":case,"stage":stage,"data":data},sort_keys=True),file=f)


def source_hashes():
    return {p:hashlib.sha256(Path("/exp",p).read_bytes()).hexdigest()
            for p in ("worker.py","flow.py")}


def snapshot(scope):
    with connection("PRODUCT_DSN") as c:
        task = c.execute("SELECT * FROM task WHERE scope=%s",(scope,)).fetchone()
        product = subset(c,"SELECT id,kind,detail FROM events WHERE scope=%s ORDER BY id",(scope,))
    with connection("WITNESS_DSN") as c:
        observed = subset(c,"SELECT seq,kind,detail FROM requests WHERE scope=%s ORDER BY seq",(scope,))
        jobs = subset(c,"SELECT * FROM jobs WHERE scope=%s",(scope,))
        effects = subset(c,"SELECT e.* FROM effects e JOIN jobs USING(op) WHERE scope=%s",(scope,))
        fees = subset(c,"SELECT f.* FROM fees f JOIN jobs USING(op) WHERE scope=%s ORDER BY f.id",(scope,))
    return {"task":task,"product":product,"observed":observed,"jobs":jobs,"effects":effects,"fees":fees}


def events(s, kind):
    return [e["detail"] for e in s["observed"] + s["product"] if e["kind"]==kind]


def counts(s):
    return [len(events(s,"arrival")),len(s["effects"]),len(s["fees"]),len(events(s,"delivery")),len(events(s,"model"))]


def start_worker(build):
    env = {k:v for k,v in os.environ.items() if k not in ("WITNESS_DSN","CI_RUN","TEST_HEAD")}
    env["BUILD"]=build
    return subprocess.Popen([sys.executable,"-u","/exp/worker.py"],env=env)


async def wait_for(predicate, process, limit=100):
    async with asyncio.timeout(limit):
        while not predicate():
            if process.poll() is not None:
                raise RuntimeError(f"worker exited {process.returncode}")
            await asyncio.sleep(.2)


def decode_payloads(obj):
    if isinstance(obj,list):
        for value in obj:
            yield from decode_payloads(value)
    if isinstance(obj,dict):
        if "data" in obj and "metadata" in obj and isinstance(obj["data"],str):
            yield base64.b64decode(obj["data"]).decode("utf8", errors="replace")
        for value in obj.values():
            yield from decode_payloads(value)


async def history(handle,name,s):
    h = await handle.fetch_history()
    raw = h.to_json()
    (OUT/f"{name}-history.json").write_text(raw)
    doc = json.loads(raw)
    payloads = list(decode_payloads(doc))
    assert payloads, name
    forbidden = [s["task"]["marker"], s["task"]["call"], s["effects"][0]["receipt"]]
    for token in forbidden:
        assert token not in raw and all(token not in x for x in payloads)
    attrs = [e["activityTaskStartedEventAttributes"] for e in doc["events"] if "activityTaskStartedEventAttributes" in e]
    record(name,"history",{"workflow":handle.id,"run":h.run_id,"activity_starts":attrs,"payloads":payloads})
    return attrs


async def main():
    before_hash=source_hashes()
    name="inspect_"+uuid.uuid4().hex[:10]
    desc={"name":name,"description":"Submit a referenced item for independent verification",
          "mode":"asynchronous","side_effect":"submit","status_source":"lookup","input_schema":{
              "type":"object","properties":{"ref":{"type":"string"}},"required":["ref"],"additionalProperties":False}}
    with connection("PRODUCT_DSN") as product, connection("WITNESS_DSN") as witness:
        product.execute(SCHEMA)
        for scope in CASES:
            marker="REQUEST_MARK_"+uuid.uuid4().hex
            product.execute("INSERT INTO task(scope,descriptor,marker,reader_versions,wrong_pair) VALUES(%s,%s,%s,%s,%s)",
                            (scope,Jsonb(desc),marker,[2] if scope=="incompatible" else [1,2],scope=="wrong_pair"))
            witness.execute("INSERT INTO scenario(scope,name,marker) VALUES(%s,%s,%s)",(scope,name,marker))
    assert before_hash==source_hashes()
    record("run","identity",{"commit":os.environ["TEST_HEAD"],"run":os.environ["CI_RUN"],"namespace":os.environ["NAMESPACE"],
                             "before":before_hash,"registered":name,"after":source_hashes()})
    client=await Client.connect("temporal:7233", namespace=os.environ["NAMESPACE"])
    first=start_worker("writer-v1")
    second=None
    try:
        handles={s:await client.start_workflow(Round.run,s,id="round-"+s,task_queue="product-lab") for s in CASES}
        await wait_for(lambda:all(snapshot(s)["task"]["state"]=="accepted" for s in CASES),first)
        for s in CASES:
            snap=snapshot(s)
            assert counts(snap)==[1,0,0,0,1]
            record(s,"accepted",snap)
        with connection("WITNESS_DSN") as w:
            w.execute("UPDATE scenario SET enabled=true")
        await wait_for(lambda:all(len(snapshot(s)["effects"])==1 for s in CASES),first)
        for s in CASES:
            snap=snapshot(s)
            assert counts(snap)==[1,1,1,0,1] and snap["task"]["settled"] is None
            assert snap["task"]["spent"]==0 and snap["task"]["held"]==3
            assert "tool-return" not in json.dumps(snap["task"]["msg"])
            record(s,"effect_before_kill",snap)
        first.kill()
        assert first.wait(timeout=8)==-9
        with connection("PRODUCT_DSN") as p, connection("WITNESS_DSN") as w:
            p.execute("UPDATE task SET active=false WHERE scope='cancel'")
            w.execute("UPDATE scenario SET visible=true WHERE scope IN ('known','wrong_pair','incompatible')")
        second=start_worker("reader-v2")
        expected={"known":"delivered","unknown":"unknown","cancel":"unknown",
                  "incompatible":"version_quarantine","wrong_pair":"rejected_pair"}
        for s in CASES:
            outcome=await asyncio.wait_for(handles[s].result(),90)
            snap=snapshot(s)
            record(s,"reentered",snap)
            assert snap["task"]["state"]==outcome==expected[s],(s,outcome)
            known=s=="known"
            assert counts(snap)==[1,1,1,int(known),1+int(known)],(s,counts(snap))
            if s in ("unknown","cancel"):
                assert (snap["task"]["held"],snap["task"]["spent"])==(3,0)
            else:
                assert (snap["task"]["held"],snap["task"]["spent"])==(0,1)
            old,new=events(snap,"attempt")
            assert old["pid"]==first.pid and new["pid"]==second.pid and old["pid"]!=new["pid"]
            assert [old["attempt"],new["attempt"]]==[1,2] and [old["build"],new["build"]]==["writer-v1","reader-v2"]
            assert all(old[k]==new[k] for k in ("activity","run","wf"))
            attrs=await history(handles[s],s,snap)
            assert any(int(a.get("attempt",1))==2 for a in attrs)
            if known:
                first_call,second_call=events(snap,"model")
                original=first_call["reply"]["tool_calls"][0]["id"]
                tool,=[m for m in second_call["request"]["messages"] if m["role"]=="tool"]
                receipt=snap["effects"][0]["receipt"]
                assert tool["tool_call_id"]==original==snap["task"]["call"] and receipt in tool["content"]
                assert events(snap,"delivery")[0]["receipt"]==receipt
                checkpoint,=events(snap,"checkpoint")
                resumed,=events(snap,"resumed")
                assert checkpoint["sdk_run"]!=resumed["sdk_run"]
                assert checkpoint["conversation"]==resumed["conversation"]
        with connection("WITNESS_DSN") as w:
            w.execute("UPDATE scenario SET visible=true WHERE scope='cancel'")
        for n in (1,2):
            h=await client.start_workflow(Notice.run,"cancel",id=f"notice-{n}",task_queue="product-lab")
            assert await asyncio.wait_for(h.result(),25)=="cancelled_settled"
            snap=snapshot("cancel")
            record("cancel",f"late_{n}",snap)
            await history(h,f"late-{n}",snap)
            assert counts(snap)==[1,1,1,0,1] and (snap["task"]["held"],snap["task"]["spent"])==(0,1)
        assert [x["new"] for x in events(snap,"settle")]==[True,False]
        print("OBSERVED",len(CASES),"cases; 5 interrupted activities on one killed worker; 2 notices",
              flush=True)
    finally:
        for child in (first,second):
            if child and child.poll() is None:
                child.kill()
                child.wait(timeout=10)


if __name__=="__main__":
    asyncio.run(main())
