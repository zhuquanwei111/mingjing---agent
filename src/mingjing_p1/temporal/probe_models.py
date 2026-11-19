"""Importable payload types for the serialization and Continue-As-New probes."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from langchain_core.messages import AnyMessage
from pydantic import BaseModel
from temporalio.contrib.workflow_streams import WorkflowStreamState


@dataclass
class Cursor:
    phase: int = 0
    carried: dict | None = None
    first_serials: list[str] = field(default_factory=list)


class Detail(BaseModel):
    at: datetime
    identifier: UUID


class TypedInput(BaseModel):
    detail: Detail
    messages: list[AnyMessage]


@dataclass
class StreamInput:
    stage: int = 0
    stream: WorkflowStreamState | None = None
