"""Unit tests for portable Windows native APP launchers.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added package-relative launcher safety and execution coverage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_ROOT = REPOSITORY_ROOT / "packaging" / "native-apps-win64" / "launch"
LAUNCHER_NAMES = ("isis-env.cmd", "isis-shell.cmd", "isis-app.cmd", "qnet.cmd")


@unittest.skipUnless(os.name == "nt", "Windows CMD launchers require Windows")
class WindowsNativeAppStagingTests(unittest.TestCase):
    """Exercise launchers from an extracted package path containing spaces."""

    def _write_launcher_fixture(self, root: Path) -> Path:
        package = root / "native package with spaces"
        for relative in ("bin", "data", "lib", "manifest", "plugins", "launch"):
            (package / relative).mkdir(parents=True, exist_ok=True)

        for name in LAUNCHER_NAMES:
            shutil.copy2(LAUNCH_ROOT / name, package / "launch" / name)

        (package / "manifest" / "apps.json").write_text(
            json.dumps({"public_apps": ["qnet", "reduce"]}) + "\n",
            encoding="utf-8",
        )
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        shutil.copy2(powershell, package / "bin" / "reduce.exe")
        shutil.copy2(powershell, package / "bin" / "qnet.exe")
        (package / "bin" / "argument-probe.ps1").write_text(
            "param([string] $Value, [int] $Code)\n"
            "Write-Output \"ARG=[$Value]\"\n"
            "exit $Code\n",
            encoding="utf-8",
        )
        return package

    def _clean_environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        for name in (
            "ISISDATA",
            "ISISROOT",
            "ISIS_PREFIX",
            "ISIS_PACKAGE_ROOT",
            "ISIS_APP_MANIFEST",
            "QT_PLUGIN_PATH",
        ):
            environment.pop(name, None)
        return environment

    def _run_launcher(
        self, launcher: Path, *arguments: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as runner_dir:
            runner = Path(runner_dir) / "run.cmd"
            command = " ".join(
                f'"{value.replace(chr(34), chr(34) * 2)}"'
                for value in (str(launcher), *arguments)
            )
            runner.write_text(
                "@echo off\n" + command + "\n",
                encoding="utf-8",
            )
            return subprocess.run(
                ["cmd", "/d", "/c", str(runner)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment or self._clean_environment(),
            )

    def _write_environment_probe(self, root: Path, launcher: Path) -> Path:
        probe = root / "probe.cmd"
        probe.write_text(
            "@echo off\n"
            f'call "{launcher}"\n'
            "if errorlevel 1 exit /b %ERRORLEVEL%\n"
            "echo ROOT=[%ISISROOT%]\n"
            "echo PREFIX=[%ISIS_PREFIX%]\n"
            "echo DATA=[%ISISDATA%]\n"
            "echo QT=[%QT_PLUGIN_PATH%]\n"
            "echo PATH=[%PATH%]\n",
            encoding="utf-8",
        )
        return probe

    def test_launchers_are_package_relative_without_machine_prefixes(self):
        for name in LAUNCHER_NAMES:
            with self.subTest(name=name):
                path = LAUNCH_ROOT / name
                self.assertTrue(path.is_file(), f"missing launcher template: {path}")
                text = path.read_text(encoding="utf-8")
                self.assertIn("%~dp0", text)
                self.assertNotIn("CONDA_PREFIX", text.upper())
                self.assertNotRegex(
                    text, r"(?i)[A-Z]:\\(?:code|miniconda|pyisis-win-env)"
                )

    def test_environment_launcher_uses_bundled_data_and_runtime_paths(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            probe = self._write_environment_probe(
                Path(temp_dir), package / "launch" / "isis-env.cmd"
            )
            result = subprocess.run(
                ["cmd", "/d", "/c", str(probe)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._clean_environment(),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"ROOT=[{package}]", result.stdout)
            self.assertIn(f"PREFIX=[{package}]", result.stdout)
            self.assertIn(f"DATA=[{package / 'data'}]", result.stdout)
            self.assertIn(f"QT=[{package / 'plugins'}]", result.stdout)
            self.assertIn(
                f"PATH=[{package / 'bin'};{package / 'lib'};", result.stdout
            )

    def test_environment_launcher_preserves_valid_external_data(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self._write_launcher_fixture(root)
            external_data = root / "external ISIS data"
            external_data.mkdir()
            environment = self._clean_environment()
            environment["ISISDATA"] = str(external_data)

            probe = self._write_environment_probe(
                root, package / "launch" / "isis-env.cmd"
            )
            result = subprocess.run(
                ["cmd", "/d", "/c", str(probe)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"DATA=[{external_data}]", result.stdout)

    def test_environment_launcher_rejects_explicit_invalid_data(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self._write_launcher_fixture(root)
            environment = self._clean_environment()
            environment["ISISDATA"] = str(root / "missing ISIS data")

            result = self._run_launcher(
                package / "launch" / "isis-env.cmd", environment=environment
            )

            self.assertEqual(result.returncode, 3)
            self.assertIn("Explicit ISISDATA directory does not exist", result.stderr)

    def test_generic_launcher_rejects_missing_unknown_helper_and_malformed_names(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            launcher = package / "launch" / "isis-app.cmd"
            for arguments, expected_code in (
                ([], 2),
                (["unknown"], 4),
                (["isisui"], 4),
                (["reduce&echo-injected"], 4),
            ):
                with self.subTest(arguments=arguments):
                    result = self._run_launcher(launcher, *arguments)
                    self.assertEqual(result.returncode, expected_code, result.stderr)
                    self.assertIn("not a public ISIS APP", result.stderr)
                    self.assertNotIn("echo-injected", result.stdout)

    def test_generic_launcher_forwards_arguments_and_exit_code(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            launcher = package / "launch" / "isis-app.cmd"
            result = self._run_launcher(
                launcher,
                "reduce",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(package / "bin" / "argument-probe.ps1"),
                "value with spaces",
                "23",
            )

            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertIn("ARG=[value with spaces]", result.stdout)

    def test_qnet_launcher_delegates_with_arguments_and_exit_code(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            result = self._run_launcher(
                package / "launch" / "qnet.cmd",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(package / "bin" / "argument-probe.ps1"),
                "QNET_OK",
                "17",
            )

            self.assertEqual(result.returncode, 17, result.stderr)
            self.assertIn("ARG=[QNET_OK]", result.stdout)


if __name__ == "__main__":
    unittest.main()
