"""Exercise architecture guard failure paths with isolated source trees."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_architecture import ENGINE_INDEPENDENT, violations


class ArchitectureGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name)
        for module in ENGINE_INDEPENDENT:
            self.write(module, "")

    def write(self, module: str, code: str):
        path = self.source / f"{module.replace('.', '/')}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)

    def test_engine_wiring_and_contract_types_are_allowed(self):
        self.write("contracts", "from pydantic import BaseModel\nfrom uuid import UUID\n")
        self.write("service", "from .contracts import Identity\nfrom .db import Database\n")
        self.write("db", "import psycopg\n")
        self.write("temporal_adapter", "from temporalio import activity\nfrom .service import Service\n")
        self.assertEqual(violations(self.source), [])

    def test_public_contract_cannot_import_storage_implementation(self):
        self.write("contracts", "from .db import Database\n")
        self.assertTrue(any("contracts must stay independent" in error for error in violations(self.source)))

    def test_contract_rejects_storage_loaded_by_package_initializer(self):
        self.write("__init__", "import psycopg\n")
        self.assertTrue(any("mingjing.contracts -> mingjing -> psycopg" in error for error in violations(self.source)))

    def test_contract_rejects_transitive_storage_loaded_by_package_initializer(self):
        self.write("__init__", "from .service import Service\n")
        self.write("service", "import psycopg\n")
        self.assertTrue(any("mingjing.contracts -> mingjing -> mingjing.service -> psycopg" in error for error in violations(self.source)))

    def test_contract_allows_empty_or_standard_library_package_initializer(self):
        for initializer in ("", "from uuid import UUID\n"):
            with self.subTest(initializer=initializer):
                self.write("__init__", initializer)
                self.assertEqual(violations(self.source), [])

    def test_package_initializer_can_reexport_contract_types(self):
        self.write("__init__", "from .contracts import Model\n")
        self.write("contracts", "from pydantic import BaseModel\n")
        self.assertEqual(violations(self.source), [])

    def test_nested_engine_import_is_rejected(self):
        self.write("service", "def run():\n    import temporalio.client as engine\n")
        self.assertTrue(any("Engine dependency" in error for error in violations(self.source)))

    def test_transitive_relative_engine_import_is_rejected(self):
        self.write("service", "from . import helper\n")
        self.write("helper", "from langgraph.graph import StateGraph\n")
        self.assertTrue(any("mingjing.service -> mingjing.helper -> langgraph" in error for error in violations(self.source)))

    def test_transitive_absolute_engine_import_is_rejected(self):
        self.write("catalog", "from mingjing import helper\n")
        self.write("helper", "import temporalio\n")
        self.assertTrue(any("mingjing.catalog -> mingjing.helper -> temporalio" in error for error in violations(self.source)))

    def test_import_cycle_does_not_hide_engine_dependency(self):
        self.write("service", "from . import helper\n")
        self.write("helper", "from . import service\nimport langgraph\n")
        self.assertTrue(any("Engine dependency" in error for error in violations(self.source)))

    def test_removing_protected_module_requires_explicit_boundary_review(self):
        (self.source / "contracts.py").unlink()
        self.assertTrue(any("Missing protected module mingjing.contracts" in error for error in violations(self.source)))

    def test_package_initializer_does_not_hide_engine_dependency(self):
        self.write("service", "import mingjing.helpers.safe\n")
        self.write("helpers.__init__", "import temporalio\n")
        self.write("helpers.safe", "")
        self.assertTrue(any("mingjing.service -> mingjing.helpers -> temporalio" in error for error in violations(self.source)))


if __name__ == "__main__":
    unittest.main()
