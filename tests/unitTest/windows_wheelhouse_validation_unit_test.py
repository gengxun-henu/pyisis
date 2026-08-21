"""Unit tests for Windows PyISIS wheelhouse release validation.

Author: Geng Xun
Created: 2026-08-16
Last Modified: 2026-08-21
Updated: 2026-08-16  Geng Xun added exact wheel, DLL closure, payload-boundary, and hash-report coverage.
Updated: 2026-08-16  Geng Xun added fail-closed clean-install check evidence coverage.
Updated: 2026-08-16  Geng Xun aligned the valid runtime fixture with the canonical ISIS library layout.
Updated: 2026-08-16  Geng Xun added strict evidence binding, ZIP safety, dependency-schema, and stale-report coverage.
Updated: 2026-08-21  Geng Xun aligned Windows wheelhouse fixtures with the rc3 release identity.
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import warnings
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "validate_windows_wheelhouse.py"
BASIC_TEST_LIST = PROJECT_ROOT / "tools" / "packaging" / "basic_tests.txt"
PACKAGE_VERSION = "1.3.0rc3"


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
            "pyisis_runtime/vendor/isis/lib/isis.dll",
            "pyisis_runtime/vendor/isis/lib/Camera.plugin",
        ]
        data_members = [
            "pyisis_isisdata_minimal/data/base/kernels/lsk/naif0012.tls",
        ]
        wheels = {
            "usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl": main_members,
            "usgs_pyisis_runtime_win64-1.3.0rc3-py3-none-win_amd64.whl": runtime_members,
            "usgs_pyisis_isisdata_minimal-1.3.0rc3-py3-none-any.whl": data_members,
        }
        for filename, members in wheels.items():
            with zipfile.ZipFile(wheelhouse / filename, "w") as archive:
                for member in members:
                    archive.writestr(member, member.encode("utf-8"))

        (wheelhouse / "usgs-pyisis-runtime-win64-dll-dependencies.json").write_text(
            json.dumps({"schema_version": 1, "binaries": [], "unresolved": []}),
            encoding="utf-8",
        )
        basic_modules = [
            line
            for raw_line in BASIC_TEST_LIST.read_text(encoding="utf-8").splitlines()
            if (line := raw_line.strip()) and not line.startswith("#")
        ]
        wheel_records = []
        for wheel in sorted(wheelhouse.glob("*.whl"), key=lambda path: path.name):
            wheel_records.append(
                {
                    "name": wheel.name,
                    "size": wheel.stat().st_size,
                    "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                }
            )
        venv = root / "clean venv"
        site_packages = venv / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)
        checks = [
            self._check("wheel-install"),
            self._check("fresh-import"),
            *(self._check(f"unit-module:{module}", passed=2) for module in basic_modules),
        ]
        checks[0]["command"] = (
            "python -m pip --isolated install --no-cache-dir --no-index "
            f"--find-links {wheelhouse.resolve()} usgs-pyisis=={PACKAGE_VERSION}"
        )
        clean_install_report = root / "clean-install-report.json"
        clean_install_report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package": f"usgs-pyisis=={PACKAGE_VERSION}",
                    "wheelhouse": str(wheelhouse.resolve()),
                    "venv": str(venv.resolve()),
                    "status": "passed",
                    "expected_isis_version": "9.0.0",
                    "pip_install_flags": [
                        "--isolated",
                        "--no-cache-dir",
                        "--no-index",
                        "--find-links",
                    ],
                    "sanitized_environment": {
                        "removed_variable_names": [
                            "CONDA_PREFIX",
                            "ISIS_PREFIX",
                            "ISISROOT",
                            "ISISDATA",
                            "PYISIS_DEP_PREFIX",
                            "PYISIS_WINDOWS_DEP_PREFIX",
                            "PYTHONHOME",
                            "PYTHONPATH",
                        ],
                        "remove_all_pip_variables": True,
                    },
                    "wheel_artifacts": wheel_records,
                    "basic_tests": {
                        "path": str(BASIC_TEST_LIST.resolve()),
                        "sha256": hashlib.sha256(BASIC_TEST_LIST.read_bytes()).hexdigest(),
                        "modules": basic_modules,
                    },
                    "installed_distributions": [
                        {
                            "name": name,
                            "version": PACKAGE_VERSION,
                            "location": str(site_packages.resolve()),
                        }
                        for name in (
                            "usgs-pyisis",
                            "usgs-pyisis-runtime-win64",
                            "usgs-pyisis-isisdata-minimal",
                        )
                    ],
                    "checks": checks,
                }
            ),
            encoding="utf-8",
        )
        return wheelhouse, clean_install_report

    @staticmethod
    def _check(check_id: str, *, passed: int = 1) -> dict[str, object]:
        command = f"run {check_id}"
        if check_id == "wheel-install":
            command = (
                "python -m pip --isolated install --no-cache-dir --no-index "
                "--find-links wheelhouse usgs-pyisis==1.3.0rc3"
            )
        return {
            "id": check_id,
            "command": command,
            "cwd": "C:/clean venv",
            "environment": {"removed": [], "set": {}, "path_entries_removed": []},
            "passed": passed,
            "failed": 0,
            "skipped": 0,
            "expected_failures": 0,
            "exit_code": 0,
        }

    @staticmethod
    def _read_report(clean_report: Path) -> dict[str, object]:
        return json.loads(clean_report.read_text(encoding="utf-8"))

    @staticmethod
    def _write_report(clean_report: Path, report: dict[str, object]) -> None:
        clean_report.write_text(json.dumps(report), encoding="utf-8")

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
            (wheelhouse / "usgs_pyisis_isisdata_minimal-1.3.0rc3-py3-none-any.whl").unlink()
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
                json.dumps(
                    {"schema_version": 1, "binaries": [], "unresolved": ["cspice.dll"]}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileNotFoundError, "unresolved Windows runtime dependencies"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_app_executables_and_xml(self):
        cases = (
            ("usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl", "isis_pybind/reduce.exe"),
            ("usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl", "bin/xml/reduce.par"),
            (
                "usgs_pyisis_runtime_win64-1.3.0rc3-py3-none-win_amd64.whl",
                "pyisis_runtime/vendor/isis/bin/xml/reduce.xml",
            ),
            (
                "usgs_pyisis_isisdata_minimal-1.3.0rc3-py3-none-any.whl",
                "pyisis_isisdata_minimal/reduce.xml",
            ),
        )
        for wheel_name, member in cases:
            with self.subTest(wheel=wheel_name, member=member), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                with zipfile.ZipFile(wheelhouse / wheel_name, "a") as archive:
                    archive.writestr(member, b"app")
                with self.assertRaisesRegex(ValueError, "forbidden ISIS APP payload"):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_unsafe_or_colliding_zip_members(self):
        cases = (
            ("../escape", "unsafe wheel member"),
            ("/absolute", "unsafe wheel member"),
            ("C:/absolute", "unsafe wheel member"),
            (r"isis_pybind\\escape", "unsafe wheel member"),
            ("isis_pybind/./escape", "unsafe wheel member"),
            ("isis_pybind//escape", "unsafe wheel member"),
        )
        binding_name = "usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl"
        for member, message in cases:
            with self.subTest(member=member), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                with zipfile.ZipFile(wheelhouse / binding_name, "a") as archive:
                    archive.writestr(member, b"unsafe")
                with self.assertRaisesRegex(ValueError, message):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

        for members, message in (
            (("isis_pybind/duplicate", "isis_pybind/duplicate"), "duplicate wheel member"),
            (("isis_pybind/CaseName", "isis_pybind/casename"), "case-colliding wheel member"),
        ):
            with self.subTest(members=members), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                with zipfile.ZipFile(wheelhouse / binding_name, "a") as archive:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        for member in members:
                            archive.writestr(member, b"collision")
                with self.assertRaisesRegex(ValueError, message):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_requires_payload_exactly_once_as_file(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            binding = wheelhouse / "usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl"
            with zipfile.ZipFile(binding, "a") as archive:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(
                        "isis_pybind/_isis_core.cp312-win_amd64.pyd",
                        b"duplicate",
                    )
            with self.assertRaisesRegex(ValueError, "duplicate wheel member"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_malformed_dependency_report(self):
        cases = (
            ({"schema_version": True, "binaries": [], "unresolved": []}, "schema_version"),
            ({"schema_version": 1, "unresolved": []}, "binaries"),
            ({"schema_version": 1, "binaries": {}, "unresolved": []}, "binaries"),
            ({"schema_version": 1, "binaries": [], "unresolved": {}}, "unresolved"),
        )
        for payload, message in cases:
            with self.subTest(payload=payload), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                dependency_report = wheelhouse / "usgs-pyisis-runtime-win64-dll-dependencies.json"
                dependency_report.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_binds_clean_report_to_current_inputs(self):
        mutations = (
            ("package", "usgs-pyisis==9.9.9", "package"),
            ("wheelhouse", "C:/wrong-wheelhouse", "wheelhouse"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                report = self._read_report(clean_report)
                report[field] = value
                self._write_report(clean_report, report)
                with self.assertRaisesRegex(ValueError, message):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["wheel_artifacts"][0]["sha256"] = "0" * 64
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "wheel artifact"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_requires_reported_pip_isolation_command(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["checks"][0]["command"] = "python -m pip install usgs-pyisis"
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "pip command"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["sanitized_environment"]["remove_all_pip_variables"] = False
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "sanitized environment"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_requires_exact_basic_checks_and_strict_counts(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["checks"] = report["checks"][:-1]
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "exact required check set"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

        mutations = (
            ("passed", True, "integer"),
            ("failed", 1, "did not pass"),
            ("exit_code", 1, "did not pass"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field), TemporaryDirectory() as temp_dir:
                wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
                report = self._read_report(clean_report)
                report["checks"][0][field] = value
                self._write_report(clean_report, report)
                with self.assertRaisesRegex(ValueError, message):
                    self.validator.validate_wheelhouse(wheelhouse, clean_report)

        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["checks"].append(dict(report["checks"][0]))
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "duplicate check"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_basic_test_declaration_or_origin_drift(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["basic_tests"]["sha256"] = "0" * 64
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "basic test declaration"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wheelhouse, clean_report = self._write_valid_fixture(root)
            report = self._read_report(clean_report)
            report["installed_distributions"][0]["location"] = str(root / "repository-source")
            self._write_report(clean_report, report)
            with self.assertRaisesRegex(ValueError, "outside clean venv"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_failed_clean_install_check(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["checks"][1]["passed"] = 0
            clean_report.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fresh-import.*did not pass"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validate_wheelhouse_rejects_missing_clean_install_check(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
            report = self._read_report(clean_report)
            report["checks"] = [
                check for check in report["checks"] if check["id"] != "fresh-import"
            ]
            clean_report.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fresh-import.*missing"):
                self.validator.validate_wheelhouse(wheelhouse, clean_report)

    def test_validator_cli_invalidates_stale_final_report_before_validation(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wheelhouse, clean_report = self._write_valid_fixture(root)
            (wheelhouse / "usgs_pyisis-1.3.0rc3-cp312-cp312-win_amd64.whl").unlink()
            final_report = root / "final-report.json"
            final_report.write_text('{"status": "passed"}\n', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR_SCRIPT),
                    "--wheelhouse",
                    str(wheelhouse),
                    "--clean-install-report",
                    str(clean_report),
                    "--report",
                    str(final_report),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(final_report.exists())


if __name__ == "__main__":
    unittest.main()
