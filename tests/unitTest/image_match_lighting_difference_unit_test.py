"""Unit tests for solar lighting-difference helpers.

Author: Geng Xun
Created: 2026-05-18
Last Modified: 2026-05-18
Updated: 2026-05-18  Geng Xun added focused coverage for azimuth-wrap difference,
    elevation/azimuth-only fallback weighting, missing-field error handling, and
    cube-label keyword resolution with mission fallbacks.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.lighting_difference import (  # noqa: E402  (sys.path manipulated above)
    SolarGeometry,
    SolarGeometryFieldMissing,
    azimuth_difference_degrees,
    compute_lighting_difference,
    read_solar_geometry_from_cube,
)


class _FakePvlGroup:
    def __init__(self, keywords: dict[str, object]):
        self._keywords = keywords

    def has_keyword(self, name: str) -> bool:
        return name in self._keywords

    def find_keyword(self, name: str):
        return self._keywords[name]


class _FakeCube:
    def __init__(self, groups: dict[str, _FakePvlGroup]):
        self._groups = groups

    def has_group(self, name: str) -> bool:
        return name in self._groups

    def group(self, name: str) -> _FakePvlGroup:
        return self._groups[name]


class ImageMatchLightingDifferenceUnitTest(unittest.TestCase):
    def test_azimuth_difference_handles_wrap(self):
        self.assertAlmostEqual(azimuth_difference_degrees(350.0, 10.0), 20.0)
        self.assertAlmostEqual(azimuth_difference_degrees(10.0, 350.0), 20.0)
        self.assertAlmostEqual(azimuth_difference_degrees(45.0, 225.0), 180.0)
        self.assertAlmostEqual(azimuth_difference_degrees(720.0 + 30.0, 360.0 + 20.0), 10.0)
        self.assertAlmostEqual(azimuth_difference_degrees(15.0, 15.0), 0.0)

    def test_compute_lighting_difference_weights_normalized_components(self):
        left = SolarGeometry(
            solar_elevation_degrees=30.0,
            solar_azimuth_degrees=10.0,
            source_group_name="Instrument",
            elevation_keyword="SolarElevation",
            azimuth_keyword="SolarAzimuth",
        )
        right = SolarGeometry(
            solar_elevation_degrees=60.0,
            solar_azimuth_degrees=190.0,
            source_group_name="Instrument",
            elevation_keyword="SolarElevation",
            azimuth_keyword="SolarAzimuth",
        )

        summary = compute_lighting_difference(left, right)

        self.assertAlmostEqual(summary.elevation_difference_degrees, 30.0)
        self.assertAlmostEqual(summary.azimuth_difference_degrees, 180.0)
        self.assertAlmostEqual(summary.normalized_elevation_difference, 30.0 / 90.0)
        self.assertAlmostEqual(summary.normalized_azimuth_difference, 1.0)
        # azimuth contribution dominates because azimuth has the larger default weight.
        self.assertGreaterEqual(summary.lighting_difference_score, 0.5)

    def test_compute_lighting_difference_falls_back_when_one_field_missing(self):
        left = SolarGeometry(
            solar_elevation_degrees=30.0,
            solar_azimuth_degrees=None,
            source_group_name="Instrument",
            elevation_keyword="SolarElevation",
            azimuth_keyword=None,
        )
        right = SolarGeometry(
            solar_elevation_degrees=90.0,
            solar_azimuth_degrees=None,
            source_group_name="Instrument",
            elevation_keyword="SolarElevation",
            azimuth_keyword=None,
        )

        summary = compute_lighting_difference(left, right)

        self.assertIsNone(summary.azimuth_difference_degrees)
        self.assertAlmostEqual(summary.elevation_difference_degrees, 60.0)
        self.assertAlmostEqual(summary.lighting_difference_score, 60.0 / 90.0)
        self.assertIn("elevation-only", summary.reason)

    def test_compute_lighting_difference_reports_when_no_components(self):
        empty_geometry = SolarGeometry(
            solar_elevation_degrees=None,
            solar_azimuth_degrees=None,
            source_group_name=None,
            elevation_keyword=None,
            azimuth_keyword=None,
        )

        summary = compute_lighting_difference(empty_geometry, empty_geometry)

        self.assertIsNone(summary.lighting_difference_score)
        self.assertIn("unavailable", summary.reason)

    def test_read_solar_geometry_resolves_first_matching_keyword(self):
        cube = _FakeCube(
            {
                "Instrument": _FakePvlGroup(
                    {
                        "SolarElevation": [35.5],
                        "SubSolarAzimuth": [120.25],
                    }
                ),
            }
        )

        geometry = read_solar_geometry_from_cube(cube)

        self.assertAlmostEqual(geometry.solar_elevation_degrees, 35.5)
        self.assertAlmostEqual(geometry.solar_azimuth_degrees, 120.25)
        self.assertEqual(geometry.elevation_keyword, "SolarElevation")
        self.assertEqual(geometry.azimuth_keyword, "SubSolarAzimuth")
        self.assertEqual(geometry.source_group_name, "Instrument")

    def test_read_solar_geometry_raises_when_all_groups_missing(self):
        cube = _FakeCube({"Mapping": _FakePvlGroup({"CenterLatitude": [0.0]})})

        with self.assertRaises(SolarGeometryFieldMissing):
            read_solar_geometry_from_cube(cube)

    def test_read_solar_geometry_returns_partial_when_only_one_field_present(self):
        cube = _FakeCube(
            {
                "Instrument": _FakePvlGroup({"SolarAzimuth": ["75.0"]}),
            }
        )

        geometry = read_solar_geometry_from_cube(cube)

        self.assertIsNone(geometry.solar_elevation_degrees)
        self.assertAlmostEqual(geometry.solar_azimuth_degrees, 75.0)
        self.assertEqual(geometry.azimuth_keyword, "SolarAzimuth")


if __name__ == "__main__":
    unittest.main()
