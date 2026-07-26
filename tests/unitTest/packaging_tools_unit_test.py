"""Unit tests for local wheel packaging tools.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-07-25
Updated: 2026-06-18  Geng Xun added local wheel build and install verification coverage.
Updated: 2026-06-19  Geng Xun added TestPyPI API token helper coverage.
Updated: 2026-06-19  Geng Xun covered usgs-pyisis wheel distribution names.
Updated: 2026-06-19  Geng Xun added Linux runtime wheel build helper coverage.
Updated: 2026-06-19  Geng Xun made wheel helper tests portable under WSL.
Updated: 2026-07-22  Geng Xun covered optional clean-wheel unittest lists.
Updated: 2026-07-22  Geng Xun required truthful Linux platform tags and preinstalled conda build tools.
Updated: 2026-07-22  Geng Xun covered CRLF-safe Windows ISIS patch application.
Updated: 2026-07-22  Geng Xun covered clean-wheel unit-test helper discovery.
Updated: 2026-07-22  Geng Xun kept clean-wheel binding tests independent of NumPy.
Updated: 2026-07-23  Geng Xun covered Linux runtime size budgets and audited platform retagging.
Updated: 2026-07-23  Geng Xun required PEP 639-capable setuptools for Windows wheel builds.
Updated: 2026-07-23  Geng Xun covered versioned package and ISIS runtime checks during clean installs.
Updated: 2026-07-23  Geng Xun covered parameterized ISIS 9/10 Windows wheel builds.
Updated: 2026-07-24  Geng Xun covered private Linux toolchain runtime packaging and the split ISIS 10 Windows patch queue.
Updated: 2026-07-24  Geng Xun preserved qisis data objects and exported SpiceQL symbols on Windows.
Updated: 2026-07-25  Geng Xun covered the ISIS 10 SpiceQL 1.4.1 export and MSVC link gates.
Updated: 2026-07-25  Geng Xun parameterized Windows wheel-set checks for ISIS 9 and ISIS 10.
Updated: 2026-07-25  Geng Xun covered the Windows APP manifest and allowlisted reduce target.
Updated: 2026-07-26  Geng Xun covered the 21-APP Windows build and smoke batch.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_WHEELS_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "build_wheels.ps1"
LINUX_BUILD_WHEELS_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "build_wheels_linux.sh"
WINDOWS_ISIS_PATCHES_DIR = PROJECT_ROOT / "ports" / "windows" / "isis" / "patches"
WINDOWS_ISIS_DIR = PROJECT_ROOT / "ports" / "windows" / "isis"
WINDOWS_ISIS_APP_MANIFEST = WINDOWS_ISIS_DIR / "windows-app-manifest.json"
WINDOWS_ISIS_APP_WORKFLOW = (
    PROJECT_ROOT / ".github" / "workflows" / "windows-isis-apps.yml"
)
UNIT_TEST_SUPPORT = PROJECT_ROOT / "tests" / "unitTest" / "_unit_test_support.py"
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
        self.assertIn('"setuptools>=77"', script)
        self.assertIn("stage_runtime_win64.py", script)
        self.assertIn("--dependency-prefix", script)
        self.assertIn("--dependency-copy-mode closure", script)
        self.assertIn("wheel tags --platform-tag win_amd64", script)
        self.assertIn("packaging\\isisdata-minimal", script)
        self.assertIn("build\\packaging\\$RuntimeDistribution", script)
        self.assertIn('$RuntimeDistribution.Replace("-", "_")', script)
        self.assertIn(
            "-m build $BindingProjectDir --wheel --no-isolation "
            "--skip-dependency-check",
            script,
        )
        self.assertIn('$DistributionName.Replace("-", "_")', script)
        self.assertIn("--distribution-name $RuntimeDistribution", script)
        self.assertIn("--package-version $PackageVersion", script)

    def test_linux_build_wheels_script_runs_runtime_and_main_wheel_steps(self):
        self.assertTrue(LINUX_BUILD_WHEELS_SCRIPT.is_file())

        script = LINUX_BUILD_WHEELS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("stage_runtime_linux.py", script)
        self.assertIn("--dependency-prefix", script)
        self.assertIn("--dependency-copy-mode closure", script)
        self.assertIn("build_linux_audit_bundle.py", script)
        self.assertIn("vendor_linux_toolchain_runtime.py", script)
        self.assertIn("--vendor-toolchain-runtime", script)
        self.assertIn("wheel tags", script)
        self.assertIn("auditwheel repair", script)
        self.assertIn('PYISIS_LINUX_PLATFORM_TAG:-linux_x86_64', script)
        self.assertIn('--plat "$platform_tag"', script)
        self.assertIn('--max-runtime-bytes "$max_runtime_bytes"', script)
        self.assertIn("PYISIS_MAX_LINUX_RUNTIME_WHEEL_BYTES", script)
        self.assertNotIn("manylinux_2_28_x86_64", script)
        self.assertNotIn("pip install", script)
        self.assertIn(
            "PYISIS_RUNTIME_DISTRIBUTION:-usgs-pyisis-runtime-linux-x86_64",
            script,
        )
        self.assertIn('runtime_normalized="${runtime_distribution//-/_}"', script)
        self.assertIn('--runtime-dependency "$runtime_distribution"', script)
        self.assertIn('"$binding_project_dir"', script)
        self.assertIn("packaging/isisdata-minimal", script)
        self.assertIn(
            '-m build "$binding_project_dir" --wheel --no-isolation '
            "--skip-dependency-check",
            script,
        )

    def test_windows_patch_queue_avoids_no_newline_only_hunks(self):
        patch_paths = sorted(WINDOWS_ISIS_PATCHES_DIR.glob("**/*.patch"))
        self.assertTrue(patch_paths)

        patches = {
            patch_path.relative_to(WINDOWS_ISIS_PATCHES_DIR).as_posix():
                patch_path.read_text(encoding="utf-8")
            for patch_path in patch_paths
        }
        for patch_name, patch in patches.items():
            with self.subTest(patch=patch_name):
                self.assertNotIn("No newline at end of file", patch)

        self.assertNotIn(
            "@@ -58,4 +62,4",
            patches["0002-windows-cmake-portability.patch"],
        )
        self.assertNotIn(
            "@@ -3040,4 +3039,4",
            patches["0004-windows-isis-core-msvc-portability.patch"],
        )

    def test_isis10_windows_port_has_versioned_environment_and_patch_queue(self):
        env_file = (
            PROJECT_ROOT
            / "ports"
            / "windows"
            / "env"
            / "pyisis-isis10-win64.yml"
        )
        spiceql_script = (
            PROJECT_ROOT / "ports" / "windows" / "isis" / "build_spiceql.ps1"
        )
        patch_dir = WINDOWS_ISIS_PATCHES_DIR / "10.0.0"

        self.assertTrue(env_file.is_file())
        environment = env_file.read_text(encoding="utf-8")
        self.assertIn("python=3.13", environment)
        self.assertIn("qt6-main", environment)
        self.assertIn("pcl", environment)
        self.assertIn("cereal", environment)

        self.assertTrue(spiceql_script.is_file())
        spiceql = spiceql_script.read_text(encoding="utf-8")
        self.assertIn("DOI-USGS/SpiceQL.git", spiceql)
        self.assertIn('[string]$Ref = "1.4.1"', spiceql)
        self.assertIn("SPICEQL_BUILD_TESTS=OFF", spiceql)
        self.assertIn("SpiceQL.dll", spiceql)
        self.assertIn("dumpbin /nologo /exports", spiceql)
        self.assertIn("SpiceQL DLL does not export strSclkToEt", spiceql)
        self.assertIn("spiceql-link-probe.cpp", spiceql)
        self.assertIn("Invoke-CheckedCommand link", spiceql)

        apply_script = (
            PROJECT_ROOT / "ports" / "windows" / "isis" / "apply_patches.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("apply --unidiff-zero --check", apply_script)

        patch_paths = sorted(patch_dir.glob("*.patch"))
        self.assertEqual(len(patch_paths), 3)
        patches = [path.read_text(encoding="utf-8") for path in patch_paths]
        self.assertIn("isis/src/core/src/Pvl.cpp", patches[0])
        self.assertIn("Trim Windows runtime to non-GUI core", patches[1])
        self.assertIn("set(thisAppFolders)", patches[1])
        self.assertIn("ISIS_DISABLED_OBJ_FOLDERS BundleAdjust", patches[1])
        self.assertIn(
            'list(REMOVE_ITEM modules "${CMAKE_CURRENT_LIST_DIR}/qisis")',
            patches[1],
        )
        self.assertIn("BundleSolutionInfo.cpp", patches[1])
        self.assertIn("#if defined(_MSC_VER)", patches[1])
        self.assertIn("ISIS_WINDOWS_APP_ALLOWLIST", patches[2])
        self.assertIn("Adding allowlisted Windows ISIS app", patches[2])
        self.assertIn(
            "compiled directly into their standalone executable",
            patches[2],
        )

        spiceql_patch = (
            WINDOWS_ISIS_PATCHES_DIR
            / "spiceql-1.4.1"
            / "0001-Export-SpiceQL-symbols-on-Windows.patch"
        ).read_text(encoding="utf-8")
        self.assertIn("WINDOWS_EXPORT_ALL_SYMBOLS ON", spiceql_patch)
        self.assertIn("find_package(nlohmann_json CONFIG REQUIRED)", spiceql_patch)
        self.assertIn('-  add_subdirectory("submodules/json")', spiceql_patch)

    def test_windows_app_manifest_drives_the_allowlisted_batch(self):
        self.assertTrue(WINDOWS_ISIS_APP_MANIFEST.is_file())
        manifest = json.loads(
            WINDOWS_ISIS_APP_MANIFEST.read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], 1)

        for version in ("9.0.0", "10.0.0"):
            with self.subTest(version=version):
                lock_path = (
                    PROJECT_ROOT
                    / "reference"
                    / f"upstream_isis-{version.split('.')[0]}.lock.json"
                )
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
                baseline = manifest["source_baselines"][version]
                self.assertEqual(baseline["ref"], lock["revision"])
                self.assertEqual(baseline["commit"], lock["commit"])

        expected_apps = {
            "algebra",
            "bit2bit",
            "catlab",
            "crop",
            "cubeatt",
            "cubediff",
            "cubenorm",
            "enlarge",
            "fillgap",
            "flip",
            "fx",
            "getkey",
            "gradient",
            "mask",
            "mirror",
            "noisefilter",
            "ratio",
            "reduce",
            "stats",
            "stretch",
            "trim",
        }
        apps = {app["name"]: app for app in manifest["apps"]}
        self.assertEqual(set(apps), expected_apps)
        self.assertEqual(len(apps) - 1, 20)
        self.assertEqual(
            manifest["app_defaults"]["windows_patch"],
            "patches/10.0.0/"
            "0003-Build-allowlisted-Windows-apps-as-executables.patch",
        )
        self.assertTrue(
            (
                WINDOWS_ISIS_DIR
                / manifest["app_defaults"]["windows_patch"]
            ).is_file()
        )
        for name, app in apps.items():
            with self.subTest(app=name):
                self.assertEqual(
                    app["source_dir"],
                    f"isis/src/base/apps/{name}",
                )
                self.assertEqual(
                    app["xml"],
                    f"isis/src/base/apps/{name}/{name}.xml",
                )
                self.assertIn(app["smoke_tier"], {"startup", "cube"})
                self.assertEqual(
                    app["versions"]["10.0.0"]["status"],
                    "experimental",
                )

        reduce_app = apps["reduce"]
        self.assertEqual(reduce_app["source_dir"], "isis/src/base/apps/reduce")
        self.assertEqual(reduce_app["xml"], "isis/src/base/apps/reduce/reduce.xml")
        self.assertEqual(reduce_app["versions"]["9.0.0"]["status"], "supported")
        self.assertEqual(
            reduce_app["versions"]["10.0.0"]["status"],
            "experimental",
        )
        self.assertEqual(
            reduce_app["versions"]["10.0.0"]["build_status"],
            "compiled_installed",
        )
        self.assertEqual(
            reduce_app["versions"]["10.0.0"]["smoke_status"],
            "minimal_passed",
        )

        configure_script = (
            WINDOWS_ISIS_DIR / "configure_isis.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[string[]]$WindowsApps", configure_script)
        self.assertIn("windows-app-manifest.json", configure_script)
        self.assertIn("ISIS_WINDOWS_APP_ALLOWLIST", configure_script)
        self.assertIn("source revision mismatch", configure_script)

        build_script = (
            WINDOWS_ISIS_DIR / "build_isis.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[string[]]$Targets", build_script)
        self.assertIn('@("--target") + $Targets', build_script)

        batch_smoke = (
            WINDOWS_ISIS_DIR / "test_isis_app_batch_smoke.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("$appNames.Count -lt 21", batch_smoke)
        self.assertIn('Join-Path $Prefix "bin\\$Name.exe"', batch_smoke)
        self.assertIn('Invoke-IsisApp $appName @("-HELP")', batch_smoke)
        for name in expected_apps:
            with self.subTest(smoke_app=name):
                self.assertIn(f'"{name}"', batch_smoke)

        self.assertTrue(WINDOWS_ISIS_APP_WORKFLOW.is_file())
        workflow = WINDOWS_ISIS_APP_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("windows-isis-apps", workflow)
        self.assertIn("runs-on: windows-2022", workflow)
        self.assertIn("-IsisVersion 10.0.0", workflow)
        self.assertIn("-WindowsApps $apps", workflow)
        self.assertIn("test_isis_app_batch_smoke.ps1", workflow)
        self.assertIn("windows-isis10-app-batch-smoke-logs", workflow)

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
        self.assertIn("--test-list", script)
        self.assertIn("--package", script)
        self.assertIn("--expected-isis-version", script)
        self.assertIn("__isis_version__", script)
        self.assertIn('"-m", "unittest"', script)

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

        expected_name = "python.exe" if module.sys.platform == "win32" else "python"
        self.assertEqual(module._python_executable(Path("venv")).name, expected_name)

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
        safe_path = PROJECT_ROOT / "safe-bin"
        path = module.os.pathsep.join(
            [
                str(runtime_root / "bin"),
                str(dependency_root / "Library" / "bin"),
                str(safe_path),
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
        self.assertEqual(env["PATH"], str(safe_path))

    def test_clean_venv_unit_test_environment_exposes_only_test_helpers(self):
        self.assertTrue(TEST_WHEEL_INSTALL_SCRIPT.is_file())

        spec = importlib.util.spec_from_file_location(
            "test_wheel_install",
            TEST_WHEEL_INSTALL_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with mock.patch.dict(
            module.os.environ,
            {
                "PYTHONPATH": str(PROJECT_ROOT / "build" / "python"),
                "CONDA_PREFIX": str(PROJECT_ROOT / "fake-conda"),
            },
            clear=True,
        ):
            env = module._unit_test_environment()

        self.assertEqual(
            env["PYTHONPATH"],
            str(PROJECT_ROOT / "tests" / "unitTest"),
        )
        self.assertNotIn("CONDA_PREFIX", env)

    def test_clean_wheel_test_support_has_no_numpy_runtime_import(self):
        self.assertTrue(UNIT_TEST_SUPPORT.is_file())

        support = UNIT_TEST_SUPPORT.read_text(encoding="utf-8")
        self.assertNotIn("import numpy", support)

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
        self.assertIn('$DistributionName.Replace("-", "_")', script)
        self.assertIn('$RuntimeDistribution.Replace("-", "_")', script)
        self.assertIn("$PythonTag-win_amd64.whl", script)
        self.assertIn("$IsisDataVersion-py3-none-any.whl", script)
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
