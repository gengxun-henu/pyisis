"""
Unit tests for ISIS control-core bindings.

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-08
Updated: 2026-04-08  Geng Xun added ControlNetStatistics summary/getter regression coverage and retained control-core helper checks.
"""

import gc
import math
import unittest

from _unit_test_support import ip, temporary_directory, workspace_test_data_path


class ControlCoreUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def make_control_point_v0001_object(self):
        pvl = ip.Pvl()
        pvl.from_string(
            """
Object = ControlPoint
    PointId = CPV1
    PointType = Ground
    X = 1000.0
    Y = 2000.0
    Z = 3000.0
    Group = Measure
        SerialNumber = SN-V1
        Sample = 10.5
        Line = 20.5
        AprioriSample = 10.5
        AprioriLine = 20.5
        SampleSigma = 0.5
        LineSigma = 0.5
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.9
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")

    def make_control_point_v0002_object(self):
        pvl = ip.Pvl()
        pvl.from_string(
            """
Object = ControlPoint
    PointId = CPV2
    PointType = Ground
    AprioriX = 1000.0
    AprioriY = 2000.0
    AprioriZ = 3000.0
    AdjustedX = 1001.0
    AdjustedY = 2001.0
    AdjustedZ = 3001.0
    Group = Measure
        SerialNumber = SN-V2
        Sample = 11.5
        Line = 21.5
        SampleResidual = 0.0
        LineResidual = 0.0
        AprioriSample = 11.5
        AprioriLine = 21.5
        SampleSigma = 0.25
        LineSigma = 0.25
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.8
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")

    def make_control_point_v0003_object(self):
        pvl = ip.Pvl()
        pvl.from_string(
            """
Object = ControlPoint
    PointId = CPV3
    PointType = Fixed
    AprioriX = 1100.0
    AprioriY = 2100.0
    AprioriZ = 3100.0
    AdjustedX = 1101.0
    AdjustedY = 2101.0
    AdjustedZ = 3101.0
    Group = Measure
        SerialNumber = SN-V3
        Sample = 12.5
        Line = 22.5
        SampleResidual = 0.1
        LineResidual = 0.2
        AprioriSample = 12.4
        AprioriLine = 22.4
        SampleSigma = 0.2
        LineSigma = 0.2
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.7
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")

    def make_control_net_filter_fixture(self):
        cube_path = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
        serial_number = ip.SerialNumber.compose(str(cube_path))

        net = ip.ControlNet()

        locked_point = ip.ControlPoint("LOCKED")
        locked_point.set_type(ip.ControlPoint.PointType.Fixed)
        locked_point.set_edit_lock(True)
        locked_measure = ip.ControlMeasure()
        locked_measure.set_cube_serial_number(serial_number)
        locked_measure.set_coordinate(10.0, 20.0)
        locked_measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        locked_point.add_measure(locked_measure)
        locked_point.set_ref_measure(0)
        net.add_point(locked_point)

        free_point = ip.ControlPoint("FREE")
        free_point.set_type(ip.ControlPoint.PointType.Free)
        free_point.set_edit_lock(False)
        free_measure = ip.ControlMeasure()
        free_measure.set_cube_serial_number(serial_number)
        free_measure.set_coordinate(30.0, 40.0)
        free_measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        free_point.add_measure(free_measure)
        free_point.set_ref_measure(0)
        net.add_point(free_point)

        return net, cube_path, serial_number

    def make_point_edit_lock_group(self, value):
        group = ip.PvlGroup("Point_EditLock")
        group.add_keyword(ip.PvlKeyword("EditLock", "True" if value else "False"))
        return group

    def make_less_greater_group(self, name, less_than=None, greater_than=None):
        group = ip.PvlGroup(name)
        if less_than is not None:
            group.add_keyword(ip.PvlKeyword("LessThan", str(less_than)))
        if greater_than is not None:
            group.add_keyword(ip.PvlKeyword("GreaterThan", str(greater_than)))
        return group

    def make_expression_group(self, name, expression):
        group = ip.PvlGroup(name)
        group.add_keyword(ip.PvlKeyword("Expression", expression))
        return group

    def make_point_properties_group(self, point_type=None, ignore=None):
        group = ip.PvlGroup("Point_Properties")
        if point_type is not None:
            group.add_keyword(ip.PvlKeyword("PointType", point_type))
        if ignore is not None:
            group.add_keyword(ip.PvlKeyword("Ignore", "True" if ignore else "False"))
        return group

    def make_control_net_filter_count_fixture(self):
        cube1_path = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
        cube2_path = workspace_test_data_path("mosrange", "EN0108828327M_iof.cub")
        serial1 = ip.SerialNumber.compose(str(cube1_path))
        serial2 = ip.SerialNumber.compose(str(cube2_path))

        net = ip.ControlNet()

        point_two_measures = ip.ControlPoint("KEEP2")
        point_two_measures.set_type(ip.ControlPoint.PointType.Free)

        measure1 = ip.ControlMeasure()
        measure1.set_cube_serial_number(serial1)
        measure1.set_coordinate(10.0, 20.0)
        measure1.set_type(ip.ControlMeasure.MeasureType.Manual)
        point_two_measures.add_measure(measure1)

        measure2 = ip.ControlMeasure()
        measure2.set_cube_serial_number(serial2)
        measure2.set_coordinate(11.0, 21.0)
        measure2.set_type(ip.ControlMeasure.MeasureType.Manual)
        point_two_measures.add_measure(measure2)
        point_two_measures.set_ref_measure(0)
        net.add_point(point_two_measures)

        point_one_measure = ip.ControlPoint("DROP1")
        point_one_measure.set_type(ip.ControlPoint.PointType.Fixed)
        point_one_measure.set_edit_lock(False)
        measure3 = ip.ControlMeasure()
        measure3.set_cube_serial_number(serial1)
        measure3.set_coordinate(30.0, 40.0)
        measure3.set_type(ip.ControlMeasure.MeasureType.Manual)
        point_one_measure.add_measure(measure3)
        point_one_measure.set_ref_measure(0)
        net.add_point(point_one_measure)

        return net, (cube1_path, cube2_path), (serial1, serial2)

    def make_control_net_statistics_fixture(self):
        net = ip.ControlNet()

        fixed_point = ip.ControlPoint("FIXED")
        fixed_point.set_type(ip.ControlPoint.PointType.Fixed)
        fixed_point.set_edit_lock(True)

        measure1 = ip.ControlMeasure()
        measure1.set_cube_serial_number("SN-A")
        measure1.set_coordinate(10.0, 20.0)
        measure1.set_apriori_sample(9.0)
        measure1.set_apriori_line(18.0)
        measure1.set_residual(3.0, 4.0)
        measure1.set_type(ip.ControlMeasure.MeasureType.Manual)
        fixed_point.add_measure(measure1)

        measure2 = ip.ControlMeasure()
        measure2.set_cube_serial_number("SN-B")
        measure2.set_coordinate(5.0, 8.0)
        measure2.set_apriori_sample(4.5)
        measure2.set_apriori_line(7.0)
        measure2.set_residual(-1.0, 2.0)
        measure2.set_edit_lock(True)
        measure2.set_type(ip.ControlMeasure.MeasureType.Manual)
        fixed_point.add_measure(measure2)
        fixed_point.set_ref_measure(0)
        net.add_point(fixed_point)

        free_point = ip.ControlPoint("FREE")
        free_point.set_type(ip.ControlPoint.PointType.Free)

        measure3 = ip.ControlMeasure()
        measure3.set_cube_serial_number("SN-C")
        measure3.set_coordinate(30.0, 40.0)
        measure3.set_apriori_sample(31.0)
        measure3.set_apriori_line(39.0)
        measure3.set_residual(-2.0, -6.0)
        measure3.set_type(ip.ControlMeasure.MeasureType.Manual)
        free_point.add_measure(measure3)
        free_point.set_ref_measure(0)
        net.add_point(free_point)

        ignored_point = ip.ControlPoint("IGNORED")
        ignored_point.set_type(ip.ControlPoint.PointType.Constrained)
        ignored_point.set_ignored(True)

        ignored_measure = ip.ControlMeasure()
        ignored_measure.set_cube_serial_number("SN-D")
        ignored_measure.set_coordinate(50.0, 60.0)
        ignored_measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        ignored_measure.set_ignored(True)
        ignored_point.add_measure(ignored_measure)
        ignored_point.set_ref_measure(0)
        net.add_point(ignored_point)

        return net

    def test_bundle_target_body_minimal_configuration(self):
        target_body = ip.BundleTargetBody()
        target_body.set_solve_settings(
            [
                ip.BundleTargetBody.TargetSolveCodes.PoleRA,
                ip.BundleTargetBody.TargetSolveCodes.PoleDec,
                ip.BundleTargetBody.TargetSolveCodes.PM,
                ip.BundleTargetBody.TargetSolveCodes.MeanRadius,
            ],
            ip.Angle(10.0, ip.Angle.Units.Degrees),
            ip.Angle(0.1, ip.Angle.Units.Degrees),
            ip.Angle(1.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(20.0, ip.Angle.Units.Degrees),
            ip.Angle(0.2, ip.Angle.Units.Degrees),
            ip.Angle(2.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(30.0, ip.Angle.Units.Degrees),
            ip.Angle(0.3, ip.Angle.Units.Degrees),
            ip.Angle(3.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.BundleTargetBody.TargetRadiiSolveMethod.Mean,
            ip.Distance(1000.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1001.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1002.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1003.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.5, ip.Distance.Units.Kilometers),
        )

        self.assertEqual(target_body.number_parameters(), 4)
        self.assertEqual(target_body.number_radius_parameters(), 1)
        self.assertTrue(target_body.solve_pole_ra())
        self.assertFalse(target_body.solve_pole_ra_velocity())
        self.assertTrue(target_body.solve_pole_dec())
        self.assertTrue(target_body.solve_pm())
        self.assertFalse(target_body.solve_triaxial_radii())
        self.assertTrue(target_body.solve_mean_radius())
        self.assertEqual(
            ip.BundleTargetBody.target_radii_option_to_string(
                ip.BundleTargetBody.TargetRadiiSolveMethod.Mean
            ),
            "MeanRadius",
        )
        self.assertEqual(
            ip.BundleTargetBody.string_to_target_radii_option("ALL"),
            ip.BundleTargetBody.TargetRadiiSolveMethod.All,
        )
        self.assertAlmostEqual(target_body.pole_ra_coefs()[0].degrees(), 10.0)
        self.assertAlmostEqual(target_body.pole_dec_coefs()[0].degrees(), 20.0)
        self.assertAlmostEqual(target_body.pm_coefs()[0].degrees(), 30.0)
        self.assertAlmostEqual(target_body.mean_radius().kilometers(), 1003.0)

        formatted = target_body.format_bundle_output_string(False)
        self.assertIn("POLE RA", formatted)
        self.assertIn("MeanRadius", formatted)
        self.assertIn("0.1", formatted)
        self.assertIn("N/A", formatted)
        self.assertEqual(
            [entry.strip() for entry in target_body.parameter_list()],
            ["POLE RA", "POLE DEC", "PM", "MeanRadius"],
        )

    def test_bundle_observation_solve_settings_round_trip(self):
        settings = ip.BundleObservationSolveSettings()
        settings.set_instrument_id("MDIS-WAC")
        settings.add_observation_number("OBS-2")
        settings.add_observation_number("OBS-1")
        settings.set_csm_solve_set(
            ip.BundleObservationSolveSettings.CSMSolveSet.ADJUSTABLE
        )
        settings.set_csm_solve_parameter_list(["PARAM_A", "PARAM_B"])
        settings.set_instrument_pointing_settings(
            ip.BundleObservationSolveSettings.InstrumentPointingSolveOption.AnglesVelocityAcceleration,
            True,
            2,
            2,
            True,
            0.1,
            0.2,
            0.3,
            [0.4],
        )
        settings.set_instrument_position_settings(
            ip.BundleObservationSolveSettings.InstrumentPositionSolveOption.PositionVelocity,
            2,
            2,
            False,
            10.0,
            20.0,
            -1.0,
            [30.0],
        )

        self.assertEqual(settings.instrument_id(), "MDIS-WAC")
        self.assertEqual(settings.observation_numbers(), ["OBS-1", "OBS-2"])
        self.assertEqual(
            settings.csm_solve_option(),
            ip.BundleObservationSolveSettings.CSMSolveOption.List,
        )
        self.assertEqual(settings.csm_parameter_set(), ip.BundleObservationSolveSettings.CSMSolveSet.ADJUSTABLE)
        self.assertEqual(settings.csm_parameter_list(), ["PARAM_A", "PARAM_B"])
        self.assertEqual(
            ip.BundleObservationSolveSettings.csm_solve_set_to_string(
                ip.BundleObservationSolveSettings.CSMSolveSet.NON_ADJUSTABLE
            ),
            "NON_ADJUSTABLE",
        )
        self.assertEqual(
            ip.BundleObservationSolveSettings.string_to_csm_solve_type("REAL"),
            ip.BundleObservationSolveSettings.CSMSolveType.REAL,
        )
        self.assertEqual(
            settings.instrument_pointing_solve_option(),
            ip.BundleObservationSolveSettings.InstrumentPointingSolveOption.AnglesVelocityAcceleration,
        )
        self.assertTrue(settings.solve_twist())
        self.assertTrue(settings.solve_poly_over_pointing())
        self.assertEqual(settings.number_camera_angle_coefficients_solved(), 3)
        self.assertEqual(settings.apriori_pointing_sigmas(), [0.1, 0.2, 0.3, 0.4])
        self.assertEqual(
            settings.pointing_interpolation_type(),
            ip.BundleObservationSolveSettings.PointingInterpolationType.PolyFunctionOverSpice,
        )
        self.assertEqual(
            settings.instrument_position_solve_option(),
            ip.BundleObservationSolveSettings.InstrumentPositionSolveOption.PositionVelocity,
        )
        self.assertFalse(settings.solve_position_over_hermite())
        self.assertEqual(settings.number_camera_position_coefficients_solved(), 2)
        self.assertEqual(settings.apriori_position_sigmas(), [10.0, 20.0, 30.0])
        self.assertEqual(
            settings.position_interpolation_type(),
            ip.BundleObservationSolveSettings.PositionInterpolationType.PolyFunction,
        )

    def test_bundle_settings_basic_configuration(self):
        settings = ip.BundleSettings()

        self.assertTrue(settings.validate_network())
        self.assertEqual(settings.number_solve_settings(), 1)
        self.assertFalse(settings.solve_target_body())
        self.assertEqual(settings.number_target_body_parameters(), 0)
        self.assertIsNone(settings.bundle_target_body())

        settings.set_validate_network(False)
        settings.set_solve_options(
            True,
            True,
            True,
            False,
            ip.SurfacePoint.CoordinateType.Rectangular,
            ip.SurfacePoint.CoordinateType.Latitudinal,
            1.25,
            2.5,
            -1.0,
        )
        settings.set_create_inverse_matrix(True)
        settings.set_outlier_rejection(True, 2.75)
        settings.set_convergence_criteria(
            ip.BundleSettings.ConvergenceCriteria.ParameterCorrections,
            1.0e-6,
            15,
        )
        settings.add_maximum_likelihood_estimator_model(
            ip.BundleSettings.MaximumLikelihoodModel.Huber,
            1.345,
        )
        settings.set_output_file_prefix("bundle/run_")
        settings.set_cube_list("cubes.lis")

        observation_settings = ip.BundleObservationSolveSettings()
        observation_settings.set_instrument_id("CTX")
        observation_settings.add_observation_number("OBS-CTX-1")
        settings.set_observation_solve_options([observation_settings])

        target_body = ip.BundleTargetBody()
        target_body.set_solve_settings(
            [
                ip.BundleTargetBody.TargetSolveCodes.PoleRA,
                ip.BundleTargetBody.TargetSolveCodes.MeanRadius,
            ],
            ip.Angle(5.0, ip.Angle.Units.Degrees),
            ip.Angle(0.1, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.BundleTargetBody.TargetRadiiSolveMethod.Mean,
            ip.Distance(1000.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1001.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1002.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1003.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.5, ip.Distance.Units.Kilometers),
        )
        settings.set_bundle_target_body(target_body)

        self.assertFalse(settings.validate_network())
        self.assertTrue(settings.solve_observation_mode())
        self.assertTrue(settings.update_cube_label())
        self.assertTrue(settings.error_propagation())
        self.assertTrue(settings.create_inverse_matrix())
        self.assertFalse(settings.solve_radius())
        self.assertEqual(
            settings.control_point_coord_type_bundle(),
            ip.SurfacePoint.CoordinateType.Rectangular,
        )
        self.assertEqual(
            settings.control_point_coord_type_reports(),
            ip.SurfacePoint.CoordinateType.Latitudinal,
        )
        self.assertAlmostEqual(settings.global_point_coord1_apriori_sigma(), 1.25)
        self.assertAlmostEqual(settings.global_point_coord2_apriori_sigma(), 2.5)
        self.assertTrue(settings.outlier_rejection())
        self.assertAlmostEqual(settings.outlier_rejection_multiplier(), 2.75)
        self.assertEqual(
            settings.convergence_criteria(),
            ip.BundleSettings.ConvergenceCriteria.ParameterCorrections,
        )
        self.assertAlmostEqual(settings.convergence_criteria_threshold(), 1.0e-6)
        self.assertEqual(settings.convergence_criteria_maximum_iterations(), 15)
        self.assertEqual(
            ip.BundleSettings.convergence_criteria_to_string(
                ip.BundleSettings.ConvergenceCriteria.ParameterCorrections
            ),
            "ParameterCorrections",
        )
        self.assertEqual(
            ip.BundleSettings.string_to_convergence_criteria("Sigma0"),
            ip.BundleSettings.ConvergenceCriteria.Sigma0,
        )

        maximum_likelihood_models = settings.maximum_likelihood_estimator_models()
        self.assertEqual(len(maximum_likelihood_models), 1)
        self.assertEqual(
            maximum_likelihood_models[0][0],
            ip.BundleSettings.MaximumLikelihoodModel.Huber,
        )
        self.assertAlmostEqual(maximum_likelihood_models[0][1], 1.345)
        self.assertEqual(settings.output_file_prefix(), "bundle/run_")
        self.assertEqual(settings.cube_list(), "cubes.lis")
        self.assertEqual(settings.number_solve_settings(), 1)
        self.assertEqual(settings.observation_solve_settings()[0].instrument_id(), "CTX")
        self.assertEqual(settings.observation_solve_settings(0).instrument_id(), "CTX")
        self.assertEqual(
            settings.observation_solve_settings("OBS-CTX-1").instrument_id(),
            "CTX",
        )
        bound_target_body = settings.bundle_target_body()
        self.assertIsNotNone(bound_target_body)
        self.assertTrue(settings.solve_target_body())
        self.assertEqual(settings.number_target_body_parameters(), 2)
        self.assertTrue(settings.solve_pole_ra())
        self.assertTrue(settings.solve_mean_radius())
        self.assertAlmostEqual(bound_target_body.pole_ra_coefs()[0].degrees(), 5.0)
        self.assertAlmostEqual(bound_target_body.mean_radius().kilometers(), 1003.0)

    def test_control_measure_log_data_round_trip(self):
        log_data = ip.ControlMeasureLogData(
            ip.ControlMeasureLogData.NumericLogDataType.GoodnessOfFit,
            0.25,
        )
        self.assertTrue(log_data.is_valid())
        self.assertEqual(
            log_data.get_data_type(),
            ip.ControlMeasureLogData.NumericLogDataType.GoodnessOfFit,
        )
        self.assertAlmostEqual(log_data.get_numerical_value(), 0.25, places=12)
        self.assertEqual(
            log_data.data_type_to_name(
                ip.ControlMeasureLogData.NumericLogDataType.GoodnessOfFit
            ),
            "GoodnessOfFit",
        )

    def test_control_point_and_measure_relationships(self):
        point = ip.ControlPoint("P1")
        point.set_type(ip.ControlPoint.PointType.Free)

        measure = ip.ControlMeasure()
        measure.set_cube_serial_number("SN-001")
        measure.set_coordinate(12.5, 22.5)
        measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        measure.set_chooser_name("pytest")
        measure.set_date_time("2026-03-17T00:00:00")
        measure.set_log_data(
            ip.ControlMeasureLogData(
                ip.ControlMeasureLogData.NumericLogDataType.GoodnessOfFit,
                0.9,
            )
        )

        point.add_measure(measure)
        point.set_ref_measure(0)

        self.assertEqual(point.get_num_measures(), 1)
        self.assertTrue(point.has_ref_measure())
        self.assertEqual(point.get_measure(0).get_cube_serial_number(), "SN-001")
        self.assertEqual(point.get_ref_measure().get_cube_serial_number(), "SN-001")
        self.assertEqual(point.get_cube_serial_numbers(), ["SN-001"])
        self.assertEqual(point.index_of("SN-001"), 0)
        self.assertEqual(point.get_measure(0).get_log_data_entries()[0].get_numerical_value(), 0.9)

    def test_control_net_basic_graph_and_io(self):
        net = ip.ControlNet()
        net.set_network_id("ExampleNet")
        net.set_user_name("pytest")
        net.set_created_date("2026-03-17T00:00:00")
        net.set_modified_date("2026-03-17T00:01:00")
        net.set_description("unit test")

        point = ip.ControlPoint("P1")
        measure1 = ip.ControlMeasure()
        measure1.set_cube_serial_number("ALPHA")
        measure1.set_coordinate(1.0, 2.0)
        point.add_measure(measure1)

        measure2 = ip.ControlMeasure()
        measure2.set_cube_serial_number("BRAVO")
        measure2.set_coordinate(3.0, 4.0)
        point.add_measure(measure2)
        point.set_ref_measure(0)

        net.add_point(point)

        self.assertEqual(net.get_num_points(), 1)
        self.assertEqual(net.get_num_measures(), 2)
        self.assertEqual(net.get_network_id(), "ExampleNet")
        self.assertEqual(sorted(net.get_cube_serials()), ["ALPHA", "BRAVO"])
        self.assertEqual(net.get_point_ids(), ["P1"])
        self.assertEqual(net.get_adjacent_images("ALPHA"), ["BRAVO"])
        self.assertEqual(net.get_edge_count(), 1)
        self.assertIn("ALPHA", net.graph_to_string())

        with temporary_directory() as temp_dir:
            output_path = temp_dir / "example.net"
            net.write(str(output_path), True)
            loaded = ip.ControlNet(str(output_path))
            self.assertEqual(loaded.get_num_points(), 1)
            self.assertEqual(loaded.get_num_measures(), 2)
            self.assertEqual(loaded.get_point("P1").get_ref_measure().get_cube_serial_number(), "ALPHA")

    def test_control_net_filter_output_helpers_write_expected_text(self):
        net, cube_path, serial_number = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")
            output_path = temp_dir / "control_net_filter_point_output.csv"

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.set_output_file(str(output_path))

            point = net.get_point("LOCKED")
            measure = point.get_measure(0)

            filter_object.point_stats_header()
            filter_object.point_stats(point)
            filter_object.print_cube_file_serial_num(measure)

            del filter_object
            gc.collect()

            output_text = output_path.read_text(encoding="utf-8")
            self.assertIn("PointID, PointType, PointIgnored, PointEditLocked", output_text)
            self.assertIn("LOCKED, Fixed, False, True, 1, 0, 1,", output_text)
            self.assertIn(str(cube_path), output_text)
            self.assertIn(serial_number, output_text)

    def test_control_net_filter_cube_stats_header_writes_expected_text(self):
        net, cube_path, _ = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")
            output_path = temp_dir / "control_net_filter_cube_output.csv"

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.set_output_file(str(output_path))
            filter_object.cube_stats_header()

            del filter_object
            gc.collect()

            output_text = output_path.read_text(encoding="utf-8")
            self.assertIn(
                "FileName, SerialNumber, ImageTotalPoints, ImagePointsIgnored, ImagePointsEditLocked",
                output_text,
            )

    def test_control_net_filter_point_edit_lock_filter_keeps_matching_points(self):
        net, cube_path, _ = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.point_edit_lock_filter(self.make_point_edit_lock_group(True), False)

            self.assertEqual(net.get_num_points(), 1)
            self.assertEqual(net.get_point(0).get_id(), "LOCKED")

    def test_control_net_filter_point_measures_filter_keeps_expected_points(self):
        net, cube_paths, _ = self.make_control_net_filter_count_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(
                "\n".join(str(path) for path in cube_paths) + "\n",
                encoding="utf-8",
            )
            output_path = temp_dir / "control_net_filter_point_measures.csv"

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.set_output_file(str(output_path))
            filter_object.point_measures_filter(
                self.make_less_greater_group("Point_NumMeasures", 2, 2),
                True,
            )

            self.assertEqual(net.get_num_points(), 1)
            self.assertEqual(net.get_point(0).get_id(), "KEEP2")

            del filter_object
            gc.collect()

            output_text = output_path.read_text(encoding="utf-8")
            self.assertIn(
                "PointID, PointType, PointIgnored, PointEditLocked, TotalMeasures",
                output_text,
            )
            self.assertIn("KEEP2", output_text)
            self.assertNotIn("DROP1", output_text)

    def test_control_net_filter_point_id_filter_keeps_matching_points(self):
        net, cube_path, _ = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.point_id_filter(
                self.make_expression_group("Point_IdExpression", "LOCK*"),
                False,
            )

            self.assertEqual(net.get_num_points(), 1)
            self.assertEqual(net.get_point(0).get_id(), "LOCKED")

    def test_control_net_filter_point_properties_filter_keeps_fixed_points(self):
        net, cube_path, _ = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.point_properties_filter(
                self.make_point_properties_group(point_type="fixed"),
                False,
            )

            self.assertEqual(net.get_num_points(), 1)
            remaining = net.get_point(0)
            self.assertEqual(remaining.get_id(), "LOCKED")
            self.assertTrue(remaining.is_fixed())

    def test_control_net_filter_cube_name_expression_filter_keeps_matching_serials(self):
        net, cube_path, serial_number = self.make_control_net_filter_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(f"{cube_path}\n", encoding="utf-8")

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.cube_name_expression_filter(
                self.make_expression_group("Cube_NameExpression", serial_number[:12]),
                False,
            )

            self.assertEqual(net.get_num_points(), 2)
            self.assertEqual(len(net.get_measures_in_cube(serial_number)), 2)

    def test_control_net_filter_cube_num_points_filter_keeps_expected_images(self):
        net, cube_paths, serials = self.make_control_net_filter_count_fixture()

        with temporary_directory() as temp_dir:
            serial_list_path = temp_dir / "serials.lis"
            serial_list_path.write_text(
                "\n".join(str(path) for path in cube_paths) + "\n",
                encoding="utf-8",
            )
            output_path = temp_dir / "control_net_filter_cube_num_points.csv"

            filter_object = ip.ControlNetFilter(net, str(serial_list_path))
            filter_object.set_output_file(str(output_path))
            filter_object.cube_num_points_filter(
                self.make_less_greater_group("Cube_NumPoints", 1, 1),
                True,
            )

            self.assertEqual(len(net.get_measures_in_cube(serials[0])), 0)
            self.assertEqual(len(net.get_measures_in_cube(serials[1])), 1)

            del filter_object
            gc.collect()

            output_text = output_path.read_text(encoding="utf-8")
            self.assertIn(
                "FileName, SerialNumber, ImageTotalPoints, ImagePointsIgnored, ImagePointsEditLocked",
                output_text,
            )
            self.assertIn(serials[1], output_text)
            self.assertNotIn(serials[0], output_text)

    def test_control_net_diff_reports_basic_difference(self):
        diff = ip.ControlNetDiff()

        net1 = ip.ControlNet()
        net1.set_network_id("NetA")
        point1 = ip.ControlPoint("P1")
        measure1 = ip.ControlMeasure()
        measure1.set_cube_serial_number("ALPHA")
        measure1.set_coordinate(1.0, 2.0)
        point1.add_measure(measure1)
        point1.set_ref_measure(0)
        net1.add_point(point1)

        net2 = ip.ControlNet()
        net2.set_network_id("NetB")
        point2 = ip.ControlPoint("P1")
        measure2 = ip.ControlMeasure()
        measure2.set_cube_serial_number("ALPHA")
        measure2.set_coordinate(1.0, 2.0)
        point2.add_measure(measure2)
        point2.set_ref_measure(0)
        net2.add_point(point2)

        with temporary_directory() as temp_dir:
            net1_path = temp_dir / "net1.net"
            net2_path = temp_dir / "net2.net"
            net1.write(str(net1_path), True)
            net2.write(str(net2_path), True)

            report = diff.compare(ip.FileName(str(net1_path)), ip.FileName(str(net2_path)))
            report_text = str(report)
            self.assertIn("NetworkId", report_text)

    def test_control_point_list_reads_ids(self):
        with temporary_directory() as temp_dir:
            point_list_path = temp_dir / "points.lis"
            point_list_path.write_text("P1\nP2\nP3\n", encoding="utf-8")

            point_list = ip.ControlPointList(ip.FileName(str(point_list_path)))

            self.assertEqual(len(point_list), 3)
            self.assertEqual(point_list.control_point_id(0), "P1")
            self.assertEqual(point_list.control_point_id(2), "P3")
            self.assertEqual(point_list.control_point_index("P2"), 1)
            self.assertTrue(point_list.has_control_point("P3"))
            self.assertFalse(point_list.has_control_point("P4"))

            pvl_log = ip.Pvl()
            point_list.register_statistics(pvl_log)
            self.assertTrue(pvl_log.has_keyword("TotalPoints"))
            self.assertEqual(pvl_log.find_keyword("TotalPoints")[0], "3")
            self.assertTrue(pvl_log.has_keyword("InvalidPoints"))

    def test_control_point_v0001_serialization_helpers(self):
        point = ip.ControlPointV0001(self.make_control_point_v0001_object(), "Mars")

        self.assertGreater(len(point.point_data()), 0)
        self.assertGreater(len(point.log_data()), 0)
        self.assertIn("CPV1", point.point_data_debug_string())
        self.assertIn("0.9", point.log_data_debug_string())

    def test_control_point_v0002_from_pvl_and_upgrade(self):
        direct_point = ip.ControlPointV0002(self.make_control_point_v0002_object())
        old_point = ip.ControlPointV0001(self.make_control_point_v0001_object(), "Mars")
        upgraded_point = ip.ControlPointV0002(old_point)

        self.assertGreater(len(direct_point.point_data()), 0)
        self.assertGreater(len(direct_point.log_data()), 0)
        self.assertIn("CPV2", direct_point.point_data_debug_string())
        self.assertEqual(upgraded_point.point_data(), old_point.point_data())
        self.assertEqual(upgraded_point.log_data(), old_point.log_data())
        self.assertIn("CPV1", upgraded_point.point_data_debug_string())

    def test_control_point_v0003_from_pvl_and_upgrade(self):
        direct_point = ip.ControlPointV0003(self.make_control_point_v0003_object())
        old_point = ip.ControlPointV0002(self.make_control_point_v0002_object())
        upgraded_point = ip.ControlPointV0003(old_point)

        self.assertGreater(len(direct_point.point_data()), 0)
        self.assertIn("CPV3", direct_point.point_data_debug_string())
        self.assertGreater(len(upgraded_point.point_data()), 0)
        self.assertIn("CPV2", upgraded_point.point_data_debug_string())

    def test_measure_validation_results_round_trip(self):
        results = ip.MeasureValidationResults()

        self.assertTrue(results.is_valid())
        self.assertEqual(results.to_string(), "succeeded")
        self.assertTrue(
            results.get_valid_status(ip.MeasureValidationResults.Option.EmissionAngle)
        )

        results.add_failure(
            ip.MeasureValidationResults.Option.EmissionAngle,
            35.5,
            "greater",
        )
        self.assertFalse(results.is_valid())
        self.assertFalse(
            results.get_valid_status(ip.MeasureValidationResults.Option.EmissionAngle)
        )
        self.assertIn(
            "Emission Angle",
            results.get_failure_prefix(ip.MeasureValidationResults.Option.EmissionAngle),
        )
        self.assertIn("greater than tolerance 35.5", results.to_string())

        ranged = ip.MeasureValidationResults()
        ranged.add_failure(
            ip.MeasureValidationResults.Option.PixelShift,
            4.25,
            0.0,
            3.0,
        )
        formatted = ranged.to_string("120.5", "220.5", "SN-42", "P42")
        self.assertIn("Control Measure with position (120.5, 220.5)", formatted)
        self.assertIn("Pixel Shift 4.25 is outside range [0, 3]", formatted)

    def test_control_net_statistics_summary_and_scalar_getters(self):
        statistics = ip.ControlNetStatistics(self.make_control_net_statistics_fixture())

        self.assertEqual(statistics.num_valid_points(), 2)
        self.assertEqual(statistics.num_fixed_points(), 1)
        self.assertEqual(statistics.num_constrained_points(), 1)
        self.assertEqual(statistics.num_free_points(), 1)
        self.assertEqual(statistics.num_ignored_points(), 1)
        self.assertEqual(statistics.num_edit_locked_points(), 1)
        self.assertEqual(statistics.num_measures(), 4)
        self.assertEqual(statistics.num_valid_measures(), 3)
        self.assertEqual(statistics.num_ignored_measures(), 1)
        self.assertEqual(statistics.num_edit_locked_measures(), 2)

        self.assertAlmostEqual(
            statistics.get_average_residual(),
            (5.0 + math.sqrt(5.0) + math.sqrt(40.0)) / 3.0,
            places=12,
        )
        self.assertAlmostEqual(statistics.get_minimum_residual(), math.sqrt(5.0), places=12)
        self.assertAlmostEqual(statistics.get_maximum_residual(), math.sqrt(40.0), places=12)
        self.assertAlmostEqual(statistics.get_min_line_residual(), 2.0, places=12)
        self.assertAlmostEqual(statistics.get_max_line_residual(), 6.0, places=12)
        self.assertAlmostEqual(statistics.get_min_sample_residual(), 1.0, places=12)
        self.assertAlmostEqual(statistics.get_max_sample_residual(), 3.0, places=12)
        self.assertAlmostEqual(statistics.get_min_line_shift(), 1.0, places=12)
        self.assertAlmostEqual(statistics.get_max_line_shift(), 2.0, places=12)
        self.assertAlmostEqual(statistics.get_min_sample_shift(), 0.5, places=12)
        self.assertAlmostEqual(statistics.get_max_sample_shift(), 1.0, places=12)
        self.assertAlmostEqual(statistics.get_min_pixel_shift(), math.sqrt(1.25), places=12)
        self.assertAlmostEqual(statistics.get_max_pixel_shift(), math.sqrt(5.0), places=12)
        self.assertAlmostEqual(
            statistics.get_avg_pixel_shift(),
            (math.sqrt(5.0) + math.sqrt(1.25) + math.sqrt(2.0)) / 3.0,
            places=12,
        )

        summary = ip.PvlGroup("Placeholder")
        statistics.generate_control_net_stats(summary)

        self.assertEqual(summary.name(), "ControlNetSummary")
        self.assertEqual(int(summary.find_keyword("TotalPoints")[0]), 3)
        self.assertEqual(int(summary.find_keyword("ValidPoints")[0]), 2)
        self.assertEqual(int(summary.find_keyword("IgnoredPoints")[0]), 1)
        self.assertEqual(int(summary.find_keyword("FixedPoints")[0]), 1)
        self.assertEqual(int(summary.find_keyword("ConstrainedPoints")[0]), 1)
        self.assertEqual(int(summary.find_keyword("FreePoints")[0]), 1)
        self.assertEqual(int(summary.find_keyword("EditLockPoints")[0]), 1)
        self.assertEqual(int(summary.find_keyword("TotalMeasures")[0]), 4)
        self.assertEqual(int(summary.find_keyword("ValidMeasures")[0]), 3)
        self.assertEqual(int(summary.find_keyword("IgnoredMeasures")[0]), 1)
        self.assertEqual(int(summary.find_keyword("EditLockMeasures")[0]), 2)
        self.assertAlmostEqual(float(summary.find_keyword("AvgResidual")[0]), statistics.get_average_residual(), places=12)
        self.assertAlmostEqual(float(summary.find_keyword("MaxLineResidual")[0]), 6.0, places=12)
        self.assertAlmostEqual(float(summary.find_keyword("MinSampleShift")[0]), 0.5, places=12)
        self.assertAlmostEqual(float(summary.find_keyword("MaxPixelShift")[0]), math.sqrt(5.0), places=12)
        self.assertEqual(summary.find_keyword("MinGoodnessOfFit")[0], "NA")
        self.assertEqual(summary.find_keyword("MaxPixelZScore")[0], "NA")

    def test_control_net_statistics_enums_and_repr(self):
        statistics = ip.ControlNetStatistics(self.make_control_net_statistics_fixture())

        self.assertEqual(ip.ControlNetStatistics.ePointDetails.total.name, "total")
        self.assertEqual(
            ip.ControlNetStatistics.ePointIntStats.validMeasures.name,
            "validMeasures",
        )
        self.assertEqual(
            ip.ControlNetStatistics.ePointDoubleStats.maxPixelShift.name,
            "maxPixelShift",
        )
        self.assertEqual(ip.ControlNetStatistics.ImageStats.imgConvexHullRatio.name, "imgConvexHullRatio")
        self.assertIn("ControlNetStatistics(valid_points=2", repr(statistics))

    def test_bundle_image_basic_accessors(self):
        cube = self.open_cube(
            workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
        )
        camera = cube.camera()

        bundle_image = ip.BundleImage(
            camera,
            "SN-MDIS-1",
            "/tmp/EN0108828322M_iof.cub",
        )

        self.assertIs(bundle_image.camera(), camera)
        self.assertEqual(bundle_image.serial_number(), "SN-MDIS-1")
        self.assertEqual(bundle_image.file_name(), "/tmp/EN0108828322M_iof.cub")
        self.assertFalse(bundle_image.has_parent_observation())
        self.assertIn("BundleImage(serial_number='SN-MDIS-1'", repr(bundle_image))


if __name__ == "__main__":
    unittest.main()
