"""Contract tests for csv2table as a native ISIS application only.

Author: Geng Xun
Created: 2026-08-17
Last Modified: 2026-08-17
Updated: 2026-08-17  Geng Xun added native-app-only csv2table boundary coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Csv2TableNativeAppContractUnitTest(unittest.TestCase):
    """Verify csv2table remains a manifest-driven native ISIS application."""

    def test_python_facade_sources_are_absent(self) -> None:
        self.assertFalse((PROJECT_ROOT / "python/isis_pybind/_csv2table.py").exists())
        self.assertFalse((PROJECT_ROOT / "python/isis_pybind/_app_runner.py").exists())

    def test_build_does_not_package_facade_sources(self) -> None:
        cmake = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertNotIn("_csv2table.py", cmake)
        self.assertNotIn("_app_runner.py", cmake)

    def test_cpp_binding_has_no_csv2table_adapter(self) -> None:
        source = (PROJECT_ROOT / "src/bind_isis10.cpp").read_text(encoding="utf-8")
        self.assertNotIn("_csv2table_native", source)
        self.assertNotIn("runCsv2TableNative", source)
        self.assertNotIn('#include "csv2table.h"', source)
        self.assertNotIn('#include "UserInterface.h"', source)

    def test_manifest_keeps_csv2table_as_a_native_app(self) -> None:
        payload = json.loads(
            (PROJECT_ROOT / "ports/windows/isis/windows-app-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        app = next(item for item in payload["apps"] if item["name"] == "csv2table")
        self.assertEqual(app["xml"], "isis/src/base/apps/csv2table/csv2table.xml")
        self.assertEqual(set(app["versions"]), {"9.0.0", "10.0.0"})
