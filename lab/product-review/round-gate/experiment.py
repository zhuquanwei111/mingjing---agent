"""Independent driver. Assertions combine product facts, actual HTTP arrivals/charges and engine histories."""
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from psycopg.types.json import Jsonb
from temporalio.client import Client

import driver as original
from gate_flow import DuplicateEntry, GateRound, MAIN, SIDE
from gate_worker import SCHEMA

CASES = ("legacy","guarded","active","revoked")
OUT = Path("/out")


def record(case, stage, data):
    with (OUT/"raw.jsonl").open("a") as file:
        print(json.dumps({"case":case,"stage":stage,"data":data},sort_keys=True),file=file)


def snapshot(scope):
    snap = original.snapshot(scope)
    with original.connection("PRODUCT_DSN") as c:
        snap["rounds"] = original.subset(c,"SELECT * FROM model_round WHERE operation=%s ORDER BY round_no",
                                         (snap["task"]["model_operation"],))
    with original.connection("WITNESS_DSN") as c:
        snap["model_fees"] = original.subset(c,"SELECT * FROM model_fee WHERE scope=%s ORDER BY arrival",(scope,))
    return snap


def initialize():
    name = "inspect_"+uuid.uuid4().hex[:10]
    first_marker = "REQUEST_MARK_"+uuid.uuid4().hex
    desc = {"name":name,"description":"Submit a referenced item for independent verification",
            "adapter":"external_receipt_v1","mode":"asynchronous","side_effect":"submit","status_source":"lookup",
            "input_schema":{"type":"object","properties":{"ref":{"type":"string"}},
                            "required":["ref"],"additionalProperties":False}}
    with original.connection("PRODUCT_DSN") as product,original.connection("WITNESS_DSN") as witness:
        product.execute(original.SCHEMA)
        product.execute(SCHEMA)
        for scope in CASES:
            marker = first_marker if scope in ("legacy","guarded") else "REQUEST_MARK_"+uuid.uuid4().hex
            product.execute("""INSERT INTO task(scope,descriptor,marker,writer_format,wrong_pair,model_operation)
                         VALUES(%s,%s,%s,1,false,%s)""",(scope,Jsonb(desc),marker,str(uuid.uuid4())))
            witness.execute("INSERT INTO scenario(scope,name,marker,enabled) VALUES(%s,%s,%s,true)",
                            (scope,name,marker))
    record("run","identity",{"head":os.environ["TEST_HEAD"],"run":os.environ["CI_RUN"],
            "namespace":os.environ["NAMESPACE"],"task_model_ceiling":2,"tool_reserve":3,"schema":SCHEMA})


def start(queue):
    env = {k:v for k,v in os.environ.items() if k not in ("WITNESS_DSN","CI_RUN","TEST_HEAD")}
    env["GATE_QUEUE"] = queue
    return subprocess.Popen([sys.executable,"-u","/exp/round-gate/gate_worker.py"],env=env)


async def until(test, children):
    async with asyncio.timeout(100):
        while not test():
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"worker exited {child.pid} {child.returncode}")
            await asyncio.sleep(.15)


def observed(s,kind):
    return original.received(s,kind)


def events(s,kind):
    return original.logged(s,kind)


def check_counts(s, tool, effects, fees, models, delivery):
    assert original.counts(s)==[tool,effects,fees,delivery,len(models)],(original.counts(s),models)
    wire = [e for e in s["observed"] if e["kind"]=="model"]
    assert [x["round_no"] for x in s["model_fees"]]==models
    assert [x["arrival"] for x in s["model_fees"]]==[e["seq"] for e in wire]
    assert all(x["units"]==1 for x in s["model_fees"]+s["fees"])
    assert [e["detail"]["logical_round"] for e in wire]==models
    if tool:
        arrivals = [e for e in s["observed"] if e["kind"]=="arrival"]
        assert [x["arrival"] for x in s["fees"]]==[e["seq"] for e in arrivals]
        assert all(e["detail"]["op"]==s["task"]["op"]==s["effects"][0]["op"]==s["fees"][0]["op"]
                   for e in arrivals)
        assert arrivals[0]["detail"]["call"]==s["task"]["call"]
        assert arrivals[0]["detail"]["name"]==s["task"]["descriptor"]["name"]
        assert arrivals[0]["detail"]["input"]=={"ref":s["task"]["marker"]}
    if s["task"]["scope"]=="legacy":
        assert not s["rounds"] and all(x["dispatch"] is None for x in s["model_fees"])
    else:
        for entry,fee in zip(wire,s["model_fees"],strict=True):
            claim, = [r for r in s["rounds"] if r["round_no"]==fee["round_no"]]
            assert entry["detail"]["wire"]=={"Dispatch":claim["dispatch"],"Round":str(claim["round_no"]),
                                            "Operation":s["task"]["model_operation"]}
            assert claim["dispatch"]==fee["dispatch"]


