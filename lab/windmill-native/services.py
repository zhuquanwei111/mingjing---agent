"""Isolated loopback product ledger and independent simulated async provider."""
import json
import sqlite3
import sys
import uuid
from model_gate import forward
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

OUT = Path("/tmp/wmn-evidence")
PRODUCT, RECEIVER = "http://127.0.0.1:8501", "http://127.0.0.1:8502"


def http(url, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with urlopen(req, timeout=20) as res:
            data = res.read().decode().strip()
    except HTTPError as exc:
        raise RuntimeError(f"{req.get_method()} {url.split('?')[0]} {exc.code} {exc.read().decode()[:1100]}") from exc
    try:
        return json.loads(data)
    except ValueError:
        return data


def database(name):
    db = sqlite3.connect(OUT / f"{name}.db", timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def start(name):
    db = database(name)
    db.execute("pragma journal_mode=wal")
    if name == "product":
        db.executescript("""
        create table ops(op text primary key, sent integer default 0, held integer default 3,
                         spent integer default 0, canceled integer default 0, receipt text, version integer default 1, delivered integer default 0, call_id text, engine_call_id text, reader integer default 1,
                         quarantine integer default 0, prompt_private text, result_private text);
        create table model_attempts(op text, allowed integer, body text, at text default current_timestamp);
        create table model_intents(op text, turn integer, state text, primary key(op,turn));
        create table entries(op text, job text, claim integer, at text default current_timestamp);
        """)
    else:
        db.executescript("""
        create table jobs(op text primary key, completed integer default 0, visible integer default 0, receipt text, result_private text);
        create table model_http(raw text, op text, fee integer default 0, at text default current_timestamp);
        create table models(op text, body text, call_id text, paired integer, at text default current_timestamp);
        create table events(op text, kind text, value text, at text default current_timestamp);
        """)
    db.close()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, obj, status=200, stream=False, prohibit_retry=False):
            data = obj.encode() if stream else json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/event-stream" if stream else "application/json")
            self.send_header("Content-Length", str(len(data)))
            if prohibit_retry:
                self.send_header("x-should-retry","false")
            self.end_headers()
            self.wfile.write(data)

        def process(self):
            path = self.path.strip("/").split("/")
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}"
            db = database(name)
            try:
                ingress=None
                if path==["v1","chat","completions"] and name=="receiver":
                    ingress=db.execute("insert into model_http(raw) values(?)",(raw.decode(errors="replace"),)).lastrowid
                body=json.loads(raw)
                if path == ["health"]:
                    return self.reply("ready")
                if path==["v1","chat","completions"] and name=="product":
                    return forward(self,db,body,raw,RECEIVER)
                if path == ["v1", "chat", "completions"] and name == "receiver":
                    return self.model(db, body, ingress)
                action, op = path
                db.execute("begin immediate")
                if name == "receiver":
                    value, code = receiver_action(db, action, op, body)
                else:
                    value, code = product_action(db, action, op, body)
                db.commit()
                return self.reply(value, code)
            except Exception as exc:
                db.rollback()
                self.reply({"error": repr(exc)}, 500)
            finally:
                db.close()

        def model(self, db, body, ingress):
            messages = body["messages"]
            op = next(m["content"] for m in messages if m["role"] == "user")
            if isinstance(op, list):
                op = next(item["text"] for item in op if item["type"] == "text")
            db.execute("update model_http set op=? where rowid=?",(op,ingress))
            if op.startswith(("lossraw_","lossguarded_")):
                # A real TCP close after committing a simulated bill, before any reply bytes.
                db.execute("update model_http set fee=1 where rowid=?",(ingress,))
                self.close_connection=True
                self.connection.shutdown(2)
                self.connection.close()
                return
            if op.startswith(("retrydefault_","retryprotected_")):
                db.execute("update model_http set fee=1 where rowid=?",(ingress,))
                return self.reply({"error":"accepted synthetic charge then HTTP 503"},503,
                                  prohibit_retry=op.startswith("retryprotected_"))
            tool = next((m for m in messages if m["role"] == "tool"), None)
            call_id = "call_" + uuid.uuid4().hex
            paired = False
            if tool:
                original = db.execute("select call_id from models where op=? order by rowid limit 1",(op,)).fetchone()
                job = db.execute("select receipt from jobs where op=?",(op,)).fetchone()
                calls = [call for message in messages for call in message.get("tool_calls",[]) if message["role"]=="assistant"]
                raw = tool["content"]
                if isinstance(raw, list):
                    raw = next((p["text"] for p in raw if p["type"]=="text"),None)
                try:
                    value = json.loads(raw)
                except (ValueError,TypeError):
                    value = raw
                paired = bool(original and job and job[0] and tool.get("tool_call_id")==original[0]
                              and len(calls)==1 and calls[0]["id"]==original[0]
                              and calls[0]["function"]["name"]=="async_operation" and value==job[0])
                delta, finish = {"role":"assistant","content":("complete_"+job[0]) if paired else "unpaired"}, "stop"
            else:
                fn = body["tools"][0]["function"]["name"]
                delta = {"role":"assistant","tool_calls":[{"index":0,"type":"function","id":call_id,
                         "function":{"name":fn,"arguments":"{}"}}]}
                finish = "tool_calls"
            db.execute("insert into models(op,body,call_id,paired) values(?,?,?,?)",
                       (op,json.dumps(body),call_id,paired))
            frames = [{"choices":[{"index":0,"delta":delta,"finish_reason":None}]},
                      {"choices":[{"index":0,"delta":{},"finish_reason":finish}]}]
            data = "".join("data: " + json.dumps(f) + "\n\n" for f in frames) + "data: [DONE]\n\n"
            self.reply(data, stream=True)

        do_POST = do_GET = process

    ThreadingHTTPServer(("127.0.0.1", 8501 if name == "product" else 8502), Handler).serve_forever()


