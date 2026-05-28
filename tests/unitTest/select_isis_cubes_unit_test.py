"""
Unit tests for caminfo-based ISIS cube selection helpers.

Author: Geng Xun
Created: 2026-05-28
Last Modified: 2026-05-28
Updated: 2026-05-28  Geng Xun added focused coverage for parsing synthetic caminfo records and resolving same-directory cube paths.
Updated: 2026-05-28  Geng Xun aligned caminfo selector expectations with the approved Task 1 field names.
Updated: 2026-05-28  Geng Xun added Task 2 parser coverage for approved numeric metadata extraction and missing optional fields.
Updated: 2026-05-28  Geng Xun added Task 3 selection-rule evaluation coverage for approved range and center-distance matching.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


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
            latitude_min=9.5,
            latitude_max=10.5,
            longitude_min=19.5,
            longitude_max=20.5,
            incidence_min=29.0,
            incidence_max=31.0,
            emission_min=39.0,
            emission_max=41.0,
            phase_min=49.0,
            phase_max=51.0,
            sub_solar_azimuth_min=59.0,
            sub_solar_azimuth_max=61.0,
        )

        outcome = module.evaluate_record(record, criteria)

        self.assertTrue(outcome.is_match)
        self.assertIn("matched", outcome.reason.lower())

    def test_evaluate_record_uses_and_composition_for_range_rules(self):
        module = load_select_isis_cubes_module()
        record = self._build_record()
        criteria = module.SelectionCriteria(
            latitude_min=9.5,
            latitude_max=10.5,
            longitude_min=19.5,
            longitude_max=20.5,
            incidence_min=29.0,
            incidence_max=31.0,
            emission_min=39.0,
            emission_max=39.5,
        )

        outcome = module.evaluate_record(record, criteria)

        self.assertFalse(outcome.is_match)
        self.assertIn("emission", outcome.reason.lower())
        self.assertIn("39.5", outcome.reason)

    def test_evaluate_record_reports_missing_required_field_as_non_match(self):
        module = load_select_isis_cubes_module()
        record = self._build_record(incidence=None)
        criteria = module.SelectionCriteria(incidence_min=10.0)

        outcome = module.evaluate_record(record, criteria)

        self.assertFalse(outcome.is_match)
        self.assertIn("incidence", outcome.reason.lower())
        self.assertIn("missing", outcome.reason.lower())

    def test_evaluate_record_applies_center_distance_in_degree_space(self):
        module = load_select_isis_cubes_module()
        matching_record = self._build_record(center_latitude=11.0, center_longitude=21.0)
        matching_criteria = module.SelectionCriteria(
            center_latitude=10.0,
            center_longitude=20.0,
            center_distance_max=1.5,
        )

        matching_outcome = module.evaluate_record(matching_record, matching_criteria)

        self.assertTrue(matching_outcome.is_match)
        self.assertIn("matched", matching_outcome.reason.lower())

        non_matching_criteria = module.SelectionCriteria(
            center_latitude=10.0,
            center_longitude=20.0,
            center_distance_max=1.0,
        )

        non_matching_outcome = module.evaluate_record(matching_record, non_matching_criteria)

        self.assertFalse(non_matching_outcome.is_match)
        self.assertIn("center distance", non_matching_outcome.reason.lower())
        self.assertIn("1.0", non_matching_outcome.reason)


if __name__ == "__main__":
    unittest.main()
