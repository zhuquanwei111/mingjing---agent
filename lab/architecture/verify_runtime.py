"""Two-phase, live PostgreSQL and Temporal probe. Run only inside the route's isolated network."""
import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
from datetime import timedelta

import psycopg
from temporalio.client import Client
from temporalio.worker import Worker

from probe_workflow import PreflightWorkflow


def config(route):
    run = os.environ["MJLAB_RUN"]
    if re.fullmatch(r"[a-f0-9]{12,24}", run) is None:
        raise ValueError("MJLAB_RUN must be a unique hexadecimal experiment identifier")
    return f"mjlab_{route}_{run}"


async def probe(phase, route):
    scope = config(route)
    # Both endpoints are Compose-only service aliases. The runner is attached only to its own lab network.
    client = await Client.connect("temporal:7233", namespace=scope)
    with psycopg.connect(host="db", port=5432, dbname=scope, user=scope,
                         password=os.environ["MJLAB_DB_PASSWORD"], connect_timeout=5) as conn:
        if phase == "write":
            marker = secrets.token_hex(24)
            conn.execute("CREATE TABLE IF NOT EXISTS probe_witness "
                         "(scope text PRIMARY KEY, marker text NOT NULL)")
            conn.execute("INSERT INTO probe_witness(scope,marker) VALUES (%s,%s)", (scope, marker))
            conn.commit()
            async with Worker(client, task_queue=scope, workflows=[PreflightWorkflow]):
                returned = await client.execute_workflow(
                    PreflightWorkflow.run, marker, id=scope, task_queue=scope,
                    execution_timeout=timedelta(seconds=45),
                )
            if returned != marker:
                raise RuntimeError("workflow result differs from the committed marker")
        else:
            witness = conn.execute("SELECT marker FROM probe_witness WHERE scope=%s", (scope,)).fetchone()
            if witness is None:
                raise RuntimeError("committed PostgreSQL marker missing")
            marker = witness[0]
            handle = client.get_workflow_handle(scope)
            result = await handle.result()
            history = await handle.fetch_history()
            if result != marker or not history.events:
                raise RuntimeError("stored workflow result/history and PostgreSQL marker disagree")
    print(json.dumps({"phase": phase, "scope": scope,
                      "marker_sha256": hashlib.sha256(marker.encode()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("write", "readback"))
    parser.add_argument("route", choices=("a", "b"))
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(probe(args.phase, args.route), timeout=90))
