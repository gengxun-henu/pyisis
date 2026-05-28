"""
Unit tests for caminfo-based ISIS cube selection helpers.

Author: Geng Xun
Created: 2026-05-28
Last Modified: 2026-05-28
Updated: 2026-05-28  Geng Xun added focused coverage for parsing synthetic caminfo records and resolving same-directory cube paths.
Updated: 2026-05-28  Geng Xun aligned caminfo selector expectations with the approved Task 1 field names.
Updated: 2026-05-28  Geng Xun added Task 2 parser coverage for approved numeric metadata extraction and missing optional fields.
Updated: 2026-05-28  Geng Xun added Task 3 selection-rule evaluation coverage for approved range and center-distance matching.
Updated: 2026-05-28  Geng Xun aligned Task 3 tests with the approved selection criteria names and list-based evaluation reasons.
Updated: 2026-05-28  Geng Xun added Task 4 move-execution coverage for unresolved, dry-run, conflict, and successful move behaviors.
Updated: 2026-05-28  Geng Xun fixed Task 4 move tests to assert file-system effects before temporary directories are cleaned up.
Updated: 2026-05-28  Geng Xun aligned Task 4 move-result assertions with the approved plan field names and status strings.
Updated: 2026-05-28  Geng Xun added Task 5 CLI-flow coverage for argument validation, batched processing, and concise summary output.
Updated: 2026-05-28  Geng Xun added Task 5 failure-path coverage for invalid center distance input and robust batch file handling.
Updated: 2026-05-28  Geng Xun added Task 6 regression coverage for readable verbose per-entry diagnostics and unresolved move details.
Updated: 2026-05-28  Geng Xun added focused usage-helper coverage for example text generation and argparse help integration.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "examples" / "utility" / "select_isis_cubes.py"


def load_select_isis_cubes_module():
    if not SCRIPT_PATH.exists():
        raise AssertionError(f"Expected example script to exist: {SCRIPT_PATH}")

    spec = importlib.util.spec_from_file_location("select_isis_cubes", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module spec for {SCRIPT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


class SelectIsisCubesUnitTest(unittest.TestCase):
    def test_parse_caminfo_file_extracts_required_fields_and_resolves_cube_path(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            caminfo_path = temp_path / "example.caminfo.pvl"
            expected_cube_path = temp_path / "example_input.cub"
            expected_cube_path.write_text("synthetic cube placeholder\n", encoding="utf-8")
            caminfo_path.write_text(
                """
Object = Caminfo
  From = example_input.cub
  CenterLatitude = 12.5
  CenterLongitude = -45.25
  SubSolarAzimuth = 123.75
End_Object
End
""".strip()
                + "\n",
                encoding="utf-8",
            )

            record = module.parse_caminfo_file(caminfo_path)

        self.assertEqual(record.cube_name, "example_input.cub")
        self.assertEqual(record.cube_path, expected_cube_path)
        self.assertAlmostEqual(record.center_latitude, 12.5)
        self.assertAlmostEqual(record.center_longitude, -45.25)
        self.assertAlmostEqual(record.sub_solar_azimuth, 123.75)


class CaminfoParsingTest(unittest.TestCase):
    def test_parse_caminfo_file_extracts_approved_numeric_fields(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            caminfo_path = temp_path / "full_metadata.caminfo.pvl"
            expected_cube_path = temp_path / "full_metadata_input.cub"
            expected_cube_path.write_text("synthetic cube placeholder\n", encoding="utf-8")
            caminfo_path.write_text(
                """
Object = Caminfo
  From = full_metadata_input.cub
  CenterLatitude = 1.25
  CenterLongitude = -2.5
  MinimumLatitude = -11.5
  MaximumLatitude = 17.75
  MinimumLongitude = 88.125
  MaximumLongitude = 102.875
  IncidenceAngle = 43.5
  EmissionAngle = 21.25
  PhaseAngle = 64.75
  SubSolarAzimuth = 145.5
