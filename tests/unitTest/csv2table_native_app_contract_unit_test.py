"""Contract tests for csv2table as a native ISIS application only.

Author: Geng Xun
Created: 2026-08-17
Last Modified: 2026-08-17
Updated: 2026-08-17  Geng Xun added native-app-only csv2table boundary coverage.
Updated: 2026-08-17  Geng Xun required four-cell native APP evidence workflows.
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

    def test_linux_ci_collects_exact_dual_native_reports(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci-pybind.yml").read_text(
            encoding="utf-8"
        )

        for job, version, build, artifact in (
            (
                "csv2table-native-app-isis9",
                "9.0.0",
                "h1f94ec8_0",
                "csv2table-native-app-isis9-linux",
            ),
            (
                "csv2table-native-app-isis10",
                "10.0.0",
                "h1f94ec8_1",
                "csv2table-native-app-isis10-linux",
            ),
        ):
            self.assertIn(f"  {job}:", workflow)
            self.assertIn(f"EXPECTED_ISIS_VERSION: {version}", workflow)
            self.assertIn(f"EXPECTED_ISIS_BUILD: {build}", workflow)
            self.assertIn(f"--isis-version {version}", workflow)
            self.assertIn(f"name: {artifact}", workflow)

        self.assertIn("tools/dev/test_csv2table_native_app.py", workflow)
        self.assertIn(
            'assert report["summary"] == {"passed": 3, "failed": 0, "skipped": 0}',
            workflow,
        )
        self.assertIn('assert packages["csm"]["version"] == "3.0.3.3"', workflow)
        self.assertGreaterEqual(workflow.count('CONDA_PREFIX: ""'), 2)

    def test_windows_isis10_ci_collects_native_report_with_full_runtime_path(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github/workflows/windows-isis-apps.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("tools\\dev\\test_csv2table_native_app.py", workflow)
        self.assertIn("--isis-version 10.0.0", workflow)
        self.assertIn("csv2table-matrix\\isis10-windows.json", workflow)
        self.assertIn("name: csv2table-native-app-isis10-windows", workflow)
        self.assertIn(
            "assert report['summary'] == {'passed': 3, 'failed': 0, 'skipped': 0}",
            workflow,
        )
        for entry in (
            "Library\\bin",
            "Library\\usr\\bin",
            "Library\\mingw-w64\\bin",
            "Scripts",
            "bin",
        ):
            self.assertIn(entry, workflow)
