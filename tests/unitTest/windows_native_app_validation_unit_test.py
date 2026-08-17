"""Unit tests for the Windows native APP release validator.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added fail-closed archive and evidence validation coverage.
Updated: 2026-08-18  Geng Xun hardened Windows paths and closed dependency/runtime schemas after review.
Updated: 2026-08-18  Geng Xun bound dependency graphs and canonical runtime command identities.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY_ROOT / "tools" / "packaging" / "validate_windows_native_apps.py"
MANIFEST_MODULE = REPOSITORY_ROOT / "tools" / "packaging" / "windows_native_app_manifest.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class ValidationFixture:
    archive: Path
    dependency_report: Path
    runtime_report: Path
    output_report: Path
    release_contract: object
    runtime_payload: dict[str, object]

    @property
    def arguments(self) -> dict[str, object]:
        return {
            "archive": self.archive,
            "dependency_report": self.dependency_report,
            "runtime_report": self.runtime_report,
            "release_contract": self.release_contract,
            "output_report": self.output_report,
        }

    @property
    def archive_sha256(self) -> str:
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def write_runtime_report(self) -> None:
        self.runtime_report.write_text(
            json.dumps(self.runtime_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class WindowsNativeAppValidationTests(unittest.TestCase):
    """Exercise the schema-1 release gate at every retained-artifact boundary."""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_module("validate_windows_native_apps", VALIDATOR)
        cls.manifest_module = _load_module("windows_native_app_manifest_validation", MANIFEST_MODULE)

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _contract(self):
        cli_apps = tuple(sorted(("reduce", "jigsaw", *(f"app{index:03d}" for index in range(148)))))
        return self.manifest_module.ReleaseContract(
            distribution="usgs-isis-native-apps",
            isis_version="9.0.0",
            platform="win64",
            archive_name="usgs-isis-native-apps-9.0.0-win64.zip",
            root_name="usgs-isis-native-apps-9.0.0-win64",
            public_cli_apps=cli_apps,
            public_gui_apps=("qnet",),
            runtime_helpers=("isisui",),
            mandatory_apps=("reduce", "jigsaw", "qnet"),
            qt_plugin_globs=("plugins/platforms/qwindows.dll",),
            forbidden_globs=("include/**", "lib/**/*.lib", "**/*.whl"),
        )

    @staticmethod
    def _regular_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        return info

    def _write_archive(self, archive: Path, root_name: str, payload: dict[str, bytes]) -> None:
        hashed = dict(payload)
        lines = [
            f"{hashlib.sha256(content).hexdigest()}  {name}"
            for name, content in sorted(hashed.items())
        ]
        hashed["manifest/files.sha256"] = ("\n".join(lines) + "\n").encode()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative, content in sorted(hashed.items()):
                bundle.writestr(self._regular_info(f"{root_name}/{relative}"), content)

    def _write_valid_fixture(self) -> ValidationFixture:
        contract = self._contract()
        archive = self.root / contract.archive_name
        dependency_report = self.root / "dependencies.json"
        runtime_report = self.root / "runtime.json"
        output_report = self.root / "validation.json"
        apps_payload = {
            "schema_version": 1,
            "distribution": contract.distribution,
            "isis_version": contract.isis_version,
            "platform": contract.platform,
            "public_cli_apps": list(contract.public_cli_apps),
            "public_gui_apps": list(contract.public_gui_apps),
            "public_apps": list(contract.public_apps),
            "runtime_helpers": list(contract.runtime_helpers),
        }
        payload = {
            "README.md": b"portable package\n",
            "lib/isis.dll": b"isis-runtime",
            "lib/runtime.dll": b"closure-runtime",
            "plugins/platforms/qwindows.dll": b"qt-plugin",
            "manifest/apps.json": (json.dumps(apps_payload, sort_keys=True) + "\n").encode(),
            "manifest/build-metadata.json": b'{"schema_version": 1}\n',
        }
        for name in contract.public_apps + contract.runtime_helpers:
            payload[f"bin/{name}.exe"] = f"exe:{name}".encode()
        for name in contract.public_cli_apps:
            payload[f"bin/xml/{name}.xml"] = f"<app name=\"{name}\"/>\n".encode()
        self._write_archive(archive, contract.root_name, payload)

        dependency_payload = {
            "schema_version": 1,
            "binaries": [
                {"binary": f"{name}.exe", "imports": []}
                for name in contract.public_apps + contract.runtime_helpers
            ] + [
                {"binary": "isis.dll", "imports": []},
                {"binary": "qwindows.dll", "imports": []},
                {"binary": "runtime.dll", "imports": []},
            ],
            "files": [{
                "name": "runtime.dll",
                "source": "Library/bin/runtime.dll",
                "target": "lib/runtime.dll",
                "import_kind": "direct",
                "parents": ["reduce.exe"],
                "sha256": hashlib.sha256(payload["lib/runtime.dll"]).hexdigest(),
            }],
            "unresolved": [],
        }
        reduce_binary = next(
            item for item in dependency_payload["binaries"] if item["binary"] == "reduce.exe"
        )
        reduce_binary["imports"] = [
            {
                "name": "runtime.dll",
                "import_kind": "direct",
                "classification": "resolved",
            },
            {
                "name": "isis.dll",
                "import_kind": "direct",
                "classification": "packaged",
            },
            {
                "name": "kernel32.dll",
                "import_kind": "direct",
                "classification": "system",
            },
        ]
        dependency_report.write_text(json.dumps(dependency_payload), encoding="utf-8")
        archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        runtime_payload = {
            "schema_version": 1,
            "artifact": {
                "archive_name": archive.name,
                "archive_sha256": archive_sha256,
            },
            "host": {
                "os": "Windows 11",
                "version": "10.0.26100",
                "architecture": "x64",
            },
            "extraction_path": r"C:\Users\clean\AppData\Local\Temp\native package with spaces",
            "scrubbed_environment": {
                "variables": [
                    "CONDA_PREFIX",
                    "ISISROOT",
                    "ISIS_PREFIX",
                    "ISISDATA",
                    "QT_PLUGIN_PATH",
                ],
                "path_entries_removed": 3,
            },
            "checks": {
                name: {
                    "commands": [f"launch/{name}-{index}" for index in range(count)],
                    "passed": count,
                    "failed": 0,
                    "skipped": 0,
                    "exit_codes": [0] * count,
                }
                for name, count in {
                    "archive-extract": 1,
                    "cli-help": 150,
                    "real-operations": 9,
                    "gui-launch": 3,
                    "external-isisdata": 1,
                    "negative-launcher": 2,
                }.items()
            },
            "summary": {"passed": 166, "failed": 0, "skipped": 0},
        }
        runtime_payload["checks"] = self._canonical_checks(contract)
        runtime_payload["checks"]["negative-launcher"]["exit_codes"] = [4, 3]
        fixture = ValidationFixture(
            archive,
            dependency_report,
            runtime_report,
            output_report,
            contract,
            runtime_payload,
        )
        fixture.write_runtime_report()
        return fixture

    @staticmethod
    def _canonical_checks(contract) -> dict[str, dict[str, object]]:
        real_apps = (
            "stats",
            "getkey",
            "catlab",
            "campt",
            "reduce",
            "cam2map",
            "isis2std",
            "cubeit",
            "fx",
        )
        commands = {
            "archive-extract": ["archive-extract"],
            "cli-help": [
                f"launch/isis-app.cmd {name} -HELP"
                for name in sorted(contract.public_cli_apps)
            ],
            "real-operations": [
                f"launch/isis-app.cmd {name} mode=real-operation"
                for name in real_apps
            ],
            "gui-launch": [
                "launch/isis-app.cmd reduce -gui",
                "launch/isis-app.cmd jigsaw -gui",
                "launch/qnet.cmd",
            ],
            "external-isisdata": [
                "launch/isis-app.cmd stats isisdata=external"
            ],
            "negative-launcher": [
                "launch/isis-app.cmd __undeclared_app__ isisdata=bundled",
                "launch/isis-app.cmd stats isisdata=missing",
            ],
        }
        return {
            name: {
                "commands": values,
                "passed": len(values),
                "failed": 0,
                "skipped": 0,
                "exit_codes": [0] * len(values),
            }
            for name, values in commands.items()
        }

    def _append_zip_member(
        self, fixture: ValidationFixture, name: str, content: bytes = b"bad", mode: int = 0o100644
    ) -> None:
        with zipfile.ZipFile(fixture.archive, "a") as bundle:
            info = self._regular_info(name)
            info.external_attr = mode << 16
            bundle.writestr(info, content)

    def test_valid_release_produces_hash_bound_report(self):
        fixture = self._write_valid_fixture()
        report = self.module.validate_release(**fixture.arguments)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["public_app_count"], 151)
        self.assertEqual(report["dependency_closure"]["unresolved"], 0)
        self.assertEqual(report["tests"]["failed"], 0)
        self.assertEqual(report["tests"]["skipped"], 0)
        self.assertEqual(report["archive"]["sha256"], fixture.archive_sha256)
        self.assertRegex(report["validated_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$")
        self.assertEqual(
            report["inputs"]["dependency_report_sha256"],
            hashlib.sha256(fixture.dependency_report.read_bytes()).hexdigest(),
        )
        self.assertEqual(json.loads(fixture.output_report.read_text()), report)

    def test_unsafe_zip_member_spellings_are_rejected(self):
        root = "usgs-isis-native-apps-9.0.0-win64"
        for name in (
            rf"{root}\escape.dll",
            "C:/escape.dll",
            f"/{root}/escape.dll",
            f"{root}//escape.dll",
            f"{root}/./escape.dll",
            f"{root}/../escape.dll",
            "wrong-root/escape.dll",
            f"{root}/readme.txt:stream",
            f"{root}/bad\x01name.txt",
            f"{root}/trailing-dot.",
            f"{root}/trailing-space ",
            f"{root}/CON",
            f"{root}/prn.txt",
            f"{root}/Aux.Xml",
            f"{root}/nul.data",
            f"{root}/COM1.log",
            f"{root}/com9",
            f"{root}/LPT1.txt",
            f"{root}/lpt9",
        ):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe ZIP member|fixed root"):
                self.module.safe_zip_member(name, root)

    def test_zip_traversal_member_is_rejected(self):
        fixture = self._write_valid_fixture()
        self._append_zip_member(fixture, f"{fixture.release_contract.root_name}/../escape.dll")
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            self.module.validate_release(**fixture.arguments)

    def test_duplicate_casefold_and_nonregular_members_are_rejected(self):
        for kind in ("duplicate", "casefold", "symlink"):
            fixture = self._write_valid_fixture()
            root = fixture.release_contract.root_name
            if kind == "duplicate":
                self._append_zip_member(fixture, f"{root}/README.md")
                pattern = "duplicate ZIP member"
            elif kind == "casefold":
                self._append_zip_member(fixture, f"{root}/readme.md")
                pattern = "case-insensitive ZIP member collision"
            else:
                self._append_zip_member(fixture, f"{root}/link", mode=stat.S_IFLNK | 0o777)
                pattern = "non-regular ZIP member"
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_inventory_drift_missing_mandatory_and_unexpected_exe_are_rejected(self):
        fixture = self._write_valid_fixture()
        apps = json.loads(self._read_member(fixture, "manifest/apps.json"))
        apps["public_apps"].remove("app000")
        self._rewrite_member(fixture, "manifest/apps.json", json.dumps(apps).encode())
        with self.assertRaisesRegex(ValueError, "public APP inventory"):
            self.module.validate_release(**fixture.arguments)

        fixture = self._write_valid_fixture()
        self._rewrite_without(fixture, "bin/reduce.exe")
        with self.assertRaisesRegex(ValueError, "mandatory APP"):
            self.module.validate_release(**fixture.arguments)

        fixture = self._write_valid_fixture()
        self._rewrite_member(fixture, "bin/surprise.exe", b"surprise")
        with self.assertRaisesRegex(ValueError, "unexpected executable"):
            self.module.validate_release(**fixture.arguments)

    def test_forbidden_member_and_absolute_build_path_are_rejected(self):
        fixture = self._write_valid_fixture()
        self._rewrite_member(fixture, "include/private.h", b"bad")
        with self.assertRaisesRegex(ValueError, "forbidden archive member"):
            self.module.validate_release(**fixture.arguments)

        fixture = self._write_valid_fixture()
        self._rewrite_member(fixture, "notes.txt", b"D:\\build\\private\\isis.dll")
        with self.assertRaisesRegex(ValueError, "absolute build/conda path"):
            self.module.validate_release(**fixture.arguments)

        fixture = self._write_valid_fixture()
        self._rewrite_member(fixture, "lib/private.lib", b"bad")
        with self.assertRaisesRegex(ValueError, "forbidden archive member"):
            self.module.validate_release(**fixture.arguments)

    def test_files_manifest_missing_extra_and_hash_mismatch_are_rejected(self):
        for kind in ("missing", "extra", "hash"):
            fixture = self._write_valid_fixture()
            lines = self._read_member(fixture, "manifest/files.sha256").decode().splitlines()
            if kind == "missing":
                lines = [line for line in lines if not line.endswith("  README.md")]
                pattern = "files.sha256 inventory"
            elif kind == "extra":
                lines.append(f"{'0' * 64}  ghost.dll")
                pattern = "files.sha256 inventory"
            else:
                lines = [f"{'0' * 64}  README.md" if line.endswith("  README.md") else line for line in lines]
                pattern = "payload hash mismatch"
            self._rewrite_member(fixture, "manifest/files.sha256", ("\n".join(lines) + "\n").encode(), refresh_manifest=False)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_dependency_unresolved_target_and_hash_fail_closed(self):
        for kind in ("unresolved", "target", "hash", "binding", "absolute"):
            fixture = self._write_valid_fixture()
            payload = json.loads(fixture.dependency_report.read_text())
            if kind == "unresolved":
                payload["unresolved"] = ["missing.dll"]
                pattern = "unresolved dependencies"
            elif kind == "target":
                payload["files"][0]["target"] = "lib/missing.dll"
                pattern = "dependency target"
            else:
                if kind == "hash":
                    payload["files"][0]["sha256"] = "0" * 64
                    pattern = "dependency hash mismatch"
                elif kind == "binding":
                    payload["binaries"] = [
                        item for item in payload["binaries"] if item["binary"] != "reduce.exe"
                    ]
                    pattern = "unknown dependency parent|dependency binary inventory"
                else:
                    payload["files"][0]["source"] = r"D:\build\private\isis.dll"
                    pattern = "absolute build/conda path"
            fixture.dependency_report.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_dependency_schema_and_reverse_dll_inventory_are_exact(self):
        mutations = []

        def add_top(payload, fixture):
            payload["extra"] = True

        mutations.append((add_top, "dependency report keys mismatch"))

        def duplicate_binary(payload, fixture):
            payload["binaries"].append(dict(payload["binaries"][0]))

        mutations.append((duplicate_binary, "duplicate dependency binary"))

        def unexpected_binary(payload, fixture):
            payload["binaries"].append({"binary": "evil.dll", "imports": []})

        mutations.append((unexpected_binary, "dependency binary inventory"))

        def extra_binary_key(payload, fixture):
            payload["binaries"][0]["extra"] = 1

        mutations.append((extra_binary_key, "dependency binary keys mismatch"))

        def malformed_import(payload, fixture):
            payload["binaries"][0]["imports"] = [{
                "name": "runtime.dll",
                "import_kind": "invalid",
                "classification": "resolved",
            }]

        mutations.append((malformed_import, "dependency import_kind"))

        def extra_file_key(payload, fixture):
            payload["files"][0]["extra"] = 1

        mutations.append((extra_file_key, "dependency file keys mismatch"))

        def unreported_archive_dll(payload, fixture):
            self._rewrite_member(fixture, "lib/evil.dll", b"evil")

        mutations.append((unreported_archive_dll, "archive DLL inventory"))

        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            payload = json.loads(fixture.dependency_report.read_text())
            mutate(payload, fixture)
            fixture.dependency_report.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_dependency_graph_edges_bind_imports_files_binaries_and_parents(self):
        def resolved_without_file(payload, fixture):
            payload["files"] = []
            payload["binaries"] = [
                item for item in payload["binaries"] if item["binary"] != "runtime.dll"
            ]
            self._rewrite_without(fixture, "lib/runtime.dll")

        def false_system(payload, fixture):
            reduce_binary = next(
                item for item in payload["binaries"] if item["binary"] == "reduce.exe"
            )
            reduce_binary["imports"][0]["classification"] = "system"

        def orphan_file(payload, fixture):
            reduce_binary = next(
                item for item in payload["binaries"] if item["binary"] == "reduce.exe"
            )
            reduce_binary["imports"] = [
                item for item in reduce_binary["imports"] if item["name"] != "runtime.dll"
            ]

        def parent_disagreement(payload, fixture):
            payload["files"][0]["parents"] = ["app000.exe"]

        def unknown_packaged(payload, fixture):
            reduce_binary = next(
                item for item in payload["binaries"] if item["binary"] == "reduce.exe"
            )
            reduce_binary["imports"].append({
                "name": "evil.dll",
                "import_kind": "direct",
                "classification": "packaged",
            })

        mutations = (
            (resolved_without_file, "resolved import.*closure file"),
            (false_system, "system classification"),
            (orphan_file, "orphaned dependency file"),
            (parent_disagreement, "parent/import disagreement"),
            (unknown_packaged, "packaged import.*staged DLL"),
        )
        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            payload = json.loads(fixture.dependency_report.read_text())
            mutate(payload, fixture)
            fixture.dependency_report.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_stale_runtime_binding_wrong_host_nonzero_and_skips_are_rejected(self):
        mutations = (
            (lambda p: p["artifact"].update(archive_sha256="0" * 64), "runtime report archive SHA-256"),
            (lambda p: p["host"].update(os="Windows 10"), "Windows 11"),
            (lambda p: p["host"].update(os="Definitely not Windows 11"), "Windows 11"),
            (lambda p: p["host"].update(version="unknown"), "host version"),
            (lambda p: p["host"].update(architecture="arm64"), "x64"),
            (lambda p: p["host"].update(architecture="X64"), "x64"),
            (lambda p: p["checks"].pop("archive-extract"), "runtime check groups mismatch"),
            (lambda p: p["checks"]["cli-help"].update(passed=149), "exactly 150"),
            (lambda p: p["checks"]["real-operations"].update(exit_codes=[1] + [0] * 8), "nonzero exit code"),
            (lambda p: p["checks"]["cli-help"].update(failed=1), "required check.*failed"),
            (lambda p: p["checks"]["gui-launch"].update(skipped=1), "required check.*skipped"),
        )
        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            mutate(fixture.runtime_payload)
            fixture.write_runtime_report()
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_runtime_schema_provenance_counts_and_results_are_exact(self):
        mutations = (
            (lambda p: p.update(extra=True), "runtime report keys mismatch"),
            (lambda p: p["artifact"].update(extra=True), "runtime artifact keys mismatch"),
            (lambda p: p["host"].update(extra=True), "runtime host keys mismatch"),
            (lambda p: p.pop("extraction_path"), "runtime report keys mismatch"),
            (lambda p: p.update(extraction_path=r"D:\build\native package with spaces"), "clean absolute Windows path"),
            (lambda p: p["scrubbed_environment"].update(extra=True), "scrubbed_environment keys mismatch"),
            (lambda p: p["scrubbed_environment"].update(variables=["CONDA_PREFIX"]), "scrubbed variables"),
            (lambda p: p["scrubbed_environment"].update(path_entries_removed=True), "path_entries_removed"),
            (lambda p: p["checks"].update(extra={"commands": [], "passed": 0, "failed": 1, "skipped": 1, "exit_codes": [1]}), "runtime check groups mismatch"),
            (lambda p: p["checks"]["gui-launch"].update(extra=True), "required check gui-launch keys mismatch"),
            (lambda p: p["checks"]["real-operations"].update(passed=8), "real-operations must record exactly 9"),
            (lambda p: p["checks"]["gui-launch"]["commands"].pop(), "commands must contain exactly 3"),
            (lambda p: p["checks"]["cli-help"]["exit_codes"].pop(), "exit_codes must contain exactly 150"),
            (lambda p: p["checks"]["negative-launcher"].update(exit_codes=[3, 4]), "expected exit codes"),
            (lambda p: p.update(summary={"passed": 165, "failed": 0, "skipped": 0}), "runtime summary mismatch"),
            (lambda p: p["checks"]["gui-launch"]["commands"].__setitem__(0, r"D:\source\qnet.cmd"), "absolute path outside extraction_path"),
        )
        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            mutate(fixture.runtime_payload)
            fixture.write_runtime_report()
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_runtime_commands_are_bound_to_canonical_probe_identities(self):
        mutations = (
            (lambda p: p["checks"]["cli-help"].update(commands=[f"fake/{index}" for index in range(150)]), "cli-help command identities"),
            (lambda p: p["checks"]["real-operations"]["commands"].__setitem__(0, "launch/isis-app.cmd fake mode=real-operation"), "real-operations command identities"),
            (lambda p: p["checks"]["real-operations"]["commands"].__setitem__(1, p["checks"]["real-operations"]["commands"][0]), "real-operations command identities|duplicates"),
            (lambda p: p["checks"]["gui-launch"]["commands"].__setitem__(2, "launch/isis-app.cmd qview -gui"), "gui-launch command identities"),
            (lambda p: p["checks"]["external-isisdata"]["commands"].__setitem__(0, "launch/isis-app.cmd stats isisdata=bundled"), "external-isisdata command identities"),
            (lambda p: p["checks"]["negative-launcher"]["commands"].reverse(), "negative-launcher command identities"),
            (lambda p: p["checks"]["cli-help"]["commands"].__setitem__(0, "launch/isis-app.cmd reduce -HELP\x01"), "control character"),
        )
        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            mutate(fixture.runtime_payload)
            fixture.write_runtime_report()
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_validator_exports_same_canonical_commands_used_by_fixture(self):
        fixture = self._write_valid_fixture()
        expected = {
            name: tuple(check["commands"])
            for name, check in fixture.runtime_payload["checks"].items()
        }
        self.assertEqual(
            self.module.canonical_runtime_commands(fixture.release_contract),
            expected,
        )

    def test_failure_preserves_existing_report(self):
        fixture = self._write_valid_fixture()
        fixture.output_report.write_bytes(b"old report")
        fixture.runtime_payload["checks"]["gui-launch"]["skipped"] = 1
        fixture.write_runtime_report()
        with self.assertRaises(ValueError):
            self.module.validate_release(**fixture.arguments)
        self.assertEqual(fixture.output_report.read_bytes(), b"old report")
        self.assertEqual(list(fixture.output_report.parent.glob(f".{fixture.output_report.name}.tmp-*")), [])

    def test_atomic_replace_failure_preserves_existing_report_and_cleans_candidate(self):
        fixture = self._write_valid_fixture()
        fixture.output_report.write_bytes(b"old report")
        with mock.patch.object(self.module.os, "replace", side_effect=OSError("injected")):
            with self.assertRaisesRegex(OSError, "injected"):
                self.module.validate_release(**fixture.arguments)
        self.assertEqual(fixture.output_report.read_bytes(), b"old report")
        self.assertEqual(list(fixture.output_report.parent.glob(f".{fixture.output_report.name}.tmp-*")), [])

    def _read_member(self, fixture: ValidationFixture, relative: str) -> bytes:
        with zipfile.ZipFile(fixture.archive) as bundle:
            return bundle.read(f"{fixture.release_contract.root_name}/{relative}")

    def _read_payload(self, fixture: ValidationFixture) -> dict[str, bytes]:
        root = fixture.release_contract.root_name + "/"
        with zipfile.ZipFile(fixture.archive) as bundle:
            return {
                info.filename[len(root):]: bundle.read(info)
                for info in bundle.infolist()
                if info.filename.startswith(root) and info.filename != root + "manifest/files.sha256"
            }

    def _rewrite_member(self, fixture: ValidationFixture, relative: str, content: bytes, *, refresh_manifest: bool = True) -> None:
        payload = self._read_payload(fixture)
        payload[relative] = content
        if refresh_manifest:
            self._write_archive(fixture.archive, fixture.release_contract.root_name, payload)
        else:
            payload["manifest/files.sha256"] = content
            with zipfile.ZipFile(fixture.archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for name, value in sorted(payload.items()):
                    bundle.writestr(self._regular_info(f"{fixture.release_contract.root_name}/{name}"), value)
        fixture.runtime_payload["artifact"]["archive_sha256"] = fixture.archive_sha256
        fixture.write_runtime_report()

    def _rewrite_without(self, fixture: ValidationFixture, relative: str) -> None:
        payload = self._read_payload(fixture)
        del payload[relative]
        self._write_archive(fixture.archive, fixture.release_contract.root_name, payload)
        fixture.runtime_payload["artifact"]["archive_sha256"] = fixture.archive_sha256
        fixture.write_runtime_report()


if __name__ == "__main__":
    unittest.main()
