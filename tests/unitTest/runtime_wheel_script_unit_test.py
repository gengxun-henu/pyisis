"""Unit tests for Windows runtime wheel staging.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added runtime wheel staging coverage.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


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


if __name__ == "__main__":
    unittest.main()
