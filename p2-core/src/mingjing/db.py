from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .contracts import Fault, Identity


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def open(self):
        return psycopg.connect(
            self.dsn, row_factory=dict_row, connect_timeout=3,
            options="-c lock_timeout=3000 -c statement_timeout=8000",
        )

    def migrate(self, directory: Path) -> list[str]:
        applied = []
        with self.open() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (687201,))
            connection.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    name text PRIMARY KEY, digest text NOT NULL, applied_at timestamptz DEFAULT clock_timestamp()
                )"""
            )
            known = {
                row["name"]: row["digest"] for row in connection.execute("SELECT name,digest FROM schema_migrations")
            }
            paths = sorted(directory.glob("*.sql"))
            if not paths or not known.keys() <= {path.name for path in paths}:
                raise RuntimeError("migration history does not match the checkout")
            for path in paths:
                raw = path.read_bytes()
                digest = sha256(raw).hexdigest()
                if path.name in known:
                    if known[path.name] != digest:
                        raise RuntimeError(f"applied migration was edited: {path.name}")
                    continue
                if known and path.name < max(known):
                    raise RuntimeError(f"out-of-order migration: {path.name}")
                connection.execute(raw.decode())
                connection.execute("INSERT INTO schema_migrations VALUES (%s,%s,DEFAULT)", (path.name, digest))
                applied.append(path.name)
        return applied

    def add_identity(self, tenant: str, subject: str, token: str, expires: datetime, *, administrator=False) -> UUID:
        if len(token) < 32 or expires.tzinfo is None:
            raise ValueError("use a high-entropy token and a timezone-aware expiration")
        credential = uuid4()
        with self.open() as connection:
            connection.execute(
                """INSERT INTO subjects(tenant,subject,administrator) VALUES (%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (tenant, subject, administrator),
            )
            registered = connection.execute(
                "SELECT administrator FROM subjects WHERE tenant=%s AND subject=%s FOR SHARE",
                (tenant, subject),
            ).fetchone()
            if registered["administrator"] != administrator:
                raise ValueError("requested role differs from the existing subject")
            connection.execute(
                "INSERT INTO credentials(id,tenant,subject,fingerprint,expires_at) VALUES (%s,%s,%s,%s,%s)",
                (credential, tenant, subject, token_hash(token), expires),
            )
        return credential


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def authenticate(connection, *, token: str | None = None, credential: UUID | None = None) -> Identity:
    if token is not None and 32 <= len(token) <= 512:
        clause, value = "c.fingerprint=%s", token_hash(token)
    elif credential is not None:
        clause, value = "c.id=%s", credential
    else:
        raise Fault("unauthenticated", 401)
    row = connection.execute(
        f"""SELECT c.id,c.tenant,c.subject,s.administrator
            FROM credentials c JOIN subjects s USING (tenant,subject)
            WHERE {clause} AND NOT c.revoked AND c.expires_at>clock_timestamp() AND s.enabled
            FOR SHARE OF c,s""", (value,),
    ).fetchone()
    if not row:
        raise Fault("unauthenticated", 401)
    return Identity(row["id"], row["tenant"], row["subject"], row["administrator"])


def audit(connection, tenant: str, subject: str, event: str, task=None, attempt=None) -> None:
    connection.execute(
        "INSERT INTO audit(tenant,subject,task_id,operation_id,attempt_id,event) VALUES (%s,%s,%s,%s,%s,%s)",
        (tenant, subject, task["id"] if task else None, task["operation_id"] if task else None, attempt, event),
    )
