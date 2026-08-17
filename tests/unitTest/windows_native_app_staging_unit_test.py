"""Unit tests for portable Windows native APP launchers.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added package-relative launcher safety and execution coverage.
Updated: 2026-08-18  Geng Xun added unlimited argv and metacharacter regression coverage.
Updated: 2026-08-18  Geng Xun covered binder-shaped and empty APP arguments.
Updated: 2026-08-18  Geng Xun added JSON argv coverage for slot transport and native quoting.
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
PUBLIC_LAUNCHER_NAMES = (
    "isis-env.cmd",
    "isis-shell.cmd",
    "isis-app.cmd",
    "qnet.cmd",
)


@unittest.skipUnless(os.name == "nt", "Windows CMD launchers require Windows")
class WindowsNativeAppStagingTests(unittest.TestCase):
    """Exercise launchers from an extracted package path containing spaces."""

    @classmethod
    def setUpClass(cls):
        cls._probe_temp = TemporaryDirectory()
        probe_root = Path(cls._probe_temp.name)
        source = probe_root / "argv-probe.cs"
        source.write_text(
            r"""
using System;
using System.Text;

internal static class ArgvProbe {
    private static string JsonString(string value) {
        var output = new StringBuilder("\"");
        foreach (char item in value) {
            switch (item) {
                case '\\': output.Append("\\\\"); break;
                case '\"': output.Append("\\\""); break;
                case '\b': output.Append("\\b"); break;
                case '\f': output.Append("\\f"); break;
                case '\n': output.Append("\\n"); break;
                case '\r': output.Append("\\r"); break;
                case '\t': output.Append("\\t"); break;
                default:
                    if (item < 0x20) output.Append("\\u" + ((int)item).ToString("x4"));
                    else output.Append(item);
                    break;
            }
        }
        return output.Append('\"').ToString();
    }

