import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
P1_INFRA = REPOSITORY_ROOT / "p1-walking-skeleton" / "infra"


class RebuildCleanupTests(unittest.TestCase):
    """Run the actual shell driver, with Docker replaced by a resource ledger."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mingjing-rebuild-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "p1"
        self.source.mkdir()
        for name in ("infra", "requirements", "src", "tests", ".p1"):
            (self.source / name).mkdir()
        (self.source / ".dockerignore").write_text("")
        for name in ("verify-rebuild.sh", "compose.sh", "new-run.sh"):
            shutil.copyfile(P1_INFRA / name, self.source / "infra" / name)
        self.original_env = self.source / ".p1" / "runtime.env"
        self.original_contents = "MINGJING_RUN_ID=local-deadbeef\n"
        self.original_env.write_text(self.original_contents)
        self.initial_resources = {
            "mingjing-p1-local-deadbeef": True,
            "mingjing-p1-local-bbbbbbbb": True,
            "mingjing-p2-aaaaaaaaaa": True,
        }
        self.state_path = self.root / "resources.json"
        self.state_path.write_text(json.dumps(self.initial_resources))
        self.calls_path = self.root / "docker-calls.jsonl"
        self.created_path = self.root / "created-directory.txt"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._stub("mktemp", """
import os
from pathlib import Path
import sys
import tempfile

assert sys.argv[1:] == ['-d', '/tmp/mingjing-p1-rebuild.XXXXXX']
directory = tempfile.mkdtemp(prefix='mingjing-p1-rebuild.', dir=os.environ['REBUILD_TEST_ROOT'])
Path(os.environ['REBUILD_TEST_CREATED']).write_text(directory)
print(directory)
""")
        self._stub("cp", """
import os
from pathlib import Path
import sys

if os.environ.get('REBUILD_FAIL_COPY'):
    (Path(sys.argv[-1]) / 'partial-copy').write_text('partial')
    sys.exit(19)
os.execv('/bin/cp', ['/bin/cp', *sys.argv[1:]])
""")
        self._stub("sh", """
import os
from pathlib import Path
import sys

if os.environ.get('REBUILD_FAIL_INIT') and sys.argv[1:] == ['infra/new-run.sh']:
    Path('.p1').mkdir(exist_ok=True)
    Path('.p1/runtime.env').write_text('MINGJING_RUN_ID=local-abcdabcd\\nP1_DB_PASSWORD=synthetic\\n')
    sys.exit(31)
os.execv('/bin/sh', ['/bin/sh', *sys.argv[1:]])
""")
        self._stub("sudo", """
import os
import sys

os.execvp(sys.argv[1], sys.argv[1:])
""")
        self._stub("docker", """
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
assert args[0] == 'compose', args
project = args[args.index('-p') + 1]
action = args[args.index('-f') + 2]
with Path(os.environ['REBUILD_TEST_CALLS']).open('a') as stream:
    stream.write(json.dumps({'project': project, 'action': action, 'args': args}) + '\\n')
state_path = Path(os.environ['REBUILD_TEST_STATE'])
state = json.loads(state_path.read_text())
if action == 'up':
    state[project] = True
    state_path.write_text(json.dumps(state))
elif action == 'down':
    if os.environ.get('REBUILD_FAIL_DOWN'):
        sys.exit(42)
    state.pop(project, None)
    state_path.write_text(json.dumps(state))
elif action == 'exec':
    print('0')
elif action == 'run' and 'pytest' in args:
    if os.environ.get('REBUILD_REPLACE_ID'):
        env_path = Path(args[args.index('--env-file') + 1])
        lines = env_path.read_text().splitlines()
        lines = ['MINGJING_RUN_ID=local-bbbbbbbb' if line.startswith('MINGJING_RUN_ID=') else line for line in lines]
        env_path.write_text('\\n'.join(lines) + '\\n')
    if os.environ.get('REBUILD_FAIL_TEST'):
        sys.exit(23)
""")

    def _stub(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + body)
        path.chmod(0o755)

    def _run(self, **flags):
        env = {
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "REBUILD_TEST_ROOT": str(self.root),
            "REBUILD_TEST_CREATED": str(self.created_path),
            "REBUILD_TEST_STATE": str(self.state_path),
            "REBUILD_TEST_CALLS": str(self.calls_path),
            **{name: "1" for name in flags},
        }
        result = subprocess.run(
            ["/bin/sh", str(self.source / "infra" / "verify-rebuild.sh")],
            cwd=self.source,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(self.original_env.read_text(), self.original_contents)
        self.created = Path(self.created_path.read_text())
        self.calls = [json.loads(line) for line in self.calls_path.read_text().splitlines()] if self.calls_path.exists() else []
        self.resources = json.loads(self.state_path.read_text())
        for project, state in self.initial_resources.items():
            self.assertEqual(self.resources.get(project), state)
        self.assertFalse({call["project"] for call in self.calls} & self.initial_resources.keys())
        return result

    def test_success_removes_only_owned_resources_and_directory(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.created.exists())
        self.assertEqual(self.resources, self.initial_resources)
        self.assertEqual(sum(call["action"] == "down" for call in self.calls), 1)

    def test_failed_tests_preserve_status_and_still_clean(self):
        result = self._run(REBUILD_FAIL_TEST=True)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertFalse(self.created.exists())
        self.assertEqual(self.resources, self.initial_resources)

    def test_cleanup_failure_retains_credentials_and_reports_recovery(self):
        result = self._run(REBUILD_FAIL_DOWN=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue((self.created / ".p1" / "runtime.env").is_file())
        self.assertIn(str(self.created), result.stderr)
        self.assertIn("Retry cleanup with:", result.stderr)
        self.assertEqual(len(self.resources), len(self.initial_resources) + 1)

    def test_cleanup_failure_does_not_replace_original_test_failure(self):
        result = self._run(REBUILD_FAIL_TEST=True, REBUILD_FAIL_DOWN=True)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertTrue((self.created / ".p1" / "runtime.env").is_file())

    def test_copy_failure_removes_partial_owned_directory(self):
        result = self._run(REBUILD_FAIL_COPY=True)
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertFalse(self.created.exists())
        self.assertEqual(self.calls, [])

    def test_init_failure_removes_partial_credentials(self):
        result = self._run(REBUILD_FAIL_INIT=True)
        self.assertEqual(result.returncode, 31, result.stderr)
        self.assertFalse(self.created.exists())
        self.assertEqual(self.calls, [])

    def test_changed_identity_does_not_clean_another_project(self):
        result = self._run(REBUILD_REPLACE_ID=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue((self.created / ".p1" / "runtime.env").is_file())
        self.assertIn("identity changed; refusing cleanup", result.stderr)
        self.assertFalse(any(call["action"] == "down" for call in self.calls))


if __name__ == "__main__":
    unittest.main()
