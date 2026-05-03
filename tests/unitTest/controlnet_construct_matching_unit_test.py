"""Focused unit tests for DOM matching SIFT helpers and invalid-value handling.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-05-04
Updated: 2026-04-16  Geng Xun added focused regression coverage for DOM cube block matching, global coordinate reassembly, and extreme special-pixel masking.
Updated: 2026-04-17  Geng Xun added regression coverage for tiled DOM matching when the paired DOM cubes differ slightly in raster size.
Updated: 2026-04-17  Geng Xun added focused regression coverage for configurable OpenCV SIFT CLI and detector parameters.
Updated: 2026-04-18  Geng Xun added focused regression coverage for merge-stage RANSAC filtering and default drawMatches visualization output naming.
Updated: 2026-04-18  Geng Xun added optional configurable real LRO DOM matching coverage while preserving repository fixture regressions.
Updated: 2026-04-19  Geng Xun added regression coverage for default image-match visualization output and the explicit no-write CLI switch.
Updated: 2026-04-21  Geng Xun added focused regression coverage for tile valid-pixel ratio filtering, 8-bit zero masking, and the new CLI threshold option.
Updated: 2026-04-22  Geng Xun added focused regression coverage for the default CPU process-pool tile-matching path and the new parallel opt-out CLI flags.
Updated: 2026-04-22  Geng Xun added focused regression coverage for configurable CPU process-pool worker limits in image_match.py.
Updated: 2026-04-23  Geng Xun added regression coverage for invalid-pixel-radius parsing and default low-resolution offset summary fields.
Updated: 2026-04-23  Geng Xun added focused regression coverage for batched projected keypoint conversion so low-resolution offset estimation no longer reopens the same cube for every retained point.
Updated: 2026-04-23  Geng Xun added regression coverage for ISIS reduce-based low-resolution DOM generation and fallback summary propagation.
Updated: 2026-04-24  Geng Xun added regression coverage for configurable low-resolution trimmed-mean fractions through the Python API, CLI, and config defaults.
Updated: 2026-04-26  Geng Xun added regression coverage for BF/FLANN matcher selection and low-resolution reprojection-error gating.
Updated: 2026-04-27  Geng Xun added regression coverage for minimum retained low-resolution matches and projected-offset magnitude gating.
Updated: 2026-05-01  Geng Xun added regression coverage for shell formatting helpers and config default lookup aliases.
Updated: 2026-05-01  Geng Xun added regression coverage for the CLI print-config-default helper path.
Updated: 2026-05-02  Geng Xun added regression coverage for precomputed low-resolution DOM reuse without repeated reduce calls.
Updated: 2026-05-02  Geng Xun added regression coverage for full-resolution image-match tile progress reporting.
Updated: 2026-05-02  Geng Xun added regression coverage for tile-validity prefilter config defaults and summary reporting.
Updated: 2026-05-02  Geng Xun adjusted tile-validity default config keys and prefilter default coverage.
Updated: 2026-05-02  Geng Xun refined tile-validity prefilter fixture to avoid degenerate valid tiles.
Updated: 2026-05-03  Geng Xun added regression coverage for batched parallel tile matching diagnostics.
Updated: 2026-05-03  Geng Xun added regression coverage for tile-validity metadata sidecar output.
Updated: 2026-05-03  Geng Xun added regression coverage for visualization option resolution and target-long-edge reduce levels.
Updated: 2026-05-04  Geng Xun added boundary regression coverage for integer-safe reduce-level calculation.
Updated: 2026-05-04  Geng Xun added regression coverage for crop-window visualization bounds and empty-point validation.
Updated: 2026-05-04  Geng Xun corrected crop-window clamping expectations for 0-based bounds.
"""

from __future__ import annotations

import io
import importlib
from datetime import datetime
import json
import os
import sys
from pathlib import Path
import unittest
from unittest import mock

import cv2
import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import attach_dom_like_projection_mapping, ip, make_test_cube, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

image_match = importlib.import_module("controlnet_construct.image_match")
match_visualization_module = importlib.import_module("controlnet_construct.match_visualization")
lowres_offset_module = importlib.import_module("controlnet_construct.lowres_offset")
build_argument_parser = image_match.build_argument_parser
default_match_visualization_path = image_match.default_match_visualization_path
filter_stereo_pair_keypoints_with_ransac = image_match.filter_stereo_pair_keypoints_with_ransac
match_dom_pair = image_match.match_dom_pair
match_dom_pair_to_key_files = image_match.match_dom_pair_to_key_files
write_stereo_pair_match_visualization_from_key_files = image_match.write_stereo_pair_match_visualization_from_key_files

tile_matching_module = importlib.import_module("controlnet_construct.tile_matching")

keypoints_module = importlib.import_module("controlnet_construct.keypoints")
Keypoint = keypoints_module.Keypoint
KeypointFile = keypoints_module.KeypointFile
write_key_file = keypoints_module.write_key_file


FIXTURE_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
FIXTURE_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")
REAL_LRO_DOM_LEFT_ENV = "ISIS_PYBIND_MATCHING_REAL_DOM_LEFT_CUBE"
REAL_LRO_DOM_RIGHT_ENV = "ISIS_PYBIND_MATCHING_REAL_DOM_RIGHT_CUBE"
DEFAULT_REAL_LRO_DOM_LEFT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104311715LE.cub")
DEFAULT_REAL_LRO_DOM_RIGHT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")
SPECIAL_PIXEL = -1.797693134862315e308


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


def _write_array_to_cube(cube: ip.Cube, values: np.ndarray) -> None:
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(values[line_index, index])
        cube.write(manager)
        manager.next()


