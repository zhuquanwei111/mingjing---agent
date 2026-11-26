"""PostgreSQL is authoritative for products and receipts; Temporal owns execution."""

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from mingjing_p1.contracts import CAPABILITIES, Principal, Rejected, digest

Row = dict[str, Any]


def connect() -> psycopg.Connection[Row]:
    return psycopg.connect(
        os.environ["MINGJING_DB_DSN"], row_factory=dict_row, connect_timeout=3,
        options="-c lock_timeout=3000 -c statement_timeout=6000",
    )


def audit(conn: psycopg.Connection[Row], tenant: str, code: str,
          task: Mapping[str, Any] | None = None, attempt: str | None = None) -> None:
    conn.execute(
        "INSERT INTO audit (tenant, task_id, operation_id, attempt_id, code) VALUES (%s,%s,%s,%s,%s)",
        (tenant, task["id"] if task else None, task["operation_id"] if task else None, attempt, code),
    )


def allowed(conn: psycopg.Connection[Row], tenant: str, subject: str,
            resource: str, action: str) -> bool:
    grant = conn.execute(
        "SELECT allowed FROM grants WHERE tenant=%s AND subject=%s AND resource=%s AND action=%s FOR SHARE",
        (tenant, subject, resource, action),
    ).fetchone()
    return bool(grant and grant["allowed"])


def is_published(conn: psycopg.Connection[Row], tenant: str, capability: str) -> bool:
    release = conn.execute(
        "SELECT enabled FROM published WHERE tenant=%s AND capability=%s FOR SHARE",
        (tenant, capability),
    ).fetchone()
    return bool(release and release["enabled"])


def create_task(principal: Principal, body: Row, request_key: str) -> Row:
    kind = body.get("kind")
    capability = body.get("capability")
    value = body.get("value")
    resource = body.get("resource", "marker")
    if kind not in ("direct", "workflow", "agent"):
        raise Rejected("bad_kind", 400)
    if not isinstance(capability, str) or capability not in CAPABILITIES:
        raise Rejected("bad_capability", 400)
    if (not isinstance(value, str) or not 0 < len(value) <= 128
            or resource != "marker" or not 0 < len(request_key) <= 128):
        raise Rejected("bad_input", 400)
    body_hash = digest([capability, kind, resource, value])
    task_id = str(uuid4())
    with connect() as conn:
        if not allowed(conn, principal.tenant, principal.subject, resource, "write"):
            audit(conn, principal.tenant, "submit_denied")
            conn.commit()
            raise Rejected("authorization_denied")
        if not is_published(conn, principal.tenant, capability):
            raise Rejected("release_disabled")
        created = conn.execute(
            """INSERT INTO tasks (id,tenant,subject,resource,kind,capability,body_hash,request_key,
                                  value,run_id,workflow_id,operation_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (tenant,subject,request_key) DO NOTHING RETURNING *""",
            (task_id, principal.tenant, principal.subject, resource, kind, capability, body_hash,
             request_key, value, str(uuid4()), f"p1-{task_id}", str(uuid4())),
        ).fetchone()
        if created and kind != "direct":
            conn.execute(
                """INSERT INTO approvals (task_id,decision_id,body_hash,expires_at)
                   VALUES (%s,%s,%s,clock_timestamp()+interval '2 minutes')""",
                (task_id, f"{task_id}:approval", body_hash),
            )
        task = created or conn.execute(
            "SELECT * FROM tasks WHERE tenant=%s AND subject=%s AND request_key=%s",
            (principal.tenant, principal.subject, request_key),
        ).fetchone()
        assert task is not None
        if task["body_hash"] != body_hash:
            raise Rejected("request_key_conflict", 409)
        return task


def for_update(conn: psycopg.Connection[Row], task_id: str) -> Row:
    task = conn.execute("SELECT * FROM tasks WHERE id=%s FOR UPDATE", (task_id,)).fetchone()
    if task is None:
        raise Rejected("task_not_found", 404)
    return task


