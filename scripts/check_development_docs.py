#!/usr/bin/env python3
"""Check local links and the engineering standard entry; optionally show Git state.

This is a read-only navigation check, not a Markdown renderer or semantic review.
It does not validate remote URLs, anchors, reference-style links, task completion,
authority, or the accuracy of recorded evidence.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
STANDARD_PACKAGE = "engineering-standard"
STANDARD_SKILL = Path("skills/engineering-handoff/SKILL.md")
PROJECT_SKILL = Path(".agents/skills/engineering-handoff/SKILL.md")
ENTRY_POINTS = (
    "AGENTS.md",
    "README.md",
    "docs/index.md",
    "docs/repository-layout.md",
    "docs/designs/current-architecture-baseline.md",
    "docs/archive/route-b/designs/whole-product-decision.md",
    "docs/development.md",
    "docs/PLANS.md",
    "docs/configuration.md",
    "docs/engineering-standard.md",
    "docs/engineering-standard-execution.md",
    "docs/requirements/engineering-standard.md",
    "docs/adr/0001-versioned-engineering-standard.md",
    "docs/archive/legacy-runtime/README.md",
    "docs/archive/legacy-runtime/core/README.md",
    "docs/archive/legacy-runtime/p1-walking-skeleton/README.md",
)
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def local_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path must stay inside the repository: {value}")
    return path


def check_file(root: Path, source: Path) -> list[str]:
    label = source.relative_to(root).as_posix()
    try:
        if not source.resolve().is_relative_to(root):
            return [f"{label}: document leaves checked directory"]
        if not source.is_file():
            return [f"{label}: missing development document"]
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, RuntimeError, UnicodeError) as error:
        return [f"{label}: cannot read document: {error}"]
    errors = []
    active_fence = ""
    for number, line in enumerate(lines, 1):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not active_fence:
                active_fence = marker
            elif marker[0] == active_fence[0] and len(marker) >= len(active_fence):
                active_fence = ""
            continue
        if active_fence:
            continue
        for match in LINK.finditer(line):
            target = match.group(1) or match.group(2)
            try:
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                path = (source.parent / unquote(parsed.path)).resolve()
                if not path.is_relative_to(root):
                    errors.append(f"{label}:{number}: link leaves checked directory: {target}")
                elif not path.exists():
                    errors.append(f"{label}:{number}: missing local target: {target}")
            except (OSError, RuntimeError, ValueError) as error:
                errors.append(f"{label}:{number}: invalid link {target}: {error}")
    return errors


def check_package(package: Path) -> tuple[int, list[str]]:
    sources = sorted(set(package.rglob("*.md")) | {package / "README.md"})
    errors = [error for source in sources for error in check_file(package, source)]
    return len(sources), errors


def check_skill_entry(root: Path, package: Path) -> list[str]:
    entry = root / PROJECT_SKILL
    canonical = package / STANDARD_SKILL
    if not entry.is_file() or entry.resolve() != canonical:
        return [f"{PROJECT_SKILL}: expected the canonical skill at {canonical.relative_to(root)}"]
    return []


def show_status(root: Path, task: Path | None) -> bool:
    print(f"Repository: {root}")
    for label, args in (
        ("Branch", ["branch", "--show-current"]),
        ("HEAD", ["rev-parse", "HEAD"]),
        ("Worktree", ["status", "--short", "--branch"]),
    ):
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=False,
        )
        if result.returncode:
            print(f"Cannot read Git {label}: {result.stderr.strip()}", file=sys.stderr)
            return False
        value = result.stdout.strip() or ("detached HEAD" if label == "Branch" else "empty")
        print(f"{label}: {value}")
    if task is not None:
        print(f"Task record: {task.relative_to(root).as_posix()}")
        print("Read that record and verify its baseline against this Git state before continuing.")
    print("This command does not fetch remotes, inspect credentials, start services, or mark work complete.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="also print current read-only Git state")
    parser.add_argument("--task", help="repository-relative Markdown task record to locate and check")
    parser.add_argument("--package", type=Path, help="check only a standalone engineering standard directory")
    args = parser.parse_args()
    if args.package is not None:
        if args.status or args.task:
            parser.error("--package cannot be combined with --status or --task")
        count, errors = check_package(args.package.resolve())
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Standard package local links passed: {count} documents.")
        return 0

    try:
        package = local_path(ROOT, STANDARD_PACKAGE)
        task = local_path(ROOT, args.task) if args.task else None
        if task is not None and task.suffix.lower() != ".md":
            raise ValueError("--task must name a Markdown record")
        sources = {local_path(ROOT, path) for path in ENTRY_POINTS}
        for folder in ("docs/tasks", "docs/archive/route-b"):
            sources.update(path.resolve() for path in (ROOT / folder).rglob("*.md"))
        if task is not None:
            sources.add(task)
        for source in sources:
            if not source.is_relative_to(ROOT):
                raise ValueError("Task record resolves outside the repository")
    except ValueError as error:
        parser.error(str(error))
    errors = [error for source in sorted(sources) for error in check_file(ROOT, source)]
    package_count, package_errors = check_package(package)
    errors.extend(f"{STANDARD_PACKAGE}/{error}" for error in package_errors)
    errors.extend(check_skill_entry(ROOT, package))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Development local links passed: {len(sources)} documents. Anchors, remote links and content are not verified.")
    print(f"Standard package local links and skill entry passed: {package_count} documents.")
    if args.status and not show_status(ROOT, task):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
