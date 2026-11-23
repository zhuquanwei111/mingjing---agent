"""Black-box examiner. The two stores have independent credentials and processes."""
import json
import os
import secrets
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from control import (EXTRAS, GATE, NAME, RUNNER, SCHEMA, SCOPES, WITNESS, api, current, db,
                     path, pending, read_run, record, wait_run)

OUT = Path(os.environ["LAB_OUT"])
children = []
markers = {s: "PROMPT_" + uuid.uuid4().hex for s in (*SCOPES, *EXTRAS)}


def evidence(event, data):
    line = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False, separators=(",", ":"))
    line = line.replace(os.environ["OS_KEY"], "[redacted-service-key]")
    print("AGNO_EVIDENCE", line, flush=True)
    with (OUT / "raw.jsonl").open("a") as handle:
        print(line, file=handle)


def witness(query, values=()):
    with psycopg.connect(os.environ["WITNESS_DSN"], row_factory=dict_row) as c:
        return c.execute(query, values).fetchall() if query.lstrip().upper().startswith("SELECT") else c.execute(query, values).rowcount


def start(script, *args):
    env = os.environ.copy()
    if script != "witness.py":
        env.pop("WITNESS_DSN", None)
    else:
        for key in ("PRODUCT_DSN", "OS_KEY"):
            env.pop(key, None)
    p = subprocess.Popen([sys.executable, "-u", script, *args], env=env)
    children.append(p)
    return p


def alive(url, process):
    def ready():
        if process.poll() is not None:
            raise RuntimeError((url, process.returncode))
        try:
            return httpx.get(url, timeout=1).status_code < 500
        except httpx.HTTPError:
            return False
    until(ready)


def until(check):
    stop = time.monotonic() + 60
    while time.monotonic() < stop:
        if check():
            return
        time.sleep(.15)
    raise TimeoutError(check.__name__)


def stop(process):
    assert process.poll() is None
    process.kill()
    assert process.wait(timeout=8) == -signal.SIGKILL


def count(scope):
    q = """SELECT
     (SELECT count(*) FROM requests WHERE scope=%s AND kind='arrival') sends,
     (SELECT count(*) FROM requests WHERE scope=%s AND kind='effect') effects,
     (SELECT count(*) FROM fees f JOIN jobs j USING(op) WHERE j.scope=%s) fees,
     (SELECT count(*) FROM requests WHERE scope=%s AND kind='model') models,
     (SELECT count(*) FROM requests WHERE scope=%s AND kind='delivery') deliveries"""
    return tuple(witness(q, [scope] * 5)[0].values())


def agno_table(name, column, value):
    with db() as c:
        t, = c.execute("SELECT table_schema FROM information_schema.tables WHERE table_name=%s", (name,)).fetchall()
        q = sql.SQL("SELECT to_jsonb(t) AS data FROM {} AS t WHERE {}=%s").format(
            sql.Identifier(t["table_schema"], name), sql.Identifier(column))
        rows = c.execute(q, (value,)).fetchall()
        return [r["data"] for r in rows]


def ticket(row):
    t, = agno_table("agno_jobs", "id", row["run_id"])
    assert t["session_id"] == row["session_id"] and t["component_id"] == row["scope"]
    return t


def wait_ticket(row, status):
    until(lambda: ticket(row)["status"].lower() == status)


def snapshot(scope, tag):
    row = current(scope)
    info = read_run(row)
    t = ticket(row)
    evidence(tag, {"scope": scope, "product": row, "run_id": info["run_id"], "status": info["status"],
                   "pending": [r.get("id") for r in info.get("requirements") or []],
                   "queue": t, "counts": count(scope)})
    return info, t


def recover(scope, wrong=None):
    output = subprocess.check_output([sys.executable, "control.py", scope, *([wrong] if wrong else [])],
                                     env={k: v for k, v in os.environ.items() if k != "WITNESS_DSN"}, text=True)
    result = json.loads(output)
    evidence("reconciler", {"scope": scope, **result})
    return result["status"]


