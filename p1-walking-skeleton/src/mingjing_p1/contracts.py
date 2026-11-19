"""Small versioned boundary for the synthetic P1 capabilities."""

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

ExecutionKind = Literal["direct", "workflow", "agent"]


@dataclass(frozen=True)
class Capability:
    code: str
    side_effect: Literal["database", "external", "metered"]


CAPABILITIES = {
    capability.code: capability
    for capability in (
        Capability("record_marker@1", "database"),
        Capability("record_note@1", "database"),
        Capability("external_marker@1", "external"),
        Capability("meter_marker@1", "metered"),
    )
}


@dataclass(frozen=True)
class Principal:
    tenant: str
    subject: str


@dataclass(frozen=True)
class Job:
    task_id: str
    operation_id: str
    decision_id: str | None
    requires_approval: bool
    deadline_seconds: int = 20
    step_limit: int = 2
    depth_limit: int = 1
    kind: ExecutionKind = "workflow"
    scenario: str = "ordinary"
    deadline_epoch: float | None = None


class Rejected(Exception):
    def __init__(self, code: str, status: int = 403):
        super().__init__(code)
        self.code = code
        self.status = status


def digest(value: object) -> str:
    body = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()
