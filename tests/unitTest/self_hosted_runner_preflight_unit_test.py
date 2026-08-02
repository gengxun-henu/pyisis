"""Unit tests for the self-hosted runner readiness preflight.

Author: Geng Xun
Created: 2026-08-01
Last Modified: 2026-08-01
Updated: 2026-08-01  Geng Xun added resource, ISIS, and Python ABI checks.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = REPO_ROOT / "scripts" / "check_self_hosted_runner.py"


def load_preflight():
    if not PREFLIGHT_PATH.is_file():
        raise AssertionError(f"Missing self-hosted preflight: {PREFLIGHT_PATH}")
    spec = importlib.util.spec_from_file_location("check_self_hosted_runner", PREFLIGHT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load self-hosted preflight: {PREFLIGHT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SelfHostedRunnerPreflightUnitTest(unittest.TestCase):
    """Validate readiness decisions using isolated fake Conda prefixes."""

    def _make_prefix(self, root: Path, isis_version: str = "9.0.0") -> Path:
        prefix = root / "asp360_new"
        (prefix / "include" / "isis").mkdir(parents=True)
        (prefix / "lib").mkdir()
        (prefix / "lib" / "libisis.so").touch()
        (prefix / "lib" / "Camera.plugin").touch()
        (prefix / "bin").mkdir()
        compiler = prefix / "bin" / "x86_64-conda-linux-gnu-c++"
        compiler.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        compiler.chmod(0o755)
        for tool_name in ("cmake", "ninja"):
            tool = prefix / "bin" / tool_name
            tool.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)
        (prefix / "conda-meta").mkdir()
        (prefix / "conda-meta" / f"isis-{isis_version}-0.json").write_text(
            json.dumps({"name": "isis", "version": isis_version}),
            encoding="utf-8",
        )
        return prefix

    def test_ready_isis9_host_passes_required_checks(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = self._make_prefix(Path(temp_dir))
            report = preflight.inspect_host(
                prefix,
                expected_jobs=16,
                expected_isis_major=9,
                expected_python=(3, 12),
                cpu_count=32,
                memory_bytes=64 * 1024**3,
                available_bytes=200 * 1024**3,
                isis_version="9.0.0",
                python_version=(3, 12, 2),
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["expected_jobs"], 16)
        self.assertTrue(report["checks"]["cpu_capacity"]["ok"])
        self.assertTrue(report["checks"]["isis_version"]["ok"])
        self.assertTrue(report["checks"]["python_version"]["ok"])

    def test_too_few_visible_cpus_fails_readiness(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = self._make_prefix(Path(temp_dir))
            report = preflight.inspect_host(
                prefix,
                expected_jobs=16,
                expected_isis_major=9,
                expected_python=(3, 12),
                cpu_count=8,
                memory_bytes=64 * 1024**3,
                available_bytes=200 * 1024**3,
                isis_version="9.0.0",
                python_version=(3, 12, 2),
            )

        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["cpu_capacity"]["ok"])

    def test_wrong_isis_and_python_versions_fail_readiness(self):
        preflight = load_preflight()
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = self._make_prefix(Path(temp_dir), isis_version="10.0.0")
            report = preflight.inspect_host(
                prefix,
                expected_jobs=16,
                expected_isis_major=9,
                expected_python=(3, 12),
                cpu_count=32,
                memory_bytes=64 * 1024**3,
                available_bytes=200 * 1024**3,
                isis_version="10.0.0",
                python_version=(3, 13, 1),
            )

        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["isis_version"]["ok"])
        self.assertFalse(report["checks"]["python_version"]["ok"])


if __name__ == "__main__":
    unittest.main()
