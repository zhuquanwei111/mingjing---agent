"""Narrow reference adapter for this tool schema and OpenAI Chat, with a typed product vault."""
import json
import uuid

PROFILE = "reference"
SCHEMA = """
CREATE TABLE guarded_value(scope text REFERENCES policy, kind text, token text PRIMARY KEY, value text NOT NULL,
 UNIQUE(scope,kind,value));
"""


def hide(c, scope, kind, value):
    if scope != PROFILE:
        return value
    row = c.execute("""INSERT INTO guarded_value VALUES(%s,%s,%s,%s)
                    ON CONFLICT(scope,kind,value) DO UPDATE SET value=EXCLUDED.value RETURNING token""",
                    (scope, kind, "opaque_" + uuid.uuid4().hex, value)).fetchone()
    return row["token"]


def open_value(c, scope, kind, token):
    if scope != PROFILE:
        return token
    row = c.execute("""SELECT value FROM guarded_value WHERE scope=%s AND kind=%s AND token=%s""",
                    (scope, kind, token)).fetchone()
    if row is None:
        raise PermissionError("unbound typed reference")
    return row["value"]


def outgoing(c, scope, path, payload):
    if scope != PROFILE:
        return payload
    if path == "submit":
        return dict(payload, ref=open_value(c, scope, "ref", payload["ref"]),
                    call=open_value(c, scope, "call", payload["call"]))
    if path == "deliver":
        answer = open_value(c, scope, "answer", payload["answer"])
        receipt = open_value(c, scope, "receipt", payload["receipt"])
        if receipt not in answer:
            raise ValueError("completion omits authoritative receipt")
        return {"op": payload["op"], "answer": answer, "receipt": receipt}
    for msg in payload["messages"]:
        if msg["role"] == "user":
            msg["content"] = open_value(c, scope, "prompt", msg["content"])
        elif msg["role"] == "assistant":
            for invocation in msg.get("tool_calls") or []:
                invocation["id"] = open_value(c, scope, "call", invocation["id"])
                args = json.loads(invocation["function"]["arguments"])
                args["ref"] = open_value(c, scope, "ref", args["ref"])
                invocation["function"]["arguments"] = json.dumps(args)
        elif msg["role"] == "tool":
            msg["tool_call_id"] = open_value(c, scope, "call", msg["tool_call_id"])
            msg["content"] = open_value(c, scope, "receipt", msg["content"])
    return payload


def incoming(c, scope, path, response):
    if scope != PROFILE or path != "v1/chat/completions":
        return response
    msg = response["choices"][0]["message"]
    for invocation in msg.get("tool_calls") or []:
        invocation["id"] = hide(c, scope, "call", invocation["id"])
        args = json.loads(invocation["function"]["arguments"])
        args["ref"] = hide(c, scope, "ref", args["ref"])
        invocation["function"]["arguments"] = json.dumps(args)
    if msg.get("content"):
        msg["content"] = hide(c, scope, "answer", msg["content"])
    return response
