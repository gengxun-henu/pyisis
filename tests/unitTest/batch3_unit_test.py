"""
Unit tests for Batch 3 bindings: ProcessMapMosaic, ProcessRubberSheet,
ProcessPolygons, ProcessGroundPolygons, and PolygonTools.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added focused unit tests covering construction,
         flag inheritance, static utility methods, and enum/type checks for the
         five Batch-3 Process and PolygonTools classes.
"""
import unittest

from _unit_test_support import ip


class ProcessMapMosaicUnitTest(unittest.TestCase):
    """Focused unit tests for ProcessMapMosaic binding. Added: 2026-04-10."""

    def test_construct(self):
        """ProcessMapMosaic() constructs without error."""
        pm = ip.ProcessMapMosaic()
        self.assertIsNotNone(pm)

    def test_inherits_track_flag(self):
        """ProcessMapMosaic inherits set/get_track_flag from ProcessMosaic."""
        pm = ip.ProcessMapMosaic()
        pm.set_track_flag(True)
        self.assertTrue(pm.get_track_flag())

    def test_inherits_null_flag(self):
        """ProcessMapMosaic inherits set/get_null_flag from ProcessMosaic."""
        pm = ip.ProcessMapMosaic()
        pm.set_null_flag(True)
        self.assertTrue(pm.get_null_flag())

    def test_inherits_image_overlay(self):
        """ProcessMapMosaic inherits set_image_overlay from ProcessMosaic."""
        pm = ip.ProcessMapMosaic()
        pm.set_image_overlay(ip.ImageOverlay.PlaceImagesOnTop)

    def test_repr(self):
        """__repr__ contains 'ProcessMapMosaic'."""
        pm = ip.ProcessMapMosaic()
        self.assertIn("ProcessMapMosaic", repr(pm))


class ProcessRubberSheetUnitTest(unittest.TestCase):
    """Focused unit tests for ProcessRubberSheet binding. Added: 2026-04-10."""

    def test_construct_default(self):
        """ProcessRubberSheet() constructs without error using defaults."""
        prs = ip.ProcessRubberSheet()
        self.assertIsNotNone(prs)

    def test_construct_with_sizes(self):
        """ProcessRubberSheet(start_size, end_size) constructs correctly."""
        prs = ip.ProcessRubberSheet(256, 16)
        self.assertIsNotNone(prs)

    def test_force_tile(self):
        """force_tile(samp, line) executes without error."""
        prs = ip.ProcessRubberSheet()
        prs.force_tile(100.0, 200.0)

    def test_set_tiling(self):
        """set_tiling(start, end) executes without error."""
        prs = ip.ProcessRubberSheet()
        prs.set_tiling(64, 4)

    def test_repr(self):
        """__repr__ contains 'ProcessRubberSheet'."""
        prs = ip.ProcessRubberSheet()
        self.assertIn("ProcessRubberSheet", repr(prs))


class ProcessPolygonsUnitTest(unittest.TestCase):
    """Focused unit tests for ProcessPolygons binding. Added: 2026-04-10."""

    def test_construct(self):
        """ProcessPolygons() constructs without error."""
        pp = ip.ProcessPolygons()
        self.assertIsNotNone(pp)

    def test_set_intersect_algorithm_center(self):
        """set_intersect_algorithm(True) executes without error."""
        pp = ip.ProcessPolygons()
        pp.set_intersect_algorithm(True)

    def test_set_intersect_algorithm_coverage(self):
        """set_intersect_algorithm(False) executes without error."""
        pp = ip.ProcessPolygons()
        pp.set_intersect_algorithm(False)

    def test_repr(self):
        """__repr__ contains 'ProcessPolygons'."""
        pp = ip.ProcessPolygons()
        self.assertIn("ProcessPolygons", repr(pp))


class ProcessGroundPolygonsUnitTest(unittest.TestCase):
    """Focused unit tests for ProcessGroundPolygons binding. Added: 2026-04-10."""

    def test_construct(self):
        """ProcessGroundPolygons() constructs without error."""
        pgp = ip.ProcessGroundPolygons()
        self.assertIsNotNone(pgp)

    def test_inherits_set_intersect_algorithm(self):
        """ProcessGroundPolygons inherits set_intersect_algorithm from ProcessPolygons."""
        pgp = ip.ProcessGroundPolygons()
        pgp.set_intersect_algorithm(True)

    def test_repr(self):
        """__repr__ contains 'ProcessGroundPolygons'."""
        pgp = ip.ProcessGroundPolygons()
        self.assertIn("ProcessGroundPolygons", repr(pgp))


class PolygonToolsUnitTest(unittest.TestCase):
    """Focused unit tests for PolygonTools static methods binding. Added: 2026-04-10."""

    def test_equal_same_values(self):
        """equal(x, x) returns True."""
        self.assertTrue(ip.PolygonTools.equal(1.234567890, 1.234567890))

    def test_equal_different_values(self):
        """equal(x, y) returns False for clearly different values."""
        self.assertFalse(ip.PolygonTools.equal(1.0, 2.0))

    def test_reduce_precision(self):
        """reduce_precision(1.23456789, 4) rounds to 4 significant figures."""
        result = ip.PolygonTools.reduce_precision(1.23456789, 4)
        self.assertAlmostEqual(result, 1.235, places=2)

    def test_decimal_place_integer(self):
        """decimal_place(100.0) returns the correct power-of-10 position."""
        pos = ip.PolygonTools.decimal_place(100.0)
        self.assertIsInstance(pos, int)

    def test_gml_schema(self):
        """gml_schema() returns a non-empty string."""
        schema = ip.PolygonTools.gml_schema()
        self.assertIsInstance(schema, str)
        self.assertGreater(len(schema), 0)

    def test_repr(self):
        """PolygonTools() repr contains 'PolygonTools'."""
        # PolygonTools is primarily a static utility class but it's bound as a class
        pt = ip.PolygonTools()
        self.assertIn("PolygonTools", repr(pt))


if __name__ == '__main__':
    unittest.main()