    public static int Main(string[] arguments) {
        int exitCode;
        if (arguments.Length == 0 || !int.TryParse(arguments[0], out exitCode)) return 97;
        Console.Write("[");
        for (int index = 1; index < arguments.Length; index++) {
            if (index > 1) Console.Write(",");
            Console.Write(JsonString(arguments[index]));
        }
        Console.WriteLine("]");
        return exitCode;
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        framework64_compiler = (
            Path(os.environ["WINDIR"])
            / "Microsoft.NET"
            / "Framework64"
            / "v4.0.30319"
            / "csc.exe"
        )
        framework = "Framework64" if framework64_compiler.is_file() else "Framework"
        compiler = (
            Path(os.environ["WINDIR"])
            / "Microsoft.NET"
            / framework
            / "v4.0.30319"
            / "csc.exe"
        )
        cls._argv_probe = probe_root / "argv-probe.exe"
        subprocess.run(
            [str(compiler), "/nologo", f"/out:{cls._argv_probe}", str(source)],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls._probe_temp.cleanup()

    def _write_launcher_fixture(
        self, root: Path, package_name: str = "native package with spaces"
    ) -> Path:
        package = root / package_name
        for relative in ("bin", "data", "lib", "manifest", "plugins", "launch"):
            (package / relative).mkdir(parents=True, exist_ok=True)

        for name in PUBLIC_LAUNCHER_NAMES:
            shutil.copy2(LAUNCH_ROOT / name, package / "launch" / name)
        worker = LAUNCH_ROOT / "isis-launch.ps1"
        shutil.copy2(worker, package / "launch" / worker.name)

        (package / "manifest" / "apps.json").write_text(
            json.dumps({"public_apps": ["qnet", "reduce"]}) + "\n",
            encoding="utf-8",
        )
        shutil.copy2(self._argv_probe, package / "bin" / "reduce.exe")
        shutil.copy2(self._argv_probe, package / "bin" / "qnet.exe")
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
            command_values = (
                str(launcher),
                *(value.replace("%", "%%") for value in arguments),
            )
            command = " ".join(
                f'"{value.replace(chr(34), chr(34) * 2)}"'
                for value in command_values
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

    def _run_launcher_syntax(
        self,
        launcher: Path,
        argument_syntax: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as runner_dir:
            runner = Path(runner_dir) / "run.cmd"
            runner.write_text(
                "@echo off\n"
                f'"{launcher}" {argument_syntax}\n',
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

    def _probe_arguments(self, result: subprocess.CompletedProcess[str]) -> list[str]:
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_launchers_are_package_relative_without_machine_prefixes(self):
        for name in PUBLIC_LAUNCHER_NAMES:
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
                "23",
                "value with spaces",
            )

            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertEqual(self._probe_arguments(result), ["value with spaces"])

    def test_generic_launcher_preserves_more_than_seventeen_arguments_in_order(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            payload = [f"arg-{index}" for index in range(1, 19)]
            result = self._run_launcher(
                package / "launch" / "isis-app.cmd",
                "reduce",
                "0",
                *payload,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._probe_arguments(result), payload)

    def test_worker_does_not_bind_app_arguments_as_its_own_parameters(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            payload = [
                "-AppName",
                "literal",
                "-AppArguments",
                "value",
                "-Verbose",
                "-ErrorAction",
                "Stop",
                "",
                "tail",
            ]
            result = self._run_launcher(
                package / "launch" / "isis-app.cmd",
                "reduce",
                "0",
                *payload,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._probe_arguments(result), payload)

    def test_cmd_shims_preserve_final_literal_quote_argument(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            for launcher, prefix in (
                (package / "launch" / "isis-app.cmd", '"reduce" '),
                (package / "launch" / "qnet.cmd", ""),
            ):
                with self.subTest(launcher=launcher.name):
                    result = self._run_launcher_syntax(
                        launcher,
                        prefix + '"0" quote^"inside',
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        self._probe_arguments(result), ['quote"inside'], result.stderr
                    )

    def test_worker_splats_adversarial_environment_slots_exactly(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            payload = [
                "",
                'quote"inside',
                r"C:\path with spaces\leaf",
                "C:\\trailing\\",
                'backslash\\"quote',
                "tail",
                "%REVIEW_SECRET%",
                "amp&inside",
                "bang!inside",
                "caret^inside",
            ]
            slots = ["reduce", "0", *payload]
            environment = self._clean_environment()
            environment["ISIS_LAUNCH_ARG_COUNT"] = str(len(slots))
            for index, value in enumerate(slots):
                environment[f"ISIS_LAUNCH_ARG_{index}"] = value

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(package / "launch" / "isis-launch.ps1"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._probe_arguments(result), payload, result.stderr)

    def test_qnet_launcher_delegates_with_arguments_and_exit_code(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            result = self._run_launcher(
                package / "launch" / "qnet.cmd",
                "17",
                "QNET_OK",
            )

            self.assertEqual(result.returncode, 17, result.stderr)
            self.assertEqual(self._probe_arguments(result), ["QNET_OK"])

    def test_qnet_launcher_does_not_expand_literal_percent_argument_twice(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(Path(temp_dir))
            environment = self._clean_environment()
            environment["REVIEW_SECRET"] = "SECOND_EXPANSION"
            result = self._run_launcher(
                package / "launch" / "qnet.cmd",
                "0",
                "%REVIEW_SECRET%",
                environment=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self._probe_arguments(result), ["%REVIEW_SECRET%"])

    def test_invalid_data_metacharacters_are_not_executed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self._write_launcher_fixture(root)
            environment = self._clean_environment()
            environment["ISISDATA"] = str(root / "missing & echo ISISDATA_INJECTED")

            for launcher, arguments in (
                (package / "launch" / "isis-env.cmd", ()),
                (package / "launch" / "isis-app.cmd", ("reduce",)),
            ):
                with self.subTest(launcher=launcher.name):
                    result = self._run_launcher(
                        launcher, *arguments, environment=environment
                    )
                    self.assertEqual(result.returncode, 3)
                    self.assertNotIn("ISISDATA_INJECTED", result.stdout)
                    self.assertEqual(
                        result.stderr.strip(),
                        "Explicit ISISDATA directory does not exist.",
                    )

    def test_package_root_metacharacters_are_not_executed_on_manifest_error(self):
        with TemporaryDirectory() as temp_dir:
            package = self._write_launcher_fixture(
                Path(temp_dir), "review & echo PACKAGE_INJECTED & fixtures"
            )
            (package / "manifest" / "apps.json").unlink()

            result = self._run_launcher(
                package / "launch" / "isis-app.cmd", "reduce"
            )

            self.assertEqual(result.returncode, 5)
            self.assertNotIn("PACKAGE_INJECTED", result.stdout)
            self.assertEqual(result.stderr.strip(), "Unable to read ISIS APP manifest.")


if __name__ == "__main__":
    unittest.main()
