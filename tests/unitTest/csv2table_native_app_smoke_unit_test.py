"""Unit tests for the native csv2table process behavior validator.

Author: Geng Xun
Created: 2026-08-17
Last Modified: 2026-08-17
Updated: 2026-08-17  Geng Xun added cross-platform native csv2table validator coverage.
Updated: 2026-08-17  Geng Xun covered ISIS 9-compatible numeric probe data.
Updated: 2026-08-17  Geng Xun covered native artifact and conda package identity.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "tools" / "dev" / "test_csv2table_native_app.py"


def load_validator_module():
    """Load the standalone validator without requiring a package import."""
    specification = importlib.util.spec_from_file_location(
        "csv2table_native_app_validator", MODULE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load validator module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class Csv2TableNativeAppSmokeUnitTest(unittest.TestCase):
    """Validate native csv2table invocation and artifact reporting."""

    def setUp(self) -> None:
        self.module = load_validator_module()
        self.temp_dir = tempfile.TemporaryDirectory(prefix="csv2table validator ")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "ISIS runtime bin"
        (self.bin_dir / "xml").mkdir(parents=True)
        (self.bin_dir / "xml" / "csv2table.xml").write_text(
            "<application/>", encoding="utf-8"
        )
        for executable in ("csv2table", "tabledump"):
            (self.bin_dir / executable).write_text("fixture", encoding="utf-8")
        conda_meta = self.root / "conda-meta"
        conda_meta.mkdir()
        (conda_meta / "isis-10.0.0-h1f94ec8_1.json").write_text(
            json.dumps(
                {
                    "name": "isis",
                    "version": "10.0.0",
                    "build": "h1f94ec8_1",
                    "build_number": 1,
                    "channel": "https://conda.anaconda.org/conda-forge/linux-64",
                    "subdir": "linux-64",
                }
            ),
            encoding="utf-8",
        )
        (conda_meta / "csm-3.0.3.3-h123_0.json").write_text(
            json.dumps(
                {
                    "name": "csm",
                    "version": "3.0.3.3",
                    "build": "h123_0",
                    "build_number": 0,
                    "channel": "https://conda.anaconda.org/conda-forge/linux-64",
                    "subdir": "linux-64",
                }
            ),
            encoding="utf-8",
        )
        self.input_cube = self.root / "source cube.cub"
        self.input_cube.write_bytes(b"native cube source\n")
        self.work_dir = self.root / "working directory"
        self.report_path = self.root / "reports" / "native report.json"

    def make_config(self, *, bin_dir: Path | None = None):
        return self.module.ValidationConfig(
            isis_version="10.0.0",
            input_cube_path=self.input_cube,
            work_dir=self.work_dir,
            report_path=self.report_path,
            bin_dir=self.bin_dir if bin_dir is None else bin_dir,
        )

    def successful_run_side_effect(self, config):
        completed = subprocess.CompletedProcess

        def run(arguments, **kwargs):
            self.assertIsInstance(arguments, list)
            self.assertFalse(kwargs["shell"])
            self.assertTrue(kwargs["text"])
            self.assertTrue(kwargs["capture_output"])
            if arguments[1:] == ["-HELP"]:
                return completed(arguments, 0, "ISIS 10.0.0 help", "")
            if arguments[0] == str(config.tabledump_executable):
                config.table_dump_path.write_text(
                    "Sample,Line,Value\n1.0,2.0,10.5\n3.5,4.0,20.5\n",
                    encoding="utf-8",
                )
                return completed(arguments, 0, "dumped", "")
            return completed(arguments, 0, "attached", "")

        return run

    def test_validator_uses_native_argument_arrays_and_writes_zero_skip_report(self):
        """A list-to-string command regression must fail this native invocation test."""
        config = self.make_config()
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=self.successful_run_side_effect(config),
        ) as run:
            report = self.module.validate_csv2table(config)

        self.assertEqual(
            run.call_args_list[1].args[0][1:],
            [
                f"CSV={config.csv_path}",
                f"TO={config.cube_path}",
                "TABLENAME=PyIsisNativeAppProbe",
            ],
        )
        self.assertEqual(report["summary"], {"passed": 3, "failed": 0, "skipped": 0})
        self.assertEqual(report["isis_version"], {"requested": "10.0.0", "reported": "10.0.0"})
        self.assertEqual(report["commands"][0]["arguments"][1:], ["-HELP"])
        self.assertTrue(report["files"]["csv"]["sha256"])
        self.assertTrue(report["files"]["tabledump"]["sha256"])
        self.assertEqual(json.loads(self.report_path.read_text(encoding="utf-8")), report)

    def test_validator_emits_cross_version_numeric_probe_csv(self):
        """A text column must not break ISIS 9, which infers every field as double."""
        config = self.make_config()
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=self.successful_run_side_effect(config),
        ):
            self.module.validate_csv2table(config)

        rows = config.csv_path.read_text(encoding="utf-8").splitlines()
        for row in rows[1:]:
            for value in row.split(","):
                self.assertTrue(value.replace(".", "", 1).isdigit(), value)

    def test_validator_records_native_artifact_hashes_and_conda_identity(self):
        """Evidence must identify exact native files and installed package builds."""
        config = self.make_config()
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=self.successful_run_side_effect(config),
        ):
            report = self.module.validate_csv2table(config)

        self.assertIn("native_artifacts", report)
        self.assertIn("runtime_packages", report)
        self.assertTrue(report["native_artifacts"]["csv2table"]["sha256"])
        self.assertTrue(report["native_artifacts"]["tabledump"]["sha256"])
        self.assertTrue(report["native_artifacts"]["csv2table_xml"]["sha256"])
        self.assertEqual(
            report["runtime_packages"]["isis"],
            {
                "name": "isis",
                "version": "10.0.0",
                "build": "h1f94ec8_1",
                "build_number": 1,
                "channel": "https://conda.anaconda.org/conda-forge/linux-64",
                "subdir": "linux-64",
            },
        )
        self.assertEqual(report["runtime_packages"]["csm"]["version"], "3.0.3.3")

    def test_validator_records_nonzero_native_exit_as_failure(self):
        """Removing native return-code handling must fail this result test."""
        config = self.make_config()
        completed = subprocess.CompletedProcess
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=[
                completed(["csv2table", "-HELP"], 0, "ISIS 10.0.0 help", ""),
                completed(["csv2table"], 9, "", "csv2table failed"),
            ],
        ):
            report = self.module.validate_csv2table(config)

        self.assertEqual(report["summary"], {"passed": 1, "failed": 1, "skipped": 0})
        self.assertEqual(report["commands"][1]["exit_code"], 9)
        self.assertIn("csv2table failed", report["commands"][1]["stderr"])

    def test_validator_marks_missing_xml_as_required_failure(self):
        """Dropping XML prerequisite validation must fail this report test."""
        (self.bin_dir / "xml" / "csv2table.xml").unlink()
        report = self.module.validate_csv2table(self.make_config())

        self.assertEqual(report["summary"], {"passed": 0, "failed": 1, "skipped": 0})
        self.assertIn("csv2table XML", report["failures"][0])

    def test_validator_marks_missing_executable_as_required_failure(self):
        """Dropping executable prerequisite validation must fail this report test."""
        (self.bin_dir / "csv2table").unlink()
        report = self.module.validate_csv2table(self.make_config())

        self.assertEqual(report["summary"], {"passed": 0, "failed": 1, "skipped": 0})
        self.assertIn("csv2table executable", report["failures"][0])

    def test_validator_rejects_tabledump_without_expected_probe_rows(self):
        """A successful tabledump process must still reproduce the probe values."""
        config = self.make_config()
        completed = subprocess.CompletedProcess

        def run(arguments, **kwargs):
            if arguments[1:] == ["-HELP"]:
                return completed(arguments, 0, "ISIS 10.0.0 help", "")
            if arguments[0] == str(config.tabledump_executable):
                config.table_dump_path.write_text(
                    "Sample,Line,Value\n9.0,9.0,9.0\n", encoding="utf-8"
                )
                return completed(arguments, 0, "dumped", "")
            return completed(arguments, 0, "attached", "")

        with mock.patch.object(self.module.subprocess, "run", side_effect=run):
            report = self.module.validate_csv2table(config)

        self.assertEqual(report["summary"], {"passed": 2, "failed": 1, "skipped": 0})
        self.assertIn("probe data", report["failures"][0])

    def test_validator_preserves_paths_containing_spaces_in_argument_arrays(self):
        """Joining argument arrays must fail this space-containing path test."""
        config = self.make_config()
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=self.successful_run_side_effect(config),
        ) as run:
            self.module.validate_csv2table(config)

        csv2table_arguments = run.call_args_list[1].args[0]
        self.assertEqual(csv2table_arguments[0], str(config.csv2table_executable))
        self.assertIn("working directory", csv2table_arguments[1])
        self.assertIn("working directory", csv2table_arguments[2])

    def test_validator_writes_report_with_atomic_replace(self):
        """Replacing atomic publication with a direct report write must fail this test."""
        config = self.make_config()
        with (
            mock.patch.object(
                self.module.subprocess,
                "run",
                side_effect=self.successful_run_side_effect(config),
            ),
            mock.patch.object(self.module.os, "replace", wraps=self.module.os.replace) as replace,
        ):
            report = self.module.validate_csv2table(config)

        replace.assert_called_once()
        temporary_path, target_path = replace.call_args.args
        self.assertEqual(Path(target_path), self.report_path)
        self.assertEqual(Path(temporary_path).suffix, ".tmp")
        self.assertTrue(self.report_path.exists())
        self.assertFalse(Path(temporary_path).exists())
        self.assertEqual(json.loads(self.report_path.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
