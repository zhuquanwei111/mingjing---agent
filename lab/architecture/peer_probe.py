"""Prove each real read-only observer is accepted on its own DB and rejected on its peer."""
import hashlib
import os

import psycopg

local = os.environ["MJLAB_ROUTE"]
for label in ("a", "b"):
    identity = f"audit_{label}_{os.environ['MJLAB_CI_RUN']}"
    valid = hashlib.sha256(f"{identity}/{os.environ['GITHUB_SHA']}".encode()).hexdigest()
    for password in ([valid, "intentionally-invalid"] if label == local else [valid]):
        expected = label == local and password == valid
        try:
            with psycopg.connect(host="db", dbname=os.environ["LAB_PROBE_DB"], user=identity,
                                 password=password, connect_timeout=5) as db:
                assert db.execute("select count(*) from probe_witness").fetchone()[0] == 1
        except psycopg.OperationalError as exc:
            if expected or "password authentication failed" not in str(exc):
                raise
            print("ISOLATION", local, label, "database rejected credentials")
        else:
            if not expected:
                raise RuntimeError("foreign or invalid credentials could read the current database")
            print("ISOLATION", local, label, "own marker read back")
