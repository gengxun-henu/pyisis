"""Unit tests for Windows runtime wheel staging.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added runtime wheel staging coverage.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "stage_runtime_win64.py"


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
                    str(STAGING_SCRIPT),
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
            STAGING_SCRIPT,
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


if __name__ == "__main__":
    unittest.main()
