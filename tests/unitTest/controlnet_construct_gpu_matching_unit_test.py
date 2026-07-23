"""Focused unit tests for GPU-assisted image matching.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun split GPU matching coverage from the general matching test module.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest
from unittest import mock

import cv2
import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

tile_matching = importlib.import_module("controlnet_construct.tile_matching")
from image_match.tiling import TileWindow


class GpuSiftIntegrationUnitTest(unittest.TestCase):
    """Verify GPU SIFT integration shares result structure with the CPU path."""

    def test_gpu_path_returns_same_structure(self):
        """When use_gpu=False, results should be valid TileMatchResult."""
        rng = np.random.default_rng(seed=20260506)
        left = rng.integers(0, 255, (256, 256), dtype=np.uint8)
        right = left.copy()

        left_mask = np.full((256, 256), 255, dtype=np.uint8)
        right_mask = left_mask.copy()

        kp_left, kp_right, matches = tile_matching._match_tile(
            left,
            right,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=None,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
        )
        self.assertIsInstance(kp_left, list)
        self.assertIsInstance(kp_right, list)
        self.assertIsInstance(matches, list)

    def test_gpu_batch_cpu_fallback(self):
        """GpuSiftBatch should work without GPU hardware via CPU fallback."""
        gpu_sift_module = importlib.import_module("controlnet_construct.gpu_sift")
        rng = np.random.default_rng(seed=20260506)
        batch = gpu_sift_module.GpuSiftBatch(batch_size=4)
        img = rng.integers(0, 255, (128, 128), dtype=np.uint8)
        mask = np.full((128, 128), 255, dtype=np.uint8)
        batch.add(img, mask)
        batch.add(img, mask)
        results = batch.execute()
        self.assertEqual(len(results), 2)
        for kp, desc in results:
            self.assertIsInstance(kp, (list, tuple))
            if desc is not None:
                self.assertEqual(desc.shape[1], 128)


class TestGpuTileMatchingPath(unittest.TestCase):
    def _call_match_tile_gpu(self, left: np.ndarray, right: np.ndarray, mask: np.ndarray):
        return tile_matching._match_tile_gpu(
            left,
            right,
            left_mask=mask,
            right_mask=mask,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=100,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
        )

    def test_match_tile_gpu_reuses_shared_gpu_sift_pair_matcher(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result) as match_mock:
            left_keypoints, right_keypoints, matches = tile_matching._match_tile_gpu(
                left,
                right,
                left_mask=mask,
                right_mask=mask,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
            )

        self.assertEqual(left_keypoints, [])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])
        match_mock.assert_called_once()
        self.assertEqual(match_mock.call_args.kwargs["sift_kwargs"]["nfeatures"], 100)

    def test_match_tile_gpu_returns_empty_triplet_when_left_has_no_features(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_right_keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[fake_right_keypoint],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result):
            left_keypoints, right_keypoints, matches = self._call_match_tile_gpu(left, right, mask)

        self.assertEqual(left_keypoints, [])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])

    def test_match_tile_gpu_preserves_left_features_when_right_has_no_features(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_left_keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[fake_left_keypoint],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result):
            left_keypoints, right_keypoints, matches = self._call_match_tile_gpu(left, right, mask)

        self.assertEqual(left_keypoints, [fake_left_keypoint])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])


class TestGpuPreparedTilePayload(unittest.TestCase):
    def test_prepare_tile_payload_skips_invalid_window_before_gpu(self):
        window = tile_matching.PairedTileWindow(
            local_window=TileWindow(0, 0, 16, 16),
            left_window=TileWindow(0, 0, 16, 16),
            right_window=TileWindow(0, 0, 16, 16),
        )
        left_values = np.zeros((16, 16), dtype=np.float64)
        right_values = np.zeros((16, 16), dtype=np.float64)

        payload_or_result = tile_matching._prepare_gpu_tile_payload_from_values(
            left_values=left_values,
            right_values=right_values,
            local_window=window.local_window,
            left_window=window.left_window,
            right_window=window.right_window,
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            left_invalid_values=(0.0,),
            right_invalid_values=(0.0,),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.05,
            invalid_pixel_radius=1,
        )

        self.assertIsInstance(payload_or_result, tile_matching.TileMatchResult)
        self.assertEqual(payload_or_result.stats.status, "skipped_valid_pixel_ratio_below_threshold")


class TestGpuTileResultFromMatches(unittest.TestCase):
    def _payload(self) -> tile_matching.PreparedGpuTilePayload:
        window = TileWindow(0, 0, 16, 16)
        return tile_matching.PreparedGpuTilePayload(
            local_window=window,
            left_window=window,
            right_window=window,
            left_image=np.zeros((16, 16), dtype=np.uint8),
            right_image=np.zeros((16, 16), dtype=np.uint8),
            left_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            right_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            left_valid_pixel_count=256,
            right_valid_pixel_count=256,
            left_valid_pixel_ratio=1.0,
            right_valid_pixel_ratio=1.0,
        )

    def test_no_keypoints_preserves_skipped_no_features_status(self):
        result = tile_matching._tile_result_from_matches(
            payload=self._payload(),
            left_keypoints=[],
            right_keypoints=[],
            filtered_matches=[],
        )

        self.assertEqual(result.stats.status, "skipped_no_features")

    def test_no_filtered_matches_preserves_skipped_no_matches_status(self):
        keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)

        result = tile_matching._tile_result_from_matches(
            payload=self._payload(),
            left_keypoints=[keypoint],
            right_keypoints=[keypoint],
            filtered_matches=[],
        )

        self.assertEqual(result.stats.status, "skipped_no_matches")


class TestGpuPipelineOrdering(unittest.TestCase):
    def test_order_gpu_results_restores_input_order(self):
        first = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(
                0, 0, 16, 16, 0, 0, 0, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"
            ),
            left_points=(),
            right_points=(),
        )
        second = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(
                16, 0, 16, 16, 16, 0, 16, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"
            ),
            left_points=(),
            right_points=(),
        )

        ordered = tile_matching._order_indexed_tile_results([(1, second), (0, first)])

        self.assertEqual(ordered, [first, second])


if __name__ == "__main__":
    unittest.main()
