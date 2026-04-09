"""
Minimal regression tests for the forward-intersection example.

Author: Geng Xun
Created: 2026-04-09
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun added focused regression coverage for pointreg-style right-image seeding and the example forward-intersection workflow.
"""

import sys
from pathlib import Path
import unittest

from _unit_test_support import ip, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from forward_intersection import (
    estimate_right_point_from_camera_geometry,
    forward_intersection,
)


LEFT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
RIGHT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828327M_iof.cub")
LEFT_SAMPLE = 64.0
LEFT_LINE = 512.0
SUCCESS_MATCH_STATUSES = {"SuccessPixel", "SuccessSubPixel"}


class ForwardIntersectionExampleUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def test_pointreg_style_seed_projects_into_right_image(self):
        left_cube = self.open_cube(LEFT_CUBE_PATH)
        right_cube = self.open_cube(RIGHT_CUBE_PATH)

        estimated_point = estimate_right_point_from_camera_geometry(
            left_cube,
            right_cube,
            LEFT_SAMPLE,
            LEFT_LINE,
        )

        self.assertIsNotNone(estimated_point)
        right_sample, right_line = estimated_point

        right_camera = right_cube.camera()
        self.assertGreaterEqual(right_sample, 1.0)
        self.assertLessEqual(right_sample, right_camera.samples())
        self.assertGreaterEqual(right_line, 1.0)
        self.assertLessEqual(right_line, right_camera.lines())
        self.assertTrue(right_camera.set_image(right_sample, right_line))
        self.assertTrue(right_camera.has_surface_intersection())

    def test_forward_intersection_runs_full_example_workflow(self):
        result = forward_intersection(
            str(LEFT_CUBE_PATH),
            str(RIGHT_CUBE_PATH),
            LEFT_SAMPLE,
            LEFT_LINE,
        )

        self.assertTrue(result.matched_by_shift)
        self.assertIn(result.match_status, SUCCESS_MATCH_STATUSES)
        self.assertIsNotNone(result.goodness_of_fit)
        self.assertGreater(result.goodness_of_fit, 0.8)
        self.assertGreater(result.radius_meters, 0.0)
        self.assertGreaterEqual(result.error_meters, 0.0)
        self.assertGreater(result.separation_angle_degrees, 0.0)
        self.assertGreaterEqual(result.right_sample, 1.0)
        self.assertGreaterEqual(result.right_line, 1.0)


if __name__ == "__main__":
    unittest.main()
