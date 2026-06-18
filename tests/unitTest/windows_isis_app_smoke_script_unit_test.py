"""Unit tests for the Windows ISIS application smoke-test script.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added guard coverage for the Windows ISIS app smoke-test harness.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = PROJECT_ROOT / "ports" / "windows" / "isis" / "test_isis_apps_smoke.ps1"


class WindowsIsisAppSmokeScriptUnitTest(unittest.TestCase):
    def test_script_exists_and_documents_core_commands(self):
        self.assertTrue(SMOKE_SCRIPT.exists(), f"missing Windows ISIS app smoke script: {SMOKE_SCRIPT}")

        script_text = SMOKE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("verify_isis_prefix.ps1", script_text)
        self.assertIn('Join-Path $env:CONDA_PREFIX "bin"', script_text)
        for command in (
            "stats",
            "getkey",
            "catlab",
            "campt",
            "reduce",
            "cam2map",
            "isis2std",
            "cubeit",
            "fx",
        ):
            with self.subTest(command=command):
                self.assertIn(command, script_text)

    def test_list_commands_mode_reports_required_and_optional_commands(self):
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            self.skipTest("PowerShell is unavailable.")
        if not SMOKE_SCRIPT.exists():
            self.fail(f"missing Windows ISIS app smoke script: {SMOKE_SCRIPT}")

        completed = subprocess.run(
            [powershell, "-NoProfile", "-File", str(SMOKE_SCRIPT), "-ListCommands"],
            cwd=str(PROJECT_ROOT),
            check=True,
            text=True,
            capture_output=True,
        )

        command_lines = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
        self.assertGreaterEqual(
            command_lines,
            {
                "stats",
                "getkey",
                "catlab",
                "campt",
                "reduce",
                "cam2map",
                "isis2std",
                "cubeit",
                "fx",
                "lronac2isis",
                "spiceinit",
                "lronaccal",
                "lronacecho",
            },
        )


if __name__ == "__main__":
    unittest.main()