End_Object
End
""".strip()
                + "\n",
                encoding="utf-8",
            )

            record = module.parse_caminfo_file(caminfo_path)

        self.assertEqual(record.cube_name, "full_metadata_input.cub")
        self.assertEqual(record.cube_path, expected_cube_path)
        self.assertAlmostEqual(record.center_latitude, 1.25)
        self.assertAlmostEqual(record.center_longitude, -2.5)
        self.assertAlmostEqual(record.minimum_latitude, -11.5)
        self.assertAlmostEqual(record.maximum_latitude, 17.75)
        self.assertAlmostEqual(record.minimum_longitude, 88.125)
        self.assertAlmostEqual(record.maximum_longitude, 102.875)
        self.assertAlmostEqual(record.incidence, 43.5)
        self.assertAlmostEqual(record.emission, 21.25)
        self.assertAlmostEqual(record.phase, 64.75)
        self.assertAlmostEqual(record.sub_solar_azimuth, 145.5)

    def test_parse_caminfo_file_returns_none_for_missing_optional_approved_fields(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            caminfo_path = temp_path / "missing_optional.caminfo.pvl"
            expected_cube_path = temp_path / "missing_optional_input.cub"
            expected_cube_path.write_text("synthetic cube placeholder\n", encoding="utf-8")
            caminfo_path.write_text(
                """
Object = Caminfo
  From = missing_optional_input.cub
  CenterLatitude = -7.5
  CenterLongitude = 33.0
