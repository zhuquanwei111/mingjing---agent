"""The scripted fixture can propose only synthetic requests."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Proposal:
    tool: str = "record"
    steps: int = 1
    depth: int = 0


def propose(scenario: str) -> Proposal:
    return {
        "test-denied-tool": Proposal(tool="unregistered"),
        "test-steps": Proposal(steps=3),
        "test-depth": Proposal(depth=2),
    }.get(scenario, Proposal())
