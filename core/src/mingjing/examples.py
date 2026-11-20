"""Three SDK capability templates and the separate synthetic provider adapter."""

from typing import Annotated, Literal, cast
from uuid import UUID

from pydantic import BaseModel, Field

from .contracts import Capability, CapabilityContext, Kind, Model, NotesPort, ProviderReceipt, Result
from .db import Database


class Text(Model):
    text: Annotated[str, Field(min_length=1, max_length=500)]


class Note(Model):
    content: Annotated[str, Field(min_length=1, max_length=500)]


class Stored(Model):
    stored: bool


class Delivery(Model):
    mode: Literal["accept", "lose_receipt", "unverifiable"]


class Delivered(Model):
    delivered: bool


def normalize(value: BaseModel, context: CapabilityContext, notes: NotesPort) -> Result:
    text = cast(Text, value).text.strip()
    if not text:
        text = cast(Text, value).text
    return Result({"text": text}, text.encode())


def append_note(value: BaseModel, context: CapabilityContext, notes: NotesPort) -> Result:
    notes.append(context, cast(Note, value).content)
    return Result({"stored": True})


class FakeProvider:
    def __init__(self, db: Database):
        self.db = db

    def send(self, data: BaseModel, context: CapabilityContext) -> ProviderReceipt | None:
        mode = cast(Delivery, data).mode
        if mode == "unverifiable":
            return None
        # A separate commit simulates a downstream receipt for synthetic data.
        with self.db.open() as connection:
            connection.execute(
                "INSERT INTO fake_provider_receipts VALUES (%s,%s,1)",
                (context.operation_id, f"synthetic:{context.operation_id}"),
            )
        return self.lookup(context.operation_id) if mode == "accept" else None

    def lookup(self, operation_id: UUID) -> ProviderReceipt | None:
        with self.db.open() as connection:
            row = connection.execute(
                "SELECT * FROM fake_provider_receipts WHERE operation_id=%s", (operation_id,),
            ).fetchone()
        return ProviderReceipt(row["reference"], row["charged"], {"delivered": True}) if row else None


def builtins(db: Database) -> tuple[Capability, ...]:
    return (
        Capability("normalize_text", 1, Kind.DIRECT, Text, Text, handler=normalize, produces_artifact=True),
        Capability("write_note", 1, Kind.WORKFLOW, Note, Stored, handler=append_note, approval=True),
        Capability("draft_note", 1, Kind.AGENT, Note, Stored, handler=append_note, approval=True),
        Capability("fake_delivery", 1, Kind.EXTERNAL, Delivery, Delivered, provider=FakeProvider(db), budget=2),
    )
