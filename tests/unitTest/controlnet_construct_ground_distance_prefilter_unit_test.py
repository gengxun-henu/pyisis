from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from controlnet_construct.ground_distance_prefilter import (
    LUNAR_MEAN_RADIUS_KM,
    filter_stereo_pair_key_files_by_ground_distance,
    filter_stereo_pair_keypoints_by_ground_distance,
    ground_distance_km,
)
from image_match.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


class GroundDistancePrefilterTest(unittest.TestCase):
    def test_ground_distance_km_handles_longitude_wrap(self) -> None:
        distance = ground_distance_km(
            0.0,
            359.99,
            0.0,
            0.01,
            radius_km=LUNAR_MEAN_RADIUS_KM,
        )

        self.assertLess(distance, 1.0)

    def test_filter_drops_only_pairs_over_threshold_and_keeps_alignment(self) -> None:
        left_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0), Keypoint(3.0, 3.0)),
        )
        right_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(10.0, 10.0), Keypoint(20.0, 20.0), Keypoint(30.0, 30.0)),
        )
        left_lookup = {
            (1.0, 1.0): (0.0, 0.0),
            (2.0, 2.0): (0.0, 0.0),
            (3.0, 3.0): (1.0, 1.0),
        }
        right_lookup = {
            (10.0, 10.0): (0.0, 0.0),
            (20.0, 20.0): (0.0, 0.01),
            (30.0, 30.0): (1.0, 1.0),
        }

        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left_key_file,
            right_key_file,
            left_ground_lookup=lambda sample, line: left_lookup[(sample, line)],
            right_ground_lookup=lambda sample, line: right_lookup[(sample, line)],
            threshold_km=0.1,
        )

        self.assertEqual(filtered_left.points, (Keypoint(1.0, 1.0), Keypoint(3.0, 3.0)))
        self.assertEqual(filtered_right.points, (Keypoint(10.0, 10.0), Keypoint(30.0, 30.0)))
        self.assertEqual(summary["input_count"], 3)
        self.assertEqual(summary["retained_count"], 2)
        self.assertEqual(summary["dropped_ground_distance_count"], 1)

    def test_lookup_failure_drops_pair_by_default(self) -> None:
        left_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0)),
        )
        right_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(10.0, 10.0), Keypoint(20.0, 20.0)),
        )

        def left_lookup(sample: float, line: float) -> tuple[float, float] | None:
            if sample == 2.0:
                return None
            return (0.0, 0.0)

        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left_key_file,
            right_key_file,
            left_ground_lookup=left_lookup,
            right_ground_lookup=lambda sample, line: (0.0, 0.0),
            threshold_km=0.1,
        )

        self.assertEqual(len(filtered_left.points), 1)
        self.assertEqual(len(filtered_right.points), 1)
        self.assertEqual(summary["ground_lookup_failure_count"], 1)

    def test_threshold_zero_disables_filter_without_lookups(self) -> None:
        left_key_file = KeypointFile(1000, 1000, (Keypoint(1.0, 1.0),))
        right_key_file = KeypointFile(1000, 1000, (Keypoint(10.0, 10.0),))

        def raising_lookup(sample: float, line: float) -> tuple[float, float] | None:
            raise AssertionError("lookup should not be called when threshold is disabled")

        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left_key_file,
            right_key_file,
            left_ground_lookup=raising_lookup,
            right_ground_lookup=raising_lookup,
            threshold_km=0.0,
        )

        self.assertEqual(filtered_left.points, left_key_file.points)
        self.assertEqual(filtered_right.points, right_key_file.points)
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["status"], "disabled")

    def test_key_file_wrapper_writes_filtered_outputs(self) -> None:
        left_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0)),
        )
        right_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(10.0, 10.0), Keypoint(20.0, 20.0)),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left.filtered.key"
            right_output = tmp_path / "right.filtered.key"
            write_key_file(left_input, left_key_file)
            write_key_file(right_input, right_key_file)

            summary = filter_stereo_pair_key_files_by_ground_distance(
                left_input,
                right_input,
                left_output,
                right_output,
                left_ground_lookup=lambda sample, line: (0.0, 0.0),
                right_ground_lookup=lambda sample, line: (0.0, 0.0)
                if sample == 10.0
                else (0.0, 0.01),
                threshold_km=0.1,
            )

            self.assertEqual(summary["retained_count"], 1)
            self.assertEqual(len(read_key_file(left_output).points), 1)
            self.assertEqual(len(read_key_file(right_output).points), 1)


if __name__ == "__main__":
    unittest.main()
