"""Unit tests for local wheel packaging tools.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-19
Updated: 2026-06-18  Geng Xun added local wheel build and install verification coverage.
Updated: 2026-06-19  Geng Xun added TestPyPI API token helper coverage.
Updated: 2026-06-19  Geng Xun covered usgs-pyisis wheel distribution names.
Updated: 2026-06-19  Geng Xun added Linux runtime wheel build helper coverage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_WHEELS_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "build_wheels.ps1"
LINUX_BUILD_WHEELS_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "build_wheels_linux.sh"
TEST_WHEEL_INSTALL_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "test_wheel_install.py"
PUBLISH_TESTPYPI_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "publish_testpypi.ps1"
TEST_TESTPYPI_INSTALL_SCRIPT = (
    PROJECT_ROOT / "tools" / "packaging" / "test_testpypi_install.py"
)


class PackagingToolsUnitTest(unittest.TestCase):
    """Test suite for wheel packaging helper scripts. Added: 2026-06-18."""

    def test_build_wheels_script_runs_all_local_wheel_steps(self):
        self.assertTrue(BUILD_WHEELS_SCRIPT.is_file())

        script = BUILD_WHEELS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("stage_runtime_win64.py", script)
        self.assertIn("--dependency-prefix", script)
        self.assertIn("--dependency-copy-mode closure", script)
        self.assertIn("wheel tags --platform-tag win_amd64", script)
        self.assertIn("packaging\\isisdata-minimal", script)
        self.assertIn("build\\packaging\\usgs-pyisis-runtime-win64", script)
        self.assertIn("usgs_pyisis_runtime_win64-*-py3-none-any.whl", script)
        self.assertIn("-m build . --wheel --no-isolation --skip-dependency-check", script)

    def test_linux_build_wheels_script_runs_runtime_and_main_wheel_steps(self):
        self.assertTrue(LINUX_BUILD_WHEELS_SCRIPT.is_file())

        script = LINUX_BUILD_WHEELS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("stage_runtime_linux.py", script)
        self.assertIn("--dependency-prefix", script)
        self.assertIn("--dependency-copy-mode closure", script)
        self.assertIn("usgs-pyisis-runtime-linux-x86_64", script)
        self.assertIn("manylinux_2_28_x86_64", script)
        self.assertIn("usgs_pyisis_runtime_linux_x86_64-*-py3-none-any.whl", script)
        self.assertIn("packaging/isisdata-minimal", script)
        self.assertIn("-m build . --wheel --no-isolation --skip-dependency-check", script)

    def test_clean_venv_install_script_installs_from_wheelhouse(self):
        self.assertTrue(TEST_WHEEL_INSTALL_SCRIPT.is_file())

        script = TEST_WHEEL_INSTALL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--no-index", script)
        self.assertIn("--find-links", script)
        self.assertIn("usgs-pyisis", script)
        self.assertIn("pyisis", script)
        self.assertIn("status.usable_for_smoke_tests", script)
        self.assertIn("_verification_environment", script)
        self.assertIn("ISIS_PREFIX", script)
        self.assertIn("CONDA_PREFIX", script)

    def test_clean_venv_install_script_selects_platform_python_path(self):
        self.assertTrue(TEST_WHEEL_INSTALL_SCRIPT.is_file())

        spec = importlib.util.spec_from_file_location(
            "test_wheel_install",
            TEST_WHEEL_INSTALL_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(
            module._python_executable(Path("venv")).name,
            "python.exe",
        )

    def test_clean_venv_verification_environment_removes_external_runtime(self):
        self.assertTrue(TEST_WHEEL_INSTALL_SCRIPT.is_file())

        spec = importlib.util.spec_from_file_location(
            "test_wheel_install",
            TEST_WHEEL_INSTALL_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        runtime_root = PROJECT_ROOT / "build" / "windows" / "isis-prefix"
        dependency_root = PROJECT_ROOT / "fake-conda"
        path = ";".join(
            [
                str(runtime_root / "bin"),
                str(dependency_root / "Library" / "bin"),
                r"C:\Windows\System32",
            ]
        )
        with mock.patch.dict(
            module.os.environ,
            {
                "ISIS_PREFIX": str(runtime_root),
                "ISISROOT": str(runtime_root),
                "ISISDATA": str(PROJECT_ROOT / "tests" / "data" / "isisdata" / "mockup"),
                "PYISIS_DEP_PREFIX": str(dependency_root),
                "CONDA_PREFIX": str(dependency_root),
                "PYTHONPATH": str(PROJECT_ROOT / "build" / "python"),
                "PATH": path,
            },
            clear=True,
        ):
            env = module._verification_environment()

        self.assertNotIn("ISIS_PREFIX", env)
        self.assertNotIn("ISISROOT", env)
        self.assertNotIn("ISISDATA", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("CONDA_PREFIX", env)
        self.assertEqual(env["PATH"], r"C:\Windows\System32")

    def test_testpypi_publish_script_checks_wheels_before_optional_upload(self):
        self.assertTrue(PUBLISH_TESTPYPI_SCRIPT.is_file())

        script = PUBLISH_TESTPYPI_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("twine check", script)
        self.assertIn("[ValidateSet(\"testpypi\")]", script)
        self.assertIn('$Repository = "testpypi"', script)
        self.assertIn("twine upload --repository $Repository", script)
        self.assertIn("[switch]$Upload", script)
        self.assertIn("[switch]$CheckOnly", script)
        self.assertIn("if (-not $Upload)", script)
        self.assertIn("PSBoundParameters.ContainsKey(\"Wheelhouse\")", script)
        self.assertIn("ExpectedWheelNames", script)
        self.assertIn("usgs_pyisis-$ExpectedVersion-cp312-cp312-win_amd64.whl", script)
        self.assertIn("usgs_pyisis_runtime_win64-$ExpectedVersion-py3-none-win_amd64.whl", script)
        self.assertIn("usgs_pyisis_isisdata_minimal-$ExpectedVersion-py3-none-any.whl", script)
        self.assertIn("Upload switch was not set", script)

    def test_testpypi_publish_script_can_use_testpypi_api_token(self):
        self.assertTrue(PUBLISH_TESTPYPI_SCRIPT.is_file())

        script = PUBLISH_TESTPYPI_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("TESTPYPI_API_TOKEN", script)
        self.assertIn('$env:TWINE_USERNAME = "__token__"', script)
        self.assertIn('$env:TWINE_PASSWORD = $env:TESTPYPI_API_TOKEN', script)

    def test_testpypi_install_script_installs_from_testpypi_with_pypi_fallback(self):
        self.assertTrue(TEST_TESTPYPI_INSTALL_SCRIPT.is_file())

        script = TEST_TESTPYPI_INSTALL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("https://test.pypi.org/simple", script)
        self.assertIn("https://pypi.org/simple", script)
        self.assertIn("--index-url", script)
        self.assertIn("--extra-index-url", script)
        self.assertIn('default="usgs-pyisis"', script)
        self.assertIn("pyisis", script)
        self.assertIn("_verification_environment", script)
        self.assertIn("status.usable_for_smoke_tests", script)


if __name__ == "__main__":
    unittest.main()
