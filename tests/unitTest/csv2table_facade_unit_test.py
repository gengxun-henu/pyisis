"""Unit tests for the cross-platform ISIS 10 csv2table facade.

Author: Geng Xun
Created: 2026-08-02
Last Modified: 2026-08-02
Updated: 2026-08-02  Geng Xun added private ISIS APP runner contract coverage.
Updated: 2026-08-02  Geng Xun added csv2table parameter, dispatch, and export coverage.
Updated: 2026-08-02  Geng Xun added Linux ISIS 10 native table round-trip coverage.
Updated: 2026-08-02  Geng Xun covered ISIS_PREFIX-based application XML lookup.
Updated: 2026-08-02  Geng Xun fixed direct-file test support imports used by CI.
"""

from __future__ import annotations

from contextlib import chdir
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "python" / "isis_pybind" / "_app_runner.py"
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "csv2table_test_app_runner", RUNNER_PATH
)
assert RUNNER_SPEC and RUNNER_SPEC.loader
_app_runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(_app_runner)

try:
    from ._unit_test_support import (
        ip,
        make_closed_test_cube,
        open_cube,
        temporary_directory,
    )
except ImportError:
    UNIT_TEST_DIR = Path(__file__).resolve().parent
    if str(UNIT_TEST_DIR) not in sys.path:
        sys.path.insert(0, str(UNIT_TEST_DIR))
    from _unit_test_support import (
        ip,
        make_closed_test_cube,
        open_cube,
        temporary_directory,
    )

from isis_pybind import _csv2table


