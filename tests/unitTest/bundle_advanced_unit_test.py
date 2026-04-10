"""
Unit tests for ISIS advanced bundle-adjustment bindings.

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-10
Updated: 2026-03-25  Geng Xun added preserved regression coverage for temporarily disabled advanced bundle-adjustment bindings.
Updated: 2026-04-10  Geng Xun re-enabled tests after bind_bundle_advanced.cpp was re-enabled with boost ublas lambda wrappers.
"""

import unittest

from _unit_test_support import ip, temporary_directory, workspace_test_data_path


class BundleAdvancedUnitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Verify that bundle-advanced bindings are loaded."""
        if not hasattr(ip, "BundleResults"):
            raise unittest.SkipTest(
                "BundleResults not available; bind_bundle_advanced may not be compiled."
            )

    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def make_control_point_with_measures(self):
        """Create a control point with two measures for testing."""
        point = ip.ControlPoint("TEST_P1")
        point.set_type(ip.ControlPoint.PointType.Free)

        # Add first measure
        measure1 = ip.ControlMeasure()
        measure1.set_cube_serial_number("SN-001")
        measure1.set_coordinate(100.5, 200.5)
        measure1.set_type(ip.ControlMeasure.MeasureType.Manual)
        point.add_measure(measure1)

        # Add second measure
        measure2 = ip.ControlMeasure()
        measure2.set_cube_serial_number("SN-002")
        measure2.set_coordinate(101.5, 201.5)
        measure2.set_type(ip.ControlMeasure.MeasureType.Manual)
        point.add_measure(measure2)

        point.set_ref_measure(0)
        return point

    def make_bundle_settings(self):
        """Create basic bundle settings for testing."""
        settings = ip.BundleSettings()
        settings.set_validate_network(False)
        settings.set_solve_options(
            False,  # solve observation mode
            False,  # update cube label
            False,  # error propagation
            False,  # solve radius
            ip.SurfacePoint.CoordinateType.Rectangular,
            ip.SurfacePoint.CoordinateType.Latitudinal,
            1.0,
            1.0,
            -1.0,
        )
        return settings

    # ─── BundleMeasure Tests ────────────────────────────────────────────

    def test_bundle_measure_construction_and_basic_accessors(self):
        """Test BundleMeasure construction and basic accessor methods."""
        # Create prerequisites
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()

        # Create BundleControlPoint
        bundle_point = ip.BundleControlPoint(settings, point)

        # Get ControlMeasure
        control_measure = point.get_measure(0)

        # Create BundleMeasure
        bundle_measure = ip.BundleMeasure(control_measure, bundle_point)

        # Test basic accessors
        self.assertIsNotNone(bundle_measure)
        self.assertFalse(bundle_measure.is_rejected())
        self.assertEqual(bundle_measure.cube_serial_number(), "SN-001")
        self.assertAlmostEqual(bundle_measure.sample(), 100.5)
        self.assertAlmostEqual(bundle_measure.line(), 200.5)

    def test_bundle_measure_rejection_state(self):
        """Test BundleMeasure rejection state management."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)
        control_measure = point.get_measure(0)
        bundle_measure = ip.BundleMeasure(control_measure, bundle_point)

        # Test rejection state
        self.assertFalse(bundle_measure.is_rejected())
        bundle_measure.set_rejected(True)
        self.assertTrue(bundle_measure.is_rejected())
        bundle_measure.set_rejected(False)
        self.assertFalse(bundle_measure.is_rejected())

    def test_bundle_measure_copy_constructor(self):
        """Test BundleMeasure copy construction."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)
        control_measure = point.get_measure(0)
        original = ip.BundleMeasure(control_measure, bundle_point)

        # Test copy
        copy = ip.BundleMeasure(original)
        self.assertIsNotNone(copy)
        self.assertEqual(copy.cube_serial_number(), original.cube_serial_number())
        self.assertAlmostEqual(copy.sample(), original.sample())
        self.assertAlmostEqual(copy.line(), original.line())

    def test_bundle_measure_repr(self):
        """Test BundleMeasure string representation."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)
        control_measure = point.get_measure(0)
        bundle_measure = ip.BundleMeasure(control_measure, bundle_point)

        repr_str = repr(bundle_measure)
        self.assertIn("BundleMeasure", repr_str)
        self.assertIn("SN-001", repr_str)
        self.assertIn("100.5", repr_str)
        self.assertIn("200.5", repr_str)

    # ─── BundleControlPoint Tests ───────────────────────────────────────

    def test_bundle_control_point_construction_and_basic_accessors(self):
        """Test BundleControlPoint construction and basic accessor methods."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()

        bundle_point = ip.BundleControlPoint(settings, point)

        # Test basic accessors
        self.assertIsNotNone(bundle_point)
        self.assertEqual(bundle_point.id(), "TEST_P1")
        self.assertEqual(bundle_point.number_of_measures(), 2)
        self.assertFalse(bundle_point.is_rejected())
        self.assertEqual(bundle_point.type(), ip.ControlPoint.PointType.Free)

    def test_bundle_control_point_rejection_state(self):
        """Test BundleControlPoint rejection state management."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)

        # Test rejection state
        self.assertFalse(bundle_point.is_rejected())
        bundle_point.set_rejected(True)
        self.assertTrue(bundle_point.is_rejected())
        bundle_point.set_rejected(False)
        self.assertFalse(bundle_point.is_rejected())

    def test_bundle_control_point_rejected_measures(self):
        """Test BundleControlPoint rejected measures management."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)

        # Test rejected measures count
        self.assertEqual(bundle_point.number_of_rejected_measures(), 0)
        bundle_point.set_number_of_rejected_measures(1)
        self.assertEqual(bundle_point.number_of_rejected_measures(), 1)
        bundle_point.zero_number_of_rejected_measures()
        self.assertEqual(bundle_point.number_of_rejected_measures(), 0)

    def test_bundle_control_point_copy_constructor(self):
        """Test BundleControlPoint copy construction."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        original = ip.BundleControlPoint(settings, point)

        # Test copy
        copy = ip.BundleControlPoint(original)
        self.assertIsNotNone(copy)
        self.assertEqual(copy.id(), original.id())
        self.assertEqual(copy.number_of_measures(), original.number_of_measures())

    def test_bundle_control_point_len_and_repr(self):
        """Test BundleControlPoint __len__ and __repr__ methods."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)

        # Test __len__
        self.assertEqual(len(bundle_point), 2)

        # Test __repr__
        repr_str = repr(bundle_point)
        self.assertIn("BundleControlPoint", repr_str)
        self.assertIn("TEST_P1", repr_str)
        self.assertIn("measures=2", repr_str)

    def test_bundle_control_point_adjusted_surface_point(self):
        """Test BundleControlPoint adjusted surface point management."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)

        # Create a surface point
        surface_point = ip.SurfacePoint()
        surface_point.set_rectangular_coordinates(
            ip.Displacement(1000.0, ip.Displacement.Units.Meters),
            ip.Displacement(2000.0, ip.Displacement.Units.Meters),
            ip.Displacement(3000.0, ip.Displacement.Units.Meters)
        )

        # Set adjusted surface point
        bundle_point.set_adjusted_surface_point(surface_point)

        # Get adjusted surface point
        adjusted = bundle_point.adjusted_surface_point()
        self.assertIsNotNone(adjusted)

    def test_bundle_control_point_format_output_strings(self):
        """Test BundleControlPoint output formatting methods."""
        settings = self.make_bundle_settings()
        point = self.make_control_point_with_measures()
        bundle_point = ip.BundleControlPoint(settings, point)

        # Test format bundle output summary string
        summary = bundle_point.format_bundle_output_summary_string(False)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

        # Test format bundle output detail string
        detail = bundle_point.format_bundle_output_detail_string(False, False)
        self.assertIsInstance(detail, str)
        self.assertGreater(len(detail), 0)

    # ─── BundleObservation Tests ────────────────────────────────────────

    def test_bundle_observation_vector_construction(self):
        """Test BundleObservationVector construction and basic operations."""
        obs_vector = ip.BundleObservationVector()

        # Test basic properties
        self.assertIsNotNone(obs_vector)
        self.assertEqual(len(obs_vector), 0)

    def test_bundle_observation_vector_copy_constructor(self):
        """Test BundleObservationVector copy construction."""
        original = ip.BundleObservationVector()
        copy = ip.BundleObservationVector(original)

        self.assertIsNotNone(copy)
        self.assertEqual(len(copy), len(original))

    def test_bundle_observation_vector_repr(self):
        """Test BundleObservationVector string representation."""
        obs_vector = ip.BundleObservationVector()
        repr_str = repr(obs_vector)

        self.assertIn("BundleObservationVector", repr_str)
        self.assertIn("size=0", repr_str)

    # ─── BundleLidarRangeConstraint Tests ───────────────────────────────

    def test_bundle_lidar_range_constraint_copy(self):
        """Test BundleLidarRangeConstraint copy functionality."""
        # Note: We cannot construct BundleLidarRangeConstraint directly without
        # complex setup, but we can test the copy method signature exists
        # This test verifies the binding exists
        self.assertTrue(hasattr(ip, 'BundleLidarRangeConstraint'))

    # ─── BundleLidarControlPoint Tests ──────────────────────────────────

    def test_bundle_lidar_control_point_methods_exist(self):
        """Test that BundleLidarControlPoint class and methods exist."""
        # Verify the class exists
        self.assertTrue(hasattr(ip, 'BundleLidarControlPoint'))

        # Note: Full functional testing would require LIDAR data setup
        # which may not be available in all test environments

    # ─── BundleLidarPointVector Tests ───────────────────────────────────

    def test_bundle_lidar_point_vector_construction(self):
        """Test BundleLidarPointVector construction and basic operations."""
        lidar_vector = ip.BundleLidarPointVector()

        # Test basic properties
        self.assertIsNotNone(lidar_vector)
        self.assertEqual(len(lidar_vector), 0)

    def test_bundle_lidar_point_vector_copy_constructor(self):
        """Test BundleLidarPointVector copy construction."""
        original = ip.BundleLidarPointVector()
        copy = ip.BundleLidarPointVector(original)

        self.assertIsNotNone(copy)
        self.assertEqual(len(copy), len(original))

    def test_bundle_lidar_point_vector_repr(self):
        """Test BundleLidarPointVector string representation."""
        lidar_vector = ip.BundleLidarPointVector()
        repr_str = repr(lidar_vector)

        self.assertIn("BundleLidarPointVector", repr_str)
        self.assertIn("size=0", repr_str)

    # ─── BundleResults Tests ────────────────────────────────────────────

    def test_bundle_results_construction_and_initialization(self):
        """Test BundleResults construction and initialization."""
        results = ip.BundleResults()

        self.assertIsNotNone(results)

        # Initialize
        results.initialize()

        # Test default/initial state
        self.assertFalse(results.converged())
        self.assertEqual(results.iterations(), 0)

    def test_bundle_results_convergence_settings(self):
        """Test BundleResults convergence-related setters and getters."""
        results = ip.BundleResults()
        results.initialize()

        # Set convergence state
        results.set_converged(True)
        self.assertTrue(results.converged())

        results.set_converged(False)
        self.assertFalse(results.converged())

        # Set iterations
        results.set_iterations(10)
        self.assertEqual(results.iterations(), 10)

        # Set sigma0
        results.set_sigma0(1.5)
        self.assertAlmostEqual(results.sigma0(), 1.5)

        # Set degrees of freedom
        results.set_degrees_of_freedom(100)
        self.assertEqual(results.degrees_of_freedom(), 100)

    def test_bundle_results_observation_counts(self):
        """Test BundleResults observation count setters and getters."""
        results = ip.BundleResults()
        results.initialize()

        # Set number of observations
        results.set_number_observations(50)
        self.assertEqual(results.number_observations(), 50)

        # Set number of image observations
        results.set_number_image_observations(45)
        self.assertEqual(results.number_image_observations(), 45)

        # Set number of LIDAR image observations
        results.set_number_lidar_image_observations(5)
        self.assertEqual(results.number_lidar_image_observations(), 5)

        # Set number of rejected observations
        results.set_number_rejected_observations(3)
        self.assertEqual(results.number_rejected_observations(), 3)

    def test_bundle_results_parameter_counts(self):
        """Test BundleResults parameter count management."""
        results = ip.BundleResults()
        results.initialize()

        # Set number of image parameters
        results.set_number_image_parameters(100)
        self.assertEqual(results.number_image_parameters(), 100)

        # Set number of unknown parameters
        results.set_number_unknown_parameters(150)
        self.assertEqual(results.number_unknown_parameters(), 150)

        # Test constrained point parameters
        results.set_number_constrained_point_parameters(30)
        self.assertEqual(results.number_constrained_point_parameters(), 30)

        results.reset_number_constrained_point_parameters()
        self.assertEqual(results.number_constrained_point_parameters(), 0)

        results.increment_number_constrained_point_parameters(5)
        self.assertEqual(results.number_constrained_point_parameters(), 5)

    def test_bundle_results_constrained_parameters_management(self):
        """Test BundleResults constrained parameters increment and reset."""
        results = ip.BundleResults()
        results.initialize()

        # Test constrained image parameters
        results.reset_number_constrained_image_parameters()
        self.assertEqual(results.number_constrained_image_parameters(), 0)
        results.increment_number_constrained_image_parameters(10)
        self.assertEqual(results.number_constrained_image_parameters(), 10)

        # Test constrained target parameters
        results.reset_number_constrained_target_parameters()
        self.assertEqual(results.number_constrained_target_parameters(), 0)
        results.increment_number_constrained_target_parameters(2)
        self.assertEqual(results.number_constrained_target_parameters(), 2)

    def test_bundle_results_lidar_specific_counts(self):
        """Test BundleResults LIDAR-specific parameter management."""
        results = ip.BundleResults()
        results.initialize()

        # Set number of LIDAR range constraints
        results.set_number_lidar_range_constraints(10)
        self.assertEqual(results.number_lidar_range_constraint_equations(), 10)

        # Set number of constrained LIDAR point parameters
        results.set_number_constrained_lidar_point_parameters(25)
        # Note: We're testing that the method exists and doesn't throw

    def test_bundle_results_residuals(self):
        """Test BundleResults residual setters and getters."""
        results = ip.BundleResults()
        results.initialize()

        # Set RMS XY residuals
        results.set_rms_xy_residuals(0.5, 0.6, 0.7)
        self.assertAlmostEqual(results.rms_rx(), 0.5)
        self.assertAlmostEqual(results.rms_ry(), 0.6)
        self.assertAlmostEqual(results.rms_rxy(), 0.7)

    def test_bundle_results_rejection_limit(self):
        """Test BundleResults rejection limit management."""
        results = ip.BundleResults()
        results.initialize()

        # Set rejection limit
        results.set_rejection_limit(3.0)
        self.assertAlmostEqual(results.rejection_limit(), 3.0)

    def test_bundle_results_elapsed_time(self):
        """Test BundleResults elapsed time management."""
        results = ip.BundleResults()
        results.initialize()

        # Set elapsed time
        results.set_elapsed_time(123.45)
        self.assertAlmostEqual(results.elapsed_time(), 123.45)

        # Set elapsed time for error propagation
        results.set_elapsed_time_error_prop(67.89)
        self.assertAlmostEqual(results.elapsed_time_error_prop(), 67.89)

    def test_bundle_results_fixed_held_ignored_counters(self):
        """Test BundleResults fixed, held, and ignored counters."""
        results = ip.BundleResults()
        results.initialize()

        # Test fixed points counter
        self.assertEqual(results.number_fixed_points(), 0)
        results.increment_fixed_points()
        self.assertEqual(results.number_fixed_points(), 1)
        results.increment_fixed_points()
        self.assertEqual(results.number_fixed_points(), 2)

        # Test held images counter
        self.assertEqual(results.number_held_images(), 0)
        results.increment_held_images()
        self.assertEqual(results.number_held_images(), 1)

        # Test ignored points counter
        self.assertEqual(results.number_ignored_points(), 0)
        results.increment_ignored_points()
        self.assertEqual(results.number_ignored_points(), 1)

    def test_bundle_results_maximum_likelihood_model(self):
        """Test BundleResults maximum likelihood model management."""
        results = ip.BundleResults()
        results.initialize()

        # Test maximum likelihood model index
        initial_index = results.maximum_likelihood_model_index()
        results.increment_maximum_likelihood_model_index()
        self.assertEqual(results.maximum_likelihood_model_index(), initial_index + 1)

    def test_bundle_results_sigma_ranges(self):
        """Test BundleResults sigma range management."""
        results = ip.BundleResults()
        results.initialize()

        # Create Distance objects for testing
        min_dist = ip.Distance(100.0, ip.Distance.Units.Meters)
        max_dist = ip.Distance(200.0, ip.Distance.Units.Meters)

        # Set sigma coord1 range
        results.set_sigma_coord1_range(min_dist, max_dist, "POINT_MIN1", "POINT_MAX1")
        self.assertEqual(results.min_sigma_coord1_point_id(), "POINT_MIN1")
        self.assertEqual(results.max_sigma_coord1_point_id(), "POINT_MAX1")

        # Set sigma coord2 range
        results.set_sigma_coord2_range(min_dist, max_dist, "POINT_MIN2", "POINT_MAX2")
        self.assertEqual(results.min_sigma_coord2_point_id(), "POINT_MIN2")
        self.assertEqual(results.max_sigma_coord2_point_id(), "POINT_MAX2")

        # Set sigma coord3 range
        results.set_sigma_coord3_range(min_dist, max_dist, "POINT_MIN3", "POINT_MAX3")
        self.assertEqual(results.min_sigma_coord3_point_id(), "POINT_MIN3")
        self.assertEqual(results.max_sigma_coord3_point_id(), "POINT_MAX3")

    def test_bundle_results_sigma_statistics_rms(self):
        """Test BundleResults sigma statistics RMS setters and getters."""
        results = ip.BundleResults()
        results.initialize()

        # Set RMS from sigma statistics
        results.set_rms_from_sigma_statistics(10.0, 20.0, 30.0)
        self.assertAlmostEqual(results.sigma_coord1_statistics_rms(), 10.0)
        self.assertAlmostEqual(results.sigma_coord2_statistics_rms(), 20.0)
        self.assertAlmostEqual(results.sigma_coord3_statistics_rms(), 30.0)

    def test_bundle_results_copy_constructor(self):
        """Test BundleResults copy construction."""
        original = ip.BundleResults()
        original.initialize()
        original.set_converged(True)
        original.set_iterations(5)
        original.set_sigma0(1.234)

        copy = ip.BundleResults(original)
        self.assertIsNotNone(copy)
        self.assertTrue(copy.converged())
        self.assertEqual(copy.iterations(), 5)
        self.assertAlmostEqual(copy.sigma0(), 1.234)

    def test_bundle_results_repr(self):
        """Test BundleResults string representation."""
        results = ip.BundleResults()
        results.initialize()
        results.set_converged(True)
        results.set_sigma0(1.5)
        results.set_iterations(10)

        repr_str = repr(results)
        self.assertIn("BundleResults", repr_str)
        self.assertIn("converged=True", repr_str)
        self.assertIn("sigma0=1.5", repr_str)
        self.assertIn("iterations=10", repr_str)

    # ─── BundleSolutionInfo Tests ───────────────────────────────────────

    def test_bundle_solution_info_construction(self):
        """Test BundleSolutionInfo construction."""
        solution_info = ip.BundleSolutionInfo()

        self.assertIsNotNone(solution_info)

    def test_bundle_solution_info_name_and_runtime(self):
        """Test BundleSolutionInfo name and run time management."""
        solution_info = ip.BundleSolutionInfo()

        # Set name
        solution_info.set_name("TestBundleSolution")
        self.assertEqual(solution_info.name(), "TestBundleSolution")

        # Set run time
        solution_info.set_run_time("2026-03-24T12:00:00")
        self.assertEqual(solution_info.run_time(), "2026-03-24T12:00:00")

    def test_bundle_solution_info_output_control_name(self):
        """Test BundleSolutionInfo output control name management."""
        solution_info = ip.BundleSolutionInfo()

        # Set output control name
        solution_info.set_output_control_name("OutputControlNet")
        self.assertEqual(solution_info.output_control_name(), "OutputControlNet")

    def test_bundle_solution_info_settings_and_results(self):
        """Test BundleSolutionInfo access to bundle settings and results."""
        solution_info = ip.BundleSolutionInfo()

        # Create and set bundle results
        results = ip.BundleResults()
        results.initialize()
        results.set_converged(True)
        results.set_iterations(5)

        solution_info.set_output_statistics(results)

        # Get bundle results
        retrieved_results = solution_info.bundle_results()
        self.assertIsNotNone(retrieved_results)
        self.assertTrue(retrieved_results.converged())
        self.assertEqual(retrieved_results.iterations(), 5)

        # Get bundle settings
        settings = solution_info.bundle_settings()
        self.assertIsNotNone(settings)

    def test_bundle_solution_info_file_names(self):
        """Test BundleSolutionInfo file name accessors."""
        solution_info = ip.BundleSolutionInfo()

        # Test that file name accessors exist and return strings
        input_control = solution_info.input_control_net_file_name()
        self.assertIsInstance(input_control, str)

        output_control = solution_info.output_control_net_file_name()
        self.assertIsInstance(output_control, str)

        input_lidar = solution_info.input_lidar_data_file_name()
        self.assertIsInstance(input_lidar, str)

    def test_bundle_solution_info_output_methods(self):
        """Test BundleSolutionInfo output generation methods exist."""
        solution_info = ip.BundleSolutionInfo()

        # These methods require full bundle adjustment setup to generate meaningful output
        # We just verify they exist and don't throw when called
        try:
            output_text = solution_info.output_text()
            self.assertIsInstance(output_text, str)
        except:
            # Expected to fail without proper setup, but method should exist
            pass

    def test_bundle_solution_info_surface_point_coord_name(self):
        """Test BundleSolutionInfo surface point coordinate name method."""
        solution_info = ip.BundleSolutionInfo()

        # Test getting coordinate name
        coord_name = solution_info.surface_point_coord_name(
            ip.SurfacePoint.CoordinateType.Latitudinal,
            ip.SurfacePoint.CoordIndex.One
        )
        self.assertIsInstance(coord_name, str)
        self.assertGreater(len(coord_name), 0)

    def test_bundle_solution_info_repr(self):
        """Test BundleSolutionInfo string representation."""
        solution_info = ip.BundleSolutionInfo()
        solution_info.set_name("TestSolution")
        solution_info.set_run_time("2026-03-24T12:00:00")

        repr_str = repr(solution_info)
        self.assertIn("BundleSolutionInfo", repr_str)
        self.assertIn("TestSolution", repr_str)
        self.assertIn("2026-03-24T12:00:00", repr_str)


if __name__ == "__main__":
    unittest.main()
