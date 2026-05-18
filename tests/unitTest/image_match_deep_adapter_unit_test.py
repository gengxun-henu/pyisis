"""Focused unit tests for deep adapter invalid-mask propagation.

Author: Geng Xun
Created: 2026-05-19
Updated: 2026-05-19  Geng Xun added focused coverage for pre-match feature filtering and LoFTR mask passthrough.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.deep_adapter import DeepMatcherAdapter


class _CapturingFeatureMatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def match(self, **kwargs):
        self.calls.append(kwargs)
        features_left = kwargs["features_left"]
        features_right = kwargs["features_right"]
        left_points = np.asarray(features_left["keypoints"], dtype=np.float32).reshape(-1, 2)
        right_points = np.asarray(features_right["keypoints"], dtype=np.float32).reshape(-1, 2)
        pair_count = min(left_points.shape[0], right_points.shape[0])
        return (
            left_points[:pair_count],
            right_points[:pair_count],
            np.ones((pair_count,), dtype=np.float32),
        )


class _CapturingLoFTRMatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def match(self, **kwargs):
        self.calls.append(kwargs)
        return (
            np.zeros((0, 2), dtype=np.float32),
            np.zeros((0, 2), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
        )


class ImageMatchDeepAdapterUnitTest(unittest.TestCase):
    def test_match_pair_filters_superpoint_features_before_matching(self):
        adapter = DeepMatcherAdapter(prefer_gpu=False)
        left_features = {
            "keypoints": np.array([[1.0, 1.0], [4.0, 4.0], [7.0, 7.0]], dtype=np.float32),
            "descriptors": np.array(
                [[10.0, 11.0], [20.0, 21.0], [30.0, 31.0]],
                dtype=np.float32,
            ),
            "scores": np.array([0.1, 0.2, 0.3], dtype=np.float32),
        }
        right_features = {
            "keypoints": np.array([[2.0, 2.0], [5.0, 5.0], [8.0, 8.0]], dtype=np.float32),
            "descriptors": np.array(
                [[12.0, 13.0], [22.0, 23.0], [32.0, 33.0]],
                dtype=np.float32,
            ),
            "scores": np.array([0.4, 0.5, 0.6], dtype=np.float32),
        }
        matcher = _CapturingFeatureMatcher()
        left_mask = np.zeros((10, 10), dtype=bool)
        left_mask[4, 4] = True

        with mock.patch.object(adapter._superpoint, "extract", side_effect=[left_features, right_features]), mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ):
            result = adapter.match_pair(
                matcher_method="lightglue",
                left_image=np.zeros((10, 10), dtype=np.float32),
                right_image=np.zeros((10, 10), dtype=np.float32),
                left_mask=left_mask,
                right_mask=np.zeros((10, 10), dtype=bool),
            )

        self.assertEqual(len(matcher.calls), 1)
        filtered_left = matcher.calls[0]["features_left"]
        filtered_right = matcher.calls[0]["features_right"]
        np.testing.assert_allclose(filtered_left["keypoints"], np.array([[1.0, 1.0], [7.0, 7.0]], dtype=np.float32))
        np.testing.assert_allclose(filtered_left["descriptors"], np.array([[10.0, 11.0], [30.0, 31.0]], dtype=np.float32))
        np.testing.assert_allclose(filtered_left["scores"], np.array([0.1, 0.3], dtype=np.float32))
        np.testing.assert_allclose(filtered_right["keypoints"], right_features["keypoints"])
        self.assertEqual(len(result.left_keypoints), 2)
        self.assertEqual(len(result.right_keypoints), 2)
        self.assertEqual(len(result.matches), 2)

    def test_match_pair_passes_prepared_loftr_masks_into_matcher(self):
        adapter = DeepMatcherAdapter(prefer_gpu=False)
        matcher = _CapturingLoFTRMatcher()
        prepared = {
            "left": object(),
            "right": object(),
            "left_mask": object(),
            "right_mask": object(),
        }
        left_mask = np.zeros((6, 6), dtype=bool)
        right_mask = np.zeros((6, 6), dtype=bool)

        with mock.patch.object(adapter._loftr_frontend, "prepare", return_value=prepared) as prepare_mock, mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ):
            adapter.match_pair(
                matcher_method="loftr",
                left_image=np.ones((6, 6), dtype=np.float32),
                right_image=np.ones((6, 6), dtype=np.float32),
                left_mask=left_mask,
                right_mask=right_mask,
            )

        prepare_mock.assert_called_once()
        self.assertIs(prepare_mock.call_args.kwargs["left_mask"], left_mask)
        self.assertIs(prepare_mock.call_args.kwargs["right_mask"], right_mask)
        self.assertEqual(len(matcher.calls), 1)
        self.assertIs(matcher.calls[0]["left_mask"], prepared["left_mask"])
        self.assertIs(matcher.calls[0]["right_mask"], prepared["right_mask"])


if __name__ == "__main__":
    unittest.main()