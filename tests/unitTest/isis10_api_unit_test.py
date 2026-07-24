"""Unit tests for the ISIS 10-only binding surface.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-24
Updated: 2026-07-23  Geng Xun covered version-gated IProj and Chandrayaan-2 camera exports.
Updated: 2026-07-24  Geng Xun covered the ISIS 10-only OCAMS OpenCV distortion model.
Updated: 2026-07-24  Geng Xun covered safe ISIS 10 ImageIoHandler and GdalIoHandler exports.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import isis_pybind as ip

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class Isis10ApiUnitTest(unittest.TestCase):
    """Verify the first ISIS 10-only non-GUI binding batch."""

    def test_exports_match_runtime_major(self):
        symbols = (
            "IProj",
            "Chandrayaan2OhrcCamera",
            "Chandrayaan2TmcCamera",
            "GdalIoHandler",
            "ImageIoHandler",
            "OsirisRexOcamsOpenCVDistortionMap",
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

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_ocams_opencv_distortion_map_surface(self):
        distortion_type = ip.OsirisRexOcamsOpenCVDistortionMap
        self.assertTrue(issubclass(distortion_type, ip.CameraDistortionMap))
        self.assertTrue(hasattr(distortion_type, "set_camera_temperature"))
        self.assertTrue(hasattr(distortion_type, "set_focal_plane"))
        self.assertTrue(
            hasattr(distortion_type, "set_undistorted_focal_plane")
        )

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_ocams_opencv_distortion_map_rejects_null_parent(self):
        with self.assertRaisesRegex(ValueError, "valid Camera"):
            ip.OsirisRexOcamsOpenCVDistortionMap(None, -64360, 0)

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_gdal_io_handler_reads_tiff_through_abstract_base(self):
        image_path = DATA_DIR / "stdFormatImages" / "grayscale.tif"
        handler = ip.GdalIoHandler(
            str(image_path),
            pixel_type=ip.PixelType.UnsignedByte,
        )

        self.assertIsInstance(handler, ip.ImageIoHandler)
        brick = ip.Brick(2, 2, 1, ip.PixelType.UnsignedByte)
        brick.set_base_position(1, 1, 1)
        handler.read(brick)

        self.assertEqual(len(brick.double_buffer()), 4)
        self.assertTrue(any(value >= 0.0 for value in brick.double_buffer()))

        labels = ip.Pvl()
        labels.from_string(
            """
Object = IsisCube
  Object = Core
  End_Object
End_Object
End
"""
        )
        handler.update_labels(labels)
        core = labels.find_object("IsisCube").find_object("Core")
        self.assertEqual(core.find_keyword("Format")[0], "GTiff")
        handler.clear_cache()

    @unittest.skipUnless(ip.__isis_major__ >= 10, "ISIS 10-only API")
    def test_gdal_io_handler_validates_path_and_virtual_bands(self):
        image_path = DATA_DIR / "stdFormatImages" / "grayscale.tif"

        with self.assertRaisesRegex(ValueError, "existing file"):
            ip.GdalIoHandler(str(image_path.with_name("missing.tif")))

        with self.assertRaisesRegex(ValueError, "band range"):
            ip.GdalIoHandler(str(image_path), virtual_bands=[2])


if __name__ == "__main__":
    unittest.main()
