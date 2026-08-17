"""Unit tests for portable Windows native APP launchers.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added package-relative launcher safety and execution coverage.
Updated: 2026-08-18  Geng Xun added unlimited argv and metacharacter regression coverage.
Updated: 2026-08-18  Geng Xun covered binder-shaped and empty APP arguments.
Updated: 2026-08-18  Geng Xun added JSON argv coverage for slot transport and native quoting.
Updated: 2026-08-18  Geng Xun added curated staging and deterministic archive coverage.
Updated: 2026-08-18  Geng Xun hardened transactional publication and reparse-point coverage.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_ROOT = REPOSITORY_ROOT / "packaging" / "native-apps-win64" / "launch"
PUBLIC_LAUNCHER_NAMES = (
    "isis-env.cmd",
    "isis-shell.cmd",
    "isis-app.cmd",
    "qnet.cmd",
)
STAGE_SCRIPT = REPOSITORY_ROOT / "tools" / "packaging" / "stage_windows_native_apps.py"
ARCHIVE_SCRIPT = REPOSITORY_ROOT / "tools" / "packaging" / "archive_windows_native_apps.py"
MANIFEST_SCRIPT = REPOSITORY_ROOT / "tools" / "packaging" / "windows_native_app_manifest.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class WindowsNativeAppPayloadStagingTests(unittest.TestCase):
    """Exercise the curated payload boundary independently of a real ISIS build."""

    @classmethod
    def setUpClass(cls):
        cls.manifest_module = _load_module("native_app_manifest_fixture", MANIFEST_SCRIPT)
        cls.stage_module = _load_module("native_app_stage_fixture", STAGE_SCRIPT)
        cls.archive_module = _load_module("native_app_archive_fixture", ARCHIVE_SCRIPT)

    def _write_stage_fixture(self, root: Path) -> SimpleNamespace:
        isis_prefix = root / "isis-prefix"
        dependency_prefix = root / "dependency-prefix"
        minimal_data = root / "minimal-data"
        output = root / "output"
        dependency_report = root / "reports" / "dependencies.json"

        for relative in (
            "bin/xml",
            "lib",
            "appdata/templates/maps",
            "include",
        ):
            (isis_prefix / relative).mkdir(parents=True, exist_ok=True)
        for name in ("reduce", "qnet", "isisui", "unlisted"):
            (isis_prefix / "bin" / f"{name}.exe").write_bytes(name.encode("ascii"))
        (isis_prefix / "bin" / "xml" / "reduce.xml").write_text(
            "<application />\n", encoding="utf-8"
        )
        (isis_prefix / "lib" / "isis.dll").write_bytes(b"isis")
        (isis_prefix / "lib" / "Camera.plugin").write_text(
            "camera metadata\n", encoding="utf-8"
        )
        (isis_prefix / "appdata" / "templates" / "maps" / "map.tpl").write_text(
            "map\n", encoding="utf-8"
        )
        (isis_prefix / "include" / "private.h").write_text(
            "private\n", encoding="utf-8"
        )
        (isis_prefix / "IsisPreferences").write_text(
            "Group = DataDirectory\n", encoding="utf-8"
        )
        (isis_prefix / "LICENSE.md").write_text("license\n", encoding="utf-8")

        for relative in (
            "Library/plugins/platforms/qwindows.dll",
            "Library/plugins/imageformats/qjpeg.dll",
            "Library/plugins/styles/qwindowsvistastyle.dll",
            "Library/plugins/bearer/qgenericbearer.dll",
        ):
            path = dependency_prefix / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode("ascii"))
        (dependency_prefix / "Library" / "bin").mkdir(parents=True, exist_ok=True)
        (dependency_prefix / "Library" / "bin" / "runtime.dll").write_bytes(b"runtime")

        (minimal_data / "base").mkdir(parents=True)
        (minimal_data / "base" / "base.test").write_text("data\n", encoding="utf-8")

        contract = self.manifest_module.ReleaseContract(
            distribution="usgs-isis-native-apps",
            isis_version="9.0.0",
            platform="win64",
            archive_name="usgs-isis-native-apps-9.0.0-win64.zip",
            root_name="usgs-isis-native-apps-9.0.0-win64",
            public_cli_apps=("reduce",),
            public_gui_apps=("qnet",),
            runtime_helpers=("isisui",),
            mandatory_apps=("reduce", "qnet"),
            qt_plugin_globs=(
                "Library/plugins/platforms/qwindows.dll",
                "Library/plugins/imageformats/*.dll",
                "Library/plugins/styles/*.dll",
            ),
            forbidden_globs=("include/**", "lib/**/*.lib", "**/*.whl"),
        )
        return SimpleNamespace(
            isis_prefix=isis_prefix,
            dependency_prefix=dependency_prefix,
            minimal_data=minimal_data,
            output=output,
            dependency_report=dependency_report,
            contract=contract,
        )

    @staticmethod
    def _fake_dependency_closure(
        seed_files, dependency_prefixes, target_root, dependency_report=None
    ):
        del seed_files
        source = dependency_prefixes[-1] / "Library" / "bin" / "runtime.dll"
        target_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_root / "runtime.dll")
        report = {
            "schema_version": 1,
            "binaries": [],
            "files": [
                {
                    "name": "runtime.dll",
                    "source": "Library/bin/runtime.dll",
                    "target": "runtime.dll",
                    "import_kind": "direct",
                    "parents": ["reduce.exe"],
                }
            ],
            "unresolved": [],
        }
        if dependency_report is not None:
            dependency_report.parent.mkdir(parents=True, exist_ok=True)
            dependency_report.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return report

    def _stage(self, fixture):
        with mock.patch.object(
            self.stage_module,
            "copy_dependency_closure",
            side_effect=self._fake_dependency_closure,
        ):
            return self.stage_module.stage_native_apps(
                fixture.isis_prefix,
                (fixture.dependency_prefix,),
                fixture.minimal_data,
                fixture.contract,
                fixture.output,
                fixture.dependency_report,
            )

    @staticmethod
    def _write_old_outputs(fixture) -> tuple[Path, bytes, bytes]:
        old_root = fixture.output / fixture.contract.root_name
        old_root.mkdir(parents=True)
        old_stage = b"known-good-stage"
        old_report = b"known-good-report"
        (old_root / "old.bin").write_bytes(old_stage)
        fixture.dependency_report.parent.mkdir(parents=True, exist_ok=True)
        fixture.dependency_report.write_bytes(old_report)
        return old_root, old_stage, old_report

    def _assert_old_outputs_unchanged(
        self, fixture, old_root: Path, old_stage: bytes, old_report: bytes
    ) -> None:
        self.assertEqual((old_root / "old.bin").read_bytes(), old_stage)
        self.assertEqual(fixture.dependency_report.read_bytes(), old_report)
        self.assertEqual(
            list(fixture.output.glob(f".{fixture.contract.root_name}.tmp-*")), []
        )
        self.assertEqual(
            list(fixture.output.glob(f".{fixture.contract.root_name}.backup-*")),
            [],
        )
        self.assertEqual(
            list(
                fixture.dependency_report.parent.glob(
                    f".{fixture.dependency_report.name}.tmp-*"
                )
            ),
            [],
        )
        self.assertEqual(
            list(
                fixture.dependency_report.parent.glob(
                    f".{fixture.dependency_report.name}.backup-*"
                )
            ),
            [],
        )

    def test_failed_dependency_closure_preserves_previous_outputs(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            old_root, old_stage, old_report = self._write_old_outputs(fixture)

            written_reports = []

            def fail_closure(seed_files, prefixes, target, dependency_report=None):
                del seed_files, prefixes, target
                written_reports.append(dependency_report)
                dependency_report.write_text(
                    json.dumps({"unresolved": ["missing.dll"]}), encoding="utf-8"
                )
                raise FileNotFoundError(
                    "Unresolved Windows runtime dependencies: missing.dll"
                )

            with mock.patch.object(
                self.stage_module,
                "copy_dependency_closure",
                side_effect=fail_closure,
            ):
                with self.assertRaisesRegex(FileNotFoundError, "missing.dll"):
                    self.stage_module.stage_native_apps(
                        fixture.isis_prefix,
                        (fixture.dependency_prefix,),
                        fixture.minimal_data,
                        fixture.contract,
                        fixture.output,
                        fixture.dependency_report,
                    )

            self._assert_old_outputs_unchanged(
                fixture, old_root, old_stage, old_report
            )
            self.assertEqual(len(written_reports), 1)
            self.assertNotEqual(written_reports[0], fixture.dependency_report)
            self.assertEqual(written_reports[0].parent, fixture.dependency_report.parent)

    def test_forbidden_content_failure_preserves_previous_outputs(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            old_root, old_stage, old_report = self._write_old_outputs(fixture)
            (fixture.isis_prefix / "IsisPreferences").write_text(
                r'D:\build\isis\runtime' + "\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "absolute build/conda"):
                self._stage(fixture)

            self._assert_old_outputs_unchanged(
                fixture, old_root, old_stage, old_report
            )

    def test_publish_rename_failure_restores_previous_outputs(self):
        for failed_output in ("stage", "report"):
            with self.subTest(failed_output=failed_output), TemporaryDirectory() as temp_dir:
                fixture = self._write_stage_fixture(Path(temp_dir))
                old_root, old_stage, old_report = self._write_old_outputs(fixture)
                real_replace = os.replace
                failed = False

                def fail_candidate_publish(source, destination):
                    nonlocal failed
                    source_path = Path(source)
                    destination_path = Path(destination)
                    target = old_root if failed_output == "stage" else fixture.dependency_report
                    if (
                        not failed
                        and ".tmp-" in source_path.name
                        and destination_path == target
                    ):
                        failed = True
                        raise OSError(f"injected {failed_output} publish failure")
                    return real_replace(source, destination)

                with mock.patch.object(
                    self.stage_module.os,
                    "replace",
                    side_effect=fail_candidate_publish,
                ):
                    with self.assertRaisesRegex(
                        OSError, f"injected {failed_output} publish"
                    ):
                        self._stage(fixture)

                self._assert_old_outputs_unchanged(
                    fixture, old_root, old_stage, old_report
                )

    def test_absolute_build_and_conda_paths_are_rejected_without_false_positive(self):
        forbidden = (
            r'D:\build\isis\x',
            '{"prefix":"C:/conda/envs/isis"}',
            r'prefix=D:\code\build\isis\x',
        )
        for value in forbidden:
            with self.subTest(value=value), TemporaryDirectory() as temp_dir:
                fixture = self._write_stage_fixture(Path(temp_dir))
                (fixture.isis_prefix / "IsisPreferences").write_text(
                    value + "\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(ValueError, "absolute build/conda"):
                    self._stage(fixture)

        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            (fixture.isis_prefix / "IsisPreferences").write_text(
                "Drive D: selected; build output is relative.\n", encoding="utf-8"
            )
            result = self._stage(fixture)
            self.assertTrue(result.root.is_dir())

    def test_stager_rejects_reparse_source_and_destination(self):
        for rejected_name in ("reduce.exe", "usgs-isis-native-apps-9.0.0-win64"):
            with self.subTest(rejected_name=rejected_name), TemporaryDirectory() as temp_dir:
                fixture = self._write_stage_fixture(Path(temp_dir))
                if rejected_name == fixture.contract.root_name:
                    (fixture.output / fixture.contract.root_name).mkdir(parents=True)
                with mock.patch.object(
                    self.stage_module,
                    "_is_reparse_point",
                    side_effect=lambda path: Path(path).name == rejected_name,
                ):
                    with self.assertRaisesRegex(ValueError, "reparse"):
                        self._stage(fixture)

    def test_stage_copies_only_declared_payload_and_hashes_every_file(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            result = self._stage(fixture)

            self.assertTrue((result.root / "bin" / "reduce.exe").is_file())
            self.assertTrue((result.root / "bin" / "qnet.exe").is_file())
            self.assertTrue((result.root / "bin" / "isisui.exe").is_file())
            self.assertTrue((result.root / "bin" / "xml" / "reduce.xml").is_file())
            self.assertFalse((result.root / "bin" / "unlisted.exe").exists())
            self.assertFalse((result.root / "include").exists())
            self.assertFalse((result.root / "plugins" / "bearer").exists())
            self.assertTrue((result.root / "plugins" / "platforms" / "qwindows.dll").is_file())
            self.assertTrue((result.root / "lib" / "Camera.plugin").is_file())
            self.assertTrue((result.root / "data" / "base" / "base.test").is_file())

            launch_files = sorted(path.name for path in (result.root / "launch").iterdir())
            self.assertEqual(
                launch_files,
                ["isis-app.cmd", "isis-env.cmd", "isis-launch.ps1", "isis-shell.cmd", "qnet.cmd"],
            )
            apps = json.loads(result.apps_manifest.read_text(encoding="utf-8"))
            self.assertEqual(apps["public_apps"], ["qnet", "reduce"])

            entries = {}
            for line in result.files_manifest.read_text(encoding="utf-8").splitlines():
                digest, relative = line.split("  ", 1)
                entries[relative] = digest
            expected = {
                path.relative_to(result.root).as_posix()
                for path in result.root.rglob("*")
                if path.is_file() and path != result.files_manifest
            }
            self.assertEqual(set(entries), expected)
            for relative, digest in entries.items():
                self.assertEqual(
                    digest,
                    hashlib.sha256((result.root / relative).read_bytes()).hexdigest(),
                )
            self.assertIn("manifest/apps.json", entries)
            self.assertIn("manifest/build-metadata.json", entries)
            self.assertNotIn("manifest/files.sha256", entries)

            generated = (
                result.apps_manifest.read_text(encoding="utf-8")
                + (result.root / "manifest" / "build-metadata.json").read_text(encoding="utf-8")
                + result.dependency_report.read_text(encoding="utf-8")
            )
            self.assertNotIn(str(fixture.isis_prefix), generated)
            self.assertNotIn(str(fixture.dependency_prefix), generated)
            dependency = json.loads(result.dependency_report.read_text(encoding="utf-8"))
            self.assertEqual(
                dependency["files"][0]["sha256"],
                hashlib.sha256(b"runtime").hexdigest(),
            )

    def test_stage_rejects_contract_root_escape(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            values = dict(vars(fixture.contract))
            values["root_name"] = "../escaped"
            fixture.contract = self.manifest_module.ReleaseContract(**values)
            with self.assertRaisesRegex(ValueError, "root_name"):
                self._stage(fixture)
            self.assertFalse((fixture.output.parent / "escaped").exists())

    def test_stage_rejects_dependency_report_inside_final_package(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            fixture.dependency_report = (
                fixture.output
                / fixture.contract.root_name
                / "manifest"
                / "dependencies.json"
            )
            with self.assertRaisesRegex(ValueError, "outside the staged package"):
                self._stage(fixture)

    def test_deterministic_zip_is_byte_reproducible(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            stage = self._stage(fixture).root
            first = self.archive_module.create_deterministic_zip(
                stage, stage.parent / "a.zip"
            )
            second = self.archive_module.create_deterministic_zip(
                stage, stage.parent / "b.zip"
            )
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(
                (stage.parent / "a.zip").read_bytes(),
                (stage.parent / "b.zip").read_bytes(),
            )
            self.assertEqual(first["root_name"], stage.name)
            with zipfile.ZipFile(stage.parent / "a.zip") as archive:
                infos = archive.infolist()
            names = [info.filename for info in infos]
            self.assertEqual(names, sorted(names))
            self.assertEqual({name.split("/", 1)[0] for name in names}, {stage.name})
            self.assertFalse(any(name.endswith("/a.zip") for name in names))
            for info in infos:
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
                self.assertEqual((info.external_attr >> 16) & 0o170000, stat.S_IFREG)
                self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)

    def test_archive_failures_preserve_previous_zip_and_remove_temps(self):
        for failure_kind in ("read", "write", "replace"):
            with self.subTest(failure_kind=failure_kind), TemporaryDirectory() as temp_dir:
                fixture = self._write_stage_fixture(Path(temp_dir))
                stage = self._stage(fixture).root
                archive_path = stage.parent / "release.zip"
                old_archive = b"known-good-zip"
                archive_path.write_bytes(old_archive)

                if failure_kind == "read":
                    original_read = Path.read_bytes

                    def fail_read(path):
                        if Path(path).name == "README.md":
                            raise RuntimeError("injected member read failure")
                        return original_read(path)

                    patcher = mock.patch.object(Path, "read_bytes", new=fail_read)
                elif failure_kind == "write":
                    patcher = mock.patch.object(
                        zipfile.ZipFile,
                        "writestr",
                        side_effect=RuntimeError("injected member write failure"),
                    )
                else:
                    patcher = mock.patch.object(
                        self.archive_module.os,
                        "replace",
                        side_effect=OSError("injected member replace failure"),
                    )

                with patcher, self.assertRaisesRegex(
                    (RuntimeError, OSError), "injected member"
                ):
                    self.archive_module.create_deterministic_zip(stage, archive_path)

                self.assertEqual(archive_path.read_bytes(), old_archive)
                self.assertEqual(
                    list(archive_path.parent.glob(f".{archive_path.name}.tmp-*")),
                    [],
                )

    def test_archive_rejects_reparse_members(self):
        with TemporaryDirectory() as temp_dir:
            fixture = self._write_stage_fixture(Path(temp_dir))
            stage = self._stage(fixture).root
            archive_path = stage.parent / "release.zip"
            with mock.patch.object(
                self.archive_module,
                "_is_reparse_point",
                return_value=True,
            ):
                with self.assertRaisesRegex(ValueError, "reparse"):
                    self.archive_module.create_deterministic_zip(stage, archive_path)
            self.assertFalse(archive_path.exists())

    def test_reparse_attribute_helper_is_permission_independent(self):
        attributes = SimpleNamespace(
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        with mock.patch("os.lstat", return_value=attributes):
            for module in (self.stage_module, self.archive_module):
                with self.subTest(module=module.__name__):
                    self.assertTrue(module._is_reparse_point(Path("virtual-entry")))

    def test_packaging_scripts_expose_orchestrator_cli(self):
        for script, expected in (
            (STAGE_SCRIPT, "--dependency-report"),
            (ARCHIVE_SCRIPT, "--archive"),
        ):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)


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
