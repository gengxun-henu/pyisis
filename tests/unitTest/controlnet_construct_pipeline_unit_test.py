"""Focused unit tests for the next-stage DOM matching ControlNet pipeline helpers.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-21
Updated: 2026-04-16  Geng Xun added regression coverage for geographic overlap estimation, stereo-pair ControlNet writing, and DOM-to-original conversion helper plumbing.
Updated: 2026-04-16  Geng Xun added semi-integration coverage for dom2ori failure logging and DOM-wrapped ControlNet CLI preparation.
Updated: 2026-04-16  Geng Xun extended the from-dom wrapper coverage to include upstream tie-point merging before dom2ori.
Updated: 2026-04-17  Geng Xun added focused coverage for per-pair JSON sidecar report writing alongside stereo-pair ControlNet output.
Updated: 2026-04-17  Geng Xun added coordinate-basis JSON checks and a no-drift semi-integration chain from image_match through dom2ori into ControlNet measures.
Updated: 2026-04-18  Geng Xun added focused wrapper coverage for merge-stage RANSAC filtering and auto-named drawMatches visualization output before dom2ori.
Updated: 2026-04-18  Geng Xun added optional configurable real LRO DOM pipeline coverage while preserving repository fixture regressions.
Updated: 2026-04-20  Geng Xun added focused coverage for stereo-pair point-id namespacing, batch auto-assigned pair IDs, backward-compatible defaults, and CLI pair-id override behavior.
Updated: 2026-04-20  Geng Xun added regression coverage for explicitly routed post-RANSAC drawMatches output paths in the from-dom wrapper.
Updated: 2026-04-21  Geng Xun added focused regression coverage for pipeline step timing logs and JSON timing summaries.
Updated: 2026-04-21  Geng Xun added regression coverage for forwarding the example config valid-pixel threshold into the batch image-match stage.
"""

from __future__ import annotations

