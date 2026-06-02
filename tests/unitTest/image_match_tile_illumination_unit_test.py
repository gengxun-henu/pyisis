from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.tile_illumination import (
    RepresentativePoint,
    TileIlluminationPair,
    TileIlluminationSample,
    TileWindowMetadata,
    angular_difference_degrees,
    illumination_difference_score,
    illumination_pair_to_payload,
    summarize_tile_illumination_pairs,
)


class ImageMatchTileIlluminationUnitTest(unittest.TestCase):
    def test_angular_difference_handles_wraparound(self):
        self.assertEqual(angular_difference_degrees(359.0, 1.0), 2.0)
        self.assertEqual(angular_difference_degrees(10.0, 350.0), 20.0)

    def test_illumination_difference_score_returns_none_when_all_inputs_none(self):
        self.assertIsNone(
            illumination_difference_score(
                azimuth_difference_degrees=None,
                incidence_difference_degrees=None,
                elevation_difference_degrees=None,
            )
        )

    def test_illumination_difference_score_returns_none_when_all_inputs_non_finite(self):
        self.assertIsNone(
            illumination_difference_score(
                azimuth_difference_degrees=float("nan"),
                incidence_difference_degrees=float("inf"),
                elevation_difference_degrees=float("-inf"),
            )
        )

    def test_illumination_difference_score_uses_only_finite_inputs(self):
        score = illumination_difference_score(
            azimuth_difference_degrees=float("nan"),
            incidence_difference_degrees=45.0,
            elevation_difference_degrees=float("inf"),
        )

        self.assertEqual(score, 0.5)

    def test_pair_payload_preserves_solar_elevation(self):
        point = RepresentativePoint(
            status="center_projectable",
            selection_reason="center pixel projected to source camera",
            local_x_0_based=5,
            local_y_0_based=6,
            dom_sample_1_based=11.0,
            dom_line_1_based=12.0,
            pixel_available=True,
            radiometric_valid_for_matching=False,
            source_projectable=True,
            failure_reason=None,
        )
        sample = TileIlluminationSample(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=3,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=32, height=32),
            representative_point=point,
            latitude=-88.5,
            longitude=123.0,
            source_sample_1_based=21.5,
            source_line_1_based=22.5,
            sun_azimuth_degrees=359.0,
            incidence_angle_degrees=87.0,
            solar_elevation_degrees=3.0,
        )
        pair = TileIlluminationPair.from_samples(tile_index=3, left=sample, right=sample)

        payload = illumination_pair_to_payload(pair)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["left"]["solar_elevation_degrees"], 3.0)
        self.assertEqual(payload["azimuth_difference_degrees"], 0.0)

    def test_summary_counts_projectable_and_skipped_tiles(self):
        failed_point = RepresentativePoint(
            status="no_projectable_pixel",
            selection_reason="no pixel projected to source camera",
            local_x_0_based=None,
            local_y_0_based=None,
            dom_sample_1_based=None,
            dom_line_1_based=None,
            pixel_available=False,
            radiometric_valid_for_matching=None,
            source_projectable=False,
            failure_reason="no_projectable_pixel",
        )
        failed_sample = TileIlluminationSample.failed(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=1,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=16, height=16),
            representative_point=failed_point,
        )
        summary = summarize_tile_illumination_pairs((
            TileIlluminationPair.from_samples(tile_index=1, left=failed_sample, right=failed_sample),
        ))

        self.assertEqual(summary["tile_count"], 1)
        self.assertEqual(summary["projectable_tile_count"], 0)
        self.assertEqual(summary["skipped_tile_count"], 1)
        self.assertEqual(summary["skip_reasons"]["both_failed"], 1)


if __name__ == "__main__":
    unittest.main()
