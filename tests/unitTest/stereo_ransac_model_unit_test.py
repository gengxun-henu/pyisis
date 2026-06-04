from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.keypoints import Keypoint, KeypointFile
from image_match import stereo_ransac


def _key_file(count: int) -> KeypointFile:
    return KeypointFile(100, 100, tuple(Keypoint(float(i), float(i + 1)) for i in range(count)))


class StereoRansacModelTest(unittest.TestCase):
    def test_affine_partial_calls_estimate_affine_partial_2d(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [0], [1], [1]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "estimateAffinePartial2D", return_value=(np.eye(2, 3), mask)) as affine_partial:
            filtered_left, filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="affine-partial",
                ransac_coordinate_space="dom_pixel",
                ransac_reproj_threshold=10.0,
                ransac_mode="strict",
            )

        affine_partial.assert_called_once()
        self.assertEqual(len(filtered_left.points), 3)
        self.assertEqual(len(filtered_right.points), 3)
        self.assertEqual(summary["model"], "affine-partial")
        self.assertEqual(summary["coordinate_space"], "dom_pixel")
        self.assertEqual(summary["matrix_type"], "affine_2x3")
        self.assertEqual(summary["retained_count"], 3)
        self.assertEqual(summary["dropped_count"], 1)

    def test_affine_calls_estimate_affine_2d(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [1], [0], [1]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "estimateAffine2D", return_value=(np.eye(2, 3), mask)) as affine:
            _filtered_left, _filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="affine",
                ransac_mode="strict",
            )

        affine.assert_called_once()
        self.assertEqual(summary["model"], "affine")
        self.assertEqual(summary["matrix_type"], "affine_2x3")
        self.assertEqual(summary["retained_count"], 3)

    def test_homography_keeps_legacy_find_homography_path(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "findHomography", return_value=(np.eye(3), mask)) as homography:
            _filtered_left, _filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="homography",
                ransac_reproj_threshold=3.0,
                ransac_mode="strict",
            )

        homography.assert_called_once()
        self.assertEqual(summary["model"], "homography")
        self.assertEqual(summary["matrix_type"], "homography_3x3")
        self.assertEqual(summary["homography_matrix"], np.eye(3).tolist())
        self.assertEqual(summary["retained_count"], 3)

    def test_insufficient_points_for_affine_partial_keeps_all_points(self) -> None:
        left_key = _key_file(1)
        right_key = _key_file(1)

        filtered_left, filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
            left_key,
            right_key,
            ransac_model="affine-partial",
        )

        self.assertEqual(filtered_left.points, left_key.points)
        self.assertEqual(filtered_right.points, right_key.points)
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["status"], "skipped_insufficient_points")
        self.assertEqual(summary["skipped_reason"], "insufficient_points")
        self.assertEqual(summary["retained_count"], 1)

    def test_insufficient_points_for_affine_keeps_all_points(self) -> None:
        left_key = _key_file(2)
        right_key = _key_file(2)

        filtered_left, filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
            left_key,
            right_key,
            ransac_model="affine",
        )

        self.assertEqual(filtered_left.points, left_key.points)
        self.assertEqual(filtered_right.points, right_key.points)
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["status"], "skipped_insufficient_points")
        self.assertEqual(summary["skipped_reason"], "insufficient_points")
        self.assertEqual(summary["retained_count"], 2)

    def test_invalid_ransac_model_raises_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "ransac_model must be one of"):
            stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                _key_file(4),
                _key_file(4),
                ransac_model="projective",
            )


if __name__ == "__main__":
    unittest.main()
