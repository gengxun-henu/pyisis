"""Contract tests for the Windows ISIS native-APP package scripts.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added runtime-matrix and guarded-orchestration coverage.
Updated: 2026-08-18  Geng Xun added repeated-prefix and descendant GUI-process fixtures.
Updated: 2026-08-18  Geng Xun covered bounded transient execution retries.
"""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid


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

    def test_runtime_retries_only_transient_access_denied_failures(self):
        script = RUNTIME_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$maximumAttempts = 4", script)
        self.assertIn('$exitCode -eq 5', script)
        self.assertIn('$tail.Trim() -ceq "Access is denied."', script)
        self.assertIn('$attempt -lt $maximumAttempts', script)
        self.assertIn('Start-Sleep -Seconds $attempt', script)
        self.assertIn('throw "package launcher exit mismatch', script)

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

    def test_orchestrator_accepts_repeated_dependency_prefixes_and_forwards_both(self):
        build_windows_root = REPOSITORY_ROOT / "build/windows"
        build_windows_root.mkdir(parents=True, exist_ok=True)
        sandbox = build_windows_root / f"task6 package & spaces-{uuid.uuid4().hex}"
        sandbox.mkdir()
        try:
            capture = sandbox / "stage-arguments.txt"
            fake_python = sandbox / "fake python.cmd"
            fake_python.write_text(
                '@echo off\r\necho %* > "%TASK6_ARGS_CAPTURE%"\r\nexit /b 91\r\n',
                encoding="utf-8",
            )
            isis_prefix = sandbox / "isis prefix"
            dependency_one = sandbox / "dependency one"
            dependency_two = sandbox / "dependency & two"
            minimal_data = sandbox / "minimal data"
            output_dir = sandbox / "output"
            report_dir = sandbox / "reports"
            work_dir = sandbox / "work"
            for directory in (
                isis_prefix,
                dependency_one,
                dependency_two,
                minimal_data,
            ):
                directory.mkdir()
            environment = dict(**__import__("os").environ)
            environment["TASK6_ARGS_CAPTURE"] = str(capture)
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(BUILD_SCRIPT),
                    "-PythonExecutable",
                    str(fake_python),
                    "-IsisPrefix",
                    str(isis_prefix),
                    "-DependencyPrefix",
                    str(dependency_one),
                    "-DependencyPrefix",
                    str(dependency_two),
                    "-MinimalDataRoot",
                    str(minimal_data),
                    "-OutputDir",
                    str(output_dir),
                    "-ReportDir",
                    str(report_dir),
                    "-WorkDir",
                    str(work_dir),
                ],
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertNotIn("specified more than once", completed.stderr)
            self.assertTrue(capture.is_file(), completed.stderr)
            arguments = capture.read_text(encoding="utf-8")
            self.assertEqual(arguments.count("--dependency-prefix"), 2)
            self.assertIn(str(dependency_one), arguments)
            self.assertIn(str(dependency_two), arguments)
        finally:
            shutil.rmtree(sandbox)

    def test_gui_probe_tracks_real_descendant_windows_and_cleans_every_target(self):
        compiler = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
        self.assertTrue(compiler.is_file(), "WinForms fixture compiler is required")
        with tempfile.TemporaryDirectory(prefix="native package & spaces-") as temporary_directory:
            root = Path(temporary_directory)
            source = root / "gui fixture.cs"
            source.write_text(
                "using System; using System.Windows.Forms; "
                "class Fixture { [STAThread] static void Main(string[] args) { "
                "Application.EnableVisualStyles(); var form = new Form(); "
                'form.Text = args.Length == 0 ? "fixture" : args[0]; '
                "Application.Run(form); } }\n",
                encoding="utf-8",
            )
            fixture_executable = root / "fixture.exe"
            compile_result = subprocess.run(
                [
                    str(compiler),
                    "/nologo",
                    "/target:winexe",
                    "/reference:System.Windows.Forms.dll",
                    f"/out:{fixture_executable}",
                    str(source),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            worker = root / "worker.ps1"
            worker.write_text(
                "param([string]$Target, [string]$Title)\n"
                "& $Target $Title\n"
                "exit $LASTEXITCODE\n",
                encoding="utf-8",
            )
            targets = []
            for name in ("reduce", "jigsaw", "qnet"):
                target = root / f"{name}.exe"
                shutil.copy2(fixture_executable, target)
                targets.append(target)
                (root / f"{name}.cmd").write_text(
                    "@echo off\r\n"
                    f'powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0worker.ps1" "%~dp0{name}.exe" "{name} fixture window"\r\n',
                    encoding="utf-8",
                )
            old_reduce = subprocess.Popen([str(targets[0]), "old reduce window"])
            try:
                time.sleep(0.5)
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
                        "-GuiProbeFixtureRoot",
                        str(root),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                diagnostics = completed.stderr + "\n" + "\n".join(
                    f"{path.name}: {path.read_text(encoding='utf-8', errors='replace')}"
                    for path in root.glob("*-std*.log")
                )
                self.assertEqual(completed.returncode, 0, diagnostics)
                self.assertIsNone(old_reduce.poll(), "pre-existing reduce process was killed")
                for target in targets:
                    query = subprocess.run(
                        [
                            "powershell.exe",
                            "-NoProfile",
                            "-Command",
                            f"@(Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -eq '{target}' }} | Select-Object -ExpandProperty ProcessId) -join ','",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    expected = str(old_reduce.pid) if target.name == "reduce.exe" else ""
                    self.assertEqual(query.stdout.strip(), expected, target.name)
                for name in ("reduce", "jigsaw", "qnet"):
                    self.assertTrue((root / f"{name}-stdout.log").is_file())
                    self.assertTrue((root / f"{name}-stderr.log").is_file())
            finally:
                if old_reduce.poll() is None:
                    old_reduce.terminate()
                    try:
                        old_reduce.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        old_reduce.kill()
                        old_reduce.wait(timeout=5)

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
