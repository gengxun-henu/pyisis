"""Unit tests for the high-level pyisis Python facade.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added facade API coverage for runtime configuration, cube context management, and camera helpers.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest import mock
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PYTHON_DIR = PROJECT_ROOT / "python"
if str(SOURCE_PYTHON_DIR) not in sys.path:
    sys.path.append(str(SOURCE_PYTHON_DIR))


class PyisisFacadeUnitTest(unittest.TestCase):
    def setUp(self):
        import pyisis

        self.pyisis = pyisis
        self.camera_cube = PROJECT_ROOT / "tests" / "data" / "mosrange" / "EN0108828322M_iof.cub"

    def test_configure_sets_runtime_environment_and_returns_config(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = self.pyisis.configure(
                isis_prefix=r"C:\isis-prefix",
                isisdata=r"C:\isisdata",
                conda_prefix=r"C:\conda-env",
            )

            self.assertEqual(os.environ["ISIS_PREFIX"], r"C:\isis-prefix")
            self.assertEqual(os.environ["ISISROOT"], r"C:\isis-prefix")
            self.assertEqual(os.environ["ISISDATA"], r"C:\isisdata")
            self.assertEqual(os.environ["CONDA_PREFIX"], r"C:\conda-env")
            self.assertEqual(config.isis_prefix, r"C:\isis-prefix")
            self.assertEqual(config.isisroot, r"C:\isis-prefix")
            self.assertEqual(config.isisdata, r"C:\isisdata")
            self.assertEqual(config.conda_prefix, r"C:\conda-env")

    def test_low_level_symbols_are_available_through_lazy_facade(self):
        self.assertIs(self.pyisis.Cube, self.pyisis.core().Cube)

    def test_open_cube_context_manager_returns_open_cube(self):
        with self.pyisis.open_cube(self.camera_cube) as cube:
            self.assertEqual(cube.sample_count(), 1024)
            self.assertEqual(cube.line_count(), 1024)
            self.assertEqual(cube.band_count(), 1)

    def test_cube_dimensions_accepts_path_or_open_cube(self):
        from_path = self.pyisis.cube_dimensions(self.camera_cube)
        self.assertEqual((from_path.samples, from_path.lines, from_path.bands), (1024, 1024, 1))

        with self.pyisis.open_cube(self.camera_cube) as cube:
            from_cube = self.pyisis.cube_dimensions(cube)
        self.assertEqual(from_cube, from_path)

    def test_ground_at_center_returns_camera_latitude_and_longitude(self):
        ground = self.pyisis.ground_at_center(self.camera_cube)

        self.assertAlmostEqual(ground.latitude, -15.260663718130933, places=8)
        self.assertAlmostEqual(ground.longitude, 140.41008503563984, places=8)
        self.assertGreater(ground.radius_meters, 0.0)


if __name__ == "__main__":
    unittest.main()
