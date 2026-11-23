"""Evaluate a trusted evidence snapshot before the separate delivery authorization step."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


_REFERENCE = re.compile(r"ev_[0-9a-f]{32}")
ItemState = Literal["satisfied", "unsatisfied", "missing", "pending"]


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    rule_version: str
    required_items: tuple[str, ...]


@dataclass(frozen=True)
class Evidence:
    """One adapter-verified observation. Reuse its reference only for the same item."""

    task_id: str
    rule_version: str
    item: str
    reference: str
    outcome: str  # confirmed, denied, pending; unknown strings cannot confirm an item.


@dataclass(frozen=True)
class ItemResult:
    item: str
    state: ItemState
    reason: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class QualityResult:
    task_id: str
    rule_version: str
    items: tuple[ItemResult, ...]
    reason: str

    @property
    def ready(self) -> bool:
        return self.reason == "all_satisfied"


def _validate_contract(contract: TaskContract) -> None:
    if not isinstance(contract, TaskContract):
        raise TypeError("contract must be a TaskContract")
    if not isinstance(contract.required_items, tuple):
        raise TypeError("required_items must be an ordered tuple")
    for identifier in (contract.task_id, contract.rule_version, *contract.required_items):
        if not isinstance(identifier, str):
            raise TypeError("contract identifiers must be strings")
        if not identifier or identifier.strip() != identifier or not identifier.isprintable():
            raise ValueError("contract identifiers must be nonempty, printable and trimmed")
    if not contract.required_items or len(set(contract.required_items)) != len(contract.required_items):
        raise ValueError("required_items must contain at least one item and no duplicates")


def _item_result(item: str, records: list[Evidence]) -> ItemResult:
    outcomes = {record.outcome for record in records}
    refs = tuple(sorted({record.reference for record in records}))
    if not outcomes:
        return ItemResult(item, "missing", "no_evidence", refs)
    if len(outcomes) > 1:
        return ItemResult(item, "pending", "conflicting_evidence", refs)
    outcome = outcomes.pop()
    if outcome == "confirmed":
        return ItemResult(item, "satisfied", "confirmed", refs)
    if outcome == "denied":
        return ItemResult(item, "unsatisfied", "denied", refs)
    reason = "pending_verification" if outcome == "pending" else "unknown_outcome"
    return ItemResult(item, "pending", reason, refs)


def evaluate_quality(
    contract: TaskContract, evidence: tuple[Evidence, ...], *, verifier_available: bool
) -> QualityResult:
    """Return ordered item decisions. A ready result alone grants no authority to send."""

    _validate_contract(contract)
    if not isinstance(evidence, tuple) or type(verifier_available) is not bool:
        raise TypeError("evidence must be a tuple and verifier_available must be a bool")

    by_item: dict[str, list[Evidence]] = {item: [] for item in contract.required_items}
    reference_owner: dict[str, str] = {}
    problems = set()
    if not verifier_available:
        problems.add("verifier_unavailable")
    for record in evidence:
        if not isinstance(record, Evidence):
            raise TypeError("each observation must be an Evidence record")
        fields = (record.task_id, record.rule_version, record.item, record.reference, record.outcome)
        if not all(isinstance(value, str) for value in fields):
            raise TypeError("evidence fields must be strings")
        if (record.task_id, record.rule_version) != (contract.task_id, contract.rule_version):
            problems.add("binding_mismatch")
        if not _REFERENCE.fullmatch(record.reference):
            problems.add("invalid_reference")
        if reference_owner.setdefault(record.reference, record.item) != record.item:
            problems.add("cross_item_replay")
        if record.item in by_item:
            by_item[record.item].append(record)
        else:
            problems.add("undeclared_item")

    # A rejected snapshot exposes no partial results. Report a stable reason in either input order.
    for reason in ("verifier_unavailable", "binding_mismatch", "invalid_reference",
                   "cross_item_replay", "undeclared_item"):
        if reason in problems:
            items = tuple(ItemResult(item, "pending", reason, ()) for item in contract.required_items)
            return QualityResult(contract.task_id, contract.rule_version, items, reason)

    items = tuple(_item_result(item, records) for item, records in by_item.items())
    ready = all(result.state == "satisfied" for result in items)
    return QualityResult(contract.task_id, contract.rule_version, items,
                         "all_satisfied" if ready else "requirements_unmet")
