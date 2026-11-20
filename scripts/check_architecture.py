#!/usr/bin/env python3
"""Check two existing import boundaries without importing application code.

The shared capability contract may depend on stdlib and Pydantic only, including
local package initialization and its transitive static dependencies. Product
state, persistence, and ordinary capability examples must not depend on a
Temporal/LangGraph engine, including through another local module. Wiring in
http_api, temporal_adapter, workflows, and __main__ is deliberately allowed.

This checks Python import statements, not runtime-generated imports or whether
authorization, transactions, and idempotency are correct; those need the P2
behavior tests and review. No database, credentials, or services are accessed.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys


ENGINE_MODULES = {"temporalio", "langgraph"}
ENGINE_INDEPENDENT = {"contracts", "service", "catalog", "db", "artifacts", "examples"}


def imports(tree: ast.AST, module: str, is_package: bool) -> set[str]:
    """Return absolute dependency names for all static imports, including nested ones."""
    dependencies = set()
    package = module if is_package else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - node.level + 1])
                base = ".".join(part for part in (base, node.module) if part)
            else:
                base = node.module or ""
            dependencies.add(base)
            # `from mingjing import helper` may load a submodule. Names that are
            # merely imported objects will not match a module in the graph.
            dependencies.update(f"{base}.{alias.name}" for alias in node.names)
    return dependencies


def violations(source: Path) -> list[str]:
    graph: dict[str, set[str]] = {}
    for path in sorted(source.rglob("*.py")):
        parts = path.relative_to(source).with_suffix("").parts
        is_package = parts[-1] == "__init__"
        suffix = parts[:-1] if is_package else parts
        module = ".".join(("mingjing", *suffix))
        graph[module] = imports(ast.parse(path.read_bytes(), filename=str(path)), module, is_package)

    errors = []
    required = {f"mingjing.{name}" for name in ENGINE_INDEPENDENT}
    for missing in sorted(required - graph.keys()):
        errors.append(f"Missing protected module {missing}; review the boundary if it was moved.")

    # Importing a local module also executes its parent packages' __init__.py.
    # Include those edges before checking either boundary, so moving a storage
    # or engine import there cannot hide a contract's actual dependencies.
    for module, dependencies in graph.items():
        parents = set()
        for name in (*dependencies, module):
            parts = name.split(".")
            parents.update(".".join(parts[:end]) for end in range(1, len(parts)))
        dependencies.update((parents & graph.keys()) - {module})

    for start in sorted(required & graph.keys()):
        pending = [(start, [start])]
        visited = set()
        while pending:
            module, chain = pending.pop(0)
            if module in visited:
                continue
            visited.add(module)
            for dependency in sorted(graph[module]):
                root = dependency.partition(".")[0]
                if start == "mingjing.contracts":
                    # Importing the parent package and reexporting contract
                    # objects are valid; all other local runtime modules and
                    # non-whitelisted external dependencies violate the boundary.
                    contract_package = dependency in {"mingjing", "mingjing.contracts"} or dependency.startswith("mingjing.contracts.")
                    if root not in sys.stdlib_module_names and root != "pydantic" and not contract_package:
                        errors.append(f"{' -> '.join((*chain, dependency))}: contracts must stay independent of runtime/storage implementations.")
                if root in ENGINE_MODULES:
                    errors.append(f"Engine dependency: {' -> '.join((*chain, dependency))}")
                if dependency in graph and dependency not in visited:
                    pending.append((dependency, [*chain, dependency]))
    return sorted(set(errors))


def main() -> int:
    source = Path(__file__).resolve().parents[1] / "core" / "src" / "mingjing"
    errors = violations(source)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Architecture imports passed: shared contracts and engine-independent product modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
