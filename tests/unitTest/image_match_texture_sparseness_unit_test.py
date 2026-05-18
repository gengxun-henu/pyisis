"""Unit tests for the tile-level texture sparseness helpers.

Author: Geng Xun
Created: 2026-05-18
Last Modified: 2026-05-18
Updated: 2026-05-18  Geng Xun added focused coverage for tile-window generation,
    lightweight GLCM contrast/energy, invalid-tile filtering, image-level P90
    aggregation, and pair-level weak-side aggregation.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.texture_sparseness import (  # noqa: E402  (sys.path manipulated above)
    ImageSparsenessSummary,
    PairSparsenessSummary,
    aggregate_pair_texture_sparseness,
    compute_image_texture_sparseness,
    compute_lightweight_glcm,
    generate_tile_windows,
)


def _flat_image(width: int, height: int, fill: float = 128.0) -> np.ndarray:
    return np.full((height, width), float(fill), dtype=np.float32)


def _striped_image(width: int, height: int, period: int = 8) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.float32)
    for column in range(width):
        if (column // period) % 2 == 0:
            image[:, column] = 220.0
        else:
            image[:, column] = 30.0
    return image


def _random_image(width: int, height: int, *, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(height, width)).astype(np.float32)


class ImageMatchTextureSparsenessUnitTest(unittest.TestCase):
    def test_generate_tile_windows_covers_image_edges(self):
        windows = generate_tile_windows(600, 600, tile_size=256, tile_step=128)

        self.assertGreater(len(windows), 0)
        last_window_end_y = max(window[0] + window[2] for window in windows)
        last_window_end_x = max(window[1] + window[3] for window in windows)
        self.assertGreaterEqual(last_window_end_y, 600)
        self.assertGreaterEqual(last_window_end_x, 600)
        for start_y, start_x, height, width in windows:
            self.assertGreaterEqual(start_y, 0)
            self.assertGreaterEqual(start_x, 0)
            self.assertGreater(height, 0)
            self.assertGreater(width, 0)

    def test_generate_tile_windows_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            generate_tile_windows(0, 100)
        with self.assertRaises(ValueError):
            generate_tile_windows(100, 100, tile_size=0)
        with self.assertRaises(ValueError):
            generate_tile_windows(100, 100, tile_step=0)
        with self.assertRaises(ValueError):
            generate_tile_windows(100, 100, tile_size=64, tile_step=128)

    def test_compute_lightweight_glcm_is_low_contrast_high_energy_on_flat_tile(self):
        tile = _flat_image(64, 64, fill=100.0)

        contrast, energy = compute_lightweight_glcm(tile, levels=16, distance=1)

        self.assertAlmostEqual(contrast, 0.0, places=6)
        self.assertGreater(energy, 0.9)

    def test_compute_lightweight_glcm_has_higher_contrast_on_striped_tile(self):
        flat_tile = _flat_image(64, 64, fill=128.0)
        striped_tile = _striped_image(64, 64, period=4)

        flat_contrast, flat_energy = compute_lightweight_glcm(flat_tile)
        striped_contrast, striped_energy = compute_lightweight_glcm(striped_tile)

        self.assertGreater(striped_contrast, flat_contrast)
        self.assertLess(striped_energy, flat_energy)

    def test_compute_lightweight_glcm_handles_all_invalid_mask(self):
        tile = _striped_image(32, 32)
        invalid = np.zeros(tile.shape, dtype=bool)

        contrast, energy = compute_lightweight_glcm(tile, valid_mask=invalid)

        self.assertEqual(contrast, 0.0)
        self.assertEqual(energy, 1.0)

    def test_compute_image_texture_sparseness_rejects_invalid_tiles(self):
        image = _flat_image(512, 512, fill=120.0)
        invalid_mask = np.ones(image.shape, dtype=bool)
        # Only the first 64 rows are valid; tiles whose valid ratio falls below
        # 0.30 should be excluded from aggregation.
        invalid_mask[:64, :] = False

        summary = compute_image_texture_sparseness(image, invalid_mask=invalid_mask)

        self.assertIsInstance(summary, ImageSparsenessSummary)
        self.assertGreater(summary.tile_total_count, summary.tile_valid_count)
        for metric in summary.tile_metrics:
            self.assertGreaterEqual(metric.valid_pixel_ratio, summary.min_valid_pixel_ratio)

    def test_compute_image_texture_sparseness_returns_none_when_no_tiles_valid(self):
        image = _flat_image(64, 64)
        invalid_mask = np.ones(image.shape, dtype=bool)

        summary = compute_image_texture_sparseness(image, invalid_mask=invalid_mask)

        self.assertIsNone(summary.image_texture_sparseness)
        self.assertEqual(summary.tile_valid_count, 0)

    def test_flat_image_is_more_sparse_than_random_image(self):
        flat_image = _flat_image(384, 384, fill=128.0)
        random_image = _random_image(384, 384)

        flat_summary = compute_image_texture_sparseness(flat_image)
        random_summary = compute_image_texture_sparseness(random_image)

        self.assertIsNotNone(flat_summary.image_texture_sparseness)
        self.assertIsNotNone(random_summary.image_texture_sparseness)
        self.assertGreater(
            float(flat_summary.image_texture_sparseness),
            float(random_summary.image_texture_sparseness),
        )

    def test_image_summary_quantiles_are_monotonic(self):
        striped_image = _striped_image(384, 384, period=6)

        summary = compute_image_texture_sparseness(striped_image)

        quantiles = summary.sparseness_quantiles
        self.assertIsNotNone(quantiles["p10"])
        self.assertIsNotNone(quantiles["p50"])
        self.assertIsNotNone(quantiles["p90"])
        self.assertLessEqual(quantiles["p10"], quantiles["p50"])
        self.assertLessEqual(quantiles["p50"], quantiles["p90"])
        self.assertGreaterEqual(quantiles["max"], quantiles["p90"])

    def test_aggregate_pair_takes_weak_side(self):
        sparse_summary = compute_image_texture_sparseness(_flat_image(384, 384))
        rich_summary = compute_image_texture_sparseness(_random_image(384, 384))

        pair_left_weaker = aggregate_pair_texture_sparseness(sparse_summary, rich_summary)
        pair_right_weaker = aggregate_pair_texture_sparseness(rich_summary, sparse_summary)

        self.assertIsInstance(pair_left_weaker, PairSparsenessSummary)
        self.assertEqual(pair_left_weaker.weaker_side, "left")
        self.assertEqual(pair_right_weaker.weaker_side, "right")
        self.assertAlmostEqual(
            float(pair_left_weaker.pair_texture_sparseness),
            float(sparse_summary.image_texture_sparseness),
        )

    def test_aggregate_pair_handles_missing_summaries(self):
        sparse_summary = compute_image_texture_sparseness(_flat_image(384, 384))
        empty_summary = compute_image_texture_sparseness(
            _flat_image(384, 384),
            invalid_mask=np.ones((384, 384), dtype=bool),
        )

        pair_left_empty = aggregate_pair_texture_sparseness(empty_summary, sparse_summary)
        pair_right_empty = aggregate_pair_texture_sparseness(sparse_summary, empty_summary)
        pair_both_empty = aggregate_pair_texture_sparseness(empty_summary, empty_summary)

        self.assertEqual(pair_left_empty.weaker_side, "right")
        self.assertEqual(pair_right_empty.weaker_side, "left")
        self.assertIsNone(pair_both_empty.pair_texture_sparseness)
        self.assertIsNone(pair_both_empty.weaker_side)


if __name__ == "__main__":
    unittest.main()
