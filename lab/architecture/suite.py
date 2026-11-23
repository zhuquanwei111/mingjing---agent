"""Identical black-box scenarios, independent receivers and failure injection."""
import asyncio, hashlib, importlib, json, os, secrets, subprocess, sys, threading, time, traceback, uuid
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from temporalio.client import Client
from ports import request
from shared_input import BASE, challenge
import witness as w
route=os.environ["LAB_ROUTE"]
app=importlib.import_module(route+".runtime")
workers=[]; scopes=[]; handles=[]
scope_namespace=os.environ["LAB_NS"]
names=[s["name"] for s in BASE]
prompt="Use read_manifest with resource bundle first. Use its returned value as key for item_state. After receiving item_state, finish with a brief answer. Call one tool per turn."
def emit(tag,data):print(tag,json.dumps(data,ensure_ascii=False,default=str),flush=True)
def check(value,why):
    if not value:raise AssertionError(why)
def start_worker():
    worker=subprocess.Popen([sys.executable,"/lab/worker.py"])
    workers.append(worker);emit("WORKER_START",worker.pid)
    return worker
def kill_worker():
    p=workers[-1];p.kill();p.wait(15);emit("WORKER_KILL",{"pid":p.pid,"rc":p.returncode})
def scope(label,**cfg):
    c=label+"-"+secrets.token_hex(4)
    scopes.append(c);app.prepare(c);w.configuration(c,key="fixture-"+secrets.token_hex(12),**cfg)
    for n in names:app.allow_tool(c,n)
    return c
def count(c,act):return sum(k==act for k,d in w.events(c))
async def wait_for(c,predicate):
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        if predicate(w.events(c)):return
        await asyncio.sleep(.10)
    raise TimeoutError("fixture barrier "+c)
async def start(c,kind,args=None):
    h=await client.start_workflow(route.upper()+"Execution",{"case":c,"kind":kind,"args":args or {}},
            id=c+"-"+kind+"-"+uuid.uuid4().hex[:8],task_queue=scope_namespace,execution_timeout=timedelta(seconds=180))
    handles.append((c,h));return h
async def run(c,kind,args=None):
    h=await start(c,kind,args)
    return await asyncio.wait_for(h.result(),185)
