"""Independent receiving services and a background job. No access to the product DB."""
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb


def connect():
    return psycopg.connect(os.environ["WITNESS_DSN"])


SCHEMA = """
CREATE TABLE scenario(scope text PRIMARY KEY, enabled boolean DEFAULT false,
    visible boolean DEFAULT false, name text NOT NULL, marker text NOT NULL);
CREATE TABLE requests(seq bigserial PRIMARY KEY, scope text, kind text, detail jsonb);
CREATE TABLE jobs(op text PRIMARY KEY, scope text, call_id text, receipt text);
CREATE TABLE effects(op text PRIMARY KEY, receipt text);
CREATE TABLE fees(arrival bigint PRIMARY KEY REFERENCES requests(seq), op text, units int);
"""


def log(conn, scope, kind, data):
    conn.execute("INSERT INTO requests(scope,kind,detail) VALUES(%s,%s,%s)", (scope, kind, Jsonb(data)))


def tick():
    while True:
        with connect() as c:
            rows = c.execute("""SELECT j.op,j.scope FROM jobs j JOIN scenario s USING(scope)
                  WHERE j.receipt IS NULL AND s.enabled FOR UPDATE OF j SKIP LOCKED""").fetchall()
            for op, scope in rows:
                receipt = "EFFECT_MARK_" + uuid.uuid4().hex
                c.execute("INSERT INTO effects VALUES(%s,%s)", (op, receipt))

                c.execute("UPDATE jobs SET receipt=%s WHERE op=%s", (receipt, op))
                log(c, scope, "effect", {"op": op, "receipt": receipt})
            c.execute("""INSERT INTO fees(arrival,op,units)
                       SELECT r.seq,r.detail->>'op',1 FROM requests r JOIN scenario s USING(scope)
                       WHERE r.kind='arrival' AND s.enabled ON CONFLICT DO NOTHING""")
        time.sleep(.08)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/ready":
            return self.reply(200, {})
        _, scope, _, op = urlsplit(self.path).path.split("/")
        with connect() as c:
            row = c.execute("""SELECT j.call_id,j.receipt,s.visible FROM jobs j
                    JOIN scenario s USING(scope) WHERE j.scope=%s AND j.op=%s""", (scope,op)).fetchone()
            found = bool(row and row[1] and row[2])
            log(c,scope,"lookup",{"op":op,"found":found})
        self.reply(200, {"known": found, **({"call": row[0], "receipt": row[1], "op": op, "units": 1} if found else {})})

    def do_POST(self):
        _, scope, action, *tail = urlsplit(self.path).path.split("/")
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with connect() as c:
            name, marker = c.execute("SELECT name,marker FROM scenario WHERE scope=%s",(scope,)).fetchone()
            if action == "v1":
                messages = data["messages"]
                returned = [m for m in messages if m["role"] == "tool"]
                if returned:
                    body = {"role": "assistant", "content": "recorded " + returned[-1]["content"]}
                    reason = "stop"
                else:
                    advertised, = [t["function"] for t in data["tools"] if t["type"]=="function" and t["function"]["name"]==name]
                    assert advertised["parameters"]["properties"]["ref"]["type"]=="string"
                    prompt, = [m["content"] for m in messages if m["role"]=="user"]
                    assert isinstance(prompt,str) and prompt.endswith(marker)
                    wire_input = {"ref":prompt.split()[-1]}
                    call = "call_" + uuid.uuid4().hex
                    body = {"role": "assistant", "content": None, "tool_calls": [
                        {"id":call, "type":"function", "function":{"name":advertised["name"],"arguments":json.dumps(wire_input)}}]}
                    reason = "tool_calls"
                log(c,scope,"model",{"request":data,"reply":body})
                result = {"id":uuid.uuid4().hex,"object":"chat.completion","created":int(time.time()),"model":"fixture",
                          "choices":[{"index":0,"message":body,"finish_reason":reason}],
                          "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}}
                status = 200
            elif action == "submit":
                log(c,scope,"arrival",data)
                c.execute("INSERT INTO jobs(op,scope,call_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                          (data["op"],scope,data["call"]))
                result, status = {"accepted":True},202
            elif action == "deliver":
                log(c,scope,"delivery",data)
                result, status = {"received":True},200
            else:
                return self.reply(404,{})
        self.reply(status,result)


if __name__ == "__main__":
    with connect() as conn:
        conn.execute(SCHEMA)
    threading.Thread(target=tick, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",8080),Handler).serve_forever()
