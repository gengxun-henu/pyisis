"""Unit tests for the Windows ISIS application smoke-test script.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-08-15
Updated: 2026-06-18  Geng Xun added guard coverage for the Windows ISIS app smoke-test harness.
Updated: 2026-08-02  Geng Xun added csv2table manifest and behavior-smoke coverage.
Updated: 2026-08-15  Geng Xun added installed-XML coverage for version-specific APP parameters.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = PROJECT_ROOT / "ports" / "windows" / "isis" / "test_isis_apps_smoke.ps1"
BATCH_SMOKE_SCRIPT = (
    PROJECT_ROOT / "ports" / "windows" / "isis" / "test_isis_app_batch_smoke.ps1"
)
MANIFEST_PATH = (
    PROJECT_ROOT / "ports" / "windows" / "isis" / "windows-app-manifest.json"
)


class WindowsIsisAppSmokeScriptUnitTest(unittest.TestCase):
    def test_installed_app_xml_controls_optional_parameter_support(self):
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            self.skipTest("PowerShell is unavailable.")

        common_script = PROJECT_ROOT / "ports" / "windows" / "isis" / "common.ps1"
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            xml_dir = prefix / "bin" / "xml"
            xml_dir.mkdir(parents=True)
            crop_xml = xml_dir / "crop.xml"

            for parameter_names, expected in (
                (("FROM", "TO", "NSAMPLES"), "False"),
                (("FROM", "TO", "NSAMPLES", "OVERHANG"), "True"),
            ):
                parameters = "".join(
                    f'<parameter name="{name}" />' for name in parameter_names
                )
                crop_xml.write_text(
                    f"<application><group>{parameters}</group></application>",
                    encoding="utf-8",
                )
                command = (
                    f'. "{common_script}"; '
                    f'Test-IsisAppParameter -Prefix "{prefix}" '
                    '-AppName crop -ParameterName overhang'
                )
                completed = subprocess.run(
                    [
                        powershell,
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        command,
                    ],
                    cwd=str(PROJECT_ROOT),
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout.strip(), expected)

    def test_csv2table_is_allowlisted_and_behavior_smoked(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        apps = {item["name"]: item for item in manifest["apps"]}
        self.assertIn("csv2table", apps)

        script_text = BATCH_SMOKE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('Invoke-IsisApp "csv2table"', script_text)
        self.assertIn('Invoke-IsisApp "tabledump"', script_text)

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
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SMOKE_SCRIPT),
                "-ListCommands",
            ],
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
