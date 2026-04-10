"""
Unit tests for ISIS PolygonSeeder family bindings.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import isis_pybind as ip


def _make_grid_seeder_pvl(xspacing=1500.0, yspacing=1500.0,
                          min_thickness=0.0, min_area=0.0,
                          sub_grid=False):
    """Build the PVL structure required by GridPolygonSeeder."""
    alg = ip.PvlGroup("PolygonSeederAlgorithm")
    alg.add_keyword(ip.PvlKeyword("Name", "Grid"))
    alg.add_keyword(ip.PvlKeyword("XSpacing", str(xspacing)))
    alg.add_keyword(ip.PvlKeyword("YSpacing", str(yspacing)))
    if min_thickness > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumThickness", str(min_thickness)))
    if min_area > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumArea", str(min_area)))
    if sub_grid:
        alg.add_keyword(ip.PvlKeyword("SubGrid", "true"))
    obj = ip.PvlObject("AutoSeed")
    obj.add_group(alg)
    pvl = ip.Pvl()
    pvl.add_object(obj)
    return pvl


def _make_limit_seeder_pvl(major=2, minor=2,
                            min_thickness=0.0, min_area=0.0):
    """Build the PVL structure required by LimitPolygonSeeder."""
    alg = ip.PvlGroup("PolygonSeederAlgorithm")
    alg.add_keyword(ip.PvlKeyword("Name", "Limit"))
    alg.add_keyword(ip.PvlKeyword("MajorAxisPoints", str(major)))
    alg.add_keyword(ip.PvlKeyword("MinorAxisPoints", str(minor)))
    if min_thickness > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumThickness", str(min_thickness)))
    if min_area > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumArea", str(min_area)))
    obj = ip.PvlObject("AutoSeed")
    obj.add_group(alg)
    pvl = ip.Pvl()
    pvl.add_object(obj)
    return pvl


def _make_strip_seeder_pvl(xspacing=1500.0, yspacing=1500.0,
                            min_thickness=0.0, min_area=0.0):
    """Build the PVL structure required by StripPolygonSeeder."""
    alg = ip.PvlGroup("PolygonSeederAlgorithm")
    alg.add_keyword(ip.PvlKeyword("Name", "Strip"))
    alg.add_keyword(ip.PvlKeyword("XSpacing", str(xspacing)))
    alg.add_keyword(ip.PvlKeyword("YSpacing", str(yspacing)))
    if min_thickness > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumThickness", str(min_thickness)))
    if min_area > 0.0:
        alg.add_keyword(ip.PvlKeyword("MinimumArea", str(min_area)))
    obj = ip.PvlObject("AutoSeed")
    obj.add_group(alg)
    pvl = ip.Pvl()
    pvl.add_object(obj)
    return pvl


class GridPolygonSeederUnitTest(unittest.TestCase):
    """Unit tests for GridPolygonSeeder binding. Added: 2026-04-10."""

    def test_construction_default_pvl(self):
        """GridPolygonSeeder constructs from a valid PVL without error."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.GridPolygonSeeder)

    def test_inherits_polygon_seeder(self):
        """GridPolygonSeeder is a PolygonSeeder instance."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.PolygonSeeder)

    def test_algorithm_name(self):
        """algorithm() returns 'Grid'."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertEqual(seeder.algorithm(), "Grid")

    def test_sub_grid_default_false(self):
        """sub_grid() returns False when SubGrid is not set in PVL."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertFalse(seeder.sub_grid())

    def test_sub_grid_true(self):
        """sub_grid() returns True when SubGrid=true in PVL."""
        pvl = _make_grid_seeder_pvl(sub_grid=True)
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertTrue(seeder.sub_grid())

    def test_minimum_thickness_default(self):
        """minimum_thickness() returns 0.0 when not set."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_thickness(), 0.0)

    def test_minimum_thickness_set(self):
        """minimum_thickness() returns value set in PVL."""
        pvl = _make_grid_seeder_pvl(min_thickness=0.3)
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_thickness(), 0.3)

    def test_minimum_area_default(self):
        """minimum_area() returns 0.0 when not set."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_area(), 0.0)

    def test_minimum_area_set(self):
        """minimum_area() returns value set in PVL."""
        pvl = _make_grid_seeder_pvl(min_area=10.0)
        seeder = ip.GridPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_area(), 10.0)

    def test_plugin_parameters(self):
        """plugin_parameters() returns a PvlGroup without error."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        grp = seeder.plugin_parameters("GridParams")
        self.assertIsInstance(grp, ip.PvlGroup)

    def test_repr(self):
        """repr(GridPolygonSeeder) contains 'GridPolygonSeeder'."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        r = repr(seeder)
        self.assertIn("GridPolygonSeeder", r)

    def test_repr_contains_algorithm(self):
        """repr(GridPolygonSeeder) contains 'Grid' algorithm name."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.GridPolygonSeeder(pvl)
        r = repr(seeder)
        self.assertIn("Grid", r)


