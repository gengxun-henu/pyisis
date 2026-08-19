"""Unit tests for the Windows native APP release contract.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added fail-closed validation for the 151-APP release inventory.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPOSITORY_ROOT / "tools" / "packaging" / "windows_native_app_manifest.py"
RELEASE_CONFIG = REPOSITORY_ROOT / "packaging" / "native-apps-win64" / "release.json"
CLI_MANIFEST = REPOSITORY_ROOT / "ports" / "windows" / "isis" / "windows-app-manifest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("windows_native_app_manifest", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WindowsNativeAppManifestTests(unittest.TestCase):
    """Validate the immutable Windows ISIS 9 native APP release boundary."""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def _load_release_data(self):
        return json.loads(RELEASE_CONFIG.read_text(encoding="utf-8"))

    def _write_fixture(self, directory, release_data, manifest_data=None):
        directory = Path(directory)
        manifest = directory / "windows-app-manifest.json"
        if manifest_data is None:
            manifest.write_bytes(CLI_MANIFEST.read_bytes())
        elif isinstance(manifest_data, bytes):
            manifest.write_bytes(manifest_data)
        else:
            manifest.write_text(json.dumps(manifest_data) + "\n", encoding="utf-8")

        release_data = copy.deepcopy(release_data)
        release_data["cli_manifest_sha256"] = hashlib.sha256(
            manifest.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        release = directory / "release.json"
        release.write_text(json.dumps(release_data) + "\n", encoding="utf-8")
        return release, manifest

    def test_repository_contract_resolves_exact_public_inventory(self):
        contract = self.module.load_release_contract(RELEASE_CONFIG, CLI_MANIFEST)
        self.assertEqual(contract.isis_version, "9.0.0")
        self.assertEqual(len(contract.public_cli_apps), 150)
        self.assertEqual(contract.public_gui_apps, ("qnet",))
        self.assertEqual(len(contract.public_apps), 151)
        self.assertTrue({"reduce", "jigsaw", "qnet"} <= set(contract.public_apps))
        self.assertEqual(contract.runtime_helpers, ("isisui",))

    def test_cli_manifest_hash_drift_is_fatal(self):
        with TemporaryDirectory() as temp_dir:
            changed = Path(temp_dir) / "windows-app-manifest.json"
            changed.write_text('{"schema_version": 1, "apps": []}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                self.module.load_release_contract(RELEASE_CONFIG, changed)

    def test_cli_manifest_hash_normalizes_platform_line_endings(self):
        normalized = CLI_MANIFEST.read_bytes().replace(b"\r\n", b"\n").replace(
            b"\r", b"\n"
        )
        with TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "windows-app-manifest.json"
            for content in (normalized, normalized.replace(b"\n", b"\r\n")):
                copied.write_bytes(content)
                with self.subTest(line_ending=b"CRLF" if b"\r\n" in content else b"LF"):
                    contract = self.module.load_release_contract(RELEASE_CONFIG, copied)
                    self.assertEqual(len(contract.public_cli_apps), 150)

    def test_release_schema_rejects_missing_extra_and_wrong_type(self):
        baseline = self._load_release_data()
        mutations = []
        missing = copy.deepcopy(baseline)
        del missing["root_name"]
        mutations.append(missing)
        extra = copy.deepcopy(baseline)
        extra["unexpected"] = True
        mutations.append(extra)
        wrong_type = copy.deepcopy(baseline)
        wrong_type["public_gui_apps"] = "qnet"
        mutations.append(wrong_type)

        for release_data in mutations:
            with self.subTest(keys=sorted(release_data)):
                with TemporaryDirectory() as temp_dir:
                    release, manifest = self._write_fixture(temp_dir, release_data)
                    with self.assertRaises(ValueError):
                        self.module.load_release_contract(release, manifest)

    def test_cli_names_must_be_150_unique_lowercase_entries(self):
        release_data = self._load_release_data()
        baseline = json.loads(CLI_MANIFEST.read_text(encoding="utf-8"))
        mutations = []
        too_short = copy.deepcopy(baseline)
        too_short["apps"].pop()
        mutations.append(too_short)
        duplicate = copy.deepcopy(baseline)
        duplicate["apps"][-1]["name"] = duplicate["apps"][0]["name"]
        mutations.append(duplicate)
        uppercase = copy.deepcopy(baseline)
        uppercase["apps"][0]["name"] = "Algebra"
        mutations.append(uppercase)

        for manifest_data in mutations:
            with self.subTest(first=manifest_data["apps"][0]["name"]):
                with TemporaryDirectory() as temp_dir:
                    release, manifest = self._write_fixture(
                        temp_dir, release_data, manifest_data
                    )
                    with self.assertRaises(ValueError):
                        self.module.load_release_contract(release, manifest)

    def test_cli_entries_require_supported_compiled_isis9_status(self):
        release_data = self._load_release_data()
        baseline = json.loads(CLI_MANIFEST.read_text(encoding="utf-8"))
        for field, value in (("status", "experimental"), ("build_status", "pending")):
            manifest_data = copy.deepcopy(baseline)
            manifest_data["apps"][0]["versions"]["9.0.0"][field] = value
            with self.subTest(field=field):
                with TemporaryDirectory() as temp_dir:
                    release, manifest = self._write_fixture(
                        temp_dir, release_data, manifest_data
                    )
                    with self.assertRaises(ValueError):
                        self.module.load_release_contract(release, manifest)

    def test_public_helpers_and_gui_names_must_not_overlap(self):
        release_data = self._load_release_data()
        for field, values in (
            ("public_gui_apps", ["qnet", "reduce"]),
            ("runtime_helpers", ["isisui", "reduce"]),
            ("runtime_helpers", ["isisui", "qnet"]),
        ):
            changed = copy.deepcopy(release_data)
            changed[field] = values
            with self.subTest(field=field, values=values):
                with TemporaryDirectory() as temp_dir:
                    release, manifest = self._write_fixture(temp_dir, changed)
                    with self.assertRaisesRegex(ValueError, "overlap"):
                        self.module.load_release_contract(release, manifest)

    def test_mandatory_apps_must_be_public(self):
        release_data = self._load_release_data()
        release_data["mandatory_apps"] = ["reduce", "jigsaw", "not-public"]
        with TemporaryDirectory() as temp_dir:
            release, manifest = self._write_fixture(temp_dir, release_data)
            with self.assertRaisesRegex(ValueError, "mandatory"):
                self.module.load_release_contract(release, manifest)


if __name__ == "__main__":
    unittest.main()
