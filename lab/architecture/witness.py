"""Independent receivers, a durable synthetic supplier and an instrumented model endpoint."""
import json, os, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import psycopg
from psycopg.types.json import Jsonb
from ports import request

DSN=os.environ["LAB_WITNESS_DSN"]
def db(): return psycopg.connect(DSN)
def record(c, action, data):
    with db() as con:
        con.execute("insert into observations(scope,action,data) values (%s,%s,%s)",(c,action,Jsonb(data)))
def events(c):
    with db() as con:
        return con.execute("select action,data from observations where scope=%s order by id",(c,)).fetchall()
def settings(c):
    with db() as con:
        row=con.execute("select options from fixtures where scope=%s",(c,)).fetchone()
    return row[0] if row else {}
def configuration(c, **cfg):
    with db() as con:
        con.execute("insert into fixtures values (%s,%s) on conflict(scope) do update set options=fixtures.options||excluded.options",(c,Jsonb(cfg)))
def gate_fixture(c, name):
    cfg=settings(c)
    if cfg.get("hold")!=name:return
    if cfg.get("after_first_tool") and not any(k=="tool" for k,_ in events(c)):return
    record(c,"barrier",{"name":name})
    deadline=time.monotonic()+70
    while settings(c).get("hold")==name:
        if time.monotonic()>deadline: raise TimeoutError(name)
        time.sleep(.08)
def model_reply(c, backend, body):
    msgs=body["messages"]
    funcs=[s["function"] for s in body.get("tools",[])]
    record(c,"model",{"backend":backend,"messages":msgs,"tools":[x["name"] for x in funcs]})
    if backend=="real":
        reply=request("http://lab-model:11434/v1/chat/completions",body)
    else:
        outputs=[m for m in msgs if m["role"]=="tool"]
        conf=settings(c)
        target=conf.get("challenge")
        next_call=None
        if funcs and not conf.get("stop"):
            if target and not outputs:
                next_call=(target["name"],target["args"])
            elif not target and not outputs and conf.get("key_first"):
                next_call=("item_state",{"key":conf["key"]})
            elif not target and not outputs:next_call=("read_manifest",{"resource":"bundle"})
            elif not target and len(outputs)==1 and not conf.get("key_first"):
                val=json.loads(outputs[-1]["content"])
                next_call=("item_state",{"key":val["value"]})
        msg={"role":"assistant","content":"Finished the requested verification."}
        if next_call:
            name,args=next_call
            msg={"role":"assistant","content":None,"tool_calls":[{"id":"call_"+uuid.uuid4().hex[:12],"type":"function","function":{"name":name,"arguments":json.dumps(args)}}]}
        reply={"id":"chatcmpl-lab","object":"chat.completion","created":int(time.time()),"model":body["model"],"choices":[{"index":0,"message":msg,"finish_reason":"tool_calls" if next_call else "stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}
    record(c,"model_reply",{"backend":backend,"message":reply["choices"][0]["message"]})
    return reply
plugin_handlers={}
def deploy_plugin(name,handler):
    if name in plugin_handlers:raise RuntimeError("duplicate external module")
    plugin_handlers[name]=handler

def receive(c, a, data):
    cfg=settings(c)
    if a=="tool":
        record(c,a,data)
        name=data["name"]; args=data["args"]
        if name=="read_manifest": return {"value":cfg["key"]}
        if name=="item_state" and "quality" in cfg and args.get("key")==cfg["key"]:
            return {"value":json.dumps(cfg["quality"])}
        if name=="item_state": return {"value":"ready" if args.get("key")==cfg["key"] else "invalid-key"}
        if name not in plugin_handlers:raise KeyError("missing capability implementation")
        return {"value":plugin_handlers[name](args)}
    if a=="quality_policy":
        record(c,a,{"available":cfg.get("validator",True)})
        if not cfg.get("validator",True):raise RuntimeError("validator unavailable")
        return {"required":["left","right"],"version":"v1"}
    if a in ("supplier_send","charge"):
        op=data["op"]
        with db() as con:
            con.execute("insert into observations(scope,action,data) values(%s,%s,%s)",(c,a,Jsonb(data)))
            con.execute("insert into effects values(%s,%s,%s) on conflict do nothing",(c,op,a))
        return {"known":not cfg.get("lose"),"units":2}
    if a in ("lookup","charge_lookup"):
        record(c,a,data)
        with db() as con:
            exists=con.execute("select 1 from effects where scope=%s and op=%s",(c,data["op"])).fetchone()
        return {"known":bool(exists) and (a=="charge_lookup" or not cfg.get("unverifiable")),"units":2}
    record(c,a,data)
    return {"value":cfg.get("key","synthetic"),"ok":True}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        try:
            body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path=="/event": out=receive(body["case"],body["action"],body["data"])
            elif self.path=="/barrier":
                gate_fixture(body["case"],body["name"]);out={"ok":True}
            else:
                _,case,backend,*_=self.path.split("/")
                out=model_reply(case,backend,body)
            code=200
        except Exception as exc:
            out={"error":type(exc).__name__,"detail":str(exc)[:450]};code=500
        raw=json.dumps(out).encode()
        self.send_response(code);self.send_header("Content-type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
def start():
    with db() as con:
        con.execute("create table fixtures(scope text primary key,options jsonb not null); create table observations(id bigserial primary key,scope text,action text,data jsonb); create table effects(scope text,op text,kind text,primary key(scope,op))")
    server=ThreadingHTTPServer(("127.0.0.1",8765),Handler); threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
