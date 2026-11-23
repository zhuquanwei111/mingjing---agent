"""FR-24/36 and AC-15 at the trusted host/worker library boundary."""

from dataclasses import replace
import subprocess
import sys
import unittest

from mingjing_agent.quality import Evidence, ItemResult, TaskContract, evaluate_quality


CONTRACT = TaskContract("task-7", "rules-2", ("content", "approval"))
CONTENT = Evidence("task-7", "rules-2", "content", "ev_" + "a" * 32, "confirmed")
APPROVAL = replace(CONTENT, item="approval", reference="ev_" + "b" * 32)


class QualityTests(unittest.TestCase):
    def evaluate(self, *records, contract=CONTRACT, available=True):
        return evaluate_quality(contract, records, verifier_available=available)

    def assert_batch_rejected(self, records, reason, *, available=True):
        result = self.evaluate(*records, available=available)
        self.assertFalse(result.ready)
        self.assertEqual(result.reason, reason)
        self.assertEqual(result.items, tuple(ItemResult(item, "pending", reason, ())
                                             for item in CONTRACT.required_items))
        self.assertEqual(result, self.evaluate(*reversed(records), available=available))
        return result

    def test_all_items_confirmed_in_contract_order(self):
        result = self.evaluate(APPROVAL, CONTENT)
        self.assertTrue(result.ready)
        self.assertEqual((result.task_id, result.rule_version), ("task-7", "rules-2"))
        self.assertEqual(result.items, (
            ItemResult("content", "satisfied", "confirmed", (CONTENT.reference,)),
            ItemResult("approval", "satisfied", "confirmed", (APPROVAL.reference,)),
        ))
        self.assertEqual(result, self.evaluate(CONTENT, APPROVAL))

    def test_tool_success_does_not_cover_missing_approval(self):
        result = self.evaluate(CONTENT)
        self.assertFalse(result.ready)
        self.assertEqual(result.reason, "requirements_unmet")
        self.assertEqual(result.items[1], ItemResult("approval", "missing", "no_evidence", ()))
        self.assertTrue(all(i.state == "missing" for i in self.evaluate().items))

    def test_new_contract_item_needs_its_own_evidence(self):
        updated = replace(CONTRACT, required_items=(*CONTRACT.required_items, "provenance"))
        result = self.evaluate(CONTENT, APPROVAL, contract=updated)
        self.assertFalse(result.ready)
        self.assertEqual(result.items[2], ItemResult("provenance", "missing", "no_evidence", ()))

    def test_denied_pending_and_unknown_outcomes(self):
        for outcome, state, reason in [
            ("denied", "unsatisfied", "denied"),
            ("pending", "pending", "pending_verification"),
            ("tool_success", "pending", "unknown_outcome"),
        ]:
            with self.subTest(outcome=outcome):
                result = self.evaluate(CONTENT, replace(APPROVAL, outcome=outcome))
                self.assertFalse(result.ready)
                self.assertEqual(result.items[1], ItemResult("approval", state, reason, (APPROVAL.reference,)))
                self.assertNotIn("tool_success", repr(result))

    def test_exact_repeat_is_idempotent_and_distinct_references_are_sorted(self):
        second = replace(CONTENT, reference="ev_" + "0" * 32)
        expected = self.evaluate(CONTENT, second, APPROVAL)
        self.assertTrue(expected.ready)
        self.assertEqual(expected.items[0].references, (second.reference, CONTENT.reference))
        self.assertEqual(self.evaluate(APPROVAL, second, CONTENT, CONTENT, APPROVAL), expected)

    def test_conflicts_are_order_independent_even_when_reusing_the_same_reference(self):
        for reference in (CONTENT.reference, "ev_" + "c" * 32):
            for outcome in ("denied", "pending", "tool_success"):
                with self.subTest(reference=reference, outcome=outcome):
                    other = replace(CONTENT, reference=reference, outcome=outcome)
                    result = self.evaluate(CONTENT, other, APPROVAL)
                    self.assertFalse(result.ready)
                    self.assertEqual((result.items[0].state, result.items[0].reason),
                                     ("pending", "conflicting_evidence"))
                    self.assertEqual(result, self.evaluate(other, APPROVAL, CONTENT))

    def test_unavailable_verifier_invalidates_even_complete_snapshot(self):
        self.assert_batch_rejected((CONTENT, APPROVAL), "verifier_unavailable", available=False)

    def test_mixed_task_or_rule_invalidates_whole_snapshot(self):
        for wrong in (replace(APPROVAL, task_id="different"), replace(APPROVAL, rule_version="old")):
            self.assert_batch_rejected((CONTENT, APPROVAL, wrong), "binding_mismatch")

    def test_malformed_reference_blocks_and_does_not_escape(self):
        for reference in ("", " ev_" + "0" * 32, "ev_" + "A" * 32, "ev_1",
                          CONTENT.reference + "\n", "https://private.example", "/private/file", "原文"):
            with self.subTest(reference=reference):
                result = self.assert_batch_rejected(
                    (CONTENT, APPROVAL, replace(CONTENT, reference=reference)), "invalid_reference")
                if reference:
                    self.assertNotIn(reference, repr(result))

    def test_one_reference_cannot_prove_two_items(self):
        self.assert_batch_rejected((CONTENT, replace(APPROVAL, reference=CONTENT.reference)), "cross_item_replay")

    def test_undeclared_item_invalidates_batch_even_when_every_required_item_matches(self):
        extra = replace(CONTENT, item="extra", reference="ev_" + "c" * 32)
        self.assert_batch_rejected((CONTENT, APPROVAL, extra), "undeclared_item")

    def test_batch_reason_priority_is_stable(self):
        extra = replace(APPROVAL, item="extra", reference=CONTENT.reference)
        invalid = replace(APPROVAL, reference="private evidence")
        wrong = replace(APPROVAL, task_id="wrong")
        records = (CONTENT, extra, invalid, wrong)
        self.assert_batch_rejected(records, "verifier_unavailable", available=False)
        self.assert_batch_rejected(records, "binding_mismatch")
        self.assert_batch_rejected(records[:-1], "invalid_reference")
        self.assert_batch_rejected(records[:2], "cross_item_replay")

    def test_invalid_contract_cannot_make_an_empty_or_ambiguous_task_ready(self):
        for contract in (replace(CONTRACT, required_items=()), replace(CONTRACT, task_id=" "),
                         replace(CONTRACT, rule_version="v\n2"), replace(CONTRACT, required_items=("a", "a")),
                         replace(CONTRACT, required_items=("item ",))):
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                self.evaluate(contract=contract)

    def test_wrong_boundary_types_raise_even_when_verification_is_unavailable(self):
        for contract, evidence, available in [
            ({}, (), True), (replace(CONTRACT, rule_version=1), (), True),
            (replace(CONTRACT, required_items=["a"]), (), True),
            (replace(CONTRACT, required_items=(None,)), (), True),
            (CONTRACT, [CONTENT], True), (CONTRACT, (), 1), (CONTRACT, ({},), False),
            (CONTRACT, (replace(CONTENT, reference=None),), False),
        ]:
            with self.subTest(contract=contract, evidence=evidence, available=available), self.assertRaises(TypeError):
                evaluate_quality(contract, evidence, verifier_available=available)

    def test_evaluation_has_no_file_network_or_process_io(self):
        # Isolate the audit hook in a stdlib-only interpreter. Both delivery paths run under it.
        script = """
import sys
from mingjing_agent.quality import Evidence, TaskContract, evaluate_quality

def reject_io(event, args):
    if event == 'open' or event.startswith(('os.', 'socket.', 'subprocess.', 'sqlite3.')):
        raise AssertionError(event)

contract = TaskContract('t', 'v', ('x',))
record = Evidence('t', 'v', 'x', 'ev_' + '1' * 32, 'confirmed')
sys.addaudithook(reject_io)
assert evaluate_quality(contract, (record,), verifier_available=True).ready
assert not evaluate_quality(contract, (), verifier_available=True).ready
"""
        subprocess.run([sys.executable, "-S", "-c", script], check=True)
