"""
Unit tests for caminfo-based ISIS cube selection helpers.

Author: Geng Xun
Created: 2026-05-28
Last Modified: 2026-05-28
Updated: 2026-05-28  Geng Xun added focused coverage for parsing synthetic caminfo records and resolving same-directory cube paths.
Updated: 2026-05-28  Geng Xun aligned caminfo selector expectations with the approved Task 1 field names.
Updated: 2026-05-28  Geng Xun added Task 2 parser coverage for approved numeric metadata extraction and missing optional fields.
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


if __name__ == "__main__":
    unittest.main()
