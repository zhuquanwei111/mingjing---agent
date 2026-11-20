from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
from opentelemetry import trace
from psycopg.types.json import Jsonb

from .artifacts import BlobStore, save_artifact
from .catalog import Catalog, require_grant
from .contracts import Action, Capability, CapabilityContext, Fault, Identity, Kind, ProviderReceipt, digest
from .db import Database, audit, authenticate

TERMINAL = {"succeeded", "denied", "unknown", "cancelled", "failed"}
TRACER = trace.get_tracer("mingjing.core")
EXECUTION_LOCK_SEED = 687202


@dataclass(frozen=True)
class Artifact:
    data: bytes
    media_type: str


def load_task(connection, task_id: UUID, tenant: str | None = None):
    row = connection.execute(
        """SELECT t.*,r.id AS run_id,r.workflow_id,r.temporal_run_id,r.engine_state,
                  r.started_at,r.ended_at
           FROM tasks t JOIN runs r ON r.task_id=t.id
           WHERE t.id=%s AND (%s::text IS NULL OR t.tenant=%s) FOR UPDATE OF t""",
        (task_id, tenant, tenant),
    ).fetchone()
    if not row:
        raise Fault("task_not_found", 404)
    return row


def load_receipt(connection, task):
    return connection.execute(
        "SELECT * FROM receipts WHERE tenant=%s AND operation_id=%s",
        (task["tenant"], task["operation_id"]),
    ).fetchone()


def task_view(connection, task) -> dict:
    receipt = load_receipt(connection, task)
    approval = connection.execute(
        "SELECT id,expires_at,decision FROM approvals WHERE task_id=%s", (task["id"],),
    ).fetchone()
    return {
        "schema_version": 1, "task_id": str(task["id"]), "operation_id": str(task["operation_id"]),
        "capability_id": task["capability"], "version": task["version"], "state": task["state"],
        "cancel_requested": task["cancel_requested"], "created_at": task["created_at"],
        "run": {
            "run_id": str(task["run_id"]), "workflow_id": task["workflow_id"], "temporal_run_id": task["temporal_run_id"],
            "engine_state": task["engine_state"], "started_at": task["started_at"], "ended_at": task["ended_at"],
        },
        "approval": approval, "receipt": {
            "state": receipt["state"], "attempt_id": str(receipt["attempt_id"]) if receipt["attempt_id"] else None,
            **receipt["outcome"],
        } if receipt else None,
    }


class TransactionNotes:
    def __init__(self, connection, context: CapabilityContext):
        self.connection = connection
        self.context = context

    def append(self, context: CapabilityContext, value: str) -> None:
        if context is not self.context:
            raise Fault("execution_context_mismatch", 403)
        self.connection.execute(
            "INSERT INTO example_notes VALUES (%s,%s,%s,%s)",
            (context.tenant, context.operation_id, context.resource, value),
        )


def require_task(connection, token: str, task_id: UUID, action: Action):
    identity = authenticate(connection, token=token)
    task = load_task(connection, task_id, identity.tenant)
    require_grant(connection, identity, task["capability"], task["version"], task["resource"], action)
    return identity, task


def context_for(task, attempt: UUID) -> CapabilityContext:
    return CapabilityContext(
        task["tenant"], task["subject"], task["id"], task["run_id"], task["operation_id"],
        attempt, task["resource"],
    )


def set_state(connection, task, state: str) -> None:
    connection.execute("UPDATE tasks SET state=%s WHERE id=%s", (state, task["id"]))
    if state in TERMINAL:
        if task["workflow_id"] is None:
            connection.execute(
                "UPDATE runs SET engine_state=%s,ended_at=clock_timestamp() WHERE task_id=%s",
                (state, task["id"]),
            )
        else:
            connection.execute(
                "UPDATE runs SET ended_at=COALESCE(ended_at,clock_timestamp()) WHERE task_id=%s",
                (task["id"],),
            )


