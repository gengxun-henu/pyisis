import unittest

from _unit_test_support import DEGREES, DISPLACEMENT_METERS, KILOMETERS, ip


class SurfacePointUnitTest(unittest.TestCase):
    def test_default_constructor_is_invalid(self):
        point = ip.SurfacePoint()
        self.assertFalse(point.valid())
        self.assertEqual(repr(point), "SurfacePoint(invalid)")

    def test_latitudinal_constructor_and_accessors(self):
        point = ip.SurfacePoint(
            ip.Latitude(10.0, DEGREES),
            ip.Longitude(20.0, DEGREES),
            ip.Distance(3396.19, KILOMETERS),
        )

        self.assertTrue(point.valid())
        self.assertAlmostEqual(point.get_latitude().degrees(), 10.0, places=10)
        self.assertAlmostEqual(point.get_longitude().degrees(), 20.0, places=10)
        self.assertAlmostEqual(point.get_local_radius().kilometers(), 3396.19, places=8)
        self.assertEqual(len(point.to_naif_array()), 3)

    def test_rectangular_constructor_and_naif_round_trip(self):
        point = ip.SurfacePoint(
            ip.Displacement(1.0, DISPLACEMENT_METERS),
            ip.Displacement(2.0, DISPLACEMENT_METERS),
            ip.Displacement(3.0, DISPLACEMENT_METERS),
        )

        self.assertTrue(point.valid())
        self.assertAlmostEqual(point.get_x().meters(), 1.0, places=12)
        self.assertAlmostEqual(point.get_y().meters(), 2.0, places=12)
        self.assertAlmostEqual(point.get_z().meters(), 3.0, places=12)

        copied = ip.SurfacePoint()
        copied.from_naif_array(point.to_naif_array())
        self.assertTrue(copied.valid())
        self.assertEqual(copied, point)

    def test_copy_and_distance_to_point(self):
        point_a = ip.SurfacePoint(
            ip.Latitude(0.0, DEGREES),
            ip.Longitude(0.0, DEGREES),
            ip.Distance(1000.0, KILOMETERS),
        )
        point_b = ip.SurfacePoint(
            ip.Latitude(0.0, DEGREES),
            ip.Longitude(0.0, DEGREES),
            ip.Distance(1000.0, KILOMETERS),
        )

        self.assertAlmostEqual(point_a.get_distance_to_point(point_b).meters(), 0.0, places=12)
        self.assertEqual(point_b.copy(), point_b)

    def test_coordinate_conversion_helpers_and_error_path(self):
        point = ip.SurfacePoint(
            ip.Latitude(5.0, DEGREES),
            ip.Longitude(15.0, DEGREES),
            ip.Distance(1000.0, KILOMETERS),
        )

        self.assertIsInstance(point.latitude_to_meters(1.0), float)
        self.assertIsInstance(point.longitude_to_meters(1.0), float)
        self.assertIsInstance(point.meters_to_latitude(1000.0), float)
        self.assertIsInstance(point.meters_to_longitude(1000.0), float)
        self.assertIn("SurfacePoint(lat=", repr(point))

        with self.assertRaises(RuntimeError):
            point.from_naif_array([1.0, 2.0])


if __name__ == "__main__":
    unittest.main()