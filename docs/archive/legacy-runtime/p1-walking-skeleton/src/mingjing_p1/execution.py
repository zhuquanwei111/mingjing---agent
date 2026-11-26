"""The only path that can commit a marker or dispatch the local fake provider."""

import http.client
import json
import os
import time
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb

from mingjing_p1 import storage as db
from mingjing_p1.contracts import CAPABILITIES, Job, Rejected
from mingjing_p1.telemetry import tracer


def gate(conn: psycopg.Connection[db.Row], task: db.Row) -> str | None:
    if task["cancel_requested"]:
        return "cancelled"
    if not db.allowed(conn, task["tenant"], task["subject"], task["resource"], "write"):
        return "authorization_denied"
    if not db.is_published(conn, task["tenant"], task["capability"]):
        return "release_disabled"
    if task["kind"] == "direct":
        return None
    approval = conn.execute(
        """SELECT approved_by, body_hash, expires_at>clock_timestamp() AS fresh
           FROM approvals WHERE task_id=%s FOR SHARE""", (task["id"],),
    ).fetchone()
    if not approval or not approval["approved_by"] or not approval["fresh"]:
        return "approval_unavailable"
    if (approval["body_hash"] != task["body_hash"] or not db.allowed(
        conn, task["tenant"], approval["approved_by"], task["resource"], "approve"
    )):
        return "approval_unavailable"
    return None


def result(task: db.Row, attempt_id: str, state: str, **details: str) -> db.Row:
    return {
        "schema_version": 1, "state": state, "task_id": task["id"],
        "run_id": task["run_id"], "workflow_id": task["workflow_id"],
        "operation_id": task["operation_id"], "attempt_id": attempt_id, **details,
    }


def finish(conn: psycopg.Connection[db.Row], task: db.Row, finished: db.Row) -> db.Row:
    conn.execute(
        """INSERT INTO receipts (tenant,operation_id,body_hash,state,result) VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (tenant,operation_id) DO UPDATE SET state=EXCLUDED.state,result=EXCLUDED.result
           WHERE receipts.state='dispatching' AND receipts.body_hash=EXCLUDED.body_hash""",
        (task["tenant"], task["operation_id"], task["body_hash"], finished["state"], Jsonb(finished)),
    )
    conn.execute("UPDATE tasks SET status=%s WHERE id=%s", (finished["state"], task["id"]))
    return finished


def deny(conn: psycopg.Connection[db.Row], task: db.Row, attempt: str, reason: str) -> db.Row:
    db.audit(conn, task["tenant"], reason, task, attempt)
    state = "cancelled" if reason == "cancelled" else "denied"
    if not db.receipt(conn, task):
        conn.execute("UPDATE tasks SET status=%s WHERE id=%s", (state, task["id"]))
    return result(task, attempt, state, code=reason)