class IsisAppRunnerTest(unittest.TestCase):
    """Exercise the private, shell-free ISIS executable runner."""

    def test_configured_prefix_precedes_path_lookup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "bin" / "csv2table.exe"
            executable.parent.mkdir()
            executable.touch()
            with (
                mock.patch.dict(
                    os.environ, {"ISIS_PREFIX": temp_dir}, clear=True
                ),
                mock.patch.object(
                    _app_runner,
                    "_executable_name",
                    return_value="csv2table.exe",
                ),
                mock.patch.object(_app_runner.shutil, "which") as which,
            ):
                resolved = _app_runner._find_isis_app_executable("csv2table")

        self.assertEqual(resolved, str(executable))
        which.assert_not_called()

    def test_runner_uses_argument_list_without_shell(self):
        completed = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with (
            mock.patch.object(
                _app_runner,
                "_find_isis_app_executable",
                return_value=r"C:\isis\bin\csv2table.exe",
            ),
            mock.patch.object(
                _app_runner.subprocess,
                "run",
                return_value=completed,
            ) as run,
        ):
            result = _app_runner._run_isis_app(
                "csv2table",
                ["CSV=input file.csv", "TO=target.cub"],
            )

        self.assertIsNone(result)
        run.assert_called_once_with(
            [
                r"C:\isis\bin\csv2table.exe",
                "CSV=input file.csv",
                "TO=target.cub",
            ],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )

    def test_runner_reports_native_failure_context(self):
        completed = subprocess.CompletedProcess(
            [],
            7,
            stdout="native output",
            stderr="bad table",
        )
        with (
            mock.patch.object(
                _app_runner,
                "_find_isis_app_executable",
                return_value="csv2table.exe",
            ),
            mock.patch.object(
                _app_runner.subprocess,
                "run",
                return_value=completed,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "exit code 7.*bad table"):
                _app_runner._run_isis_app(
                    "csv2table",
                    ["CSV=input.csv"],
                )


class Csv2TableFacadeTest(unittest.TestCase):
    """Validate shared parameter encoding and platform dispatch."""

    def test_arguments_preserve_paths_and_encode_optional_values(self):
        arguments = _csv2table._build_csv2table_arguments(
            Path("input files/measurements.csv"),
            Path("output files/target.cub"),
            "Measurements",
            label=Path("labels/table label.pvl"),
            coltypes=["Double", "Text"],
        )

        self.assertEqual(
            arguments,
            [
                "CSV=input files/measurements.csv",
                "TO=output files/target.cub",
                "TABLENAME=Measurements",
                "LABEL=labels/table label.pvl",
                "COLTYPES=(Double,Text)",
            ],
        )

    def test_empty_table_name_and_invalid_coltype_are_rejected(self):
        with self.assertRaises(ValueError):
            _csv2table._build_csv2table_arguments(
                "a.csv",
                "b.cub",
                "   ",
            )
        with self.assertRaisesRegex(ValueError, "Unsupported COLTYPES value"):
            _csv2table._build_csv2table_arguments(
                "a.csv",
                "b.cub",
                "T",
                coltypes=["Complex"],
            )

    def test_windows_dispatch_uses_private_runner(self):
        with (
            mock.patch(
                "isis_pybind._csv2table._is_windows",
                return_value=True,
            ),
            mock.patch("isis_pybind._csv2table._run_isis_app") as runner,
        ):
            result = _csv2table.csv2table("a.csv", "b.cub", "T")

        self.assertIsNone(result)
        runner.assert_called_once_with(
            "csv2table",
            ["CSV=a.csv", "TO=b.cub", "TABLENAME=T"],
        )

    def test_linux_dispatch_uses_native_entry_point(self):
        with (
            mock.patch(
                "isis_pybind._csv2table._is_windows",
                return_value=False,
            ),
            mock.patch(
                "isis_pybind._csv2table._native_csv2table"
            ) as native,
        ):
            result = _csv2table.csv2table("a.csv", "b.cub", "T")

        self.assertIsNone(result)
        native.assert_called_once_with(
            ["CSV=a.csv", "TO=b.cub", "TABLENAME=T"]
        )

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10 only")
    def test_isis10_package_exports_public_facade_only(self):
        self.assertGreaterEqual(ip.__isis_major__, 10)
        self.assertIs(ip.csv2table, _csv2table.csv2table)
        self.assertIn("csv2table", ip.__all__)
        self.assertNotIn("_run_isis_app", ip.__all__)

    def test_native_failure_is_wrapped_with_operation_context(self):
        with (
            mock.patch(
                "isis_pybind._csv2table._is_windows",
                return_value=True,
            ),
            mock.patch(
                "isis_pybind._csv2table._run_isis_app",
                side_effect=RuntimeError("exit code 7: bad table"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "csv2table failed: exit code 7: bad table",
            ):
                _csv2table.csv2table("a.csv", "b.cub", "T")

    def test_native_adapter_uses_authoritative_isis_prefix_for_xml(self):
        source = (PROJECT_ROOT / "src" / "bind_isis10.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'Isis::FileName("$ISIS_PREFIX/bin/xml/csv2table.xml")',
            source,
        )
        self.assertNotIn(
            'Isis::FileName("$ISISROOT/bin/xml/csv2table.xml")',
            source,
        )


@unittest.skipUnless(
    ip.__isis_major__ >= 10 and os.name != "nt",
    "Linux ISIS 10 only",
)
class Csv2TableLinuxIntegrationTest(unittest.TestCase):
    """Run the exported ISIS 10 csv2table implementation in process."""

    def test_csv_and_label_are_attached_as_typed_table(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(
                temp_dir,
                name="target.cub",
            )
            csv_path = temp_dir / "measurements.csv"
            csv_path.write_text(
                "Value,Name\n1.5,M\n2.5,P\n",
                encoding="utf-8",
            )
            label_path = temp_dir / "table.pvl"
            label_path.write_text(
                "Source = UnitTest\nEnd\n",
                encoding="utf-8",
            )

            with chdir(temp_dir):
                result = ip.csv2table(
                    csv_path,
                    cube_path,
                    "Measurements",
                    label=label_path,
                    coltypes=["Double", "Text"],
                )
            self.assertIsNone(result)

            cube = open_cube(cube_path)
            try:
                self.assertTrue(cube.has_table("Measurements"))
                table = cube.read_table("Measurements")
                self.assertEqual(table.records(), 2)
                self.assertEqual(table[0]["Value"].value(), 1.5)
                self.assertEqual(
                    table[1]["Name"].value().rstrip("\x00"),
                    "P",
                )
                self.assertEqual(
                    table.label().keyword("Source")[0],
                    "UnitTest",
                )
            finally:
                cube.close()


if __name__ == "__main__":
    unittest.main()
