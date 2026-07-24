"""Unit tests for the installed ISIS API/ABI comparison tool.

Author: Geng Xun
Created: 2026-07-24
Last Modified: 2026-07-24
Updated: 2026-07-24  Geng Xun added header and exported-symbol difference coverage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "dev" / "compare_isis_installations.py"
SPEC = importlib.util.spec_from_file_location("compare_isis_installations", TOOL_PATH)
assert SPEC and SPEC.loader
comparison = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = comparison
SPEC.loader.exec_module(comparison)


class IsisInstallationComparisonUnitTest(unittest.TestCase):
    """Validate mechanical header and runtime symbol comparison."""

    def test_extract_header_api_ignores_comments_and_finds_declarations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            header = Path(temp_dir) / "Example.h"
            header.write_text(
                """
                // class CommentOnly {};
                class ISIS3SHARED_EXPORT Example {
                  public:
                    int value() const;
                };
                enum class Mode { A, B };
                /** @deprecated Use value() instead. */
                inline int oldValue() { return 0; }
                void freeFunction(double input);
                """,
                encoding="utf-8",
            )

            api = comparison.extract_header_api(header)

            self.assertEqual(frozenset({"Example"}), api.classes)
            self.assertEqual(frozenset({"Mode"}), api.enums)
            self.assertIn("int value()const;", api.callables)
            self.assertIn("void freeFunction(double input);", api.callables)
            self.assertIn("inline int oldValue(){", api.deprecated)

    def test_compare_headers_separates_non_declaration_and_api_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            isis9 = root / "isis9"
            isis10 = root / "isis10"
            headers9 = isis9 / "include" / "isis"
            headers10 = isis10 / "include" / "isis"
            headers9.mkdir(parents=True)
            headers10.mkdir(parents=True)
            (headers9 / "Doc.h").write_text("class Doc {};\n", encoding="utf-8")
            (headers10 / "Doc.h").write_text(
                "// changed documentation\nclass Doc {};\n", encoding="utf-8"
            )
            (headers9 / "Api.h").write_text(
                "class Api { int oldValue() const; };\n", encoding="utf-8"
            )
            (headers10 / "Api.h").write_text(
                "class Api { int newValue() const; };\n", encoding="utf-8"
            )
            (headers9 / "Removed.h").touch()
            (headers10 / "Added.hpp").touch()

            rows, counts = comparison.compare_headers(isis9, isis10)
            statuses = {row["header"]: row["status"] for row in rows}

            self.assertEqual("changed_non_declaration", statuses["Doc.h"])
            self.assertEqual("changed_declarations", statuses["Api.h"])
            self.assertEqual("removed", statuses["Removed.h"])
            self.assertEqual("added", statuses["Added.hpp"])
            self.assertEqual(1, counts["changed_declarations"])

    def test_parse_nm_output_and_group_changed_callable_signatures(self):
        parsed = comparison.parse_nm_output(
            """
            00000001 T Isis::Camera::value(int) const
            00000002 T Isis::freeFunction(double)
            00000003 V vtable for Isis::Camera
            00000004 W QList<Isis::Camera*>::reserve(long long)
            """
        )

        self.assertEqual("method", parsed["Isis::Camera::value(int) const"].kind)
        self.assertEqual("function", parsed["Isis::freeFunction(double)"].kind)
        self.assertEqual("type_metadata", parsed["vtable for Isis::Camera"].kind)
        self.assertEqual(
            "Isis::Camera::value",
            parsed["Isis::Camera::value(int) const"].callable_key,
        )
        self.assertNotIn("QList<Isis::Camera*>::reserve(long long)", parsed)


if __name__ == "__main__":
    unittest.main()
