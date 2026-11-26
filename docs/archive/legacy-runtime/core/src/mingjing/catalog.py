from __future__ import annotations

from collections.abc import Iterable

from psycopg.types.json import Jsonb

from .contracts import Action, Capability, Fault, Identity
from .db import Database, audit, authenticate


def require_grant(connection, identity: Identity, capability: str, version: int, resource: str, action: Action) -> None:
    found = connection.execute(
        """SELECT allowed FROM grants
           WHERE tenant=%s AND subject=%s AND capability=%s AND version=%s AND resource=%s AND action=%s
           FOR SHARE""",
        (identity.tenant, identity.subject, capability, version, resource, action.value),
    ).fetchone()
    if found is None or not found["allowed"]:
        raise Fault("permission_denied", 403)


class Catalog:
    def __init__(self, db: Database, environment: str, capabilities: Iterable[Capability]):
        if not environment:
            raise ValueError("environment is required")
        self.db = db
        self.environment = environment
        self.entries = {}
        for capability in capabilities:
            key = (capability.name, capability.version)
            if key in self.entries:
                raise ValueError(f"duplicate adapter {key}")
            self.entries[key] = capability

    def implementation(self, capability: str, version: int) -> Capability:
        try:
            return self.entries[capability, version]
        except KeyError as error:
            raise Fault("adapter_unavailable", 503) from error

    def key(self, tenant: str, capability: Capability) -> tuple:
        return tenant, capability.name, capability.version

    def release(self, connection, tenant: str, capability: Capability, *, inflight: bool = False) -> None:
        key = self.key(tenant, capability)
        registration = connection.execute(
            "SELECT state,fingerprint FROM releases WHERE tenant=%s AND capability=%s AND version=%s FOR SHARE",
            key,
        ).fetchone()
        if not registration or registration["state"] != "validated":
            raise Fault("release_unavailable", 403)
        if registration["fingerprint"] != capability.fingerprint:
            raise Fault("contract_drift", 503)
        publication = connection.execute(
            """SELECT state FROM publications
               WHERE tenant=%s AND capability=%s AND version=%s AND environment=%s FOR SHARE""",
            (*key, self.environment),
        ).fetchone()
        allowed = ("published", "deprecated") if inflight else ("published",)
        if not publication or publication["state"] not in allowed:
            raise Fault("release_unavailable", 403)

    def transition(self, token: str, name: str, version: int, target: str) -> dict:
        with self.db.open() as connection:
            identity = authenticate(connection, token=token)
            if not identity.administrator:
                raise Fault("administration_required", 403)
            key = (identity.tenant, name, version)
            capability = None if target == "disable" else self.implementation(name, version)
            if target == "register":
                assert capability is not None
                inserted = connection.execute(
                    """INSERT INTO releases VALUES (%s,%s,%s,'registered',%s,%s)
                       ON CONFLICT DO NOTHING RETURNING state""",
                    (*key, Jsonb(capability.description()), capability.fingerprint),
                ).fetchone()
                if not inserted:
                    raise Fault("already_registered")
                state = inserted["state"]
                contract = capability.description()
            else:
                release = connection.execute(
                    "SELECT * FROM releases WHERE tenant=%s AND capability=%s AND version=%s FOR UPDATE", key,
                ).fetchone()
                if not release:
                    raise Fault("release_not_found", 404)
                if capability is not None and release["fingerprint"] != capability.fingerprint:
                    raise Fault("contract_drift", 503)
                contract = release["contract"]
                if target == "validate":
                    if release["state"] != "registered":
                        raise Fault("invalid_transition")
                    connection.execute(
                        "UPDATE releases SET state='validated' WHERE tenant=%s AND capability=%s AND version=%s", key,
                    )
                    state = "validated"
                else:
                    state = self.update_publication(connection, key, release["state"], target)
            audit(connection, identity.tenant, identity.subject, f"capability_{state}", details={
                "capability_id": name, "version": version, "environment": self.environment,
            })
            return {**contract, "state": state, "environment": self.environment}

    def update_publication(self, connection, key: tuple, registration: str, target: str) -> str:
        if registration != "validated":
            raise Fault("invalid_transition")
        scope = (*key, self.environment)
        row = connection.execute(
            """SELECT state FROM publications
               WHERE tenant=%s AND capability=%s AND version=%s AND environment=%s FOR UPDATE""", scope,
        ).fetchone()
        previous = row["state"] if row else None
        transitions = {
            (None, "publish"): "published",
            ("published", "deprecate"): "deprecated",
            ("published", "disable"): "disabled",
            ("deprecated", "disable"): "disabled",
        }
        state = transitions.get((previous, target))
        if not state:
            raise Fault("invalid_transition")
        connection.execute(
            """INSERT INTO publications VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (tenant,capability,version,environment) DO UPDATE SET state=EXCLUDED.state""",
            (*scope, state),
        )
        return state

    def grant(self, token: str, subject: str, name: str, version: int, resource: str, action: Action, allowed: bool) -> None:
        with self.db.open() as connection:
            identity = authenticate(connection, token=token)
            if not identity.administrator:
                raise Fault("administration_required", 403)
            if not connection.execute(
                "SELECT 1 FROM subjects WHERE tenant=%s AND subject=%s", (identity.tenant, subject),
            ).fetchone():
                raise Fault("subject_not_found", 404)
            if not connection.execute(
                "SELECT 1 FROM releases WHERE tenant=%s AND capability=%s AND version=%s",
                (identity.tenant, name, version),
            ).fetchone():
                raise Fault("release_not_found", 404)
            connection.execute(
                """INSERT INTO grants VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (tenant,subject,capability,version,resource,action)
                   DO UPDATE SET allowed=EXCLUDED.allowed""",
                (identity.tenant, subject, name, version, resource, action.value, allowed),
            )
            audit(connection, identity.tenant, identity.subject, "grant_changed", details={
                "subject": subject, "capability_id": name, "version": version,
                "resource": resource, "action": action.value, "allowed": allowed,
            })

    def discover(self, token: str, resource: str) -> list[dict]:
        with self.db.open() as connection:
            identity = authenticate(connection, token=token)
            rows = connection.execute(
                """SELECT r.capability,r.version,r.contract,r.fingerprint
                    FROM releases r JOIN publications p USING (tenant,capability,version)
                    JOIN grants g USING (tenant,capability,version)
                    WHERE r.tenant=%s AND g.subject=%s AND g.action='execute' AND g.allowed
                    AND g.resource=%s AND p.environment=%s AND p.state='published' AND r.state='validated'
                    ORDER BY r.capability,r.version""",
                (identity.tenant, identity.subject, resource, self.environment),
            )
            return [
                row["contract"] for row in rows
                if (impl := self.entries.get((row["capability"], row["version"])))
                and impl.fingerprint == row["fingerprint"]
            ]
