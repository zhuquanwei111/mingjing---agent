import tempfile
from pathlib import Path
import unittest

from scripts.check_development_docs import (
    PROJECT_SKILL,
    STANDARD_SKILL,
    check_package,
    check_skill_entry,
)


class DevelopmentDocsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.package = self.root / "engineering-standard"
        self.package.mkdir()

    def test_package_can_be_checked_without_project_docs(self):
        (self.package / "README.md").write_text(
            "[template](task.md)\n[upstream](https://example.com/source)\n",
            encoding="utf-8",
        )
        (self.package / "task.md").write_text("# Task\n", encoding="utf-8")
        self.assertEqual(check_package(self.package), (2, []))

    def test_package_detects_missing_and_outside_links(self):
        (self.root / "project.md").write_text("# Project\n", encoding="utf-8")
        (self.package / "README.md").write_text(
            "[missing](missing.md)\n[project](../project.md)\n",
            encoding="utf-8",
        )
        count, errors = check_package(self.package)
        self.assertEqual(count, 1)
        self.assertEqual(len(errors), 2)
        self.assertIn("missing local target: missing.md", errors[0])
        self.assertIn("link leaves checked directory: ../project.md", errors[1])

    def test_package_detects_a_link_through_a_symlink_to_project_data(self):
        (self.root / "project.txt").write_text("Project\n", encoding="utf-8")
        (self.package / "linked.txt").symlink_to("../project.txt")
        (self.package / "README.md").write_text(
            "[project](linked.txt)\n", encoding="utf-8",
        )
        _, errors = check_package(self.package)
        self.assertEqual(len(errors), 1)
        self.assertIn("link leaves checked directory: linked.txt", errors[0])

    def test_skill_entry_must_resolve_to_the_canonical_skill(self):
        canonical = self.package / STANDARD_SKILL
        canonical.parent.mkdir(parents=True)
        canonical.touch()
        entry = self.root / PROJECT_SKILL
        entry.parent.parent.mkdir(parents=True)
        self.assertTrue(check_skill_entry(self.root, self.package))
        entry.parent.symlink_to(canonical.parent, target_is_directory=True)
        self.assertEqual(check_skill_entry(self.root, self.package), [])

        entry.parent.unlink()
        entry.parent.mkdir()
        entry.touch()
        self.assertTrue(check_skill_entry(self.root, self.package))
