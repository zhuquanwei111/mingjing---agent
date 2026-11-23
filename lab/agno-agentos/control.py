"""Product-owned operation state and reconciliation, using AgentOS public HTTP only."""
import json
import os
import time
import uuid
from urllib.parse import quote

import httpx
import psycopg
from psycopg.rows import dict_row

SCOPES = ("known", "unknown", "cancel", "incompatible", "wrong", "revoked")
EXTRAS = ("direct", "workflow")
NAME = "request_receipt"
RUNNER = os.getenv("RUNNER_URL", "http://127.0.0.1:8090")
GATE = os.getenv("GATE_URL", "http://127.0.0.1:8091")
WITNESS = os.getenv("WITNESS_URL", "http://127.0.0.1:8080")
SCHEMA = """
CREATE TABLE policy(scope text PRIMARY KEY, allowed boolean NOT NULL);
CREATE TABLE operation(scope text PRIMARY KEY REFERENCES policy, operation_id text UNIQUE NOT NULL,
  run_id text NOT NULL, session_id text NOT NULL, call_id text NOT NULL, ref text NOT NULL,
  active boolean NOT NULL DEFAULT true, reader_version int NOT NULL DEFAULT 1,
  state text NOT NULL DEFAULT 'prepared', held int NOT NULL DEFAULT 3,
  spent int NOT NULL DEFAULT 0, receipt text, UNIQUE(run_id,call_id));
"""


def db():
    return psycopg.connect(os.environ["PRODUCT_DSN"], row_factory=dict_row)


def api(method, path, **kwargs):
    response = httpx.request(method, RUNNER + path, timeout=45,
                             headers={"Authorization": "Bearer " + os.environ["OS_KEY"]}, **kwargs)
    response.raise_for_status()
    return response.json()


def authorized(scope, path, payload):
    """Serializes policy changes with the first hand-off to this synthetic receiver."""
    with db() as c:
        row = c.execute("SELECT allowed FROM policy WHERE scope=%s FOR SHARE", (scope,)).fetchone()
        if not row or not row["allowed"]:
            raise PermissionError(scope)
        response = httpx.post(f"{WITNESS}/{scope}/{path}", json=payload, timeout=15)
        response.raise_for_status()
        return response.status_code, response.json()


def record(scope, run, session, call, ref):
    with db() as c:
        c.execute("""INSERT INTO operation(scope,operation_id,run_id,session_id,call_id,ref)
                  VALUES (%s,%s,%s,%s,%s,%s)""",
                  (scope, "op_" + uuid.uuid4().hex, run, session, call, ref))


def current(scope):
    with db() as c:
        return c.execute("SELECT * FROM operation WHERE scope=%s", (scope,)).fetchone()


def dispatch(scope):
    # No second send after a committed claim, even if the first acknowledgement is lost.
    with db() as c:
        row = c.execute("""UPDATE operation SET state='unconfirmed' WHERE scope=%s
                         AND state='prepared' AND active RETURNING *""", (scope,)).fetchone()
    if row:
        status, _ = authorized(scope, "submit",
                               {"op": row["operation_id"], "call": row["call_id"], "ref": row["ref"]})
        assert status == 202


def path(row):
    return f"/agents/{row['scope']}/runs/{quote(row['run_id'], safe='')}"


def read_run(row):
    return api("GET", path(row), params={"session_id": row["session_id"]})


def wait_run(row, target):
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        run = read_run(row)
        status = run["status"].lower()
        if status == target:
            return run
        if status in ("error", "failed", "cancelled"):
            raise RuntimeError(run)
        time.sleep(.2)
    raise TimeoutError((target, row["scope"], run))


def pending(run):
    requirement, = run["requirements"]
    tool = requirement["tool_execution"]
    assert tool["external_execution_required"] and tool["tool_name"] == NAME
    return tool


def reconcile(scope, notified_call=None):
    row = current(scope)
    if (notified_call is not None and notified_call != row["call_id"]):
        return "wrong-call"
    if row["state"] != "unconfirmed":
        return row["state"]
    # The sender supplies only an optional ID. Terminal facts come from the bound service.
    lookup = httpx.get(f"{WITNESS}/{scope}/lookup/{row['operation_id']}", timeout=10)
    lookup.raise_for_status()
    proof = lookup.json()
    if not proof["known"]:
        return "unknown"
    if (proof["op"], proof["call"]) != (row["operation_id"], row["call_id"]):
        return "invalid-proof"
    assert 0 <= proof["units"] <= row["held"]
    with db() as c:
        locked = c.execute("SELECT * FROM operation WHERE scope=%s FOR UPDATE", (scope,)).fetchone()
        if locked["state"] != "unconfirmed":
            return locked["state"]
        allowed = c.execute("SELECT allowed FROM policy WHERE scope=%s FOR SHARE", (scope,)).fetchone()["allowed"]
        state = ("cancelled-settled" if not locked["active"] else "isolated-version"
                 if locked["reader_version"] != 1 else "revoked-settled" if not allowed else "continuing")
        c.execute("""UPDATE operation SET state=%s,held=0,spent=%s,receipt=%s WHERE scope=%s""",
                  (state, proof["units"], proof["receipt"], scope))
    if state != "continuing":
        return state
    run = read_run(row)
    tool = pending(run)
    assert (run["run_id"], run["session_id"], tool["tool_call_id"]) == (row["run_id"], row["session_id"], proof["call"])
    tool = dict(tool, result=proof["receipt"])
    ack = api("POST", path(row) + "/continue", data={"session_id": row["session_id"], "stream": "false", "background": "true",
                                                      "tools": json.dumps([tool])})
    assert ack["run_id"] == row["run_id"], ack
    done = wait_run(row, "completed")
    assert done["run_id"] == row["run_id"] and done["status"].lower() == "completed", done
    assert proof["receipt"] in str(done["content"])
    authorized(scope, "deliver", {"op": row["operation_id"], "receipt": proof["receipt"]})
    with db() as c:
        c.execute("UPDATE operation SET state='delivered' WHERE scope=%s AND state='continuing'", (scope,))
    return "delivered"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps({"status": reconcile(*sys.argv[1:]), "pid": os.getpid()}), flush=True)
        sys.exit(0)
    # Old worker performs the real first dispatch, then watches for product-level reconciliation.
    while True:
        for scenario in SCOPES:
            dispatch(scenario)
            if current(scenario)["state"] == "unconfirmed":
                reconcile(scenario)
        time.sleep(.20)