def scoped(conn: psycopg.Connection[Row], principal: Principal,
           task_id: str, action: str) -> Row:
    task = for_update(conn, task_id)
    if task["tenant"] != principal.tenant or not allowed(
        conn, principal.tenant, principal.subject, task["resource"], action
    ):
        audit(conn, principal.tenant, f"{action}_denied")
        conn.commit()
        raise Rejected("authorization_denied")
    return task


def review(principal: Principal, task_id: str) -> tuple[Row, str]:
    with connect() as conn:
        task = scoped(conn, principal, task_id, "approve")
        approval = conn.execute(
            """SELECT *, expires_at>clock_timestamp() AS fresh
               FROM approvals WHERE task_id=%s FOR UPDATE""",
            (task_id,),
        ).fetchone()
        if not approval or not approval["fresh"] or task["cancel_requested"]:
            audit(conn, principal.tenant, "approval_unavailable", task)
            conn.commit()
            raise Rejected("approval_unavailable", 409)
        if not approval["approved_by"]:
            conn.execute("UPDATE approvals SET approved_by=%s WHERE task_id=%s",
                         (principal.subject, task_id))
            audit(conn, principal.tenant, "approval_accepted", task)
        return task, approval["decision_id"]


def request_cancel(principal: Principal, task_id: str) -> Row:
    with connect() as conn:
        task = scoped(conn, principal, task_id, "cancel")
        conn.execute(
            """UPDATE tasks SET cancel_requested=true,
               status=CASE WHEN status='pending' THEN 'cancelled' ELSE status END WHERE id=%s""",
            (task_id,),
        )
        audit(conn, principal.tenant, "cancel_requested", task)
        return task


def receipt(conn: psycopg.Connection[Row], task: Row) -> Row | None:
    return conn.execute(
        "SELECT * FROM receipts WHERE tenant=%s AND operation_id=%s",
        (task["tenant"], task["operation_id"]),
    ).fetchone()


def inspect_task(principal: Principal, task_id: str) -> Row:
    with connect() as conn:
        task = scoped(conn, principal, task_id, "read")
        recorded = receipt(conn, task)
        return {
            "task_id": task["id"], "run_id": task["run_id"], "workflow_id": task["workflow_id"],
            "operation_id": task["operation_id"], "status": task["status"],
            "cancel_requested": task["cancel_requested"],
            "result": recorded["result"] if recorded else None,
        }


def add_artifact(conn: psycopg.Connection[Row], task: Row, version: int, value: str) -> str:
    content = value.encode()
    content_hash = hashlib.sha256(content).hexdigest()
    artifact_id = f"{task['id']}:{version}"
    inserted = conn.execute(
        """INSERT INTO artifacts (id,tenant,task_id,version,digest) VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (task_id,version) DO NOTHING RETURNING digest""",
        (artifact_id, task["tenant"], task["id"], version, content_hash),
    ).fetchone()
    if not inserted:
        old = conn.execute("SELECT digest FROM artifacts WHERE id=%s", (artifact_id,)).fetchone()
        if old is None or old["digest"] != content_hash:
            raise Rejected("artifact_version_conflict", 409)
    folder = Path(os.environ["MINGJING_ARTIFACT_DIR"])
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = folder / content_hash
    temporary = folder / f".{uuid4()}"
    try:
        temporary.write_bytes(content)
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != content:
                raise Rejected("artifact_hash_mismatch", 409)
    finally:
        temporary.unlink(missing_ok=True)
    return artifact_id


def read_artifact(principal: Principal, artifact_id: str) -> Row:
    with connect() as conn:
        artifact = conn.execute(
            "SELECT * FROM artifacts WHERE id=%s AND tenant=%s", (artifact_id, principal.tenant)
        ).fetchone()
        if not artifact:
            raise Rejected("artifact_not_found", 404)
        scoped(conn, principal, artifact["task_id"], "read")
        content = (Path(os.environ["MINGJING_ARTIFACT_DIR"]) / artifact["digest"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != artifact["digest"]:
            raise Rejected("artifact_hash_mismatch", 409)
        return {"artifact_id": artifact_id, "version": artifact["version"],
                "sha256": artifact["digest"], "text": content.decode()}
