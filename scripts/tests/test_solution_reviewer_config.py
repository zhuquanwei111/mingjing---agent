"""Validate portable and project-native Codex reviewer role definitions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SolutionReviewerRoleTest(unittest.TestCase):
    def test_role_files_match_and_required_fields_exist(self):
        generic = ROOT / "engineering-standard/agents/solution-reviewer.toml"
        project = ROOT / ".codex/agents/solution-reviewer.toml"
        self.assertEqual(generic.read_bytes(), project.read_bytes())
        body = generic.read_text(encoding="utf-8")
        self.assertIn('name = "solution_reviewer"', body)
        self.assertIn('description = "', body)
        self.assertIn('developer_instructions = """', body)
        self.assertIn("Do not edit files", body)
        self.assertNotIn("sandbox_mode =", body)
        try:
            import tomllib
        except ModuleNotFoundError:
            return  # Python 3.10 retains the text checks; CI Python 3.12 parses.
        parsed = tomllib.loads(body)
        self.assertEqual(parsed["name"], "solution_reviewer")
        self.assertTrue(parsed["developer_instructions"])


if __name__ == "__main__":
    unittest.main()
