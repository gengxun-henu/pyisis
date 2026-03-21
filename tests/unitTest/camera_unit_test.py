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


if __name__ == "__main__":
    unittest.main()
