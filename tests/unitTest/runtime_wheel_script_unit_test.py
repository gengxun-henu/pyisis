"""Unit tests for platform runtime wheel staging.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-08-18
Updated: 2026-06-18  Geng Xun added runtime wheel staging coverage.
Updated: 2026-06-19  Geng Xun added Linux runtime wheel staging coverage.
Updated: 2026-07-22  Geng Xun covered Linux SONAME aliases and closure verification.
Updated: 2026-07-23  Geng Xun limited Linux runtime staging to ISIS-owned binding files.
Updated: 2026-07-23  Geng Xun covered versioned ISIS 10 runtime distribution metadata.
Updated: 2026-07-23  Geng Xun covered versioned ISIS 10 Windows runtime metadata.
Updated: 2026-07-24  Geng Xun preserved declared ELF SONAME aliases in Linux dependency closures.
Updated: 2026-07-25  Geng Xun aligned runtime staging fixtures with the ISIS 10 rc2 identity.
Updated: 2026-08-05  Geng Xun added Windows PE export-forwarder closure regression coverage.
Updated: 2026-08-05  Geng Xun required fail-closed Windows DLL audit reports.
Updated: 2026-08-05  Geng Xun enforced the Windows minimal-runtime boundary against APP executables and XML.
Updated: 2026-08-16  Geng Xun covered tolerant UTF-8 decoding of Windows dumpbin output.
Updated: 2026-08-18  Geng Xun covered shared Windows PE closure provenance.
Updated: 2026-08-18  Geng Xun made PE closure evidence order and case deterministic.
Updated: 2026-08-18  Geng Xun classified the Qt WTS dependency as a Windows system DLL.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WINDOWS_STAGING_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "stage_runtime_win64.py"
WINDOWS_PE_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "windows_pe_dependencies.py"
LINUX_STAGING_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "stage_runtime_linux.py"


class RuntimeWheelScriptUnitTest(unittest.TestCase):
    """Test suite for runtime wheel staging. Added: 2026-06-18."""

    def _load_module(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_shared_pe_closure_records_forwarder_provenance(self):
        module = self._load_module("windows_pe_dependencies", WINDOWS_PE_SCRIPT)
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prefix = root / "deps"
            target = root / "stage"
            seed = root / "reduce.exe"
            (prefix / "bin").mkdir(parents=True)
            target.mkdir()
            seed.write_bytes(b"exe")
            (prefix / "bin" / "isis.dll").write_bytes(b"isis")
            (prefix / "bin" / "openblas.dll").write_bytes(b"blas")
            direct = {"reduce.exe": ("isis.dll",), "isis.dll": ()}
            forwarded = {"reduce.exe": ("openblas.dll",), "openblas.dll": ()}
            with (
                mock.patch.object(
                    module,
                    "dumpbin_dependencies",
                    side_effect=lambda path: direct.get(path.name, ()),
                ),
                mock.patch.object(
                    module,
                    "dumpbin_forwarded_dependencies",
                    side_effect=lambda path: forwarded.get(path.name, ()),
                ),
            ):
                report = module.copy_dependency_closure(
                    (seed,),
                    (prefix,),
                    target,
                )
            self.assertEqual(report["unresolved"], [])
            openblas = next(
                item for item in report["files"] if item["name"] == "openblas.dll"
            )
            self.assertEqual(openblas["import_kind"], "forwarder")
            self.assertEqual(openblas["parents"], ["reduce.exe"])

    def test_shared_pe_closure_is_seed_order_and_case_deterministic(self):
        module = self._load_module(
            "windows_pe_dependencies_determinism",
            WINDOWS_PE_SCRIPT,
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prefix = root / "deps"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "bin" / "Isis.DLL").write_bytes(b"isis")
            upper_seed = root / "A.exe"
            lower_seed = root / "b.exe"
            upper_seed.write_bytes(b"upper")
            lower_seed.write_bytes(b"lower")
            direct = {"A.exe": ("ISIS.dll",)}
            forwarded = {"b.exe": ("isis.DLL",)}

            def build_report(seed_files, target_name):
                target = root / target_name
                target.mkdir()
                with (
                    mock.patch.object(
                        module,
                        "dumpbin_dependencies",
                        side_effect=lambda path: direct.get(path.name, ()),
                    ),
                    mock.patch.object(
                        module,
                        "dumpbin_forwarded_dependencies",
                        side_effect=lambda path: forwarded.get(path.name, ()),
                    ),
                ):
                    return module.copy_dependency_closure(
                        seed_files,
                        (prefix,),
                        target,
                    )

            forward = build_report((upper_seed, lower_seed), "forward")
            reverse = build_report((lower_seed, upper_seed), "reverse")

            self.assertEqual(forward, reverse)
            dependency = self.assert_single_dependency_file(forward)
            self.assertEqual(dependency["name"], "isis.dll")
            self.assertEqual(dependency["import_kind"], "direct")
            self.assertEqual(dependency["parents"], ["A.exe", "b.exe"])
            classifications = {
                binary["binary"]: binary["imports"][0]["classification"]
                for binary in forward["binaries"]
                if binary["imports"]
            }
            self.assertEqual(
                classifications,
                {"A.exe": "resolved", "b.exe": "packaged"},
            )

    def test_shared_pe_closure_classifies_wtsapi32_as_system(self):
        module = self._load_module(
            "windows_pe_dependencies_wtsapi32",
            WINDOWS_PE_SCRIPT,
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prefix = root / "deps"
            target = root / "stage"
            seed = root / "qwindows.dll"
            prefix.mkdir()
            target.mkdir()
            seed.write_bytes(b"qt-platform")
            with (
                mock.patch.object(
                    module,
                    "dumpbin_dependencies",
                    side_effect=lambda path: (
                        ("wtsapi32.dll",) if path.name == "qwindows.dll" else ()
                    ),
                ),
                mock.patch.object(
                    module,
                    "dumpbin_forwarded_dependencies",
                    return_value=(),
                ),
            ):
                report = module.copy_dependency_closure(
                    (seed,),
                    (prefix,),
                    target,
                )

            self.assertEqual(report["unresolved"], [])
            self.assertEqual(report["files"], [])
            self.assertEqual(
                report["binaries"][0]["imports"],
                [
                    {
                        "name": "wtsapi32.dll",
                        "import_kind": "direct",
                        "classification": "system",
                    }
                ],
            )

    def assert_single_dependency_file(self, report):
        self.assertEqual(len(report["files"]), 1)
        return report["files"][0]

    def test_stage_runtime_preserves_shared_pe_compatibility_aliases(self):
        stage_module = self._load_module(
            "stage_runtime_win64_compatibility_aliases",
            WINDOWS_STAGING_SCRIPT,
        )
        self.assertIs(
            stage_module._copy_dependency_closure,
            stage_module._pe_dependencies.copy_dependency_closure,
        )
        self.assertIs(
            stage_module._dumpbin_dependencies,
            stage_module._pe_dependencies.dumpbin_dependencies,
        )
        self.assertIs(
            stage_module._dumpbin_forwarded_dependencies,
            stage_module._pe_dependencies.dumpbin_forwarded_dependencies,
        )

    def test_stage_runtime_direct_script_loads_shared_pe_sibling(self):
        with TemporaryDirectory() as temp_dir:
            environment = dict(os.environ)
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, str(WINDOWS_STAGING_SCRIPT), "--help"],
                cwd=temp_dir,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dependency-copy-mode", result.stdout)

    def test_dumpbin_forwarded_dependencies_extracts_unique_non_system_dlls(self):
        pe_module = self._load_module(
            "windows_pe_dependencies_forwarder_parser",
            WINDOWS_PE_SCRIPT,
        )

        completed = subprocess.CompletedProcess(
            ["dumpbin", "/EXPORTS", "libcblas.dll"],
            0,
            stdout=(
                "3 2 00000000 cblas_caxpy = openblas.dll.cblas_caxpy\n"
                "4 3 00000000 cblas_ccopy = openblas.dll.cblas_ccopy\n"
                "5 4 00000000 forwarded = KERNEL32.dll.Sleep\n"
            ),
            stderr="",
        )
        with mock.patch.object(
            pe_module.subprocess,
            "run",
            return_value=completed,
        ):
            result = pe_module.dumpbin_forwarded_dependencies(Path("libcblas.dll"))

        self.assertEqual(result, ("openblas.dll", "KERNEL32.dll"))

    def test_dumpbin_dependencies_uses_tolerant_utf8_decoding(self):
        pe_module = self._load_module(
            "windows_pe_dependencies_dependency_decoding",
            WINDOWS_PE_SCRIPT,
        )

        def fake_run(command, **kwargs):
            self.assertEqual(command[1], "/DEPENDENTS")
            self.assertTrue(kwargs.get("text"))
            self.assertEqual(kwargs.get("encoding"), "utf-8")
            self.assertEqual(kwargs.get("errors"), "replace")
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="\ufffd diagnostic text\nale.dll\n",
                stderr="",
            )

        with mock.patch.object(pe_module.subprocess, "run", side_effect=fake_run):
            result = pe_module.dumpbin_dependencies(Path("isis.dll"))

        self.assertEqual(result, ("ale.dll",))

    def test_dumpbin_forwarded_dependencies_uses_tolerant_utf8_decoding(self):
        pe_module = self._load_module(
            "windows_pe_dependencies_forwarder_decoding",
            WINDOWS_PE_SCRIPT,
        )

        def fake_run(command, **kwargs):
            self.assertEqual(command[1], "/EXPORTS")
            self.assertTrue(kwargs.get("text"))
            self.assertEqual(kwargs.get("encoding"), "utf-8")
            self.assertEqual(kwargs.get("errors"), "replace")
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="\ufffd diagnostic text\nforwarded = openblas.dll.cblas_saxpy\n",
                stderr="",
            )

        with mock.patch.object(pe_module.subprocess, "run", side_effect=fake_run):
            result = pe_module.dumpbin_forwarded_dependencies(Path("libcblas.dll"))

        self.assertEqual(result, ("openblas.dll",))

    def test_dumpbin_dependency_failure_is_fatal(self):
        pe_module = self._load_module(
            "windows_pe_dependencies_dumpbin_failure",
            WINDOWS_PE_SCRIPT,
        )

        completed = subprocess.CompletedProcess(
            ["dumpbin", "/DEPENDENTS", "isis.dll"],
            1,
            stdout="",
            stderr="fatal error LNK1107",
        )
        with mock.patch.object(
            pe_module.subprocess,
            "run",
            return_value=completed,
        ):
            with self.assertRaisesRegex(RuntimeError, "dumpbin failed.*isis.dll"):
                pe_module.dumpbin_dependencies(Path("isis.dll"))

    def test_stage_runtime_copies_binding_runtime_and_excludes_apps_and_sdk_files(self):
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin" / "xml").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "include" / "isis").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text("Group = DataDirectory", encoding="utf-8")
            (prefix / "isis_version.txt").write_text("9.0.0", encoding="utf-8")
            (prefix / "LICENSE.md").write_text("MIT", encoding="utf-8")
            (prefix / "bin" / "isis.dll").write_bytes(b"dll")
            (prefix / "bin" / "isis.exe").write_bytes(b"exe")
            (prefix / "bin" / "reduce.exe").write_bytes(b"app")
            (prefix / "bin" / "Qt5Core.dll").write_bytes(b"qt")
            (prefix / "bin" / "xml" / "stats.xml").write_text(
                "<application />",
                encoding="utf-8",
            )
            (prefix / "lib" / "Camera.plugin").write_text("Plugin", encoding="utf-8")
            (prefix / "lib" / "isis.lib").write_bytes(b"import library")
            (prefix / "include" / "isis" / "Cube.h").write_text(
                "// header",
                encoding="utf-8",
            )

            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "Library" / "bin").mkdir(parents=True)
            (dep_prefix / "Library" / "plugins" / "platforms").mkdir(parents=True)
            (dep_prefix / "Library" / "include").mkdir(parents=True)
            (dep_prefix / "Library" / "bin" / "zlib.dll").write_bytes(b"zlib")
            (dep_prefix / "Library" / "bin" / "qt-tool.exe").write_bytes(b"tool")
            (dep_prefix / "Library" / "plugins" / "platforms" / "qwindows.dll").write_bytes(
                b"qt-platform"
            )
            (dep_prefix / "Library" / "lib" / "zlib.lib").parent.mkdir(parents=True)
            (dep_prefix / "Library" / "lib" / "zlib.lib").write_bytes(b"import library")
            (dep_prefix / "Library" / "include" / "zlib.h").write_text(
                "// header",
                encoding="utf-8",
            )

            stage = temp / "runtime-stage"
            subprocess.run(
                [
                    sys.executable,
                    str(WINDOWS_STAGING_SCRIPT),
                    "--isis-prefix",
                    str(prefix),
                    "--dependency-prefix",
                    str(dep_prefix),
                    "--dependency-copy-mode",
                    "pattern",
                    "--distribution-name",
                    "usgs-pyisis-runtime-isis10-win64",
                    "--package-version",
                    "1.4.0rc2",
                    "--stage-dir",
                    str(stage),
                ],
                check=True,
                cwd=PROJECT_ROOT,
            )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "IsisPreferences").is_file())
            self.assertTrue((vendor / "isis_version.txt").is_file())
            self.assertTrue((vendor / "LICENSE.md").is_file())
            self.assertTrue((vendor / "bin" / "isis.dll").is_file())
            self.assertTrue((vendor / "bin" / "Qt5Core.dll").is_file())
            self.assertTrue((vendor / "lib" / "Camera.plugin").is_file())
            self.assertTrue((vendor / "Library" / "bin" / "zlib.dll").is_file())
            self.assertTrue(
                (vendor / "Library" / "plugins" / "platforms" / "qwindows.dll").is_file()
            )
            self.assertFalse((vendor / "bin" / "isis.exe").exists())
            self.assertFalse((vendor / "bin" / "reduce.exe").exists())
            self.assertFalse((vendor / "bin" / "xml" / "stats.xml").exists())
            self.assertFalse((vendor / "Library" / "bin" / "qt-tool.exe").exists())
            self.assertEqual(list(vendor.rglob("*.exe")), [])
            self.assertFalse((vendor / "lib" / "isis.lib").exists())
            self.assertFalse((vendor / "include" / "isis" / "Cube.h").exists())
            self.assertFalse((vendor / "Library" / "lib" / "zlib.lib").exists())
            self.assertFalse((vendor / "Library" / "include" / "zlib.h").exists())
            runtime_pyproject = (stage / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn(
                'name = "usgs-pyisis-runtime-isis10-win64"',
                runtime_pyproject,
            )
            self.assertIn('version = "1.4.0rc2"', runtime_pyproject)

            sys.path.insert(0, str(stage / "src"))
            sys.modules.pop("pyisis_runtime", None)
            try:
                runtime = importlib.import_module("pyisis_runtime")
                self.assertEqual(runtime.prefix(), vendor)
                self.assertIn(vendor / "Library" / "bin", runtime.dll_directories())
                self.assertIn(vendor / "bin", runtime.dll_directories())
                self.assertIn(vendor / "lib", runtime.dll_directories())
            finally:
                sys.modules.pop("pyisis_runtime", None)
                sys.path.remove(str(stage / "src"))

    def test_stage_runtime_closure_copies_only_resolved_dependency_dlls(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_win64",
            WINDOWS_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text("Group = DataDirectory", encoding="utf-8")
            (prefix / "lib" / "isis.dll").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "Library" / "bin").mkdir(parents=True)
            (dep_prefix / "bin").mkdir(parents=True)
            (dep_prefix / "Library" / "bin" / "needed.dll").write_bytes(b"needed")
            (dep_prefix / "Library" / "bin" / "unused.dll").write_bytes(b"unused")
            (dep_prefix / "bin" / "cspice.dll").write_bytes(b"cspice")

            def fake_dumpbin(binary):
                if binary.name == "isis.dll":
                    return ("needed.dll", "cspice.dll", "KERNEL32.dll")
                return ()

            stage = temp / "runtime-stage"
            report = temp / "dependency-report.json"
            with (
                mock.patch.object(
                    stage_module._pe_dependencies,
                    "dumpbin_dependencies",
                    fake_dumpbin,
                ),
                mock.patch.object(
                    stage_module._pe_dependencies,
                    "dumpbin_forwarded_dependencies",
                    return_value=(),
                ),
            ):
                stage_module.stage_runtime(
                    prefix,
                    stage,
                    (dep_prefix,),
                    dependency_copy_mode="closure",
                    dependency_report=report,
                )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "Library" / "bin" / "needed.dll").is_file())
            self.assertTrue((vendor / "bin" / "cspice.dll").is_file())
            self.assertFalse((vendor / "Library" / "bin" / "unused.dll").exists())
            audit = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(audit["schema_version"], 1)
            self.assertEqual(audit["unresolved"], [])
            isis_imports = next(
                item["imports"]
                for item in audit["binaries"]
                if item["binary"] == "isis.dll"
            )
            classifications = {item["name"]: item["classification"] for item in isis_imports}
            self.assertEqual(classifications["needed.dll"], "resolved")
            self.assertEqual(classifications["cspice.dll"], "resolved")
            self.assertEqual(classifications["kernel32.dll"], "system")

    def test_stage_runtime_closure_reports_unresolved_dependency(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_win64_unresolved",
            WINDOWS_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text(
                "Group = DataDirectory",
                encoding="utf-8",
            )
            (prefix / "bin" / "isis.dll").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")
            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "Library" / "bin").mkdir(parents=True)
            stage = temp / "runtime-stage"
            report = temp / "dependency-report.json"

            def fake_dumpbin(binary):
                return ("missing.dll",) if binary.name == "isis.dll" else ()

            with (
                mock.patch.object(
                    stage_module._pe_dependencies,
                    "dumpbin_dependencies",
                    fake_dumpbin,
                ),
                mock.patch.object(
                    stage_module._pe_dependencies,
                    "dumpbin_forwarded_dependencies",
                    return_value=(),
                ),
            ):
                with self.assertRaisesRegex(FileNotFoundError, "missing.dll"):
                    stage_module.stage_runtime(
                        prefix,
                        stage,
                        (dep_prefix,),
                        dependency_copy_mode="closure",
                        dependency_report=report,
                    )

            audit = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(audit["unresolved"], ["missing.dll"])

    def test_stage_runtime_closure_copies_forwarded_dependencies_for_both_windows_runtimes(
        self,
    ):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_win64_forwarder_closure",
            WINDOWS_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text(
                "Group = DataDirectory",
                encoding="utf-8",
            )
            (prefix / "lib" / "isis.dll").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

            dep_prefix = temp / "dep-prefix"
            dep_bin = dep_prefix / "Library" / "bin"
            dep_bin.mkdir(parents=True)
            (dep_bin / "libcblas.dll").write_bytes(b"cblas-forwarder")
            (dep_bin / "openblas.dll").write_bytes(b"openblas")
            (dep_bin / "vcruntime140.dll").write_bytes(b"vcruntime")

            def fake_dependencies(binary):
                if binary.name == "isis.dll":
                    return ("libcblas.dll",)
                if binary.name == "openblas.dll":
                    return ("vcruntime140.dll",)
                return ()

            def fake_forwarded_dependencies(binary):
                return ("openblas.dll",) if binary.name == "libcblas.dll" else ()

            releases = (
                ("usgs-pyisis-runtime-win64", "1.3.0rc2"),
                ("usgs-pyisis-runtime-isis10-win64", "1.4.0rc2"),
            )
            for distribution_name, package_version in releases:
                with self.subTest(distribution_name=distribution_name):
                    stage = temp / distribution_name
                    with (
                        mock.patch.object(
                            stage_module._pe_dependencies,
                            "dumpbin_dependencies",
                            fake_dependencies,
                        ),
                        mock.patch.object(
                            stage_module._pe_dependencies,
                            "dumpbin_forwarded_dependencies",
                            fake_forwarded_dependencies,
                        ),
                    ):
                        stage_module.stage_runtime(
                            prefix,
                            stage,
                            (dep_prefix,),
                            dependency_copy_mode="closure",
                            distribution_name=distribution_name,
                            package_version=package_version,
                        )

                    vendor_bin = (
                        stage
                        / "src"
                        / "pyisis_runtime"
                        / "vendor"
                        / "isis"
                        / "Library"
                        / "bin"
                    )
                    self.assertTrue((vendor_bin / "libcblas.dll").is_file())
                    self.assertTrue((vendor_bin / "openblas.dll").is_file())
                    self.assertTrue((vendor_bin / "vcruntime140.dll").is_file())

    def test_stage_linux_runtime_copies_shared_libraries_plugins_and_resources(self):
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin").mkdir(parents=True)
            (prefix / "appdata" / "templates").mkdir(parents=True)
            (prefix / "include" / "isis").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "share" / "isis" / "templates").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text("Group = DataDirectory", encoding="utf-8")
            (prefix / "isis_version.txt").write_text("9.0.0", encoding="utf-8")
            (prefix / "LICENSE.md").write_text("MIT", encoding="utf-8")
            (prefix / "bin" / "cam2map").write_bytes(b"app")
            (prefix / "appdata" / "templates" / "map.tpl").write_text(
                "template",
                encoding="utf-8",
            )
            (prefix / "lib" / "libisis.so").write_bytes(b"isis")
            (prefix / "lib" / "libisis.so.9").write_bytes(b"isis-soname")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")
            (prefix / "lib" / "libisis.a").write_bytes(b"static")
            (prefix / "include" / "isis" / "Cube.h").write_text("// header", encoding="utf-8")
            (prefix / "share" / "isis" / "templates" / "stats.xml").write_text(
                "<application />",
                encoding="utf-8",
            )

            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "lib").mkdir(parents=True)
            (dep_prefix / "plugins" / "platforms").mkdir(parents=True)
            (dep_prefix / "include").mkdir(parents=True)
            (dep_prefix / "lib" / "libQt5Core.so").write_bytes(b"qt")
            (dep_prefix / "lib" / "libQt5Core.so.5").write_bytes(b"qt-soname")
            (dep_prefix / "lib" / "libQt5Core.a").write_bytes(b"static")
            (dep_prefix / "plugins" / "platforms" / "libqxcb.so").write_bytes(b"qt-platform")
            (dep_prefix / "include" / "qt.h").write_text("// header", encoding="utf-8")

            stage = temp / "runtime-stage"
            subprocess.run(
                [
                    sys.executable,
                    str(LINUX_STAGING_SCRIPT),
                    "--isis-prefix",
                    str(prefix),
                    "--dependency-prefix",
                    str(dep_prefix),
                    "--dependency-copy-mode",
                    "pattern",
                    "--distribution-name",
                    "usgs-pyisis-runtime-isis10-linux-x86_64",
                    "--package-version",
                    "1.4.0rc2",
                    "--stage-dir",
                    str(stage),
                ],
                check=True,
                cwd=PROJECT_ROOT,
            )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "IsisPreferences").is_file())
            self.assertTrue((vendor / "isis_version.txt").is_file())
            self.assertTrue((vendor / "LICENSE.md").is_file())
            self.assertFalse((vendor / "bin").exists())
            self.assertTrue((vendor / "appdata" / "templates" / "map.tpl").is_file())
            self.assertTrue((vendor / "lib" / "libisis.so").is_file())
            self.assertTrue((vendor / "lib" / "libisis.so.9").is_file())
            self.assertTrue((vendor / "lib" / "Camera.plugin").is_file())
            self.assertTrue((vendor / "share" / "isis" / "templates" / "stats.xml").is_file())
            self.assertTrue((vendor / "lib" / "libQt5Core.so").is_file())
            self.assertTrue((vendor / "lib" / "libQt5Core.so.5").is_file())
            self.assertTrue((vendor / "plugins" / "platforms" / "libqxcb.so").is_file())
            self.assertFalse((vendor / "lib" / "libisis.a").exists())
            self.assertFalse((vendor / "include" / "isis" / "Cube.h").exists())
            self.assertFalse((vendor / "include" / "qt.h").exists())
            runtime_pyproject = (stage / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn(
                'name = "usgs-pyisis-runtime-isis10-linux-x86_64"',
                runtime_pyproject,
            )
            self.assertIn('version = "1.4.0rc2"', runtime_pyproject)

            sys.path.insert(0, str(stage / "src"))
            sys.modules.pop("pyisis_runtime", None)
            try:
                runtime = importlib.import_module("pyisis_runtime")
                self.assertEqual(runtime.prefix(), vendor)
                self.assertIn(vendor / "lib", runtime.dll_directories())
                self.assertNotIn(vendor / "bin", runtime.dll_directories())
                self.assertIn(vendor / "plugins", runtime.plugin_directories())
                with mock.patch.dict("os.environ", {}, clear=True):
                    runtime.configure_environment()
                    self.assertEqual(os.environ["ISIS_PREFIX"], str(vendor))
                    self.assertIn(str(vendor / "plugins"), os.environ["QT_PLUGIN_PATH"])
            finally:
                sys.modules.pop("pyisis_runtime", None)
                sys.path.remove(str(stage / "src"))

    def test_stage_linux_runtime_uses_conda_isis_manifest_as_allowlist(self):
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "conda-meta").mkdir(parents=True)
            (prefix / "appdata").mkdir()
            (prefix / "bin").mkdir()
            (prefix / "include").mkdir()
            (prefix / "lib").mkdir()
            (prefix / "IsisPreferences").write_text("preferences", encoding="utf-8")
            (prefix / "appdata" / "template.tpl").write_text("template", encoding="utf-8")
            (prefix / "bin" / "cam2map").write_bytes(b"application")
            (prefix / "include" / "Cube.h").write_text("header", encoding="utf-8")
            (prefix / "lib" / "Camera.plugin").write_text(
                "Group = Camera\n  Library = TestCamera\nEndGroup\n",
                encoding="utf-8",
            )
            (prefix / "lib" / "libisis.so").write_bytes(b"isis")
            (prefix / "lib" / "libTestCamera.so").write_bytes(b"camera")
            manifest_files = [
                "IsisPreferences",
                "appdata/template.tpl",
                "bin/cam2map",
                "include/Cube.h",
                "lib/Camera.plugin",
                "lib/libisis.so",
                "lib/libTestCamera.so",
            ]
            (prefix / "conda-meta" / "isis-9.0.0-test.json").write_text(
                json.dumps({"name": "isis", "files": manifest_files}),
                encoding="utf-8",
            )

            stage = temp / "runtime-stage"
            subprocess.run(
                [
                    sys.executable,
                    str(LINUX_STAGING_SCRIPT),
                    "--isis-prefix",
                    str(prefix),
                    "--dependency-copy-mode",
                    "closure",
                    "--stage-dir",
                    str(stage),
                ],
                check=True,
                cwd=PROJECT_ROOT,
            )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "appdata" / "template.tpl").is_file())
            self.assertTrue((vendor / "lib" / "libisis.so").is_file())
            self.assertTrue((vendor / "lib" / "libTestCamera.so").is_file())
            self.assertFalse((vendor / "bin").exists())
            self.assertFalse((vendor / "include").exists())

    def test_stage_linux_runtime_materializes_missing_soname_alias(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_linux",
            LINUX_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text("Group = DataDirectory", encoding="utf-8")
            (prefix / "lib" / "libisis.so").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "lib").mkdir(parents=True)
            versioned_library = dep_prefix / "lib" / "libcsmapi.so.3.0.3"
            versioned_library.write_bytes(b"csmapi")

            def fake_ldd_dependencies(binary):
                if binary.name == "libisis.so":
                    return ("libcsmapi.so.3",)
                return ()

            stage = temp / "runtime-stage"
            with mock.patch.object(
                stage_module,
                "_ldd_dependencies",
                fake_ldd_dependencies,
            ), mock.patch.object(
                stage_module,
                "_missing_runtime_dependencies",
                return_value=(),
            ):
                stage_module.stage_runtime(
                    prefix,
                    stage,
                    (dep_prefix,),
                    dependency_copy_mode="closure",
                )

            vendor_lib = stage / "src" / "pyisis_runtime" / "vendor" / "isis" / "lib"
            self.assertEqual((vendor_lib / "libcsmapi.so.3").read_bytes(), b"csmapi")
            self.assertFalse((vendor_lib / "libcsmapi.so.3").is_symlink())
            self.assertEqual((vendor_lib / "libcsmapi.so.3.0.3").read_bytes(), b"csmapi")

    def test_stage_linux_runtime_preserves_declared_elf_soname_alias(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_linux_soname",
            LINUX_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text(
                "Group = DataDirectory",
                encoding="utf-8",
            )
            (prefix / "lib" / "libisis.so").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

            dep_prefix = temp / "dep-prefix"
            (dep_prefix / "lib").mkdir(parents=True)
            (dep_prefix / "lib" / "libblas.so.3").write_bytes(b"openblas")

            def fake_ldd_dependencies(binary):
                if binary.name == "libisis.so":
                    return ("libblas.so.3",)
                return ()

            stage = temp / "runtime-stage"
            with mock.patch.object(
                stage_module,
                "_ldd_dependencies",
                fake_ldd_dependencies,
            ), mock.patch.object(
                stage_module,
                "_elf_soname",
                return_value="libopenblas.so.0",
            ), mock.patch.object(
                stage_module,
                "_missing_runtime_dependencies",
                return_value=(),
            ):
                stage_module.stage_runtime(
                    prefix,
                    stage,
                    (dep_prefix,),
                    dependency_copy_mode="closure",
                )

            vendor_lib = stage / "src" / "pyisis_runtime" / "vendor" / "isis" / "lib"
            self.assertEqual((vendor_lib / "libblas.so.3").read_bytes(), b"openblas")
            self.assertEqual(
                (vendor_lib / "libopenblas.so.0").read_bytes(),
                b"openblas",
            )

    def test_verify_linux_runtime_closure_reports_missing_dependencies(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_linux_verify",
            LINUX_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            vendor = Path(temp_dir)
            (vendor / "lib").mkdir(parents=True)
            (vendor / "lib" / "libisis.so").write_bytes(b"isis")
            with mock.patch.object(
                stage_module,
                "_missing_runtime_dependencies",
                return_value=("libcsmapi.so.3",),
            ):
                with self.assertRaisesRegex(FileNotFoundError, "libcsmapi.so.3"):
                    stage_module._verify_runtime_closure(vendor)

    def test_linux_runtime_closure_check_excludes_external_library_paths(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_linux_environment",
            LINUX_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            vendor = Path(temp_dir)
            (vendor / "lib").mkdir(parents=True)
            libisis = vendor / "lib" / "libisis.so"
            libisis.write_bytes(b"isis")
            completed = subprocess.CompletedProcess(
                ["ldd", str(libisis)],
                0,
                stdout="",
                stderr="",
            )
            with mock.patch.dict(
                stage_module.os.environ,
                {"LD_LIBRARY_PATH": "/external/conda/lib"},
            ), mock.patch.object(
                stage_module.subprocess,
                "run",
                return_value=completed,
            ) as run_mock:
                self.assertEqual(
                    stage_module._missing_runtime_dependencies(libisis, vendor),
                    (),
                )
            verification_env = run_mock.call_args.kwargs["env"]
            self.assertNotIn("/external/conda/lib", verification_env["LD_LIBRARY_PATH"])
            self.assertIn(str(vendor / "lib"), verification_env["LD_LIBRARY_PATH"])

    def test_stage_linux_runtime_enforces_size_budget(self):
        spec = importlib.util.spec_from_file_location(
            "stage_runtime_linux_size_budget",
            LINUX_STAGING_SCRIPT,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        stage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_module)

        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "lib").mkdir(parents=True)
            (prefix / "IsisPreferences").write_text("preferences", encoding="utf-8")
            (prefix / "lib" / "libisis.so").write_bytes(b"isis")
            (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

            with mock.patch.object(
                stage_module,
                "_missing_runtime_dependencies",
                return_value=(),
            ), self.assertRaisesRegex(ValueError, "exceeds its size budget"):
                stage_module.stage_runtime(
                    prefix,
                    temp / "runtime-stage",
                    max_runtime_bytes=1,
                )


if __name__ == "__main__":
    unittest.main()