def record_receipt(connection, task, state: str, result: dict, attempt: UUID | None = None) -> None:
    updated = connection.execute(
        """INSERT INTO receipts (tenant,operation_id,payload_hash,state,attempt_id,outcome)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON CONFLICT (tenant,operation_id) DO UPDATE
           SET state=EXCLUDED.state,attempt_id=EXCLUDED.attempt_id,outcome=EXCLUDED.outcome,updated_at=clock_timestamp()
           WHERE receipts.payload_hash=EXCLUDED.payload_hash AND receipts.state IN ('dispatching','unknown')
           RETURNING state""",
        (task["tenant"], task["operation_id"], task["payload_hash"], state, attempt, Jsonb(result)),
    ).fetchone()
    if not updated:
        raise Fault("receipt_conflict")
    set_state(connection, task, "running" if state == "dispatching" else state)
    audit(connection, task["tenant"], task["subject"], f"receipt_{state}", task, attempt)


class Service:
    def __init__(self, db: Database, catalog: Catalog, blobs: BlobStore):
        self.db = db
        self.catalog = catalog
        self.blobs = blobs

    def submit(self, token: str, name: str, version: int, resource: str, payload: dict, key: str) -> dict:
        with self.db.open() as connection:
            identity = authenticate(connection, token=token)
            require_grant(connection, identity, name, version, resource, Action.EXECUTE)
            cap = self.catalog.implementation(name, version)
            value = cap.validate_input(payload).model_dump(mode="json")
            body_hash = digest([name, version, resource, self.catalog.environment, value])
            existing = self.find_request(connection, identity, key)
            if existing:
                return self.reuse_request(connection, existing, body_hash)
            self.catalog.release(connection, identity.tenant, cap)
            task_id, operation_id = uuid4(), uuid4()
            inserted = connection.execute(
                """INSERT INTO tasks(id,tenant,subject,credential_id,capability,version,resource,environment,
                    operation_id,request_key,payload_hash,payload,contract_hash,kind,state)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued')
                    ON CONFLICT (tenant,subject,request_key) DO NOTHING RETURNING id""",
                (task_id, identity.tenant, identity.subject, identity.credential, name, version, resource,
                 self.catalog.environment, operation_id, key, body_hash, Jsonb(value), cap.fingerprint, cap.kind.value),
            ).fetchone()
            if not inserted:
                return self.reuse_request(connection, self.find_request(connection, identity, key), body_hash)
            workflow_id = f"mingjing-p2-{task_id}" if cap.kind in (Kind.WORKFLOW, Kind.AGENT) else None
            connection.execute(
                "INSERT INTO runs(id,task_id,workflow_id) VALUES (%s,%s,%s)", (uuid4(), task_id, workflow_id),
            )
            if cap.approval:
                connection.execute(
                    """INSERT INTO approvals(id,task_id,payload_hash,expires_at)
                       VALUES (%s,%s,%s,clock_timestamp()+interval '10 minutes')""",
                    (uuid4(), task_id, body_hash),
                )
            task = load_task(connection, task_id)
            audit(connection, identity.tenant, identity.subject, "task_submitted", task)
            return task_view(connection, task)

    @staticmethod
    def find_request(connection, identity: Identity, key: str):
        return connection.execute(
            "SELECT id,payload_hash FROM tasks WHERE tenant=%s AND subject=%s AND request_key=%s",
            (identity.tenant, identity.subject, key),
        ).fetchone()

    @staticmethod
    def reuse_request(connection, stored, body_hash: str) -> dict:
        if not stored or stored["payload_hash"] != body_hash:
            raise Fault("request_key_conflict")
        return task_view(connection, load_task(connection, stored["id"]))

    def get(self, token: str, task: UUID) -> dict:
        with self.db.open() as connection:
            _, row = require_task(connection, token, task, Action.READ)
            return task_view(connection, row)

    def submission_response(self, token: str, task_id: UUID) -> tuple[int, dict]:
        with self.db.open() as connection:
            identity, task = require_task(connection, token, task_id, Action.EXECUTE)
            status = 200 if task["state"] in TERMINAL else 202
            try:
                require_grant(
                    connection, identity, task["capability"], task["version"], task["resource"], Action.READ,
                )
            except Fault:
                return status, {
                    "schema_version": 1, "task_id": str(task_id),
                    "run": {"run_id": str(task["run_id"])},
                }
            return status, task_view(connection, task)

    def system_view(self, task: UUID) -> dict:
        with self.db.open() as connection:
            return task_view(connection, load_task(connection, task))

    def approval(self, token: str, task_id: UUID, decision: str) -> dict:
        with self.db.open() as connection:
            approver, task = require_task(connection, token, task_id, Action.APPROVE)
            if approver.subject == task["subject"]:
                raise Fault("self_approval_denied", 403)
            approval = connection.execute(
                "SELECT *,expires_at>clock_timestamp() AS fresh FROM approvals WHERE task_id=%s FOR UPDATE",
                (task_id,),
            ).fetchone()
            if not approval or not approval["fresh"] or task["cancel_requested"]:
                raise Fault("approval_unavailable")
            if approval["decision"]:
                if approval["decision"] != decision:
                    raise Fault("approval_decision_conflict")
            elif task["state"] not in TERMINAL:
                connection.execute(
                    """UPDATE approvals SET decision=%s,approver=%s,credential_id=%s,decided_at=clock_timestamp()
                       WHERE task_id=%s""", (decision, approver.subject, approver.credential, task_id),
                )
                audit(connection, approver.tenant, approver.subject, f"approval_{decision}", task)
            else:
                raise Fault("approval_unavailable")
            return task_view(connection, load_task(connection, task_id))

    def cancel(self, token: str, task_id: UUID) -> dict:
        with self.db.open() as connection:
            identity, task = require_task(connection, token, task_id, Action.CANCEL)
            if not task["cancel_requested"]:
                connection.execute("UPDATE tasks SET cancel_requested=true WHERE id=%s", (task_id,))
                audit(connection, identity.tenant, identity.subject, "cancel_requested", task)
                if task["state"] not in TERMINAL and not load_receipt(connection, task):
                    record_receipt(connection, task, "cancelled", {"code": "cancelled"})
            return task_view(connection, load_task(connection, task_id))

    def artifact(self, token: str, artifact_id: UUID) -> Artifact:
        with self.db.open() as connection:
            identity = authenticate(connection, token=token)
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id=%s AND tenant=%s", (artifact_id, identity.tenant),
            ).fetchone()
            if not row:
                raise Fault("artifact_not_found", 404)
            task = load_task(connection, row["task_id"], identity.tenant)
            require_grant(connection, identity, task["capability"], task["version"], task["resource"], Action.ARTIFACT)
            data = self.blobs.read(row["digest"])
            if len(data) != row["size"]:
                raise Fault("artifact_corrupt", 503)
            return Artifact(data, row["media_type"])

    def engine(self, task_id: UUID, status: str, temporal_run_id: str | None) -> None:
        with self.db.open() as connection:
            task = load_task(connection, task_id)
            if not task["workflow_id"]:
                return
            closed = status in {"completed", "failed", "cancelled", "terminated", "timed_out"}
            if task["engine_state"] in {"completed", "failed", "cancelled", "terminated", "timed_out"} and not closed:
                return
            connection.execute(
                """UPDATE runs SET temporal_run_id=COALESCE(%s,temporal_run_id),engine_state=%s,
                    started_at=COALESCE(started_at,clock_timestamp()),
                    ended_at=CASE WHEN %s THEN COALESCE(ended_at,clock_timestamp()) ELSE ended_at END
                    WHERE task_id=%s""",
                (temporal_run_id, status, closed, task_id),
            )
            if closed and task["state"] not in TERMINAL and not load_receipt(connection, task):
                state = "cancelled" if status == "cancelled" else "failed"
                set_state(connection, task, state)
                audit(connection, task["tenant"], task["subject"], f"orchestration_{state}", task)

    def require_pinned_contract(self, task, cap: Capability) -> None:
        if (task["environment"] != self.catalog.environment or task["contract_hash"] != cap.fingerprint):
            raise Fault("contract_drift", 503)

    def gate(self, connection, task, cap: Capability) -> None:
        if task["cancel_requested"]:
            raise Fault("cancelled")
        self.require_pinned_contract(task, cap)
        identity = authenticate(connection, credential=task["credential_id"])
        if (identity.tenant, identity.subject) != (task["tenant"], task["subject"]):
            raise Fault("identity_mismatch", 403)
        self.catalog.release(connection, identity.tenant, cap, inflight=True)
        require_grant(connection, identity, cap.name, cap.version, task["resource"], Action.EXECUTE)
        if cap.approval:
            approval = connection.execute(
                "SELECT *,expires_at>clock_timestamp() AS fresh FROM approvals WHERE task_id=%s FOR SHARE",
                (task["id"],),
            ).fetchone()
            if not approval or not approval["fresh"] or approval["payload_hash"] != task["payload_hash"]:
                raise Fault("approval_unavailable")
            if approval["decision"] is None:
                raise Fault("approval_pending")
            if approval["decision"] != "approved" or approval["credential_id"] is None:
                raise Fault("approval_rejected")
            approver = authenticate(connection, credential=approval["credential_id"])
            if approver.tenant != identity.tenant or approver.subject != approval["approver"]:
                raise Fault("approval_unavailable")
            require_grant(connection, approver, cap.name, cap.version, task["resource"], Action.APPROVE)

    def readiness(self, task_id: UUID) -> str:
        with self.db.open() as connection:
            task = load_task(connection, task_id)
            if task["state"] in TERMINAL:
                return "done"
            try:
                cap = self.catalog.implementation(task["capability"], task["version"])
                self.gate(connection, task, cap)
            except Fault as fault:
                if fault.code == "approval_pending":
                    if task["state"] != "waiting":
                        set_state(connection, task, "waiting")
                    return "wait"
                self.reject(connection, task, fault)
                return "done"
            if task["state"] != "running":
                set_state(connection, task, "running")
            return "ready"

    @staticmethod
    def reject(connection, task, fault: Fault, attempt: UUID | None = None) -> None:
        if not load_receipt(connection, task) or attempt is not None:
            record_receipt(
                connection, task, "cancelled" if fault.code == "cancelled" else "denied",
                {"code": fault.code}, attempt,
            )

    def execute(self, task_id: UUID, *, agent_tool: str | None = None) -> bool:
        with TRACER.start_as_current_span("mingjing.execute") as span:
            # Keep a session lock over the reservation and the separate send
            # transaction. A closed session releases it even if the process died.
            with self.db.open() as lock:
                acquired = lock.execute(
                    "SELECT pg_try_advisory_lock(hashtextextended(%s,%s)) AS acquired",
                    (str(task_id), EXECUTION_LOCK_SEED),
                ).fetchone()
                if not acquired["acquired"]:
                    return False
                lock.commit()
                external = self.start_execution(task_id, span, agent_tool)
                if external:
                    self.send(task_id, *external)
                return True

    def start_execution(self, task_id: UUID, span, agent_tool: str | None):
        with self.db.open() as connection:
            task = load_task(connection, task_id)
            span.set_attributes({key: str(task[field]) for key, field in (
                ("task_id", "id"), ("run_id", "run_id"), ("operation_id", "operation_id"),
            )})
            if task["workflow_id"]:
                span.set_attribute("workflow_id", task["workflow_id"])
            if task["state"] in TERMINAL:
                return None
            previous = load_receipt(connection, task)
            if previous:
                if previous["state"] == "dispatching":
                    self.mark_unknown(connection, task, previous["attempt_id"])
                return None
            try:
                cap = self.catalog.implementation(task["capability"], task["version"])
                self.gate(connection, task, cap)
                if cap.kind == Kind.AGENT and agent_tool != "append_note":
                    raise Fault("agent_tool_denied", 403)
                if cap.kind != Kind.AGENT and agent_tool is not None:
                    raise Fault("agent_tool_denied", 403)
            except Fault as fault:
                if fault.code == "approval_pending":
                    set_state(connection, task, "waiting")
                else:
                    self.reject(connection, task, fault)
                return None
            attempt = uuid4()
            span.set_attribute("attempt_id", str(attempt))
            connection.execute(
                "UPDATE runs SET started_at=COALESCE(started_at,clock_timestamp()) WHERE task_id=%s", (task_id,),
            )
            audit(connection, task["tenant"], task["subject"], "execution_allowed", task, attempt)
            if cap.provider:
                if not connection.execute(
                    "UPDATE budgets SET available=available-%s WHERE tenant=%s AND available>=%s RETURNING available",
                    (cap.budget, task["tenant"], cap.budget),
                ).fetchone():
                    self.reject(connection, task, Fault("budget_unavailable"))
                    return None
                connection.execute(
                    "INSERT INTO attempts(id,operation_id,state,reserved) VALUES (%s,%s,'reserved',%s)",
                    (attempt, task["operation_id"], cap.budget),
                )
                record_receipt(connection, task, "dispatching", {"code": "dispatch_inflight"}, attempt)
                return attempt, cap
            connection.execute(
                "INSERT INTO attempts(id,operation_id,state,reserved,actual) VALUES (%s,%s,'settled',0,0)",
                (attempt, task["operation_id"]),
            )
            context = context_for(task, attempt)
            assert cap.handler is not None
            result = cap.handler(cap.validate_input(task["payload"]), context, TransactionNotes(connection, context))
            outcome = {"value": cap.validate_output(result.value)}
            if result.artifact is not None:
                if not cap.produces_artifact:
                    raise Fault("artifact_contract_mismatch", 503)
                artifact = save_artifact(connection, self.blobs, task, result.artifact)
                outcome["artifact_id"] = artifact
                span.set_attribute("artifact_id", artifact)
            record_receipt(connection, task, "succeeded", outcome, attempt)
            return None

    def send(self, task_id: UUID, attempt: UUID, cap: Capability) -> None:
        assert cap.provider is not None
        may_have_sent = False
        try:
            with self.db.open() as connection:
                task = load_task(connection, task_id)
                receipt = load_receipt(connection, task)
                if not receipt or receipt["state"] != "dispatching" or receipt["attempt_id"] != attempt:
                    return
                try:
                    self.gate(connection, task, cap)
                except Fault as fault:
                    self.finish_budget(connection, task, attempt, cap.budget, 0, None, "released")
                    self.reject(connection, task, fault, attempt)
                    return
                may_have_sent = True
                try:
                    reply = cap.provider.send(cap.validate_input(task["payload"]), context_for(task, attempt))
                except Exception:
                    reply = None
                self.confirm_external(connection, task, cap, attempt, reply)
        except (psycopg.Error, Fault, ValueError):
            if not may_have_sent:
                raise
            # The committed dispatch record prevents a second send even if this write fails.
            with self.db.open() as connection:
                task = load_task(connection, task_id)
                if load_receipt(connection, task)["state"] == "dispatching":
                    self.mark_unknown(connection, task, attempt)

    @staticmethod
    def finish_budget(connection, task, attempt: UUID, reserved: int, units: int,
                      reference: str | None, state: str) -> None:
        changed = connection.execute(
            """UPDATE attempts SET state=%s,actual=%s,provider_reference=%s
               WHERE id=%s AND operation_id=%s AND reserved=%s AND state IN ('reserved','unknown')
               RETURNING id""",
            (state, units, reference, attempt, task["operation_id"], reserved),
        ).fetchone()
        if not changed:
            raise Fault("budget_settlement_conflict")
        updated = connection.execute(
            "UPDATE budgets SET available=available+%s WHERE tenant=%s RETURNING available",
            (reserved - units, task["tenant"]),
        ).fetchone()
        if not updated:
            raise Fault("budget_unavailable", 503)

    @staticmethod
    def mark_unknown(connection, task, attempt: UUID) -> None:
        connection.execute("UPDATE attempts SET state='unknown' WHERE id=%s AND state='reserved'", (attempt,))
        record_receipt(connection, task, "unknown", {"code": "provider_result_unknown"}, attempt)

    def confirm_external(self, connection, task, cap: Capability, attempt: UUID,
                         reply: ProviderReceipt | None) -> None:
        if not reply or type(reply.units) is not int or not 0 <= reply.units <= cap.budget or not reply.reference:
            self.mark_unknown(connection, task, attempt)
            return
        value = cap.validate_output(reply.value)
        self.finish_budget(connection, task, attempt, cap.budget, reply.units, reply.reference, "settled")
        record_receipt(connection, task, "succeeded", {"value": value}, attempt)

    def reconcile(self, token: str, task_id: UUID) -> dict:
        with self.db.open() as connection:
            available = connection.execute(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(%s,%s)) AS acquired",
                (str(task_id), EXECUTION_LOCK_SEED),
            ).fetchone()
            identity, task = require_task(connection, token, task_id, Action.RECONCILE)
            if not available["acquired"]:
                raise Fault("dispatch_inflight")
            cap = self.catalog.implementation(task["capability"], task["version"])
            receipt = load_receipt(connection, task)
            if not cap.provider or not receipt or not receipt["attempt_id"]:
                raise Fault("reconciliation_unavailable")
            if receipt["state"] in ("dispatching", "unknown"):
                self.require_pinned_contract(task, cap)
                answer = cap.provider.lookup(task["operation_id"])
                self.confirm_external(connection, task, cap, receipt["attempt_id"], answer)
                audit(connection, identity.tenant, identity.subject, "reconciliation_checked", task, receipt["attempt_id"])
            return task_view(connection, load_task(connection, task_id))
