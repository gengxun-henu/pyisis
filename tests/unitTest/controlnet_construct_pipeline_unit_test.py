"""Focused unit tests for the next-stage DOM matching ControlNet pipeline helpers.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-06-01
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
Updated: 2026-05-05  Geng Xun added regression coverage for compact default stdout summaries and explicit full-detail stdout opt-in in controlnet_stereopair.py.
Updated: 2026-05-05  Geng Xun added regression coverage for routing pipeline step JSON outputs into files while keeping terminal output summary-only.
Updated: 2026-05-05  Geng Xun aligned pipeline-wrapper regressions with explicit report-json forwarding for overlap and post-merge summary CLIs.
Updated: 2026-05-08  Geng Xun replaced the overbuilt deep-matcher pipeline forwarding regression with a lightweight matcher parser acceptance check.
Updated: 2026-05-08  Geng Xun split deep-matcher parser acceptance from a lightweight pipeline forwarding assertion that checks matcher-method passthrough.
Updated: 2026-05-09  Geng Xun added wrapper-help regression coverage requiring superglue/lightglue/loftr method strings.
Updated: 2026-05-22  Geng Xun added baseline parser coverage for the new from-ori-match controlnet subcommand.
Updated: 2026-05-10  Geng Xun added CLI execution-path coverage so from-ori-match fails in a controlled Task-1-safe way instead of crashing on missing parser attrs.
Updated: 2026-05-10  Geng Xun updated from-ori-match coverage to require a clean argparse-style CLI rejection without a traceback.
Updated: 2026-05-10  Geng Xun updated from-ori-match coverage for full CLI dispatch into ori matching and direct ControlNet build.
Updated: 2026-05-16  Geng Xun added wrapper coverage for deep-match manifest export handoff summaries.
Updated: 2026-05-16  Geng Xun added pipeline wrapper coverage for adaptive-routing profile forwarding.
Updated: 2026-05-19  Geng Xun added regression coverage for deep matcher config path wrapper forwarding.
Updated: 2026-05-19  Geng Xun aligned wrapper regression coverage for ImageMatch-only defaults, adaptive routing, and resolved deep matcher config paths.
Updated: 2026-05-20  Geng Xun added preset-aware adaptive-routing forwarding coverage for deep preset maps loaded from config.
Updated: 2026-05-20  Geng Xun added stage-6 manifest provenance roundtrip coverage for deep-match runtime config export metadata.
Updated: 2026-05-23  Geng Xun added raw image ControlNet wrapper dry-run and execution coverage.
Updated: 2026-05-23  Geng Xun added raw image deep matcher and adaptive-routing forwarding coverage.
Updated: 2026-05-20  Geng Xun added config-relative adaptive-routing preset-map regression coverage.
Updated: 2026-05-20  Geng Xun added repo-root fallback coverage for adaptive-routing deep preset maps loaded from config.
Updated: 2026-05-20  Geng Xun added routed deep-preset compatibility regressions for initial and cascade adaptive routing.
Updated: 2026-05-20  Geng Xun added an export-path regression ensuring initial routed flann adopts the selected deep preset matcher.
Updated: 2026-05-27  Geng Xun added wrapper regression coverage for forwarding explicit OpenCV thread limits.
Updated: 2026-05-28  Geng Xun aligned adaptive-routing fake serial tile batches with TileMatchBatchResult.
Updated: 2026-05-28  Geng Xun added focused Step1 spiced-isis2std regression coverage for working-cube export, resume ordering, and docs/help discoverability.
Updated: 2026-05-28  Geng Xun restored Step1 wrapper regression coverage for input-dir, output-file, skip-step, and resume-from alongside the spiced stage checks.
Updated: 2026-06-01  Geng Xun added adaptive-routing ControlNet orchestration coverage for ORI and DOM matching flows.
"""

from __future__ import annotations

