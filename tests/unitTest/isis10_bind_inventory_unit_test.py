"""Unit tests for the ISIS 10-only binding candidate inventory.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun added source-diff and generated-inventory coverage.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "dev" / "generate_isis10_bind_inventory.py"
SPEC = importlib.util.spec_from_file_location("generate_isis10_bind_inventory", TOOL_PATH)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


class Isis10BindInventoryUnitTest(unittest.TestCase):
    """Validate the curated ISIS 10-only candidate catalog."""

    def setUp(self) -> None:
        self.isis9_root = PROJECT_ROOT / "reference" / "upstream_isis" / "9.0.0"
        self.isis10_root = PROJECT_ROOT / "reference" / "upstream_isis" / "10.0.0"
        if not self.isis9_root.is_dir() or not self.isis10_root.is_dir():
            self.skipTest("versioned upstream ISIS source trees are not restored")

    def test_candidates_exist_only_at_the_isis10_source_path(self) -> None:
        inventory._validate_candidates(self.isis9_root, self.isis10_root)

    def test_inventory_covers_high_value_new_isis10_apis(self) -> None:
        classes = {candidate.class_name for candidate in inventory.CLASS_CANDIDATES}
        functions = {
            candidate.function_name for candidate in inventory.FUNCTION_CANDIDATES
        }
        self.assertTrue(
            {
                "IProj",
                "Chandrayaan2OhrcCamera",
                "Chandrayaan2TmcCamera",
                "OsirisRexOcamsOpenCVDistortionMap",
                "GdalIoHandler",
                "ImageIoHandler",
            }.issubset(classes)
        )
        self.assertEqual({"csv2table", "ocams2isis", "eisstitch"}, functions)

    def test_generated_inventory_matches_isis9_ledger_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            details = {
                candidate.class_name: inventory._write_class_detail(
                    output_dir, candidate
                )
                for candidate in inventory.CLASS_CANDIDATES
            }
            inventory._write_summary(output_dir, None, details)
            inventory._write_functions(output_dir, None)
            inventory._write_exclusions(output_dir)

            detail_path = (
                output_dir
                / "class_details"
                / details["IProj"]
            )
            with detail_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(
                [
                    "Class",
                    "Module Category",
                    "Source",
                    "Binding",
                    "Status Legend",
                    "Python Naming Note",
                    "Class Note",
                ],
                rows[0],
            )
            self.assertIn(
                ["Class Symbol", "IProj", "isis_pybind.IProj", "N", inventory.CLASS_CANDIDATES[0].reason],
                rows,
            )


if __name__ == "__main__":
    unittest.main()
