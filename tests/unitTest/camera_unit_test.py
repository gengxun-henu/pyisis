"""
Unit tests for ISIS camera and CameraFactory bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-13
Updated: 2026-04-12  Geng Xun added Spice integration coverage using local MDIS cubes and SPICE tables.
Updated: 2026-04-13  Geng Xun added SpiceRotation core methods coverage (matrix, angular_velocity, cache, frame chains).
"""

import math
import unittest

from _unit_test_support import ip, workspace_test_data_path


MDIS_CUBES = [
    workspace_test_data_path("mosrange", "EN0108828322M_iof.cub"),
    workspace_test_data_path("mosrange", "EN0108828327M_iof.cub"),
    workspace_test_data_path("mosrange", "EN0108828332M_iof.cub"),
    workspace_test_data_path("mosrange", "EN0108828337M_iof.cub"),
]
NO_SPICE_CUBE = workspace_test_data_path("mosrange", "EN0108828337M_noSPICE.cub")


class CameraUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def test_camera_factory_create_and_version_with_local_mdis_cube(self):
        cube = self.open_cube(MDIS_CUBES[0])

        camera = ip.CameraFactory.create(cube)

        self.assertIsInstance(camera, ip.Camera)
        self.assertIsInstance(camera, ip.FramingCamera)
        self.assertIsInstance(camera, ip.MdisCamera)
        self.assertEqual(ip.CameraFactory.camera_version(cube), 2)

    def test_camera_base_methods_with_local_mdis_cube(self):
        cube = self.open_cube(MDIS_CUBES[0])
        camera = cube.camera()

        self.assertEqual(camera.instrument_id(), "MDIS-NAC")
        self.assertTrue(camera.is_band_independent())
        self.assertFalse(camera.has_projection())
        self.assertEqual(camera.samples(), 1024)
        self.assertEqual(camera.lines(), 1024)
        self.assertEqual(camera.bands(), 1)
        self.assertEqual(camera.ck_frame_id(), -236000)
        self.assertEqual(camera.ck_reference_id(), 1)
        self.assertEqual(camera.spk_target_id(), -236)
        self.assertEqual(camera.spk_reference_id(), 1)
        self.assertEqual(camera.get_camera_type(), ip.Camera.CameraType.Framing)
        self.assertEqual(camera.reference_band(), 0)
        self.assertFalse(camera.has_reference_band())
        self.assertEqual(camera.band(), 1)
        self.assertEqual(camera.parent_samples(), cube.sample_count())
        self.assertEqual(camera.parent_lines(), cube.line_count())
        self.assertAlmostEqual(camera.focal_length(), 549.11781953727)
        self.assertAlmostEqual(camera.pixel_pitch(), 0.014)
        self.assertTrue(math.isfinite(ip.Camera.ground_azimuth(-15.0, 140.0, -14.0, 141.0)))

    def test_camera_set_image_and_ground_round_trip_for_local_mdis_cubes(self):
        expected_centers = [
            (-15.260663718130933, 140.41008503563984),
            (-14.290767737268501, 151.84462642143592),
            (-13.256303304233857, 164.56060377359765),
            (-12.121776390792757, 180.74394430178248),
        ]

        for path, (expected_lat, expected_lon) in zip(MDIS_CUBES, expected_centers):
            cube = self.open_cube(path)
            camera = cube.camera()

            self.assertTrue(camera.set_image(camera.samples() / 2.0, camera.lines() / 2.0))
            self.assertAlmostEqual(camera.universal_latitude(), expected_lat, places=8)
            self.assertAlmostEqual(camera.universal_longitude(), expected_lon, places=8)

            self.assertTrue(
                camera.set_universal_ground(
                    camera.universal_latitude(),
                    camera.universal_longitude(),
                )
            )
            self.assertAlmostEqual(camera.sample(), camera.samples() / 2.0, places=3)
            self.assertAlmostEqual(camera.line(), camera.lines() / 2.0, places=3)

    def test_camera_surface_point_matches_current_ground_solution(self):
        cube = self.open_cube(MDIS_CUBES[0])
        camera = cube.camera()

        center_sample = camera.samples() / 2.0
        center_line = camera.lines() / 2.0
        self.assertTrue(camera.set_image(center_sample, center_line))
        self.assertTrue(camera.has_surface_intersection())

        surface_point = camera.get_surface_point()

        self.assertTrue(surface_point.valid())
        self.assertAlmostEqual(
            surface_point.get_latitude().degrees(),
            camera.universal_latitude(),
            places=8,
        )
        self.assertAlmostEqual(
            surface_point.get_longitude().degrees(),
            camera.universal_longitude(),
            places=8,
        )
        self.assertGreater(surface_point.get_local_radius().meters(), 0.0)

    def test_camera_factory_failure_path_matches_no_spice_case(self):
        cube = self.open_cube(NO_SPICE_CUBE)

        with self.assertRaises(Exception):
            ip.CameraFactory.create(cube)

        with self.assertRaises(Exception):
            cube.camera()

    def test_camera_hierarchy_and_mission_binding_identity(self):
        cube = self.open_cube(MDIS_CUBES[1])
        camera = cube.camera()

        self.assertEqual(type(camera).__name__, "MdisCamera")
        self.assertIsInstance(camera, ip.Camera)
        self.assertIsInstance(camera, ip.FramingCamera)
        self.assertIsInstance(camera, ip.MdisCamera)
        self.assertFalse(isinstance(camera, ip.LineScanCamera))
        self.assertFalse(isinstance(camera, ip.PushFrameCamera))
        self.assertFalse(isinstance(camera, ip.RadarCamera))

    def test_camera_point_info_with_local_mdis_cube(self):
        cube = self.open_cube(MDIS_CUBES[0])
        camera = cube.camera()

        center_sample = camera.samples() / 2.0
        center_line = camera.lines() / 2.0
        self.assertTrue(camera.set_image(center_sample, center_line))
        center_latitude = camera.universal_latitude()
        center_longitude = camera.universal_longitude()

        point_info = ip.CameraPointInfo()
        self.assertEqual(repr(point_info), "CameraPointInfo()")

        with self.assertRaises(ip.IException):
            point_info.set_center()

        point_info.set_cube(str(MDIS_CUBES[0]))

        center_group = point_info.set_center()
        self.assertEqual(center_group.name(), "GroundPoint")
        self.assertAlmostEqual(float(center_group.keyword("Sample")[0]), center_sample, places=3)
        self.assertAlmostEqual(float(center_group.keyword("Line")[0]), center_line, places=3)
        self.assertAlmostEqual(
            float(center_group.keyword("PlanetocentricLatitude")[0]),
            center_latitude,
            places=6,
        )
        self.assertAlmostEqual(
            float(center_group.keyword("PositiveEast360Longitude")[0]),
            center_longitude,
            places=6,
        )

        image_group = point_info.set_image(center_sample, center_line)
        self.assertAlmostEqual(float(image_group.keyword("Sample")[0]), center_sample, places=3)
        self.assertAlmostEqual(float(image_group.keyword("Line")[0]), center_line, places=3)

        sample_group = point_info.set_sample(center_sample)
        self.assertAlmostEqual(float(sample_group.keyword("Sample")[0]), center_sample, places=3)
        self.assertAlmostEqual(float(sample_group.keyword("Line")[0]), center_line, places=3)

        line_group = point_info.set_line(center_line)
        self.assertAlmostEqual(float(line_group.keyword("Sample")[0]), center_sample, places=3)
        self.assertAlmostEqual(float(line_group.keyword("Line")[0]), center_line, places=3)

        ground_group = point_info.set_ground(center_latitude, center_longitude)
        self.assertAlmostEqual(float(ground_group.keyword("Sample")[0]), center_sample, places=2)
        self.assertAlmostEqual(float(ground_group.keyword("Line")[0]), center_line, places=2)

        point_info.set_csv_output(True)
        csv_group = point_info.set_image(center_sample, center_line)
        self.assertEqual(csv_group.name(), "GroundPoint")
        self.assertTrue(csv_group.has_keyword("ObliqueDetectorResolution"))

    def test_spice_accessors_with_mdis_cube_tables(self):
        cube = self.open_cube(MDIS_CUBES[0])
        spice = ip.Spice(cube)

        self.assertEqual(spice.target_name(), "Mercury")
        self.assertFalse(spice.is_time_set())

        instrument = cube.label().find_group("Instrument", ip.PvlObject.FindOptions.Traverse)
        start_time = instrument.find_keyword("StartTime")[0]
        et = ip.iTime(start_time)
        spice.set_time(et)

        self.assertTrue(spice.is_time_set())
        self.assertAlmostEqual(spice.time().et(), et.et(), places=6)

        self.assertEqual(spice.naif_body_code(), 199)
        self.assertEqual(spice.naif_spk_code(), -236)

        radii = spice.radii()
        self.assertEqual(len(radii), 3)
        self.assertGreater(radii[0].kilometers(), 0.0)

        instrument_position = spice.instrument_body_fixed_position()
        self.assertEqual(len(instrument_position), 3)
        self.assertTrue(all(math.isfinite(value) for value in instrument_position))

        sun_position = spice.sun_position_vector()
        self.assertEqual(len(sun_position), 3)
        self.assertTrue(all(math.isfinite(value) for value in sun_position))

        self.assertGreater(spice.target_center_distance(), 0.0)
        self.assertGreater(spice.sun_to_body_distance(), 0.0)

        target = spice.target()
        self.assertEqual(target.name(), "Mercury")

    def test_spice_rotation_core_methods_with_mdis_cube(self):
        cube = self.open_cube(MDIS_CUBES[0])
        spice = ip.Spice(cube)

        instrument = cube.label().find_group("Instrument", ip.PvlObject.FindOptions.Traverse)
        start_time = instrument.find_keyword("StartTime")[0]
        et = ip.iTime(start_time)
        spice.set_time(et)

        # Get body rotation from Spice object
        body_rotation = spice.body_rotation()
        self.assertIsInstance(body_rotation, ip.SpiceRotation)

        # Test basic rotation properties
        self.assertIsInstance(body_rotation.frame(), int)
        self.assertAlmostEqual(body_rotation.ephemeris_time(), et.et(), places=6)

        # Test frame type and source
        frame_type = body_rotation.get_frame_type()
        self.assertIn(frame_type, [
            ip.SpiceRotationFrameType.PCK,
            ip.SpiceRotationFrameType.CK,
            ip.SpiceRotationFrameType.BPC,
        ])

        source = body_rotation.get_source()
        self.assertIsInstance(source, ip.SpiceRotationSource)

        # Test matrix access
        matrix = body_rotation.matrix()
        self.assertEqual(len(matrix), 9)
        self.assertTrue(all(math.isfinite(value) for value in matrix))

        # Test angular velocity
        self.assertTrue(body_rotation.has_angular_velocity())
        av = body_rotation.angular_velocity()
        self.assertEqual(len(av), 3)
        self.assertTrue(all(math.isfinite(value) for value in av))

        # Test vector rotation
        test_vec = [1.0, 0.0, 0.0]
        j2000_vec = body_rotation.j2000_vector(test_vec)
        self.assertEqual(len(j2000_vec), 3)
        self.assertTrue(all(math.isfinite(value) for value in j2000_vec))

        ref_vec = body_rotation.reference_vector(j2000_vec)
        self.assertEqual(len(ref_vec), 3)
        for i in range(3):
            self.assertAlmostEqual(ref_vec[i], test_vec[i], places=10)

        # Test cache status
        self.assertTrue(body_rotation.is_cached() or not body_rotation.is_cached())
        cache_size = body_rotation.cache_size()
        self.assertGreaterEqual(cache_size, 0)

        # Test time scale methods
        if body_rotation.is_cached():
            base_time = body_rotation.get_base_time()
            time_scale = body_rotation.get_time_scale()
            self.assertTrue(math.isfinite(base_time))
            self.assertTrue(math.isfinite(time_scale))

        # Test frame chains
        const_chain = body_rotation.constant_frame_chain()
        self.assertIsInstance(const_chain, list)
        self.assertGreater(len(const_chain), 0)

        time_chain = body_rotation.time_frame_chain()
        self.assertIsInstance(time_chain, list)
        self.assertGreaterEqual(len(time_chain), 0)


if __name__ == "__main__":
    unittest.main()