import argparse
import importlib
import json
import io
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, temporary_directory, workspace_test_data_path, write_synthetic_stereo_lists


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.controlnet_stereopair import (
    ControlNetConfig,
    build_argument_parser as build_controlnet_stereopair_parser,
    build_controlnet_for_dom_match_stereo_pair,
    build_controlnets_for_dom_match_overlap_list,
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
from controlnet_construct.deep_match_config import DeepMatchRuntimeConfig
from controlnet_construct.image_match import (
    build_argument_parser as build_controlnet_stereopair_argument_parser,
    main as image_match_main,
    match_dom_pair_to_key_files,
)
from controlnet_construct.image_overlap import (
    GeoBounds,
    _minimal_longitude_interval,
    extract_camera_ground_bounds,
    find_overlapping_image_pairs,
    geographic_bounds_overlap,
)
from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
from image_match.deep_match_manifest import build_deep_match_pair_manifest, read_deep_match_pair_manifest, write_deep_match_pair_manifest
from image_match.tile_matching import PairedTileWindow, TileMatchBatchResult, TileMatchTask, TileWindow


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
RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_ori_match_pipeline_example.sh"
CONTROLNET_STEP1_BATCH_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh"


def _embedded_python_script(source: str) -> str:
    lines = source.splitlines()
    normalized = [line[20:] if line.startswith(" " * 20) else line for line in lines]
    return "\n".join(normalized).lstrip() + "\n"


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


class ControlNetConstructPipelineUnitTest(unittest.TestCase):
    def _run_pipeline_validate_parameters_only(self, extra_args: list[str]) -> subprocess.CompletedProcess[str]:
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "validate_bad_wrapper_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            return subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    *extra_args,
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_run_pipeline_example_prints_parameter_groups(self):
        result = subprocess.run(
            [
                "bash",
                str(RUN_PIPELINE_EXAMPLE_PATH),
                "--print-parameter-groups",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Parameter groups for run_pipeline_example", result.stdout)
        self.assertIn("Matching", result.stdout)
        self.assertIn("--matcher-method", result.stdout)
        self.assertIn("Low Resolution", result.stdout)

    def test_run_pipeline_example_help_shows_compact_parameter_group_index(self):
        result = subprocess.run(
            [
                "bash",
                str(RUN_PIPELINE_EXAMPLE_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Parameter groups:", result.stdout)
        for group_name in (
            "inputs",
            "pipeline",
            "matching",
            "tile",
            "low_resolution",
            "adaptive_routing",
            "execution",
            "visualization",
            "controlnet",
            "reporting",
        ):
            self.assertIn(group_name, result.stdout)
        self.assertIn("--print-parameter-groups", result.stdout)
        self.assertIn("full catalog", result.stdout)

    def test_wrapper_help_mentions_opencv_num_threads(self):
        for script_path in (RUN_PIPELINE_EXAMPLE_PATH, RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH):
            with self.subTest(script_path=script_path.name):
                result = subprocess.run(
                    [
                        "bash",
                        str(script_path),
                        "--help",
                    ],
                    cwd=PROJECT_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--opencv-num-threads", result.stdout)
                self.assertIn("OpenCV", result.stdout)

    def test_lronac_step1_batch_script_accepts_explicit_input_dir(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            (input_dir / "E456.IMG").write_text("", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "lronac2isis",
                    "--input-dir",
                    str(input_dir),
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        command_lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(
            command_lines,
            [
                f"lronac2isis from={input_dir / 'E456.IMG'} to=E456.cub",
                f"lronac2isis from={input_dir / 'M123.IMG'} to=M123.cub",
            ],
        )

    def test_lronac_step1_batch_docs_mention_input_dir(self):
        help_result = subprocess.run(
            [
                "bash",
                str(CONTROLNET_STEP1_BATCH_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(
            encoding="utf-8"
        )
        combined_docs = help_result.stdout + "\n" + usage + "\n" + templates

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--input-dir", help_result.stdout)
        self.assertIn("--input-dir", usage)
        self.assertIn("--input-dir", templates)
        self.assertIn("--input-dir", combined_docs)

    def test_lronac_step1_batch_script_writes_commands_to_output_file(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            (input_dir / "E456.IMG").write_text("", encoding="utf-8")
            output_file = temp_dir / "step1_lronac2isis_batch.txt"

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "lronac2isis",
                    "--input-dir",
                    str(input_dir),
                    "--output-file",
                    str(output_file),
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            command_lines = [line for line in output_file.read_text(encoding="utf-8").splitlines() if line.strip()]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            command_lines,
            [
                f"lronac2isis from={input_dir / 'E456.IMG'} to=E456.cub",
                f"lronac2isis from={input_dir / 'M123.IMG'} to=M123.cub",
            ],
        )

    def test_lronac_step1_batch_docs_mention_output_file(self):
        help_result = subprocess.run(
            [
                "bash",
                str(CONTROLNET_STEP1_BATCH_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(
            encoding="utf-8"
        )
        combined_docs = help_result.stdout + "\n" + usage + "\n" + templates

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--output-file", help_result.stdout)
        self.assertIn("--output-file", usage)
        self.assertIn("--output-file", templates)
        self.assertIn("--output-file", combined_docs)

    def test_lronac_step1_batch_script_skips_multiple_requested_steps(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            (input_dir / "E456.IMG").write_text("", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "all",
                    "--use-reduce",
                    "--input-dir",
                    str(input_dir),
                    "--skip-step",
                    "lronac2isis,reduce",
                    "--skip-step",
                    "spiceinit",
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("lronac2isis ", result.stdout)
        self.assertNotIn("reduce from=", result.stdout)
        self.assertNotIn("spiceinit from=", result.stdout)
        self.assertIn("lronaccal from=E456.cub to=E456.cal.cub", result.stdout)
        self.assertIn("lronacecho from=E456.cal.cub to=E456.echo.cal.cub", result.stdout)
        self.assertIn("lronaccal from=M123.cub to=M123.cal.cub", result.stdout)
        self.assertIn("lronacecho from=M123.cal.cub to=M123.echo.cal.cub", result.stdout)

    def test_lronac_step1_batch_docs_mention_skip_step(self):
        help_result = subprocess.run(
            [
                "bash",
                str(CONTROLNET_STEP1_BATCH_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(
            encoding="utf-8"
        )
        combined_docs = help_result.stdout + "\n" + usage + "\n" + templates

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--skip-step", help_result.stdout)
        self.assertIn("--skip-step", usage)
        self.assertIn("--skip-step", templates)
        self.assertIn("lronac2isis,reduce", combined_docs)
        self.assertIn("--skip-step spiceinit", combined_docs)

    def test_lronac_step1_batch_script_resumes_from_named_step(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            (input_dir / "E456.IMG").write_text("", encoding="utf-8")
            output_file = temp_dir / "step1_resume_batch.txt"

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "all",
                    "--use-reduce",
                    "--input-dir",
                    str(input_dir),
                    "--output-file",
                    str(output_file),
                    "--include-spiceinit",
                    "--resume-from",
                    "spiceinit",
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            command_text = output_file.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("lronac2isis ", command_text)
        self.assertNotIn("reduce from=", command_text)
        self.assertNotIn("lronaccal from=", command_text)
        self.assertNotIn("lronacecho from=", command_text)
        self.assertIn("spiceinit from=REDUCED_E456.echo.cal.cub", command_text)
        self.assertIn("cam2map from=REDUCED_E456.echo.cal.cub", command_text)
        self.assertIn("isis2std from=dom_REDUCED_E456.cub", command_text)
        self.assertIn("spiceinit from=REDUCED_M123.echo.cal.cub", command_text)
        self.assertIn("cam2map from=REDUCED_M123.echo.cal.cub", command_text)
        self.assertIn("isis2std from=dom_REDUCED_M123.cub", command_text)

    def test_lronac_step1_batch_docs_mention_resume_from(self):
        help_result = subprocess.run(
            [
                "bash",
                str(CONTROLNET_STEP1_BATCH_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(
            encoding="utf-8"
        )
        combined_docs = help_result.stdout + "\n" + usage + "\n" + templates

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--resume-from", help_result.stdout)
        self.assertIn("--resume-from", usage)
        self.assertIn("--resume-from", templates)
        self.assertIn("--resume-from spiceinit", combined_docs)

    def test_lronac_step1_batch_script_emits_spiced_isis2std_for_original_working_cube(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "isis2std-spiced",
                    "--input-dir",
                    str(input_dir),
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            command_lines = [line for line in result.stdout.splitlines() if line.strip()]
            self.assertEqual(
                command_lines,
                [
                    "isis2std from=M123.echo.cal.cub to=M123.tif format=tiff minpercent=0.1 maxpercent=99.9",
                ],
            )

    def test_lronac_step1_batch_script_emits_spiced_isis2std_for_reduced_working_cube(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "isis2std-spiced",
                    "--input-dir",
                    str(input_dir),
                    "--use-reduce",
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            command_lines = [line for line in result.stdout.splitlines() if line.strip()]
            self.assertEqual(
                command_lines,
                [
                    "isis2std from=REDUCED_M123.echo.cal.cub to=REDUCED_M123.tif format=tiff minpercent=0.1 maxpercent=99.9",
                ],
            )

    def test_lronac_step1_batch_script_resume_from_spiceinit_includes_spiced_isis2std(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            output_file = temp_dir / "step1_resume_batch.txt"

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "all",
                    "--input-dir",
                    str(input_dir),
                    "--output-file",
                    str(output_file),
                    "--use-reduce",
                    "--include-spiceinit",
                    "--resume-from",
                    "spiceinit",
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            command_text = output_file.read_text(encoding="utf-8")
            self.assertIn("spiceinit from=REDUCED_M123.echo.cal.cub", command_text)
            self.assertIn("isis2std from=REDUCED_M123.echo.cal.cub to=REDUCED_M123.tif", command_text)
            self.assertIn("cam2map from=REDUCED_M123.echo.cal.cub", command_text)
            self.assertIn("isis2std from=dom_REDUCED_M123.cub", command_text)

    def test_lronac_step1_batch_script_resume_from_cam2map_skips_spiced_isis2std(self):
        with temporary_directory() as temp_dir:
            input_dir = temp_dir / "img_inputs"
            input_dir.mkdir()
            (input_dir / "M123.IMG").write_text("", encoding="utf-8")
            output_file = temp_dir / "step1_resume_batch.txt"

            result = subprocess.run(
                [
                    "bash",
                    str(CONTROLNET_STEP1_BATCH_PATH),
                    "--step",
                    "all",
                    "--input-dir",
                    str(input_dir),
                    "--output-file",
                    str(output_file),
                    "--use-reduce",
                    "--resume-from",
                    "cam2map",
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            command_text = output_file.read_text(encoding="utf-8")
            self.assertNotIn("to=REDUCED_M123.tif", command_text)
            self.assertIn("cam2map from=REDUCED_M123.echo.cal.cub", command_text)
            self.assertIn("isis2std from=dom_REDUCED_M123.cub", command_text)

    def test_lronac_step1_batch_docs_mention_spiced_isis2std(self):
        help_result = subprocess.run(
            [
                "bash",
                str(CONTROLNET_STEP1_BATCH_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(
            encoding="utf-8"
        )
        combined_docs = help_result.stdout + "\n" + usage + "\n" + templates

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("isis2std-spiced", help_result.stdout)
        self.assertIn("--resume-from", help_result.stdout)
        self.assertIn("isis2std-spiced", usage)
        self.assertIn("--resume-from spiceinit", usage)
        self.assertIn("isis2std-spiced", templates)
        self.assertIn("--resume-from spiceinit", templates)
        self.assertIn("isis2std-spiced", combined_docs)
        self.assertIn("--resume-from spiceinit", combined_docs)

    def test_run_pipeline_example_validates_parameters_only_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "validate_only_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                            "opencv_num_threads": 1,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Parameter validation passed", result.stdout)
        self.assertIn("MATCHER_METHOD=bf", result.stdout)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=3", result.stdout)
        self.assertIn("OPENCV_NUM_THREADS=1", result.stdout)
        self.assertIn(f"WORK_DIR={work_dir}", result.stdout)
        self.assertIn("NETWORK_ID=validate_only_unit", result.stdout)
        self.assertNotIn("Step 1/", result.stdout)

    def test_run_pipeline_example_validate_only_reads_image_match_config_once(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "validate_config_probe_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                            "low_resolution_level": 4,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            calls_path = temp_dir / "print_config_default_calls.txt"
            stdin_calls_path = temp_dir / "stdin_calls.txt"
            catalog_calls_path = temp_dir / "catalog_calls.txt"
            fake_python = temp_dir / "fake_python.py"
            fake_python.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import os",
                        "import subprocess",
                        "import sys",
                        f"real_python = {sys.executable!r}",
                        f"calls_path = {str(calls_path)!r}",
                        f"stdin_calls_path = {str(stdin_calls_path)!r}",
                        "args = sys.argv[1:]",
                        "if args and args[0].endswith('examples/image_match/image_match.py') and '--print-config-default' in args:",
                        "    with open(calls_path, 'a', encoding='utf-8') as handle:",
                        "        handle.write(args[args.index('--print-config-default') + 1] + '\\n')",
                        "if args and args[0] == '-':",
                        "    with open(stdin_calls_path, 'a', encoding='utf-8') as handle:",
                        "        handle.write('stdin\\n')",
                        "completed = subprocess.run([real_python, *args], check=False)",
                        "raise SystemExit(completed.returncode)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            fake_catalog_python = temp_dir / "fake_catalog_python.py"
            fake_catalog_python.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import subprocess",
                        "import sys",
                        "from pathlib import Path",
                        f"real_python = {sys.executable!r}",
                        f"catalog_calls_path = {str(catalog_calls_path)!r}",
                        "args = sys.argv[1:]",
                        "label = 'stdin' if args and args[0] == '-' else Path(args[0]).name if args else 'empty'",
                        "with open(catalog_calls_path, 'a', encoding='utf-8') as handle:",
                        "    handle.write(label + '\\n')",
                        "completed = subprocess.run([real_python, *args], check=False)",
                        "raise SystemExit(completed.returncode)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_catalog_python.chmod(0o755)
            env = dict(os.environ)
            env["PARAMETER_CATALOG_PYTHON_EXECUTABLE"] = str(fake_catalog_python)

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            calls = calls_path.read_text(encoding="utf-8").splitlines() if calls_path.exists() else []
            stdin_calls = stdin_calls_path.read_text(encoding="utf-8").splitlines() if stdin_calls_path.exists() else []
            catalog_calls = catalog_calls_path.read_text(encoding="utf-8").splitlines() if catalog_calls_path.exists() else []

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=3", result.stdout)
        self.assertEqual(calls, [])
        self.assertEqual(stdin_calls, ["stdin"])
        self.assertEqual(catalog_calls, ["stdin"])

    def test_run_pipeline_example_parameter_profile_applies_balanced_defaults(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            (work_dir / "original_images.lis").write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            (work_dir / "doms.lis").write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"NetworkId": "profile_balanced_unit", "TargetName": "Mars", "UserName": "unit"})
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--parameter-profile",
                    "balanced",
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PARAMETER_PROFILE=balanced", result.stdout)
        self.assertIn("MATCHER_METHOD=flann", result.stdout)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=8", result.stdout)
        self.assertIn("ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION=1", result.stdout)
        self.assertIn("LOW_RESOLUTION_LEVEL=3", result.stdout)

    def test_run_pipeline_example_parameter_profile_does_not_override_cli_values(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            (work_dir / "original_images.lis").write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            (work_dir / "doms.lis").write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"NetworkId": "profile_cli_unit", "TargetName": "Mars", "UserName": "unit"})
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--parameter-profile",
                    "aggressive",
                    "--matcher-method",
                    "flann",
                    "--num-worker-parallel-cpu",
                    "6",
                    "--low-resolution-level",
                    "2",
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PARAMETER_PROFILE=aggressive", result.stdout)
        self.assertIn("MATCHER_METHOD=flann", result.stdout)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=6", result.stdout)
        self.assertIn("LOW_RESOLUTION_LEVEL=2", result.stdout)

    def test_run_pipeline_example_parameter_profile_does_not_override_config_values(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            (work_dir / "original_images.lis").write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            (work_dir / "doms.lis").write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "profile_config_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                            "low_resolution_level": 5,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--parameter-profile",
                    "aggressive",
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PARAMETER_PROFILE=aggressive", result.stdout)
        self.assertIn("MATCHER_METHOD=bf", result.stdout)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=3", result.stdout)
        self.assertIn("LOW_RESOLUTION_LEVEL=5", result.stdout)

    def test_run_pipeline_example_validate_parameters_only_rejects_bad_wrapper_cli_values(self):
        cases = (
            ("pair_id_start", ["--pair-id-start", "not_an_int"]),
            ("invalid_pixel_radius", ["--invalid-pixel-radius", "bad"]),
            ("valid_pixel_percent_threshold", ["--valid-pixel-percent-threshold", "bad"]),
        )

        for expected_field, extra_args in cases:
            with self.subTest(expected_field=expected_field):
                result = self._run_pipeline_validate_parameters_only(extra_args)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_field, result.stderr)

    def test_run_pipeline_example_inactive_cli_low_resolution_value_errors_without_strict(self):
        result = self._run_pipeline_validate_parameters_only(["--low-resolution-level", "4"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("low_resolution_level", result.stderr)
        self.assertIn("explicit CLI", result.stderr)

    def test_run_pipeline_example_inactive_config_low_resolution_value_warns_without_strict(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "inactive_config_low_resolution_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "enable_low_resolution_offset_estimation": False,
                            "low_resolution_level": 4,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning:", result.stderr)
        self.assertIn("low_resolution_level", result.stderr)

    def test_run_pipeline_example_deep_match_manifest_dir_is_inactive_in_direct_mode(self):
        result = self._run_pipeline_validate_parameters_only(["--deep-match-manifest-dir", "/tmp/deep-match-manifests"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deep_match_manifest_dir", result.stderr)
        self.assertIn("deep_match_mode is direct", result.stderr)

    def test_run_pipeline_example_strict_parameter_validation_promotes_warning(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "strict_validate_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                            "enable_low_resolution_offset_estimation": False,
                            "low_resolution_level": 4,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--strict-parameter-validation",
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("strict parameter validation", result.stderr)
        self.assertIn("low_resolution_level", result.stderr)

    def test_run_pipeline_example_strict_parameter_validation_can_come_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            dom_list = work_dir / "doms.lis"
            dom_list.write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "strict_config_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                            "enable_low_resolution_offset_estimation": False,
                            "low_resolution_level": 4,
                        },
                        "Reporting": {
                            "strict_parameter_validation": True,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("strict parameter validation", result.stderr)
        self.assertIn("low_resolution_level", result.stderr)

    def test_run_pipeline_example_preserves_wrapper_defaults_after_parameter_validation(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "preserve-defaults-unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                        },
                    }
                )
                + "\n",
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
                        "    return 0",
                        "",
                        "def _write_fake_key_outputs(args: list[str]) -> None:",
                        "    key_index = 4 if args and args[0] == '--config' else 2",
                        "    Path(args[key_index]).write_text('synthetic-left-key\\n', encoding='utf-8')",
                        "    Path(args[key_index + 1]).write_text('synthetic-right-key\\n', encoding='utf-8')",
                        "",
                        "def main() -> int:",
                        "    if len(sys.argv) < 2:",
                        "        return 0",
                        "    if sys.argv[1] == '-':",
                        "        return _run_stdin_python()",
                        "    script_name = Path(sys.argv[1]).name",
                        "    args = sys.argv[2:]",
                        "",
                        "    if script_name == 'image_overlap.py':",
                        "        Path(args[1]).write_text('left.cub,right.cub\\n', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'prepare_low_resolution_doms.py':",
                        "        if '--level' not in args:",
                        "            raise SystemExit('missing low-resolution prepare --level')",
                        "        level = args[args.index('--level') + 1]",
                        "        if level != '3':",
                        "            raise SystemExit(f'unexpected prepare level: {level}')",
                        "        output_list = Path(args[1])",
                        "        output_list.parent.mkdir(parents=True, exist_ok=True)",
                        "        output_list.write_text('left_low_level3.cub\\nright_low_level3.cub\\n', encoding='utf-8')",
                        "        return 0",
                        "",
                        "    if script_name == 'image_match.py':",
                        "        if '--print-config-default' in args:",
                        "            config_path = Path(args[args.index('--config') + 1])",
                        "            field_name = args[args.index('--print-config-default') + 1]",
                        "            payload = json.loads(config_path.read_text(encoding='utf-8'))",
                        "            image_match_config = payload.get('ImageMatch') or {}",
                        "            if field_name == 'matcher_method':",
                        "                print(image_match_config.get('matcher_method', ''))",
                        "            else:",
                        "                print('')",
                        "            return 0",
                        "        expected_pairs = {",
                        "            '--low-resolution-level': '3',",
                        "            '--low-resolution-max-mean-reprojection-error-pixels': '3.0',",
                        "            '--low-resolution-min-retained-match-count': '5',",
                        "            '--low-resolution-max-mean-projected-offset-meters': '0.0',",
                        "        }",
                        "        if '--enable-low-resolution-offset-estimation' not in args:",
                        "            raise SystemExit('missing low-resolution enable flag')",
                        "        for flag, expected in expected_pairs.items():",
                        "            if flag not in args:",
                        "                raise SystemExit(f'missing {flag}')",
                        "            actual = args[args.index(flag) + 1]",
                        "            if actual != expected:",
                        "                raise SystemExit(f'unexpected {flag}: {actual!r}')",
                        "        _write_fake_key_outputs(args)",
                        "        return 0",
                        "",
                        "    if script_name == 'controlnet_stereopair.py':",
                        "        if '--visualization-mode' not in args:",
                        "            raise SystemExit('missing --visualization-mode')",
                        "        visualization_mode = args[args.index('--visualization-mode') + 1]",
                        "        if visualization_mode != 'full':",
                        "            raise SystemExit(f'unexpected visualization mode: {visualization_mode}')",
                        "        if '--preview-crop-margin-pixels' not in args:",
                        "            raise SystemExit('missing --preview-crop-margin-pixels')",
                        "        crop_margin = args[args.index('--preview-crop-margin-pixels') + 1]",
                        "        if crop_margin != '128':",
                        "            raise SystemExit(f'unexpected preview crop margin pixels: {crop_margin}')",
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

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python_dispatcher),
                    "--enable-low-resolution-offset-estimation",
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Low-resolution max mean reprojection error (pixels): 3.0", result.stdout)
        self.assertIn("Low-resolution minimum retained matches: 5", result.stdout)
        self.assertIn("Low-resolution max mean projected offset (meters): 0.0", result.stdout)
        self.assertIn("Post-RANSAC visualization mode: full", result.stdout)
        self.assertIn("Post-RANSAC preview crop margin (pixels): 128", result.stdout)

    def test_run_ori_match_pipeline_dry_run_writes_expected_commands(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            overlap_list = work_dir / "images_overlap.lis"
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "raw_ori_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "Description": "raw image unit test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            deep_config_path = temp_dir / "lightglue_official_superpoint.json"
            deep_config_path.write_text('{"matcher":{"method":"lightglue","backend":"official"}}\n', encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--images-overlap-list",
                    str(overlap_list),
                    "--config",
                    str(config_path),
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-config-path",
                    str(deep_config_path),
                    "--adaptive-routing",
                    "--adaptive-routing-profile",
                    "relaxed",
                    "--ratio-test",
                    "0.8",
                    "--max-features",
                    "1200",
                    "--pair-id-prefix",
                    "R",
                    "--pair-id-start",
                    "7",
                    "--num-worker-parallel-cpu",
                    "2",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            command_script = work_dir / "command.sh"
            self.assertTrue(command_script.exists())
            command_text = command_script.read_text(encoding="utf-8")
            command_lines = command_text.splitlines()
            parsed_commands = [shlex.split(line) for line in command_lines[2:]]

        self.assertEqual(command_lines[:2], ["#!/usr/bin/env bash", "set -euo pipefail"])
        self.assertIn("image_overlap.py", command_text)
        self.assertIn("controlnet_stereopair.py", command_text)
        self.assertIn("from-ori-match", command_text)
        self.assertIn("controlnet_merge.py", command_text)
        self.assertIn(str(left), command_text)
        self.assertIn(str(right), command_text)
        self.assertIn("--pair-id", command_text)
        self.assertIn("R7", command_text)
        self.assertIn("--left-output-key", command_text)
        self.assertIn("ori_keys/left__right_A.key", command_text)
        self.assertIn("ori_keys/left__right_B.key", command_text)
        self.assertIn("ori_pair_nets/left__right.net", command_text)
        self.assertIn("--matcher-method", command_text)
        self.assertIn("lightglue", command_text)
        self.assertIn("--deep-match-config-path", command_text)
        self.assertIn(str(deep_config_path), command_text)
        self.assertIn("--adaptive-routing", command_text)
        self.assertIn("--adaptive-routing-profile", command_text)
        self.assertIn("relaxed", command_text)
        self.assertIn("--ratio-test", command_text)
        self.assertIn("0.8", command_text)
        self.assertIn("--max-features", command_text)
        self.assertIn("1200", command_text)
        self.assertIn("--num-worker-parallel-cpu", command_text)
        self.assertIn("2", command_text)
        self.assertIn("merge_all_controlnets.sh", command_text)
        self.assertNotIn(" /images_overlap.lis", command_text)

        overlap_command = parsed_commands[0]
        self.assertEqual(overlap_command[1], str(PROJECT_ROOT / "examples" / "controlnet_construct" / "image_overlap.py"))
        self.assertEqual(overlap_command[2:4], [str(original_list), str(overlap_list)])
        self.assertEqual(overlap_command[4:6], ["--report-json", str(work_dir / "reports" / "image_overlap_summary.json")])

        pair_command = next(command for command in parsed_commands if "from-ori-match" in command)
        self.assertEqual(pair_command[1], str(PROJECT_ROOT / "examples" / "controlnet_construct" / "controlnet_stereopair.py"))
        self.assertEqual(pair_command[2:7], ["from-ori-match", str(left), str(right), str(config_path), str(work_dir / "ori_pair_nets" / "left__right.net")])
        self.assertEqual(pair_command[pair_command.index("--pair-id") + 1], "R7")
        self.assertEqual(pair_command[pair_command.index("--left-output-key") + 1], str(work_dir / "ori_keys" / "left__right_A.key"))
        self.assertEqual(pair_command[pair_command.index("--right-output-key") + 1], str(work_dir / "ori_keys" / "left__right_B.key"))
        self.assertEqual(pair_command[pair_command.index("--report-path") + 1], str(work_dir / "reports" / "left__right.summary.json"))
        self.assertEqual(pair_command[pair_command.index("--matcher-method") + 1], "lightglue")
        self.assertEqual(pair_command[pair_command.index("--deep-match-config-path") + 1], str(deep_config_path))
        self.assertIn("--adaptive-routing", pair_command)
        self.assertEqual(pair_command[pair_command.index("--adaptive-routing-profile") + 1], "relaxed")
        self.assertEqual(pair_command[pair_command.index("--ratio-test") + 1], "0.8")
        self.assertEqual(pair_command[pair_command.index("--max-features") + 1], "1200")
        self.assertEqual(pair_command[pair_command.index("--num-worker-parallel-cpu") + 1], "2")

        merge_command = next(command for command in parsed_commands if any(Path(arg).name == "controlnet_merge.py" for arg in command))
        self.assertEqual(merge_command[2:6], [str(overlap_list), str(work_dir / "ori_pair_nets"), str(work_dir / "merge" / "ori_matching_merged.net"), str(work_dir / "merge" / "merge_all_controlnets.sh")])
        self.assertIn("--strict", merge_command)

    def test_run_ori_match_pipeline_fresh_dry_run_warns_without_overlap_list(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "missing_parent" / "work_ori"
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = temp_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "raw_ori_fresh_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("cd:", result.stderr)
            self.assertIn("overlap list not found", result.stderr)
            command_script = work_dir / "command.sh"
            self.assertTrue(command_script.exists())
            command_text = command_script.read_text(encoding="utf-8")

        self.assertTrue(command_text.startswith("#!/usr/bin/env bash\nset -euo pipefail\n"))
        self.assertIn("image_overlap.py", command_text)
        self.assertIn("controlnet_merge.py", command_text)
        self.assertNotIn("from-ori-match", command_text)
        self.assertNotIn(" /images_overlap.lis", command_text)

    def test_run_ori_match_pipeline_executes_fake_pipeline_and_writes_summary(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                '{"NetworkId":"raw_image_matching","TargetName":"Mars","UserName":"unit"}\n',
                encoding="utf-8",
            )
            deep_config_path = temp_dir / "lightglue_official_superpoint.json"
            deep_config_path.write_text('{"matcher":{"method":"lightglue","backend":"official"}}\n', encoding="utf-8")
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    r'''
                    from __future__ import annotations

                    import json
                    from pathlib import Path
                    import sys

                    script = Path(sys.argv[1])
                    args = sys.argv[2:]

                    if script.name == "image_overlap.py":
                        input_list = Path(args[0])
                        output_list = Path(args[1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        images = [line.strip() for line in input_list.read_text(encoding="utf-8").splitlines() if line.strip()]
                        output_list.write_text(f"{images[0]},{images[1]}\n", encoding="utf-8")
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(json.dumps({"pair_count": 1, "image_count": 2}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_stereopair.py" and args[0] == "from-ori-match":
                        if "--deep-match-config-path" not in args:
                            raise SystemExit("missing --deep-match-config-path forwarding")
                        if "--adaptive-routing" not in args:
                            raise SystemExit("missing --adaptive-routing forwarding")
                        if args[args.index("--adaptive-routing-profile") + 1] != "fast":
                            raise SystemExit("missing --adaptive-routing-profile fast forwarding")
                        output_net = Path(args[4])
                        left_key = Path(args[args.index("--left-output-key") + 1])
                        right_key = Path(args[args.index("--right-output-key") + 1])
                        report_path = Path(args[args.index("--report-path") + 1])
                        for path in (output_net, left_key, right_key, report_path):
                            path.parent.mkdir(parents=True, exist_ok=True)
                        output_net.write_text("pair net\n", encoding="utf-8")
                        left_key.write_text("left key\n", encoding="utf-8")
                        right_key.write_text("right key\n", encoding="utf-8")
                        report_path.write_text(json.dumps({"mode": "from-ori-match", "controlnet": {"point_count": 3}}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_merge.py":
                        if "--strict" not in args:
                            raise SystemExit("controlnet_merge.py was called without --strict")
                        pair_net_dir = Path(args[1])
                        script_path = Path(args[3])
                        pair_list = Path(args[args.index("--pair-list") + 1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        output_net = Path(args[2])
                        script_path.parent.mkdir(parents=True, exist_ok=True)
                        pair_list.write_text("\n".join(str(path) for path in pair_net_dir.glob("*.net")) + "\n", encoding="utf-8")
                        script_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\nprintf merged > " + str(output_net) + "\n", encoding="utf-8")
                        script_path.chmod(0o755)
                        report_path.write_text(json.dumps({"included_count": 1, "output_net": str(output_net)}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    raise SystemExit(f"unexpected command: {sys.argv}")
                    '''
                ),
                encoding="utf-8",
            )
            fake_python = temp_dir / "fake_python"
            quoted_python = shlex.quote(str(sys.executable))
            quoted_dispatcher = shlex.quote(str(fake_python_dispatcher))
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                f"exec {quoted_python} {quoted_dispatcher} \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = {**os.environ, "PYTHON_EXECUTABLE": str(fake_python)}
            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-config-path",
                    str(deep_config_path),
                    "--adaptive-routing",
                    "--adaptive-routing-profile",
                    "fast",
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary_path = work_dir / "reports" / "ori_match_batch_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["mode"], "from-ori-match-batch-wrapper")
        self.assertEqual(summary["original_list"], str(original_list))
        self.assertEqual(summary["images_overlap_list"], str(work_dir / "images_overlap.lis"))
        self.assertEqual(summary["pair_count"], 1)
        self.assertEqual(summary["pair_id_prefix"], "S")
        self.assertEqual(summary["pair_id_start"], 1)
        self.assertEqual(summary["matcher_method"], "lightglue")
        self.assertEqual(summary["deep_match_config_path"], str(deep_config_path))
        self.assertTrue(summary["adaptive_routing"])
        self.assertEqual(summary["adaptive_routing_profile"], "fast")
        self.assertEqual(summary["pair_net_directory"], str(work_dir / "ori_pair_nets"))
        self.assertEqual(summary["report_directory"], str(work_dir / "reports"))
        self.assertEqual(summary["merge_output_net"], str(work_dir / "merge" / "ori_matching_merged.net"))
        self.assertEqual(summary["merge_script_path"], str(work_dir / "merge" / "merge_all_controlnets.sh"))
        self.assertEqual(summary["pairs"][0]["pair_id"], "S1")
        self.assertEqual(summary["pairs"][0]["pair"], f"{left},{right}")
        self.assertEqual(summary["pairs"][0]["output_net"], str(work_dir / "ori_pair_nets" / "left__right.net"))
        self.assertEqual(summary["pairs"][0]["left_key"], str(work_dir / "ori_keys" / "left__right_A.key"))
        self.assertEqual(summary["pairs"][0]["right_key"], str(work_dir / "ori_keys" / "left__right_B.key"))
        self.assertEqual(summary["pairs"][0]["report_path"], str(work_dir / "reports" / "left__right.summary.json"))
        self.assertEqual(summary["pairs"][0]["status"], "success")
        self.assertIn("raw image pair matching complete", result.stdout)

    def test_run_ori_match_pipeline_fails_when_final_merge_output_is_missing(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                '{"NetworkId":"raw_image_matching","TargetName":"Mars","UserName":"unit"}\n',
                encoding="utf-8",
            )
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    r'''
                    from __future__ import annotations

                    import json
                    from pathlib import Path
                    import sys

                    script = Path(sys.argv[1])
                    args = sys.argv[2:]

                    if script.name == "image_overlap.py":
                        input_list = Path(args[0])
                        output_list = Path(args[1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        images = [line.strip() for line in input_list.read_text(encoding="utf-8").splitlines() if line.strip()]
                        output_list.write_text(f"{images[0]},{images[1]}\n", encoding="utf-8")
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(json.dumps({"pair_count": 1, "image_count": 2}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_stereopair.py" and args[0] == "from-ori-match":
                        output_net = Path(args[4])
                        left_key = Path(args[args.index("--left-output-key") + 1])
                        right_key = Path(args[args.index("--right-output-key") + 1])
                        report_path = Path(args[args.index("--report-path") + 1])
                        for path in (output_net, left_key, right_key, report_path):
                            path.parent.mkdir(parents=True, exist_ok=True)
                        output_net.write_text("pair net\n", encoding="utf-8")
                        left_key.write_text("left key\n", encoding="utf-8")
                        right_key.write_text("right key\n", encoding="utf-8")
                        report_path.write_text(json.dumps({"mode": "from-ori-match", "controlnet": {"point_count": 3}}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_merge.py":
                        script_path = Path(args[3])
                        pair_list = Path(args[args.index("--pair-list") + 1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        script_path.parent.mkdir(parents=True, exist_ok=True)
                        pair_list.write_text("pair.net\n", encoding="utf-8")
                        script_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n", encoding="utf-8")
                        script_path.chmod(0o755)
                        report_path.write_text(json.dumps({"included_count": 1}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    raise SystemExit(f"unexpected command: {sys.argv}")
                    '''
                ),
                encoding="utf-8",
            )
            fake_python = temp_dir / "fake_python"
            quoted_python = shlex.quote(str(sys.executable))
            quoted_dispatcher = shlex.quote(str(fake_python_dispatcher))
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                f"exec {quoted_python} {quoted_dispatcher} \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = {**os.environ, "PYTHON_EXECUTABLE": str(fake_python)}
            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected from-ori-match output not found", result.stderr)
        self.assertIn("ori_matching_merged.net", result.stderr)
        self.assertFalse((work_dir / "reports" / "ori_match_batch_summary.json").exists())

    def test_run_ori_match_pipeline_rejects_invalid_pair_id_start(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text('{"NetworkId":"n","TargetName":"Mars","UserName":"u"}\n', encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                    "--pair-id-start",
                    "0",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--pair-id-start must be at least 1", result.stderr)

    def test_run_ori_match_pipeline_rejects_unsupported_deep_export_mode(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            config_path = temp_dir / "config.json"
            original_list.write_text("", encoding="utf-8")
            config_path.write_text(
                json.dumps({"NetworkId": "raw_unit", "TargetName": "Moon", "UserName": "tester"}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                    "--deep-match-mode",
                    "export",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--deep-match-mode currently supports only direct", result.stderr)

    def test_run_ori_match_pipeline_forwards_official_deep_and_adaptive_flags(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            overlap_list = work_dir / "images_overlap.lis"
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text('{"NetworkId":"n","TargetName":"Mars","UserName":"u"}\n', encoding="utf-8")
            deep_config_path = temp_dir / "lightglue_official_superpoint.json"
            deep_config_path.write_text('{"matcher":{"method":"lightglue","backend":"official"}}\n', encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--images-overlap-list",
                    str(overlap_list),
                    "--config",
                    str(config_path),
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-config-path",
                    str(deep_config_path),
                    "--adaptive-routing",
                    "--adaptive-routing-profile",
                    "strict",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            command_text = (work_dir / "command.sh").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--matcher-method lightglue", command_text)
        self.assertIn(f"--deep-match-config-path {deep_config_path}", command_text)
        self.assertIn("--adaptive-routing", command_text)
        self.assertIn("--adaptive-routing-profile strict", command_text)

    def test_run_ori_match_pipeline_forwards_adaptive_and_official_deep_presets(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            left = temp_dir / "left.cub"
            right = temp_dir / "right.cub"
            left.write_text("left", encoding="utf-8")
            right.write_text("right", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            overlap_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "config.json"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "raw_adaptive_unit",
                        "TargetName": "Moon",
                        "UserName": "tester",
                        "ImageMatch": {
                            "enable_adaptive_routing": True,
                            "adaptive_routing_profile": "strict",
                            "matcher_method": "flann",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                            "adaptive_routing_deep_presets": {
                                "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                                "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--images-overlap-list",
                    str(overlap_list),
                    "--config",
                    str(config_path),
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            command_text = (work_dir / "command.sh").read_text(encoding="utf-8")
            parsed_commands = [
                shlex.split(line)
                for line in command_text.splitlines()
                if line and not line.startswith("#") and not line.startswith("set ")
            ]

        self.assertEqual(result.returncode, 0, result.stderr)
        expected_lightglue = str(PROJECT_ROOT / "examples/controlnet_construct/presets/lightglue_official_superpoint.json")
        expected_loftr = str(PROJECT_ROOT / "examples/controlnet_construct/presets/loftr_external_outdoor.json")
        pair_command = next(command for command in parsed_commands if "from-ori-match" in command)
        self.assertIn("--adaptive-routing", pair_command)
        self.assertIn("--adaptive-routing-profile", pair_command)
        self.assertEqual(pair_command[pair_command.index("--adaptive-routing-profile") + 1], "strict")
        self.assertIn("--deep-match-config-path", pair_command)
        self.assertEqual(
            pair_command[pair_command.index("--deep-match-config-path") + 1],
            expected_lightglue,
        )
        preset_values = [
            pair_command[index + 1]
            for index, value in enumerate(pair_command)
            if value == "--adaptive-routing-deep-preset"
        ]
        self.assertIn(
            f"lightglue={expected_lightglue}",
            preset_values,
        )
        self.assertIn(
            f"loftr={expected_loftr}",
            preset_values,
        )

    def test_recommended_docs_use_official_lightglue_and_external_loftr_presets(self):
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(encoding="utf-8")
        matcher_example = json.loads(
            (PROJECT_ROOT / "examples" / "controlnet_construct" / "experiments" / "matcher_comparison.example.json").read_text(
                encoding="utf-8"
            )
        )
        combined_docs = usage + "\n" + templates

        self.assertIn("lightglue_official_superpoint.json", combined_docs)
        self.assertIn("loftr_external_outdoor.json", combined_docs)
        self.assertIn("loftr_default.json` is the Kornia compatibility preset", combined_docs)
        for legacy in (
            "lightglue_default.json",
            "lightglue_high_recall.json",
            "lightglue_disk.json",
            "lightglue_aliked.json",
            "lightglue_doghardnet.json",
            "superglue_default.json",
            "superglue_aliked.json",
        ):
            self.assertNotIn(f"presets/{legacy}", combined_docs)

        method_presets = {
            method.get("deep_match_config_path")
            for method in matcher_example.get("methods", [])
            if method.get("deep_match_config_path")
        }
        self.assertIn("examples/controlnet_construct/presets/lightglue_official_superpoint.json", method_presets)
        self.assertIn("examples/controlnet_construct/presets/loftr_external_outdoor.json", method_presets)
        self.assertNotIn("examples/controlnet_construct/presets/superglue_aliked.json", method_presets)
        self.assertNotIn("examples/controlnet_construct/presets/lightglue_disk.json", method_presets)

    def test_deep_match_manifest_roundtrip_preserves_runtime_config_provenance_fields(self):
        runtime_config = DeepMatchRuntimeConfig(
            matcher_method="lightglue",
            feature_extractor_method="superpoint",
            prefer_gpu=True,
            device_dtype="float16",
            fallback_on_error=None,
            raw_config={"matcher": {"method": "lightglue"}},
        )
        task = TileMatchTask(
            left_dom_path="left_dom.cub",
            right_dom_path="right_dom.cub",
            band=1,
            paired_window=PairedTileWindow(
                local_window=TileWindow(start_x=0, start_y=0, width=32, height=32),
                left_window=TileWindow(start_x=10, start_y=20, width=32, height=32),
                right_window=TileWindow(start_x=12, start_y=24, width=32, height=32),
            ),
            minimum_value=0.0,
            maximum_value=255.0,
            lower_percent=1.0,
            upper_percent=99.0,
            invalid_values=(0.0, -32768.0),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=32,
            valid_pixel_percent_threshold=0.25,
            invalid_pixel_radius=2,
            ratio_test=0.75,
            matcher_method="lightglue",
            max_features=2048,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            image_space="dom",
            use_gpu=True,
            gpu_batch_size=4,
            deep_match_runtime_config=runtime_config,
        )

        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[task],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=temp_dir / "deep_match_workspace",
                requested_device="cuda",
                created_at_utc="2026-05-19T12:00:00Z",
                deep_match_config_path="examples/controlnet_construct/presets/lightglue_default.json",
                deep_match_runtime_config=runtime_config,
                created_by_python="/opt/conda/envs/deep-learning/bin/python",
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            reloaded = read_deep_match_pair_manifest(manifest_path)

        record = reloaded.tasks[0]
        self.assertEqual(record.deep_match_config_path, "examples/controlnet_construct/presets/lightglue_default.json")
        self.assertEqual(record.deep_match_runtime_config["matcher_method"], "lightglue")
        self.assertEqual(record.feature_extractor_method, "superpoint")
        self.assertEqual(record.matcher_method, "lightglue")
        self.assertEqual(record.tile_window["local_window"]["width"], 32)
        self.assertEqual(record.invalid_mask_summary["invalid_pixel_radius"], 2)
        self.assertEqual(record.normalization["upper_percent"], 99.0)
        self.assertEqual(record.created_by_python, "/opt/conda/envs/deep-learning/bin/python")
        self.assertEqual(record.created_at_utc, "2026-05-19T12:00:00Z")

    def test_run_pipeline_example_routes_step_json_outputs_to_files_and_keeps_stdout_compact(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            if "--report-json" not in args:
                                raise SystemExit("missing --report-json forwarding for image_overlap.py")
                            report_json_path = Path(args[args.index("--report-json") + 1])
                            report_json_path.parent.mkdir(parents=True, exist_ok=True)
                            report_json_path.write_text(
                                json.dumps({{"pair_count": 1, "image_count": 2, "sentinel": "IMAGE_OVERLAP_REPORT_ONLY"}}),
                                encoding="utf-8",
                            )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            print(json.dumps({{"pair_count": 1, "image_count": 2, "sentinel": "SHOULD_NOT_LEAK_IMAGE_OVERLAP_JSON"}}))
                            return 0

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                print("")
                                return 0
                            if "--result-output" not in args:
                                raise SystemExit("missing --result-output forwarding")
                            result_output_path = Path(args[args.index("--result-output") + 1])
                            result_output_path.parent.mkdir(parents=True, exist_ok=True)
                            result_output_path.write_text(
                                json.dumps({{"point_count": 7, "matched_tile_count": 1, "skipped_tile_count": 0, "tile_count": 1}}),
                                encoding="utf-8",
                            )
                            Path(args[4]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[5]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            metadata_path = Path(args[args.index("--metadata-output") + 1])
                            metadata_path.parent.mkdir(parents=True, exist_ok=True)
                            metadata_path.write_text(json.dumps({{"status": "matched"}}), encoding="utf-8")
                            print(json.dumps({{"sentinel": "SHOULD_NOT_LEAK_IMAGE_MATCH_JSON"}}))
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            report_dir = Path(args[args.index("--report-dir") + 1])
                            report_dir.mkdir(parents=True, exist_ok=True)
                            (report_dir / "controlnet_batch_summary.json").write_text(
                                json.dumps({{"pair_count": 1, "total_final_control_point_count": 7, "total_dom2ori_retained_count": 7}}),
                                encoding="utf-8",
                            )
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            print(json.dumps({{"sentinel": "SHOULD_NOT_LEAK_CONTROLNET_JSON"}}))
                            return 0

                        if script_name == "controlnet_merge.py":
                            if "--report-json" not in args:
                                raise SystemExit("missing --report-json forwarding")
                            report_json_path = Path(args[args.index("--report-json") + 1])
                            report_json_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path = Path(args[3])
                            merge_script_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.write_text("#!/usr/bin/env bash\\nexit 0\\n", encoding="utf-8")
                            os.chmod(merge_script_path, 0o755)
                            report_json_path.write_text(
                                json.dumps({{"included_count": 1, "skipped_missing_count": 0, "script_path": str(merge_script_path)}}),
                                encoding="utf-8",
                            )
                            print(json.dumps({{"sentinel": "SHOULD_NOT_LEAK_MERGE_JSON"}}))
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

            image_overlap_summary_exists = (work_dir / "reports" / "image_overlap_summary.json").exists()
            image_match_result_exists = (work_dir / "match_results" / "left__right.json").exists()
            controlnet_batch_report_exists = (work_dir / "reports" / "controlnet_batch_summary.json").exists()
            controlnet_merge_report_exists = (work_dir / "reports" / "controlnet_merge_summary.json").exists()

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertNotIn("SHOULD_NOT_LEAK_IMAGE_OVERLAP_JSON", completed.stdout)
        self.assertNotIn("SHOULD_NOT_LEAK_IMAGE_MATCH_JSON", completed.stdout)
        self.assertNotIn("SHOULD_NOT_LEAK_CONTROLNET_JSON", completed.stdout)
        self.assertNotIn("SHOULD_NOT_LEAK_MERGE_JSON", completed.stdout)
        self.assertIn("image-match result json:", completed.stdout)
        self.assertIn("merge summary json:", completed.stdout)
        self.assertTrue(image_overlap_summary_exists)
        self.assertTrue(image_match_result_exists)
        self.assertTrue(controlnet_batch_report_exists)
        self.assertTrue(controlnet_merge_report_exists)

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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
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
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
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
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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

    def test_run_image_match_batch_example_forwards_cli_match_preset(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=bf")
                            print("DEEP_MATCHER_CONFIG_PATH=''")
                            return 0
                        if script_name == "image_match.py":
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            if "--matcher-method" in args:
                                raise SystemExit("preset should not forward --matcher-method")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--python",
                    str(fake_python),
                    "--match-preset-path",
                    str(expected_preset),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)

    def test_run_image_match_batch_example_does_not_forward_deep_config_with_deep_match_preset(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_official_superpoint.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=lightglue")
                            print(f"DEEP_MATCHER_CONFIG_PATH={{EXPECTED_PRESET!r}}")
                            return 0
                        if script_name == "image_match.py":
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            if "--deep-match-config-path" in args:
                                raise SystemExit("deep preset should not forward --deep-match-config-path")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--python",
                    str(fake_python),
                    "--match-preset-path",
                    str(expected_preset),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Matcher method: lightglue", completed.stdout)
        self.assertIn(f"Deep-match config path: {expected_preset}", completed.stdout)

    def test_run_image_match_batch_example_resolves_cli_match_preset_path_from_caller_cwd(self):
        with temporary_directory() as temp_dir:
            caller_dir = temp_dir / "caller"
            work_dir = temp_dir / "work"
            caller_dir.mkdir()
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            local_preset = caller_dir / "local_preset.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            local_preset.write_text("{}", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(local_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=bf")
                            print("DEEP_MATCHER_CONFIG_PATH=''")
                            return 0
                        if script_name == "image_match.py":
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--python",
                    str(fake_python),
                    "--match-preset-path",
                    "local_preset.json",
                ],
                cwd=caller_dir,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(f"Match preset path: {local_preset}", completed.stdout)

    def test_run_image_match_batch_example_ignores_config_match_preset_when_matcher_method_cli_is_explicit(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            config_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps({"ImageMatch": {"match_preset_path": str(config_preset)}}),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "match_preset_config.py":
                            raise SystemExit("config match_preset_path should not be applied")
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" in args:
                                raise SystemExit("explicit matcher method should suppress config match preset")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "bf":
                                raise SystemExit(f"unexpected matcher method: {{matcher_method}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--matcher-method",
                    "bf",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertNotIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)

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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            "opencv_num_threads": 1,
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
                                    "opencv_num_threads": image_match_config.get("opencv_num_threads", ""),
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
                            if "--opencv-num-threads" not in args:
                                raise SystemExit("missing --opencv-num-threads forwarding")
                            opencv_num_threads = args[args.index("--opencv-num-threads") + 1]
                            if opencv_num_threads != "1":
                                raise SystemExit(f"unexpected opencv thread limit: {{opencv_num_threads}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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
        self.assertIn("OpenCV thread limit: 1", completed.stdout)

    def test_run_image_match_batch_example_prefers_image_match_section_over_legacy_top_level_config_keys(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            "enable_adaptive_routing": (
                                "enable_adaptive_routing",
                                "enableAdaptiveRouting",
                                "EnableAdaptiveRouting",
                            ),
                            "adaptive_routing_profile": (
                                "adaptive_routing_profile",
                                "adaptiveRoutingProfile",
                                "AdaptiveRoutingProfile",
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
                            "deep_matcher_config_path": (
                                "deep_matcher_config_path",
                                "deepMatcherConfigPath",
                                "DeepMatcherConfigPath",
                            ),
                            "use_parallel_cpu": (
                                "use_parallel_cpu",
                                "useParallelCpu",
                                "UseParallelCpu",
                            ),
                        }}
                        for container in _config_containers(payload, order):
                            for key in candidate_keys.get(field_name, ()):
                                if key not in container:
                                    continue
                                value = container[key]
                                if value is None or value == "":
                                    continue
                                if field_name in {"use_parallel_cpu", "enable_adaptive_routing"}:
                                    if isinstance(value, bool):
                                        return "1" if value else "0"
                                    normalized = str(value).strip().lower()
                                    if normalized in {{"1", "true", "yes", "on"}}:
                                        return "1"
                                    if normalized in {{"0", "false", "no", "off"}}:
                                        return "0"
                                    raise SystemExit(f"invalid {{field_name}} value: {{value!r}}")
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
                            if threshold != "0.02":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            if "--invalid-pixel-radius" not in args:
                                raise SystemExit("missing --invalid-pixel-radius forwarding")
                            radius = args[args.index("--invalid-pixel-radius") + 1]
                            if radius != "2":
                                raise SystemExit(f"unexpected invalid pixel radius: {{radius}}")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method forwarding")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "bf":
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
        self.assertIn("Valid pixel percent threshold: 0.02", completed.stdout)
        self.assertIn("Invalid pixel radius: 2", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
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

    def test_run_pipeline_example_forwards_classic_sift_match_preset_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "preset-net",
                        "ImageMatch": {"match_preset_path": str(expected_preset)},
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=flann")
                            print("DEEP_MATCHER_CONFIG_PATH=''")
                            return 0
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            if "--matcher-method" in args:
                                raise SystemExit("preset should not forward --matcher-method")
                            if "--deep-match-config-path" in args:
                                raise SystemExit("classic SIFT preset should not forward deep-match-config-path")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        if script_name == "controlnet_stereopair.py":
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
        self.assertIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: flann", completed.stdout)

    def test_run_pipeline_example_does_not_forward_deep_config_with_deep_match_preset(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_official_superpoint.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "deep-preset-net",
                        "ImageMatch": {"match_preset_path": str(expected_preset)},
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(json.dumps({{"pair_count": 1, "image_count": 2}}), encoding="utf-8")
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=lightglue")
                            print(f"DEEP_MATCHER_CONFIG_PATH={{EXPECTED_PRESET!r}}")
                            return 0
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            if "--deep-match-config-path" in args:
                                raise SystemExit("deep preset should not forward --deep-match-config-path")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        if script_name == "controlnet_stereopair.py":
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
        self.assertIn("Matcher method: lightglue", completed.stdout)
        self.assertIn(f"Deep match config: {expected_preset}", completed.stdout)

    def test_run_pipeline_example_ignores_config_match_preset_when_matcher_method_cli_is_explicit(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            config_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "explicit-matcher-net",
                        "ImageMatch": {"match_preset_path": str(config_preset)},
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            raise SystemExit("config match_preset_path should not be applied")
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" in args:
                                raise SystemExit("explicit matcher method should suppress config match preset")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "bf":
                                raise SystemExit(f"unexpected matcher method: {{matcher_method}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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
                ),
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
                    "--matcher-method",
                    "bf",
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertNotIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)

    def test_run_pipeline_example_ignores_config_match_preset_when_deep_config_cli_is_explicit(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            config_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"
            explicit_deep_config = "examples/controlnet_construct/presets/lightglue_default.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "explicit-deep-config-net",
                        "ImageMatch": {"match_preset_path": str(config_preset)},
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    EXPLICIT_DEEP_CONFIG = {explicit_deep_config!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            raise SystemExit("config match_preset_path should not be applied")
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" in args:
                                raise SystemExit("explicit deep config should suppress config match preset")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "lightglue":
                                raise SystemExit(f"unexpected matcher method: {{matcher_method}}")
                            if "--deep-match-config-path" not in args:
                                raise SystemExit("missing --deep-match-config-path")
                            deep_config_path = args[args.index("--deep-match-config-path") + 1]
                            if deep_config_path != EXPLICIT_DEEP_CONFIG:
                                raise SystemExit(f"unexpected deep match config path: {{deep_config_path}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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
                ),
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
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-config-path",
                    explicit_deep_config,
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertNotIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: lightglue", completed.stdout)
        self.assertIn(f"Deep match config: {explicit_deep_config}", completed.stdout)

    def test_run_pipeline_example_resolves_cli_match_preset_path_repo_relative(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            raw_preset_path = "examples/controlnet_construct/presets/classic_sift_bf.json"
            expected_preset = PROJECT_ROOT / raw_preset_path
            config_relative_preset = temp_dir / raw_preset_path

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_relative_preset.parent.mkdir(parents=True, exist_ok=True)
            config_relative_preset.write_text("{}", encoding="utf-8")
            config_path.write_text(
                json.dumps({"NetworkId": "cli-preset-net"}),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}
                    CONFIG_RELATIVE_PRESET = {str(config_relative_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(
                                    f"unexpected match preset resolver args: {{args}}; config-relative={{CONFIG_RELATIVE_PRESET}}"
                                )
                            print("MATCHER_METHOD=bf")
                            print("DEEP_MATCHER_CONFIG_PATH=''")
                            return 0
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                print("")
                                return 0
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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
                ),
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
                    "--match-preset-path",
                    raw_preset_path,
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(f"Match preset path: {expected_preset}", completed.stdout)

    def test_run_pipeline_example_resolves_cli_match_preset_path_from_caller_cwd(self):
        with temporary_directory() as temp_dir:
            caller_dir = temp_dir / "caller"
            work_dir = temp_dir / "work"
            caller_dir.mkdir()
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            local_preset = caller_dir / "local_preset.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps({"NetworkId": "caller-cwd-cli-preset-net"}),
                encoding="utf-8",
            )
            local_preset.write_text("{}", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(local_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_overlap.py":
                            if "--report-json" in args:
                                report_json_path = Path(args[args.index("--report-json") + 1])
                                report_json_path.parent.mkdir(parents=True, exist_ok=True)
                                report_json_path.write_text(
                                    json.dumps({{"pair_count": 1, "image_count": 2}}),
                                    encoding="utf-8",
                                )
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0
                        if script_name == "match_preset_config.py":
                            if args != [EXPECTED_PRESET, "--shell-assignments"]:
                                raise SystemExit(f"unexpected match preset resolver args: {{args}}")
                            print("MATCHER_METHOD=bf")
                            print("DEEP_MATCHER_CONFIG_PATH=''")
                            return 0
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                print("")
                                return 0
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
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
                ),
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
                    "--match-preset-path",
                    "local_preset.json",
                    "--skip-final-merge",
                ],
                cwd=caller_dir,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(f"Match preset path: {local_preset}", completed.stdout)

    def test_run_pipeline_example_prefers_image_match_section_over_legacy_top_level_config_keys(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            "enable_adaptive_routing": (
                                "enable_adaptive_routing",
                                "enableAdaptiveRouting",
                                "EnableAdaptiveRouting",
                            ),
                            "adaptive_routing_profile": (
                                "adaptive_routing_profile",
                                "adaptiveRoutingProfile",
                                "AdaptiveRoutingProfile",
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
                            "deep_matcher_config_path": (
                                "deep_matcher_config_path",
                                "deepMatcherConfigPath",
                                "DeepMatcherConfigPath",
                            ),
                            "use_parallel_cpu": (
                                "use_parallel_cpu",
                                "useParallelCpu",
                                "UseParallelCpu",
                            ),
                        }}
                        for container in _config_containers(payload, order):
                            for key in candidate_keys.get(field_name, ()):
                                if key not in container:
                                    continue
                                value = container[key]
                                if value is None or value == "":
                                    continue
                                if field_name in {"use_parallel_cpu", "enable_adaptive_routing"}:
                                    if isinstance(value, bool):
                                        return "1" if value else "0"
                                    normalized = str(value).strip().lower()
                                    if normalized in {{"1", "true", "yes", "on"}}:
                                        return "1"
                                    if normalized in {{"0", "false", "no", "off"}}:
                                        return "0"
                                    raise SystemExit(f"invalid {{field_name}} value: {{value!r}}")
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
                            if threshold != "0.02":
                                raise SystemExit(f"unexpected threshold: {{threshold}}")
                            if "--invalid-pixel-radius" not in args:
                                raise SystemExit("missing --invalid-pixel-radius forwarding")
                            radius = args[args.index("--invalid-pixel-radius") + 1]
                            if radius != "2":
                                raise SystemExit(f"unexpected invalid pixel radius: {{radius}}")
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method forwarding")
                            matcher_method = args[args.index("--matcher-method") + 1]
                            if matcher_method != "bf":
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
        self.assertIn("Valid pixel percent threshold: 0.02", completed.stdout)
        self.assertIn("Invalid pixel radius: 2", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)
        self.assertIn("CPU parallel tile matching: enabled", completed.stdout)
        self.assertIn("CPU parallel worker limit: 3", completed.stdout)


    def test_image_match_parser_accepts_deep_matcher_method(self):
        parser = build_controlnet_stereopair_argument_parser()
        parsed = parser.parse_args(
            [
                "left_dom.cub",
                "right_dom.cub",
                "left.key",
                "right.key",
                "--matcher-method",
                "lightglue",
            ]
        )
        self.assertEqual(parsed.matcher_method, "lightglue")

    def test_image_match_config_match_preset_overrides_legacy_matcher_fields(self):
        from image_match.image_match import load_image_match_defaults_from_config

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "match_preset_path": str(preset_path),
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = load_image_match_defaults_from_config(config_path)

        self.assertEqual(defaults["match_preset_path"], str(preset_path.resolve()))
        self.assertEqual(defaults["matcher_method"], "bf")
        self.assertIsNone(defaults["deep_match_config_path"])
        self.assertEqual(defaults["max_features"], 1000)

    def test_image_match_parser_accepts_match_preset_path_cli(self):
        parser = build_controlnet_stereopair_argument_parser()
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

        parsed = parser.parse_args(
            [
                "left_dom.cub",
                "right_dom.cub",
                "left.key",
                "right.key",
                "--match-preset-path",
                str(preset_path),
            ]
        )

        self.assertEqual(parsed.match_preset_path, str(preset_path.resolve()))
        self.assertEqual(parsed.matcher_method, "flann")
        self.assertEqual(parsed.max_features, 1000)

    def test_image_match_config_match_preset_allows_cli_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"match_preset_path": str(preset_path)}}),
                encoding="utf-8",
            )

            with (
                patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
                patch.object(sys, "stdout", stdout),
            ):
                image_match_main(
                    [
                        "--config",
                        str(config_path),
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                        "--ratio-test",
                        "0.9",
                    ]
                )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_match_preset_allows_later_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

        with (
            patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
            patch.object(sys, "stdout", stdout),
        ):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--ratio-test",
                    "0.9",
                ]
            )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_match_preset_allows_earlier_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

        with (
            patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
            patch.object(sys, "stdout", stdout),
        ):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--ratio-test",
                    "0.9",
                    "--match-preset-path",
                    str(preset_path),
                ]
            )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_rejects_match_preset_with_explicit_matcher_method(self):
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--matcher-method",
                    "flann",
                ]
            )

        self.assertIn("--match-preset-path conflicts with --matcher-method", stderr.getvalue())

    def test_image_match_cli_rejects_match_preset_with_explicit_deep_config_path(self):
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--deep-match-config-path",
                    "examples/controlnet_construct/presets/lightglue_default.json",
                ]
            )

        self.assertIn("--match-preset-path conflicts with --deep-match-config-path", stderr.getvalue())

    def test_image_match_cli_match_preset_path_prefers_caller_cwd_over_repo_relative(self):
        parser = build_controlnet_stereopair_argument_parser()

        with temporary_directory() as temp_dir:
            caller_dir = temp_dir / "caller"
            local_preset = caller_dir / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
            local_preset.parent.mkdir(parents=True)
            local_preset.write_text(
                json.dumps(
                    {
                        "feature_extractor": {
                            "method": "classic_sift",
                            "max_features": 77,
                            "octave_layers": 3,
                            "contrast_threshold": 0.04,
                            "edge_threshold": 10.0,
                            "sigma": 1.6,
                        },
                        "matcher": {
                            "method": "bf",
                            "ratio_test": 0.61,
                        },
                    }
                ),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            try:
                os.chdir(caller_dir)
                parsed = parser.parse_args(
                    [
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                        "--match-preset-path",
                        "examples/controlnet_construct/presets/classic_sift_bf.json",
                    ]
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(parsed.match_preset_path, str(local_preset.resolve()))
        self.assertEqual(parsed.max_features, 77)
        self.assertEqual(parsed.ratio_test, 0.61)

    def test_image_match_parser_rejects_invalid_match_preset_path_cleanly(self):
        parser = build_controlnet_stereopair_argument_parser()
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    "does-not-exist.json",
                ]
            )

    def test_pipeline_forwards_deep_matcher_method(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()

        with (
            patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
            patch.object(sys, "stdout", stdout),
        ):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--matcher-method",
                    "lightglue",
                ]
            )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "lightglue")

    def test_pipeline_forwards_config_relative_adaptive_routing_deep_presets_from_config(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_dir = temp_dir / "configs"
            preset_dir = config_dir / "presets"
            config_dir.mkdir()
            preset_dir.mkdir()
            config_path = config_dir / "controlnet_config.json"
            (preset_dir / "lightglue_default.json").write_text("{}", encoding="utf-8")
            (preset_dir / "lightglue_high_recall.json").write_text("{}", encoding="utf-8")
            (preset_dir / "loftr_default.json").write_text("{}", encoding="utf-8")
            expected_preset_map = {
                "lightglue": str(preset_dir / "lightglue_default.json"),
                "lightglue_high_recall": str(preset_dir / "lightglue_high_recall.json"),
                "loftr": str(preset_dir / "loftr_default.json"),
            }
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "adaptive_routing_deep_presets": {
                                "lightglue": "presets/lightglue_default.json",
                                "lightglue_high_recall": "presets/lightglue_high_recall.json",
                                "loftr": "presets/loftr_default.json",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
                patch.object(sys, "stdout", stdout),
            ):
                image_match_main(
                    [
                        "--config",
                        str(config_path),
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                    ]
                )

        self.assertEqual(
            match_mock.call_args.kwargs["adaptive_routing_deep_presets"],
            expected_preset_map,
        )

    def test_pipeline_forwards_repo_relative_adaptive_routing_deep_presets_from_config(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            expected_preset_map = {
                "lightglue": str(PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"),
                "lightglue_high_recall": str(PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_high_recall.json"),
                "loftr": str(PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "loftr_default.json"),
            }

            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "adaptive_routing_deep_presets": {
                                "lightglue": "examples/controlnet_construct/presets/lightglue_default.json",
                                "lightglue_high_recall": "examples/controlnet_construct/presets/lightglue_high_recall.json",
                                "loftr": "examples/controlnet_construct/presets/loftr_default.json",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value=fake_result) as match_mock,
                patch.object(sys, "stdout", stdout),
            ):
                image_match_main(
                    [
                        "--config",
                        str(config_path),
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                    ]
                )

        self.assertEqual(
            match_mock.call_args.kwargs["adaptive_routing_deep_presets"],
            expected_preset_map,
        )

    def test_adaptive_cascade_steps_keep_only_prior_selected_matcher_without_presets(self):
        from controlnet_construct.image_match import _adaptive_cascade_steps_from_summary

        steps = _adaptive_cascade_steps_from_summary(
            {
                "status": "routed",
                "selected_initial_matcher": "flann",
                "selected_deep_match_config_path": None,
            },
            initial_matcher="flann",
            initial_deep_match_config_path=None,
            adaptive_routing_deep_presets=None,
        )

        self.assertEqual(
            steps,
            (
                {"matcher_method": "flann", "deep_match_config_path": None},
            ),
        )

    def test_match_dom_pair_rejects_initial_routed_deep_preset_matcher_conflict(self):
        image_match_module = importlib.import_module("controlnet_construct.image_match")

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def sample_count(self):
                return 64

            def line_count(self):
                return 64

            def band_count(self):
                return 1

            def pixel_type(self):
                return None

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        low_resolution_summary = {
            "left_low_resolution_dom": "left_preview.cub",
            "right_low_resolution_dom": "right_preview.cub",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
        }
        routed_summary = {
            "enabled": True,
            "status": "routed",
            "selected_initial_matcher": "lightglue",
            "selected_deep_match_config_path": "preset_loftr.json",
        }
        routed_runtime_config = SimpleNamespace(
            matcher_method="loftr",
            raw_config={"matcher": {"method": "loftr"}},
        )

        with (
            patch.object(image_match_module, "build_image_backend", return_value=SimpleNamespace(space="dom")),
            patch.object(image_match_module.ip, "Cube", side_effect=[FakeCube(), FakeCube()]),
            patch.object(
                image_match_module,
                "_estimate_low_resolution_projected_offset",
                return_value=low_resolution_summary,
            ),
            patch.object(
                image_match_module,
                "_resolve_adaptive_route_for_pair",
                return_value=("lightglue", routed_summary),
            ),
            patch.object(
                image_match_module,
                "_resolve_deep_match_runtime_config",
                return_value=routed_runtime_config,
            ),
            patch.object(
                image_match_module,
                "prepare_dom_pair_for_matching",
                side_effect=AssertionError("compatibility validation should stop before preparation"),
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "matcher_method 'lightglue' conflicts with deep_match_config matcher.method 'loftr'",
            ):
                image_match_module.match_dom_pair(
                    "left.cub",
                    "right.cub",
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                )

    def test_match_dom_pair_initial_routed_flann_export_uses_selected_deep_preset_matcher(self):
        image_match_module = importlib.import_module("controlnet_construct.image_match")

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def sample_count(self):
                return 64

            def line_count(self):
                return 64

            def band_count(self):
                return 1

            def pixel_type(self):
                return None

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        low_resolution_summary = {
            "left_low_resolution_dom": "left_preview.cub",
            "right_low_resolution_dom": "right_preview.cub",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
        }
        routed_summary = {
            "enabled": True,
            "status": "routed",
            "selected_initial_matcher": "lightglue",
            "selected_deep_match_config_path": "preset_lightglue.json",
        }
        routed_runtime_config = SimpleNamespace(
            matcher_method="lightglue",
            raw_config={"matcher": {"method": "lightglue"}},
        )
        ready_preparation = SimpleNamespace(
            status="ready",
            reason="",
            left=SimpleNamespace(offset_sample=0, offset_line=0),
            right=SimpleNamespace(offset_sample=0, offset_line=0),
            shared_width=32,
            shared_height=32,
        )

        def fake_export_deep_match_pair_tasks(*_args, **kwargs):
            self.assertEqual(kwargs["matcher_method"], "lightglue")
            self.assertIs(kwargs["deep_match_runtime_config"], routed_runtime_config)
            raise RuntimeError("stop after initial routed export assertion")

        with (
            patch.object(image_match_module, "build_image_backend", return_value=SimpleNamespace(space="dom")),
            patch.object(image_match_module.ip, "Cube", side_effect=[FakeCube(), FakeCube()]),
            patch.object(
                image_match_module,
                "_estimate_low_resolution_projected_offset",
                return_value=low_resolution_summary,
            ),
            patch.object(
                image_match_module,
                "_resolve_adaptive_route_for_pair",
                return_value=("lightglue", routed_summary),
            ),
            patch.object(
                image_match_module,
                "_resolve_deep_match_runtime_config",
                return_value=routed_runtime_config,
            ),
            patch.object(
                image_match_module,
                "prepare_dom_pair_for_matching",
                return_value=ready_preparation,
            ),
            patch.object(image_match_module, "_paired_windows", return_value=[object()]),
            patch.object(
                image_match_module,
                "_export_deep_match_pair_tasks",
                side_effect=fake_export_deep_match_pair_tasks,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop after initial routed export assertion"):
                image_match_module.match_dom_pair(
                    "left.cub",
                    "right.cub",
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    deep_match_mode="export",
                )

    def test_match_dom_pair_export_rejects_non_deep_adaptive_route_without_fallback(self):
        image_match_module = importlib.import_module("controlnet_construct.image_match")

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def sample_count(self):
                return 64

            def line_count(self):
                return 64

            def band_count(self):
                return 1

            def pixel_type(self):
                return None

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        low_resolution_summary = {
            "left_low_resolution_dom": "left_preview.cub",
            "right_low_resolution_dom": "right_preview.cub",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
        }
        routed_summary = {
            "enabled": True,
            "status": "routed",
            "selected_initial_matcher": "flann",
            "selected_deep_match_config_path": None,
        }
        ready_preparation = SimpleNamespace(
            status="ready",
            reason="",
            left=SimpleNamespace(offset_sample=0, offset_line=0),
            right=SimpleNamespace(offset_sample=0, offset_line=0),
            shared_width=32,
            shared_height=32,
        )

        with (
            patch.object(image_match_module, "build_image_backend", return_value=SimpleNamespace(space="dom")),
            patch.object(image_match_module.ip, "Cube", side_effect=[FakeCube(), FakeCube()]),
            patch.object(
                image_match_module,
                "_estimate_low_resolution_projected_offset",
                return_value=low_resolution_summary,
            ),
            patch.object(
                image_match_module,
                "_resolve_adaptive_route_for_pair",
                return_value=("flann", routed_summary),
            ),
            patch.object(
                image_match_module,
                "prepare_dom_pair_for_matching",
                return_value=ready_preparation,
            ),
            patch.object(image_match_module, "_paired_windows", return_value=[object()]),
            patch.object(
                image_match_module,
                "_export_deep_match_pair_tasks",
            ) as export_mock,
        ):
            with self.assertRaisesRegex(ValueError, "deep_match_mode='export' currently supports only deep matcher"):
                image_match_module.match_dom_pair(
                    "left.cub",
                    "right.cub",
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    adaptive_routing_deep_presets={"lightglue": "preset_lightglue.json"},
                    deep_match_mode="export",
                )
        export_mock.assert_not_called()
        self.assertEqual(routed_summary["selected_initial_matcher"], "flann")

    def test_match_dom_pair_adaptive_quality_rejection_records_no_post_match_fallback(self):
        image_match_module = importlib.import_module("controlnet_construct.image_match")
        from image_match.adaptive_routing import MatchQualityReport
        from image_match.dom_prepare import CropWindow, PairPreparationMetadata

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def sample_count(self):
                return 64

            def line_count(self):
                return 64

            def band_count(self):
                return 1

            def pixel_type(self):
                return None

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        low_resolution_summary = {
            "left_low_resolution_dom": "left_preview.cub",
            "right_low_resolution_dom": "right_preview.cub",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
        }
        routed_summary = {
            "enabled": True,
            "status": "routed",
            "selected_initial_matcher": "bf",
            "selected_deep_match_config_path": None,
        }
        left_window = CropWindow(
            path="left.cub",
            start_sample=1,
            start_line=1,
            width=32,
            height=32,
            offset_sample=0,
            offset_line=0,
            projected_min_x=0.0,
            projected_max_x=32.0,
            projected_min_y=0.0,
            projected_max_y=32.0,
            clipped_by_image_bounds=False,
        )
        right_window = CropWindow(
            path="right.cub",
            start_sample=1,
            start_line=1,
            width=32,
            height=32,
            offset_sample=0,
            offset_line=0,
            projected_min_x=0.0,
            projected_max_x=32.0,
            projected_min_y=0.0,
            projected_max_y=32.0,
            clipped_by_image_bounds=False,
        )
        ready_preparation = PairPreparationMetadata(
            left=left_window,
            right=right_window,
            overlap_min_x=0.0,
            overlap_max_x=32.0,
            overlap_min_y=0.0,
            overlap_max_y=32.0,
            expanded_min_x=0.0,
            expanded_max_x=32.0,
            expanded_min_y=0.0,
            expanded_max_y=32.0,
            projected_delta_x=0.0,
            projected_delta_y=0.0,
            expand_pixels=0,
            min_overlap_size=1,
            shared_width=32,
            shared_height=32,
            left_resolution=1.0,
            right_resolution=1.0,
            reference_resolution=1.0,
            gsd_ratio=1.0,
            status="ready",
            reason="",
        )
        rejected_quality = MatchQualityReport(
            inlier_count=0,
            total_match_count=0,
            inlier_ratio=0.0,
            coverage=0.0,
            residual_summary={"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0},
            quality_score=0.0,
            accepted=False,
            rejection_reasons=("insufficient_inlier_count",),
        )
        run_tile_call_count = 0

        def fake_run_serial_tile_match_tasks(*_args, **_kwargs):
            nonlocal run_tile_call_count
            run_tile_call_count += 1
            if run_tile_call_count > 1:
                raise AssertionError("adaptive routing must not rerun tiles through fallback matchers")
            return TileMatchBatchResult(results=[])

        with (
            patch.object(image_match_module, "build_image_backend", return_value=SimpleNamespace(space="dom")),
            patch.object(image_match_module.ip, "Cube", side_effect=[FakeCube(), FakeCube()]),
            patch.object(
                image_match_module,
                "_estimate_low_resolution_projected_offset",
                return_value=low_resolution_summary,
            ),
            patch.object(
                image_match_module,
                "_resolve_adaptive_route_for_pair",
                return_value=("bf", routed_summary),
            ),
            patch.object(
                image_match_module,
                "prepare_dom_pair_for_matching",
                return_value=ready_preparation,
            ),
            patch.object(image_match_module, "_paired_windows", return_value=[object()]),
            patch.object(
                image_match_module,
                "_run_serial_tile_match_tasks",
                side_effect=fake_run_serial_tile_match_tasks,
            ),
            patch.object(
                image_match_module,
                "_quality_report_for_tile_results",
                return_value=rejected_quality,
            ),
            patch.object(
                image_match_module,
                "decide_post_match_action",
                return_value={
                    "accepted": False,
                    "fallback_used": False,
                    "next_matcher": None,
                    "selected_matcher": "bf",
                    "stop_reason": "quality_insufficient_no_fallback",
                    "rejection_reasons": ("insufficient_inlier_count",),
                },
            ) as decision_mock,
            patch.object(
                image_match_module,
                "_resolve_deep_match_runtime_config",
                side_effect=AssertionError("adaptive routing must not resolve fallback deep presets"),
            ),
        ):
            _left_key_file, _right_key_file, summary = image_match_module.match_dom_pair(
                "left.cub",
                "right.cub",
                matcher_method="bf",
                enable_adaptive_routing=True,
                adaptive_routing_deep_presets={
                    "loftr": "cascade_loftr.json",
                },
            )

        self.assertEqual(run_tile_call_count, 1)
        self.assertEqual(decision_mock.call_count, 1)
        adaptive_summary = summary["adaptive_routing"]
        self.assertTrue(adaptive_summary["no_post_match_fallback"])
        self.assertTrue(adaptive_summary["cascade_disabled"])
        self.assertEqual(adaptive_summary["cascade_plan"], ["bf"])
        self.assertEqual(adaptive_summary["final_decision"]["stop_reason"], "quality_insufficient_no_fallback")

    def test_batch_wrapper_accepts_lightglue_in_help_text(self):
        content = Path("examples/controlnet_construct/run_image_match_batch_example.sh").read_text(encoding="utf-8")
        self.assertIn("lightglue", content)
        self.assertIn("superglue", content)
        self.assertIn("loftr", content)

    def test_run_image_match_batch_example_forwards_deep_match_export_and_writes_manifest_summary(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_match.py":
                            if "--deep-match-mode" not in args:
                                raise SystemExit("missing --deep-match-mode forwarding")
                            mode = args[args.index("--deep-match-mode") + 1]
                            if mode != "export":
                                raise SystemExit(f"unexpected deep-match mode: {{mode}}")
                            if "--deep-match-temp-root-dir" not in args:
                                raise SystemExit("missing --deep-match-temp-root-dir forwarding")
                            metadata_path = Path(args[args.index("--metadata-output") + 1])
                            metadata_path.parent.mkdir(parents=True, exist_ok=True)
                            metadata_path.write_text(
                                json.dumps(
                                    {{
                                        "status": "exported_for_deep_learning",
                                        "point_count": 0,
                                        "deep_match_export": {{
                                            "manifest_path": "work/deep_match_workspaces/left__right/tasks.json",
                                            "workspace_root": "work/deep_match_workspaces/left__right",
                                            "pair_id": "left__right",
                                            "exported_task_count": 1,
                                        }},
                                    }}
                                ),
                                encoding="utf-8",
                            )
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--python",
                    str(fake_python),
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-mode",
                    "export",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary_path = work_dir / "deep_match_manifests.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertIn("Deep-match mode: export", completed.stdout)
        self.assertEqual(summary["deep_match_mode"], "export")
        self.assertEqual(summary["pairs"][0]["pair_tag"], "left__right")
        self.assertEqual(summary["pairs"][0]["manifest_path"], "work/deep_match_workspaces/left__right/tasks.json")

    def test_run_image_match_batch_example_forwards_deep_match_config_path_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_resolved_config = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

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
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "deep_matcher_config_path": image_match_config.get("deep_matcher_config_path", ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--matcher-method" not in args:
                                raise SystemExit("missing --matcher-method")
                            if args[args.index("--matcher-method") + 1] != "lightglue":
                                raise SystemExit("unexpected matcher method")
                            if "--deep-match-config-path" not in args:
                                raise SystemExit("missing --deep-match-config-path")
                            config_value = args[args.index("--deep-match-config-path") + 1]
                            if config_value != {str(expected_resolved_config)!r}:
                                raise SystemExit(f"unexpected deep config: {{config_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(f"Deep-match config path: {expected_resolved_config}", completed.stdout)

    def test_run_image_match_batch_example_cli_deep_match_config_path_overrides_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

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
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "deep_matcher_config_path": image_match_config.get("deep_matcher_config_path", ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--deep-match-config-path" not in args:
                                raise SystemExit("missing --deep-match-config-path")
                            config_value = args[args.index("--deep-match-config-path") + 1]
                            if config_value != "examples/controlnet_construct/presets/loftr_default.json":
                                raise SystemExit(f"unexpected deep config: {{config_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--deep-match-config-path",
                    "examples/controlnet_construct/presets/loftr_default.json",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Deep-match config path: examples/controlnet_construct/presets/loftr_default.json", completed.stdout)

    def test_run_image_match_batch_example_resolves_config_relative_deep_match_config_path(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            config_dir = temp_dir / "configs"
            preset_dir = config_dir / "presets"
            work_dir.mkdir()
            preset_dir.mkdir(parents=True)

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = config_dir / "controlnet_config.json"
            expected_resolved_config = preset_dir / "lightglue_default.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            expected_resolved_config.write_text(
                (PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import sys
                    from pathlib import Path

                    EXPECTED_CONFIG = {str(expected_resolved_config)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

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
                                    "matcher_method": image_match_config.get("matcher_method", ""),
                                    "deep_matcher_config_path": image_match_config.get("deep_matcher_config_path", ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--deep-match-config-path" not in args:
                                raise SystemExit("missing --deep-match-config-path")
                            config_value = args[args.index("--deep-match-config-path") + 1]
                            if config_value != EXPECTED_CONFIG:
                                raise SystemExit(f"unexpected resolved deep config: {{config_value}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn(f"Deep-match config path: {expected_resolved_config}", completed.stdout)

    def test_run_image_match_batch_example_forwards_adaptive_routing_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enable_adaptive_routing": True,
                            "adaptive_routing_profile": "relaxed",
                        }
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

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
                                    "enable_adaptive_routing": "1" if image_match_config.get("enable_adaptive_routing") is True else ("0" if image_match_config.get("enable_adaptive_routing") is False else ""),
                                    "adaptive_routing_profile": image_match_config.get("adaptive_routing_profile", ""),
                                }}
                                print(mapping.get(field_name, ""))
                                return 0
                            if "--adaptive-routing" not in args:
                                raise SystemExit("missing --adaptive-routing forwarding")
                            if "--adaptive-routing-profile" not in args:
                                raise SystemExit("missing --adaptive-routing-profile forwarding")
                            profile = args[args.index("--adaptive-routing-profile") + 1]
                            if profile != "relaxed":
                                raise SystemExit(f"unexpected adaptive routing profile: {{profile}}")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Adaptive routing: enabled", completed.stdout)
        self.assertIn("Adaptive routing profile: relaxed", completed.stdout)

    def test_run_pipeline_example_resolves_deep_match_config_path_and_export_mode_stops_after_manifest_export(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "deep-match-export-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "ImageMatch": {
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        },
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
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
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]

                        if script_name == "image_overlap.py":
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            if "--report-json" in args:
                                report_path = Path(args[args.index("--report-json") + 1])
                                report_path.parent.mkdir(parents=True, exist_ok=True)
                                report_path.write_text(json.dumps({{"pair_count": 1, "image_count": 2}}), encoding="utf-8")
                            return 0

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--deep-match-config-path" not in args:
                                raise SystemExit("missing --deep-match-config-path forwarding")
                            deep_config = args[args.index("--deep-match-config-path") + 1]
                            expected_deep_config = str({str(PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json")!r})
                            if deep_config != expected_deep_config:
                                raise SystemExit(f"unexpected resolved deep config: {{deep_config}}")
                            if "--deep-match-mode" not in args:
                                raise SystemExit("missing --deep-match-mode forwarding")
                            if args[args.index("--deep-match-mode") + 1] != "export":
                                raise SystemExit("pipeline did not forward export mode")
                            result_path = Path(args[args.index("--result-output") + 1])
                            result_path.parent.mkdir(parents=True, exist_ok=True)
                            result_path.write_text(
                                json.dumps(
                                    {{
                                        "status": "exported_for_deep_learning",
                                        "point_count": 0,
                                        "deep_match_export": {{
                                            "manifest_path": "work/deep_match_workspaces/left__right/tasks.json",
                                            "workspace_root": "work/deep_match_workspaces/left__right",
                                            "pair_id": "left__right",
                                            "exported_task_count": 1,
                                        }},
                                    }}
                                ),
                                encoding="utf-8",
                            )
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            raise SystemExit("export mode should stop before controlnet_stereopair.py")

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
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
                    "--deep-match-mode",
                    "export",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary_path = work_dir / "reports" / "deep_match_manifests.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertIn("Pipeline stopped after image_match_batch", completed.stdout)
        self.assertEqual(summary["deep_match_mode"], "export")
        self.assertEqual(summary["pairs"][0]["manifest_path"], "work/deep_match_workspaces/left__right/tasks.json")

    def test_controlnet_stereopair_parser_recognizes_from_ori_match_command(self):
        parser = importlib.import_module("controlnet_construct.controlnet_stereopair").build_argument_parser()
        parsed = parser.parse_args(
            [
                "from-ori-match",
                "left.cub",
                "right.cub",
                "config.json",
                "output.net",
            ]
        )

        self.assertEqual(parsed.command, "from-ori-match")
        self.assertEqual(parsed.left_cube, "left.cub")
        self.assertEqual(parsed.right_cube, "right.cub")
        self.assertEqual(parsed.config, "config.json")
        self.assertEqual(parsed.output_net, "output.net")

    def test_controlnet_stereopair_parser_accepts_from_ori_match_matcher_and_gpu_flags(self):
        parser = importlib.import_module("controlnet_construct.controlnet_stereopair").build_argument_parser()
        parsed = parser.parse_args(
            [
                "from-ori-match",
                "left.cub",
                "right.cub",
                "config.json",
                "output.net",
                "--matcher-method",
                "loftr",
                "--use-gpu",
                "--gpu-batch-size",
                "8",
            ]
        )
        self.assertEqual(parsed.command, "from-ori-match")
        self.assertEqual(parsed.matcher_method, "loftr")
        self.assertTrue(parsed.use_gpu)
        self.assertEqual(parsed.gpu_batch_size, 8)

    def test_controlnet_stereopair_parser_accepts_from_ori_match_adaptive_and_deep_config(self):
        parser = importlib.import_module("controlnet_construct.controlnet_stereopair").build_argument_parser()
        parsed = parser.parse_args(
            [
                "from-ori-match",
                "left.cub",
                "right.cub",
                "config.json",
                "out.net",
                "--adaptive-routing",
                "--adaptive-routing-profile",
                "strict",
                "--deep-match-config-path",
                "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "--adaptive-routing-deep-preset",
                "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "--adaptive-routing-deep-preset",
                "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
            ]
        )

        self.assertEqual(parsed.command, "from-ori-match")
        self.assertTrue(parsed.enable_adaptive_routing)
        self.assertEqual(parsed.adaptive_routing_profile, "strict")
        self.assertEqual(
            parsed.deep_match_config_path,
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        self.assertEqual(
            parsed.adaptive_routing_deep_preset,
            [
                "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
            ],
        )

    def test_controlnet_stereopair_main_from_ori_match_forwards_adaptive_and_deep_options(self):
        with temporary_directory() as temp_dir:
            left = temp_dir / "left.cub"
            right = temp_dir / "right.cub"
            config = temp_dir / "config.json"
            output_net = temp_dir / "out.net"
            left.write_text("left", encoding="utf-8")
            right.write_text("right", encoding="utf-8")
            config.write_text(
                json.dumps({"NetworkId": "raw_adaptive", "TargetName": "Moon", "UserName": "tester"}),
                encoding="utf-8",
            )

            with patch(
                "controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files",
                return_value={
                    "status": "matched",
                    "point_count": 4,
                    "adaptive_routing": {"status": "routed"},
                    "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                    "left_output_key": str(temp_dir / "left.key"),
                    "right_output_key": str(temp_dir / "right.key"),
                },
            ) as match_mock, patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                return_value={"point_count": 4, "output_net": str(output_net)},
            ):
                controlnet_stereopair_main(
                    [
                        "from-ori-match",
                        str(left),
                        str(right),
                        str(config),
                        str(output_net),
                        "--adaptive-routing",
                        "--adaptive-routing-profile",
                        "strict",
                        "--deep-match-config-path",
                        "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "--adaptive-routing-deep-preset",
                        "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "--adaptive-routing-deep-preset",
                        "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
                    ]
                )

        kwargs = match_mock.call_args.kwargs
        self.assertTrue(kwargs["enable_adaptive_routing"])
        self.assertEqual(kwargs["adaptive_routing_profile"], "strict")
        self.assertEqual(
            kwargs["deep_match_config_path"],
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        self.assertEqual(
            kwargs["adaptive_routing_deep_presets"],
            {
                "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
            },
        )

    def test_controlnet_stereopair_main_from_ori_match_dispatches_matching_and_controlnet(self):
        fake_config = ControlNetConfig(network_id="N", target_name="Mars", user_name="tester")
        fake_match_result = {
            "left_output_key": "left_out.key",
            "right_output_key": "right_out.key",
            "status": "matched",
        }
        fake_controlnet_result = {"point_count": 3, "measure_count": 6}
        stdout = io.StringIO()

        with (
            patch(
                "controlnet_construct.controlnet_stereopair.read_controlnet_config",
                return_value=fake_config,
            ),
            patch(
                "controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files",
                return_value=fake_match_result,
            ) as match_mock,
            patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                return_value=fake_controlnet_result,
            ) as controlnet_mock,
            patch.object(sys, "stdout", stdout),
        ):
            controlnet_stereopair_main(
                [
                    "from-ori-match",
                    "left.cub",
                    "right.cub",
                    "config.json",
                    "output.net",
                    "--left-output-key",
                    "left_out.key",
                    "--right-output-key",
                    "right_out.key",
                    "--matcher-method",
                    "loftr",
                    "--use-gpu",
                ]
            )

        self.assertEqual(match_mock.call_args.args[0:4], ("left.cub", "right.cub", Path("left_out.key"), Path("right_out.key")))
        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "loftr")
        self.assertTrue(match_mock.call_args.kwargs["use_gpu"])
        self.assertEqual(
            controlnet_mock.call_args.args[0:6],
            (Path("left_out.key"), Path("right_out.key"), "left.cub", "right.cub", fake_config, "output.net"),
        )
        self.assertTrue(controlnet_mock.call_args.kwargs["pvl_format"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["mode"], "from-ori-match")
        self.assertEqual(payload["match"], fake_match_result)
        self.assertEqual(payload["controlnet"], fake_controlnet_result)

    def test_controlnet_from_ori_match_writes_json_safe_route_audit(self):
        fake_match_summary = {
            "status": "matched",
            "point_count": 7,
            "matcher": {
                "matcher_method_requested": "flann",
                "matcher_method_effective": "lightglue",
                "ratio_test": 0.75,
            },
            "adaptive_routing_profile": "balanced",
            "adaptive_routing": {
                "status": "routed",
                "selected_initial_matcher": "lightglue",
                "selected_final_matcher": "flann",
                "fallback_chain": ["lightglue", "flann", "bf"],
                "cascade_steps": [
                    {"matcher": "lightglue", "status": "failed_quality_gate"},
                    {"matcher": "flann", "status": "accepted"},
                ],
                "match_quality": {"accepted": True, "inlier_count": 7},
                "final_decision": "accepted",
            },
            "deep_match_config_path": "presets/lightglue_official_superpoint.json",
        }
        fake_controlnet = {
            "output_path": "pair.net",
            "point_count": 7,
            "measure_count": 14,
        }
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            report_path = temp_dir / "pair.summary.json"
            output_net = temp_dir / "pair.net"
            config_path.write_text(
                json.dumps({"NetworkId": "route_unit", "TargetName": "Mars", "UserName": "unit"}) + "\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files",
                    return_value=("left-key-object", "right-key-object", fake_match_summary),
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                    return_value=fake_controlnet,
                ),
                patch.object(sys, "stdout", stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-ori-match",
                        "left.cub",
                        "right.cub",
                        str(config_path),
                        str(output_net),
                        "--report-path",
                        str(report_path),
                        "--adaptive-routing",
                    ]
                )

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["mode"], "from-ori-match")
        self.assertEqual(report["match"]["point_count"], 7)
        self.assertEqual(report["routing_audit"]["requested_matcher"], "flann")
        self.assertEqual(report["routing_audit"]["effective_matcher"], "lightglue")
        self.assertEqual(report["routing_audit"]["adaptive_routing_profile"], "balanced")
        self.assertEqual(report["routing_audit"]["selected_initial_matcher"], "lightglue")
        self.assertEqual(report["routing_audit"]["selected_final_matcher"], "flann")
        self.assertEqual(report["routing_audit"]["match_count"], 7)
        json.dumps(json.loads(stdout.getvalue()))

    def test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags(self):
        parser = build_controlnet_stereopair_parser()
        parsed = parser.parse_args(
            [
                "from-dom-match",
                "left_dom.cub",
                "right_dom.cub",
                "left.cub",
                "right.cub",
                "config.json",
                "pair.net",
                "--adaptive-routing",
                "--adaptive-routing-profile",
                "fast",
                "--adaptive-routing-deep-preset",
                "loftr=presets/loftr_external_outdoor.json",
                "--matcher-method",
                "flann",
            ]
        )

        self.assertEqual(parsed.command, "from-dom-match")
        self.assertTrue(parsed.enable_adaptive_routing)
        self.assertEqual(parsed.adaptive_routing_profile, "fast")
        self.assertEqual(parsed.adaptive_routing_deep_preset, ["loftr=presets/loftr_external_outdoor.json"])
        self.assertEqual(parsed.matcher_method, "flann")

    def test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report(self):
        fake_result = {
            "mode": "from-dom-match",
            "routing_audit": {"selected_final_matcher": "loftr", "match_count": 9},
            "match": {"point_count": 9},
            "controlnet": {"controlnet": {"point_count": 9}},
        }
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "config.json"
            report_path = temp_dir / "pair.summary.json"
            output_net = temp_dir / "pair.net"
            config_path.write_text(
                json.dumps({"NetworkId": "dom_match_cli", "TargetName": "Mars", "UserName": "unit"}) + "\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_match_stereo_pair",
                    return_value=fake_result,
                ) as build_mock,
                patch.object(sys, "stdout", stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-dom-match",
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.cub",
                        "right.cub",
                        str(config_path),
                        str(output_net),
                        "--report-path",
                        str(report_path),
                        "--adaptive-routing",
                        "--adaptive-routing-profile",
                        "fast",
                        "--adaptive-routing-deep-preset",
                        "loftr=presets/loftr_external_outdoor.json",
                    ]
                )

            report = json.loads(report_path.read_text(encoding="utf-8"))
            expected_config = read_controlnet_config(config_path)

        self.assertEqual(report["mode"], "from-dom-match")
        self.assertEqual(report["routing_audit"]["selected_final_matcher"], "loftr")
        self.assertEqual(
            build_mock.call_args.args[:6],
            ("left_dom.cub", "right_dom.cub", "left.cub", "right.cub", expected_config, Path(output_net)),
        )
        self.assertTrue(build_mock.call_args.kwargs["enable_adaptive_routing"])
        self.assertEqual(build_mock.call_args.kwargs["adaptive_routing_profile"], "fast")
        self.assertEqual(
            build_mock.call_args.kwargs["adaptive_routing_deep_presets"],
            {"loftr": "presets/loftr_external_outdoor.json"},
        )
        json.dumps(json.loads(stdout.getvalue()))

    def test_run_pipeline_example_forwards_adaptive_routing_and_new_matching_options_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            dom_source_metadata_csv = work_dir / "reduced_selected_pair_paths.csv"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            dom_source_metadata_csv.write_text("dom_cube,echo_cal_cube\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "timing-net",
                        "TargetName": "Mars",
                        "UserName": "copilot",
                        "PointIdPrefix": "TMP",
                        "ImageMatch": {
                            "invalid_pixel_radius": 3,
                            "enable_adaptive_routing": True,
                            "adaptive_routing_profile": "strict",
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
                        "                'enable_adaptive_routing': '1' if image_match_config.get('enable_adaptive_routing') else ('0' if image_match_config.get('enable_adaptive_routing') is False else ''),",
                        "                'adaptive_routing_profile': image_match_config.get('adaptive_routing_profile', ''),",
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
                        "        if '--adaptive-routing' not in args:",
                        "            raise SystemExit('missing --adaptive-routing forwarding')",
                        "        if '--adaptive-routing-profile' not in args:",
                        "            raise SystemExit('missing --adaptive-routing-profile forwarding')",
                        "        routing_profile = args[args.index('--adaptive-routing-profile') + 1]",
                        "        if routing_profile != 'strict':",
                        "            raise SystemExit(f'unexpected adaptive routing profile: {routing_profile}')",
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
                        "        if '--dom-source-metadata-csv' not in args:",
                        "            raise SystemExit('missing --dom-source-metadata-csv')",
                        "        source_metadata_csv = args[args.index('--dom-source-metadata-csv') + 1]",
                        f"        if source_metadata_csv != {str(dom_source_metadata_csv)!r}:",
                        "            raise SystemExit(f'unexpected DOM source metadata CSV: {source_metadata_csv}')",
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
                    "--dom-source-metadata-csv",
                    str(dom_source_metadata_csv),
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Invalid pixel radius: 3", completed.stdout)
        self.assertIn("Adaptive routing: enabled", completed.stdout)
        self.assertIn("Adaptive routing profile: strict", completed.stdout)
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
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
                            if "--report-json" not in args:
                                raise SystemExit("missing --report-json for merge_control_measure.py")
                            if "--decimals" not in args:
                                raise SystemExit("missing --decimals for merge_control_measure.py")
                            decimals = args[args.index("--decimals") + 1]
                            if decimals != "2":
                                raise SystemExit(f"unexpected post-merge decimals: {{decimals}}")
                            output_path = Path(args[2])
                            report_json_path = Path(args[args.index("--report-json") + 1])
                            report_json_path.parent.mkdir(parents=True, exist_ok=True)
                            report_json_path.write_text(
                                json.dumps({{"output_control_net": str(output_path), "point_count_after": 1}}),
                                encoding="utf-8",
                            )
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text("post-merged-net\\n", encoding="utf-8")
                            print(json.dumps({{"sentinel": "SHOULD_NOT_LEAK_POST_MERGE_JSON"}}))
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
            post_merge_report_path = work_dir / "reports" / "merge_control_measure_summary.json"
            post_merge_report_exists = post_merge_report_path.exists()

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn("Post-merge ControlNet deduplication: enabled", completed.stdout)
            self.assertIn("START merge_control_measure", completed.stdout)
            self.assertNotIn("SHOULD_NOT_LEAK_POST_MERGE_JSON", completed.stdout)
            self.assertTrue(post_merge_output.exists())
            self.assertTrue(post_merge_report_exists)
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

    def test_controlnet_stereopair_cli_from_dom_omits_failure_details_from_stdout_by_default(self):
        fake_result = {
            "mode": "from-dom",
            "left_conversion": {
                "output_count": 1,
                "failure_count": 2,
                "failures": [
                    {"reason": "dom_lookup_failed", "sample": 1.0},
                    {"reason": "original_projection_failed", "sample": 2.0},
                ],
            },
            "right_conversion": {
                "output_count": 1,
                "failure_count": 1,
                "failures": [
                    {"reason": "paired_point_dropped", "sample": 3.0},
                ],
            },
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

            stdout = io.StringIO()
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                    return_value=fake_result,
                ),
                redirect_stdout(stdout),
            ):
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
                    ]
                )

        stdout_payload = json.loads(stdout.getvalue())
        self.assertNotIn("failures", stdout_payload["left_conversion"])
        self.assertNotIn("failures", stdout_payload["right_conversion"])
        self.assertEqual(stdout_payload["left_conversion"]["failure_detail_count"], 2)
        self.assertEqual(stdout_payload["right_conversion"]["failure_detail_count"], 1)
        self.assertEqual(stdout_payload["controlnet"], fake_result["controlnet"])

    def test_controlnet_stereopair_cli_from_dom_can_include_failure_details_in_stdout(self):
        fake_result = {
            "mode": "from-dom",
            "left_conversion": {
                "output_count": 1,
                "failure_count": 1,
                "failures": [{"reason": "dom_lookup_failed", "sample": 1.0}],
            },
            "right_conversion": {
                "output_count": 1,
                "failure_count": 0,
                "failures": [],
            },
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

            stdout = io.StringIO()
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                    return_value=fake_result,
                ),
                redirect_stdout(stdout),
            ):
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
                        "--include-detail-records",
                    ]
                )

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

    def test_build_controlnets_for_dom_match_overlap_list_auto_assigns_pair_ids_and_writes_summary(self):
        config = ControlNetConfig(
            network_id="ctx_dom_match_batch",
            target_name="Mars",
            user_name="zmoratto",
            point_id_prefix="CTX",
            pair_id="CFG_SINGLE",
        )
        fake_pair_result = {
            "mode": "from-dom-match",
            "match": {"point_count": 5},
            "routing_audit": {"selected_final_matcher": "loftr", "match_count": 5},
            "controlnet": {
                "mode": "from-dom",
                "controlnet": {"point_count": 5, "measure_count": 10},
            },
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
            output_dir = temp_dir / "pair_nets"
            report_dir = temp_dir / "reports"

            with patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_match_stereo_pair",
                return_value=fake_pair_result,
            ) as build_mock:
                summary = build_controlnets_for_dom_match_overlap_list(
                    overlap_list_path,
                    original_list_path,
                    dom_list_path,
                    output_dir,
                    config,
                    report_directory=report_dir,
                    pair_id_prefix="S",
                    pair_id_start=4,
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="strict",
                    adaptive_routing_deep_presets={"loftr": "presets/loftr_external_outdoor.json"},
                )
                self.assertEqual(build_mock.call_count, 2)
                first_call = build_mock.call_args_list[0]
                second_call = build_mock.call_args_list[1]
                self.assertEqual(
                    first_call.args[:4],
                    ("left1_dom.cub", "right1_dom.cub", "left1.cub", "right1.cub"),
                )
                self.assertEqual(
                    second_call.args[:4],
                    ("left2_dom.cub", "right2_dom.cub", "left2.cub", "right2.cub"),
                )
                self.assertEqual(first_call.args[4].pair_id, "S4")
                self.assertEqual(second_call.args[4].pair_id, "S5")
                self.assertTrue(first_call.kwargs["enable_adaptive_routing"])
                self.assertEqual(first_call.kwargs["adaptive_routing_profile"], "strict")
                self.assertEqual(
                    first_call.kwargs["adaptive_routing_deep_presets"],
                    {"loftr": "presets/loftr_external_outdoor.json"},
                )
                self.assertEqual(summary["pair_count"], 2)
                self.assertEqual(summary["pairs"][0]["pair_id"], "S4")
                self.assertEqual(summary["pairs"][1]["pair_id"], "S5")
                self.assertEqual(summary["pairs"][0]["control_point_count"], 5)
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
        stdout_payload = json.loads(stdout.getvalue())
        self.assertNotIn("batch_summary", stdout_payload)
        self.assertEqual(stdout_payload["pairs"], fake_summary["pairs"])
        self.assertEqual(stdout_payload["batch_report_path"], fake_summary["batch_report_path"])

    def test_controlnet_stereopair_cli_from_dom_batch_can_include_batch_summary_in_stdout(self):
        fake_summary = {
            "mode": "from-dom-batch",
            "pair_count": 2,
            "pairs": [{"pair": "left1.cub,right1.cub", "pair_id": "S3"}],
            "batch_report_path": "reports/controlnet_batch_summary.json",
            "batch_summary": {"point_count_total": 12},
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
                ),
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
                        "--include-detail-records",
                    ]
                )

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

    def test_build_controlnet_for_dom_match_stereo_pair_matches_then_converts(self):
        config = ControlNetConfig(
            network_id="dom_match_unit",
            target_name="Mars",
            user_name="unit",
            description="",
            point_id_prefix="P",
            pair_id=None,
        )
        fake_match_summary = {
            "status": "matched",
            "point_count": 5,
            "matcher": {
                "matcher_method_requested": "flann",
                "matcher_method_effective": "loftr",
            },
            "adaptive_routing_profile": "strict",
            "adaptive_routing": {
                "status": "routed",
                "selected_initial_matcher": "loftr",
                "selected_final_matcher": "loftr",
                "final_decision": "accepted",
            },
            "deep_match_config_path": "presets/loftr_external_outdoor.json",
        }
        fake_controlnet = {
            "mode": "from-dom",
            "controlnet": {"output_path": "pair.net", "point_count": 5},
        }

        with temporary_directory() as temp_dir:
            output_net = temp_dir / "pair.net"
            left_dom_key = temp_dir / "pair_left_dom_match.key"
            right_dom_key = temp_dir / "pair_right_dom_match.key"
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_dom_pair_to_key_files",
                    return_value=fake_match_summary,
                ) as match_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                    return_value=fake_controlnet,
                ) as build_mock,
            ):
                result = build_controlnet_for_dom_match_stereo_pair(
                    "left_dom.cub",
                    "right_dom.cub",
                    "left_original.cub",
                    "right_original.cub",
                    config,
                    output_net,
                    left_dom_match_key_path=left_dom_key,
                    right_dom_match_key_path=right_dom_key,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="strict",
                    adaptive_routing_deep_presets={"loftr": "presets/loftr_external_outdoor.json"},
                    deep_match_config_path="presets/loftr_external_outdoor.json",
                    write_match_visualization=False,
                )

        self.assertEqual(result["mode"], "from-dom-match")
        self.assertEqual(result["match"], fake_match_summary)
        self.assertEqual(result["routing_audit"]["selected_final_matcher"], "loftr")
        self.assertEqual(result["routing_audit"]["match_count"], 5)
        self.assertEqual(match_mock.call_args.args[:4], ("left_dom.cub", "right_dom.cub", left_dom_key, right_dom_key))
        self.assertTrue(match_mock.call_args.kwargs["enable_adaptive_routing"])
        self.assertEqual(match_mock.call_args.kwargs["adaptive_routing_profile"], "strict")
        self.assertEqual(
            build_mock.call_args.args[:6],
            (left_dom_key, right_dom_key, "left_dom.cub", "right_dom.cub", "left_original.cub", "right_original.cub"),
        )

    def test_build_controlnet_for_dom_match_stereo_pair_does_not_convert_after_match_failure(self):
        config = ControlNetConfig(
            network_id="dom_match_failure_unit",
            target_name="Mars",
            user_name="unit",
            description="",
            point_id_prefix="P",
            pair_id=None,
        )

        with temporary_directory() as temp_dir:
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_dom_pair_to_key_files",
                    side_effect=RuntimeError("all routed matchers failed"),
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                ) as build_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "all routed matchers failed"):
                    build_controlnet_for_dom_match_stereo_pair(
                        "left_dom.cub",
                        "right_dom.cub",
                        "left_original.cub",
                        "right_original.cub",
                        config,
                        temp_dir / "pair.net",
                        enable_adaptive_routing=True,
                    )

        build_mock.assert_not_called()

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

    def test_build_controlnet_for_dom_stereo_pair_records_visualization_failure_report(self):
        config = ControlNetConfig(
            network_id="ctx_dom_viz_failure",
            target_name="Mars",
            user_name="zmoratto",
            description="dom visualization failure report test",
            point_id_prefix="VZF",
        )

        with temporary_directory() as temp_dir:
            left_dom_key = temp_dir / "left_dom.key"
            right_dom_key = temp_dir / "right_dom.key"
            output_net = temp_dir / "visualization_failure.net"
            report_path = temp_dir / "visualization_failure.summary.json"
            visualization_output_path = temp_dir / "post_ransac_match.png"
            write_key_file(left_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))
            write_key_file(right_dom_key, KeypointFile(10, 10, (Keypoint(1.0, 1.0),)))

            fake_ransac_result = {
                "applied": True,
                "status": "filtered",
                "mode": "loose",
                "input_count": 2,
                "retained_count": 1,
                "dropped_count": 1,
                "retained_soft_outlier_positions": [0],
            }

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.filter_stereo_pair_key_files_with_ransac",
                    return_value=fake_ransac_result,
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.write_stereo_pair_match_visualization_from_key_files",
                    side_effect=RuntimeError("visualization exploded"),
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original",
                ) as paired_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                ) as controlnet_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "visualization exploded"):
                    build_controlnet_for_dom_stereo_pair(
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
                        report_path=report_path,
                    )

            paired_mock.assert_not_called()
            controlnet_mock.assert_not_called()
            failure_report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(failure_report["match_visualization"]["status"], "failed")
        self.assertEqual(failure_report["match_visualization"]["error_type"], "RuntimeError")
        self.assertEqual(failure_report["match_visualization"]["error"], "visualization exploded")
        self.assertEqual(failure_report["match_visualization"]["output_path"], str(visualization_output_path))
        self.assertEqual(failure_report["ransac"]["retained_count"], 1)

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