End_Object
End
""".strip()
                + "\n",
                encoding="utf-8",
            )

            record = module.parse_caminfo_file(caminfo_path)

        self.assertEqual(record.cube_name, "missing_optional_input.cub")
        self.assertEqual(record.cube_path, expected_cube_path)
        self.assertAlmostEqual(record.center_latitude, -7.5)
        self.assertAlmostEqual(record.center_longitude, 33.0)
        self.assertIsNone(record.minimum_latitude)
        self.assertIsNone(record.maximum_latitude)
        self.assertIsNone(record.minimum_longitude)
        self.assertIsNone(record.maximum_longitude)
        self.assertIsNone(record.incidence)
        self.assertIsNone(record.emission)
        self.assertIsNone(record.phase)
        self.assertIsNone(record.sub_solar_azimuth)


class SelectionRulesTest(unittest.TestCase):
    @staticmethod
    def _build_record(**overrides):
        module = load_select_isis_cubes_module()
        defaults = {
            "cube_name": "example.cub",
            "cube_path": Path("/tmp/example.cub"),
            "center_latitude": 10.0,
            "center_longitude": 20.0,
            "minimum_latitude": None,
            "maximum_latitude": None,
            "minimum_longitude": None,
            "maximum_longitude": None,
            "incidence": 30.0,
            "emission": 40.0,
            "phase": 50.0,
            "sub_solar_azimuth": 60.0,
        }
        defaults.update(overrides)
        return module.CaminfoRecord(**defaults)

    def test_evaluate_record_matches_when_all_approved_ranges_are_satisfied(self):
        module = load_select_isis_cubes_module()
        record = self._build_record()
        criteria = module.SelectionCriteria(
            min_latitude=9.5,
            max_latitude=10.5,
            min_longitude=19.5,
            max_longitude=20.5,
            min_incidence=29.0,
            max_incidence=31.0,
            min_emission=39.0,
            max_emission=41.0,
            min_phase=49.0,
            max_phase=51.0,
            min_sub_solar_azimuth=59.0,
            max_sub_solar_azimuth=61.0,
        )

        outcome = module.evaluate_record(record, criteria)

        self.assertTrue(outcome.matched)
        self.assertEqual(outcome.reasons, [])

    def test_evaluate_record_accumulates_all_enabled_range_failure_reasons(self):
        module = load_select_isis_cubes_module()
        record = self._build_record()
        criteria = module.SelectionCriteria(
            min_latitude=10.5,
            max_longitude=19.5,
            max_emission=39.5,
        )

        outcome = module.evaluate_record(record, criteria)

        self.assertFalse(outcome.matched)
        self.assertEqual(len(outcome.reasons), 3)
        self.assertTrue(any("latitude" in reason.lower() for reason in outcome.reasons))
        self.assertTrue(any("longitude" in reason.lower() for reason in outcome.reasons))
        self.assertTrue(any("emission" in reason.lower() for reason in outcome.reasons))
        self.assertTrue(any("10.5" in reason for reason in outcome.reasons))
        self.assertTrue(any("19.5" in reason for reason in outcome.reasons))
        self.assertTrue(any("39.5" in reason for reason in outcome.reasons))

    def test_evaluate_record_reports_missing_required_field_as_non_match(self):
        module = load_select_isis_cubes_module()
        record = self._build_record(incidence=None)
        criteria = module.SelectionCriteria(min_incidence=10.0)

        outcome = module.evaluate_record(record, criteria)

        self.assertFalse(outcome.matched)
        self.assertEqual(len(outcome.reasons), 1)
        self.assertIn("incidence", outcome.reasons[0].lower())
        self.assertIn("missing", outcome.reasons[0].lower())

    def test_evaluate_record_applies_center_distance_in_degree_space(self):
        module = load_select_isis_cubes_module()
        matching_record = self._build_record(center_latitude=11.0, center_longitude=21.0)
        matching_criteria = module.SelectionCriteria(
            center_latitude=10.0,
            center_longitude=20.0,
            max_center_distance_deg=1.5,
        )

        matching_outcome = module.evaluate_record(matching_record, matching_criteria)

        self.assertTrue(matching_outcome.matched)
        self.assertEqual(matching_outcome.reasons, [])

        non_matching_criteria = module.SelectionCriteria(
            center_latitude=10.0,
            center_longitude=20.0,
            max_center_distance_deg=1.0,
        )

        non_matching_outcome = module.evaluate_record(matching_record, non_matching_criteria)

        self.assertFalse(non_matching_outcome.matched)
        self.assertEqual(len(non_matching_outcome.reasons), 1)
        self.assertIn("center distance", non_matching_outcome.reasons[0].lower())
        self.assertIn("1.0", non_matching_outcome.reasons[0])


class MoveExecutionTest(unittest.TestCase):
    @staticmethod
    def _build_record(module, **overrides):
        defaults = {
            "cube_name": "example.cub",
            "cube_path": Path("/tmp/example.cub"),
            "center_latitude": 10.0,
            "center_longitude": 20.0,
            "minimum_latitude": None,
            "maximum_latitude": None,
            "minimum_longitude": None,
            "maximum_longitude": None,
            "incidence": 30.0,
            "emission": 40.0,
            "phase": 50.0,
            "sub_solar_azimuth": 60.0,
        }
        defaults.update(overrides)
        return module.CaminfoRecord(**defaults)

    def test_execute_move_returns_unresolved_when_cube_path_is_missing(self):
        module = load_select_isis_cubes_module()
        record = self._build_record(module, cube_name=None, cube_path=None)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "selected"

            result = module.execute_move(record, output_dir, dry_run=False)

        self.assertEqual(result.status, "unresolved")
        self.assertIsNone(result.source)
        self.assertIsNone(result.destination)
        self.assertIn("missing", result.detail.lower())
        self.assertIn("cube path", result.detail.lower())

    def test_execute_move_returns_unresolved_when_cube_path_is_absent_on_disk(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            missing_cube_path = temp_path / "missing_input.cub"
            output_dir = temp_path / "selected"
            record = self._build_record(module, cube_name=missing_cube_path.name, cube_path=missing_cube_path)

            result = module.execute_move(record, output_dir, dry_run=False)

        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.source, missing_cube_path)
        self.assertIsNone(result.destination)
        self.assertIn("does not exist", result.detail.lower())

    def test_execute_move_dry_run_does_not_move_file(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cube_path = temp_path / "dry_run_input.cub"
            cube_path.write_text("cube data\n", encoding="utf-8")
            output_dir = temp_path / "selected"
            record = self._build_record(module, cube_name=cube_path.name, cube_path=cube_path)

            result = module.execute_move(record, output_dir, dry_run=True)

            source_exists = cube_path.exists()
            destination_exists = (output_dir / cube_path.name).exists()

        self.assertEqual(result.status, "dry-run")
        self.assertEqual(result.source, cube_path)
        self.assertEqual(result.destination, output_dir / cube_path.name)
        self.assertTrue(source_exists)
        self.assertFalse(destination_exists)
        self.assertIn("dry-run", result.detail.lower())

    def test_execute_move_returns_destination_conflict_without_overwriting_existing_destination(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cube_path = temp_path / "conflict_input.cub"
            cube_path.write_text("source cube\n", encoding="utf-8")
            output_dir = temp_path / "selected"
            output_dir.mkdir()
            destination_path = output_dir / cube_path.name
            destination_path.write_text("existing cube\n", encoding="utf-8")
            record = self._build_record(module, cube_name=cube_path.name, cube_path=cube_path)

            result = module.execute_move(record, output_dir, dry_run=False)

            destination_contents = destination_path.read_text(encoding="utf-8")
            source_exists = cube_path.exists()

        self.assertEqual(result.status, "destination-conflict")
        self.assertEqual(result.source, cube_path)
        self.assertEqual(result.destination, destination_path)
        self.assertTrue(source_exists)
        self.assertEqual(destination_contents, "existing cube\n")
        self.assertIn("already exists", result.detail.lower())

    def test_execute_move_moves_file_and_creates_output_directory(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cube_path = temp_path / "move_input.cub"
            cube_path.write_text("cube payload\n", encoding="utf-8")
            output_dir = temp_path / "nested" / "selected"
            destination_path = output_dir / cube_path.name
            record = self._build_record(module, cube_name=cube_path.name, cube_path=cube_path)

            result = module.execute_move(record, output_dir, dry_run=False)

            moved_contents = destination_path.read_text(encoding="utf-8")
            source_exists = cube_path.exists()
            output_dir_exists = output_dir.exists()

        self.assertEqual(result.status, "moved")
        self.assertEqual(result.source, cube_path)
        self.assertEqual(result.destination, destination_path)
        self.assertFalse(source_exists)
        self.assertTrue(output_dir_exists)
        self.assertEqual(moved_contents, "cube payload\n")
        self.assertIn("moved", result.detail.lower())


class CliFlowTest(unittest.TestCase):
    def test_parse_args_reads_approved_cli_surface(self):
        module = load_select_isis_cubes_module()

        args = module.parse_args(
            [
                "--caminfo-list",
                "caminfo_files.txt",
                "--output-dir",
                "selected",
                "--dry-run",
                "--verbose",
                "--center-latitude",
                "10.5",
                "--center-longitude",
                "20.5",
                "--max-center-distance-deg",
                "2.5",
                "--min-latitude",
                "-5",
                "--max-latitude",
                "15",
                "--min-incidence",
                "30",
                "--max-incidence",
                "70",
            ]
        )

        self.assertEqual(args.caminfo_list, Path("caminfo_files.txt"))
        self.assertEqual(args.output_dir, Path("selected"))
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verbose)
        self.assertEqual(args.center_latitude, 10.5)
        self.assertEqual(args.center_longitude, 20.5)
        self.assertEqual(args.max_center_distance_deg, 2.5)
        self.assertEqual(args.min_latitude, -5.0)
        self.assertEqual(args.max_latitude, 15.0)
        self.assertEqual(args.min_incidence, 30.0)
        self.assertEqual(args.max_incidence, 70.0)

    def test_build_criteria_rejects_incomplete_center_distance_input(self):
        module = load_select_isis_cubes_module()
        args = argparse.Namespace(
            center_latitude=10.0,
            center_longitude=None,
            max_center_distance_deg=2.0,
            min_latitude=None,
            max_latitude=None,
            min_longitude=None,
            max_longitude=None,
            min_incidence=None,
            max_incidence=None,
            min_emission=None,
            max_emission=None,
            min_phase=None,
            max_phase=None,
            min_sub_solar_azimuth=None,
            max_sub_solar_azimuth=None,
        )

        with self.assertRaisesRegex(ValueError, "center distance"):
            module.build_criteria(args)

    def test_build_criteria_rejects_invalid_min_max_pair(self):
        module = load_select_isis_cubes_module()
        args = argparse.Namespace(
            center_latitude=None,
            center_longitude=None,
            max_center_distance_deg=None,
            min_latitude=20.0,
            max_latitude=10.0,
            min_longitude=None,
            max_longitude=None,
            min_incidence=None,
            max_incidence=None,
            min_emission=None,
            max_emission=None,
            min_phase=None,
            max_phase=None,
            min_sub_solar_azimuth=None,
            max_sub_solar_azimuth=None,
        )

        with self.assertRaisesRegex(ValueError, "latitude"):
            module.build_criteria(args)

    def test_build_criteria_rejects_negative_max_center_distance(self):
        module = load_select_isis_cubes_module()
        args = argparse.Namespace(
            center_latitude=10.0,
            center_longitude=20.0,
            max_center_distance_deg=-0.5,
            min_latitude=None,
            max_latitude=None,
            min_longitude=None,
            max_longitude=None,
            min_incidence=None,
            max_incidence=None,
            min_emission=None,
            max_emission=None,
            min_phase=None,
            max_phase=None,
            min_sub_solar_azimuth=None,
            max_sub_solar_azimuth=None,
        )

        with self.assertRaisesRegex(ValueError, "max-center-distance-deg"):
            module.build_criteria(args)

    def test_main_dry_run_processes_caminfo_batch_and_prints_concise_summary(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            caminfo_list_path = temp_path / "caminfo_list.txt"
            caminfo_a = temp_path / "a.caminfo"
            caminfo_b = temp_path / "b.caminfo"
            caminfo_c = temp_path / "c.caminfo"
            for caminfo_path in (caminfo_a, caminfo_b, caminfo_c):
                caminfo_path.write_text("placeholder\n", encoding="utf-8")

            caminfo_list_path.write_text(
                f"{caminfo_a}\n\n{caminfo_b}\n{caminfo_c}\n",
                encoding="utf-8",
            )
            output_dir = temp_path / "selected"
            criteria = module.SelectionCriteria(min_incidence=10.0)
            record_a = module.CaminfoRecord(
                cube_name="a.cub",
                cube_path=temp_path / "a.cub",
                center_latitude=1.0,
                center_longitude=2.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=12.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )
            record_b = module.CaminfoRecord(
                cube_name="b.cub",
                cube_path=temp_path / "b.cub",
                center_latitude=3.0,
                center_longitude=4.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=8.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )
            record_c = module.CaminfoRecord(
                cube_name="c.cub",
                cube_path=temp_path / "c.cub",
                center_latitude=5.0,
                center_longitude=6.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=18.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )

            parse_side_effect = [record_a, record_b, record_c]
            evaluate_side_effect = [
                module.EvaluationOutcome(matched=True, reasons=[]),
                module.EvaluationOutcome(matched=False, reasons=["incidence 8.0 is below minimum 10.0."]),
                module.EvaluationOutcome(matched=True, reasons=[]),
            ]
            move_side_effect = [
                module.MoveResult(
                    status="dry-run",
                    source=record_a.cube_path,
                    destination=output_dir / "a.cub",
                    detail="Dry-run only; cube would be moved.",
                ),
                module.MoveResult(
                    status="unresolved",
                    source=record_c.cube_path,
                    destination=None,
                    detail="Cannot move cube because source path does not exist.",
                ),
            ]

            stdout_buffer = io.StringIO()
            with mock.patch.object(module, "build_criteria", return_value=criteria) as build_criteria_mock, mock.patch.object(
                module, "parse_caminfo_file", side_effect=parse_side_effect
            ) as parse_mock, mock.patch.object(
                module, "evaluate_record", side_effect=evaluate_side_effect
            ) as evaluate_mock, mock.patch.object(
                module, "execute_move", side_effect=move_side_effect
            ) as move_mock, redirect_stdout(stdout_buffer):
                exit_code = module.main(
                    [
                        "--caminfo-list",
                        str(caminfo_list_path),
                        "--output-dir",
                        str(output_dir),
                        "--dry-run",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(build_criteria_mock.call_count, 1)
        self.assertEqual(parse_mock.call_count, 3)
        self.assertEqual(evaluate_mock.call_count, 3)
        self.assertEqual(move_mock.call_count, 2)
        self.assertEqual([call.args[0] for call in parse_mock.call_args_list], [caminfo_a, caminfo_b, caminfo_c])
        self.assertEqual([call.args[0] for call in evaluate_mock.call_args_list], [record_a, record_b, record_c])
        self.assertTrue(all(call.args[1] == criteria for call in evaluate_mock.call_args_list))
        self.assertEqual([call.args[0] for call in move_mock.call_args_list], [record_a, record_c])
        self.assertTrue(all(call.args[1] == output_dir for call in move_mock.call_args_list))
        self.assertTrue(all(call.args[2] is True for call in move_mock.call_args_list))

        output = stdout_buffer.getvalue()
        self.assertIn("Processed 3 caminfo files.", output)
        self.assertIn("Matched 2.", output)
        self.assertIn("Skipped 1.", output)
        self.assertIn("Dry-run moves 1.", output)
        self.assertIn("Unresolved moves 1.", output)
        self.assertNotIn("a.caminfo", output)
        self.assertNotIn("b.caminfo", output)

    def test_main_verbose_reports_readable_per_entry_diagnostics(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            caminfo_list_path = temp_path / "caminfo_list.txt"
            caminfo_a = temp_path / "a.caminfo"
            caminfo_b = temp_path / "b.caminfo"
            caminfo_c = temp_path / "c.caminfo"
            caminfo_d = temp_path / "d.caminfo"
            for caminfo_path in (caminfo_a, caminfo_b, caminfo_c, caminfo_d):
                caminfo_path.write_text("placeholder\n", encoding="utf-8")

            caminfo_list_path.write_text(
                f"{caminfo_a}\n{caminfo_b}\n{caminfo_c}\n{caminfo_d}\n",
                encoding="utf-8",
            )
            output_dir = temp_path / "selected"
            criteria = module.SelectionCriteria(min_incidence=10.0)
            record_a = module.CaminfoRecord(
                cube_name="a.cub",
                cube_path=temp_path / "a.cub",
                center_latitude=1.0,
                center_longitude=2.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=12.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )
            record_b = module.CaminfoRecord(
                cube_name="b.cub",
                cube_path=temp_path / "b.cub",
                center_latitude=3.0,
                center_longitude=4.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=8.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )
            record_c = module.CaminfoRecord(
                cube_name="c.cub",
                cube_path=temp_path / "missing.cub",
                center_latitude=5.0,
                center_longitude=6.0,
                minimum_latitude=None,
                maximum_latitude=None,
                minimum_longitude=None,
                maximum_longitude=None,
                incidence=18.0,
                emission=20.0,
                phase=30.0,
                sub_solar_azimuth=40.0,
            )

            parse_side_effect = [
                record_a,
                record_b,
                record_c,
                OSError("synthetic parse failure"),
            ]
            evaluate_side_effect = [
                module.EvaluationOutcome(matched=True, reasons=[]),
                module.EvaluationOutcome(matched=False, reasons=["incidence 8.0 is below minimum 10.0."]),
                module.EvaluationOutcome(matched=True, reasons=[]),
            ]
            move_side_effect = [
                module.MoveResult(
                    status="dry-run",
                    source=record_a.cube_path,
                    destination=output_dir / "a.cub",
                    detail="Dry-run only; cube would be moved to selected/a.cub",
                ),
                module.MoveResult(
                    status="unresolved",
                    source=record_c.cube_path,
                    destination=None,
                    detail="Cannot move cube because source path does not exist.",
                ),
            ]

            stdout_buffer = io.StringIO()
            with mock.patch.object(module, "build_criteria", return_value=criteria), mock.patch.object(
                module, "parse_caminfo_file", side_effect=parse_side_effect
            ), mock.patch.object(
                module, "evaluate_record", side_effect=evaluate_side_effect
            ), mock.patch.object(
                module, "execute_move", side_effect=move_side_effect
            ), redirect_stdout(stdout_buffer):
                exit_code = module.main(
                    [
                        "--caminfo-list",
                        str(caminfo_list_path),
                        "--output-dir",
                        str(output_dir),
                        "--dry-run",
                        "--verbose",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout_buffer.getvalue()
        self.assertIn(
            f"MATCH {caminfo_a} -> a.cub [dry-run]: Dry-run only; cube would be moved to selected/a.cub",
            output,
        )
        self.assertIn(
            f"SKIP {caminfo_b}: incidence 8.0 is below minimum 10.0.",
            output,
        )
        self.assertIn(
            f"MATCH {caminfo_c} -> c.cub [unresolved]: Cannot move cube because source path does not exist.",
            output,
        )
        self.assertIn(
            f"PARSE-FAIL {caminfo_d}: synthetic parse failure",
            output,
        )
        self.assertIn("Processed 4 caminfo files.", output)
        self.assertIn("Matched 2.", output)
        self.assertIn("Skipped 1.", output)
        self.assertIn("Parse failures 1.", output)
        self.assertIn("Dry-run moves 1.", output)
        self.assertIn("Unresolved moves 1.", output)

    def test_main_returns_error_without_traceback_when_caminfo_list_is_unreadable(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            missing_list_path = temp_path / "missing_list.txt"
            output_dir = temp_path / "selected"
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    [
                        "--caminfo-list",
                        str(missing_list_path),
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout_buffer.getvalue(), "")
        error_output = stderr_buffer.getvalue()
        self.assertIn("Error:", error_output)
        self.assertIn("caminfo list", error_output)
        self.assertIn(str(missing_list_path), error_output)
        self.assertNotIn("Traceback", error_output)

    def test_main_continues_after_missing_caminfo_file_and_reports_parse_failures(self):
        module = load_select_isis_cubes_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            missing_caminfo_path = temp_path / "missing.caminfo"
            valid_caminfo_path = temp_path / "valid.caminfo"
            valid_cube_path = temp_path / "valid.cub"
            valid_cube_path.write_text("cube data\n", encoding="utf-8")
            valid_caminfo_path.write_text(
                f"""
