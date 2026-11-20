from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError


class Kind(StrEnum):
    DIRECT = "direct_program"
    WORKFLOW = "durable_workflow"
    AGENT = "agent_loop"
    EXTERNAL = "external_service"


class Action(StrEnum):
    EXECUTE = "execute"
    READ = "read"
    APPROVE = "approve"
    CANCEL = "cancel"
    ARTIFACT = "artifact"
    RECONCILE = "reconcile"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Fault(Exception):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Identity:
    credential: UUID
    tenant: str
    subject: str
    administrator: bool


@dataclass(frozen=True)
class CapabilityContext:
    tenant: str
    subject: str
    task_id: UUID
    run_id: UUID
    operation_id: UUID
    attempt_id: UUID
    resource: str


@dataclass(frozen=True)
class Result:
    value: dict
    artifact: bytes | None = None


@dataclass(frozen=True)
class ProviderReceipt:
    reference: str
    units: int
    value: dict


class NotesPort(Protocol):
    def append(self, context: CapabilityContext, value: str) -> None: ...


class Handler(Protocol):
    def __call__(self, data: BaseModel, context: CapabilityContext, notes: NotesPort) -> Result: ...


class ExternalPort(Protocol):
    def send(self, data: BaseModel, context: CapabilityContext) -> ProviderReceipt | None: ...
    def lookup(self, operation_id: UUID) -> ProviderReceipt | None: ...


@dataclass(frozen=True)
class Capability:
    name: str
    version: int
    kind: Kind
    input: type[Model]
    output: type[Model]
    handler: Handler | None = None
    provider: ExternalPort | None = None
    approval: bool = False
    budget: int = 0
    produces_artifact: bool = False

    def __post_init__(self) -> None:
        if self.kind == Kind.EXTERNAL:
            if not self.provider or self.handler or self.budget <= 0:
                raise ValueError("external adapters require a known positive cost bound")
        elif not self.handler or self.provider or self.budget:
            raise ValueError("internal adapters require an in-process handler")

    def description(self) -> dict:
        return {
            "capability_id": self.name, "version": self.version,
            "execution_kind": self.kind, "input_schema": self.input.model_json_schema(),
            "output_schema": self.output.model_json_schema(),
            "implementation_ref": f"{self.name}@{self.version}",
            "side_effect_class": "external" if self.provider else "internal_transaction",
            "required_permissions": [Action.EXECUTE], "resource_scope": "exact",
            "timeout_policy": {"activity_seconds": 20, "execution_hours": 24},
            "retry_policy": "internal_activity" if not self.provider else "reconcile_only",
            "idempotency_policy": "stable_operation_id",
            "approval_policy": "required" if self.approval else "none",
            "budget_units": self.budget, "artifact_types": ["text/plain"] if self.produces_artifact else [],
        }

    @property
    def fingerprint(self) -> str:
        return digest(self.description())

    def validate_input(self, payload: dict) -> BaseModel:
        try:
            return self.input.model_validate(payload)
        except ValidationError as error:
            raise Fault("invalid_input", 422) from error

    def validate_output(self, payload: dict) -> dict:
        try:
            return self.output.model_validate(payload).model_dump(mode="json")
        except ValidationError as error:
            raise Fault("invalid_adapter_output", 503) from error


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
