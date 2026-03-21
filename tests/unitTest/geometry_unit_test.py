import unittest

from _unit_test_support import ip, workspace_test_data_path


MDIS_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")


class GeometryUnitTest(unittest.TestCase):
    def open_cube_or_skip(self):
        if not MDIS_CUBE.exists():
            self.skipTest(f"Required cube is unavailable in this environment: {MDIS_CUBE}")

        cube = ip.Cube()
        cube.open(str(MDIS_CUBE), "r")
        self.addCleanup(cube.close)
        return cube

    def test_transform_default_behavior_matches_wrapper_contract(self):
        transform = ip.Transform()

        self.assertEqual(transform.output_samples(), 0)
        self.assertEqual(transform.output_lines(), 0)

        success, in_sample, in_line = transform.xform(12.5, 7.5)
        self.assertTrue(success)
        self.assertEqual(in_sample, 0.0)
        self.assertEqual(in_line, 0.0)
        self.assertIn("Transform(", repr(transform))

    def test_interpolator_requires_type_before_dimension_queries(self):
        interpolator = ip.Interpolator()

        with self.assertRaises(ip.IException):
            interpolator.samples()

        with self.assertRaises(ip.IException):
            interpolator.lines()

    def test_interpolator_nearest_neighbor_and_bilinear_paths(self):
        nearest = ip.Interpolator(ip.Interpolator.InterpType.NearestNeighborType)
        self.assertEqual(nearest.samples(), 1)
        self.assertEqual(nearest.lines(), 1)
        self.assertAlmostEqual(nearest.hot_sample(), -0.5, places=12)
        self.assertAlmostEqual(nearest.hot_line(), -0.5, places=12)
        self.assertAlmostEqual(nearest.interpolate(10.2, 20.7, [42.5]), 42.5, places=12)

        bilinear = ip.Interpolator(ip.Interpolator.InterpType.BiLinearType)
        self.assertEqual(bilinear.samples(), 2)
        self.assertEqual(bilinear.lines(), 2)
        self.assertAlmostEqual(bilinear.hot_sample(), 0.0, places=12)
        self.assertAlmostEqual(bilinear.hot_line(), 0.0, places=12)

        value = bilinear.interpolate(1.25, 2.75, [10.0, 20.0, 30.0, 50.0])
        self.assertAlmostEqual(value, 29.375, places=12)

    def test_interpolator_cubic_metadata_and_buffer_validation(self):
        cubic = ip.Interpolator()
        cubic.set_type(ip.Interpolator.InterpType.CubicConvolutionType)

        self.assertEqual(cubic.samples(), 4)
        self.assertEqual(cubic.lines(), 4)
        self.assertAlmostEqual(cubic.hot_sample(), 1.0, places=12)
        self.assertAlmostEqual(cubic.hot_line(), 1.0, places=12)

        with self.assertRaisesRegex(RuntimeError, "buffer size mismatch"):
            cubic.interpolate(1.25, 1.25, [1.0] * 15)

    def test_enlarge_construction_xform_and_subarea(self):
        cube = self.open_cube_or_skip()

        enlarge = ip.Enlarge(cube, 2.0, 1.5)

        self.assertIsInstance(enlarge, ip.Transform)
        self.assertEqual(enlarge.output_samples(), 2048)
        self.assertEqual(enlarge.output_lines(), 1536)

        success, in_sample, in_line = enlarge.xform(1.0, 1.0)
        self.assertTrue(success)
        self.assertAlmostEqual(in_sample, 0.75, places=12)
        self.assertAlmostEqual(in_line, 0.8333333333333334, places=12)

        enlarge.set_input_area(101, 200, 51, 150)
        self.assertEqual(enlarge.output_samples(), 200)
        self.assertEqual(enlarge.output_lines(), 150)

        success, in_sample, in_line = enlarge.xform(1.0, 1.0)
        self.assertTrue(success)
        self.assertAlmostEqual(in_sample, 100.75, places=12)
        self.assertAlmostEqual(in_line, 50.833333333333336, places=12)

        with self.assertRaises(ip.IException):
            enlarge.set_input_area(10, 5, 1, 2)

        self.assertIn("Enlarge(", repr(enlarge))

    def test_reduce_construction_and_boundary_mutator(self):
        cube = self.open_cube_or_skip()

        reduce_obj = ip.Reduce(cube, 2.0, 4.0)

        reduce_obj.set_input_boundary(101, 500, 21, 220)

        self.assertIn("Reduce(", repr(reduce_obj))


if __name__ == "__main__":
    unittest.main()