"""
Unit tests for ISIS New Horizons mission camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class NewHorizonsLeisaCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for New Horizons LEISA camera bindings."""

    def test_leisa_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsLeisaCamera"))

    def test_leisa_camera_inherits_linescan_camera(self):
        self.assertTrue(issubclass(ip.NewHorizonsLeisaCamera, ip.LineScanCamera))

    def test_leisa_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.NewHorizonsLeisaCamera, "set_band"))
        self.assertTrue(hasattr(ip.NewHorizonsLeisaCamera, "is_band_independent"))
        self.assertTrue(hasattr(ip.NewHorizonsLeisaCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.NewHorizonsLeisaCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.NewHorizonsLeisaCamera, "spk_reference_id"))


class NewHorizonsLorriBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for New Horizons LORRI bindings."""

    def test_lorri_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsLorriCamera"))

    def test_lorri_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.NewHorizonsLorriCamera, ip.FramingCamera))

    def test_lorri_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.NewHorizonsLorriCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.NewHorizonsLorriCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.NewHorizonsLorriCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.NewHorizonsLorriCamera, "spk_reference_id"))

    def test_lorri_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsLorriDistortionMap"))

    def test_lorri_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.NewHorizonsLorriDistortionMap, ip.CameraDistortionMap)
        )

    def test_lorri_distortion_map_methods_exist(self):
        self.assertTrue(hasattr(ip.NewHorizonsLorriDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.NewHorizonsLorriDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.NewHorizonsLorriDistortionMap, "__repr__"))

    def test_lorri_distortion_map_inherits_base_methods(self):
        self.assertTrue(hasattr(ip.NewHorizonsLorriDistortionMap, "focal_plane_x"))
        self.assertTrue(hasattr(ip.NewHorizonsLorriDistortionMap, "focal_plane_y"))
        self.assertTrue(
            hasattr(ip.NewHorizonsLorriDistortionMap, "undistorted_focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.NewHorizonsLorriDistortionMap, "undistorted_focal_plane_y")
        )


class NewHorizonsMvicBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for New Horizons MVIC bindings."""

    def test_mvic_frame_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsMvicFrameCamera"))

    def test_mvic_frame_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.NewHorizonsMvicFrameCamera, ip.FramingCamera))

    def test_mvic_frame_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.NewHorizonsMvicFrameCamera, "set_band"))
        self.assertTrue(
            hasattr(ip.NewHorizonsMvicFrameCamera, "shutter_open_close_times")
        )
        self.assertTrue(hasattr(ip.NewHorizonsMvicFrameCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.NewHorizonsMvicFrameCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.NewHorizonsMvicFrameCamera, "spk_reference_id"))

    def test_mvic_frame_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsMvicFrameCameraDistortionMap"))

    def test_mvic_frame_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(
                ip.NewHorizonsMvicFrameCameraDistortionMap,
                ip.CameraDistortionMap,
            )
        )

    def test_mvic_frame_distortion_map_methods_exist(self):
        self.assertTrue(
            hasattr(ip.NewHorizonsMvicFrameCameraDistortionMap, "set_focal_plane")
        )
        self.assertTrue(
            hasattr(
                ip.NewHorizonsMvicFrameCameraDistortionMap,
                "set_undistorted_focal_plane",
            )
        )
        self.assertTrue(
            hasattr(ip.NewHorizonsMvicFrameCameraDistortionMap, "__repr__")
        )

    def test_mvic_tdi_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsMvicTdiCamera"))

    def test_mvic_tdi_camera_inherits_linescan_camera(self):
        self.assertTrue(issubclass(ip.NewHorizonsMvicTdiCamera, ip.LineScanCamera))

    def test_mvic_tdi_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.NewHorizonsMvicTdiCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.NewHorizonsMvicTdiCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.NewHorizonsMvicTdiCamera, "spk_reference_id"))

    def test_mvic_tdi_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "NewHorizonsMvicTdiCameraDistortionMap"))

    def test_mvic_tdi_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(
                ip.NewHorizonsMvicTdiCameraDistortionMap,
                ip.CameraDistortionMap,
            )
        )

    def test_mvic_tdi_distortion_map_methods_exist(self):
        self.assertTrue(
            hasattr(ip.NewHorizonsMvicTdiCameraDistortionMap, "set_focal_plane")
        )
        self.assertTrue(
            hasattr(
                ip.NewHorizonsMvicTdiCameraDistortionMap,
                "set_undistorted_focal_plane",
            )
        )
        self.assertTrue(hasattr(ip.NewHorizonsMvicTdiCameraDistortionMap, "__repr__"))


if __name__ == "__main__":
    unittest.main()