import json
import io
import os
import subprocess
import sys
import textwrap
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout


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
    build_controlnets_for_dom_overlap_list,
    build_controlnet_for_dom_stereo_pair,
    build_controlnet_for_stereo_pair,
    default_controlnet_report_path,
    main as controlnet_stereopair_main,
    read_controlnet_config,
    write_controlnet_result_report,
)
from controlnet_construct.dom2ori import (
    main as dom2ori_main,
    convert_dom_key_file_via_ground_functions,
    convert_dom_keypoints_to_original,
    convert_paired_dom_key_files_via_ground_functions,
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
REAL_LRO_DOM_LEFT_ENV = "ISIS_PYBIND_PIPELINE_REAL_DOM_LEFT_CUBE"
REAL_LRO_DOM_RIGHT_ENV = "ISIS_PYBIND_PIPELINE_REAL_DOM_RIGHT_CUBE"
DEFAULT_REAL_LRO_DOM_LEFT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871LE.cub")
DEFAULT_REAL_LRO_DOM_RIGHT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")
RUN_PIPELINE_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_pipeline_example.sh"


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


class ControlNetConstructPipelineUnitTest(unittest.TestCase):
    def test_run_pipeline_example_writes_timing_json_and_logs_step_durations(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            reports_dir = work_dir / "reports"
            work_dir.mkdir()
            reports_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            timing_json_path = temp_dir / "pipeline_timing.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]

                        if script_name == "image_overlap.py":
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0

                        if script_name == "image_match.py":
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            if "--metadata-output" in args:
                                metadata_path = Path(args[args.index("--metadata-output") + 1])
                                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                                metadata_path.write_text(json.dumps({{"status": "matched"}}), encoding="utf-8")
                            if "--match-visualization-output-dir" in args:
                                viz_dir = Path(args[args.index("--match-visualization-output-dir") + 1])
                                viz_dir.mkdir(parents=True, exist_ok=True)
                                (viz_dir / "synthetic.png").write_text("png", encoding="utf-8")
                            print(json.dumps({{"status": "matched", "point_count": 1}}))
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            if "--report-dir" in args:
                                report_dir = Path(args[args.index("--report-dir") + 1])
                                report_dir.mkdir(parents=True, exist_ok=True)
                                (report_dir / "synthetic_pair.summary.json").write_text(json.dumps({{"point_count": 1}}), encoding="utf-8")
                            print(json.dumps({{"pair_count": 1}}))
                            return 0

                        if script_name == "controlnet_merge.py":
                            merge_script_path = Path(args[3])
                            merge_script_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.write_text("#!/usr/bin/env bash\\nexit 0\\n", encoding="utf-8")
                            os.chmod(merge_script_path, 0o755)
                            print(json.dumps({{"merge_script": str(merge_script_path)}}))
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--skip-final-merge",
                    "--timing-json",
                    str(timing_json_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            timing_payload = json.loads(timing_json_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("START image_overlap", completed.stdout)
        self.assertIn("END image_overlap status=success duration=", completed.stdout)
        self.assertEqual(timing_payload["pipeline"]["status"], "success")
        self.assertEqual(
            [entry["name"] for entry in timing_payload["steps"]],
            ["image_overlap", "image_match_batch", "pairwise_controlnets", "merge"],
        )
        self.assertEqual(timing_payload["pair_matches"][0]["name"], "image_match:left__right")
        self.assertTrue(all(entry["duration_seconds"] >= 0 for entry in timing_payload["steps"]))

    def test_run_pipeline_example_forwards_valid_pixel_threshold_from_config_to_image_match(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "ImageMatch": {
                            "valid_pixel_percent_threshold": 0.05,
                        },
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]

                        if script_name == "image_overlap.py":
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0

                        if script_name == "image_match.py":
                            if "--valid-pixel-percent-threshold" not in args:
                                raise SystemExit("missing valid pixel threshold")
                            threshold = args[args.index("--valid-pixel-percent-threshold") + 1]
                            if threshold != "0.05":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_merge.py":
                            merge_script_path = Path(args[3])
                            merge_script_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.write_text("#!/usr/bin/env bash\\nexit 0\\n", encoding="utf-8")
                            os.chmod(merge_script_path, 0o755)
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Valid pixel percent threshold: 0.05", completed.stdout)

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
                        "PairId": "S12",
                    }
                ),
                encoding="utf-8",
            )

            config = read_controlnet_config(config_path)

            self.assertEqual(config.network_id, "ctx")
            self.assertEqual(config.target_name, "Mars")
            self.assertEqual(config.user_name, "zmoratto")
            self.assertEqual(config.point_id_prefix, "CTX")
            self.assertEqual(config.pair_id, "S12")

    def test_read_controlnet_config_normalizes_blank_pair_id_to_none(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config_blank_pair_id.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "ctx",
                        "TargetName": "Mars",
                        "UserName": "zmoratto",
                        "PointIdPrefix": "CTX",
                        "PairId": "   ",
                    }
                ),
                encoding="utf-8",
            )

            config = read_controlnet_config(config_path)

            self.assertIsNone(config.pair_id)

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
            self.assertEqual(loaded.get_point(0).get_id(), "CTX00000001")
            self.assertEqual(result["point_id_namespace"], "CTX")
            self.assertEqual(result["point_id_example"], "CTX00000001")

    def test_build_controlnet_for_stereo_pair_includes_pair_id_namespace(self):
        left_key_file = KeypointFile(128, 128, (Keypoint(10.0, 20.0),))
        right_key_file = KeypointFile(128, 128, (Keypoint(12.0, 22.0),))
        config = ControlNetConfig(
            network_id="ctx_pair",
            target_name="Mars",
            user_name="zmoratto",
            description="pair-id namespace test",
            point_id_prefix="CTX",
            pair_id="S2",
        )

        with temporary_directory() as temp_dir:
            left_key_path = temp_dir / "ori_A.key"
            right_key_path = temp_dir / "ori_B.key"
            output_net = temp_dir / "stereo_pair_namespaced.net"

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

            loaded = ip.ControlNet(str(output_net))

        self.assertEqual(loaded.get_point(0).get_id(), "CTX_S2_00000001")
        self.assertEqual(result["pair_id"], "S2")
        self.assertEqual(result["point_id_namespace"], "CTX_S2_")
        self.assertEqual(result["point_id_example"], "CTX_S2_00000001")

    def test_build_controlnet_for_stereo_pair_different_pair_ids_avoid_collisions(self):
        left_key_file = KeypointFile(64, 64, (Keypoint(10.0, 20.0),))
        right_key_file = KeypointFile(64, 64, (Keypoint(12.0, 22.0),))
        config_s1 = ControlNetConfig(
            network_id="ctx_pair_s1",
            target_name="Mars",
            user_name="zmoratto",
            point_id_prefix="CTX",
            pair_id="S1",
        )
        config_s2 = ControlNetConfig(
            network_id="ctx_pair_s2",
            target_name="Mars",
            user_name="zmoratto",
            point_id_prefix="CTX",
            pair_id="S2",
        )

        with temporary_directory() as temp_dir:
            left_key_path = temp_dir / "ori_A.key"
            right_key_path = temp_dir / "ori_B.key"
            output_net_s1 = temp_dir / "pair_s1.net"
            output_net_s2 = temp_dir / "pair_s2.net"

            write_key_file(left_key_path, left_key_file)
            write_key_file(right_key_path, right_key_file)

            build_controlnet_for_stereo_pair(
                left_key_path,
                right_key_path,
                LEFT_CUBE_PATH,
                RIGHT_CUBE_PATH,
                config_s1,
                output_net_s1,
                pvl_format=True,
            )
            build_controlnet_for_stereo_pair(
                left_key_path,
                right_key_path,
                LEFT_CUBE_PATH,
                RIGHT_CUBE_PATH,
                config_s2,
                output_net_s2,
                pvl_format=True,
            )

            point_id_s1 = ip.ControlNet(str(output_net_s1)).get_point(0).get_id()
            point_id_s2 = ip.ControlNet(str(output_net_s2)).get_point(0).get_id()

        self.assertNotEqual(point_id_s1, point_id_s2)
        self.assertEqual(point_id_s1, "CTX_S1_00000001")
        self.assertEqual(point_id_s2, "CTX_S2_00000001")

    def test_controlnet_stereopair_cli_pair_id_overrides_config_value(self):
        fake_result = {
            "output_path": "synthetic.net",
            "point_count": 1,
            "measure_count": 2,
            "point_id_example": "CTX_CLI_00000001",
        }

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "ctx",
                        "TargetName": "Mars",
                        "UserName": "zmoratto",
                        "PointIdPrefix": "CTX",
                        "PairId": "CFG",
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                    return_value=fake_result,
                ) as build_mock,
                redirect_stdout(stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-ori",
                        "left.key",
                        "right.key",
                        str(LEFT_CUBE_PATH),
                        str(RIGHT_CUBE_PATH),
                        str(config_path),
                        "synthetic.net",
                        "--pair-id",
                        "CLI",
                    ]
                )

        called_config = build_mock.call_args.args[4]
        self.assertEqual(called_config.point_id_prefix, "CTX")
        self.assertEqual(called_config.pair_id, "CLI")
        self.assertEqual(json.loads(stdout.getvalue()), fake_result)

    def test_build_controlnets_for_dom_overlap_list_auto_assigns_batch_pair_ids(self):
        config = ControlNetConfig(
            network_id="ctx_batch",
            target_name="Mars",
            user_name="zmoratto",
            point_id_prefix="CTX",
            pair_id="CFG_SINGLE",
        )
        fake_pair_result = {
            "mode": "from-dom",
            "merge": {"unique_count": 5, "applied": True},
            "ransac": {"retained_count": 5, "dropped_count": 0},
            "left_conversion": {"output_count": 5},
            "right_conversion": {"output_count": 5},
            "controlnet": {"point_count": 5, "measure_count": 10},
        }

        with temporary_directory() as temp_dir:
            overlap_list_path = temp_dir / "images_overlap.lis"
            overlap_list_path.write_text(
                "left1.cub,right1.cub\nleft2.cub,right2.cub\n",
                encoding="utf-8",
            )
            original_list_path = temp_dir / "original_images.lis"
            original_list_path.write_text(
                "left1.cub\nright1.cub\nleft2.cub\nright2.cub\n",
                encoding="utf-8",
            )
            dom_list_path = temp_dir / "doms.lis"
            dom_list_path.write_text(
                "left1_dom.cub\nright1_dom.cub\nleft2_dom.cub\nright2_dom.cub\n",
                encoding="utf-8",
            )
            dom_key_dir = temp_dir / "dom_keys"
            dom_key_dir.mkdir()
            output_dir = temp_dir / "pair_nets"
            report_dir = temp_dir / "reports"
            for filename in (
                "left1__right1_A.key",
                "left1__right1_B.key",
                "left2__right2_A.key",
                "left2__right2_B.key",
            ):
                (dom_key_dir / filename).write_text("synthetic\n", encoding="utf-8")

            with patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                return_value=fake_pair_result,
            ) as build_mock:
                summary = build_controlnets_for_dom_overlap_list(
                    overlap_list_path,
                    original_list_path,
                    dom_list_path,
                    dom_key_dir,
                    output_dir,
                    config,
                    report_directory=report_dir,
                    pair_id_prefix="S",
                    pair_id_start=1,
                )

                self.assertEqual(build_mock.call_count, 2)
                first_config = build_mock.call_args_list[0].args[6]
                second_config = build_mock.call_args_list[1].args[6]
                self.assertEqual(first_config.pair_id, "S1")
                self.assertEqual(second_config.pair_id, "S2")
                self.assertEqual(first_config.point_id_prefix, "CTX")
                self.assertEqual(summary["pair_count"], 2)
                self.assertEqual(summary["pairs"][0]["pair_id"], "S1")
                self.assertEqual(summary["pairs"][1]["pair_id"], "S2")
                self.assertTrue(Path(summary["batch_report_path"]).exists())
                self.assertTrue(Path(summary["pairs"][0]["report_path"]).exists())
                self.assertTrue(Path(summary["pairs"][1]["report_path"]).exists())

    def test_controlnet_stereopair_cli_from_dom_batch_dispatches(self):
        fake_summary = {
            "mode": "from-dom-batch",
            "pair_count": 2,
            "pairs": [{"pair": "left1.cub,right1.cub", "pair_id": "S3"}],
            "batch_report_path": "reports/controlnet_batch_summary.json",
        }

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "ctx",
                        "TargetName": "Mars",
                        "UserName": "zmoratto",
                        "PointIdPrefix": "CTX",
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnets_for_dom_overlap_list",
                    return_value=fake_summary,
                ) as batch_mock,
                redirect_stdout(stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-dom-batch",
                        "images_overlap.lis",
                        "original_images.lis",
                        "doms.lis",
                        "dom_keys",
                        str(config_path),
                        "pair_nets",
                        "--pair-id-prefix",
                        "S",
                        "--pair-id-start",
                        "3",
                        "--report-dir",
                        "reports",
                    ]
                )

        called_config = batch_mock.call_args.args[5]
        self.assertEqual(called_config.point_id_prefix, "CTX")
        self.assertEqual(batch_mock.call_args.kwargs["pair_id_prefix"], "S")
        self.assertEqual(batch_mock.call_args.kwargs["pair_id_start"], 3)
        self.assertEqual(batch_mock.call_args.kwargs["report_directory"], "reports")
        self.assertEqual(json.loads(stdout.getvalue()), fake_summary)

    def test_write_controlnet_result_report_uses_default_summary_sidecar_name(self):
        result = {
            "pair": f"{LEFT_CUBE_PATH},{RIGHT_CUBE_PATH}",
            "controlnet": {"point_count": 4},
            "merge": {"unique_count": 5},
        }

        with temporary_directory() as temp_dir:
            output_net = temp_dir / "synthetic_pair.net"
            expected_report_path = default_controlnet_report_path(output_net)
            report_path = write_controlnet_result_report(result, output_net)
            report_payload = json.loads(Path(report_path).read_text(encoding="utf-8"))

        self.assertEqual(report_path, str(expected_report_path))
        self.assertEqual(report_payload["controlnet"]["point_count"], 4)
        self.assertTrue(report_path.endswith("synthetic_pair.summary.json"))
        self.assertIn("coordinate_conventions", report_payload)
        self.assertEqual(report_payload["coordinate_conventions"]["context"], "controlnet_pair_result")
        self.assertIn(
            "1-based",
            report_payload["coordinate_conventions"]["field_bases"]["left_conversion.failures[].sample"],
        )

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
        self.assertIn("coordinate_conventions", logged)
        self.assertEqual(logged["coordinate_conventions"]["context"], "dom2ori_failure_log")
        self.assertIn("1-based", logged["coordinate_conventions"]["field_bases"]["failures[].sample"])
        self.assertIn("1-based", logged["coordinate_conventions"]["field_bases"]["failures[].projected_sample"])

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

    def test_convert_paired_dom_key_files_via_ground_functions_drops_unpaired_successes(self):
        input_key_file = KeypointFile(
            20,
            20,
            (
                Keypoint(5.0, 5.0),
                Keypoint(7.0, 7.0),
            ),
        )

        def ground_lookup(sample, line):
            return sample + 100.0, line + 200.0

        def left_project(latitude, longitude):
            return latitude - 100.0, longitude - 200.0

        def right_project(latitude, longitude):
            sample = latitude - 100.0
            line = longitude - 200.0
            if sample == 5.0:
                return None
            return sample, line

        with temporary_directory() as temp_dir:
            left_input_key_path = temp_dir / "left_dom.key"
            right_input_key_path = temp_dir / "right_dom.key"
            left_output_key_path = temp_dir / "left_ori.key"
            right_output_key_path = temp_dir / "right_ori.key"
            write_key_file(left_input_key_path, input_key_file)
            write_key_file(right_input_key_path, input_key_file)

            result = convert_paired_dom_key_files_via_ground_functions(
                left_input_key_path,
                right_input_key_path,
                left_output_key_path,
                right_output_key_path,
                left_ground_lookup=ground_lookup,
                left_image_project=left_project,
                right_ground_lookup=ground_lookup,
                right_image_project=right_project,
                left_output_width=20,
                left_output_height=20,
                right_output_width=20,
                right_output_height=20,
            )
            left_converted = read_key_file(left_output_key_path)
            right_converted = read_key_file(right_output_key_path)

        self.assertEqual(result["retained_pair_count"], 1)
        self.assertEqual(result["left_conversion"]["output_count"], 1)
        self.assertEqual(result["right_conversion"]["output_count"], 1)
        self.assertEqual(left_converted.points, (Keypoint(7.0, 7.0),))
        self.assertEqual(right_converted.points, (Keypoint(7.0, 7.0),))
        self.assertEqual(result["left_conversion"]["failure_reasons"]["paired_point_dropped"], 1)
        self.assertEqual(result["right_conversion"]["failure_reasons"]["original_projection_failed"], 1)

    def test_build_controlnet_for_dom_stereo_pair_uses_paired_dom2ori_conversion(self):
        config = ControlNetConfig(
            network_id="ctx_dom_patch",
            target_name="Mars",
            user_name="zmoratto",
            description="paired dom2ori wrapper test",
            point_id_prefix="DPT",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            output_net = temp_dir / "paired_wrapper.net"
            write_key_file(left_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))
            write_key_file(right_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))

            fake_pair_result = {
                "left_conversion": {"output_count": 1, "failure_count": 0},
                "right_conversion": {"output_count": 1, "failure_count": 0},
                "retained_pair_count": 1,
            }
            fake_controlnet_result = {
                "output_path": str(output_net),
                "network_id": config.network_id,
                "target_name": config.target_name,
                "user_name": config.user_name,
                "point_count": 1,
                "measure_count": 2,
                "left_serial_number": "left-serial",
                "right_serial_number": "right-serial",
                "pvl_format": True,
            }

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original",
                    return_value=fake_pair_result,
                ) as paired_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                    return_value=fake_controlnet_result,
                ) as controlnet_mock,
            ):
                result = build_controlnet_for_dom_stereo_pair(
                    left_dom_key,
                    right_dom_key,
                    REAL_DOM_LEFT,
                    REAL_DOM_RIGHT,
                    LEFT_CUBE_PATH,
                    RIGHT_CUBE_PATH,
                    config,
                    output_net,
                    skip_merge=True,
                )

        paired_mock.assert_called_once()
        controlnet_mock.assert_called_once()
        self.assertEqual(result["left_conversion"]["output_count"], 1)
        self.assertEqual(result["right_conversion"]["output_count"], 1)
        self.assertEqual(result["controlnet"]["point_count"], 1)

    def test_build_controlnet_for_dom_stereo_pair_applies_ransac_and_optional_visualization_after_merge(self):
        config = ControlNetConfig(
            network_id="ctx_dom_ransac",
            target_name="Mars",
            user_name="zmoratto",
            description="dom ransac wrapper test",
            point_id_prefix="RSC",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            output_net = temp_dir / "ransac_wrapper.net"
            visualization_output_path = temp_dir / "post_ransac_match.png"
            write_key_file(left_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))
            write_key_file(right_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))

            fake_pair_result = {
                "left_conversion": {"output_count": 1, "failure_count": 0},
                "right_conversion": {"output_count": 1, "failure_count": 0},
                "retained_pair_count": 1,
            }
            fake_controlnet_result = {
                "output_path": str(output_net),
                "network_id": config.network_id,
                "target_name": config.target_name,
                "user_name": config.user_name,
                "point_count": 1,
                "measure_count": 2,
                "left_serial_number": "left-serial",
                "right_serial_number": "right-serial",
                "pvl_format": True,
            }
            fake_ransac_result = {
                "applied": True,
                "status": "filtered",
                "mode": "loose",
                "input_count": 2,
                "retained_count": 1,
                "dropped_count": 1,
                "retained_soft_outlier_positions": [0],
            }
            fake_visualization = {
                "output_path": str(temp_dir / "left__right__20260418T184432.png"),
                "point_count": 1,
                "scale_factor": 3.0,
                "highlighted_match_count": 1,
            }

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.filter_stereo_pair_key_files_with_ransac",
                    return_value=fake_ransac_result,
                ) as ransac_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.write_stereo_pair_match_visualization_from_key_files",
                    return_value=fake_visualization,
                ) as visualization_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original",
                    return_value=fake_pair_result,
                ) as paired_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                    return_value=fake_controlnet_result,
                ) as controlnet_mock,
            ):
                result = build_controlnet_for_dom_stereo_pair(
                    left_dom_key,
                    right_dom_key,
                    REAL_DOM_LEFT,
                    REAL_DOM_RIGHT,
                    LEFT_CUBE_PATH,
                    RIGHT_CUBE_PATH,
                    config,
                    output_net,
                    skip_merge=True,
                    write_match_visualization=True,
                    match_visualization_output_path=visualization_output_path,
                    match_visualization_scale=3.0,
                    ransac_mode="loose",
                    loose_ransac_keep_threshold=1.0,
                )

        ransac_mock.assert_called_once()
        visualization_mock.assert_called_once()
        self.assertEqual(visualization_mock.call_args.kwargs["output_path"], visualization_output_path)
        paired_mock.assert_called_once()
        controlnet_mock.assert_called_once()
        self.assertEqual(result["ransac"]["retained_count"], 1)
        self.assertEqual(result["match_visualization"]["highlighted_match_count"], 1)
        self.assertEqual(result["controlnet"]["point_count"], 1)

    def test_dom2ori_cli_paired_mode_dispatches_to_paired_conversion(self):
        fake_result = {
            "left_conversion": {"output_count": 2, "failure_count": 0},
            "right_conversion": {"output_count": 2, "failure_count": 0},
            "retained_pair_count": 2,
        }

        stdout = io.StringIO()
        with (
            patch(
                "controlnet_construct.dom2ori.convert_paired_dom_keypoints_to_original",
                return_value=fake_result,
            ) as paired_mock,
            redirect_stdout(stdout),
        ):
            dom2ori_main(
                [
                    "paired",
                    "left_dom.key",
                    "right_dom.key",
                    "left_dom.cub",
                    "right_dom.cub",
                    "left_original.cub",
                    "right_original.cub",
                    "left_ori.key",
                    "right_ori.key",
                    "--dom-band",
                    "2",
                    "--left-original-band",
                    "3",
                    "--right-original-band",
                    "4",
                    "--left-failure-log",
                    "left_failures.json",
                    "--right-failure-log",
                    "right_failures.json",
                ]
            )

        paired_mock.assert_called_once_with(
            "left_dom.key",
            "right_dom.key",
            "left_dom.cub",
            "right_dom.cub",
            "left_original.cub",
            "right_original.cub",
            "left_ori.key",
            "right_ori.key",
            dom_band=2,
            left_original_band=3,
            right_original_band=4,
            left_failure_log_path="left_failures.json",
            right_failure_log_path="right_failures.json",
            logger=paired_mock.call_args.kwargs["logger"],
        )
        self.assertEqual(json.loads(stdout.getvalue()), fake_result)

    def test_dom2ori_cli_legacy_single_mode_stays_backward_compatible(self):
        fake_result = {"output_count": 1, "failure_count": 0}

        stdout = io.StringIO()
        with (
            patch(
                "controlnet_construct.dom2ori.convert_dom_keypoints_to_original",
                return_value=fake_result,
            ) as single_mock,
            redirect_stdout(stdout),
        ):
            dom2ori_main(
                [
                    "dom.key",
                    "dom.cub",
                    "original.cub",
                    "ori.key",
                    "--dom-band",
                    "2",
                    "--original-band",
                    "5",
                    "--failure-log",
                    "failures.json",
                ]
            )

        single_mock.assert_called_once_with(
            "dom.key",
            "dom.cub",
            "original.cub",
            "ori.key",
            dom_band=2,
            original_band=5,
            failure_log_path="failures.json",
            logger=single_mock.call_args.kwargs["logger"],
        )
        self.assertEqual(json.loads(stdout.getvalue()), fake_result)

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

    def test_build_controlnet_for_dom_stereo_pair_supports_configurable_real_lro_pair_when_available(self):
        real_left_dom, real_right_dom = _configured_real_lro_dom_pair()
        if not real_left_dom.exists() or not real_right_dom.exists():
            self.skipTest(
                "Real LRO DOM pair is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} and {REAL_LRO_DOM_RIGHT_ENV} if needed."
            )

        config = ControlNetConfig(
            network_id="ctx_dom_real_lro",
            target_name="Moon",
            user_name="copilot",
            description="configurable real LRO DOM wrapper test",
            point_id_prefix="LRD",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_real_dom.key"
            right_dom_key = temp_dir / "right_real_dom.key"
            output_net = temp_dir / "real_lro_wrapped.net"
            left_output_key = temp_dir / "left_real_ori.key"
            right_output_key = temp_dir / "right_real_ori.key"

            match_summary = match_dom_pair_to_key_files(
                real_left_dom,
                real_right_dom,
                left_dom_key,
                right_dom_key,
                min_valid_pixels=16,
                ratio_test=0.85,
            )
            self.assertGreater(match_summary["point_count"], 0)

            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                real_left_dom,
                real_right_dom,
                real_left_dom,
                real_right_dom,
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
        self.assertGreater(result["controlnet"]["point_count"], 0)
        self.assertEqual(result["left_conversion"]["failure_count"], 0)
        self.assertEqual(result["right_conversion"]["failure_count"], 0)
        self.assertTrue(left_output_exists)
        self.assertTrue(right_output_exists)
        self.assertEqual(loaded.get_num_points(), result["controlnet"]["point_count"])

    def test_image_match_to_dom2ori_to_controlnet_chain_preserves_measure_coordinates_without_drift(self):
        config = ControlNetConfig(
            network_id="ctx_chain",
            target_name="Mars",
            user_name="zmoratto",
            description="coordinate drift guard",
            point_id_prefix="DRF",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            metadata_output = temp_dir / "pair_preparation.json"
            left_ori_key = temp_dir / "left_ori.key"
            right_ori_key = temp_dir / "right_ori.key"
            left_failure_log = temp_dir / "left_failures.json"
            right_failure_log = temp_dir / "right_failures.json"
            output_net = temp_dir / "chain.net"

            match_summary = match_dom_pair_to_key_files(
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                left_dom_key,
                right_dom_key,
                metadata_output=metadata_output,
                min_valid_pixels=16,
                ratio_test=0.85,
            )
            self.assertGreater(match_summary["point_count"], 0)

            metadata_payload = json.loads(metadata_output.read_text(encoding="utf-8"))
            self.assertIn("coordinate_conventions", metadata_payload)
            self.assertIn("0-based", metadata_payload["coordinate_conventions"]["field_bases"]["left.offset_sample"])
            self.assertIn("1-based", metadata_payload["coordinate_conventions"]["field_bases"]["left.start_sample"])

            left_dom_points = read_key_file(left_dom_key)
            right_dom_points = read_key_file(right_dom_key)

            left_conversion = convert_dom_keypoints_to_original(
                left_dom_key,
                REAL_DOM_LEFT,
                REAL_DOM_LEFT,
                left_ori_key,
                failure_log_path=left_failure_log,
            )
            right_conversion = convert_dom_keypoints_to_original(
                right_dom_key,
                REAL_DOM_RIGHT,
                REAL_DOM_RIGHT,
                right_ori_key,
                failure_log_path=right_failure_log,
            )

            self.assertEqual(left_conversion["failure_count"], 0)
            self.assertEqual(right_conversion["failure_count"], 0)
            self.assertEqual(left_conversion["output_count"], match_summary["point_count"])
            self.assertEqual(right_conversion["output_count"], match_summary["point_count"])

            left_ori_points = read_key_file(left_ori_key)
            right_ori_points = read_key_file(right_ori_key)
            self.assertEqual(len(left_dom_points.points), len(left_ori_points.points))
            self.assertEqual(len(right_dom_points.points), len(right_ori_points.points))

            for expected, actual in zip(left_dom_points.points, left_ori_points.points, strict=True):
                self.assertAlmostEqual(actual.sample, expected.sample, places=3)
                self.assertAlmostEqual(actual.line, expected.line, places=3)
            for expected, actual in zip(right_dom_points.points, right_ori_points.points, strict=True):
                self.assertAlmostEqual(actual.sample, expected.sample, places=3)
                self.assertAlmostEqual(actual.line, expected.line, places=3)

            controlnet_summary = build_controlnet_for_stereo_pair(
                left_ori_key,
                right_ori_key,
                REAL_DOM_LEFT,
                REAL_DOM_RIGHT,
                config,
                output_net,
                pvl_format=True,
            )

            loaded = ip.ControlNet(str(output_net))
            self.assertEqual(loaded.get_num_points(), len(left_ori_points.points))
            self.assertEqual(controlnet_summary["point_count"], len(left_ori_points.points))

            for index, (left_expected, right_expected) in enumerate(
                zip(left_ori_points.points, right_ori_points.points, strict=True)
            ):
                point = loaded.get_point(index)
                self.assertEqual(point.get_num_measures(), 2)
                left_measure = point.get_measure(0)
                right_measure = point.get_measure(1)
                self.assertAlmostEqual(left_measure.get_sample(), left_expected.sample, places=3)
                self.assertAlmostEqual(left_measure.get_line(), left_expected.line, places=3)
                self.assertAlmostEqual(right_measure.get_sample(), right_expected.sample, places=3)
                self.assertAlmostEqual(right_measure.get_line(), right_expected.line, places=3)

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