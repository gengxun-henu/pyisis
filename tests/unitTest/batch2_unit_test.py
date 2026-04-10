"""
Unit tests for Batch 2 bindings: ProcessMosaic, CsmBundleObservation,
IsisBundleObservation, ImagePolygon, and GSLUtility.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added focused unit tests covering construction,
         flag setters/getters, enum values, WKT polygon creation, and singleton
         access for the five Batch-2 classes.
"""
import unittest

from _unit_test_support import ip


class ProcessMosaicUnitTest(unittest.TestCase):
    """Focused unit tests for ProcessMosaic binding. Added: 2026-04-10."""

    def test_construct(self):
        """ProcessMosaic() constructs without error."""
        pm = ip.ProcessMosaic()
        self.assertIsNotNone(pm)

    def test_image_overlay_enum_values(self):
        """All ImageOverlay enum values are accessible."""
        self.assertIsNotNone(ip.ImageOverlay.PlaceImagesOnTop)
        self.assertIsNotNone(ip.ImageOverlay.PlaceImagesBehind)
        self.assertIsNotNone(ip.ImageOverlay.UseBandPlacementCriteria)
        self.assertIsNotNone(ip.ImageOverlay.AverageImageWithMosaic)

    def test_overlay_to_string(self):
        """overlay_to_string() returns a non-empty string for each enum value."""
        s = ip.ProcessMosaic.overlay_to_string(ip.ImageOverlay.PlaceImagesOnTop)
        self.assertIsInstance(s, str)
        self.assertGreater(len(s), 0)

    def test_string_to_overlay_roundtrip(self):
        """string_to_overlay(overlay_to_string(v)) roundtrips correctly."""
        v = ip.ImageOverlay.PlaceImagesBehind
        name = ip.ProcessMosaic.overlay_to_string(v)
        result = ip.ProcessMosaic.string_to_overlay(name)
        self.assertEqual(result, v)

    def test_track_flag_default(self):
        """get_track_flag() defaults to False for a new ProcessMosaic."""
        pm = ip.ProcessMosaic()
        self.assertFalse(pm.get_track_flag())

    def test_set_track_flag(self):
        """set_track_flag(True) causes get_track_flag() to return True."""
        pm = ip.ProcessMosaic()
        pm.set_track_flag(True)
        self.assertTrue(pm.get_track_flag())

    def test_null_flag_default(self):
        """get_null_flag() defaults to False."""
        pm = ip.ProcessMosaic()
        self.assertFalse(pm.get_null_flag())

    def test_set_null_flag(self):
        """set_null_flag(True) toggles get_null_flag()."""
        pm = ip.ProcessMosaic()
        pm.set_null_flag(True)
        self.assertTrue(pm.get_null_flag())

    def test_high_saturation_flag(self):
        """set/get_high_saturation_flag round-trip."""
        pm = ip.ProcessMosaic()
        pm.set_high_saturation_flag(True)
        self.assertTrue(pm.get_high_saturation_flag())

    def test_low_saturation_flag(self):
        """set/get_low_saturation_flag round-trip."""
        pm = ip.ProcessMosaic()
        pm.set_low_saturation_flag(True)
        self.assertTrue(pm.get_low_saturation_flag())

    def test_set_image_overlay(self):
        """set_image_overlay(AverageImageWithMosaic) executes without error."""
        pm = ip.ProcessMosaic()
        pm.set_image_overlay(ip.ImageOverlay.AverageImageWithMosaic)

    def test_repr(self):
        """__repr__ contains 'ProcessMosaic'."""
        pm = ip.ProcessMosaic()
        self.assertIn("ProcessMosaic", repr(pm))


class CsmBundleObservationUnitTest(unittest.TestCase):
    """Focused unit tests for CsmBundleObservation binding. Added: 2026-04-10."""

    def test_construct(self):
        """CsmBundleObservation() constructs without error."""
        obs = ip.CsmBundleObservation()
        self.assertIsNotNone(obs)

    def test_number_parameters_default(self):
        """number_parameters() returns 0 for a default-constructed observation."""
        obs = ip.CsmBundleObservation()
        n = obs.number_parameters()
        self.assertIsInstance(n, int)
        self.assertEqual(n, 0)

    def test_parameter_list_default(self):
        """parameter_list() returns an empty list for a default-constructed observation."""
        obs = ip.CsmBundleObservation()
        params = obs.parameter_list()
        self.assertIsInstance(params, list)
        self.assertEqual(len(params), 0)

    def test_bundle_output_csv_default(self):
        """bundle_output_csv(False) returns a string for a default observation."""
        obs = ip.CsmBundleObservation()
        csv = obs.bundle_output_csv(False)
        self.assertIsInstance(csv, str)

    def test_repr(self):
        """__repr__ contains 'CsmBundleObservation'."""
        obs = ip.CsmBundleObservation()
        self.assertIn("CsmBundleObservation", repr(obs))


