"""
Unit tests for ISIS projection and ProjectionFactory bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import unittest

from _unit_test_support import (
    ip,
    make_equirectangular_label,
    make_ring_cylindrical_label,
    make_simple_cylindrical_label,
)


class ProjectionUnitTest(unittest.TestCase):
    def test_equirectangular_requires_center_keywords_without_defaults(self):
        """Test that Equirectangular requires CenterLongitude and CenterLatitude when defaults not allowed"""
        label = make_equirectangular_label(include_center_longitude=False)

        with self.assertRaises(Exception):
            ip.Equirectangular(label)

        label = make_equirectangular_label(include_center_latitude=False)

        with self.assertRaises(Exception):
            ip.Equirectangular(label)

    def test_equirectangular_allow_defaults_matches_cpp_default_path(self):
        """Test that Equirectangular computes default center values when allowed"""
        label = make_equirectangular_label(
            include_center_longitude=False,
            include_center_latitude=False
        )

        projection = ip.Equirectangular(label, True)

        self.assertEqual(projection.name(), "Equirectangular")
        self.assertEqual(projection.version(), "1.0")
        self.assertTrue(projection.is_equatorial_cylindrical())

        # Default center latitude should be 0.0 (middle of -65 to 65)
        # Default center longitude should be 0.0 (middle of -180 to 180)
        self.assertAlmostEqual(projection.true_scale_latitude(), 0.0, places=8)

    def test_equirectangular_ground_and_coordinate_round_trip(self):
        """Test round-trip conversion between ground and coordinate"""
        projection = ip.Equirectangular(make_equirectangular_label())

        # Test setting ground coordinates
        self.assertTrue(projection.set_ground(30.0, 45.0))
        self.assertAlmostEqual(projection.latitude(), 30.0, places=10)
        self.assertAlmostEqual(projection.longitude(), 45.0, places=10)

        x = projection.x_coord()
        y = projection.y_coord()

        # Test setting coordinate from the same X/Y
        self.assertTrue(projection.set_coordinate(x, y))
        self.assertAlmostEqual(projection.latitude(), 30.0, places=8)
        self.assertAlmostEqual(projection.longitude(), 45.0, places=8)

    def test_equirectangular_xy_range_export(self):
        """Test that xy_range returns valid min/max values"""
        projection = ip.Equirectangular(make_equirectangular_label())

        xy_range = projection.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

        minX, maxX, minY, maxY = xy_range
        self.assertLess(minX, maxX)
        self.assertLess(minY, maxY)

    def test_equirectangular_mapping_methods(self):
        """Test mapping, mapping_latitudes, and mapping_longitudes methods"""
        projection = ip.Equirectangular(make_equirectangular_label())

        mapping = projection.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(mapping.has_keyword("CenterLongitude"))
        self.assertTrue(mapping.has_keyword("CenterLatitude"))

        mapping_latitudes = projection.mapping_latitudes()
        self.assertTrue(mapping_latitudes.has_keyword("MinimumLatitude"))
        self.assertTrue(mapping_latitudes.has_keyword("CenterLatitude"))

        mapping_longitudes = projection.mapping_longitudes()
        self.assertTrue(mapping_longitudes.has_keyword("MinimumLongitude"))
        self.assertTrue(mapping_longitudes.has_keyword("CenterLongitude"))

    def test_equirectangular_near_pole_raises_exception(self):
        """Test that setting center latitude near pole raises exception"""
        # Create a label with center latitude very close to 90 degrees
        lines = [
            "Group = Mapping",
            "  EquatorialRadius = 3396190.0",
            "  PolarRadius = 3376200.0",
            "  LatitudeType = Planetographic",
            "  LongitudeDirection = PositiveEast",
            "  LongitudeDomain = 360",
            "  ProjectionName = Equirectangular",
            "  CenterLongitude = 0.0",
            "  CenterLatitude = 89.9999999",  # Very close to pole
            "  MinimumLatitude = -65.0",
            "  MaximumLatitude = 65.0",
            "  MinimumLongitude = -180.0",
            "  MaximumLongitude = 180.0",
            "EndGroup",
            "End",
        ]

        pvl = ip.Pvl()
        pvl.from_string("\n".join(lines) + "\n")

        with self.assertRaises(Exception):
            ip.Equirectangular(pvl)

    def test_simple_cylindrical_requires_center_longitude_without_defaults(self):
        label = make_simple_cylindrical_label(include_center_longitude=False)

        with self.assertRaises(Exception):
            ip.SimpleCylindrical(label)

    def test_simple_cylindrical_allow_defaults_matches_cpp_default_path(self):
        label = make_simple_cylindrical_label(include_center_longitude=False)

        projection = ip.SimpleCylindrical(label, True)

        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertTrue(projection.set_ground(-50.0, -75.0))
        self.assertAlmostEqual(projection.latitude(), -50.0, places=10)
        self.assertAlmostEqual(projection.longitude(), -75.0, places=10)

    def test_simple_cylindrical_ground_and_coordinate_round_trip(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())

        self.assertTrue(projection.set_ground(-50.0, -75.0))
        self.assertAlmostEqual(projection.latitude(), -50.0, places=10)
        self.assertAlmostEqual(projection.longitude(), -75.0, places=10)

        self.assertTrue(projection.set_coordinate(0.2617993877991494, -0.8726646259971648))
        self.assertAlmostEqual(projection.latitude(), -1.4722380078853067e-05, places=10)
        self.assertAlmostEqual(projection.longitude(), 220.00000441671403, places=8)

    def test_simple_cylindrical_mapping_and_xy_range_exports(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())

        xy_range = projection.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)
        self.assertLess(xy_range[0], xy_range[1])
        self.assertLess(xy_range[2], xy_range[3])

        mapping = projection.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(mapping.has_keyword("CenterLongitude"))
        self.assertTrue(projection.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(projection.mapping_longitudes().has_keyword("MinimumLongitude"))

    def test_projection_factory_create_from_cube_label_requires_cube_keywords(self):
        label = make_simple_cylindrical_label(include_pixel_resolution=False, include_upper_left=False)

        with self.assertRaises(Exception):
            ip.ProjectionFactory.create_from_cube_label(label)

        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=False)
        with self.assertRaises(Exception):
            ip.ProjectionFactory.create_from_cube_label(label)

        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=True)
        projection = ip.ProjectionFactory.create_from_cube_label(label)
        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertTrue(projection.set_world(245.0, 355.0))
        self.assertAlmostEqual(projection.latitude(), 22.82592837302989, places=8)
        self.assertAlmostEqual(projection.longitude(), 227.94605488817228, places=8)

    def test_projection_factory_create_for_cube_computes_cube_shape(self):
        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=False)

        projection, samples, lines = ip.ProjectionFactory.create_for_cube(label)

        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertGreater(samples, 0)
        self.assertGreater(lines, 0)

        mapping = label.find_group("Mapping")
        self.assertTrue(mapping.has_keyword("UpperLeftCornerX"))
        self.assertTrue(mapping.has_keyword("UpperLeftCornerY"))

    def test_ring_cylindrical_requires_center_keywords_without_defaults(self):
        missing_longitude = make_ring_cylindrical_label(include_center_longitude=False)
        with self.assertRaises(Exception):
            ip.RingCylindrical(missing_longitude)

        missing_radius = make_ring_cylindrical_label(include_center_radius=False)
        with self.assertRaises(Exception):
            ip.RingCylindrical(missing_radius)

    def test_ring_cylindrical_default_constructor_path_and_round_trip(self):
        label = make_ring_cylindrical_label(include_center_longitude=False, include_center_radius=False)
        projection = ip.RingCylindrical(label, True)

        self.assertEqual(projection.name(), "RingCylindrical")
        self.assertTrue(projection.mapping().has_keyword("CenterRingLongitude"))
        self.assertTrue(projection.mapping().has_keyword("CenterRingRadius"))

        configured = ip.RingCylindrical(make_ring_cylindrical_label())
        self.assertTrue(configured.set_ground(20000.0, 45.0))
        self.assertAlmostEqual(configured.ring_radius(), 20000.0, places=8)
        self.assertAlmostEqual(configured.ring_longitude(), 45.0, places=8)

        self.assertTrue(configured.set_coordinate(-157079.6326794896, 180000.0))
        self.assertAlmostEqual(configured.ring_radius(), 20000.0, places=8)
        self.assertAlmostEqual(configured.ring_longitude(), 45.0, places=8)

    def test_ring_cylindrical_range_and_direction_helpers(self):
        configured = ip.RingCylindrical(make_ring_cylindrical_label())

        self.assertEqual(configured.ring_longitude_direction_string(), "Clockwise")
        self.assertEqual(configured.ring_longitude_domain_string(), "180")
        self.assertEqual(configured.true_scale_ring_radius(), 200000.0)

        self.assertFalse(configured.set_coordinate(-157079.6326794896, -20000001.0))
        self.assertFalse(configured.set_coordinate(-1570.6326794896, 184000.5))
        self.assertAlmostEqual(configured.ring_radius(), 15999.5, places=8)

        xy_range = configured.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

        counter_clockwise = ip.RingCylindrical(
            make_ring_cylindrical_label(
                include_center_longitude=False,
                include_center_radius=False,
                direction="CounterClockwise",
                domain="360",
            ),
            True,
        )
        self.assertEqual(counter_clockwise.ring_longitude_direction_string(), "CounterClockwise")
        self.assertEqual(counter_clockwise.ring_longitude_domain_string(), "360")
        self.assertFalse(counter_clockwise.set_ground(-1000.0, 45.0))
        self.assertFalse(counter_clockwise.set_ground(0.0, 45.0))


if __name__ == "__main__":
    unittest.main()
