"""
Unit tests for additional ISIS mission camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added Dawn (DawnFcCamera, DawnFcDistortionMap, DawnVirCamera) and Kaguya (KaguyaMiCamera, KaguyaTcCamera, KaguyaMiCameraDistortionMap, KaguyaTcCameraDistortionMap) unit tests.
"""

import unittest

from _unit_test_support import ip


class ApolloMissionBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Apollo mission camera/helper bindings."""

    def test_apollo_metric_camera_surface(self):
        self.assertTrue(issubclass(ip.ApolloMetricCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.ApolloMetricCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.ApolloMetricCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.ApolloMetricCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.ApolloMetricCamera, "spk_target_id"))
        self.assertTrue(hasattr(ip.ApolloMetricCamera, "spk_reference_id"))

    def test_apollo_metric_distortion_map_surface(self):
        self.assertTrue(issubclass(ip.ApolloMetricDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.ApolloMetricDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.ApolloMetricDistortionMap, "set_undistorted_focal_plane"))

    def test_apollo_panoramic_camera_and_detector_map_surface(self):
        self.assertTrue(issubclass(ip.ApolloPanoramicCamera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.ApolloPanoramicCamera, "int_ori_residuals_report"))
        self.assertTrue(hasattr(ip.ApolloPanoramicCamera, "int_ori_residual_max"))
        self.assertTrue(hasattr(ip.ApolloPanoramicCamera, "int_ori_residual_mean"))
        self.assertTrue(hasattr(ip.ApolloPanoramicCamera, "int_ori_residual_stdev"))
        self.assertTrue(issubclass(ip.ApolloPanoramicDetectorMap, ip.CameraDetectorMap))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "set_parent"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "set_detector"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "set_line_rate"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "line_rate"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "mean_residual"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "max_residual"))
        self.assertTrue(hasattr(ip.ApolloPanoramicDetectorMap, "stdev_residual"))


class CassiniMissionBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Cassini mission camera/helper bindings."""

    def test_cassini_iss_camera_surface(self):
        for cls in (ip.IssNACamera, ip.IssWACamera):
            self.assertTrue(issubclass(cls, ip.FramingCamera))
            self.assertTrue(hasattr(cls, "shutter_open_close_times"))
            self.assertTrue(hasattr(cls, "ck_frame_id"))
            self.assertTrue(hasattr(cls, "ck_reference_id"))
            self.assertTrue(hasattr(cls, "spk_reference_id"))

    def test_vims_camera_and_maps_surface(self):
        self.assertTrue(issubclass(ip.VimsCamera, ip.Camera))
        self.assertTrue(hasattr(ip.VimsCamera, "get_camera_type"))
        self.assertTrue(hasattr(ip.VimsCamera, "pixel_ifov_offsets"))
        self.assertTrue(issubclass(ip.VimsGroundMap, ip.CameraGroundMap))
        self.assertTrue(issubclass(ip.VimsSkyMap, ip.CameraSkyMap))
        self.assertTrue(hasattr(ip.VimsGroundMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.VimsGroundMap, "set_ground"))
        self.assertTrue(hasattr(ip.VimsGroundMap, "init"))
        self.assertTrue(hasattr(ip.VimsSkyMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.VimsSkyMap, "set_sky"))
        self.assertTrue(hasattr(ip.VimsSkyMap, "init"))


class ChandrayaanAndClementineBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Chandrayaan-1 and Clementine bindings."""

    def test_chandrayaan_camera_and_distortion_surface(self):
        self.assertTrue(issubclass(ip.Chandrayaan1M3Camera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.Chandrayaan1M3Camera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.Chandrayaan1M3Camera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.Chandrayaan1M3Camera, "spk_reference_id"))
        self.assertTrue(issubclass(ip.Chandrayaan1M3DistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.Chandrayaan1M3DistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.Chandrayaan1M3DistortionMap, "set_undistorted_focal_plane"))

    def test_clementine_cameras_and_distortion_surface(self):
        for cls in (ip.HiresCamera, ip.LwirCamera, ip.NirCamera, ip.UvvisCamera):
            self.assertTrue(issubclass(cls, ip.FramingCamera))
            self.assertTrue(hasattr(cls, "shutter_open_close_times"))
            self.assertTrue(hasattr(cls, "ck_frame_id"))
            self.assertTrue(hasattr(cls, "ck_reference_id"))
            self.assertTrue(hasattr(cls, "spk_reference_id"))
        self.assertTrue(issubclass(ip.ClementineUvvisDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.ClementineUvvisDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.ClementineUvvisDistortionMap, "set_undistorted_focal_plane"))


class ClipperGalileoAndJunoBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Clipper, Galileo, and Juno bindings."""

    def test_clipper_camera_surface(self):
        self.assertTrue(issubclass(ip.ClipperNacRollingShutterCamera, ip.RollingShutterCamera))
        self.assertTrue(issubclass(ip.ClipperPushBroomCamera, ip.LineScanCamera))
        self.assertTrue(issubclass(ip.ClipperWacFcCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.ClipperNacRollingShutterCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.ClipperPushBroomCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.ClipperWacFcCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.ClipperWacFcCamera, "spk_reference_id"))

    def test_galileo_ssi_camera_surface(self):
        self.assertTrue(issubclass(ip.SsiCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.SsiCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.SsiCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.SsiCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.SsiCamera, "spk_reference_id"))

    def test_juno_camera_and_distortion_surface(self):
        self.assertTrue(issubclass(ip.JunoCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.JunoCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.JunoCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.JunoCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.JunoCamera, "spk_target_id"))
        self.assertTrue(hasattr(ip.JunoCamera, "spk_reference_id"))
        self.assertTrue(issubclass(ip.JunoDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.JunoDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.JunoDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.JunoDistortionMap, "set_undistorted_focal_plane"))


class DawnMissionCameraUnitTest(unittest.TestCase):
    """Regression coverage for Dawn mission camera/helper bindings. Added: 2026-04-10."""

    def test_dawn_fc_camera_surface(self):
        """DawnFcCamera inherits FramingCamera with required SPICE ID methods."""
        self.assertTrue(issubclass(ip.DawnFcCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.DawnFcCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.DawnFcCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.DawnFcCamera, "spk_reference_id"))

    def test_dawn_fc_distortion_map_surface(self):
        """DawnFcDistortionMap inherits CameraDistortionMap with focal-plane converters."""
        self.assertTrue(issubclass(ip.DawnFcDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.DawnFcDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.DawnFcDistortionMap, "set_undistorted_focal_plane"))

    def test_dawn_vir_camera_surface(self):
        """DawnVirCamera inherits LineScanCamera with required SPICE ID methods."""
        self.assertTrue(issubclass(ip.DawnVirCamera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.DawnVirCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.DawnVirCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.DawnVirCamera, "spk_reference_id"))


class KaguyaMissionCameraUnitTest(unittest.TestCase):
    """Regression coverage for Kaguya mission camera/helper bindings. Added: 2026-04-10."""

    def test_kaguya_mi_camera_surface(self):
        """KaguyaMiCamera inherits LineScanCamera with required SPICE ID methods."""
        self.assertTrue(issubclass(ip.KaguyaMiCamera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.KaguyaMiCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.KaguyaMiCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.KaguyaMiCamera, "spk_reference_id"))

    def test_kaguya_tc_camera_surface(self):
        """KaguyaTcCamera inherits LineScanCamera with required SPICE ID methods."""
        self.assertTrue(issubclass(ip.KaguyaTcCamera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.KaguyaTcCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.KaguyaTcCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.KaguyaTcCamera, "spk_reference_id"))

    def test_kaguya_mi_distortion_map_surface(self):
        """KaguyaMiCameraDistortionMap inherits CameraDistortionMap with focal-plane converters."""
        self.assertTrue(issubclass(ip.KaguyaMiCameraDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.KaguyaMiCameraDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.KaguyaMiCameraDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.KaguyaMiCameraDistortionMap, "set_undistorted_focal_plane"))

    def test_kaguya_tc_distortion_map_surface(self):
        """KaguyaTcCameraDistortionMap inherits CameraDistortionMap with focal-plane converters."""
        self.assertTrue(issubclass(ip.KaguyaTcCameraDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.KaguyaTcCameraDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.KaguyaTcCameraDistortionMap, "set_undistorted_focal_plane"))


if __name__ == "__main__":
    unittest.main()