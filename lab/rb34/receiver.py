"""Disposable HTTP receivers. Arrival, fee, and deduplicated effect commit before the socket closes."""
import hashlib
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import psycopg

DSN = os.environ["RECEIVER_DSN"]
SIDE = sys.argv[1]


def initialize():
    with psycopg.connect(DSN) as conn:
        if SIDE == "delivery":
            conn.execute("CREATE TABLE delivery (id bigserial PRIMARY KEY, scope text, op text)")
            return
        conn.execute("""
            CREATE TABLE fixtures (scope text PRIMARY KEY, drop_first boolean, published boolean);
            CREATE TABLE arrival (id bigserial PRIMARY KEY, scope text, op text, digest text, sdk_retry text);
            CREATE TABLE effect (op text PRIMARY KEY, scope text, digest text);
            CREATE TABLE charge (arrival_id bigint PRIMARY KEY REFERENCES arrival, scope text, units int);
            CREATE TABLE lookup (id bigserial PRIMARY KEY, scope text, found boolean)
        """)


class Receiver(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path.strip("/").split("/")
        if path == ["ready"]:
            return self.reply(200, {"ready": True})
        if SIDE != "provider" or len(path) != 2 or path[1] != "receipt":
            return self.reply(404, {})
        scope = path[0]
        with psycopg.connect(DSN) as conn:
            row = conn.execute("SELECT published FROM fixtures WHERE scope=%s", (scope,)).fetchone()
            if row is None:
                return self.reply(404, {})
            published = row[0]
            conn.execute("INSERT INTO lookup(scope,found) VALUES (%s,%s)", (scope,published))
            fees = conn.execute("SELECT arrival_id,units FROM charge WHERE scope=%s ORDER BY arrival_id", (scope,)).fetchall() if published else []
            effect = conn.execute("SELECT op,digest FROM effect WHERE scope=%s", (scope,)).fetchone() if published else None
        self.reply(200, {"scope": scope, "known": bool(effect), "effect": effect, "fees": fees})

    def do_POST(self):
        path = urlsplit(self.path).path.strip("/").split("/")
        body = self.rfile.read(int(self.headers["Content-Length"]))
        scope = path[0]
        op = self.headers.get("Idempotency-Key")
        if not op or op != "op-" + scope:
            return self.reply(400, {"error": "operation binding"})
        if SIDE == "delivery" and path == [scope, "deliver"]:
            with psycopg.connect(DSN) as conn:
                conn.execute("INSERT INTO delivery(scope,op) VALUES (%s,%s)", (scope, op))
            return self.reply(200, {"received": True})
        if SIDE != "provider" or path != [scope, "v1", "chat", "completions"]:
            return self.reply(404, {})
        digest = hashlib.sha256(body).hexdigest()
        with psycopg.connect(DSN) as conn:
            drop, = conn.execute("SELECT drop_first FROM fixtures WHERE scope=%s FOR UPDATE", (scope,)).fetchone()
            prev = conn.execute("SELECT digest FROM effect WHERE op=%s", (op,)).fetchone()
            if prev and prev[0] != digest:
                return self.reply(409, {"error": "key / payload mismatch"})
            arrival, = conn.execute("INSERT INTO arrival(scope,op,digest,sdk_retry) VALUES (%s,%s,%s,%s) RETURNING id",
                                    (scope, op, digest, self.headers.get("x-stainless-retry-count"))).fetchone()
            conn.execute("INSERT INTO effect(op,scope,digest) VALUES (%s,%s,%s) ON CONFLICT (op) DO NOTHING", (op,scope,digest))
            conn.execute("INSERT INTO charge VALUES (%s,%s,1)", (arrival,scope))
            if not drop or prev:
                # Every acknowledged POST publishes the same authoritative lookup, in either group.
                conn.execute("UPDATE fixtures SET published=true WHERE scope=%s", (scope,))
        if drop and not prev:
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        self.reply(200, {"id": "fixture-response", "created": 1, "object": "chat.completion",
                         "model": "fixture-model", "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "accepted"}}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


if __name__ == "__main__":
    initialize()
    ThreadingHTTPServer(("0.0.0.0", 8080), Receiver).serve_forever()
