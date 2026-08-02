"""Unit tests for the ISIS 10-only binding candidate inventory.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-24
Updated: 2026-07-23  Geng Xun added source-diff and generated-inventory coverage.
Updated: 2026-07-24  Geng Xun added installed-header discovery and classification-gate coverage.
Updated: 2026-07-24  Geng Xun covered C++ .hpp discovery for the official ISIS 10 prefix.
Updated: 2026-08-02  Geng Xun added final ISIS APP disposition coverage.
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

    def test_candidates_exist_only_at_the_isis10_source_path(self) -> None:
        if not self.isis9_root.is_dir() or not self.isis10_root.is_dir():
            self.skipTest("versioned upstream ISIS source trees are not restored")
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

    def test_application_headers_have_final_dispositions(self) -> None:
        classifications = inventory.HEADER_CLASSIFICATIONS
        self.assertEqual(
            classifications["csv2table.h"].disposition,
            "bound",
        )
        self.assertEqual(
            classifications["ocams2isis.h"].disposition,
            "native-app",
        )
        self.assertEqual(
            classifications["eisstitch.h"].disposition,
            "native-app",
        )

    def test_installed_header_diff_is_discovered_without_a_curated_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            isis9_prefix = root / "isis9"
            isis10_prefix = root / "isis10"
            isis9_headers = isis9_prefix / "include" / "isis"
            isis10_headers = isis10_prefix / "include" / "isis"
            isis9_headers.mkdir(parents=True)
            isis10_headers.mkdir(parents=True)
            for name in ("Common.h", "OnlyNine.h"):
                (isis9_headers / name).touch()
            for name in ("Common.h", "NewClass.h", "NewFunction.h", "NewInternal.hpp"):
                (isis10_headers / name).touch()

            self.assertEqual(
                ["NewClass.h", "NewFunction.h", "NewInternal.hpp"],
                inventory._discover_new_installed_headers(
                    isis9_prefix, isis10_prefix
                ),
            )

    def test_classification_gate_rejects_unclassified_discovered_headers(self) -> None:
        classifications = {
            "Known.h": inventory.HeaderClassification(
                "class", "candidate", "Known", "public class"
            )
        }
        with self.assertRaisesRegex(ValueError, "Unclassified ISIS 10 headers: New.h"):
            inventory._validate_header_classifications(
                ["Known.h", "New.h"], classifications
            )

    def test_raw_header_diff_records_every_discovered_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            classifications = {
                "Class.h": inventory.HeaderClassification(
                    "class", "candidate", "Class", "public class"
                ),
                "Internal.h": inventory.HeaderClassification(
                    "internal", "excluded", "", "third-party implementation"
                ),
            }
            inventory._write_raw_header_diff(
                output_dir, ["Class.h", "Internal.h"], classifications
            )
            with (output_dir / "raw_new_headers.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(["Class.h", "Internal.h"], [row["Header"] for row in rows])
            self.assertEqual(["candidate", "excluded"], [row["Disposition"] for row in rows])

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
                [
                    "Class Symbol",
                    "IProj",
                    "isis_pybind.IProj",
                    "Y",
                    "ISIS 10-only binding; tested against the target ISIS 10 environment",
                ],
                rows,
            )


if __name__ == "__main__":
    unittest.main()
