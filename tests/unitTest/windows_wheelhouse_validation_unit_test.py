"""Unit tests for Windows PyISIS wheelhouse release validation.

Author: Geng Xun
Created: 2026-08-16
Last Modified: 2026-08-16
Updated: 2026-08-16  Geng Xun added exact wheel, DLL closure, payload-boundary, and hash-report coverage.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "validate_windows_wheelhouse.py"


class WindowsWheelhouseValidationUnitTest(unittest.TestCase):
    """Test strict Windows wheelhouse release validation."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "validate_windows_wheelhouse",
            VALIDATOR_SCRIPT,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load validator from {VALIDATOR_SCRIPT}")
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def _write_valid_fixture(self, root: Path) -> tuple[Path, Path]:
        wheelhouse = root / "wheelhouse"
        wheelhouse.mkdir()
        main_members = ["isis_pybind/_isis_core.cp312-win_amd64.pyd"]
        runtime_members = [
            "pyisis_runtime/vendor/isis/bin/isis.dll",
            "pyisis_runtime/vendor/isis/lib/Camera.plugin",
        ]
        data_members = [
            "pyisis_isisdata_minimal/data/base/kernels/lsk/naif0012.tls",
        ]
        wheels = {
            "usgs_pyisis-1.3.0rc2-cp312-cp312-win_amd64.whl": main_members,
            "usgs_pyisis_runtime_win64-1.3.0rc2-py3-none-win_amd64.whl": runtime_members,
            "usgs_pyisis_isisdata_minimal-1.3.0rc2-py3-none-any.whl": data_members,
        }
        for filename, members in wheels.items():
            with zipfile.ZipFile(wheelhouse / filename, "w") as archive:
                for member in members:
                    archive.writestr(member, member.encode("utf-8"))

        (wheelhouse / "usgs-pyisis-runtime-win64-dll-dependencies.json").write_text(
            json.dumps({"schema_version": 1, "unresolved": []}),
            encoding="utf-8",
        )
        clean_install_report = root / "clean-install-report.json"
        clean_install_report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "passed",
                    "expected_isis_version": "9.0.0",
                    "checks": [
                        {"id": "wheel-install", "passed": 1},
                        {"id": "fresh-import", "passed": 1},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return wheelhouse, clean_install_report

    def test_validate_wheelhouse_reports_exact_artifacts_and_hashes(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self.validator.validate_wheelhouse(wheelhouse, clean_report)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(report["artifacts"]), 4)
        self.assertTrue(
            all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in report["artifacts"])
        )

    def test_validate_wheelhouse_rejects_missing_or_unexpected_wheels(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            (wheelhouse / "usgs_pyisis_isisdata_minimal-1.3.0rc2-py3-none-any.whl").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "exactly three wheels"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)
            (wheelhouse / "unexpected-1.0-py3-none-any.whl").write_bytes(b"unexpected")
            with self.assertRaisesRegex(FileNotFoundError, "exactly three wheels"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_unresolved_runtime_dependencies(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            dependency_report = wheelhouse / "usgs-pyisis-runtime-win64-dll-dependencies.json"
            dependency_report.write_text(
                json.dumps({"schema_version": 1, "unresolved": ["cspice.dll"]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileNotFoundError, "unresolved Windows runtime dependencies"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_app_executables_and_xml(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            runtime = wheelhouse / "usgs_pyisis_runtime_win64-1.3.0rc2-py3-none-win_amd64.whl"
            with zipfile.ZipFile(runtime, "a") as archive:
                archive.writestr("pyisis_runtime/vendor/isis/bin/reduce.exe", b"app")
            with self.assertRaisesRegex(ValueError, "forbidden ISIS APP payload"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)


if __name__ == "__main__":
    unittest.main()
