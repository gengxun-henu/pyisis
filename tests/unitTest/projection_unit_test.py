import unittest

from _unit_test_support import (
    ip,
    make_ring_cylindrical_label,
    make_simple_cylindrical_label,
)


class ProjectionUnitTest(unittest.TestCase):
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