def trial():
    service = start("witness.py")
    alive(WITNESS + "/ready", service)
    with db() as c:
        c.execute(SCHEMA)
        c.cursor().executemany("INSERT INTO policy VALUES(%s,true)", [(s,) for s in markers])
    for scope, marker in markers.items():
        witness("INSERT INTO scenario(scope,name,marker) VALUES(%s,%s,%s)", (scope, NAME, marker))

    gate = start("gateway.py")
    alive(GATE + "/openapi.json", gate)
    server = start("server.py")
    alive(RUNNER + "/openapi.json", server)
    for scope in SCOPES:
        session = "sess_" + uuid.uuid4().hex
        ack = api("POST", f"/agents/{scope}/runs", data={"message": "Check reference " + markers[scope],
                  "session_id": session, "stream": "false", "background": "true"})
        binding = {"scope": scope, "run_id": ack["run_id"], "session_id": session}
        run = wait_run(binding, "paused")
        wait_ticket(binding, "paused")
        tool = pending(run)
        assert tool["tool_args"]["ref"] == markers[scope]
        record(scope, ack["run_id"], session, tool["tool_call_id"], tool["tool_args"]["ref"])
    worker = start("control.py")
    until(lambda: all(count(s) == (1, 0, 0, 1, 0) for s in SCOPES))
    for scope in SCOPES:
        snapshot(scope, "accepted")
    witness("UPDATE scenario SET enabled=true")
    until(lambda: all(count(s) == (1, 1, 1, 1, 0) for s in SCOPES))
    for scope in SCOPES:
        row = current(scope)
        assert (row["held"], row["spent"], row["receipt"], row["state"]) == (3, 0, None, "unconfirmed")
        snapshot(scope, "effect-before-kill")
    stop(worker)
    stop(server)
    replacement = start("server.py")
    alive(RUNNER + "/openapi.json", replacement)
    assert replacement.pid != server.pid
    for scope in SCOPES:
        info, t = snapshot(scope, "new-server-read")
        assert pending(info)["tool_call_id"] == current(scope)["call_id"] and t["status"] == "paused"
        assert recover(scope) == "unknown"
    evidence("SIGKILL", {"old_agentos": server.pid, "old_worker": worker.pid, "new_agentos": replacement.pid,
                         "old_agentos_exit": server.returncode, "old_worker_exit": worker.returncode})

    for s in ("unknown", "cancel"):
        r = current(s)
        assert (r["held"], r["spent"], count(s)) == (3, 0, (1, 1, 1, 1, 0))
    with db() as c:
        c.execute("UPDATE operation SET active=false WHERE scope='cancel'")
        c.execute("UPDATE operation SET reader_version=2 WHERE scope='incompatible'")
        c.execute("UPDATE policy SET allowed=false WHERE scope='revoked'")
    cancelled = current("cancel")
    cancel_reply = api("POST", path(cancelled) + "/cancel", data={"session_id": cancelled["session_id"]})
    evidence("cancel-response", cancel_reply)
    # Exercise the actual model gateway after revocation instead of only checking local state.
    denied = httpx.post(GATE + "/revoked/v1/chat/completions", json={"messages": [{"role": "user", "content": markers["revoked"]}]})
    assert denied.status_code == 403
    witness("UPDATE scenario SET visible=true WHERE scope!='unknown'")
    wrong_id = "call_" + uuid.uuid4().hex
    assert recover("wrong", wrong_id) == "wrong-call"
    states = {"known": "delivered", "unknown": "unknown", "cancel": "cancelled-settled",
              "incompatible": "isolated-version", "revoked": "revoked-settled"}
    for scope, expected in states.items():
        assert recover(scope) == expected
        assert recover(scope) == expected
    wait_ticket(current("known"), "completed")
    for scope in SCOPES:
        row = current(scope)
        expected = (1, 1, 1, 2, 1) if scope == "known" else (1, 1, 1, 1, 0)
        assert count(scope) == expected, (scope, count(scope), expected)
        assert (row["held"], row["spent"]) == ((3, 0) if scope in ("wrong", "unknown") else (0, 1))
        snapshot(scope, "final")
    row = current("known")
    actual, = witness("SELECT e.receipt FROM effects e WHERE op=%s", (row["operation_id"],))
    responses = witness("SELECT detail FROM requests WHERE scope='known' AND kind='model' ORDER BY seq")
    original = responses[0]["detail"]["reply"]["tool_calls"][0]["id"]
    delivered, = [m for m in responses[1]["detail"]["request"]["messages"] if m["role"] == "tool"]
    assert delivered["tool_call_id"] == original == row["call_id"]
    assert actual["receipt"] == row["receipt"] and actual["receipt"] in delivered["content"]
    assert len(agno_table("agno_jobs", "session_id", row["session_id"])) == 1
    scanned = {"queue": ticket(row), "http_run": read_run(row), "product": row,
               "wire": responses, "session_db": agno_table("agno_sessions", "session_id", row["session_id"])}
    persistent_runs = agno_table("agno_runs", "run_id", row["run_id"])
    assert persistent_runs, "missing normalized persistent run"
    scanned["run_db"] = persistent_runs
    for name, data in scanned.items():
        raw = json.dumps(data, default=str)
        evidence("payload-presence", {"where": name, "argument": markers["known"] in raw,
                 "receipt": row["receipt"] in raw, "tool_call_id": original in raw})
        (OUT / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2)
                                            .replace(os.environ["OS_KEY"], "[redacted-service-key]"))
    assert markers["known"] in json.dumps(responses) and actual["receipt"] in json.dumps(responses)
    # Count optional deterministic paths independently; no model interaction on either.
    api("POST", "/fixture/direct", json={"ref": markers["direct"]})
    result = api("POST", "/workflows/fixed/runs", data={"message": markers["workflow"], "stream": "false"})
    assert result["status"].lower() == "completed", result
    for s in EXTRAS:
        until(lambda: count(s) == (1, 1, 1, 0, 0))
        evidence("deterministic-entry", {"scope": s, "counts": count(s), "operation": current(s)})
    for record_row in witness("SELECT * FROM requests ORDER BY seq"):
        evidence("receiver", record_row)
    evidence("complete", {"scenarios": list(SCOPES), "extras": list(EXTRAS), "sha": os.environ["TEST_HEAD"]})


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ["OS_KEY"] = secrets.token_hex(32)
    try:
        trial()
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.kill()
                process.wait()
