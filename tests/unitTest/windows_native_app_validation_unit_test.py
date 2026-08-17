"""Unit tests for the Windows native APP release validator.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added fail-closed archive and evidence validation coverage.
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
            ],
            "files": [{
                "name": "isis.dll",
                "source": "bin/isis.dll",
                "target": "lib/isis.dll",
                "import_kind": "direct",
                "parents": ["reduce.exe"],
                "sha256": hashlib.sha256(payload["lib/isis.dll"]).hexdigest(),
            }],
            "unresolved": [],
        }
        dependency_report.write_text(json.dumps(dependency_payload), encoding="utf-8")
        archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        runtime_payload = {
            "schema_version": 1,
            "artifact": {
                "archive_name": archive.name,
                "archive_sha256": archive_sha256,
            },
            "host": {"os": "Windows 11", "architecture": "x64"},
            "checks": {
                name: {"passed": 1, "failed": 0, "skipped": 0, "exit_codes": [0]}
                for name in (
                    "archive-extract",
                    "cli-help",
                    "real-operations",
                    "gui-launch",
                    "external-isisdata",
                    "negative-launcher",
                )
            },
        }
        runtime_payload["checks"]["cli-help"]["passed"] = 150
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
                    pattern = "dependency report seed binding"
                else:
                    payload["files"][0]["source"] = r"D:\build\private\isis.dll"
                    pattern = "absolute build/conda path"
            fixture.dependency_report.write_text(json.dumps(payload), encoding="utf-8")
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

    def test_stale_runtime_binding_wrong_host_nonzero_and_skips_are_rejected(self):
        mutations = (
            (lambda p: p["artifact"].update(archive_sha256="0" * 64), "runtime report archive SHA-256"),
            (lambda p: p["host"].update(os="Windows 10"), "Windows 11"),
            (lambda p: p["host"].update(architecture="arm64"), "x64"),
            (lambda p: p["checks"].pop("archive-extract"), "missing required checks"),
            (lambda p: p["checks"]["cli-help"].update(passed=149), "exactly 150"),
            (lambda p: p["checks"]["real-operations"].update(exit_codes=[1]), "nonzero exit code"),
            (lambda p: p["checks"]["cli-help"].update(failed=1), "required check.*failed"),
            (lambda p: p["checks"]["gui-launch"].update(skipped=1), "required check.*skipped"),
        )
        for mutate, pattern in mutations:
            fixture = self._write_valid_fixture()
            mutate(fixture.runtime_payload)
            fixture.write_runtime_report()
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                self.module.validate_release(**fixture.arguments)

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
