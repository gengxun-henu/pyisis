"""Focused unit tests for the next-stage DOM matching ControlNet pipeline helpers.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-05-04
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
Updated: 2026-04-22  Geng Xun added regression coverage for the optional post-cnetmerge merge_control_measure pipeline step and preserved the default four-step timing sequence.
Updated: 2026-04-22  Geng Xun added regression coverage for default post-RANSAC pipeline visualizations and batch-script forwarding of the new CPU parallel tile-matching flag.
Updated: 2026-04-22  Geng Xun added regression coverage for forwarding configurable CPU process-pool worker limits through the example batch and pipeline wrappers.
Updated: 2026-04-22  Geng Xun added regression coverage for reading ImageMatch.num_worker_parallel_cpu from config JSON while preserving CLI override precedence.
Updated: 2026-04-22  Geng Xun updated example pipeline regressions to assert kebab-case CLI forwarding after removing legacy underscore spellings.
Updated: 2026-04-23  Geng Xun added regression coverage for forwarding invalid-pixel-radius and low-resolution coarse-registration options through the example wrappers.
Updated: 2026-05-01  Geng Xun updated batch-wrapper fake dispatchers to serve config-default helper lookups through image_match.py.
Updated: 2026-05-01  Geng Xun added batch-wrapper regression coverage for legacy top-level config precedence while preserving explicit CLI overrides.
Updated: 2026-05-01  Geng Xun refactored pipeline-wrapper helper-mode regressions to preserve legacy config precedence while reusing image_match.py config-default probes.
Updated: 2026-05-02  Geng Xun added regression coverage for reusable low-resolution DOM list preparation and forwarding.
Updated: 2026-05-03  Geng Xun added regression coverage for forwarding post-RANSAC visualization preview options into match visualization.
Updated: 2026-05-03  Geng Xun added regression coverage for forwarding post-RANSAC visualization preview defaults from the pipeline wrapper.
Updated: 2026-05-04  Geng Xun added pipeline and CLI forwarding coverage for reduced visualization preview options and aligned CLI default preview scale expectations.
Updated: 2026-05-04  Geng Xun added CLI coverage for the remaining reduced visualization preview flags.
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
RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_image_match_batch_example.sh"


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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
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
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
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
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
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
        self.assertIn("post-RANSAC match viz:", completed.stdout)
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
                            "num_worker_parallel_cpu": 8,
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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--valid-pixel-percent-threshold" not in args:
                                raise SystemExit("missing valid pixel threshold")
                            threshold = args[args.index("--valid-pixel-percent-threshold") + 1]
                            if threshold != "0.05":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing worker limit")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "8":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
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
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
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

    def test_run_image_match_batch_example_forwards_default_parallel_flag_and_pre_ransac_viz_dir(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    f"""
                    #!{sys.executable}
                    import json
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

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--use-parallel-cpu" not in args:
                                raise SystemExit("missing --use-parallel-cpu forwarding")
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing --num-worker-parallel-cpu forwarding")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "8":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} \"{fake_python_dispatcher}\" "$@"
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--python",
                    str(fake_python),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("CPU parallel tile matching: enabled", completed.stdout)
        self.assertIn("CPU parallel worker limit: 8", completed.stdout)

    def test_run_image_match_batch_example_reads_parallel_worker_limit_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "ImageMatch": {
                            "valid_pixel_percent_threshold": 0.05,
                            "num_worker_parallel_cpu": 6,
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

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing --num-worker-parallel-cpu forwarding")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "6":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} \"{fake_python_dispatcher}\" "$@"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("CPU parallel worker limit: 6", completed.stdout)

    def test_run_image_match_batch_example_preserves_legacy_top_level_precedence_for_duplicate_config_keys(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "valid_pixel_percent_threshold": 0.11,
                        "num_worker_parallel_cpu": 9,
                        "invalid_pixel_radius": 7,
                        "matcher_method": "flann",
                        "use_parallel_cpu": False,
                        "ImageMatch": {
                            "valid_pixel_percent_threshold": 0.02,
                            "num_worker_parallel_cpu": 4,
                            "invalid_pixel_radius": 2,
                            "matcher_method": "bf",
                            "use_parallel_cpu": True,
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
                    import sys
                    from pathlib import Path

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)

                    def _config_containers(payload: dict[str, object], order: str) -> list[dict[str, object]]:
                        image_match_containers = []
                        for key in ("ImageMatch", "image_match", "imageMatch"):
                            value = payload.get(key)
                            if isinstance(value, dict):
                                image_match_containers.append(value)
                        if order == "top-level-first":
                            return [payload, *image_match_containers]
                        return [*image_match_containers, payload]

                    def _lookup_config_default(payload: dict[str, object], field_name: str, order: str) -> str:
                        candidate_keys = {{
                            "valid_pixel_percent_threshold": (
                                "valid_pixel_percent_threshold",
                                "validPixelPercentThreshold",
                                "ValidPixelPercentThreshold",
                            ),
                            "num_worker_parallel_cpu": (
                                "num_worker_parallel_cpu",
                                "numWorkerParallelCpu",
                                "NumWorkerParallelCpu",
                            ),
                            "invalid_pixel_radius": (
                                "invalid_pixel_radius",
                                "invalidPixelRadius",
                                "InvalidPixelRadius",
                            ),
                            "matcher_method": (
                                "matcher_method",
                                "matcherMethod",
                                "MatcherMethod",
                            ),
                            "enable_low_resolution_offset_estimation": (
                                "enable_low_resolution_offset_estimation",
                                "enableLowResolutionOffsetEstimation",
                                "EnableLowResolutionOffsetEstimation",
                            ),
                            "low_resolution_level": (
                                "low_resolution_level",
                                "lowResolutionLevel",
                                "LowResolutionLevel",
                            ),
                            "low_resolution_max_mean_reprojection_error_pixels": (
                                "low_resolution_max_mean_reprojection_error_pixels",
                                "lowResolutionMaxMeanReprojectionErrorPixels",
                                "LowResolutionMaxMeanReprojectionErrorPixels",
                            ),
                            "low_resolution_min_retained_match_count": (
                                "low_resolution_min_retained_match_count",
                                "lowResolutionMinRetainedMatchCount",
                                "LowResolutionMinRetainedMatchCount",
                            ),
                            "low_resolution_max_mean_projected_offset_meters": (
                                "low_resolution_max_mean_projected_offset_meters",
                                "lowResolutionMaxMeanProjectedOffsetMeters",
                                "LowResolutionMaxMeanProjectedOffsetMeters",
                            ),
                            "visualization_mode": (
                                "visualization_mode",
                                "visualizationMode",
                                "VisualizationMode",
                            ),
                            "memory_profile": (
                                "memory_profile",
                                "memoryProfile",
                                "MemoryProfile",
                            ),
                            "visualization_target_long_edge": (
                                "visualization_target_long_edge",
                                "visualizationTargetLongEdge",
                                "VisualizationTargetLongEdge",
                            ),
                            "preview_crop_margin_pixels": (
                                "preview_crop_margin_pixels",
                                "previewCropMarginPixels",
                                "PreviewCropMarginPixels",
                            ),
                            "preview_cache_source": (
                                "preview_cache_source",
                                "previewCacheSource",
                                "PreviewCacheSource",
                            ),
                            "use_parallel_cpu": (
                                "use_parallel_cpu",
                                "useParallelCpu",
                                "UseParallelCpu",
                            ),
                        }}
                        for container in _config_containers(payload, order):
                            for key in candidate_keys[field_name]:
                                if key not in container:
                                    continue
                                value = container[key]
                                if value is None or value == "":
                                    continue
                                if field_name == "use_parallel_cpu":
                                    if isinstance(value, bool):
                                        return "1" if value else "0"
                                    normalized = str(value).strip().lower()
                                    if normalized in {{"1", "true", "yes", "on"}}:
                                        return "1"
                                    if normalized in {{"0", "false", "no", "off"}}:
                                        return "0"
                                    raise SystemExit(f"invalid use_parallel_cpu value: {{value!r}}")
                                return str(value)
                        return ""

                    def _write_fake_key_outputs(args: list[str]) -> None:
                        key_index = 4 if args and args[0] == "--config" else 2
                        Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                        Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                order = args[args.index("--print-config-default-container-order") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                print(_lookup_config_default(payload, field_name, order))
                                return 0
                            if "--valid-pixel-percent-threshold" not in args:
                                raise SystemExit("missing --valid-pixel-percent-threshold forwarding")
                            threshold = args[args.index("--valid-pixel-percent-threshold") + 1]
                            if threshold != "0.11":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            if "--invalid-pixel-radius" not in args:
                                raise SystemExit("missing --invalid-pixel-radius forwarding")
                            radius = args[args.index("--invalid-pixel-radius") + 1]
                            if radius != "7":
                                raise SystemExit(f"unexpected invalid pixel radius: {{radius}}")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method forwarding")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "flann":
                                raise SystemExit(f"unexpected matcher method: {{matcher_method}}")
                            if "--use-parallel-cpu" not in args:
                                raise SystemExit("missing --use-parallel-cpu forwarding")
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing --num-worker-parallel-cpu forwarding")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "3":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            _write_fake_key_outputs(args)
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--num-worker-parallel-cpu",
                    "3",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Valid pixel percent threshold: 0.11", completed.stdout)
        self.assertIn("Invalid pixel radius: 7", completed.stdout)
        self.assertIn("Matcher method: flann", completed.stdout)
        self.assertIn("CPU parallel tile matching: enabled", completed.stdout)
        self.assertIn("CPU parallel worker limit: 3", completed.stdout)

    def test_run_image_match_batch_example_reads_new_matching_options_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "ImageMatch": {
                            "invalid_pixel_radius": 2,
                            "enable_low_resolution_offset_estimation": True,
                            "low_resolution_level": 4,
                            "low_resolution_min_retained_match_count": 6,
                            "low_resolution_max_mean_projected_offset_meters": 2000.0,
                        },
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                (
                    f"#!{sys.executable}\n"
                    "import json\n"
                    "import sys\n"
                    "from pathlib import Path\n"
                    "\n"
                    "def _run_stdin_python() -> int:\n"
                    "    code = sys.stdin.read()\n"
                    "    globals_dict = {'__name__': '__main__', '__file__': '<stdin>'}\n"
                    "    sys.argv = ['-'] + sys.argv[2:]\n"
                    "    exec(compile(code, '<stdin>', 'exec'), globals_dict)\n"
                    "\n"
                    "def main() -> int:\n"
                    "    if len(sys.argv) < 2:\n"
                    "        return 0\n"
                    "    if sys.argv[1] == '-':\n"
                    "        return _run_stdin_python()\n"
                    "\n"
                    "    script_name = Path(sys.argv[1]).name\n"
                    "    args = sys.argv[2:]\n"
                    "\n"
                    "    if script_name == 'prepare_low_resolution_doms.py':\n"
                    "        if '--level' not in args:\n"
                    "            raise SystemExit('missing low-resolution prepare --level')\n"
                    "        level = args[args.index('--level') + 1]\n"
                    "        if level != '4':\n"
                    "            raise SystemExit(f'unexpected prepare level: {level}')\n"
                    "        output_list = Path(args[1])\n"
                    "        output_list.parent.mkdir(parents=True, exist_ok=True)\n"
                    "        output_list.write_text('left_low_level4.cub\\nright_low_level4.cub\\n', encoding='utf-8')\n"
                    "        return 0\n"
                    "\n"
                    "    if script_name == 'image_match.py':\n"
                    "        if '--print-config-default' in args:\n"
                    "            config_path = Path(args[args.index('--config') + 1])\n"
                    "            field_name = args[args.index('--print-config-default') + 1]\n"
                    "            payload = json.loads(config_path.read_text(encoding='utf-8'))\n"
                    "            image_match_config = payload.get('ImageMatch') or {}\n"
                    "            mapping = {\n"
                    "                'valid_pixel_percent_threshold': image_match_config.get('valid_pixel_percent_threshold', ''),\n"
                    "                'num_worker_parallel_cpu': image_match_config.get('num_worker_parallel_cpu', ''),\n"
                    "                'invalid_pixel_radius': image_match_config.get('invalid_pixel_radius', ''),\n"
                    "                'matcher_method': image_match_config.get('matcher_method', ''),\n"
                    "                'enable_low_resolution_offset_estimation': '1' if image_match_config.get('enable_low_resolution_offset_estimation') else '',\n"
                    "                'low_resolution_level': image_match_config.get('low_resolution_level', ''),\n"
                    "                'low_resolution_max_mean_reprojection_error_pixels': image_match_config.get('low_resolution_max_mean_reprojection_error_pixels', ''),\n"
                    "                'low_resolution_min_retained_match_count': image_match_config.get('low_resolution_min_retained_match_count', ''),\n"
                    "                'low_resolution_max_mean_projected_offset_meters': image_match_config.get('low_resolution_max_mean_projected_offset_meters', ''),\n"
                    "                'use_parallel_cpu': '1' if image_match_config.get('use_parallel_cpu') is True else ('0' if image_match_config.get('use_parallel_cpu') is False else ''),\n"
                    "            }\n"
                    "            print(mapping.get(field_name, ''))\n"
                    "            return 0\n"
                    "        if '--invalid-pixel-radius' not in args:\n"
                    "            raise SystemExit('missing --invalid-pixel-radius forwarding')\n"
                    "        radius = args[args.index('--invalid-pixel-radius') + 1]\n"
                    "        if radius != '2':\n"
                    "            raise SystemExit(f'unexpected invalid pixel radius: {radius}')\n"
                    "        if '--enable-low-resolution-offset-estimation' not in args:\n"
                    "            raise SystemExit('missing low-resolution enable flag')\n"
                    "        if '--low-resolution-level' not in args:\n"
                    "            raise SystemExit('missing --low-resolution-level')\n"
                    "        level = args[args.index('--low-resolution-level') + 1]\n"
                    "        if level != '4':\n"
                    "            raise SystemExit(f'unexpected low-resolution level: {level}')\n"
                    "        if '--low-resolution-min-retained-match-count' not in args:\n"
                    "            raise SystemExit('missing --low-resolution-min-retained-match-count')\n"
                    "        min_count = args[args.index('--low-resolution-min-retained-match-count') + 1]\n"
                    "        if min_count != '6':\n"
                    "            raise SystemExit(f'unexpected low-resolution min retained match count: {min_count}')\n"
                    "        if '--low-resolution-max-mean-projected-offset-meters' not in args:\n"
                    "            raise SystemExit('missing --low-resolution-max-mean-projected-offset-meters')\n"
                    "        max_offset = args[args.index('--low-resolution-max-mean-projected-offset-meters') + 1]\n"
                    "        if max_offset != '2000.0':\n"
                    "            raise SystemExit(f'unexpected low-resolution max mean projected offset meters: {max_offset}')\n"
                    "        if '--left-low-resolution-dom' not in args:\n"
                    "            raise SystemExit('missing --left-low-resolution-dom')\n"
                    "        if '--right-low-resolution-dom' not in args:\n"
                    "            raise SystemExit('missing --right-low-resolution-dom')\n"
                    "        left_low = args[args.index('--left-low-resolution-dom') + 1]\n"
                    "        right_low = args[args.index('--right-low-resolution-dom') + 1]\n"
                    "        if left_low != 'left_low_level4.cub':\n"
                    "            raise SystemExit(f'unexpected left low-resolution DOM: {left_low}')\n"
                    "        if right_low != 'right_low_level4.cub':\n"
                    "            raise SystemExit(f'unexpected right low-resolution DOM: {right_low}')\n"
                    "        Path(args[2]).write_text('synthetic-left-key\\n', encoding='utf-8')\n"
                    "        Path(args[3]).write_text('synthetic-right-key\\n', encoding='utf-8')\n"
                    "        return 0\n"
                    "\n"
                    "    raise SystemExit(f'Unhandled fake python script: {script_name}')\n"
                    "\n"
                    "raise SystemExit(main())\n"
                ),
                encoding="utf-8",
            )
            fake_python_dispatcher.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python_dispatcher),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Invalid pixel radius: 2", completed.stdout)
        self.assertIn("Low-resolution offset estimation: enabled", completed.stdout)
        self.assertIn("Low-resolution level: 4", completed.stdout)
        self.assertIn("Low-resolution minimum retained matches: 6", completed.stdout)
        self.assertIn("Low-resolution max mean projected offset (meters): 2000.0", completed.stdout)

    def test_run_pipeline_example_reads_parallel_worker_limit_from_config(self):
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
                            "num_worker_parallel_cpu": 5,
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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing worker limit")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "5":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
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
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
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
        self.assertIn("CPU parallel worker limit: 5", completed.stdout)

    def test_run_pipeline_example_preserves_legacy_top_level_precedence_for_duplicate_config_keys(self):
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
                        "valid_pixel_percent_threshold": 0.11,
                        "num_worker_parallel_cpu": 9,
                        "invalid_pixel_radius": 7,
                        "matcher_method": "flann",
                        "use_parallel_cpu": False,
                        "ImageMatch": {
                            "valid_pixel_percent_threshold": 0.02,
                            "num_worker_parallel_cpu": 4,
                            "invalid_pixel_radius": 2,
                            "matcher_method": "bf",
                            "use_parallel_cpu": True,
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

                    def _config_containers(payload: dict[str, object], order: str) -> list[dict[str, object]]:
                        image_match_containers = []
                        for key in ("ImageMatch", "image_match", "imageMatch"):
                            value = payload.get(key)
                            if isinstance(value, dict):
                                image_match_containers.append(value)
                        if order == "top-level-first":
                            return [payload, *image_match_containers]
                        return [*image_match_containers, payload]

                    def _lookup_config_default(payload: dict[str, object], field_name: str, order: str) -> str:
                        candidate_keys = {{
                            "valid_pixel_percent_threshold": (
                                "valid_pixel_percent_threshold",
                                "validPixelPercentThreshold",
                                "ValidPixelPercentThreshold",
                            ),
                            "num_worker_parallel_cpu": (
                                "num_worker_parallel_cpu",
                                "numWorkerParallelCpu",
                                "NumWorkerParallelCpu",
                            ),
                            "invalid_pixel_radius": (
                                "invalid_pixel_radius",
                                "invalidPixelRadius",
                                "InvalidPixelRadius",
                            ),
                            "matcher_method": (
                                "matcher_method",
                                "matcherMethod",
                                "MatcherMethod",
                            ),
                            "enable_low_resolution_offset_estimation": (
                                "enable_low_resolution_offset_estimation",
                                "enableLowResolutionOffsetEstimation",
                                "EnableLowResolutionOffsetEstimation",
                            ),
                            "low_resolution_level": (
                                "low_resolution_level",
                                "lowResolutionLevel",
                                "LowResolutionLevel",
                            ),
                            "low_resolution_max_mean_reprojection_error_pixels": (
                                "low_resolution_max_mean_reprojection_error_pixels",
                                "lowResolutionMaxMeanReprojectionErrorPixels",
                                "LowResolutionMaxMeanReprojectionErrorPixels",
                            ),
                            "low_resolution_min_retained_match_count": (
                                "low_resolution_min_retained_match_count",
                                "lowResolutionMinRetainedMatchCount",
                                "LowResolutionMinRetainedMatchCount",
                            ),
                            "low_resolution_max_mean_projected_offset_meters": (
                                "low_resolution_max_mean_projected_offset_meters",
                                "lowResolutionMaxMeanProjectedOffsetMeters",
                                "LowResolutionMaxMeanProjectedOffsetMeters",
                            ),
                            "visualization_mode": (
                                "visualization_mode",
                                "visualizationMode",
                                "VisualizationMode",
                            ),
                            "memory_profile": (
                                "memory_profile",
                                "memoryProfile",
                                "MemoryProfile",
                            ),
                            "visualization_target_long_edge": (
                                "visualization_target_long_edge",
                                "visualizationTargetLongEdge",
                                "VisualizationTargetLongEdge",
                            ),
                            "preview_crop_margin_pixels": (
                                "preview_crop_margin_pixels",
                                "previewCropMarginPixels",
                                "PreviewCropMarginPixels",
                            ),
                            "preview_cache_source": (
                                "preview_cache_source",
                                "previewCacheSource",
                                "PreviewCacheSource",
                            ),
                            "use_parallel_cpu": (
                                "use_parallel_cpu",
                                "useParallelCpu",
                                "UseParallelCpu",
                            ),
                        }}
                        for container in _config_containers(payload, order):
                            for key in candidate_keys[field_name]:
                                if key not in container:
                                    continue
                                value = container[key]
                                if value is None or value == "":
                                    continue
                                if field_name == "use_parallel_cpu":
                                    if isinstance(value, bool):
                                        return "1" if value else "0"
                                    normalized = str(value).strip().lower()
                                    if normalized in {{"1", "true", "yes", "on"}}:
                                        return "1"
                                    if normalized in {{"0", "false", "no", "off"}}:
                                        return "0"
                                    raise SystemExit(f"invalid use_parallel_cpu value: {{value!r}}")
                                return str(value)
                        return ""

                    def _write_fake_key_outputs(args: list[str]) -> None:
                        key_index = 4 if args and args[0] == "--config" else 2
                        Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                        Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")

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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                order = args[args.index("--print-config-default-container-order") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                print(_lookup_config_default(payload, field_name, order))
                                return 0
                            if "--valid-pixel-percent-threshold" not in args:
                                raise SystemExit("missing --valid-pixel-percent-threshold forwarding")
                            threshold = args[args.index("--valid-pixel-percent-threshold") + 1]
                            if threshold != "0.11":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            if "--invalid-pixel-radius" not in args:
                                raise SystemExit("missing --invalid-pixel-radius forwarding")
                            radius = args[args.index("--invalid-pixel-radius") + 1]
                            if radius != "7":
                                raise SystemExit(f"unexpected invalid pixel radius: {{radius}}")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method forwarding")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "flann":
                                raise SystemExit(f"unexpected matcher method: {{matcher_method}}")
                            if "--use-parallel-cpu" not in args:
                                raise SystemExit("missing --use-parallel-cpu forwarding")
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing --num-worker-parallel-cpu forwarding")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "3":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            _write_fake_key_outputs(args)
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
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
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
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
                    "--num-worker-parallel-cpu",
                    "3",
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Valid pixel percent threshold: 0.11", completed.stdout)
        self.assertIn("Invalid pixel radius: 7", completed.stdout)
        self.assertIn("Matcher method: flann", completed.stdout)
        self.assertIn("CPU parallel tile matching: enabled", completed.stdout)
        self.assertIn("CPU parallel worker limit: 3", completed.stdout)

    def test_run_pipeline_example_forwards_new_matching_options_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"

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
                            "invalid_pixel_radius": 3,
                            "enable_low_resolution_offset_estimation": True,
                            "low_resolution_level": 5,
                            "low_resolution_min_retained_match_count": 6,
                            "low_resolution_max_mean_projected_offset_meters": 2000.0,
                            "visualization_mode": "auto",
                            "memory_profile": "low-memory",
                            "visualization_target_long_edge": 1024,
                            "preview_crop_margin_pixels": 128,
                            "preview_cache_source": "auto",
                        },
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                "\n".join(
                    [
                        f"#!{sys.executable}",
                        "import json",
                        "import os",
                        "import sys",
                        "from pathlib import Path",
                        "",
                        "def _run_stdin_python() -> int:",
                        "    code = sys.stdin.read()",
                        "    globals_dict = {'__name__': '__main__', '__file__': '<stdin>'}",
                        "    sys.argv = ['-'] + sys.argv[2:]",
                        "    exec(compile(code, '<stdin>', 'exec'), globals_dict)",
                        "",
                        "def main() -> int:",
                        "    if len(sys.argv) < 2:",
                        "        return 0",
                        "    if sys.argv[1] == '-':",
                        "        return _run_stdin_python()",
                        "",
                        "    script_name = Path(sys.argv[1]).name",
                        "    args = sys.argv[2:]",
                        "",
                        "    if script_name == 'prepare_low_resolution_doms.py':",
                        "        if '--level' not in args:",
                        "            raise SystemExit('missing low-resolution prepare --level')",
                        "        level = args[args.index('--level') + 1]",
                        "        if level != '5':",
                        "            raise SystemExit(f'unexpected prepare level: {level}')",
                        "        output_list = Path(args[1])",
                        "        output_list.parent.mkdir(parents=True, exist_ok=True)",
                        "        output_list.write_text('left_low_level5.cub\\nright_low_level5.cub\\n', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'image_overlap.py':",
                        "        Path(args[1]).write_text('left.cub,right.cub\\n', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'image_match.py':",
                        "        if '--print-config-default' in args:",
                        "            config_path = Path(args[args.index('--config') + 1])",
                        "            field_name = args[args.index('--print-config-default') + 1]",
                        "            payload = json.loads(config_path.read_text(encoding='utf-8'))",
                        "            image_match_config = payload.get('ImageMatch') or {}",
                        "            mapping = {",
                        "                'valid_pixel_percent_threshold': image_match_config.get('valid_pixel_percent_threshold', ''),",
                        "                'num_worker_parallel_cpu': image_match_config.get('num_worker_parallel_cpu', ''),",
                        "                'invalid_pixel_radius': image_match_config.get('invalid_pixel_radius', ''),",
                        "                'matcher_method': image_match_config.get('matcher_method', ''),",
                        "                'enable_low_resolution_offset_estimation': '1' if image_match_config.get('enable_low_resolution_offset_estimation') else '',",
                        "                'low_resolution_level': image_match_config.get('low_resolution_level', ''),",
                        "                'low_resolution_max_mean_reprojection_error_pixels': image_match_config.get('low_resolution_max_mean_reprojection_error_pixels', ''),",
                        "                'low_resolution_min_retained_match_count': image_match_config.get('low_resolution_min_retained_match_count', ''),",
                        "                'low_resolution_max_mean_projected_offset_meters': image_match_config.get('low_resolution_max_mean_projected_offset_meters', ''),",
                        "                'visualization_mode': image_match_config.get('visualization_mode', ''),",
                        "                'memory_profile': image_match_config.get('memory_profile', ''),",
                        "                'visualization_target_long_edge': image_match_config.get('visualization_target_long_edge', ''),",
                        "                'preview_crop_margin_pixels': image_match_config.get('preview_crop_margin_pixels', ''),",
                        "                'preview_cache_source': image_match_config.get('preview_cache_source', ''),",
                        "                'use_parallel_cpu': '1' if image_match_config.get('use_parallel_cpu') is True else ('0' if image_match_config.get('use_parallel_cpu') is False else ''),",
                        "            }",
                        "            print(mapping.get(field_name, ''))",
                        "            return 0",
                        "        if '--invalid-pixel-radius' not in args:",
                        "            raise SystemExit('missing --invalid-pixel-radius forwarding')",
                        "        radius = args[args.index('--invalid-pixel-radius') + 1]",
                        "        if radius != '3':",
                        "            raise SystemExit(f'unexpected invalid pixel radius: {radius}')",
                        "        if '--enable-low-resolution-offset-estimation' not in args:",
                        "            raise SystemExit('missing low-resolution enable flag')",
                        "        if '--low-resolution-level' not in args:",
                        "            raise SystemExit('missing --low-resolution-level')",
                        "        level = args[args.index('--low-resolution-level') + 1]",
                        "        if level != '5':",
                        "            raise SystemExit(f'unexpected low-resolution level: {level}')",
                        "        if '--low-resolution-min-retained-match-count' not in args:",
                        "            raise SystemExit('missing --low-resolution-min-retained-match-count')",
                        "        min_count = args[args.index('--low-resolution-min-retained-match-count') + 1]",
                        "        if min_count != '6':",
                        "            raise SystemExit(f'unexpected low-resolution min retained match count: {min_count}')",
                        "        if '--low-resolution-max-mean-projected-offset-meters' not in args:",
                        "            raise SystemExit('missing --low-resolution-max-mean-projected-offset-meters')",
                        "        max_offset = args[args.index('--low-resolution-max-mean-projected-offset-meters') + 1]",
                        "        if max_offset != '2000.0':",
                        "            raise SystemExit(f'unexpected low-resolution max mean projected offset meters: {max_offset}')",
                        "        if '--left-low-resolution-dom' not in args:",
                        "            raise SystemExit('missing --left-low-resolution-dom')",
                        "        if '--right-low-resolution-dom' not in args:",
                        "            raise SystemExit('missing --right-low-resolution-dom')",
                        "        left_low = args[args.index('--left-low-resolution-dom') + 1]",
                        "        right_low = args[args.index('--right-low-resolution-dom') + 1]",
                        "        if left_low != 'left_low_level5.cub':",
                        "            raise SystemExit(f'unexpected left low-resolution DOM: {left_low}')",
                        "        if right_low != 'right_low_level5.cub':",
                        "            raise SystemExit(f'unexpected right low-resolution DOM: {right_low}')",
                        "        Path(args[2]).write_text('synthetic-left-key\\n', encoding='utf-8')",
                        "        Path(args[3]).write_text('synthetic-right-key\\n', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'controlnet_stereopair.py':",
                        "        if '--write-match-visualization' not in args:",
                        "            raise SystemExit('missing --write-match-visualization for controlnet_stereopair.py')",
                        "        if '--match-visualization-output-dir' not in args:",
                        "            raise SystemExit('missing --match-visualization-output-dir for controlnet_stereopair.py')",
                        "        if '--visualization-mode' not in args:",
                        "            raise SystemExit('missing --visualization-mode for controlnet_stereopair.py')",
                        "        visualization_mode = args[args.index('--visualization-mode') + 1]",
                        "        if visualization_mode != 'auto':",
                        "            raise SystemExit(f'unexpected visualization mode: {visualization_mode}')",
                        "        if '--memory-profile' not in args:",
                        "            raise SystemExit('missing --memory-profile for controlnet_stereopair.py')",
                        "        memory_profile = args[args.index('--memory-profile') + 1]",
                        "        if memory_profile != 'low-memory':",
                        "            raise SystemExit(f'unexpected memory profile: {memory_profile}')",
                        "        if '--visualization-target-long-edge' not in args:",
                        "            raise SystemExit('missing --visualization-target-long-edge for controlnet_stereopair.py')",
                        "        target_long_edge = args[args.index('--visualization-target-long-edge') + 1]",
                        "        if target_long_edge != '1024':",
                        "            raise SystemExit(f'unexpected visualization target long edge: {target_long_edge}')",
                        "        if '--preview-crop-margin-pixels' not in args:",
                        "            raise SystemExit('missing --preview-crop-margin-pixels for controlnet_stereopair.py')",
                        "        crop_margin = args[args.index('--preview-crop-margin-pixels') + 1]",
                        "        if crop_margin != '128':",
                        "            raise SystemExit(f'unexpected preview crop margin pixels: {crop_margin}')",
                        "        if '--preview-cache-source' not in args:",
                        "            raise SystemExit('missing --preview-cache-source for controlnet_stereopair.py')",
                        "        cache_source = args[args.index('--preview-cache-source') + 1]",
                        "        if cache_source != 'auto':",
                        "            raise SystemExit(f'unexpected preview cache source: {cache_source}')",
                        "        output_dir = Path(args[6])",
                        "        output_dir.mkdir(parents=True, exist_ok=True)",
                        "        (output_dir / 'synthetic_pair.net').write_text('net', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'controlnet_merge.py':",
                        "        merge_script_path = Path(args[3])",
                        "        merge_script_path.parent.mkdir(parents=True, exist_ok=True)",
                        "        merge_script_path.write_text('#!/usr/bin/env bash\\nexit 0\\n', encoding='utf-8')",
                        "        os.chmod(merge_script_path, 0o755)",
                        "        return 0",
                        "",
                        "    raise SystemExit(f'Unhandled fake python script: {script_name}')",
                        "",
                        "raise SystemExit(main())",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_python_dispatcher.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python_dispatcher),
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Invalid pixel radius: 3", completed.stdout)
        self.assertIn("Low-resolution offset estimation: enabled", completed.stdout)
        self.assertIn("Low-resolution level: 5", completed.stdout)

    def test_run_pipeline_example_forwards_custom_parallel_worker_limit_to_image_match(self):
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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--num-worker-parallel-cpu" not in args:
                                raise SystemExit("missing worker limit")
                            worker_limit = args[args.index("--num-worker-parallel-cpu") + 1]
                            if worker_limit != "3":
                                raise SystemExit(f"unexpected worker limit: {{worker_limit}}")
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
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
                    exec {sys.executable} \"{fake_python_dispatcher}\" "$@"
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
                    "--num-worker-parallel-cpu",
                    "3",
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("CPU parallel worker limit: 3", completed.stdout)

    def test_run_pipeline_example_optionally_runs_post_merge_control_measure(self):
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
            post_merge_output = work_dir / "merge" / "dom_matching_merged_dedup.net"

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
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                mapping = {{
                                    "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                    "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                    "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                    "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                    "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                    "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                    "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                    "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            if "--write-match-visualization" not in args:
                                raise SystemExit("missing --write-match-visualization for controlnet_stereopair.py")
                            if "--match-visualization-output-dir" not in args:
                                raise SystemExit("missing --match-visualization-output-dir for controlnet_stereopair.py")
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_merge.py":
                            merged_net_path = Path(args[2])
                            merge_script_path = Path(args[3])
                            merged_net_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.write_text(
                                "#!/usr/bin/env bash\\n"
                                f"mkdir -p {{shlex_quote(str(merged_net_path.parent))}}\\n"
                                f"printf 'merged-net\\n' > {{shlex_quote(str(merged_net_path))}}\\n",
                                encoding="utf-8",
                            )
                            os.chmod(merge_script_path, 0o755)
                            return 0

                        if script_name == "merge_control_measure.py":
                            if args[0] != {str(original_list)!r}:
                                raise SystemExit(f"unexpected original list: {{args[0]}}")
                            if args[1] != {str(work_dir / 'merge' / 'dom_matching_merged.net')!r}:
                                raise SystemExit(f"unexpected merged input: {{args[1]}}")
                            if args[2] != {str(post_merge_output)!r}:
                                raise SystemExit(f"unexpected post-merge output: {{args[2]}}")
                            if "--decimals" not in args:
                                raise SystemExit("missing --decimals for merge_control_measure.py")
                            decimals = args[args.index("--decimals") + 1]
                            if decimals != "2":
                                raise SystemExit(f"unexpected post-merge decimals: {{decimals}}")
                            output_path = Path(args[2])
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text("post-merged-net\\n", encoding="utf-8")
                            print(json.dumps({{"output_control_net": str(output_path), "point_count_after": 1}}))
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    def shlex_quote(value: str) -> str:
                        return "'" + value.replace("'", "'\\''") + "'"

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
                    "--cnetmerge",
                    "true",
                    "--post-merge-control-measure",
                    "--post-merge-output",
                    str(post_merge_output),
                    "--post-merge-decimals",
                    "2",
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
            self.assertIn("Post-merge ControlNet deduplication: enabled", completed.stdout)
            self.assertIn("START merge_control_measure", completed.stdout)
            self.assertTrue(post_merge_output.exists())
            self.assertEqual(
                [entry["name"] for entry in timing_payload["steps"]],
                ["image_overlap", "image_match_batch", "pairwise_controlnets", "merge", "merge_control_measure"],
            )

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

    def test_controlnet_stereopair_cli_from_dom_forwards_visualization_preview_options(self):
        fake_result = {
            "mode": "from-dom",
            "merge": {"unique_count": 1, "applied": True},
            "ransac": {"retained_count": 1, "dropped_count": 0},
            "left_conversion": {"output_count": 1},
            "right_conversion": {"output_count": 1},
            "controlnet": {"point_count": 1, "measure_count": 2},
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
            preview_cache_dir = temp_dir / "preview_cache"

            stdout = io.StringIO()
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                    return_value=fake_result,
                ) as build_mock,
                redirect_stdout(stdout),
            ):
                try:
                    controlnet_stereopair_main(
                        [
                            "from-dom",
                            "left_dom.key",
                            "right_dom.key",
                            "left_dom.cub",
                            "right_dom.cub",
                            "left.cub",
                            "right.cub",
                            str(config_path),
                            "output.net",
                            "--write-match-visualization",
                            "--visualization-mode",
                            "reduced",
                            "--memory-profile",
                            "low-memory",
                            "--visualization-target-long-edge",
                            "640",
                            "--max-preview-pixels",
                            "180000",
                            "--preview-crop-margin-pixels",
                            "32",
                            "--preview-cache-dir",
                            str(preview_cache_dir),
                            "--preview-cache-source",
                            "visualization-cache",
                            "--preview-level",
                            "3",
                            "--preview-force-regenerate",
                        ]
                    )
                except SystemExit as exc:
                    self.fail(f"CLI rejected visualization preview options: {exc}")

        call_kwargs = build_mock.call_args.kwargs
        self.assertTrue(call_kwargs["write_match_visualization"])
        self.assertAlmostEqual(call_kwargs["match_visualization_scale"], 1.0 / 3.0)
        self.assertEqual(call_kwargs["visualization_mode"], "reduced")
        self.assertEqual(call_kwargs["memory_profile"], "low-memory")
        self.assertEqual(call_kwargs["visualization_target_long_edge"], 640)
        self.assertEqual(call_kwargs["max_preview_pixels"], 180000)
        self.assertEqual(call_kwargs["preview_crop_margin_pixels"], 32)
        self.assertEqual(call_kwargs["preview_cache_dir"], str(preview_cache_dir))
        self.assertEqual(call_kwargs["preview_cache_source"], "visualization_cache")
        self.assertEqual(call_kwargs["preview_level"], 3)
        self.assertTrue(call_kwargs["preview_force_regenerate"])
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

    def test_build_controlnets_for_dom_overlap_list_forwards_visualization_preview_options(self):
        config = ControlNetConfig(
            network_id="ctx_batch_preview",
            target_name="Mars",
            user_name="zmoratto",
            point_id_prefix="CTX",
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
            visualization_dir = temp_dir / "visualizations"
            preview_cache_dir = temp_dir / "preview_cache"
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
                build_controlnets_for_dom_overlap_list(
                    overlap_list_path,
                    original_list_path,
                    dom_list_path,
                    dom_key_dir,
                    output_dir,
                    config,
                    report_directory=report_dir,
                    write_match_visualization=True,
                    match_visualization_scale=0.5,
                    match_visualization_output_dir=visualization_dir,
                    visualization_mode="reduced",
                    memory_profile="low-memory",
                    visualization_target_long_edge=640,
                    max_preview_pixels=180000,
                    preview_crop_margin_pixels=32,
                    preview_cache_dir=preview_cache_dir,
                    preview_cache_source="visualization_cache",
                    preview_force_regenerate=True,
                    preview_level=3,
                )

                self.assertEqual(build_mock.call_count, 2)
                for call in build_mock.call_args_list:
                    call_kwargs = call.kwargs
                    self.assertTrue(call_kwargs["write_match_visualization"])
                    self.assertEqual(call_kwargs["match_visualization_scale"], 0.5)
                    self.assertEqual(call_kwargs["match_visualization_output_dir"], Path(visualization_dir))
                    self.assertEqual(call_kwargs["visualization_mode"], "reduced")
                    self.assertEqual(call_kwargs["memory_profile"], "low-memory")
                    self.assertEqual(call_kwargs["visualization_target_long_edge"], 640)
                    self.assertEqual(call_kwargs["max_preview_pixels"], 180000)
                    self.assertEqual(call_kwargs["preview_crop_margin_pixels"], 32)
                    self.assertEqual(call_kwargs["preview_cache_dir"], Path(preview_cache_dir))
                    self.assertEqual(call_kwargs["preview_cache_source"], "visualization_cache")
                    self.assertTrue(call_kwargs["preview_force_regenerate"])
                    self.assertEqual(call_kwargs["preview_level"], 3)

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
            preview_cache_dir = temp_dir / "preview_cache"

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
                        "--write-match-visualization",
                        "--visualization-mode",
                        "reduced",
                        "--memory-profile",
                        "low-memory",
                        "--visualization-target-long-edge",
                        "640",
                        "--max-preview-pixels",
                        "180000",
                        "--preview-crop-margin-pixels",
                        "32",
                        "--preview-cache-dir",
                        str(preview_cache_dir),
                        "--preview-cache-source",
                        "visualization-cache",
                        "--preview-level",
                        "3",
                        "--preview-force-regenerate",
                    ]
                )

        called_config = batch_mock.call_args.args[5]
        call_kwargs = batch_mock.call_args.kwargs
        self.assertEqual(called_config.point_id_prefix, "CTX")
        self.assertEqual(batch_mock.call_args.kwargs["pair_id_prefix"], "S")
        self.assertEqual(batch_mock.call_args.kwargs["pair_id_start"], 3)
        self.assertEqual(batch_mock.call_args.kwargs["report_directory"], "reports")
        self.assertTrue(call_kwargs["write_match_visualization"])
        self.assertAlmostEqual(call_kwargs["match_visualization_scale"], 1.0 / 3.0)
        self.assertEqual(call_kwargs["visualization_mode"], "reduced")
        self.assertEqual(call_kwargs["memory_profile"], "low-memory")
        self.assertEqual(call_kwargs["visualization_target_long_edge"], 640)
        self.assertEqual(call_kwargs["max_preview_pixels"], 180000)
        self.assertEqual(call_kwargs["preview_crop_margin_pixels"], 32)
        self.assertEqual(call_kwargs["preview_cache_dir"], str(preview_cache_dir))
        self.assertEqual(call_kwargs["preview_cache_source"], "visualization_cache")
        self.assertEqual(call_kwargs["preview_level"], 3)
        self.assertTrue(call_kwargs["preview_force_regenerate"])
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

    def test_build_controlnet_for_dom_stereo_pair_forwards_visualization_preview_options(self):
        config = ControlNetConfig(
            network_id="ctx_dom_preview",
            target_name="Mars",
            user_name="zmoratto",
            description="dom preview wrapper test",
            point_id_prefix="PRV",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            output_net = temp_dir / "preview_wrapper.net"
            preview_cache_dir = temp_dir / "preview_cache"
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
                "status": "ok",
                "visualization_mode_used": "reduced_cropped",
                "memory_profile": "low-memory",
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
                    visualization_mode="reduced_cropped",
                    memory_profile="low-memory",
                    visualization_target_long_edge=1024,
                    max_preview_pixels=1_000_000,
                    preview_crop_margin_pixels=128,
                    preview_cache_dir=preview_cache_dir,
                    preview_cache_source="visualization_cache",
                    preview_force_regenerate=True,
                    preview_level=3,
                )

        ransac_mock.assert_called_once()
        visualization_mock.assert_called_once()
        paired_mock.assert_called_once()
        controlnet_mock.assert_called_once()
        self.assertEqual(result["match_visualization"], fake_visualization)
        call_kwargs = visualization_mock.call_args.kwargs
        self.assertEqual(call_kwargs["visualization_mode"], "reduced_cropped")
        self.assertEqual(call_kwargs["memory_profile"], "low-memory")
        self.assertEqual(call_kwargs["visualization_target_long_edge"], 1024)
        self.assertEqual(call_kwargs["max_preview_pixels"], 1_000_000)
        self.assertEqual(call_kwargs["preview_crop_margin_pixels"], 128)
        self.assertEqual(call_kwargs["preview_cache_dir"], preview_cache_dir)
        self.assertEqual(call_kwargs["preview_cache_source"], "visualization_cache")
        self.assertTrue(call_kwargs["preview_force_regenerate"])
        self.assertEqual(call_kwargs["preview_level"], 3)

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
                invalid_pixel_radius=0,
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
                invalid_pixel_radius=0,
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
