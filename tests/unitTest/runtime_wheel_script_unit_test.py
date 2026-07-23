"""Unit tests for platform runtime wheel staging.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-07-23
Updated: 2026-06-18  Geng Xun added runtime wheel staging coverage.
Updated: 2026-06-19  Geng Xun added Linux runtime wheel staging coverage.
Updated: 2026-07-22  Geng Xun covered Linux SONAME aliases and closure verification.
Updated: 2026-07-23  Geng Xun limited Linux runtime staging to ISIS-owned binding files.
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
LINUX_STAGING_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "stage_runtime_linux.py"


class RuntimeWheelScriptUnitTest(unittest.TestCase):
    """Test suite for runtime wheel staging. Added: 2026-06-18."""

    def test_stage_runtime_copies_runtime_files_and_excludes_sdk_files(self):
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
            self.assertTrue((vendor / "bin" / "isis.exe").is_file())
            self.assertTrue((vendor / "bin" / "Qt5Core.dll").is_file())
            self.assertTrue((vendor / "bin" / "xml" / "stats.xml").is_file())
            self.assertTrue((vendor / "lib" / "Camera.plugin").is_file())
            self.assertTrue((vendor / "Library" / "bin" / "zlib.dll").is_file())
            self.assertTrue(
                (vendor / "Library" / "plugins" / "platforms" / "qwindows.dll").is_file()
            )
            self.assertFalse((vendor / "lib" / "isis.lib").exists())
            self.assertFalse((vendor / "include" / "isis" / "Cube.h").exists())
            self.assertFalse((vendor / "Library" / "lib" / "zlib.lib").exists())
            self.assertFalse((vendor / "Library" / "include" / "zlib.h").exists())

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
            with mock.patch.object(stage_module, "_dumpbin_dependencies", fake_dumpbin):
                stage_module.stage_runtime(
                    prefix,
                    stage,
                    (dep_prefix,),
                    dependency_copy_mode="closure",
                )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "Library" / "bin" / "needed.dll").is_file())
            self.assertTrue((vendor / "bin" / "cspice.dll").is_file())
            self.assertFalse((vendor / "Library" / "bin" / "unused.dll").exists())

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
