"""
Unit tests for Batch 2 ISIS bindings:
ImageOverlap, HiLab, PixelFOV, PushFrameCameraCcdLayout, CameraStatistics.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import isis_pybind as ip


class ImageOverlapUnitTest(unittest.TestCase):
    """Unit tests for ImageOverlap binding. Added: 2026-04-10."""

    def test_construction_default(self):
        """ImageOverlap constructs with default constructor."""
        overlap = ip.ImageOverlap()
        self.assertIsInstance(overlap, ip.ImageOverlap)

    def test_initial_size_zero(self):
        """New ImageOverlap has no serial numbers (size=0)."""
        overlap = ip.ImageOverlap()
        self.assertEqual(overlap.size(), 0)

    def test_len_zero(self):
        """len(ImageOverlap) is 0 for empty overlap."""
        overlap = ip.ImageOverlap()
        self.assertEqual(len(overlap), 0)

    def test_add_serial_number(self):
        """add() increases size by 1."""
        overlap = ip.ImageOverlap()
        overlap.add("TestSN001")
        self.assertEqual(overlap.size(), 1)

    def test_add_multiple_serial_numbers(self):
        """Adding multiple serial numbers increments size correctly."""
        overlap = ip.ImageOverlap()
        overlap.add("SN001")
        overlap.add("SN002")
        overlap.add("SN003")
        self.assertEqual(overlap.size(), 3)

    def test_getitem_serial_number(self):
        """operator[] returns the correct serial number by index."""
        overlap = ip.ImageOverlap()
        overlap.add("SN001")
        overlap.add("SN002")
        self.assertEqual(overlap[0], "SN001")
        self.assertEqual(overlap[1], "SN002")

    def test_getitem_out_of_range(self):
        """operator[] raises IndexError for out-of-range index."""
        overlap = ip.ImageOverlap()
        with self.assertRaises(IndexError):
            _ = overlap[0]

    def test_has_serial_number_true(self):
        """has_serial_number() returns True when serial number is present."""
        overlap = ip.ImageOverlap()
        overlap.add("SN001")
        self.assertTrue(overlap.has_serial_number("SN001"))

    def test_has_serial_number_false(self):
        """has_serial_number() returns False when serial number is absent."""
        overlap = ip.ImageOverlap()
        overlap.add("SN001")
        self.assertFalse(overlap.has_serial_number("MISSING"))

    def test_has_any_same_serial_number_true(self):
        """has_any_same_serial_number() returns True when overlaps share serial numbers."""
        a = ip.ImageOverlap()
        a.add("SN001")
        a.add("SN002")
        b = ip.ImageOverlap()
        b.add("SN002")
        b.add("SN003")
        self.assertTrue(a.has_any_same_serial_number(b))

    def test_has_any_same_serial_number_false(self):
        """has_any_same_serial_number() returns False when no shared serial numbers."""
        a = ip.ImageOverlap()
        a.add("SN001")
        b = ip.ImageOverlap()
        b.add("SN999")
        self.assertFalse(a.has_any_same_serial_number(b))

    def test_area_no_polygon(self):
        """area() returns 0.0 when no polygon is set."""
        overlap = ip.ImageOverlap()
        self.assertAlmostEqual(overlap.area(), 0.0)

    def test_repr(self):
        """repr(ImageOverlap) contains 'ImageOverlap'."""
        overlap = ip.ImageOverlap()
        overlap.add("SN001")
        r = repr(overlap)
        self.assertIn("ImageOverlap", r)


class HiLabUnitTest(unittest.TestCase):
    """Unit tests for HiLab binding. Added: 2026-04-10.

    HiLab requires an open HiRise Cube with an Instrument group containing
    CpmmNumber, ChannelNumber, Summing, and Tdi keywords. These tests verify
    the class is importable and that the constructor is accessible.
    Runtime tests that need a real HiRise cube are skipped.
    """

    def test_class_exists(self):
        """HiLab is importable as isis_pybind.HiLab."""
        self.assertTrue(hasattr(ip, "HiLab"))

    def test_has_expected_methods(self):
        """HiLab has the expected getter methods."""
        for method in ["get_cpmm_number", "get_channel", "get_bin",
                       "get_tdi", "get_ccd"]:
            self.assertTrue(hasattr(ip.HiLab, method),
                            f"HiLab missing method: {method}")

    @unittest.skip(
        "HiLab constructor requires an open HiRise Cube with Instrument labels "
        "which is not available in this test environment."
    )
    def test_construction_from_hirise_cube(self):
        """HiLab constructs from an open HiRise cube."""
        pass


class PixelFOVUnitTest(unittest.TestCase):
    """Unit tests for PixelFOV binding. Added: 2026-04-10.

    PixelFOV.latLonVertices() requires a Camera with valid spice setup.
    Tests here verify class structure; geometry tests are skipped.
    """

    def test_class_exists(self):
        """PixelFOV is importable."""
        self.assertTrue(hasattr(ip, "PixelFOV"))

    def test_construction(self):
        """PixelFOV default constructor works."""
        fov = ip.PixelFOV()
        self.assertIsInstance(fov, ip.PixelFOV)

    def test_copy_construction(self):
        """PixelFOV copy constructor works."""
        fov = ip.PixelFOV()
        fov_copy = ip.PixelFOV(fov)
        self.assertIsInstance(fov_copy, ip.PixelFOV)

    def test_has_lat_lon_vertices(self):
        """PixelFOV has lat_lon_vertices method."""
        self.assertTrue(hasattr(ip.PixelFOV, "lat_lon_vertices"))

    def test_repr(self):
        """repr(PixelFOV) is a string."""
        fov = ip.PixelFOV()
        r = repr(fov)
        self.assertIn("PixelFOV", r)


class FrameletInfoUnitTest(unittest.TestCase):
    """Unit tests for FrameletInfo struct binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """FrameletInfo is importable."""
        self.assertTrue(hasattr(ip, "FrameletInfo"))

    def test_default_construction(self):
        """FrameletInfo default constructor initializes frame_id to -1."""
        fi = ip.FrameletInfo()
        self.assertEqual(fi.frame_id, -1)

    def test_construction_with_frame_id(self):
        """FrameletInfo(frame_id) constructor sets frame_id."""
        fi = ip.FrameletInfo(42)
        self.assertEqual(fi.frame_id, 42)

    def test_construction_full(self):
        """FrameletInfo full constructor sets all fields."""
        fi = ip.FrameletInfo(7, "RED", 100, 200, 512, 256)
        self.assertEqual(fi.frame_id, 7)
        self.assertEqual(fi.filter_name, "RED")
        self.assertEqual(fi.start_sample, 100)
        self.assertEqual(fi.start_line, 200)
        self.assertEqual(fi.samples, 512)
        self.assertEqual(fi.lines, 256)

    def test_read_write_fields(self):
        """FrameletInfo fields are read-write."""
        fi = ip.FrameletInfo()
        fi.frame_id = 10
        fi.start_sample = 50
        fi.start_line = 60
        fi.samples = 128
        fi.lines = 64
        fi.filter_name = "NIR"
        self.assertEqual(fi.frame_id, 10)
        self.assertEqual(fi.start_sample, 50)
        self.assertEqual(fi.start_line, 60)
        self.assertEqual(fi.samples, 128)
        self.assertEqual(fi.lines, 64)
        self.assertEqual(fi.filter_name, "NIR")

    def test_repr(self):
        """repr(FrameletInfo) contains 'FrameletInfo'."""
        fi = ip.FrameletInfo(5, "RED", 0, 0, 512, 256)
        r = repr(fi)
        self.assertIn("FrameletInfo", r)


