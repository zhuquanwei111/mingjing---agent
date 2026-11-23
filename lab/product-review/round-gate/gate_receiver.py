"""Frozen HTTP receiver plus an append-only charge per model arrival and controlled lost replies."""
import json
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from psycopg.types.json import Jsonb
import witness as base


class Handler(base.Handler):
    def reply(self, status, obj):
        path = urlsplit(self.path).path.split("/")
        if len(path) >= 3:
            scope, action = path[1:3]
            if action == "submit":
                # The async job commits independently. Delay its HTTP ack to deterministically
                # place the first subsequent lookup after the effect but before visibility.
                while True:
                    with base.connect() as conn:
                        ready = conn.execute("""SELECT 1 FROM jobs j JOIN effects e USING(op)
                                   JOIN fees f USING(op) WHERE j.scope=%s""",(scope,)).fetchone()
                    if ready:
                        break
                    time.sleep(.07)
            gate = None
            if action == "v1" and scope in ("legacy", "guarded"):
                gate = "drop_model"
            elif action == "lookup" and obj.get("known"):
                gate = "release_lookups"
            if gate:
                # Committed model charge/lookup precedes this barrier. No HTTP bytes have been sent.
                with base.connect() as conn:
                    base.log(conn, scope, "reply_barrier", {"gate":gate})
                while True:
                    with base.connect() as conn:
                        if conn.execute("SELECT opened FROM barrier WHERE name=%s",(gate,)).fetchone()[0]:
                            break
                    time.sleep(.07)
                if gate == "drop_model":
                    self.close_connection = True
                    return
        return super().reply(status, obj)

    def do_POST(self):
        # Headers travel on the actual OpenAI SDK POST. Never synthesize a dispatch ID for the control.
        local.headers = {key:self.headers.get("X-Gate-" + key) for key in ("Operation","Round","Dispatch")}
        try:
            super().do_POST()
        finally:
            del local.headers


local = threading.local()
original_log = base.log


def metered_log(conn, scope, kind, data):
    if kind != "model":
        return original_log(conn, scope, kind, data)
    wire = getattr(local,"headers")
    returned = any(m["role"] == "tool" for m in data["request"]["messages"])
    number = 2 if returned else 1
    if scope != "legacy":
        assert wire["Round"] == str(number) and wire["Operation"] and wire["Dispatch"]
    seq, = conn.execute("INSERT INTO requests(scope,kind,detail) VALUES(%s,%s,%s) RETURNING seq",
                        (scope,kind,Jsonb({**data,"wire":wire,"logical_round":number}))).fetchone()
    conn.execute("INSERT INTO model_fee(arrival,scope,round_no,dispatch,units) VALUES(%s,%s,%s,%s,1)",
                 (seq,scope,number,wire["Dispatch"]))


if __name__ == "__main__":
    base.log = metered_log
    with base.connect() as conn:
        conn.execute(base.SCHEMA)
        conn.execute("""
          CREATE TABLE model_fee(arrival bigint PRIMARY KEY REFERENCES requests(seq),scope text,
              round_no int,dispatch text,units int NOT NULL CHECK(units=1));
          CREATE TABLE barrier(name text PRIMARY KEY,opened boolean NOT NULL DEFAULT false);
          INSERT INTO barrier(name) VALUES('drop_model'),('release_lookups');
        """)
    threading.Thread(target=base.tick,daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",8080),Handler).serve_forever()