class API(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def do_POST(self):
        try:
            data=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            answer=app.tool(data["case"],data["name"],data["args"],self.headers.get("Authorization",""))
            status=200
        except Exception as exc:
            answer={"name":type(exc).__name__,"reason":str(exc)[:160]};status=422 if "valid" in str(exc).lower() else 403
        raw=json.dumps(answer).encode();self.send_response(status);self.end_headers();self.wfile.write(raw)
def direct(c,n,data):
    return request("http://127.0.0.1:8766/tool",{"case":c,"name":n,"args":data},{"Authorization":os.environ["LAB_TOKEN"]})
def agent_args(backend="controlled",offered=names,user=prompt):
    return {"backend":backend,"prompt":user,"names":offered}
async def v01():
    for tag,opts,order,expected in [("chain",{},names,names),("alternate",{"key_first":True},names[::-1],["item_state"]),("stop",{"stop":True},names,[])]:
        c=scope(tag,**opts)
        result=await run(c,"agent",agent_args(offered=order,user=prompt if tag=="chain" else ("Already have key "+w.settings(c)["key"] if tag=="alternate" else "Stop now")))
        events=w.events(c)
        got=[d["name"] for k,d in events if k=="tool"]
        check(got==expected and result["finished"] and count(c,"model")==len(expected)+1,(got,result))
        if tag=="chain":
            model_inputs=[d for k,d in events if k=="model"]
            check(any(m["role"]=="tool" and w.settings(c)["key"] in str(m) for m in model_inputs[1]["messages"]),"missing runtime key")
            check("ready" in str(model_inputs[2]["messages"]),"result did not return")
    c=scope("real")
    result=await run(c,"agent",agent_args(backend="real"))
    records=w.events(c); inputs=[d for k,d in records if k=="model"]
    selected=[d["name"] for k,d in records if k=="tool"]
    check(bool(selected) and any(m.get("role")=="tool" for d in inputs[1:] for m in d["messages"]),"real model had no valid roundtrip")
    emit("REAL_MODEL",{"tools":selected,"result":result,"turns":len(inputs)})

async def v02():
    spec=challenge(); data={k:"value-"+k for k in spec["fields"]}; name=spec["name"]
    c=scope("new",challenge={"name":name,"args":data})
    app.install(spec,True);app.allow_tool(c,name)
    expected={"value":json.dumps(data,sort_keys=True)}
    check(direct(c,name,data)==expected,"direct result")
    check(await run(c,"tool",{"name":name,"data":data})==expected,"workflow result")
    check(count(c,"model")==0,"deterministic path invoked model")
    await run(c,"agent",agent_args(offered=[name],user="Verify the two supplied fields "+json.dumps(data)))
    msgs=[d for k,d in w.events(c) if k=="model"][-1]["messages"]
    check(any(m["role"]=="tool" and json.loads(m["content"])==expected for m in msgs),"agent result")
    other={**spec,"name":name+"_draft"};app.install(other,False);app.allow_tool(c,other["name"])
    for bad,body in [(name,{}),(other["name"],data),(name,data)]:
        if bad==name and body:app.allow_tool(c,name,False)
        for channel in ("api","flow","agent"):
            guard={"name":bad,"args":body}
            w.configuration(c,challenge=guard)
            try:
                if channel=="api":direct(c,bad,body)
                elif channel=="flow":await run(c,"tool",{"name":bad,"data":body})
                else:await run(c,"agent",agent_args(offered=[bad],user="Verify"))
            except Exception:pass
            check(count(c,"tool")==3,"negative reached external tool via "+channel)
    emit("EXTENSION",{"spec":spec,"receiver_calls":count(c,"tool"),"runtime_changes_after_challenge":0})
async def v03():
    stages=["read","model","tool_out","commit","deliver"]
    observed=["read","model","tool","commit","deliver"]
    for mode in ("staged","continuous"):
        good=scope("allow-"+mode)
        check(await run(good,mode,stages)=="ok" and all(count(good,s)==1 for s in observed),"permissions positive")
        for idx,action in enumerate(stages):
            c=scope("revoke-"+mode+"-"+action,hold=action)
            h=await start(c,mode,stages)
            await wait_for(c,lambda ev:any(k=="barrier" for k,d in ev))
            app.revoke(c,action)
            w.configuration(c,hold="")
            check(await h.result()=="denied" and app.state(c)["product"]=="denied","missing denial")
            counts=[count(c,s) for s in observed]
            check(counts==[1]*idx+[0]*(5-idx),counts)
            hist=await h.fetch_history()
            check(w.settings(c)["key"].encode() not in b"".join(e.SerializeToString() for e in hist.events),"sensitive marker in history")
async def v04():
    for mode,unverifiable in (("confirm",False),("unknown",True),("cancel",True)):
        c=scope(mode,hold="after_effect",lose=True,unverifiable=unverifiable)
        h=await start(c,"supplier")
        await wait_for(c,lambda ev:any(k=="barrier" for k,d in ev))
        with w.db() as db:check(db.execute("select count(*) from effects where scope=%s",(c,)).fetchone()[0]==1,"commit-before-kill")
        kill_worker()
        w.configuration(c,hold="")
        if mode=="cancel":
            app.cancel(c);await h.cancel()
        start_worker()
        if mode=="cancel":
            try:await h.result()
            except Exception:pass
            app.callback(c,True);app.callback(c,True)
            desc=await h.describe()
            check("CANCEL" in desc.status.name,"engine cancel not terminal")
        else:
            outcome=await h.result()
            check(outcome==("unknown" if unverifiable else "confirmed"),outcome)
            check(count(c,"lookup")>=1,"retry did not query")
        events=w.events(c);state=app.state(c)
        check(count(c,"supplier_send")==1 and count(c,"downstream")==int(mode=="confirm"),events)
        check(state["op"][1]==int(mode!="unknown"),state)
        if mode=="cancel":check(state["product"]=="cancelled",state)
        with w.db() as db:check(db.execute("select count(*) from effects where scope=%s",(c,)).fetchone()[0]==1,"duplicate remote effect")
        emit("RECOVERY",{"mode":mode,"account":state,"events":[k for k,d in events]})
async def v05():
    for items,version,validator,ok in [(["left"],"v1",True,False),(["left","right"],"v0",True,False),(["left","right"],"v1",False,False),(["left","right"],"v1",True,True)]:
        c=scope("quality");data={"items":items,"version":version,"validator":validator}
        check(direct(c,"read_manifest",{"resource":"bundle"})=={"value":w.settings(c)["key"]},"tool success")
        result=await run(c,"quality",data)
        check(result==app.state(c)["product"]==("succeeded" if ok else "review"),result)
        check(count(c,"commit")==count(c,"deliver")==int(ok),"incorrect delivery")
        emit("QUALITY",{"input":data,"rule":"v1","state":result})
async def v06():
    c=scope("race",hold="reserved");h=await start(c,"family",["one","two","three"])
    await wait_for(c,lambda ev:sum(k=="budget_denied" for k,d in ev)==2 and any(k=="barrier" for k,d in ev))
    state=app.state(c);check(state["held"]==3 and state["spent"]==0,state)
    w.configuration(c,hold="");out=await h.result()
    check(sorted(out)==["blocked","blocked","settled"],out)
    winner=["one","two","three"][out.index("settled")]
    check(await run(c,"child",winner)=="settled","duplicate")
    check(await run(c,"child","extra")=="settled" and await run(c,"child","over")=="blocked","remaining quota")
    state=app.state(c);check(state["spent"]==4 and state["held"]==0 and count(c,"charge")==2,state)
    for hold in ("reserved","charged"):
        c=scope("late-"+hold,hold=hold);h=await start(c,"family",["only"])
        await wait_for(c,lambda ev:any(k=="barrier" for k,d in ev))
        state=app.state(c);check(state["held"]==3,state)
        kill_worker();app.cancel(c);w.configuration(c,hold="");start_worker()
        out=await h.result()
        check(await run(c,"child","late")=="blocked","cancel allowed dispatch")
        state=app.state(c)
        check(count(c,"charge")==int(hold=="charged") and state["product"]=="cancelled",state)
        check((state["spent"],state["held"])==((2,0) if hold=="charged" else (0,3)),state)
        check(out==(["settled"] if hold=="charged" else ["unknown"]),out)
        emit("SHARED_BUDGET",{"hold":hold,"state":state,"summary":out})
async def main():
    global client
    server=w.start(); api=ThreadingHTTPServer(("127.0.0.1",8766),API);threading.Thread(target=api.serve_forever,daemon=True).start()
    app.setup()
    for spec in BASE:app.install(spec,True)
    client=await Client.connect("temporal:7233",namespace=scope_namespace)
    start_worker();scores={}
    try:
        for func in (v01,v02,v03,v04,v05,v06):
            before=len(scopes);id=func.__name__.upper()
            try:
                await func();scores[id]="pass"
            except Exception as exc:
                scores[id]="incomplete";traceback.print_exc()
            emit("GROUP",{"group":id,"result":scores[id]})
            for c in scopes[before:]:
                with w.db() as db:
                    effects=db.execute("select op,kind from effects where scope=%s",(c,)).fetchall()
                emit("RAW",{"case":c,"events":w.events(c),"effects":effects,"account":app.state(c)})
            for c,h in handles:
                if c in scopes[before:]:
                    hist=await h.fetch_history()
                    emit("HISTORY",{"case":c,"workflow_id":h.id,"events":[e.event_type for e in hist.events]})
        emit("RESULT",{"route":route,"groups":scores})
        return int(any(v!="pass" for v in scores.values()))
    finally:
        if workers[-1].poll() is None:kill_worker()
        api.shutdown();server.shutdown()
if __name__=="__main__":sys.exit(asyncio.run(main()))