class PushFrameCameraCcdLayoutUnitTest(unittest.TestCase):
    """Unit tests for PushFrameCameraCcdLayout binding. Added: 2026-04-10.

    ccdSamples() and ccdLines() require SPICE kernels. Only structural
    tests are run here; SPICE-dependent tests are skipped.
    """

    def test_class_exists(self):
        """PushFrameCameraCcdLayout is importable."""
        self.assertTrue(hasattr(ip, "PushFrameCameraCcdLayout"))

    def test_default_construction(self):
        """PushFrameCameraCcdLayout default constructor works."""
        layout = ip.PushFrameCameraCcdLayout()
        self.assertIsInstance(layout, ip.PushFrameCameraCcdLayout)

    def test_construction_with_ccd_id(self):
        """PushFrameCameraCcdLayout(ccd_id) constructor works."""
        layout = ip.PushFrameCameraCcdLayout(-94001)
        self.assertIsInstance(layout, ip.PushFrameCameraCcdLayout)

    def test_has_expected_methods(self):
        """PushFrameCameraCcdLayout has expected method names."""
        for method in ["add_kernel", "ccd_samples", "ccd_lines", "get_frame_info"]:
            self.assertTrue(hasattr(ip.PushFrameCameraCcdLayout, method),
                            f"PushFrameCameraCcdLayout missing method: {method}")

    def test_repr(self):
        """repr(PushFrameCameraCcdLayout) is a string."""
        layout = ip.PushFrameCameraCcdLayout()
        r = repr(layout)
        self.assertIn("PushFrameCameraCcdLayout", r)

    @unittest.skip(
        "ccd_samples() and ccd_lines() require SPICE kernels loaded via add_kernel()."
    )
    def test_ccd_dimensions_with_kernels(self):
        """ccd_samples() and ccd_lines() return positive values with kernels loaded."""
        pass


class CameraStatisticsUnitTest(unittest.TestCase):
    """Unit tests for CameraStatistics binding. Added: 2026-04-10.

    CameraStatistics requires an ISIS cube or Camera with valid geometry.
    Only class structure tests are run; runtime construction tests are skipped.
    """

    def test_class_exists(self):
        """CameraStatistics is importable."""
        self.assertTrue(hasattr(ip, "CameraStatistics"))

    def test_has_expected_methods(self):
        """CameraStatistics has all expected stat accessor methods."""
        stat_methods = [
            "to_pvl",
            "get_lat_stat", "get_lon_stat", "get_res_stat",
            "get_oblique_res_stat", "get_oblique_sample_res_stat",
            "get_oblique_line_res_stat", "get_sample_res_stat",
            "get_line_res_stat", "get_aspect_ratio_stat",
            "get_phase_stat", "get_emission_stat", "get_incidence_stat",
            "get_local_solar_time_stat", "get_local_radius_stat",
            "get_north_azimuth_stat",
        ]
        for method in stat_methods:
            self.assertTrue(hasattr(ip.CameraStatistics, method),
                            f"CameraStatistics missing method: {method}")

    @unittest.skip(
        "CameraStatistics requires an ISIS cube filename or Camera with "
        "a valid camera model, SPICE data, and geometry. "
        "These are not available in the unit test environment."
    )
    def test_construction_from_filename(self):
        """CameraStatistics constructs from a cube filename."""
        pass


if __name__ == "__main__":
    unittest.main()
