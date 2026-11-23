import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "engineering-standard/adapters/codex-cli/start_implementation.py"
)
SPEC = importlib.util.spec_from_file_location("start_implementation", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

INPUTS = {"requirements_sha256": "requirements", "plan_sha256": "plan", "implementation_sha256": "argv"}
PASS = {
    "role": "solution-reviewer", "decision": "pass", "scope": "Development entry",
    "summary": "Feasible", "inputs": INPUTS, "evidence": ["AGENTS.md"], "findings": [],
}
FINDING = {
    "category": "required", "issue": "Specify the rollback", "evidence": "plan.md:4",
    "action": "Record the rollback command",
}
REVISE = dict(PASS, decision="revise", findings=[FINDING])
EVENTS = [
    {"type": "thread.started", "thread_id": "new-session"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(PASS)}},
    {"type": "turn.completed"},
]


def jsonl(events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


class PlanGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan = self.root / "docs/tasks/plan.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text("# Plan\n", encoding="utf-8")
        self.requirements = self.root / "docs/requirements/original.md"
        self.requirements.parent.mkdir(parents=True)
        self.requirements.write_text("# Requirements\n", encoding="utf-8")
        self.result = self.root / "verdict.json"
        self.state = ("refs/heads/task", "abc", self.plan.read_bytes())

    def test_valid_verdict_needs_one_completed_independent_turn(self):
        self.result.write_text(json.dumps(PASS), encoding="utf-8")
        self.assertEqual(gate.read_verdict(self.result, jsonl(EVENTS), INPUTS), ("new-session", PASS))
        bad_streams = [
            "", "[]", jsonl(EVENTS + [{"type": "turn.failed"}]),
            jsonl(EVENTS + EVENTS), jsonl(EVENTS[::-1]), jsonl(EVENTS[:-1]),
            jsonl(EVENTS + [{"type": "turn.started"}]),
        ]
        for events in bad_streams:
            with self.subTest(events=events), self.assertRaises(ValueError):
                gate.read_verdict(self.result, events, INPUTS)

    def test_partial_or_conflicting_verdict_is_invalid(self):
        cases = [
            "{broken",
            '{"decision":"pass","decision":"revise"}',
            json.dumps(dict(PASS, decision="approved")),
            json.dumps(dict(PASS, evidence=[])),
            json.dumps(dict(PASS, findings=[FINDING])),
            json.dumps(dict(PASS, decision="blocked")),
            json.dumps(dict(PASS, role="default")),
            json.dumps(dict(PASS, inputs=dict(INPUTS, plan_sha256="stale"))),
        ]
        for text in cases:
            self.result.write_text(text, encoding="utf-8")
            matching_event = {"type": "item.completed", "item": {"type": "agent_message", "text": text}}
            with self.subTest(text=text), self.assertRaises(ValueError):
                gate.read_verdict(self.result, jsonl([*EVENTS[:2], matching_event, EVENTS[-1]]), INPUTS)

    def test_file_must_match_this_turns_final_message(self):
        self.result.write_text(json.dumps(REVISE), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from the final message"):
            gate.read_verdict(self.result, jsonl(EVENTS), INPUTS)

    def test_duplicate_event_fields_cannot_hide_a_failure(self):
        self.result.write_text(json.dumps(PASS), encoding="utf-8")
        events = jsonl(EVENTS[:2]) + '{"type":"error","type":"item.updated"}\n' + jsonl(EVENTS[2:])
        with self.assertRaisesRegex(ValueError, "duplicate fields"):
            gate.read_verdict(self.result, events, INPUTS)

    def test_thread_created_without_a_delivered_task_is_not_a_review(self):
        receipt_only = {"type": "item.completed", "item": {
            "type": "agent_message", "text": "No task has come through yet",
        }}
        self.result.write_text(receipt_only["item"]["text"], encoding="utf-8")
        with self.assertRaises(ValueError):
            gate.read_verdict(self.result, jsonl([*EVENTS[:2], receipt_only, EVENTS[-1]]), INPUTS)

    def test_only_optional_findings_are_consistent_with_pass(self):
        optional = dict(PASS, findings=[dict(FINDING, category="optional")])
        result = json.dumps(optional)
        self.result.write_text(result, encoding="utf-8")
        event = {"type": "item.completed", "item": {"type": "agent_message", "text": result}}
        self.assertEqual(
            gate.read_verdict(self.result, jsonl([*EVENTS[:2], event, EVENTS[-1]]), INPUTS),
            ("new-session", optional),
        )

    def run_entry(self, verdict, states, code=17, plan="docs/tasks/plan.md"):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(gate, "git", return_value=str(self.root)), \
                patch.object(gate, "committed_digest", return_value=INPUTS["requirements_sha256"]), \
                patch.object(gate, "candidate", side_effect=states), \
                patch.object(gate, "review", side_effect=[verdict]), \
                patch.object(gate.subprocess, "run") as implementation, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            implementation.return_value.returncode = code
            status = gate.main([
                "docs/requirements/original.md", plan, "--", "implementation", "literal argument",
            ])
        return status, implementation, stdout.getvalue() + stderr.getvalue()

    def test_review_feedback_reaches_designer_without_starting_command(self):
        status, implementation, output = self.run_entry(("session", REVISE), [self.state])
        self.assertEqual(status, 2)
        self.assertIn("Specify the rollback", output)
        implementation.assert_not_called()

    def test_review_failure_aborts_before_starting_command(self):
        for failure in (
            FileNotFoundError("Missing reviewer or verdict"),
            ValueError("Reviewer exited nonzero"),
            subprocess.TimeoutExpired("codex", 1),
            KeyboardInterrupt(),
        ):
            with self.subTest(failure=failure):
                status, implementation, _ = self.run_entry(failure, [self.state])
                self.assertIn(status, (2, 130))
                implementation.assert_not_called()

    def test_changed_state_after_pass_blocks_implementation(self):
        for final_state in (
            ("refs/heads/other", "abc", self.state[2]),
            ("refs/heads/task", "def", self.state[2]),
            ("refs/heads/task", "abc", b"Revised during the review"),
            ValueError("Other worktree changes appeared"),
        ):
            with self.subTest(state=final_state):
                status, implementation, _ = self.run_entry(
                    ("session", PASS), [self.state, final_state],
                )
                self.assertEqual(status, 2)
                implementation.assert_not_called()

    def test_pass_starts_exact_arguments_and_propagates_exit_status(self):
        status, implementation, _ = self.run_entry(("session", PASS), [self.state, self.state])
        self.assertEqual(status, 17)
        implementation.assert_called_once_with(
            ["implementation", "literal argument"], cwd=self.root, check=False,
        )

    def test_plan_may_not_overlay_authoritative_root_rules(self):
        (self.root / "AGENTS.md").touch()
        status, implementation, _ = self.run_entry(("session", PASS), [], plan="AGENTS.md")
        self.assertEqual(status, 2)
        implementation.assert_not_called()

    def test_signalled_implementation_uses_shell_exit_status(self):
        status, _, _ = self.run_entry(("session", PASS), [self.state, self.state], code=-signal.SIGTERM)
        self.assertEqual(status, 143)

    def test_fixed_git_snapshot_ignores_export_attributes_and_worktree_bytes(self):
        repo = self.root / "committed"
        repo.mkdir()
        command = ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo)]
        subprocess.run([*command, "init", "-q"], check=True)
        (repo / ".gitattributes").write_text("AGENTS.md export-ignore\ndata.md export-subst\n")
        (repo / "AGENTS.md").write_bytes(b"Committed authority\n")
        (repo / "data.md").write_bytes(b"$Format:%H$\n")
        subprocess.run([*command, "add", ".gitattributes", "AGENTS.md", "data.md"], check=True)
        subprocess.run([
            *command, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
            "-c", "commit.gpgsign=false", "commit", "-qm", "Test committed inputs",
        ], check=True)
        (repo / "AGENTS.md").write_bytes(b"Changed authority\n")
        snapshot = self.root / "snapshot"
        snapshot.mkdir()
        gate.export_base(repo, gate.git(repo, "rev-parse", "HEAD"), snapshot)
        self.assertEqual((snapshot / "AGENTS.md").read_bytes(), b"Committed authority\n")
        self.assertEqual((snapshot / "data.md").read_bytes(), b"$Format:%H$\n")

    def test_timeout_kills_and_waits_for_reviewer_process_group(self):
        worker, pids = self.review_worker()
        with self.assertRaises(subprocess.TimeoutExpired):
            gate.run_process(worker, self.root, os.environ.copy(), "", 1)
        self.assert_processes_stopped(pids)

    def test_signals_reclaim_reviewer_group_without_running_next_step(self):
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signum=signum):
                worker, pids = self.review_worker()
                parent = [
                    sys.executable, "-B", "-c",
                    "import os, signal, sys; from pathlib import Path; "
                    "sys.path.insert(0, sys.argv[1]); import start_implementation as gate; "
                    "signal.signal(signal.SIGTERM, gate.cancel_review); "
                    "gate.run_process(sys.argv[2:], Path.cwd(), os.environ.copy(), '', 30); "
                    "Path('next-step').touch()",
                    str(SCRIPT.parent), *worker,
                ]
                process = subprocess.Popen(parent, cwd=self.root, stderr=subprocess.DEVNULL)
                try:
                    deadline = time.monotonic() + 5
                    while not pids.exists() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(pids.exists(), "Reviewer child did not start")
                    process.send_signal(signum)
                    self.assertNotEqual(process.wait(timeout=5), 0)
                    self.assertFalse((self.root / "next-step").exists())
                    self.assert_processes_stopped(pids)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)

    def test_cancellation_after_spawn_before_process_handle_returns(self):
        worker, pids = self.review_worker()
        start = subprocess.Popen

        def cancelled_launch(*args, **kwargs):
            proc = start(*args, **kwargs)
            deadline = time.monotonic() + 5
            while not pids.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            if not pids.exists():
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
                self.fail("Reviewer child did not start")
            os.kill(os.getpid(), signal.SIGTERM)
            return proc

        with patch.object(gate.subprocess, "Popen", side_effect=cancelled_launch):
            with self.assertRaises(gate.ReviewCancelled):
                gate.run_process(worker, self.root, os.environ.copy(), "", 30)
        self.assert_processes_stopped(pids)

    def review_worker(self):
        pids = self.root / "reviewer-pids"
        pids.unlink(missing_ok=True)
        program = (
            "import os, subprocess, sys, time; from pathlib import Path; "
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            "pids = Path(sys.argv[1]); temp = pids.with_suffix('.tmp'); "
            "temp.write_text(f'{os.getpid()} {child.pid}'); temp.replace(pids); time.sleep(30)"
        )
        return [sys.executable, "-c", program, str(pids)], pids

    def assert_processes_stopped(self, pids):
        for pid in pids.read_text().split():
            # An orphan may briefly remain as a zombie until the OS reaps it.
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                state = subprocess.run(["ps", "-p", pid, "-o", "stat="], capture_output=True, text=True)
                if state.returncode != 0 or state.stdout.strip().startswith("Z"):
                    break
                time.sleep(0.02)
            else:
                self.fail(f"Reviewer process {pid} is still active")
