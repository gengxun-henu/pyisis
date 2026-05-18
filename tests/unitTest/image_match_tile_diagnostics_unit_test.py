"""Unit tests for image_match tile-aware diagnostic orchestration.

Author: Geng Xun
Created: 2026-05-19
Last Modified: 2026-05-19
Updated: 2026-05-19  Geng Xun added coverage that adaptive diagnostics use
    windowed tile reads instead of full-band cube reads.
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

from image_match.texture_sparseness import ImageSparsenessSummary  # noqa: E402
from image_match import image_match as image_match_module  # noqa: E402


class _FakeCube:
    def __init__(self, data: np.ndarray):
        self.data = data
        self.opened_path: str | None = None
        self.closed = False

    def open(self, path: str, mode: str) -> None:
        self.opened_path = path
        self.closed = False

    def is_open(self) -> bool:
        return not self.closed

    def close(self) -> None:
        self.closed = True

    def sample_count(self) -> int:
        return int(self.data.shape[1])

    def line_count(self) -> int:
        return int(self.data.shape[0])

    def pixel_type(self):
        return object()

    def has_group(self, name: str) -> bool:
        return False


class _FakeIpModule:
    class PixelType:
        UnsignedByte = "unsigned-byte"
        SignedByte = "signed-byte"

    def __init__(self, cube: _FakeCube):
        self._cube = cube

    def Cube(self) -> _FakeCube:
        return self._cube


class ImageMatchTileDiagnosticsUnitTest(unittest.TestCase):
    def test_texture_sparseness_diagnostics_use_window_reader_not_full_band(self):
        data = np.arange(64, dtype=np.float32).reshape((8, 8))
        fake_cube = _FakeCube(data)
        reader_calls = []

        def fail_full_band(*args, **kwargs):
            raise AssertionError("full-band read should not be used for tile diagnostics")

        def read_window(cube, window, *, band: int):
            reader_calls.append((window.start_x, window.start_y, window.width, window.height, band))
            return cube.data[
                window.start_y : window.start_y + window.height,
                window.start_x : window.start_x + window.width,
            ]

        def fake_sparseness_from_reader(*, image_width, image_height, read_window, **kwargs):
            self.assertEqual(image_width, 8)
            self.assertEqual(image_height, 8)
            tile_values = read_window(0, 0, 4, 4)
            np.testing.assert_array_equal(tile_values, data[:4, :4])
            return ImageSparsenessSummary(
                tile_total_count=1,
                tile_valid_count=1,
                tile_size=4,
                tile_step=4,
                min_valid_pixel_ratio=0.3,
                aggregation_quantile=0.9,
                image_texture_sparseness=0.25,
                sparseness_quantiles={"p10": 0.25, "p50": 0.25, "p90": 0.25, "max": 0.25},
                tile_metrics=(),
            )

        originals = {
            "ip": image_match_module.ip,
            "_read_full_cube_band": image_match_module._read_full_cube_band,
            "_read_cube_window": image_match_module._read_cube_window,
            "compute_image_texture_sparseness_from_reader": getattr(
                image_match_module,
                "compute_image_texture_sparseness_from_reader",
                None,
            ),
        }
        image_match_module.ip = _FakeIpModule(fake_cube)
        image_match_module._read_full_cube_band = fail_full_band
        image_match_module._read_cube_window = read_window
        image_match_module.compute_image_texture_sparseness_from_reader = fake_sparseness_from_reader
        try:
            sparseness, solar_geometry, solar_error = (
                image_match_module._compute_texture_sparseness_and_geometry_from_cube_path(
                    "fake.cub",
                    band=1,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                )
            )
        finally:
            image_match_module.ip = originals["ip"]
            image_match_module._read_full_cube_band = originals["_read_full_cube_band"]
            image_match_module._read_cube_window = originals["_read_cube_window"]
            if originals["compute_image_texture_sparseness_from_reader"] is None:
                delattr(image_match_module, "compute_image_texture_sparseness_from_reader")
            else:
                image_match_module.compute_image_texture_sparseness_from_reader = originals[
                    "compute_image_texture_sparseness_from_reader"
                ]

        self.assertEqual(sparseness.image_texture_sparseness, 0.25)
        self.assertIsNone(solar_geometry)
        self.assertIsNotNone(solar_error)
        self.assertEqual(reader_calls, [(0, 0, 4, 4, 1)])


if __name__ == "__main__":
    unittest.main()