Object = Caminfo
  From = {valid_cube_path.name}
  CenterLatitude = 1.0
  CenterLongitude = 2.0
  IncidenceAngle = 12.0
End_Object
End
""".strip()
                + "\n",
                encoding="utf-8",
            )
            caminfo_list_path = temp_path / "caminfo_list.txt"
            caminfo_list_path.write_text(
                f"{missing_caminfo_path}\n{valid_caminfo_path}\n",
                encoding="utf-8",
            )
            output_dir = temp_path / "selected"
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    [
                        "--caminfo-list",
                        str(caminfo_list_path),
                        "--output-dir",
                        str(output_dir),
                        "--dry-run",
                        "--min-incidence",
                        "10",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        output = stdout_buffer.getvalue()
        self.assertIn("Processed 2 caminfo files.", output)
        self.assertIn("Matched 1.", output)
        self.assertIn("Skipped 0.", output)
        self.assertIn("Parse failures 1.", output)
        self.assertIn("Dry-run moves 1.", output)
        self.assertNotIn("Traceback", output)


class UsageHelperTest(unittest.TestCase):
    def test_build_usage_examples_returns_examples_block_with_public_flags(self):
        module = load_select_isis_cubes_module()

        examples_text = module.build_usage_examples()

        self.assertIn("Examples:", examples_text)
        self.assertIn("--caminfo-list", examples_text)
        self.assertIn("--output-dir", examples_text)
        self.assertIn("--dry-run", examples_text)
        self.assertTrue(
            "--min-sub-solar-azimuth" in examples_text
            or "--max-sub-solar-azimuth" in examples_text
        )

    def test_parse_args_help_includes_usage_examples_block(self):
        module = load_select_isis_cubes_module()
        stdout_buffer = io.StringIO()

        with self.assertRaises(SystemExit) as context:
            with redirect_stdout(stdout_buffer):
                module.parse_args(["--help"])

        self.assertEqual(context.exception.code, 0)
        help_text = stdout_buffer.getvalue()
        self.assertIn("Examples:", help_text)
        self.assertIn("--dry-run", help_text)
        self.assertIn("--min-sub-solar-azimuth", help_text)


if __name__ == "__main__":
    unittest.main()
