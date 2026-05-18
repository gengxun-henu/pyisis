"""Focused unit tests for the learning_methods deep-match manifest runner.

Author: Geng Xun
Created: 2026-05-16
Last Modified: 2026-05-16
Updated: 2026-05-16  Geng Xun added regression coverage for manifest execution with a fake deep matcher adapter and standardized NPZ results.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
LEARNING_METHODS_DIR = EXAMPLES_DIR / "learning_methods"
for import_path in (EXAMPLES_DIR, LEARNING_METHODS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.deep_match_manifest import (
    DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
    build_deep_match_pair_manifest,
    read_deep_match_task_result,
    write_deep_match_pair_manifest,
    write_deep_match_task_arrays,
)
from image_match.tile_matching import PairedTileWindow, TileMatchTask, TileWindow
from run_deep_match_manifest import build_argument_parser, run_manifest


def _make_tile_task() -> TileMatchTask:
    return TileMatchTask(
        left_dom_path="left_dom.cub",
        right_dom_path="right_dom.cub",
        band=1,
        paired_window=PairedTileWindow(
            local_window=TileWindow(start_x=0, start_y=0, width=8, height=8),
            left_window=TileWindow(start_x=10, start_y=20, width=8, height=8),
            right_window=TileWindow(start_x=30, start_y=40, width=8, height=8),
        ),
        minimum_value=None,
        maximum_value=None,
        lower_percent=0.5,
        upper_percent=99.5,
        invalid_values=(),
        special_pixel_abs_threshold=1.0e300,
        min_valid_pixels=4,
        valid_pixel_percent_threshold=0.0,
        invalid_pixel_radius=1,
        ratio_test=0.75,
        matcher_method="lightglue",
        max_features=128,
        sift_octave_layers=3,
        sift_contrast_threshold=0.04,
        sift_edge_threshold=10.0,
        sift_sigma=1.6,
        image_space="dom",
        use_gpu=False,
        gpu_batch_size=4,
    )


class FakeDeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool) -> None:
        self.prefer_gpu = prefer_gpu
        self._device = "cuda" if prefer_gpu else "cpu"

    def match_pair(self, *, matcher_method: str, left_image, right_image, left_mask=None, right_mask=None):
        self.matcher_method = matcher_method
        self.left_shape = tuple(left_image.shape)
        self.right_shape = tuple(right_image.shape)
        self.left_mask_shape = None if left_mask is None else tuple(left_mask.shape)
        self.right_mask_shape = None if right_mask is None else tuple(right_mask.shape)
        return SimpleNamespace(
            left_keypoints=(np.array([1.0, 1.0]), np.array([4.0, 4.0]), np.array([7.0, 7.0])),
            right_keypoints=(np.array([2.0, 2.0]), np.array([5.0, 5.0]), np.array([7.0, 7.0])),
            matches=(
                SimpleNamespace(queryIdx=0, trainIdx=0, distance=0.1),
                SimpleNamespace(queryIdx=1, trainIdx=1, distance=0.2),
                SimpleNamespace(queryIdx=2, trainIdx=2, distance=0.3),
            ),
        )


class LearningMethodsDeepManifestRunnerUnitTest(unittest.TestCase):
    def test_build_argument_parser_accepts_manifest_runner_options(self):
        parser = build_argument_parser()

        parsed = parser.parse_args(
            [
                "tasks.json",
                "--device",
                "cpu",
                "--summary-output",
                "summary.json",
                "--fail-fast",
                "--skip-existing",
            ]
        )

        self.assertEqual(parsed.manifest, "tasks.json")
        self.assertEqual(parsed.device, "cpu")
        self.assertEqual(parsed.summary_output, "summary.json")
        self.assertTrue(parsed.fail_fast)
        self.assertTrue(parsed.skip_existing)

    def test_run_manifest_writes_standard_result_npz_and_filters_invalid_mask_matches(self):
        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[_make_tile_task()],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            left_mask = np.zeros((8, 8), dtype=bool)
            right_mask = np.zeros((8, 8), dtype=bool)
            left_mask[4, 4] = True
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=left_mask,
                right_mask=right_mask,
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            summary = run_manifest(
                manifest_path,
                device="cpu",
                adapter_factory=FakeDeepMatcherAdapter,
            )
            result = read_deep_match_task_result(record)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["task_count"], 1)
            self.assertEqual(summary["succeeded_task_count"], 1)
            self.assertEqual(summary["failed_task_count"], 0)
            self.assertEqual(summary["tasks"][0]["raw_match_count"], 3)
            self.assertEqual(summary["tasks"][0]["invalid_mask_removed_count"], 1)
            self.assertEqual(result["metadata"]["status"], "matched")
            self.assertEqual(result["metadata"]["match_count"], 2)
            np.testing.assert_allclose(result["left_points"], np.array([[1.0, 1.0], [7.0, 7.0]], dtype=np.float32))
            np.testing.assert_allclose(result["right_points"], np.array([[2.0, 2.0], [7.0, 7.0]], dtype=np.float32))
            np.testing.assert_allclose(result["scores"], np.array([0.9, 0.7], dtype=np.float32), rtol=1e-6)
            self.assertTrue(Path(record.log_path).exists())

    def test_run_manifest_passes_invalid_masks_into_adapter(self):
        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[_make_tile_task()],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            left_mask = np.zeros((8, 8), dtype=bool)
            right_mask = np.zeros((8, 8), dtype=bool)
            left_mask[2, 2] = True
            right_mask[6, 6] = True
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=left_mask,
                right_mask=right_mask,
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            created_adapters: list[FakeDeepMatcherAdapter] = []

            def _adapter_factory(*, prefer_gpu: bool):
                adapter = FakeDeepMatcherAdapter(prefer_gpu=prefer_gpu)
                created_adapters.append(adapter)
                return adapter

            run_manifest(
                manifest_path,
                device="cpu",
                adapter_factory=_adapter_factory,
            )

            self.assertEqual(len(created_adapters), 1)
            self.assertEqual(created_adapters[0].left_mask_shape, (8, 8))
            self.assertEqual(created_adapters[0].right_mask_shape, (8, 8))


if __name__ == "__main__":
    unittest.main()