class LimitPolygonSeederUnitTest(unittest.TestCase):
    """Unit tests for LimitPolygonSeeder binding. Added: 2026-04-10."""

    def test_construction(self):
        """LimitPolygonSeeder constructs from valid PVL."""
        pvl = _make_limit_seeder_pvl()
        seeder = ip.LimitPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.LimitPolygonSeeder)

    def test_inherits_polygon_seeder(self):
        """LimitPolygonSeeder is a PolygonSeeder instance."""
        pvl = _make_limit_seeder_pvl()
        seeder = ip.LimitPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.PolygonSeeder)

    def test_algorithm_name(self):
        """algorithm() returns 'Limit'."""
        pvl = _make_limit_seeder_pvl()
        seeder = ip.LimitPolygonSeeder(pvl)
        self.assertEqual(seeder.algorithm(), "Limit")

    def test_minimum_thickness_set(self):
        """minimum_thickness() returns value from PVL."""
        pvl = _make_limit_seeder_pvl(min_thickness=0.3)
        seeder = ip.LimitPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_thickness(), 0.3)

    def test_minimum_area_set(self):
        """minimum_area() returns value from PVL."""
        pvl = _make_limit_seeder_pvl(min_area=5.0)
        seeder = ip.LimitPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_area(), 5.0)

    def test_plugin_parameters(self):
        """plugin_parameters() returns a PvlGroup."""
        pvl = _make_limit_seeder_pvl()
        seeder = ip.LimitPolygonSeeder(pvl)
        grp = seeder.plugin_parameters("LimitParams")
        self.assertIsInstance(grp, ip.PvlGroup)

    def test_repr(self):
        """repr(LimitPolygonSeeder) contains 'LimitPolygonSeeder'."""
        pvl = _make_limit_seeder_pvl()
        seeder = ip.LimitPolygonSeeder(pvl)
        r = repr(seeder)
        self.assertIn("LimitPolygonSeeder", r)


class StripPolygonSeederUnitTest(unittest.TestCase):
    """Unit tests for StripPolygonSeeder binding. Added: 2026-04-10."""

    def test_construction(self):
        """StripPolygonSeeder constructs from valid PVL."""
        pvl = _make_strip_seeder_pvl()
        seeder = ip.StripPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.StripPolygonSeeder)

    def test_inherits_polygon_seeder(self):
        """StripPolygonSeeder is a PolygonSeeder instance."""
        pvl = _make_strip_seeder_pvl()
        seeder = ip.StripPolygonSeeder(pvl)
        self.assertIsInstance(seeder, ip.PolygonSeeder)

    def test_algorithm_name(self):
        """algorithm() returns 'Strip'."""
        pvl = _make_strip_seeder_pvl()
        seeder = ip.StripPolygonSeeder(pvl)
        self.assertEqual(seeder.algorithm(), "Strip")

    def test_minimum_thickness_set(self):
        """minimum_thickness() returns value from PVL."""
        pvl = _make_strip_seeder_pvl(min_thickness=0.3)
        seeder = ip.StripPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_thickness(), 0.3)

    def test_minimum_area_set(self):
        """minimum_area() returns value from PVL."""
        pvl = _make_strip_seeder_pvl(min_area=10.0)
        seeder = ip.StripPolygonSeeder(pvl)
        self.assertAlmostEqual(seeder.minimum_area(), 10.0)

    def test_plugin_parameters(self):
        """plugin_parameters() returns a PvlGroup."""
        pvl = _make_strip_seeder_pvl()
        seeder = ip.StripPolygonSeeder(pvl)
        grp = seeder.plugin_parameters("StripParams")
        self.assertIsInstance(grp, ip.PvlGroup)

    def test_repr(self):
        """repr(StripPolygonSeeder) contains 'StripPolygonSeeder'."""
        pvl = _make_strip_seeder_pvl()
        seeder = ip.StripPolygonSeeder(pvl)
        r = repr(seeder)
        self.assertIn("StripPolygonSeeder", r)


class PolygonSeederFactoryUnitTest(unittest.TestCase):
    """Unit tests for PolygonSeederFactory binding. Added: 2026-04-10."""

    def test_factory_class_exists(self):
        """PolygonSeederFactory is importable."""
        self.assertTrue(hasattr(ip, "PolygonSeederFactory"))

    def test_factory_has_create(self):
        """PolygonSeederFactory has a create static method."""
        self.assertTrue(hasattr(ip.PolygonSeederFactory, "create"))

    @unittest.skip(
        "PolygonSeederFactory.create requires ISISROOT/lib/PolygonSeeder.plugin "
        "which is not available in this test environment."
    )
    def test_factory_creates_grid_seeder(self):
        """PolygonSeederFactory.create returns a GridPolygonSeeder for Name=Grid."""
        pvl = _make_grid_seeder_pvl()
        seeder = ip.PolygonSeederFactory.create(pvl)
        self.assertIsInstance(seeder, ip.PolygonSeeder)
        self.assertEqual(seeder.algorithm(), "Grid")


if __name__ == "__main__":
    unittest.main()
