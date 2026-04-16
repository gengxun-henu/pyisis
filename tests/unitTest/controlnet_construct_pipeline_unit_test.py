"""Focused unit tests for the next-stage DOM matching ControlNet pipeline helpers.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-16
Updated: 2026-04-16  Geng Xun added regression coverage for geographic overlap estimation, stereo-pair ControlNet writing, and DOM-to-original conversion helper plumbing.
Updated: 2026-04-16  Geng Xun added semi-integration coverage for dom2ori failure logging and DOM-wrapped ControlNet CLI preparation.
Updated: 2026-04-16  Geng Xun extended the from-dom wrapper coverage to include upstream tie-point merging before dom2ori.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.controlnet_stereopair import (
    ControlNetConfig,
    build_controlnet_for_dom_stereo_pair,
    build_controlnet_for_stereo_pair,
    read_controlnet_config,
)
from controlnet_construct.dom2ori import (
    convert_dom_key_file_via_ground_functions,
    convert_dom_keypoints_to_original,
    convert_points_via_ground_functions,
)
from controlnet_construct.image_match import match_dom_pair_to_key_files
from controlnet_construct.image_overlap import (
    GeoBounds,
    _minimal_longitude_interval,
    extract_camera_ground_bounds,
    find_overlapping_image_pairs,
    geographic_bounds_overlap,
)
from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


LEFT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
RIGHT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828327M_iof.cub")
REAL_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
REAL_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")


class ControlNetConstructPipelineUnitTest(unittest.TestCase):
    def test_minimal_longitude_interval_detects_wraparound_cluster(self):
        start, end, wraps = _minimal_longitude_interval([359.0, 1.0, 2.0])

        self.assertTrue(wraps)
        self.assertAlmostEqual(start, 359.0, places=6)
        self.assertAlmostEqual(end, 2.0, places=6)

    def test_geographic_bounds_overlap_handles_dateline_wrap(self):
        left = GeoBounds("left.cub", -10.0, 10.0, 350.0, 5.0, True, 10, 25)
        right = GeoBounds("right.cub", -5.0, 15.0, 0.0, 20.0, False, 10, 25)
        far = GeoBounds("far.cub", -5.0, 15.0, 40.0, 60.0, False, 10, 25)

        self.assertTrue(geographic_bounds_overlap(left, right))
        self.assertFalse(geographic_bounds_overlap(left, far))

    def test_extract_camera_ground_bounds_returns_valid_bbox_for_real_cube(self):
        bounds = extract_camera_ground_bounds(LEFT_CUBE_PATH, grid_samples=4, grid_lines=4, min_valid_points=4)

        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertGreater(bounds.valid_points, 0)
        self.assertLess(bounds.latitude_min, bounds.latitude_max)

    def test_find_overlapping_image_pairs_matches_real_mdis_sequence(self):
        third_cube_path = workspace_test_data_path("mosrange", "EN0108828332M_iof.cub")
        image_paths = [str(LEFT_CUBE_PATH), str(RIGHT_CUBE_PATH), str(third_cube_path)]

        pairs, bounds = find_overlapping_image_pairs(
            image_paths,
            grid_samples=4,
            grid_lines=4,
            min_valid_points=4,
        )

        self.assertEqual(
            [pair.as_csv_line() for pair in pairs],
            [
                f"{LEFT_CUBE_PATH},{RIGHT_CUBE_PATH}",
                f"{RIGHT_CUBE_PATH},{third_cube_path}",
            ],
        )
        self.assertEqual(set(bounds.keys()), set(image_paths))

    def test_read_controlnet_config_accepts_required_keys(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "ctx",
                        "TargetName": "Mars",
                        "UserName": "zmoratto",
                        "Description": "demo",
                        "PointIdPrefix": "CTX",
                    }
                ),
                encoding="utf-8",
            )

            config = read_controlnet_config(config_path)

            self.assertEqual(config.network_id, "ctx")
            self.assertEqual(config.target_name, "Mars")
            self.assertEqual(config.user_name, "zmoratto")
            self.assertEqual(config.point_id_prefix, "CTX")

    def test_build_controlnet_for_stereo_pair_writes_valid_network(self):
        left_key_file = KeypointFile(1024, 1024, (Keypoint(10.0, 20.0), Keypoint(30.0, 40.0)))
        right_key_file = KeypointFile(1024, 1024, (Keypoint(12.0, 22.0), Keypoint(32.0, 42.0)))
        config = ControlNetConfig(
            network_id="ctx",
            target_name="Mars",
            user_name="zmoratto",
            description="unit test",
            point_id_prefix="CTX",
        )

        with temporary_directory() as temp_dir:
            left_key_path = temp_dir / "ori_A.key"
            right_key_path = temp_dir / "ori_B.key"
            output_net = temp_dir / "stereo_pair.net"

            write_key_file(left_key_path, left_key_file)
            write_key_file(right_key_path, right_key_file)

            result = build_controlnet_for_stereo_pair(
                left_key_path,
                right_key_path,
                LEFT_CUBE_PATH,
                RIGHT_CUBE_PATH,
                config,
                output_net,
                pvl_format=True,
            )

            self.assertEqual(result["point_count"], 2)
            self.assertEqual(result["measure_count"], 4)

            loaded = ip.ControlNet(str(output_net))
            self.assertEqual(loaded.get_num_points(), 2)
            self.assertEqual(loaded.get_num_measures(), 4)
            self.assertEqual(loaded.get_network_id(), "ctx")
            self.assertEqual(loaded.get_target(), "Mars")
            self.assertEqual(loaded.get_user_name(), "zmoratto")

    def test_convert_points_via_ground_functions_preserves_success_order_and_failures(self):
        dom_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 2.0),
                Keypoint(3.0, 4.0),
                Keypoint(5.0, 6.0),
            ),
        )

        def ground_lookup(sample, line):
            if sample == 3.0:
                return None
            return sample + 100.0, line + 200.0

        def image_project(latitude, longitude):
            if latitude == 105.0:
                return None
            return latitude - 100.0, longitude - 200.0

        output_key_file, failures, summary = convert_points_via_ground_functions(
            dom_key_file,
            ground_lookup=ground_lookup,
            image_project=image_project,
            output_width=512,
            output_height=256,
        )

        self.assertEqual(summary.input_count, 3)
        self.assertEqual(summary.output_count, 1)
        self.assertEqual(summary.failure_count, 2)
        self.assertEqual(summary.failure_reasons["dom_lookup_failed"], 1)
        self.assertEqual(summary.failure_reasons["original_projection_failed"], 1)
        self.assertEqual(summary.failure_categories["dom_lookup"], 1)
        self.assertEqual(summary.failure_categories["original_projection"], 1)
        self.assertEqual(output_key_file.points, (Keypoint(1.0, 2.0),))
        self.assertEqual(failures[0].reason, "dom_lookup_failed")
        self.assertEqual(failures[1].reason, "original_projection_failed")

    def test_convert_dom_key_file_via_ground_functions_writes_failure_log(self):
        input_key_file = KeypointFile(
            20,
            20,
            (
                Keypoint(5.0, 5.0),
                Keypoint(25.0, 3.0),
                Keypoint(7.0, 7.0),
            ),
        )

        def ground_lookup(sample, line):
            if sample == 7.0:
                raise RuntimeError("synthetic lookup crash")
            return sample + 100.0, line + 200.0

        def image_project(latitude, longitude):
            return latitude - 100.0, longitude - 200.0

        with temporary_directory() as temp_dir:
            input_key_path = temp_dir / "dom.key"
            output_key_path = temp_dir / "ori.key"
            failure_log_path = temp_dir / "dom2ori_failures.json"
            write_key_file(input_key_path, input_key_file)

            result = convert_dom_key_file_via_ground_functions(
                input_key_path,
                output_key_path,
                ground_lookup=ground_lookup,
                image_project=image_project,
                output_width=20,
                output_height=20,
                failure_log_path=failure_log_path,
            )

            converted = read_key_file(output_key_path)
            logged = json.loads(failure_log_path.read_text(encoding="utf-8"))

        self.assertEqual(result["output_count"], 1)
        self.assertEqual(result["failure_count"], 2)
        self.assertEqual(result["failure_reasons"]["dom_point_out_of_bounds"], 1)
        self.assertEqual(result["failure_reasons"]["dom_lookup_exception"], 1)
        self.assertEqual(converted.points, (Keypoint(5.0, 5.0),))
        self.assertEqual(logged["failure_categories"]["input_validation"], 1)
        self.assertEqual(logged["failure_categories"]["dom_lookup"], 1)

    def test_convert_dom_keypoints_to_original_supports_projection_self_roundtrip(self):
        dom_key_file = KeypointFile(
            50,
            50,
            (
                Keypoint(10.0, 10.0),
                Keypoint(25.0, 30.0),
            ),
        )

        with temporary_directory() as temp_dir:
            dom_key_path = temp_dir / "dom.key"
            output_key_path = temp_dir / "ori.key"
            failure_log_path = temp_dir / "dom2ori_real.json"
            write_key_file(dom_key_path, dom_key_file)

            result = convert_dom_keypoints_to_original(
                dom_key_path,
                REAL_DOM_LEFT,
                REAL_DOM_LEFT,
                output_key_path,
                failure_log_path=failure_log_path,
            )
            converted = read_key_file(output_key_path)
            logged = json.loads(failure_log_path.read_text(encoding="utf-8"))

        self.assertEqual(result["output_count"], 2)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(logged["failure_count"], 0)
        self.assertEqual(len(converted.points), 2)
        for expected, actual in zip(dom_key_file.points, converted.points, strict=True):
            self.assertAlmostEqual(actual.sample, expected.sample, places=3)
            self.assertAlmostEqual(actual.line, expected.line, places=3)

    def test_build_controlnet_for_dom_stereo_pair_wraps_dom2ori_outputs(self):
        config = ControlNetConfig(
            network_id="ctx_dom",
            target_name="Mars",
            user_name="zmoratto",
            description="dom wrapper test",
            point_id_prefix="DOM",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            output_net = temp_dir / "wrapped.net"
            left_output_key = temp_dir / "left_ori.key"
            right_output_key = temp_dir / "right_ori.key"

            match_summary = match_dom_pair_to_key_files(
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                left_dom_key,
                right_dom_key,
                min_valid_pixels=16,
                ratio_test=0.85,
            )
            self.assertGreater(match_summary["point_count"], 0)

            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                config,
                output_net,
                left_output_key_path=left_output_key,
                right_output_key_path=right_output_key,
                pvl_format=True,
            )

            loaded = ip.ControlNet(str(output_net))
            left_output_exists = left_output_key.exists()
            right_output_exists = right_output_key.exists()

        self.assertEqual(result["mode"], "from-dom")
        self.assertTrue(result["merge"]["applied"])
        self.assertEqual(result["left_conversion"]["failure_count"], 0)
        self.assertEqual(result["right_conversion"]["failure_count"], 0)
        self.assertGreater(result["controlnet"]["point_count"], 0)
        self.assertTrue(left_output_exists)
        self.assertTrue(right_output_exists)
        self.assertEqual(loaded.get_num_points(), result["controlnet"]["point_count"])

    def test_build_controlnet_for_dom_stereo_pair_merges_duplicate_dom_points_before_dom2ori(self):
        config = ControlNetConfig(
            network_id="ctx_dom_merge",
            target_name="Mars",
            user_name="zmoratto",
            description="dom merge wrapper test",
            point_id_prefix="DMG",
        )
        duplicated_left = KeypointFile(50, 50, (Keypoint(10.0, 10.0), Keypoint(10.0, 10.0), Keypoint(20.0, 20.0)))
        duplicated_right = KeypointFile(50, 50, (Keypoint(11.0, 11.0), Keypoint(11.0, 11.0), Keypoint(21.0, 21.0)))

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_duplicate_dom.key"
            right_dom_key = temp_dir / "right_duplicate_dom.key"
            left_merged_dom_key = temp_dir / "left_merged_dom.key"
            right_merged_dom_key = temp_dir / "right_merged_dom.key"
            left_output_key = temp_dir / "left_ori.key"
            right_output_key = temp_dir / "right_ori.key"
            output_net = temp_dir / "wrapped_merged.net"

            write_key_file(left_dom_key, duplicated_left)
            write_key_file(right_dom_key, duplicated_right)

            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                config,
                output_net,
                left_merged_dom_key_path=left_merged_dom_key,
                right_merged_dom_key_path=right_merged_dom_key,
                left_output_key_path=left_output_key,
                right_output_key_path=right_output_key,
                pvl_format=True,
            )

            merged_left = read_key_file(left_merged_dom_key)
            merged_right = read_key_file(right_merged_dom_key)
            loaded = ip.ControlNet(str(output_net))

        self.assertTrue(result["merge"]["applied"])
        self.assertEqual(result["merge"]["input_count"], 3)
        self.assertEqual(result["merge"]["unique_count"], 2)
        self.assertEqual(result["merge"]["duplicate_count"], 1)
        self.assertEqual(len(merged_left.points), 2)
        self.assertEqual(len(merged_right.points), 2)
        self.assertEqual(result["left_conversion"]["input_count"], 2)
        self.assertEqual(result["right_conversion"]["input_count"], 2)
        self.assertEqual(result["controlnet"]["point_count"], 2)
        self.assertEqual(loaded.get_num_points(), 2)


if __name__ == "__main__":
    unittest.main()