def balances(s, *expected):
    actual=[(r["round_no"],r["phase"],r["held"],r["spent"]) for r in s["rounds"]]
    assert actual==list(expected),(actual,expected)
    assert s["task"]["model_slots"]==len(expected)


def barrier(name):
    with original.connection("WITNESS_DSN") as c:
        c.execute("UPDATE barrier SET opened=true WHERE name=%s",(name,))


async def save_history(handle, scope, tag):
    hist = await handle.fetch_history()
    raw = hist.to_json()
    (OUT/f"{tag}-history.json").write_text(raw)
    s = snapshot(scope)
    doc = json.loads(raw)
    payloads = list(original.decode_payloads(doc))
    assert payloads
    forbidden = [s["task"]["marker"],s["task"]["descriptor"]["name"],"Request the registered asynchronous",
                 '"tool_calls"','"messages"','"tool_call_id"']
    for m in observed(s,"model"):
        forbidden.extend(call["id"] for call in m["reply"].get("tool_calls",[]))
    forbidden.extend(e["receipt"] for e in s["effects"])
    if s["task"]["call"]:
        forbidden.append(s["task"]["call"])
    assert all(sensitive not in raw and all(sensitive not in p for p in payloads) for sensitive in forbidden)
    record(scope,"history",{"id":handle.id,"run":hist.run_id,"file":f"{tag}-history.json",
            "sha256":hashlib.sha256(raw.encode()).hexdigest(),"events":len(doc["events"]),
            "payloads":payloads,"forbidden_markers_checked":len(forbidden)})
    return doc,hist.run_id