def dispatch(value: str, operation_id: str) -> tuple[str, str]:
    url = urlsplit(os.environ["MINGJING_PROVIDER_URL"])
    if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port or url.path != "/mark":
        raise Rejected("invalid_fake_provider")
    connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=1)
    try:
        payload = json.dumps({"value": value, "operation_id": operation_id})
        connection.request("POST", "/mark", payload, {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status == 200:
            return "succeeded", json.loads(response.read(4096))["reference"]
    except (OSError, http.client.HTTPException, ValueError, KeyError):
        pass
    finally:
        connection.close()
    return "unknown", "missing_provider_receipt"


def execute(job: Job, attempt_id: str, engine_run_id: str | None = None,
            engine_attempt: int = 1) -> db.Row:
    with tracer().start_as_current_span("mingjing.tool") as span:
        span.set_attributes({"task_id": job.task_id, "operation_id": job.operation_id,
                             "attempt_id": attempt_id})
        try:
            finished = _execute(job, attempt_id, engine_run_id, engine_attempt)
        except psycopg.Error:
            span.set_attribute("outcome", "gate_unavailable")
            return {"schema_version": 1, "state": "denied", "code": "gate_unavailable",
                    "task_id": job.task_id, "operation_id": job.operation_id}
        for key in ("run_id", "workflow_id", "artifact_id"):
            if key in finished:
                span.set_attribute(key, finished[key])
        span.set_attribute("outcome", finished["state"])
        return finished


def _execute(job: Job, attempt_id: str, engine_run_id: str | None,
             engine_attempt: int) -> db.Row:
    with db.connect() as conn:
        task = db.for_update(conn, job.task_id)
        if task["operation_id"] != job.operation_id:
            raise Rejected("operation_mismatch")
        reason = gate(conn, task)
        if reason:
            return deny(conn, task, attempt_id, reason)
        db.audit(conn, task["tenant"], "execution_allowed", task, attempt_id)
        conn.execute(
            """INSERT INTO attempts (id,operation_id,engine_run_id,state) VALUES (%s,%s,%s,'started')
               ON CONFLICT (id) DO NOTHING""",
            (attempt_id, job.operation_id, engine_run_id),
        )
        prior = db.receipt(conn, task)
        if prior:
            if prior["body_hash"] != task["body_hash"]:
                raise Rejected("operation_payload_conflict", 409)
            if prior["state"] == "dispatching" and engine_attempt > 1:
                db.audit(conn, task["tenant"], "manual_reconciliation", task, attempt_id)
                return finish(conn, task, result(task, attempt_id, "unknown", code="unconfirmed_dispatch"))
            db.audit(conn, task["tenant"], "receipt_reused", task, attempt_id)
            return prior["result"]
        if job.deadline_epoch is not None and time.time() >= job.deadline_epoch:
            return deny(conn, task, attempt_id, "agent_deadline")
        mode = CAPABILITIES[task["capability"]].side_effect
        if mode == "database":
            conn.execute("INSERT INTO markers (operation_id,value) VALUES (%s,%s)",
                         (task["operation_id"], task["value"]))
            artifact_id = db.add_artifact(conn, task, 1, task["value"])
            conn.execute("UPDATE attempts SET state='settled' WHERE id=%s", (attempt_id,))
            db.audit(conn, task["tenant"], "committed", task, attempt_id)
            return finish(conn, task, result(task, attempt_id, "succeeded",
                                             value=task["value"], artifact_id=artifact_id))
        if mode == "metered":
            budget = conn.execute(
                "UPDATE accounts SET remaining=remaining-1 WHERE tenant=%s AND remaining>0 RETURNING remaining",
                (task["tenant"],),
            ).fetchone()
            if budget is None:
                return deny(conn, task, attempt_id, "budget_exhausted")
            conn.execute("UPDATE attempts SET reserved=1,state='reserved' WHERE id=%s", (attempt_id,))
        finish(conn, task, result(task, attempt_id, "dispatching"))

    may_have_sent = False
    try:
        with db.connect() as conn:
            task = db.for_update(conn, job.task_id)
            prior = db.receipt(conn, task)
            if not prior or prior["state"] != "dispatching":
                return prior["result"] if prior else deny(conn, task, attempt_id, "receipt_unavailable")
            reason = gate(conn, task)
            if not reason and job.deadline_epoch is not None and time.time() >= job.deadline_epoch:
                reason = "agent_deadline"
            if reason:
                if mode == "metered":
                    conn.execute("UPDATE accounts SET remaining=remaining+1 WHERE tenant=%s",
                                 (task["tenant"],))
                conn.execute("UPDATE attempts SET state='unsent' WHERE id=%s", (attempt_id,))
                return finish(conn, task, deny(conn, task, attempt_id, reason))
            db.audit(conn, task["tenant"], "provider_send", task, attempt_id)
            may_have_sent = True
            state, reference = dispatch(task["value"], task["operation_id"])
            conn.execute("UPDATE attempts SET state=%s,reference=%s WHERE id=%s",
                         ("settled" if state == "succeeded" else "unknown", reference, attempt_id))
            db.audit(conn, task["tenant"], "provider_receipt" if state == "succeeded" else
                     "manual_reconciliation", task, attempt_id)
            return finish(conn, task, result(task, attempt_id, state, reference=reference))
    except psycopg.Error:
        if not may_have_sent:
            raise
        return mark_uncertain(task, attempt_id)


def mark_uncertain(task: db.Row, attempt_id: str) -> db.Row:
    uncertain = result(task, attempt_id, "unknown", code="unconfirmed_dispatch")
    try:
        with db.connect() as conn:
            task = db.for_update(conn, task["id"])
            prior = db.receipt(conn, task)
            if prior and prior["state"] != "dispatching":
                return prior["result"]
            conn.execute("UPDATE attempts SET state='unknown' WHERE id=%s", (attempt_id,))
            db.audit(conn, task["tenant"], "manual_reconciliation", task, attempt_id)
            return finish(conn, task, uncertain)
    except psycopg.Error:
        # The preceding transaction already committed the reservation and dispatch intent.
        return uncertain


def reconcile_metered(task_id: str, attempt_id: str, verified_reference: str) -> db.Row:
    """Fixture-only reconciliation with a receipt from the synthetic provider ledger."""
    with db.connect() as conn:
        task = db.for_update(conn, task_id)
        attempted = conn.execute(
            """SELECT * FROM attempts WHERE id=%s AND operation_id=%s AND reserved=1 FOR UPDATE""",
            (attempt_id, task["operation_id"]),
        ).fetchone()
        prior = db.receipt(conn, task)
        if not prior or not attempted:
            raise Rejected("reconciliation_unavailable")
        if prior["state"] == "succeeded" and attempted["reference"] == verified_reference:
            return prior["result"]
        if prior["state"] != "unknown" or attempted["state"] != "unknown":
            raise Rejected("reconciliation_unavailable")
        conn.execute("UPDATE receipts SET state='dispatching' WHERE operation_id=%s",
                     (task["operation_id"],))
        conn.execute("UPDATE attempts SET state='settled',reference=%s WHERE id=%s",
                     (verified_reference, attempt_id))
        db.audit(conn, task["tenant"], "reconciled", task, attempt_id)
        return finish(conn, task, result(task, attempt_id, "succeeded", reference=verified_reference))
