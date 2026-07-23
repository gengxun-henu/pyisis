"""Unit tests for the ISIS 10-only binding surface.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun covered version-gated IProj and Chandrayaan-2 camera exports.
"""

from __future__ import annotations

import unittest

import isis_pybind as ip


class Isis10ApiUnitTest(unittest.TestCase):
    """Verify the first ISIS 10-only non-GUI binding batch."""

    def test_exports_match_runtime_major(self):
        symbols = (
            "IProj",
            "Chandrayaan2OhrcCamera",
            "Chandrayaan2TmcCamera",
        )

        for symbol in symbols:
            with self.subTest(symbol=symbol):
                self.assertEqual(hasattr(ip, symbol), ip.__isis_major__ >= 10)
                self.assertEqual(symbol in ip.__all__, ip.__isis_major__ >= 10)

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_iproj_projection_methods(self):
        label = ip.Pvl()
        label.from_string(
            """
Group = Mapping
  TargetName = Mars
  ProjStr = "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=-90 +over +x_0=0 +y_0=0 +R=1 +units=m +no_defs +type=crs"
  LatitudeType = Planetocentric
  LongitudeDirection = PositiveEast
  LongitudeDomain = 180
  EquatorialRadius = 1
  PolarRadius = 1
  MinimumLatitude = -90.0
  MaximumLatitude = 90.0
  MinimumLongitude = -180
  MaximumLongitude = 180
End_Group
End
"""
        )

        projection = ip.IProj(label)
        self.assertEqual(projection.name(), "Proj")
        self.assertEqual(projection.version(), "1.0")
        self.assertTrue(projection.set_ground(-50.0, -75.0))
        self.assertTrue(projection.set_coordinate(0.26179938779914935, -0.87266462599716477))
        self.assertEqual(len(projection.xy_range()), 4)
        self.assertEqual(projection.mapping().name(), "Mapping")

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_chandrayaan2_camera_types_use_line_scan_base(self):
        self.assertTrue(issubclass(ip.Chandrayaan2OhrcCamera, ip.LineScanCamera))
        self.assertTrue(issubclass(ip.Chandrayaan2TmcCamera, ip.LineScanCamera))


if __name__ == "__main__":
    unittest.main()
