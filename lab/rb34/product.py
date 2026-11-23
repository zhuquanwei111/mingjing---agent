"""Experimental product state. Only the fixture controller can access the receiver's database."""
import asyncio
import hashlib
import json
import os
from urllib.request import Request, urlopen

import httpx2 as httpx
import psycopg
from psycopg.types.json import Jsonb
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from temporalio import activity
from temporalio.exceptions import ApplicationError


def db():
    return psycopg.connect(os.environ["PRODUCT_DSN"], options="-c lock_timeout=5s")


def setup():
    with db() as conn:
        conn.execute("""
            CREATE TABLE job (
                scope text PRIMARY KEY, guarded boolean, can_lookup boolean,
                authority text DEFAULT 'active', fault_seen boolean DEFAULT false,
                released boolean DEFAULT false, state text DEFAULT 'new', digest text,
                held int DEFAULT 0, spent int DEFAULT 0, delivery_claim boolean DEFAULT false
            );
            CREATE TABLE event (id bigserial PRIMARY KEY, scope text, kind text,
                                detail jsonb, recorded timestamptz DEFAULT clock_timestamp());
            CREATE TABLE fee (scope text, receipt_id bigint, units int, PRIMARY KEY(scope,receipt_id))
        """)


def log(conn, scope, kind, **detail):
    conn.execute("INSERT INTO event(scope,kind,detail) VALUES (%s,%s,%s)", (scope, kind, Jsonb(detail)))


class ObserveWire(httpx.AsyncHTTPTransport):
    def __init__(self, scope):
        super().__init__(retries=0)
        self.scope = scope
        self.observed_disconnect = False
        self.released_disconnect = False

    async def handle_async_request(self, request):
        scope = self.scope
        request.headers["Idempotency-Key"] = "op-" + scope
        digest = hashlib.sha256(await request.aread()).hexdigest()
        with db() as conn:
            authority, previous = conn.execute(
                "SELECT authority,digest FROM job WHERE scope=%s FOR UPDATE", (scope,)
            ).fetchone()
            if previous and digest != previous:
                raise ValueError("request fingerprint changed")
            conn.execute("UPDATE job SET digest=%s WHERE scope=%s", (digest, scope))
            log(conn, scope, "wire_attempt", authority=authority, digest=digest,
                sdk_retry=request.headers.get("x-stainless-retry-count"))
        try:
            return await super().handle_async_request(request)
        except httpx.TransportError as error:
            if self.observed_disconnect:
                raise
            self.observed_disconnect = True
            with db() as conn:
                conn.execute("UPDATE job SET fault_seen=true WHERE scope=%s", (scope,))
                log(conn, scope, "wire_error", error=type(error).__name__, message=str(error))
            async with asyncio.timeout(40):
                while True:
                    with db() as conn:
                        released, = conn.execute("SELECT released FROM job WHERE scope=%s", (scope,)).fetchone()
                    if released:
                        break
                    await asyncio.sleep(.08)
            self.released_disconnect = True
            raise


def reconcile(scope):
    with db() as conn:
        capable, = conn.execute("SELECT can_lookup FROM job WHERE scope=%s", (scope,)).fetchone()
    if not capable:
        return "unknown"
    with urlopen(f"http://provider:8080/{scope}/receipt", timeout=5) as response:
        receipt = json.load(response)
    if not receipt["known"]:
        return "unknown"
    with db() as conn:
        digest, authority, claimed = conn.execute(
            "SELECT digest,authority,delivery_claim FROM job WHERE scope=%s FOR UPDATE", (scope,)
        ).fetchone()
        if receipt["scope"] != scope or receipt["effect"] != ["op-" + scope, digest] or not receipt["fees"]:
            raise ValueError("receipt binding mismatch")
        added = 0
        for fee_id, units in receipt["fees"]:
            if units != 1:
                raise ValueError("unexpected fee units")
            paid = conn.execute("""INSERT INTO fee VALUES (%s,%s,%s) ON CONFLICT DO NOTHING
                                  RETURNING units""", (scope, fee_id, units)).fetchone()
            if paid:
                added += paid[0]
        deliver = authority == "active" and not claimed
        conn.execute("""UPDATE job SET held=0,spent=spent+%s,state='confirmed',
                        delivery_claim=delivery_claim OR %s WHERE scope=%s""", (added, deliver, scope))
        log(conn, scope, "settle", added=added, authority=authority, deliver=deliver)
    if deliver:
        request = Request(f"http://delivery:8080/{scope}/deliver", data=b"{}", headers={"Idempotency-Key": "op-" + scope})
        with urlopen(request, timeout=5) as response:
            if not json.load(response)["received"]:
                raise ValueError("receiver failed")
    return "confirmed"


@activity.defn
async def reconcile_notice(scope: str) -> str:
    return reconcile(scope)


@activity.defn
async def dispatch(scope: str) -> str:
    attempt = activity.info().attempt
    with db() as conn:
        state, authority, guarded = conn.execute(
            "SELECT state,authority,guarded FROM job WHERE scope=%s FOR UPDATE", (scope,)
        ).fetchone()
        log(conn, scope, "activity", attempt=attempt, state=state, authority=authority)
        if state == "new":
            if authority != "active":
                raise ApplicationError("authority denied", non_retryable=True)
            conn.execute("UPDATE job SET state='sent',held=3 WHERE scope=%s", (scope,))
            log(conn, scope, "reserve", units=3)
    if state != "new":
        return reconcile(scope)
    transport = ObserveWire(scope)
    async with httpx.AsyncClient(transport=transport, timeout=10, trust_env=False) as client:
        provider = OpenAIProvider(base_url=f"http://provider:8080/{scope}/v1", api_key="fixture-only", http_client=client)
        model = OpenAIChatModel("fixture-model", provider=provider)
        settings = {"temperature": 0}
        if guarded:
            settings["max_retries"] = 0
        agent = Agent(model, model_settings=settings)
        try:
            result = await agent.run("Check the synthetic receipt.")
        except Exception as exc:
            if not transport.released_disconnect:
                raise ApplicationError(f"unexpected model failure: {type(exc).__name__}: {exc}", non_retryable=True) from exc
            with db() as conn:
                conn.execute("UPDATE job SET state='unknown' WHERE scope=%s", (scope,))
                log(conn, scope, "unknown", error=type(exc).__name__)
            raise ApplicationError("request receipt unknown") from exc
        if result.output != "accepted":
            raise ApplicationError("unexpected model response", non_retryable=True)
    return reconcile(scope)