def receiver_action(db, action, op, body):
    def event(kind, value=""):
        db.execute("insert into events(op,kind,value) values(?,?,?)", (op,kind,str(value)))

    if action == "send":
        event("http_post", body.get("job"))
        db.execute("insert or ignore into jobs(op) values(?)", (op,))
        return {"accepted":True}, 202
    if action == "complete":
        receipt = "receipt_" + uuid.uuid4().hex
        private="vendorprivate"+uuid.uuid4().hex
        assert db.execute("update jobs set completed=1,receipt=?,result_private=? where op=? and completed=0",(receipt,private,op)).rowcount == 1
        event("effect",receipt)
        event("simulated_charge",1)
    elif action == "open":
        db.execute("update jobs set visible=1 where op=?", (op,))
    elif action == "lookup":
        job = db.execute("select receipt,result_private from jobs where op=? and completed and visible",(op,)).fetchone()
        event("query", "known" if job else "unknown")
        return {"receipt":job[0] if job else None, "details":job[1] if job else None}, 200
    elif action == "deliver":
        event("delivery",body)
    else:
        raise ValueError(action)
    return {"ok":True}, 200


def product_action(db, action, op, body):
    if action == "init":
        db.execute("insert into ops(op,prompt_private) values(?,?)", (op,"productprivate"+uuid.uuid4().hex))
    elif action == "enter":
        claim = db.execute("update ops set sent=1 where op=? and sent=0 and canceled=0 and version=reader and version=1 and quarantine=0", (op,)).rowcount
        db.execute("insert into entries(op,job,claim) values(?,?,?)", (op,body["job"],claim))
        return {"send":bool(claim)}, 200
    elif action == "switch_reader":
        db.execute("update ops set reader=2 where op=?", (op,))
    elif action == "cancel":
        db.execute("update ops set canceled=1 where op=?", (op,))
    elif action == "reconcile":
        found = http(RECEIVER+"/lookup/"+op)
        receipt = found["receipt"]
        if receipt:
            db.execute("update ops set held=0,spent=1,receipt=?,result_private=? where op=? and receipt is null", (receipt,found["details"],op))
        mismatch=db.execute("select version<>reader from ops where op=?",(op,)).fetchone()[0]
        if mismatch:
            db.execute("update ops set quarantine=1 where op=?",(op,))
        return {"receipt":None if mismatch else receipt}, 200
    elif action == "deliver":
        row = db.execute("select * from ops where op=?", (op,)).fetchone()
        if (row and row["receipt"] and not row["canceled"] and row["version"] == row["reader"] == 1 and not row["quarantine"]
                and body.get("verdict")=="complete_"+row["receipt"]):
            if db.execute("update ops set delivered=1 where op=? and delivered=0",(op,)).rowcount:
                return http(RECEIVER+"/deliver/"+op, {"receipt":row["receipt"]}), 200
            return {"already_delivered":True}, 200
        return {"denied":True}, 403
    else:
        raise ValueError(action)
    return {"ok":True}, 200


if __name__ == "__main__":
    start(sys.argv[1])
