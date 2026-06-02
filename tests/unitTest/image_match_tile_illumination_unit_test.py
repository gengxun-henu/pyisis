from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np


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

    def test_shadowed_pixel_can_be_selected_when_source_projectable(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.full((5, 5), 10.0, dtype=np.float64)
        radiometric_mask = np.ones((5, 5), dtype=bool)
        radiometric_mask[2, 2] = False

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=100,
            tile_start_y=200,
            radiometric_valid_for_matching_mask=radiometric_mask,
            project_source_pixel=lambda sample, line: {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": 11.0,
                "source_line": 12.0,
                "sun_azimuth": 250.0,
                "incidence": 87.5,
            },
        )

        self.assertEqual(selected.representative_point.status, "center_projectable")
        self.assertFalse(selected.representative_point.radiometric_valid_for_matching)
        self.assertEqual(selected.representative_point.dom_sample_1_based, 103.0)
        self.assertEqual(selected.representative_point.dom_line_1_based, 203.0)
        self.assertEqual(selected.solar_elevation_degrees, 2.5)

    def test_center_projection_failure_uses_nearest_projectable_pixel(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.ones((3, 3), dtype=np.float64)
        calls = []

        def projector(sample, line):
            calls.append((sample, line))
            if (sample, line) == (2.0, 2.0):
                raise RuntimeError("center outside source camera")
            return {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": sample + 10.0,
                "source_line": line + 10.0,
                "sun_azimuth": 180.0,
                "incidence": 80.0,
            }

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=projector,
        )

        self.assertEqual(selected.representative_point.status, "nearest_projectable_pixel")
        self.assertEqual(calls[0], (2.0, 2.0))
        self.assertGreaterEqual(len(calls), 2)

    def test_finite_isis_special_center_pixel_is_skipped_by_default(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.ones((3, 3), dtype=np.float64)
        values[1, 1] = np.finfo(np.float32).max
        calls = []

        def projector(sample, line):
            calls.append((sample, line))
            return {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": sample + 10.0,
                "source_line": line + 10.0,
                "sun_azimuth": 180.0,
                "incidence": 80.0,
            }

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=projector,
        )

        self.assertEqual(selected.representative_point.status, "nearest_projectable_pixel")
        self.assertEqual(selected.representative_point.local_x_0_based, 1)
        self.assertEqual(selected.representative_point.local_y_0_based, 0)
        self.assertNotIn((2.0, 2.0), calls)

    def test_pixel_available_rejects_non_finite_values(self):
        from image_match.tile_illumination_geometry import pixel_available

        self.assertFalse(pixel_available(float("nan")))
        self.assertFalse(pixel_available(float("inf")))
        self.assertFalse(pixel_available(float("-inf")))

    def test_no_projectable_pixel_reports_failure(self):
        from image_match.tile_illumination_geometry import select_representative_point

        selected = select_representative_point(
            dom_values=np.ones((2, 2), dtype=np.float64),
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=lambda sample, line: (_ for _ in ()).throw(RuntimeError("not covered")),
        )

        self.assertEqual(selected.representative_point.status, "no_projectable_pixel")
        self.assertEqual(selected.representative_point.failure_reason, "no_projectable_pixel")


if __name__ == "__main__":
    unittest.main()