def _build_textured_test_image(width: int, height: int) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(image, (width // 4, height // 4), 12, 180, thickness=-1)
    cv2.circle(image, (3 * width // 4, height // 4), 10, 220, thickness=2)
    cv2.rectangle(image, (20, height // 2), (width // 2, height - 20), 140, thickness=3)
    cv2.line(image, (0, height - 1), (width - 1, 0), 255, thickness=2)
    cv2.putText(image, "ISIS", (width // 3, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 200, 2)
    return image.astype(np.float64)


def _write_projected_dom_pair(
    temp_dir: Path,
    left_values: np.ndarray,
    right_values: np.ndarray | None = None,
    *,
    pixel_type=ip.PixelType.Real,
    left_name: str = "left_dom.cub",
    right_name: str = "right_dom.cub",
) -> tuple[Path, Path]:
    left_array = np.asarray(left_values, dtype=np.float64)
    right_array = left_array if right_values is None else np.asarray(right_values, dtype=np.float64)
    height, width = left_array.shape

    left_cube, left_path = make_test_cube(
        temp_dir,
        name=left_name,
        samples=width,
        lines=height,
        bands=1,
        pixel_type=pixel_type,
    )
    right_cube, right_path = make_test_cube(
        temp_dir,
        name=right_name,
        samples=right_array.shape[1],
        lines=right_array.shape[0],
        bands=1,
        pixel_type=pixel_type,
    )
    try:
        _write_array_to_cube(left_cube, left_array)
        _write_array_to_cube(right_cube, right_array)
        attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
        attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(right_array.shape[0]))
    finally:
        left_cube.close()
        right_cube.close()

    return left_path, right_path


class ControlNetConstructMatchingUnitTest(unittest.TestCase):
    def test_create_low_resolution_dom_uses_isis_reduce_scale_mode(self):
        with temporary_directory() as temp_dir:
            source_path = temp_dir / "source_input.cub"
            output_path = temp_dir / "reduced_output.cub"
            source_path.write_bytes(b"fake cube bytes")

            with mock.patch.object(image_match, "_run_command") as run_command_mock, mock.patch.object(
                image_match,
                "_validate_projection_ready_cube",
                return_value=10.0,
            ) as validate_mock:
                result = image_match._create_low_resolution_dom(source_path, output_path, level=3)

        self.assertEqual(result, output_path)
        run_command_mock.assert_called_once_with(
            [
                "reduce",
                f"from={source_path}",
                f"to={output_path}",
                "mode=scale",
                "sscale=8",
                "lscale=8",
                "algorithm=AVERAGE",
            ]
        )
        validate_mock.assert_called_once_with(output_path)

    def test_create_low_resolution_dom_level_zero_copies_source_without_reduce(self):
        with temporary_directory() as temp_dir:
            source_path = temp_dir / "source_level_zero.cub"
            output_path = temp_dir / "copied_level_zero.cub"
            source_path.write_bytes(b"level-zero-copy")

            with mock.patch.object(image_match, "_run_command") as run_command_mock, mock.patch.object(
                image_match,
                "_validate_projection_ready_cube",
                return_value=10.0,
            ) as validate_mock:
                result = image_match._create_low_resolution_dom(source_path, output_path, level=0)

            self.assertEqual(result, output_path)
            self.assertEqual(output_path.read_bytes(), b"level-zero-copy")

        run_command_mock.assert_not_called()
        validate_mock.assert_called_once_with(output_path)

    def test_estimate_low_resolution_projected_offset_reuses_precomputed_doms_without_reduce(self):
        with temporary_directory() as temp_dir:
            left_precomputed = temp_dir / "left_cached_low.cub"
            right_precomputed = temp_dir / "right_cached_low.cub"
            left_pair_local = temp_dir / "left_pair_low.cub"
            right_pair_local = temp_dir / "right_pair_low.cub"
            left_precomputed.write_bytes(b"left-low")
            right_precomputed.write_bytes(b"right-low")

            create_mock = mock.Mock(side_effect=AssertionError("reduce should not run for precomputed DOMs"))
            copy_mock = mock.Mock(side_effect=[left_pair_local, right_pair_local])

            summary = image_match._estimate_low_resolution_projected_offset(
                "left_dom.cub",
                "right_dom.cub",
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                left_low_resolution_dom=left_precomputed,
                right_low_resolution_dom=right_precomputed,
                match_dom_pair_func=mock.Mock(
                    return_value=(KeypointFile(10, 10, ()), KeypointFile(10, 10, ()), {"status": "matched_no_points"})
                ),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(KeypointFile(10, 10, ()), KeypointFile(10, 10, ()), {"applied": False})
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=create_mock,
                copy_precomputed_low_resolution_dom_func=copy_mock,
            )

        create_mock.assert_not_called()
        copy_mock.assert_has_calls(
            [
                mock.call(left_precomputed, temp_dir / "left_dom__level3.cub"),
                mock.call(right_precomputed, temp_dir / "right_dom__level3.cub"),
            ]
        )
        self.assertEqual(summary["status"], "fallback_zero")
        self.assertEqual(summary["failure_reason_code"], "no_matches")
        self.assertEqual(summary["left_low_resolution_dom"], str(left_pair_local))
        self.assertEqual(summary["right_low_resolution_dom"], str(right_pair_local))
        self.assertEqual(summary["low_resolution_dom_sources"]["left"]["mode"], "precomputed_copy")
        self.assertEqual(summary["low_resolution_dom_sources"]["left"]["cache_dom"], str(left_precomputed))

    def test_estimate_low_resolution_projected_offset_reports_reduce_generation_failure(self):
        with temporary_directory() as temp_dir:
            with mock.patch.object(image_match, "_require_command") as require_command_mock, mock.patch.object(
                image_match,
                "_create_low_resolution_dom",
                side_effect=RuntimeError("reduce failed for synthetic test"),
            ):
                summary = image_match._estimate_low_resolution_projected_offset(
                    "left_dom.cub",
                    "right_dom.cub",
                    enabled=True,
                    low_resolution_level=3,
                    low_resolution_output_dir=temp_dir,
                    band=1,
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=64,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=1,
                    matcher_method="bf",
                    ratio_test=0.75,
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                    low_resolution_trim_fraction_each_side=0.05,
                )

        require_command_mock.assert_called_once_with("reduce")
        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertIn("reduce failed for synthetic test", summary["reason"])
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)
        self.assertEqual(summary["retained_match_count"], 0)
        self.assertEqual(summary["trim_fraction_each_side"], 0.05)

    def test_trimmed_mean_allows_custom_fraction_and_rejects_invalid_values(self):
        self.assertAlmostEqual(
            image_match._trimmed_mean([1.0, 2.0, 3.0, 100.0], trim_ratio=0.25),
            2.5,
        )

        with self.assertRaisesRegex(ValueError, r"trim_fraction_each_side must be within \[0\.0, 0\.5\)"):
            image_match._trimmed_mean([1.0, 2.0, 3.0], trim_ratio=0.5)

    def test_format_image_match_default_for_shell_normalizes_scalars(self):
        self.assertEqual(image_match.format_image_match_default_for_shell(True), "1")
        self.assertEqual(image_match.format_image_match_default_for_shell(False), "0")
        self.assertEqual(image_match.format_image_match_default_for_shell(6), "6")
        self.assertEqual(image_match.format_image_match_default_for_shell(0.05), "0.05")
        self.assertEqual(image_match.format_image_match_default_for_shell("bf"), "bf")

    def test_print_image_match_config_default_reads_existing_parser_aliases(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "validPixelPercentThreshold": 0.07,
                            "useParallelCpu": False,
                            "numWorkerParallelCpu": 4,
                            "matcherMethod": "flann",
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                image_match.print_image_match_config_default(config_path, "valid_pixel_percent_threshold"),
                "0.07",
            )
            self.assertEqual(image_match.print_image_match_config_default(config_path, "use_parallel_cpu"), "0")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "num_worker_parallel_cpu"), "4")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "matcher_method"), "flann")

    def test_print_image_match_config_default_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableTileValidityPrefilter": True,
                            "tileValidityCellWidth": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )
            enabled = image_match.print_image_match_config_default(config_path, "enable_tile_validity_prefilter")
            cell_width = image_match.print_image_match_config_default(config_path, "tile_validity_cell_width")

        self.assertEqual(enabled, "1")
        self.assertEqual(cell_width, "256")

    def test_print_image_match_config_default_returns_empty_string_for_missing_field(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps({"ImageMatch": {}}), encoding="utf-8")

            self.assertEqual(image_match.print_image_match_config_default(config_path, "low_resolution_level"), "")

    def test_image_match_cli_print_config_default_exits_before_positional_args(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"enableLowResolutionOffsetEstimation": True}}),
                encoding="utf-8",
            )

            with mock.patch("sys.stdout") as stdout_mock:
                image_match.main(
                    [
                        "--config",
                        str(config_path),
                        "--print-config-default",
                        "enable_low_resolution_offset_estimation",
                    ]
                )

        stdout_mock.write.assert_any_call("1")

    def test_projected_xy_from_keypoints_opens_cube_once_and_preserves_input_order(self):
        class FakeProjection:
            def __init__(self):
                self.calls: list[tuple[float, float]] = []
                self._sample = 0.0
                self._line = 0.0

            def set_world(self, sample: float, line: float) -> bool:
                self.calls.append((sample, line))
                self._sample = sample
                self._line = line
                return True

            def x_coord(self) -> float:
                return self._sample + 1000.0

            def y_coord(self) -> float:
                return self._line + 2000.0

        class FakeCube:
            def __init__(self):
                self.open_calls: list[tuple[str, str]] = []
                self.close_call_count = 0
                self._is_open = False
                self._projection = FakeProjection()

            def open(self, path: str, mode: str) -> None:
                self.open_calls.append((path, mode))
                self._is_open = True

            def projection(self) -> FakeProjection:
                return self._projection

            def is_open(self) -> bool:
                return self._is_open

            def close(self) -> None:
                self.close_call_count += 1
                self._is_open = False

        fake_cube = FakeCube()
        points = (
            Keypoint(10.5, 20.5),
            Keypoint(30.25, 40.75),
            Keypoint(5.0, 6.0),
        )

        with mock.patch.object(image_match.ip, "Cube", return_value=fake_cube):
            projected_points = image_match._projected_xy_from_keypoints("fake_lowres.cub", points)

        self.assertEqual(fake_cube.open_calls, [("fake_lowres.cub", "r")])
        self.assertEqual(fake_cube.close_call_count, 1)
        self.assertEqual(fake_cube._projection.calls, [(10.5, 20.5), (30.25, 40.75), (5.0, 6.0)])
        self.assertEqual(
            projected_points,
            (
                (1010.5, 2020.5),
                (1030.25, 2040.75),
                (1005.0, 2006.0),
            ),
        )

    def test_projected_xy_from_keypoints_in_open_cube_raises_with_failed_point_context(self):
        class FakeProjection:
            def set_world(self, sample: float, line: float) -> bool:
                return (sample, line) != (8.0, 9.0)

            def x_coord(self) -> float:
                return 0.0

            def y_coord(self) -> float:
                return 0.0

        class FakeCube:
            def __init__(self):
                self.projection_call_count = 0

            def projection(self) -> FakeProjection:
                self.projection_call_count += 1
                return FakeProjection()

        fake_cube = FakeCube()

        with self.assertRaisesRegex(
            RuntimeError,
            r"Failed to convert keypoint sample/line to projected coordinates for failing_lowres\.cub: \(8\.0, 9\.0\)",
        ):
            image_match._projected_xy_from_keypoints_in_open_cube(
                fake_cube,
                "failing_lowres.cub",
                (Keypoint(1.0, 2.0), Keypoint(8.0, 9.0)),
            )

        self.assertEqual(fake_cube.projection_call_count, 1)

    def test_default_match_visualization_path_uses_auto_timestamped_name(self):
        timestamp = datetime(2026, 4, 18, 18, 44, 32)

        output_path = default_match_visualization_path(
            "left/A.cub",
            "right/B.cub",
            output_directory="/tmp/rendered",
            timestamp=timestamp,
        )

        self.assertEqual(str(output_path), "/tmp/rendered/A__B__20260418T184432.png")

    def test_filter_stereo_pair_keypoints_with_ransac_strict_drops_marked_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(30.0, 30.0),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="strict",
            )

        self.assertEqual(summary["mode"], "strict")
        self.assertEqual(summary["retained_count"], 4)
        self.assertEqual(summary["dropped_count"], 1)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 0)
        self.assertEqual(len(filtered_left.points), 4)
        self.assertEqual(len(filtered_right.points), 4)

    def test_filter_stereo_pair_keypoints_with_ransac_loose_keeps_small_reprojection_soft_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(8.6, 9.4),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="loose",
                loose_keep_pixel_threshold=1.0,
            )

        self.assertEqual(summary["mode"], "loose")
        self.assertEqual(summary["retained_count"], 5)
        self.assertEqual(summary["dropped_count"], 0)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 1)
        self.assertEqual(summary["soft_outlier_original_indices"], [4])
        self.assertEqual(summary["retained_soft_outlier_positions"], [4])
        self.assertEqual(len(filtered_left.points), 5)
        self.assertEqual(len(filtered_right.points), 5)

    def test_build_argument_parser_accepts_custom_sift_parameters(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--max-features",
                "4096",
                "--sift-octave-layers",
                "5",
                "--sift-contrast-threshold",
                "0.02",
                "--sift-edge-threshold",
                "15.5",
                "--sift-sigma",
                "1.2",
            ]
        )

        self.assertEqual(args.max_features, 4096)
        self.assertEqual(args.sift_octave_layers, 5)
        self.assertAlmostEqual(args.sift_contrast_threshold, 0.02)
        self.assertAlmostEqual(args.sift_edge_threshold, 15.5)
        self.assertAlmostEqual(args.sift_sigma, 1.2)

    def test_build_argument_parser_defaults_to_writing_match_visualization_and_allows_disabling_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--no-write-match-visualization",
            ]
        )

        self.assertTrue(default_args.write_match_visualization)
        self.assertFalse(disabled_args.write_match_visualization)

    def test_build_argument_parser_defaults_to_parallel_cpu_and_allows_disabling_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--no-parallel-cpu",
            ]
        )
        explicit_enabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--use-parallel-cpu",
            ]
        )

        self.assertTrue(default_args.use_parallel_cpu)
        self.assertEqual(default_args.num_worker_parallel_cpu, 8)
        self.assertFalse(disabled_args.use_parallel_cpu)
        self.assertTrue(explicit_enabled_args.use_parallel_cpu)

    def test_build_argument_parser_accepts_custom_parallel_worker_limit(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--num-worker-parallel-cpu",
                "32",
            ]
        )

        self.assertEqual(args.num_worker_parallel_cpu, 32)

    def test_build_argument_parser_rejects_out_of_range_parallel_worker_limit(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--num-worker-parallel-cpu",
                    "0",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--num-worker-parallel-cpu",
                    "4097",
                ]
            )

    def test_build_argument_parser_accepts_valid_pixel_percent_threshold(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--valid-pixel-percent-threshold",
                "0.35",
            ]
        )

        self.assertAlmostEqual(args.valid_pixel_percent_threshold, 0.35)

    def test_build_argument_parser_accepts_tile_validity_prefilter_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--enable-tile-validity-prefilter",
                "--tile-validity-cache-dir",
                "work/tile_validity_cache",
                "--tile-validity-cell-width",
                "512",
                "--tile-validity-cell-height",
                "256",
            ]
        )

        self.assertTrue(args.enable_tile_validity_prefilter)
        self.assertEqual(args.tile_validity_cache_dir, "work/tile_validity_cache")
        self.assertEqual(args.tile_validity_cell_width, 512)
        self.assertEqual(args.tile_validity_cell_height, 256)

    def test_build_argument_parser_accepts_invalid_pixel_radius_and_low_resolution_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--invalid-pixel-radius",
                "2",
                "--matcher-method",
                "flann",
                "--enable-low-resolution-offset-estimation",
                "--low-resolution-level",
                "4",
                "--low-resolution-trim-fraction-each-side",
                "0.1",
                "--low-resolution-max-mean-reprojection-error-pixels",
                "2.5",
                "--low-resolution-min-retained-match-count",
                "5",
                "--low-resolution-max-mean-projected-offset-meters",
                "2000",
                "--left-low-resolution-dom",
                "left_low.cub",
                "--right-low-resolution-dom",
                "right_low.cub",
            ]
        )

        self.assertEqual(args.invalid_pixel_radius, 2)
        self.assertEqual(args.matcher_method, "flann")
        self.assertTrue(args.enable_low_resolution_offset_estimation)
        self.assertEqual(args.low_resolution_level, 4)
        self.assertAlmostEqual(args.low_resolution_trim_fraction_each_side, 0.1)
        self.assertAlmostEqual(args.low_resolution_max_mean_reprojection_error_pixels, 2.5)
        self.assertEqual(args.low_resolution_min_retained_match_count, 5)
        self.assertAlmostEqual(args.low_resolution_max_mean_projected_offset_meters, 2000.0)
        self.assertEqual(args.left_low_resolution_dom, "left_low.cub")
        self.assertEqual(args.right_low_resolution_dom, "right_low.cub")

    def test_build_argument_parser_rejects_invalid_low_resolution_match_count_and_offset_threshold(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-min-retained-match-count",
                    "0",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-max-mean-projected-offset-meters",
                    "-1",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_invalid_pixel_radius(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--invalid-pixel-radius",
                    "-1",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--invalid-pixel-radius",
                    "101",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_low_resolution_level(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-level",
                    "-1",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_low_resolution_trim_fraction_each_side(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-trim-fraction-each-side",
                    "-0.01",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-trim-fraction-each-side",
                    "0.5",
                ]
            )

    def test_load_image_match_defaults_from_config_accepts_low_resolution_trim_fraction(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "image_match_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "lowResolutionTrimFractionEachSide": 0.12,
                            "matcherMethod": "flann",
                            "lowResolutionMaxMeanReprojectionErrorPixels": 2.25,
                            "lowResolutionMinRetainedMatchCount": 6,
                            "lowResolutionMaxMeanProjectedOffsetMeters": 2000.0,
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertAlmostEqual(defaults["low_resolution_trim_fraction_each_side"], 0.12)
        self.assertEqual(defaults["matcher_method"], "flann")
        self.assertAlmostEqual(defaults["low_resolution_max_mean_reprojection_error_pixels"], 2.25)
        self.assertEqual(defaults["low_resolution_min_retained_match_count"], 6)
        self.assertAlmostEqual(defaults["low_resolution_max_mean_projected_offset_meters"], 2000.0)

    def test_load_image_match_defaults_from_config_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableTileValidityPrefilter": True,
                            "tileValidityCacheDir": "work/tile_validity_cache",
                            "tileValidityCellWidth": 512,
                            "tileValidityCellHeight": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertTrue(defaults["enable_tile_validity_prefilter"])
        self.assertEqual(defaults["tile_validity_cache_dir"], "work/tile_validity_cache")
        self.assertEqual(defaults["tile_validity_cell_width"], 512)
        self.assertEqual(defaults["tile_validity_cell_height"], 256)

    def test_create_descriptor_matcher_supports_bf_and_flann(self):
        fake_bf_matcher = object()
        fake_flann_matcher = object()

        with mock.patch.object(tile_matching_module.cv2, "BFMatcher", return_value=fake_bf_matcher) as bf_mock, mock.patch.object(
            tile_matching_module.cv2,
            "FlannBasedMatcher",
            return_value=fake_flann_matcher,
        ) as flann_mock:
            self.assertIs(tile_matching_module._create_descriptor_matcher("bf"), fake_bf_matcher)
            self.assertIs(tile_matching_module._create_descriptor_matcher("flann"), fake_flann_matcher)

        bf_mock.assert_called_once_with(tile_matching_module.cv2.NORM_L2, crossCheck=False)
        flann_mock.assert_called_once_with(
            {"algorithm": 1, "trees": tile_matching_module.DEFAULT_FLANN_TREES},
            {"checks": tile_matching_module.DEFAULT_FLANN_CHECKS},
        )

    def test_match_dom_pair_passes_matcher_method_into_parallel_tile_tasks(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_matcher_method.cub",
                right_name="right_matcher_method.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    matcher_method="flann",
                )

        submitted_tasks = parallel_mock.call_args.args[0]
        self.assertTrue(submitted_tasks)
        self.assertTrue(all(task.matcher_method == "flann" for task in submitted_tasks))
        self.assertEqual(summary["matcher"]["matcher_method_requested"], "flann")
        self.assertEqual(summary["matcher"]["matcher_method_used"], "flann")
        self.assertEqual(summary["matcher"]["flann_index_params"]["algorithm"], "KDTree")

    def test_match_dom_pair_forwards_custom_low_resolution_trim_fraction(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_trim_forward.cub",
                right_name="right_lowres_trim_forward.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "succeeded",
                    "fallback_offset_zero": False,
                    "reason": "ok",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 0,
                    "trim_fraction_each_side": 0.12,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 2000.0,
                    "mean_projected_offset_meters": 0.0,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_trim_fraction_each_side=0.12,
                )

        self.assertAlmostEqual(summary["low_resolution_trim_fraction_each_side"], 0.12)
        self.assertAlmostEqual(summary["low_resolution_offset"]["trim_fraction_each_side"], 0.12)
        self.assertAlmostEqual(
            estimate_mock.call_args.kwargs["low_resolution_trim_fraction_each_side"],
            0.12,
        )

    def test_match_dom_pair_forwards_low_resolution_min_match_count_and_offset_threshold(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_threshold_forward.cub",
                right_name="right_lowres_threshold_forward.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "fallback_zero",
                    "fallback_offset_zero": True,
                    "reason": "thresholded",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 4,
                    "trim_fraction_each_side": 0.05,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 2000.0,
                    "mean_projected_offset_meters": None,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_min_retained_match_count=5,
                    low_resolution_max_mean_projected_offset_meters=2000.0,
                )

        self.assertEqual(summary["low_resolution_offset"]["min_retained_match_count"], 5)
        self.assertAlmostEqual(summary["low_resolution_offset"]["max_mean_projected_offset_meters"], 2000.0)
        self.assertEqual(
            estimate_mock.call_args.kwargs["low_resolution_min_retained_match_count"],
            5,
        )
        self.assertAlmostEqual(
            estimate_mock.call_args.kwargs["low_resolution_max_mean_projected_offset_meters"],
            2000.0,
        )

    def test_match_dom_pair_prefilters_invalid_tiles_and_reports_summary(self):
        values = np.zeros((32, 64), dtype=np.float64)
        values[:, :32] = _build_textured_test_image(32, 32)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter.cub",
                right_name="right_prefilter.cub",
            )
            cache_dir = temp_dir / "tile_validity_cache"
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cache_dir=cache_dir,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

        self.assertTrue(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count"], 2)
        self.assertEqual(summary["tile_count_before_preindex_filter"], 2)
        self.assertEqual(summary["tile_count_after_preindex_filter"], 1)
        self.assertEqual(summary["preindexed_skipped_tile_count"], 1)
        self.assertEqual(summary["tile_validity_cache_dir"], str(cache_dir))
        self.assertEqual(
            summary["full_resolution_skipped_tile_count"],
            summary["skipped_tile_count"] - summary["preindexed_skipped_tile_count"],
        )
        self.assertIn(summary["left_tile_validity_index"]["status"], {"rebuilt", "hit"})
        self.assertIn(summary["right_tile_validity_index"]["status"], {"rebuilt", "hit"})

    def test_match_dom_pair_keeps_prefilter_disabled_by_default(self):
        values = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_default.cub",
                right_name="right_prefilter_default.cub",
            )
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                valid_pixel_percent_threshold=0.2,
                invalid_pixel_radius=0,
                use_parallel_cpu=False,
            )

        self.assertFalse(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count_before_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["tile_count_after_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["preindexed_skipped_tile_count"], 0)
        self.assertIsNone(summary["tile_validity_cache_dir"])

    def test_estimate_low_resolution_projected_offset_rejects_large_reprojection_error(self):
        with temporary_directory() as temp_dir:
            left_low_res_dom, right_low_res_dom = _write_projected_dom_pair(
                temp_dir,
                _build_textured_test_image(32, 32),
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_low_res_reproj.cub",
                right_name="right_low_res_reproj.cub",
            )

            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(25.0, 25.0),
                    Keypoint(30.0, 25.0),
                    Keypoint(25.0, 30.0),
                    Keypoint(30.0, 30.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                left_low_res_dom,
                right_low_res_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.0,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=4,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[left_low_res_dom, right_low_res_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "reprojection_error_above_threshold")
        self.assertGreater(summary["trimmed_mean_reprojection_error_pixels"], 3.0)
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)

    def test_estimate_low_resolution_projected_offset_rejects_retained_match_count_below_threshold(self):
        with temporary_directory() as temp_dir:
            fake_left_dom = temp_dir / "left_min_matches.cub"
            fake_right_dom = temp_dir / "right_min_matches.cub"
            fake_left_dom.write_bytes(b"left")
            fake_right_dom.write_bytes(b"right")
            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(15.0, 15.0),
                    Keypoint(20.0, 15.0),
                    Keypoint(15.0, 20.0),
                    Keypoint(20.0, 20.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                fake_left_dom,
                fake_right_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=5,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[fake_left_dom, fake_right_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "retained_match_count_below_threshold")
        self.assertEqual(summary["retained_match_count"], 4)
        self.assertEqual(summary["min_retained_match_count"], 5)
        self.assertIsNone(summary["trimmed_mean_reprojection_error_pixels"])
        self.assertIsNone(summary["mean_projected_offset_meters"])

    def test_estimate_low_resolution_projected_offset_rejects_large_mean_projected_offset(self):
        with temporary_directory() as temp_dir:
            left_cube, left_low_res_dom = make_test_cube(
                temp_dir,
                name="left_low_res_offset_threshold.cub",
                samples=32,
                lines=32,
                bands=1,
                pixel_type=ip.PixelType.UnsignedByte,
            )
            right_cube, right_low_res_dom = make_test_cube(
                temp_dir,
                name="right_low_res_offset_threshold.cub",
                samples=32,
                lines=32,
                bands=1,
                pixel_type=ip.PixelType.UnsignedByte,
            )
            try:
                _write_array_to_cube(left_cube, _build_textured_test_image(32, 32))
                _write_array_to_cube(right_cube, _build_textured_test_image(32, 32))
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=32.0)
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=5000.0, upper_left_y=32.0)
            finally:
                left_cube.close()
                right_cube.close()

            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                    Keypoint(12.0, 12.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                    Keypoint(12.0, 12.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                left_low_res_dom,
                right_low_res_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.0,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=5,
                low_resolution_max_mean_projected_offset_meters=2000.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[left_low_res_dom, right_low_res_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "mean_projected_offset_above_threshold")
        self.assertGreater(summary["mean_projected_offset_meters"], 2000.0)
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)

    def test_estimate_low_resolution_projected_offset_rejects_insufficient_points_for_homography(self):
        with temporary_directory() as temp_dir:
            fake_left_dom = temp_dir / "left_insufficient.cub"
            fake_right_dom = temp_dir / "right_insufficient.cub"
            fake_left_dom.write_bytes(b"left")
            fake_right_dom.write_bytes(b"right")
            filtered_left = KeypointFile(32, 32, (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0), Keypoint(3.0, 3.0)))
            filtered_right = KeypointFile(32, 32, (Keypoint(1.5, 1.5), Keypoint(2.5, 2.5), Keypoint(3.5, 3.5)))

            summary = image_match._estimate_low_resolution_projected_offset(
                fake_left_dom,
                fake_right_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=3,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": False,
                            "status": "skipped_insufficient_points",
                            "homography_matrix": None,
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[fake_left_dom, fake_right_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "insufficient_points_for_homography")
        self.assertIsNone(summary["trimmed_mean_reprojection_error_pixels"])

    def test_build_argument_parser_rejects_out_of_range_valid_pixel_percent_threshold(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--valid-pixel-percent-threshold",
                    "1.5",
                ]
            )

    def test_build_sift_detector_forwards_custom_parameters_to_opencv(self):
        fake_detector = object()

        with mock.patch.object(image_match.cv2, "SIFT_create", return_value=fake_detector) as sift_create:
            detector = image_match._build_sift_detector(
                max_features=2048,
                octave_layers=5,
                contrast_threshold=0.03,
                edge_threshold=12.0,
                sigma=1.8,
            )

        self.assertIs(detector, fake_detector)
        sift_create.assert_called_once_with(
            nfeatures=2048,
            nOctaveLayers=5,
            contrastThreshold=0.03,
            edgeThreshold=12.0,
            sigma=1.8,
        )

    def test_match_dom_pair_uses_shared_extent_for_unequal_dom_sizes(self):
        left_width = 128
        right_width = 120
        height = 128
        left_image = _build_textured_test_image(left_width, height)
        right_image = left_image[:, :right_width]

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_shared_extent_dom.cub", samples=left_width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_shared_extent_dom.cub", samples=right_width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, left_image)
                _write_array_to_cube(right_cube, right_image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertTrue(summary["dimension_mismatch"])
        self.assertEqual(summary["shared_extent_width"], right_width)
        self.assertEqual(summary["shared_extent_height"], height)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= left_width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= right_width for point in right_key_file.points))

    def test_match_dom_pair_reassembles_global_coordinates_after_tiling(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertGreater(summary["tile_count"], 1)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(any(point.sample > 64.0 or point.line > 64.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= height for point in left_key_file.points))

    def test_match_dom_pair_uses_parallel_helper_for_multi_tile_runs_by_default(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=64,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=64,
                    left_start_y=0,
                    right_start_x=64,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(80.0, 20.0),),
                right_points=(Keypoint(80.5, 20.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_default.cub",
                right_name="right_parallel_default.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                left_key_file, right_key_file, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                )

        parallel_mock.assert_called_once()
        self.assertEqual(parallel_mock.call_args.kwargs["max_workers"], 4)
        self.assertTrue(summary["parallel_cpu_requested"])
        self.assertEqual(summary["num_worker_parallel_cpu"], 8)
        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 4)
        self.assertEqual(summary["point_count"], 2)
        self.assertEqual(len(left_key_file.points), 2)
        self.assertEqual(len(right_key_file.points), 2)

    def test_match_dom_pair_respects_requested_parallel_worker_limit(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_cap.cub",
                right_name="right_parallel_cap.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                )

        parallel_mock.assert_called_once()
        self.assertEqual(parallel_mock.call_args.kwargs["max_workers"], 2)
        self.assertEqual(summary["num_worker_parallel_cpu"], 2)
        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_worker_count"], 2)

    def test_match_dom_pair_reports_serial_backend_when_parallel_cpu_is_disabled(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_disabled.cub",
                right_name="right_parallel_disabled.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
                use_parallel_cpu=False,
            )

        self.assertFalse(summary["parallel_cpu_requested"])
        self.assertEqual(summary["num_worker_parallel_cpu"], 8)
        self.assertFalse(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "serial")
        self.assertEqual(summary["parallel_cpu_worker_count"], 1)

    def test_match_dom_pair_progress_reports_full_resolution_tile_count_and_completion(self):
        image = _build_textured_test_image(128, 128)

        def fake_serial_tile_match_tasks(windows, **kwargs):
            progress_callback = kwargs.get("progress_callback")
            tile_results = []
            for paired_window in windows:
                if progress_callback is not None:
                    progress_callback()
                tile_results.append(
                    image_match.TileMatchResult(
                        stats=image_match.TileMatchStats(
                            local_start_x=paired_window.local_window.start_x,
                            local_start_y=paired_window.local_window.start_y,
                            width=paired_window.local_window.width,
                            height=paired_window.local_window.height,
                            left_start_x=paired_window.left_window.start_x,
                            left_start_y=paired_window.left_window.start_y,
                            right_start_x=paired_window.right_window.start_x,
                            right_start_y=paired_window.right_window.start_y,
                            left_valid_pixel_count=paired_window.local_window.width * paired_window.local_window.height,
                            right_valid_pixel_count=paired_window.local_window.width * paired_window.local_window.height,
                            left_valid_pixel_ratio=1.0,
                            right_valid_pixel_ratio=1.0,
                            left_feature_count=0,
                            right_feature_count=0,
                            match_count=0,
                            status="skipped_no_matches",
                        ),
                        left_points=(),
                        right_points=(),
                    )
                )
            return tile_results

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_progress.cub",
                right_name="right_progress.cub",
            )
            stderr = io.StringIO()

            with mock.patch.object(image_match.sys, "stderr", stderr), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                side_effect=fake_serial_tile_match_tasks,
            ) as serial_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    use_parallel_cpu=False,
                    show_progress=True,
                )

        progress_output = stderr.getvalue()
        self.assertEqual(summary["tile_count"], 4)
        self.assertIn("4 TILE(s) to process at full resolution", progress_output)
        self.assertIn("4/4 TILE(s) done", progress_output)
        self.assertIsNotNone(serial_mock.call_args.kwargs["progress_callback"])

    def test_match_dom_pair_skips_invalid_only_tiles_but_keeps_valid_tile(self):
        width = 96
        height = 96
        image = np.full((height, width), SPECIAL_PIXEL, dtype=np.float64)
        image[48:96, 48:96] = _build_textured_test_image(48, 48)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_invalid_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_invalid_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=40,
                block_width=48,
                block_height=48,
                overlap_x=0,
                overlap_y=0,
                min_valid_pixels=32,
            )

        self.assertEqual(summary["tile_count"], 4)
        self.assertGreaterEqual(summary["skipped_tile_count"], 3)
        self.assertGreater(summary["point_count"], 0)
        self.assertIn(
            "skipped_insufficient_valid_pixels",
            {tile["status"] for tile in summary["tiles"]},
        )

    def test_match_dom_pair_skips_tile_when_valid_ratio_is_below_threshold(self):
        image = np.zeros((48, 48), dtype=np.float64)
        image[12:36, 12:36] = 100.0

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_ratio_skip.cub",
                right_name="right_ratio_skip.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=32,
                valid_pixel_percent_threshold=0.3,
                invalid_pixel_radius=0,
            )

        self.assertEqual(summary["point_count"], 0)
        self.assertEqual(summary["valid_pixel_percent_threshold"], 0.3)
        self.assertEqual(summary["tile_count"], 1)
        self.assertEqual(summary["tiles"][0]["status"], "skipped_valid_pixel_ratio_below_threshold")
        self.assertAlmostEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 0.25, places=6)
        self.assertAlmostEqual(summary["tiles"][0]["right_valid_pixel_ratio"], 0.25, places=6)

    def test_match_dom_pair_reports_valid_pixel_ratio_fields_in_summary(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_ratio_summary.cub",
                right_name="right_ratio_summary.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
            )

        self.assertIn("valid_pixel_percent_threshold", summary)
        self.assertIn("min_valid_pixels", summary)
        self.assertIn("left_valid_pixel_ratio", summary["tiles"][0])
        self.assertIn("right_valid_pixel_ratio", summary["tiles"][0])
        self.assertGreaterEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 0.0)
        self.assertLessEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 1.0)

    def test_match_dom_pair_reports_disabled_low_resolution_offset_summary_by_default(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_default.cub",
                right_name="right_lowres_default.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
            )

        low_resolution_summary = summary["low_resolution_offset"]
        self.assertFalse(low_resolution_summary["enabled"])
        self.assertEqual(low_resolution_summary["status"], "disabled")
        self.assertFalse(low_resolution_summary["fallback_offset_zero"])
        self.assertEqual(low_resolution_summary["delta_x_projected"], 0.0)
        self.assertEqual(low_resolution_summary["delta_y_projected"], 0.0)
        self.assertEqual(low_resolution_summary["retained_match_count"], 0)

    def test_match_dom_pair_treats_zero_as_invalid_for_8bit_images(self):
        image = np.zeros((48, 48), dtype=np.float64)
        image[8:40, 8:40] = np.tile(np.arange(1.0, 33.0, dtype=np.float64), (32, 1))

        with temporary_directory() as temp_dir:
            byte_left_path, byte_right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_byte_zero_invalid.cub",
                right_name="right_byte_zero_invalid.cub",
            )
            real_left_path, real_right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.Real,
                left_name="left_real_zero_valid.cub",
                right_name="right_real_zero_valid.cub",
            )

            _, _, byte_summary = match_dom_pair(
                byte_left_path,
                byte_right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
            )
            _, _, real_summary = match_dom_pair(
                real_left_path,
                real_right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
            )

        self.assertLess(byte_summary["tiles"][0]["left_valid_pixel_ratio"], 1.0)
        self.assertAlmostEqual(real_summary["tiles"][0]["left_valid_pixel_ratio"], 1.0, places=6)

    def test_match_dom_pair_on_real_dom_cubes_returns_in_bounds_keypoints(self):
        left_key_file, right_key_file, summary = match_dom_pair(
            FIXTURE_DOM_LEFT,
            FIXTURE_DOM_RIGHT,
            min_valid_pixels=16,
            ratio_test=0.85,
            invalid_pixel_radius=0,
        )

        self.assertEqual(left_key_file.image_width, 50)
        self.assertEqual(left_key_file.image_height, 50)
        self.assertEqual(right_key_file.image_width, 50)
        self.assertEqual(right_key_file.image_height, 50)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertGreater(summary["point_count"], 0)
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in right_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in right_key_file.points))

    def test_match_dom_pair_supports_configurable_real_lro_dom_pair_when_available(self):
        real_left_dom, real_right_dom = _configured_real_lro_dom_pair()
        if not real_left_dom.exists() or not real_right_dom.exists():
            self.skipTest(
                "Real LRO DOM pair is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} and {REAL_LRO_DOM_RIGHT_ENV} if needed."
            )

        left_key_file, right_key_file, summary = match_dom_pair(
            real_left_dom,
            real_right_dom,
            min_valid_pixels=16,
            ratio_test=0.85,
        )

        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertGreater(summary["point_count"], 0)
        self.assertGreater(left_key_file.image_width, 0)
        self.assertGreater(left_key_file.image_height, 0)
        self.assertGreater(right_key_file.image_width, 0)
        self.assertGreater(right_key_file.image_height, 0)
        self.assertTrue(all(1.0 <= point.sample <= left_key_file.image_width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= left_key_file.image_height for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= right_key_file.image_width for point in right_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= right_key_file.image_height for point in right_key_file.points))

    def test_write_stereo_pair_match_visualization_from_key_files_writes_default_png(self):
        width = 24
        height = 24
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="A.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="B.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left.key"
            right_key_path = temp_dir / "right.key"
            write_key_file(left_key_path, KeypointFile(width, height, (Keypoint(5.0, 5.0), Keypoint(10.0, 12.0))))
            write_key_file(right_key_path, KeypointFile(width, height, (Keypoint(6.0, 6.0), Keypoint(11.0, 13.0))))

            result = write_stereo_pair_match_visualization_from_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                output_directory=temp_dir,
                timestamp=datetime(2026, 4, 18, 18, 44, 32),
                scale_factor=3.0,
                highlight_match_indices=[1],
            )
            output_exists = Path(result["output_path"]).exists()

        self.assertTrue(result["output_path"].endswith("A__B__20260418T184432.png"))
        self.assertEqual(result["point_count"], 2)
        self.assertEqual(result["highlighted_match_count"], 1)
        self.assertTrue(output_exists)

    def test_match_dom_pair_to_key_files_writes_default_match_visualization_next_to_key_outputs(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_stage.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_stage.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left_stage.key"
            right_key_path = temp_dir / "right_stage.key"
            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )
            visualization_output_path = Path(result["match_visualization"]["output_path"])
            visualization_output_exists = visualization_output_path.exists()
            visualization_output_parent = visualization_output_path.parent

        self.assertGreater(result["point_count"], 0)
        self.assertIn("match_visualization", result)
        self.assertTrue(visualization_output_exists)
        self.assertEqual(visualization_output_parent, Path(left_key_path).parent)

    def test_parallel_tile_batch_worker_reuses_open_cubes_for_task_shard(self):
        open_paths: list[str] = []
        close_count = 0

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, path, mode):
                open_paths.append(str(path))
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                nonlocal close_count
                close_count += 1
                self._open = False

        tasks = [
            tile_matching_module.IndexedTileMatchTask(
                index=0,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
            tile_matching_module.IndexedTileMatchTask(
                index=1,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
        ]

        def fake_match_task_with_open_cubes(task, **kwargs):
            return tile_matching_module.TileMatchResult(
                stats=tile_matching_module.TileMatchStats(
                    local_start_x=task.paired_window.local_window.start_x,
                    local_start_y=task.paired_window.local_window.start_y,
                    width=task.paired_window.local_window.width,
                    height=task.paired_window.local_window.height,
                    left_start_x=task.paired_window.left_window.start_x,
                    left_start_y=task.paired_window.left_window.start_y,
                    right_start_x=task.paired_window.right_window.start_x,
                    right_start_y=task.paired_window.right_window.start_y,
                    left_valid_pixel_count=64,
                    right_valid_pixel_count=64,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_insufficient_matches",
                ),
                left_points=(),
                right_points=(),
            )

        with mock.patch.object(tile_matching_module.ip, "Cube", FakeCube), mock.patch.object(
            tile_matching_module,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching_module,
            "_match_tile_task_with_open_cubes",
            side_effect=fake_match_task_with_open_cubes,
        ):
            results = tile_matching_module._match_tile_task_batch_worker(tuple(tasks))

        self.assertEqual(open_paths, ["left.cub", "right.cub"])
        self.assertEqual(close_count, 2)
        self.assertEqual([index for index, _ in results], [0, 1])

    def test_match_dom_pair_reports_batched_parallel_backend(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            )
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_batched_parallel.cub",
                right_name="right_batched_parallel.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ):
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                )

        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 2)

    def test_match_dom_pair_to_key_files_writes_tile_validity_metadata(self):
        values = np.zeros((32, 64), dtype=np.float64)
        values[:, :32] = _build_textured_test_image(32, 32)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_metadata.cub",
                right_name="right_prefilter_metadata.cub",
            )
            left_key = temp_dir / "dom_keys" / "left.key"
            right_key = temp_dir / "dom_keys" / "right.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"
            left_key.parent.mkdir(parents=True)
            metadata_output.parent.mkdir(parents=True)

            match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key,
                right_key,
                metadata_output=metadata_output,
                write_match_visualization=False,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        image_match_payload = payload["image_match"]
        self.assertTrue(image_match_payload["tile_validity_prefilter_enabled"])
        self.assertEqual(image_match_payload["preindexed_skipped_tile_count"], 1)
        self.assertEqual(image_match_payload["tile_count_before_preindex_filter"], 2)
        self.assertEqual(image_match_payload["tile_count_after_preindex_filter"], 1)
        self.assertTrue(str(image_match_payload["tile_validity_cache_dir"]).endswith("tile_validity_cache"))

    def test_visualization_memory_profile_resolves_target_long_edges(self):
        high = match_visualization_module.resolve_visualization_options(memory_profile="high-memory")
        balanced = match_visualization_module.resolve_visualization_options(memory_profile="balanced")
        low = match_visualization_module.resolve_visualization_options(memory_profile="low-memory")

        self.assertEqual(high.visualization_target_long_edge, 4096)
        self.assertEqual(balanced.visualization_target_long_edge, 2048)
        self.assertEqual(low.visualization_target_long_edge, 1024)
        self.assertEqual(balanced.visualization_mode, "auto")
        self.assertEqual(balanced.preview_cache_source, "auto")

    def test_visualization_option_validation_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "visualization_mode"):
            match_visualization_module.resolve_visualization_options(visualization_mode="huge")
        with self.assertRaisesRegex(ValueError, "memory_profile"):
            match_visualization_module.resolve_visualization_options(memory_profile="tiny")
        with self.assertRaisesRegex(ValueError, "visualization_target_long_edge must be positive"):
            match_visualization_module.resolve_visualization_options(visualization_target_long_edge=0)
        with self.assertRaisesRegex(ValueError, "preview_crop_margin_pixels must be >= 0"):
            match_visualization_module.resolve_visualization_options(preview_crop_margin_pixels=-1)

    def test_reduce_level_from_target_long_edge_uses_pair_common_longest_edge(self):
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 4096), 1)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 2048), 2)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(1000, 2048), 0)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4096, 4096), 0)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4097, 4096), 1)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4097, 2048), 2)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(2049, 2048), 1)
        self.assertEqual(
            lowres_offset_module.reduce_level_for_pair_target_long_edge(
                left_width=2048,
                left_height=1024,
                right_width=16384,
                right_height=512,
                target_long_edge=2048,
            ),
            3,
        )

    def test_visualization_crop_window_uses_keypoint_bounds_and_margin(self):
        points = (Keypoint(20.0, 30.0), Keypoint(80.0, 90.0))

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=120,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y, window.width, window.height), (9, 19, 81, 81))

    def test_visualization_crop_window_clips_to_image_start(self):
        points = (Keypoint(1.0, 1.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (0, 0))
        self.assertEqual((window.width, window.height), (11, 11))

    def test_visualization_crop_window_clips_to_image_end(self):
        points = (Keypoint(100.0, 100.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (89, 89))
        self.assertEqual((window.start_x + window.width, window.start_y + window.height), (100, 100))

    def test_visualization_crop_window_clips_out_of_bounds_point(self):
        points = (Keypoint(1000.0, 1000.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (99, 99))
        self.assertEqual((window.width, window.height), (1, 1))

    def test_visualization_crop_window_rejects_invalid_dimensions(self):
        points = (Keypoint(1.0, 1.0),)

        with self.assertRaisesRegex(ValueError, "image_width"):
            match_visualization_module.crop_window_for_keypoints(
                points,
                image_width=0,
                image_height=100,
                margin_pixels=0,
            )
        with self.assertRaisesRegex(ValueError, "image_height"):
            match_visualization_module.crop_window_for_keypoints(
                points,
                image_width=100,
                image_height=0,
                margin_pixels=0,
            )

    def test_visualization_crop_window_rejects_empty_points(self):
        with self.assertRaisesRegex(ValueError, "At least one keypoint"):
            match_visualization_module.crop_window_for_keypoints(
                (),
                image_width=100,
                image_height=100,
                margin_pixels=10,
            )


if __name__ == "__main__":
    unittest.main()