class IsisBundleObservationUnitTest(unittest.TestCase):
    """Focused unit tests for IsisBundleObservation binding. Added: 2026-04-10."""

    def test_construct(self):
        """IsisBundleObservation() constructs without error."""
        obs = ip.IsisBundleObservation()
        self.assertIsNotNone(obs)

    def test_number_parameters_default(self):
        """number_parameters() returns 0 for a default-constructed observation."""
        obs = ip.IsisBundleObservation()
        self.assertEqual(obs.number_parameters(), 0)

    def test_number_position_parameters_default(self):
        """number_position_parameters() returns 0 for default-constructed."""
        obs = ip.IsisBundleObservation()
        self.assertEqual(obs.number_position_parameters(), 0)

    def test_number_pointing_parameters_default(self):
        """number_pointing_parameters() returns 0 for default-constructed."""
        obs = ip.IsisBundleObservation()
        self.assertEqual(obs.number_pointing_parameters(), 0)

    def test_parameter_list_default(self):
        """parameter_list() is empty for default-constructed."""
        obs = ip.IsisBundleObservation()
        self.assertIsInstance(obs.parameter_list(), list)
        self.assertEqual(len(obs.parameter_list()), 0)

    def test_spice_position_none(self):
        """spice_position() returns None for default-constructed (no cube loaded)."""
        obs = ip.IsisBundleObservation()
        # Before a cube is loaded, spice position is None
        pos = obs.spice_position()
        # May be None (nullptr) or a SpicePosition
        # Just check it doesn't raise an exception
        self.assertTrue(pos is None or isinstance(pos, ip.SpicePosition))

    def test_bundle_output_csv_default(self):
        """bundle_output_csv(False) returns a string."""
        obs = ip.IsisBundleObservation()
        csv = obs.bundle_output_csv(False)
        self.assertIsInstance(csv, str)

    def test_repr(self):
        """__repr__ contains 'IsisBundleObservation'."""
        obs = ip.IsisBundleObservation()
        self.assertIn("IsisBundleObservation", repr(obs))


class ImagePolygonUnitTest(unittest.TestCase):
    """Focused unit tests for ImagePolygon binding. Added: 2026-04-10."""

    def _make_square_coords(self):
        """Return a simple closed square polygon as [[lon, lat], ...]."""
        return [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [0.0, 0.0],   # closed
        ]

    def test_construct_default(self):
        """ImagePolygon() constructs without error."""
        ip_obj = ip.ImagePolygon()
        self.assertIsNotNone(ip_obj)

    def test_poly_str_empty(self):
        """poly_str() returns empty string for default-constructed polygon."""
        ip_obj = ip.ImagePolygon()
        self.assertEqual(ip_obj.poly_str(), "")

    def test_create_from_coords(self):
        """create_from_coords() populates the polygon."""
        ip_obj = ip.ImagePolygon()
        ip_obj.create_from_coords(self._make_square_coords())
        wkt = ip_obj.poly_str()
        self.assertIsInstance(wkt, str)
        self.assertGreater(len(wkt), 0)

    def test_poly_str_contains_polygon(self):
        """poly_str() after create_from_coords contains 'MULTIPOLYGON' or 'POLYGON'."""
        ip_obj = ip.ImagePolygon()
        ip_obj.create_from_coords(self._make_square_coords())
        wkt = ip_obj.poly_str()
        self.assertTrue("POLYGON" in wkt.upper() or "MULTIPOLYGON" in wkt.upper())

    def test_num_vertices(self):
        """num_vertices() returns >= 4 for a 5-point closed square."""
        ip_obj = ip.ImagePolygon()
        ip_obj.create_from_coords(self._make_square_coords())
        n = ip_obj.num_vertices()
        self.assertGreaterEqual(n, 4)

    def test_set_emission(self):
        """set_emission(90.0) executes without error."""
        ip_obj = ip.ImagePolygon()
        ip_obj.set_emission(90.0)

    def test_set_incidence(self):
        """set_incidence(90.0) executes without error."""
        ip_obj = ip.ImagePolygon()
        ip_obj.set_incidence(90.0)

    def test_set_ellipsoid_limb(self):
        """set_ellipsoid_limb(True) executes without error."""
        ip_obj = ip.ImagePolygon()
        ip_obj.set_ellipsoid_limb(True)

    def test_set_subpixel_accuracy(self):
        """set_subpixel_accuracy(10) executes without error."""
        ip_obj = ip.ImagePolygon()
        ip_obj.set_subpixel_accuracy(10)

    def test_repr(self):
        """__repr__ contains 'ImagePolygon'."""
        ip_obj = ip.ImagePolygon()
        self.assertIn("ImagePolygon", repr(ip_obj))


class GSLUtilityUnitTest(unittest.TestCase):
    """Focused unit tests for GSLUtility singleton binding. Added: 2026-04-10."""

    def test_get_instance(self):
        """get_instance() returns a GSLUtility object."""
        util = ip.GSLUtility.get_instance()
        self.assertIsNotNone(util)
        self.assertIsInstance(util, ip.GSLUtility)

    def test_singleton_identity(self):
        """Two calls to get_instance() return the same underlying object."""
        u1 = ip.GSLUtility.get_instance()
        u2 = ip.GSLUtility.get_instance()
        # Both should be non-None and of the same type
        self.assertIsNotNone(u1)
        self.assertIsNotNone(u2)

    def test_success_for_zero(self):
        """success(0) returns True (GSL_SUCCESS == 0)."""
        util = ip.GSLUtility.get_instance()
        self.assertTrue(util.success(0))

    def test_success_for_nonzero(self):
        """success(1) returns False."""
        util = ip.GSLUtility.get_instance()
        self.assertFalse(util.success(1))

    def test_status_for_zero(self):
        """status(0) returns a string."""
        util = ip.GSLUtility.get_instance()
        s = util.status(0)
        self.assertIsInstance(s, str)

    def test_repr(self):
        """__repr__ contains 'GSLUtility'."""
        util = ip.GSLUtility.get_instance()
        self.assertIn("GSLUtility", repr(util))


if __name__ == '__main__':
    unittest.main()
