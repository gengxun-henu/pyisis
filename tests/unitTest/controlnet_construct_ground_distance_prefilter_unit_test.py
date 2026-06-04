from __future__ import annotations

import tempfile
import sys
import unittest
from unittest import mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct import ground_distance_prefilter as ground_distance_module
from controlnet_construct.ground_distance_prefilter import (
    LUNAR_MEAN_RADIUS_KM,
    filter_stereo_pair_key_files_by_ground_distance,
    filter_stereo_pair_keypoints_by_ground_distance,
    ground_distance_km,
)
from image_match.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


class FakeCube:
    def __init__(self) -> None:
        self.opened_path = None
        self.opened_mode = None
        self.closed = False
        self._open = False

    def open(self, path, mode) -> None:
        self.opened_path = path
        self.opened_mode = mode
        self._open = True

    def band_count(self) -> int:
        return 1

    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        self.closed = True
        self._open = False


class FakeGroundMap:
    instances = []

    def __init__(self, cube, priority) -> None:
        self.cube = cube
        self.priority = priority
        self.band = None
        self.sample = 0.0
        self.line = 0.0
        FakeGroundMap.instances.append(self)

    def set_band(self, band: int) -> None:
        self.band = band

    def set_image(self, sample: float, line: float) -> bool:
        self.sample = sample
        self.line = line
        return sample != 99.0

    def universal_latitude(self) -> float:
        return 0.0

    def universal_longitude(self) -> float:
        return 0.0 if self.sample < 50.0 else 0.01


FakeCameraPriority = type(
    "CameraPriority",
    (),
    {
        "ProjectionFirst": "ProjectionFirst",
        "CameraFirst": "CameraFirst",
    },
)
FakeUniversalGroundMap = type(
    "UniversalGroundMap",
    (FakeGroundMap,),
    {"CameraPriority": FakeCameraPriority},
)
fake_ip = type("FakeIsisPybind", (), {"Cube": FakeCube, "UniversalGroundMap": FakeUniversalGroundMap})


class GroundDistancePrefilterTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeGroundMap.instances.clear()

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

    def test_dom_wrapper_uses_projection_first_and_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left.filtered.key"
            right_output = tmp_path / "right.filtered.key"
            write_key_file(left_input, KeypointFile(100, 100, (Keypoint(1.0, 1.0),)))
            write_key_file(right_input, KeypointFile(100, 100, (Keypoint(60.0, 1.0),)))

            with (
                mock.patch.object(ground_distance_module, "bootstrap_runtime_environment", lambda: None),
                mock.patch.dict(sys.modules, {"isis_pybind": fake_ip}),
            ):
                summary = ground_distance_module.filter_dom_key_files_by_ground_distance(
                    left_input,
                    right_input,
                    left_output,
                    right_output,
                    "left_dom.cub",
                    "right_dom.cub",
                    threshold_km=0.1,
                )

            self.assertEqual(summary["space"], "dom")
            self.assertEqual(summary["geometry_source"], "dom_projection_set_image")
            self.assertEqual(summary["retained_count"], 0)
            self.assertEqual(
                [ground_map.priority for ground_map in FakeGroundMap.instances],
                ["ProjectionFirst", "ProjectionFirst"],
            )

    def test_ori_wrapper_uses_camera_first_and_drops_lookup_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left.filtered.key"
            right_output = tmp_path / "right.filtered.key"
            write_key_file(left_input, KeypointFile(100, 100, (Keypoint(99.0, 1.0),)))
            write_key_file(right_input, KeypointFile(100, 100, (Keypoint(1.0, 1.0),)))

            with (
                mock.patch.object(ground_distance_module, "bootstrap_runtime_environment", lambda: None),
                mock.patch.dict(sys.modules, {"isis_pybind": fake_ip}),
            ):
                summary = ground_distance_module.filter_ori_key_files_by_ground_distance(
                    left_input,
                    right_input,
                    left_output,
                    right_output,
                    "left.cub",
                    "right.cub",
                    threshold_km=1.0,
                )

            self.assertEqual(summary["space"], "ori")
            self.assertEqual(summary["geometry_source"], "ori_camera_set_image")
            self.assertEqual(summary["ground_lookup_failure_count"], 1)
            self.assertEqual(summary["retained_count"], 0)
            self.assertEqual(
                [ground_map.priority for ground_map in FakeGroundMap.instances],
                ["CameraFirst", "CameraFirst"],
            )


if __name__ == "__main__":
    unittest.main()
