"""
Unit tests for caminfo-based ISIS cube selection helpers.

Author: Geng Xun
Created: 2026-05-28
Last Modified: 2026-05-28
Updated: 2026-05-28  Geng Xun added focused coverage for parsing synthetic caminfo records and resolving same-directory cube paths.
Updated: 2026-05-28  Geng Xun aligned caminfo selector expectations with the approved Task 1 field names.
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


if __name__ == "__main__":
    unittest.main()
