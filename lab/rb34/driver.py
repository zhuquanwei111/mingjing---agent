"""Out-of-band controller. Assert against independent receiving ledgers and persisted workflow history."""
import asyncio
import hashlib
import json
import os
from pathlib import Path

import psycopg
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client
from flow import GovernedRequest, ReceiptNotice
from product import db, log, setup

OUT = Path(os.environ["OUT"])
RAW = OUT / "raw.jsonl"
CASES = (
    ("normal", True, "active", True, False),
    ("default-revoke", False, "revoked", True, False),
    ("default-cancel", False, "cancelled", True, False),
    ("guard-revoke", True, "revoked", True, False),
    ("guard-cancel", True, "cancelled", True, False),
    ("late-revoke", True, "revoked", True, True),
    ("late-cancel", True, "cancelled", True, True),
    ("key-only", True, "active", False, False),
)


def witness():
    return psycopg.connect(os.environ["WITNESS_DSN"])


def record(scope, kind, payload):
    line = json.dumps([scope, kind, payload], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    with RAW.open("a", encoding="ascii") as stream:
        stream.write(line + "\n")
    print("RB34_RAW " + line, flush=True)


def snapshot(scope):
    with witness() as conn:
        def rows(statement):
            return conn.execute(statement, (scope,)).fetchall()
        published, = rows("SELECT published FROM fixtures WHERE scope=%s")[0]
        arrivals = rows("SELECT id,op,digest,sdk_retry FROM arrival WHERE scope=%s ORDER BY id")
        effects = rows("SELECT op,digest FROM effect WHERE scope=%s ORDER BY op")
        fees = rows("SELECT arrival_id,units FROM charge WHERE scope=%s ORDER BY arrival_id")
        deliveries = rows("SELECT id,op FROM delivery WHERE scope=%s ORDER BY id")
        lookups = rows("SELECT id,found FROM lookup WHERE scope=%s ORDER BY id")
    with db() as conn:
        state, held, spent, authority, digest = conn.execute(
            "SELECT state,held,spent,authority,digest FROM job WHERE scope=%s", (scope,)
        ).fetchone()
        ledger = conn.execute("SELECT receipt_id,units FROM fee WHERE scope=%s ORDER BY receipt_id", (scope,)).fetchall()
    return dict(counts=list(map(len, (arrivals,effects,fees,deliveries))), arrivals=arrivals, effects=effects,
                fees=fees, deliveries=deliveries, lookups=lookups, state=state, held=held, spent=spent,
                authority=authority, digest=digest, product_fees=ledger, receipt_published=published)


async def history(handle, scope, label):
    hist = await handle.fetch_history()
    (OUT / f"{scope}-{label}-history.json").write_text(hist.to_json(), encoding="utf8")
    events = [[ev.event_id, EventType.Name(ev.event_type)] for ev in hist.events]
    record(scope, label + "_history", {"workflow": handle.id, "run": hist.run_id, "events": events})
    assert events[-1][1] == "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED", events
    return [name for _, name in events]


async def notice(client, scope, index):
    handle = await client.start_workflow(ReceiptNotice.run, scope, id=f"{scope}-receipt-{index}", task_queue="rb34")
    assert await asyncio.wait_for(handle.result(), 35) == "confirmed"
    await history(handle, scope, f"notice-{index}")


async def run_case(client, scope, guarded, action, can_lookup, late):
    drop = scope != "normal"
    with witness() as conn:
        conn.execute("INSERT INTO fixtures VALUES (%s,%s,%s)", (scope, drop, False))
    with db() as conn:
        conn.execute("INSERT INTO job(scope,guarded,can_lookup) VALUES (%s,%s,%s)", (scope, guarded, can_lookup))
    handle = await client.start_workflow(GovernedRequest.run, scope, id=scope, task_queue="rb34")
    signaled = drop and action != "active"
    if drop:
        async with asyncio.timeout(35):
            while True:
                with db() as conn:
                    fault, = conn.execute("SELECT fault_seen FROM job WHERE scope=%s", (scope,)).fetchone()
                if fault:
                    break
                await asyncio.sleep(.10)
        before = snapshot(scope)
        record(scope, "before_control", before)
        assert not before["receipt_published"]
        assert before["counts"] == [1,1,1,0] and (before["held"],before["spent"],before["authority"]) == (3,0,"active")
        with db() as conn:
            conn.execute("UPDATE job SET authority=%s WHERE scope=%s", (action,scope))
            log(conn, scope, "control", authority=action)
        if signaled:
            await handle.signal(GovernedRequest.product_control, action)
        with db() as conn:
            conn.execute("UPDATE job SET released=true WHERE scope=%s", (scope,))
            log(conn, scope, "release")
    outcome = await asyncio.wait_for(handle.result(), 105)
    assert outcome["observed_control"] == action, outcome
    events = await history(handle, scope, "dispatch")
    assert ("EVENT_TYPE_WORKFLOW_EXECUTION_SIGNALED" in events) == signaled
    recovered = snapshot(scope)
    record(scope, "after_recovery", recovered)
    unknown = guarded and drop
    expected = [1 if guarded else 2, 1, 1 if guarded else 2, int(not drop)]
    assert recovered["counts"] == expected, recovered
    assert recovered["authority"] == action
    assert [a[3] for a in recovered["arrivals"]] == (["0"] if guarded else ["0","1"])
    assert all(a[1:3] == ("op-" + scope, recovered["digest"]) for a in recovered["arrivals"])
    assert outcome["result"] == recovered["state"] == ("unknown" if unknown else "confirmed")
    assert (recovered["held"], recovered["spent"]) == ((3,0) if unknown else (0,expected[2]))
    if unknown:
        assert recovered["product_fees"] == []
        assert [found for _,found in recovered["lookups"]] == ([False] if can_lookup else [])
    if late:
        with witness() as conn:
            conn.execute("UPDATE fixtures SET published=true WHERE scope=%s", (scope,))
    if late or not drop:
        for i in (1,2):
            await notice(client, scope, i)
            record(scope, f"notice-{i}", snapshot(scope))
    end = snapshot(scope)
    record(scope, "final", end)
    assert end["counts"] == expected
    assert (end["held"],end["spent"]) == ((3,0) if unknown and not late else (0,expected[2]))
    if not unknown or late:
        assert end["fees"] == end["product_fees"]
    if late:
        assert [found for _,found in end["lookups"]] == [False,True,True]
    with db() as conn:
        trace = conn.execute("SELECT id,kind,detail,recorded FROM event WHERE scope=%s ORDER BY id", (scope,)).fetchall()
    for seq, kind, detail, at in trace:
        record(scope, "product_event", [seq,kind,detail,at.isoformat()])
    kinds = [kind for _,kind,_,_ in trace]
    assert [d["attempt"] for _,k,d,_ in trace if k == "activity"] == ([1,2] if unknown else [1])
    assert [d["authority"] for _,k,d,_ in trace if k == "wire_attempt"] == (["active"] if guarded else ["active",action])
    if drop:
        assert kinds.index("wire_attempt") < kinds.index("wire_error") < kinds.index("control") < kinds.index("release")
        assert [d["error"] for _,k,d,_ in trace if k == "wire_error"] == ["RemoteProtocolError"]
        if not guarded:
            assert kinds.index("release") < max(i for i,k in enumerate(kinds) if k=="wire_attempt")
    if late or not drop:
        assert [d["added"] for _,k,d,_ in trace if k == "settle"] == ([1,0] if late else [1,0,0])
    print("RB34_CASE", scope, "PASS", expected, "held", end["held"], "spent", end["spent"], flush=True)
    return end["arrivals"][0][2]


async def main():
    setup()
    client = await Client.connect("temporal:7233", namespace=os.environ["NAMESPACE"])
    record("run", "identity", {"head": os.environ["TEST_HEAD"], "run": os.environ["CI_RUN"], "namespace": os.environ["NAMESPACE"]})
    input_digests = {}
    for case in CASES:
        input_digests[case[0]] = await run_case(client, *case)
    record("run", "receiver_input_digests", input_digests)
    assert len(set(input_digests.values())) == 1, input_digests
    print("RB34_RAW_SHA256", hashlib.sha256(RAW.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