async def main():
    initialize()
    client = await Client.connect("temporal:7233",namespace=os.environ["NAMESPACE"])
    first,side = start(MAIN),start(SIDE)
    workers=[first,side]
    handles={}
    try:
        for scope in CASES[:2]:
            handles[scope] = await client.start_workflow(GateRound.run,scope,id="gate-"+scope,task_queue=MAIN)
        await until(lambda:all(len(observed(snapshot(s),"reply_barrier"))==1 for s in CASES[:2]),workers)
        for s in CASES[:2]:
            snap = snapshot(s)
            check_counts(snap,0,0,0,[1],0)
            assert snap["task"]["msg"] is None and snap["task"]["op"] is None
            assert snap["task"]["model_slots"]==1
            assert (snap["task"]["held"],snap["task"]["spent"])==(0,0)
            if s=="guarded":
                balances(snap,(1,"claimed",1,0))
            record(s,"charged_no_reply",snap)
        assert observed(snapshot("legacy"),"model")[0]["request"]==observed(snapshot("guarded"),"model")[0]["request"]
        async def duplicate(label):
            h = await client.start_workflow(DuplicateEntry.run,"guarded",id="dup-"+label,task_queue=SIDE)
            assert await asyncio.wait_for(h.result(),30)=="suppressed"
            await save_history(h,"guarded","dup-"+label)
        await duplicate("inflight")
        first.kill()
        assert first.wait(timeout=10)==-9
        record("run","kill",{"pid":first.pid,"exit":first.returncode})
        replacement = start(MAIN)
        workers.append(replacement)
        alive=[replacement,side]
        await until(lambda:len(observed(snapshot("legacy"),"reply_barrier"))==2,alive)
        barrier("drop_model")
        for scope,outcome in (("legacy","legacy_unknown"),("guarded","model_unknown")):
            assert await asyncio.wait_for(handles[scope].result(),60)==outcome
        await duplicate("after-unknown")
        for s in CASES[:2]:
            snap=snapshot(s)
            count=2 if s=="legacy" else 1
            check_counts(snap,0,0,0,[1]*count,0)
            assert snap["task"]["model_slots"]==count and snap["task"]["msg"] is None and snap["task"]["op"] is None
            assert (snap["task"]["held"],snap["task"]["spent"])==(0,0)
            p,q=events(snap,"attempt")
            assert (p["attempt"],q["attempt"],p["pid"],q["pid"])==(1,2,first.pid,replacement.pid)
            assert all(p[k]==q[k] for k in ("wf","run","activity"))
            doc,run=await save_history(handles[s],s,s)
            assert p["run"]==run and p["wf"]==handles[s].id
            assert [e["activityTaskScheduledEventAttributes"]["activityId"] for e in doc["events"]
                    if "activityTaskScheduledEventAttributes" in e]==[p["activity"]]
            assert any(int(e.get("activityTaskStartedEventAttributes",{}).get("attempt",1))==2 for e in doc["events"])
            if s=="guarded":
                balances(snap,(1,"unknown",1,0))
                assert [r["pid"] for r in events(snap,"duplicate_entry")]==[side.pid]*2
                assert [r["pid"] for r in events(snap,"duplicate_claim")]==[side.pid,replacement.pid,side.pid]
            record(s,"final",snap)
        for s in CASES[2:]:
            handles[s]=await client.start_workflow(GateRound.run,s,id="gate-"+s,task_queue=MAIN)
        await until(lambda:all(snapshot(s)["task"]["state"]=="tool_unknown" for s in CASES[2:]),alive)
        prior={}
        for s in CASES[2:]:
            snap=snapshot(s)
            check_counts(snap,1,1,1,[1],0)
            balances(snap,(1,"confirmed",0,1))
            assert (snap["task"]["held"],snap["task"]["spent"],snap["task"]["settled"])==(3,0,None)
            assert observed(snap,"lookup")==[{"op":snap["task"]["op"],"found":False}]
            assert [e["kind"] for e in snap["observed"] if e["kind"] in ("effect","lookup")]==["effect","lookup"]
            assert (await handles[s].describe()).status.name=="RUNNING"
            prior[s]=snap["task"]["msg"]
            record(s,"effect_unknown_running",snap)
        with original.connection("PRODUCT_DSN") as c:
            c.execute("UPDATE task SET active=false WHERE scope='revoked'")
        with original.connection("WITNESS_DSN") as c:
            c.execute("UPDATE scenario SET visible=true WHERE scope IN ('active','revoked')")
        for s in CASES[2:]:
            await asyncio.gather(*(handles[s].signal(GateRound.notice,label) for label in ("notice-A","notice-B")))
        await until(lambda:all(len(observed(snapshot(s),"reply_barrier"))==2 for s in CASES[2:]),alive)
        for s in CASES[2:]:
            snap=snapshot(s)
            check_counts(snap,1,1,1,[1],0)
            assert [q["found"] for q in observed(snap,"lookup")]==[False,True,True]
            assert len(events(snap,"settle"))==0
            assert sorted(x["pid"] for x in events(snap,"notice"))==sorted([side.pid,replacement.pid])
            assert sorted(x["notice"] for x in events(snap,"notice"))==["notice-A","notice-B"]
            assert all(x["op"]==snap["task"]["op"] for x in observed(snap,"lookup"))
            record(s,"both_lookups_before_release",snap)
        barrier("release_lookups")
        for s in CASES[2:]:
            active=s=="active"
            result=await asyncio.wait_for(handles[s].result(),75)
            snap=snapshot(s)
            assert snap["task"]["state"]==result==("delivered" if active else "revoked_settled")
            check_counts(snap,1,1,1,[1,2] if active else [1],int(active))
            assert (snap["task"]["held"],snap["task"]["spent"])==(0,1)
            assert snap["task"]["settled"]==snap["effects"][0]["receipt"]
            assert snap["task"]["active"]==active and snap["task"]["msg"]==prior[s]
            assert sorted(x["new"] for x in events(snap,"settle"))==[False,True]
            assert all(x["active"]==active for x in events(snap,"settle"))
            doc,run=await save_history(handles[s],s,s)
            signals = [e for e in doc["events"] if "workflowExecutionSignaledEventAttributes" in e]
            assert len(signals)==2
            assert all(x["wf"]==handles[s].id and x["run"]==run for x in events(snap,"notice")+events(snap,"attempt"))
            if active:
                balances(snap,(1,"confirmed",0,1),(2,"confirmed",0,1))
                old,new=observed(snap,"model")
                call=old["reply"]["tool_calls"][0]["id"]
                tool,=[m for m in new["request"]["messages"] if m["role"]=="tool"]
                assert call==snap["task"]["call"]==tool["tool_call_id"]
                assert snap["effects"][0]["receipt"] in tool["content"]
                resumed,=events(snap,"resumed")
                cp,=events(snap,"checkpoint")
                assert cp["conversation"]==resumed["conversation"] and cp["sdk_run"]!=resumed["sdk_run"]
                assert cp["call"]==resumed["call"]==call
                assert len(events(snap,"duplicate_claim"))==1
                delivery,=observed(snap,"delivery")
                assert delivery["delivery"]==snap["task"]["delivery_claim"] and delivery["op"]==snap["task"]["op"]
                assert delivery["receipt"]==snap["task"]["settled"] and delivery["call"]==call
                assert delivery["output"]==new["reply"]["content"]
            else:
                balances(snap,(1,"confirmed",0,1))
                assert snap["task"]["delivery_claim"] is None and not events(snap,"resumed")
            record(s,"final",snap)
        print("PASS four scopes, six histories, two overlapping notices per late-receipt scope",flush=True)
    finally:
        for process in workers:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


if __name__=="__main__":
    asyncio.run(main())
