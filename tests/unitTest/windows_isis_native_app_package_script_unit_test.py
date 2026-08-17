"""Contract tests for the Windows ISIS native-APP package scripts.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added runtime-matrix and guarded-orchestration coverage.
"""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SCRIPT = REPOSITORY_ROOT / "ports/windows/isis/test_isis_native_app_package.ps1"
BUILD_SCRIPT = REPOSITORY_ROOT / "tools/packaging/build_windows_native_apps.ps1"


class WindowsIsisNativeAppPackageScriptUnitTest(unittest.TestCase):
    def test_runtime_matrix_contains_all_required_gates(self):
        script = RUNTIME_SCRIPT.read_text(encoding="utf-8")
        for token in (
            "CONDA_PREFIX",
            "ISISROOT",
            "ISIS_PREFIX",
            "ISISDATA",
            "QT_PLUGIN_PATH",
            "reduce",
            "jigsaw",
            "qnet",
            "stats",
            "getkey",
            "catlab",
            "campt",
            "cam2map",
            "isis2std",
            "cubeit",
            "fx",
            "MainWindowTitle",
        ):
            self.assertIn(token, script)
        self.assertIn("passed = 150", script)
        self.assertIn("skipped = 0", script)

    def test_runtime_report_uses_the_closed_canonical_schema(self):
        script = RUNTIME_SCRIPT.read_text(encoding="utf-8")
        for token in (
            '"archive-extract"',
            '"cli-help"',
            '"real-operations"',
            '"gui-launch"',
            '"external-isisdata"',
            '"negative-launcher"',
            '"Windows 11"',
            '"native package with spaces"',
            "archive_sha256",
            "path_entries_removed",
            "passed = 166",
            "exit_codes = @(4, 3)",
        ):
            self.assertIn(token, script)
        self.assertIn("ConvertTo-Json -Depth", script)
        self.assertIn("[System.IO.File]::Move", script)
        self.assertIn("$global:LASTEXITCODE = 0", script)
        self.assertIn('"validation-data\\EN0108828322M_iof.cub"', script)
        self.assertIn('"validation-data\\equi.map"', script)
        self.assertIn("validation camera cube is missing", script)
        self.assertIn("validation map file is missing", script)

    def test_runtime_rejects_forbidden_paths_and_scrubs_child_environment(self):
        script = RUNTIME_SCRIPT.read_text(encoding="utf-8")
        self.assertRegex(script, r"Test-Path\s+-LiteralPath\s+\$path")
        self.assertIn("Remove-Item Env:\\CONDA_PREFIX", script)
        self.assertIn("Remove-Item Env:\\ISISROOT", script)
        self.assertIn("Remove-Item Env:\\ISIS_PREFIX", script)
        self.assertIn("Remove-Item Env:\\ISISDATA", script)
        self.assertIn("Remove-Item Env:\\QT_PLUGIN_PATH", script)
        self.assertIn("pathEntriesRemoved", script)

    def test_orchestrator_guards_recursive_cleanup(self):
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Resolve-FullPath $WorkDir", script)
        self.assertIn("Assert-PathWithin", script)
        self.assertNotRegex(script, r"Remove-Item\s+[^\r\n]*-[Rr]ecurse[^\r\n]*\*")
        self.assertIn("Remove-Item -LiteralPath $resolvedWorkDir -Recurse -Force", script)

    def test_orchestrator_runs_the_pipeline_and_preserves_failure_diagnostics(self):
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        expected_order = (
            "stage_windows_native_apps.py",
            "archive_windows_native_apps.py",
            "test_isis_native_app_package.ps1",
            "validate_windows_native_apps.py",
        )
        offsets = [script.index(item) for item in expected_order]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("$completed = $true", script)
        self.assertIn("output directory must remain outside work directory", script)
        self.assertIn("report directory must remain outside work directory", script)
        self.assertRegex(
            script,
            re.compile(r"if \(\$completed\)[\s\S]*Remove-Item -LiteralPath \$resolvedWorkDir"),
        )

    def test_powershell_scripts_parse(self):
        shell = "powershell.exe"
        for script_path in (RUNTIME_SCRIPT, BUILD_SCRIPT):
            command = (
                "$errors = $null; "
                f"[void][System.Management.Automation.Language.Parser]::ParseFile('{script_path}', "
                "[ref]$null, [ref]$errors); "
                "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_runtime_fixture_rejects_an_existing_forbidden_path_without_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive = root / "fixture.zip"
            release = root / "release.json"
            absent_forbidden = root / "absent-prefix"
            forbidden = root / "forbidden-prefix"
            report = root / "runtime.json"
            archive.write_bytes(b"not needed before the forbidden-host gate")
            release.write_text("{}\n", encoding="utf-8")
            forbidden.mkdir()
            report.write_text('{"stale": true}\n', encoding="utf-8")
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(RUNTIME_SCRIPT),
                    "-Archive",
                    str(archive),
                    "-ReleaseConfig",
                    str(release),
                    "-WorkDir",
                    str(root / "work"),
                    "-Report",
                    str(report),
                    "-ForbiddenPath",
                    str(absent_forbidden),
                    "-ForbiddenPath",
                    str(forbidden),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forbidden path exists", completed.stderr)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
