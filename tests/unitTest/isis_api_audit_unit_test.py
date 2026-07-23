"""Unit tests for the ISIS 9/10 binding-header audit tool.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun added header comparison and GUI filtering coverage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_TOOL = PROJECT_ROOT / "tools" / "dev" / "audit_isis_api.py"


def _load_audit_tool():
    spec = importlib.util.spec_from_file_location("audit_isis_api", AUDIT_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {AUDIT_TOOL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IsisApiAuditUnitTest(unittest.TestCase):
    """Test deterministic binding-header comparison. Added: 2026-07-23."""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_audit_tool()

    def _write_fixture(
        self,
        root: Path,
        relative_path: str,
        content: str,
    ) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_extracts_bound_headers_and_symbols(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "src"
            self._write_fixture(
                source_root,
                "bind_cube.cpp",
                '#include <Cube.h>\n#include <QString>\n'
                'py::class_<Isis::Cube>(module, "Cube");\n',
            )

            references = self.module.extract_binding_references(source_root, root)

            self.assertEqual(
                references,
                [
                    self.module.BindingReference(
                        "src/bind_cube.cpp",
                        "Cube.h",
                        ("Cube",),
                    )
                ],
            )

    def test_compares_headers_and_filters_direct_gui_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "src"
            isis9_root = root / "isis9"
            isis10_root = root / "isis10"
            self._write_fixture(
                source_root,
                "bind.cpp",
                "\n".join(
                    [
                        "#include <Stable.h>",
                        "#include <Changed.h>",
                        "#include <Observer.h>",
                        "#include <Window.h>",
                    ]
                ),
            )
            for version_root in (isis9_root, isis10_root):
                self._write_fixture(
                    version_root,
                    "src/base/objs/Stable/Stable.h",
                    "class Stable {};",
                )
                self._write_fixture(
                    version_root,
                    "src/base/objs/Observer/Observer.h",
                    "class Observer : public QObject { Q_OBJECT\nsignals:\n void changed(); };",
                )
                self._write_fixture(
                    version_root,
                    "src/qisis/objs/Window/Window.h",
                    "class Window : public QWidget {};",
                )
            self._write_fixture(
                isis9_root,
                "src/base/objs/Changed/Changed.h",
                "class Changed { void old_api(); };",
            )
            self._write_fixture(
                isis10_root,
                "src/base/objs/Changed/Changed.h",
                "class Changed { void new_api(); };",
            )

            rows = self.module.create_audit_rows(
                source_root,
                isis9_root,
                isis10_root,
                root,
            )

            by_header = {row["header"]: row for row in rows}
            self.assertEqual(
                set(by_header),
                {"Changed.h", "Observer.h", "Stable.h"},
            )
            self.assertEqual(
                by_header["Stable.h"]["comparison"],
                "identical_text",
            )
            self.assertEqual(
                by_header["Changed.h"]["comparison"],
                "changed_review_required",
            )
            self.assertEqual(
                by_header["Observer.h"]["gui_status"],
                "qt_observer_review",
            )

    def test_marks_headers_missing_from_isis10(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "src"
            isis9_root = root / "isis9"
            isis10_root = root / "isis10"
            isis10_root.mkdir()
            self._write_fixture(source_root, "bind.cpp", "#include <Legacy.h>\n")
            self._write_fixture(
                isis9_root,
                "src/base/objs/Legacy/Legacy.h",
                "class Legacy {};",
            )

            rows = self.module.create_audit_rows(
                source_root,
                isis9_root,
                isis10_root,
                root,
            )

            self.assertEqual(rows[0]["comparison"], "missing_in_isis10")

    def test_identifies_known_isis10_header_rename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "src"
            isis9_root = root / "isis9"
            isis10_root = root / "isis10"
            self._write_fixture(source_root, "bind.cpp", "#include <Endian.h>\n")
            self._write_fixture(
                isis9_root,
                "isis/src/base/objs/Endian/Endian.h",
                "enum ByteOrder { Lsb, Msb };",
            )
            self._write_fixture(
                isis10_root,
                "isis/src/core/include/IEndian.h",
                "enum ByteOrder { Lsb, Msb };",
            )

            rows = self.module.create_audit_rows(
                source_root,
                isis9_root,
                isis10_root,
                root,
            )

            self.assertEqual(
                rows[0]["comparison"],
                "renamed_review_required",
            )
            self.assertIn("IEndian.h:", rows[0]["replacement_hint"])

    def test_report_uses_portable_labels_and_matrix_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_path = root / "report.md"
            row = {
                "binding_file": "src/bind.cpp",
                "header": "Stable.h",
                "bound_symbols": "Stable",
                "gui_status": "non_gui",
                "isis9_status": "present",
                "isis10_status": "present",
                "comparison": "identical_text",
                "replacement_hint": "",
                "isis9_paths": "Stable.h",
                "isis10_paths": "Stable.h",
            }

            self.module.write_report(
                [row],
                output_path,
                root / "private-isis9",
                root / "private-isis10",
                "ISIS 9 test prefix",
                "ISIS 10 test prefix",
                "custom-matrix.csv",
            )
            report = output_path.read_text(encoding="utf-8")

            self.assertIn("ISIS 9 test prefix", report)
            self.assertIn("ISIS 10 test prefix", report)
            self.assertIn("custom-matrix.csv", report)
            self.assertNotIn("private-isis9", report)


if __name__ == "__main__":
    unittest.main()
