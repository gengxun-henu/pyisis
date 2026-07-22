"""Unit tests for optional upstream ISIS reference restoration metadata.

Author: Geng Xun
Created: 2026-07-22
Last Modified: 2026-07-22
Updated: 2026-07-22  Geng Xun added lock validation and optional-mirror workflow coverage.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNC_TOOL = PROJECT_ROOT / "tools" / "dev" / "sync_upstream_isis.py"
LOCK_FILE = PROJECT_ROOT / "reference" / "upstream_isis.lock.json"
AUTOFILL_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "autofill-pybind-task-issue.yml"


def _load_sync_tool():
    spec = importlib.util.spec_from_file_location("sync_upstream_isis", SYNC_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SYNC_TOOL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class UpstreamReferenceToolUnitTest(unittest.TestCase):
    """Test optional reference metadata and safe local behavior. Added: 2026-07-22."""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_sync_tool()

    def test_repository_lock_pins_official_isis_900_commit(self):
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["revision"], "9.0.0")
        self.assertEqual(payload["commit"], "950a5606ffeaa13ddb40101fbf25a8737e88902a")
        self.assertEqual(payload["destination"], "reference/upstream_isis")

    def test_load_spec_rejects_destination_outside_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lock_file = root / "lock.json"
            lock_file.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repository": "https://example.invalid/upstream.git",
                        "revision": "9.0.0",
                        "commit": "a" * 40,
                        "destination": "../outside",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "inside the project root"):
                self.module.load_spec(lock_file, root)

    def test_existing_unmanaged_snapshot_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "reference" / "upstream_isis"
            destination.mkdir(parents=True)
            (destination / "local-source.cpp").write_text("local", encoding="utf-8")
            spec = self.module.UpstreamSpec(
                "https://example.invalid/upstream.git",
                "9.0.0",
                "a" * 40,
                destination,
            )

            present, message = self.module.destination_status(spec)
            self.module.restore(spec)

            self.assertTrue(present)
            self.assertIn("unmanaged local snapshot", message)
            self.assertEqual((destination / "local-source.cpp").read_text(), "local")

    def test_restore_clones_and_checks_out_pinned_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(
                ["git", "-C", str(source), "config", "user.name", "PyISIS Test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            (source / "Cube.cpp").write_text("pinned source", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "Cube.cpp"], check=True)
            subprocess.run(
                ["git", "-C", str(source), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            destination = root / "reference" / "upstream_isis"
            spec = self.module.UpstreamSpec(str(source), "local-test", commit, destination)

            self.module.restore(spec)

            self.assertEqual((destination / "Cube.cpp").read_text(), "pinned source")
            present, message = self.module.destination_status(spec)
            self.assertTrue(present)
            self.assertIn(commit, message)

    def test_issue_autofill_uses_inventory_source_before_optional_scan(self):
        workflow = AUTOFILL_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("normalize_upstream_source", workflow)
        self.assertIn("if source_path:", workflow)
        self.assertIn("if ref_root.exists():", workflow)

        embedded_python = workflow.split("python3 - <<'PY'\n", 1)[1].split(
            "\n          PY", 1
        )[0]
        compile(textwrap.dedent(embedded_python), str(AUTOFILL_WORKFLOW), "exec")


if __name__ == "__main__":
    unittest.main()
