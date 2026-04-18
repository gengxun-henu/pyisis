"""External-data end-to-end tests for the DOM matching ControlNet pipeline.

Author: Geng Xun
Created: 2026-04-17
Last Modified: 2026-04-17
Updated: 2026-04-17  Geng Xun added an LRO NAC DOM-matching E2E regression that runs overlap discovery, DOM matching, duplicate merge, dom2ori conversion, and ControlNet writing from the provided `.lis` inputs.
Updated: 2026-04-17  Geng Xun expanded the external LRO regression to batch-process every overlap pair written to `images_overlap.lis`.
Updated: 2026-04-17  Geng Xun added per-pair pipeline statistics and a CLI black-box batch regression that drives the full example workflow through script entrypoints.
Updated: 2026-04-17  Geng Xun extended the E2E flow to emit DOM GSD reports/lists and generate a final cnetmerge shell script for all processed overlap pairs.
Updated: 2026-04-17  Geng Xun added an opt-in preserved output directory and batch JSON reports so external E2E artifacts can be kept on disk for inspection.
Updated: 2026-04-18  Geng Xun added an opt-in E2E artifact switch for saving stereo-pair DOM match line plots alongside preserved outputs.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import cv2
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.controlnet_stereopair import build_controlnet_for_stereo_pair, read_controlnet_config
from controlnet_construct.controlnet_merge import generate_cnetmerge_shell_script
from controlnet_construct.dom_prepare import normalize_dom_list_gsd
from controlnet_construct.dom2ori import convert_dom_keypoints_to_original
from controlnet_construct.image_match import match_dom_pair_to_key_files
from controlnet_construct.batch_summary import DEFAULT_BATCH_REPORT_NAME, write_batch_summary_report
from controlnet_construct.image_overlap import find_overlapping_image_pairs
from controlnet_construct.keypoints import read_key_file
from controlnet_construct.listing import (
    StereoPair,
    read_path_list,
    read_stereo_pair_list,
    validate_paired_path_lists,
    write_stereo_pair_list,
)
from controlnet_construct.tie_point_merge_in_overlap import merge_stereo_pair_key_files


EXTERNAL_DATA_ROOT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python")
ORIGINAL_LIST_PATH = EXTERNAL_DATA_ROOT / "ori_images.lis"
DOM_LIST_PATH = EXTERNAL_DATA_ROOT / "doms.lis"
CONTROLNET_CONFIG = {
    "NetworkId": "lro_dom_matching_e2e",
    "TargetName": "Moon",
    "UserName": "copilot",
    "Description": "External LRO NAC DOM matching ControlNet E2E regression",
    "PointIdPrefix": "LRO",
}

IMAGE_OVERLAP_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "image_overlap.py"
DOM_PREPARE_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "dom_prepare.py"
IMAGE_MATCH_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "image_match.py"
MERGE_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "tie_point_merge_in_overlap.py"
DOM2ORI_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "dom2ori.py"
CONTROLNET_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "controlnet_stereopair.py"
CONTROLNET_MERGE_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "controlnet_merge.py"
PRESERVED_E2E_OUTPUT_ROOT_ENV = "ISIS_PYBIND_E2E_OUTPUT_ROOT"
GENERATE_MATCH_LINE_PLOTS_ENV = "ISIS_PYBIND_E2E_GENERATE_MATCH_LINE_PLOTS"
E2E_RUN_METADATA_NAME = "e2e_run_metadata.json"


def _candidate_resolved_paths(list_directory: Path, entry: str) -> list[Path]:
    raw_path = Path(entry)
    candidates: list[Path] = []

    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append((list_directory / raw_path).resolve())
        if "REDUCED_8bpp" in entry:
            candidates.append((list_directory / entry.replace("REDUCED_8bpp", "REDUCED_")).resolve())
        basename = raw_path.name
        candidates.extend(sorted(path.resolve() for path in list_directory.rglob(basename)))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def _resolve_list_entries(list_path: Path) -> list[str]:
    list_directory = list_path.parent
    resolved_entries: list[str] = []
    missing_entries: list[str] = []

    for entry in read_path_list(list_path):
        resolved = next((candidate for candidate in _candidate_resolved_paths(list_directory, entry) if candidate.exists()), None)
        if resolved is None:
            missing_entries.append(entry)
            continue
        resolved_entries.append(str(resolved))

    if missing_entries:
        raise FileNotFoundError(
            f"Unable to resolve {len(missing_entries)} entries from {list_path}: {missing_entries}"
        )

    return resolved_entries


def _pair_tag(pair: StereoPair) -> str:
    return f"{Path(pair.left).stem}__{Path(pair.right).stem}"


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


class ControlNetConstructE2eUnitTest(unittest.TestCase):
    def _preserved_output_root(self) -> Path | None:
        configured = os.environ.get(PRESERVED_E2E_OUTPUT_ROOT_ENV, "").strip()
        if not configured:
            return None
        return Path(configured).expanduser().resolve()

    def _should_generate_match_line_plots(self) -> bool:
        configured = os.environ.get(GENERATE_MATCH_LINE_PLOTS_ENV, "").strip().lower()
        return configured in {"1", "true", "yes", "on"}

    @contextmanager
    def _managed_output_directory(self, scenario_name: str):
        preserved_root = self._preserved_output_root()
        if preserved_root is None:
            with temporary_directory() as temp_dir:
                yield temp_dir
            return

        preserved_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = preserved_root / f"{scenario_name}_{timestamp}"
        suffix = 1
        while output_dir.exists():
            suffix += 1
            output_dir = preserved_root / f"{scenario_name}_{timestamp}_{suffix:02d}"
        output_dir.mkdir(parents=True, exist_ok=False)
        yield output_dir

    def _write_json_report(self, output_path: Path, payload: dict[str, object]) -> Path:
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return output_path

    def _write_pair_report(self, output_dir: Path, pair: StereoPair, result: dict[str, object], *, prefix: str = "") -> Path:
        filename = f"{prefix}{_pair_tag(pair)}.summary.json"
        return self._write_json_report(output_dir / filename, result)

    def _write_run_metadata(
        self,
        output_dir: Path,
        *,
        scenario_name: str,
        pair_results: list[dict[str, object]],
        pair_report_paths: list[Path],
        batch_report_path: Path,
        extra_paths: dict[str, object],
    ) -> Path:
        metadata = {
            "scenario": scenario_name,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "output_directory": str(output_dir),
            "preserved_output_root": str(self._preserved_output_root()) if self._preserved_output_root() is not None else None,
            "pair_count": len(pair_results),
            "pair_report_paths": [str(path) for path in pair_report_paths],
            "batch_report_path": str(batch_report_path),
            **extra_paths,
        }
        return self._write_json_report(output_dir / E2E_RUN_METADATA_NAME, metadata)

    def _load_external_dataset_or_skip(self) -> tuple[list[str], list[str], dict[str, str]]:
        if not ORIGINAL_LIST_PATH.exists() or not DOM_LIST_PATH.exists():
            self.skipTest("The external LRO NAC E2E lists are not available on this machine.")

        try:
            original_paths = _resolve_list_entries(ORIGINAL_LIST_PATH)
            dom_paths = _resolve_list_entries(DOM_LIST_PATH)
        except FileNotFoundError as error:
            self.skipTest(str(error))

        try:
            paired_paths = validate_paired_path_lists(original_paths, dom_paths)
        except ValueError as error:
            self.fail(f"The external LRO NAC E2E lists are invalid: {error}")

        missing_paths = [path for pair in paired_paths for path in pair if not Path(path).exists()]
        if missing_paths:
            self.skipTest(f"The external LRO NAC E2E dataset is incomplete: {missing_paths}")

        return original_paths, dom_paths, dict(paired_paths)

    def _open_cube_dimensions(self, cube_path: str) -> tuple[int, int]:
        cube = ip.Cube()
        cube.open(str(cube_path), "r")
        try:
            return cube.sample_count(), cube.line_count()
        finally:
            cube.close()

    def _write_match_line_plot(
        self,
        left_key_path: Path,
        right_key_path: Path,
        output_path: Path,
        *,
        title: str,
        max_panel_width: int = 900,
        max_panel_height: int = 900,
        max_render_matches: int = 500,
    ) -> Path:
        left_key_file = read_key_file(left_key_path)
        right_key_file = read_key_file(right_key_path)

        point_count = min(len(left_key_file.points), len(right_key_file.points))
        if point_count <= 0:
            raise ValueError("Cannot render a stereo-pair match line plot without matched points.")

        left_width = max(1, int(left_key_file.image_width))
        left_height = max(1, int(left_key_file.image_height))
        right_width = max(1, int(right_key_file.image_width))
        right_height = max(1, int(right_key_file.image_height))

        scale = min(
            1.0,
            float(max_panel_width) / float(max(left_width, right_width)),
            float(max_panel_height) / float(max(left_height, right_height)),
        )
        scaled_left_width = max(1, int(round(left_width * scale)))
        scaled_left_height = max(1, int(round(left_height * scale)))
        scaled_right_width = max(1, int(round(right_width * scale)))
        scaled_right_height = max(1, int(round(right_height * scale)))

        margin_x = 40
        top_margin = 90
        bottom_margin = 40
        panel_gap = 100

        canvas_width = margin_x * 2 + scaled_left_width + panel_gap + scaled_right_width
        canvas_height = top_margin + max(scaled_left_height, scaled_right_height) + bottom_margin
        canvas = np.full((canvas_height, canvas_width, 3), 255, dtype=np.uint8)

        left_origin_x = margin_x
        left_origin_y = top_margin
        right_origin_x = margin_x + scaled_left_width + panel_gap
        right_origin_y = top_margin

        cv2.rectangle(
            canvas,
            (left_origin_x - 1, left_origin_y - 1),
            (left_origin_x + scaled_left_width, left_origin_y + scaled_left_height),
            (180, 180, 180),
            1,
        )
        cv2.rectangle(
            canvas,
            (right_origin_x - 1, right_origin_y - 1),
            (right_origin_x + scaled_right_width, right_origin_y + scaled_right_height),
            (180, 180, 180),
            1,
        )

        cv2.putText(canvas, title, (margin_x, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2, cv2.LINE_AA)
        cv2.putText(
            canvas,
            f"Rendered matches: {min(point_count, max_render_matches)} / {point_count}",
            (margin_x, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (70, 70, 70),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(canvas, "Left DOM", (left_origin_x, top_margin - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1, cv2.LINE_AA)
        cv2.putText(canvas, "Right DOM", (right_origin_x, top_margin - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 1, cv2.LINE_AA)

        if point_count > max_render_matches:
            step = float(point_count - 1) / float(max_render_matches - 1)
            point_indices = [int(round(step * index)) for index in range(max_render_matches)]
        else:
            point_indices = list(range(point_count))

        for index in point_indices:
            left_point = left_key_file.points[index]
            right_point = right_key_file.points[index]

            left_x = left_origin_x + int(round((left_point.sample - 1.0) * scale))
            left_y = left_origin_y + int(round((left_point.line - 1.0) * scale))
            right_x = right_origin_x + int(round((right_point.sample - 1.0) * scale))
            right_y = right_origin_y + int(round((right_point.line - 1.0) * scale))

            left_x = max(left_origin_x, min(left_x, left_origin_x + scaled_left_width - 1))
            left_y = max(left_origin_y, min(left_y, left_origin_y + scaled_left_height - 1))
            right_x = max(right_origin_x, min(right_x, right_origin_x + scaled_right_width - 1))
            right_y = max(right_origin_y, min(right_y, right_origin_y + scaled_right_height - 1))

            hue = int(round(179.0 * float(index % max(1, point_count)) / float(max(1, point_count))))
            color_pixel = np.uint8([[[hue, 220, 245]]])
            bgr = tuple(int(channel) for channel in cv2.cvtColor(color_pixel, cv2.COLOR_HSV2BGR)[0, 0])

            cv2.line(canvas, (left_x, left_y), (right_x, right_y), bgr, 1, cv2.LINE_AA)
            cv2.circle(canvas, (left_x, left_y), 2, (255, 80, 80), -1, cv2.LINE_AA)
            cv2.circle(canvas, (right_x, right_y), 2, (80, 140, 255), -1, cv2.LINE_AA)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), canvas):
            raise IOError(f"Failed to write stereo-pair match line plot: {output_path}")
        return output_path

    def _maybe_write_match_line_plot(
        self,
        output_dir: Path,
        pair: StereoPair,
        left_key_path: Path,
        right_key_path: Path,
        *,
        prefix: str = "",
        title_prefix: str = "",
    ) -> str | None:
        if not self._should_generate_match_line_plots():
            return None

        pair_tag = _pair_tag(pair)
        output_path = output_dir / f"{prefix}{pair_tag}_match_lines.png"
        title = f"{title_prefix}{pair_tag}" if title_prefix else pair_tag
        return str(self._write_match_line_plot(left_key_path, right_key_path, output_path, title=title))

    def _summarize_pair_result(self, pair: StereoPair, result: dict[str, object]) -> dict[str, object]:
        merged_count = int(result["merge"]["unique_count"])
        retained_count = int(result["left_conversion"]["output_count"])
        return {
            "pair": pair.as_csv_line(),
            "match_point_count": int(result["match"]["point_count"]),
            "merged_point_count": merged_count,
            "dom2ori_retained_count": retained_count,
            "dom2ori_retention_rate": round(_safe_ratio(retained_count, merged_count), 6),
            "control_point_count": int(result["controlnet"]["point_count"]),
            "dimension_mismatch": bool(result["match"]["dimension_mismatch"]),
            "shared_extent_width": int(result["match"]["shared_extent_width"]),
            "shared_extent_height": int(result["match"]["shared_extent_height"]),
        }

    def _make_cli_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        build_python = str(PROJECT_ROOT / "build" / "python")
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = build_python if not existing_pythonpath else f"{build_python}:{existing_pythonpath}"
        return env

    def _run_cli_json(self, *args: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, *args],
            cwd=str(PROJECT_ROOT),
            env=self._make_cli_environment(),
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = completed.stdout.strip()
        if not stdout:
            self.fail(f"CLI produced no stdout JSON: {' '.join(args)}\nstderr:\n{completed.stderr}")

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as error:
            self.fail(
                f"CLI stdout was not valid JSON for {' '.join(args)}: {error}\nstdout:\n{stdout}\nstderr:\n{completed.stderr}"
            )

    def _write_resolved_path_list(self, destination: Path, paths: list[str]) -> None:
        destination.write_text("\n".join(paths) + "\n", encoding="utf-8")

    def _run_e2e_for_pair(
        self,
        temp_dir: Path,
        pair: StereoPair,
        *,
        left_dom_path: str,
        right_dom_path: str,
        config,
    ) -> dict[str, object]:
        pair_tag = _pair_tag(pair)
        left_dom_key_path = temp_dir / f"{pair_tag}_left_dom.key"
        right_dom_key_path = temp_dir / f"{pair_tag}_right_dom.key"
        merged_left_dom_key_path = temp_dir / f"{pair_tag}_left_dom_merged.key"
        merged_right_dom_key_path = temp_dir / f"{pair_tag}_right_dom_merged.key"
        left_original_key_path = temp_dir / f"{pair_tag}_left_ori.key"
        right_original_key_path = temp_dir / f"{pair_tag}_right_ori.key"
        left_failure_log_path = temp_dir / f"{pair_tag}_left_dom2ori_failures.json"
        right_failure_log_path = temp_dir / f"{pair_tag}_right_dom2ori_failures.json"
        output_net_path = temp_dir / f"{pair_tag}.net"

        match_summary = match_dom_pair_to_key_files(
            left_dom_path,
            right_dom_path,
            left_dom_key_path,
            right_dom_key_path,
            max_image_dimension=2048,
            block_width=1024,
            block_height=1024,
            overlap_x=128,
            overlap_y=128,
            min_valid_pixels=64,
            ratio_test=0.9,
            max_features=3000,
            crop_expand_pixels=100,
            min_overlap_size=16,
        )
        self.assertGreater(match_summary["point_count"], 0)
        self.assertTrue(left_dom_key_path.exists())
        self.assertTrue(right_dom_key_path.exists())

        match_line_plot_path = self._maybe_write_match_line_plot(
            temp_dir,
            pair,
            left_dom_key_path,
            right_dom_key_path,
            title_prefix="function_e2e DOM matches: ",
        )

        merge_summary = merge_stereo_pair_key_files(
            str(left_dom_key_path),
            str(right_dom_key_path),
            str(merged_left_dom_key_path),
            str(merged_right_dom_key_path),
            decimals=3,
        )
        self.assertGreater(merge_summary["unique_count"], 0)
        self.assertLessEqual(merge_summary["unique_count"], merge_summary["input_count"])
        self.assertTrue(merged_left_dom_key_path.exists())
        self.assertTrue(merged_right_dom_key_path.exists())

        left_conversion = convert_dom_keypoints_to_original(
            merged_left_dom_key_path,
            left_dom_path,
            pair.left,
            left_original_key_path,
            failure_log_path=left_failure_log_path,
        )
        right_conversion = convert_dom_keypoints_to_original(
            merged_right_dom_key_path,
            right_dom_path,
            pair.right,
            right_original_key_path,
            failure_log_path=right_failure_log_path,
        )
        self.assertGreater(left_conversion["output_count"], 0)
        self.assertGreater(right_conversion["output_count"], 0)
        self.assertEqual(left_conversion["output_count"], right_conversion["output_count"])
        self.assertTrue(left_original_key_path.exists())
        self.assertTrue(right_original_key_path.exists())
        self.assertTrue(left_failure_log_path.exists())
        self.assertTrue(right_failure_log_path.exists())

        left_original_keypoints = read_key_file(left_original_key_path)
        right_original_keypoints = read_key_file(right_original_key_path)
        self.assertEqual(len(left_original_keypoints.points), left_conversion["output_count"])
        self.assertEqual(len(right_original_keypoints.points), right_conversion["output_count"])
        self.assertEqual(len(left_original_keypoints.points), len(right_original_keypoints.points))

        controlnet_summary = build_controlnet_for_stereo_pair(
            left_original_key_path,
            right_original_key_path,
            pair.left,
            pair.right,
            config,
            output_net_path,
            pvl_format=True,
        )
        self.assertTrue(output_net_path.exists())
        self.assertGreater(controlnet_summary["point_count"], 0)
        self.assertEqual(controlnet_summary["measure_count"], controlnet_summary["point_count"] * 2)

        loaded_net = ip.ControlNet(str(output_net_path))
        left_failures = json.loads(left_failure_log_path.read_text(encoding="utf-8"))
        right_failures = json.loads(right_failure_log_path.read_text(encoding="utf-8"))

        self.assertEqual(loaded_net.get_num_points(), controlnet_summary["point_count"])
        self.assertEqual(loaded_net.get_num_measures(), controlnet_summary["measure_count"])
        self.assertEqual(loaded_net.get_target(), "Moon")
        self.assertEqual(loaded_net.get_network_id(), "lro_dom_matching_e2e")
        self.assertEqual(left_failures["output_count"], right_failures["output_count"])
        self.assertLess(left_failures["failure_count"], merge_summary["unique_count"])
        self.assertLess(right_failures["failure_count"], merge_summary["unique_count"])

        return {
            "pair": pair.as_csv_line(),
            "match": match_summary,
            "merge": merge_summary,
            "left_conversion": left_conversion,
            "right_conversion": right_conversion,
            "controlnet": controlnet_summary,
            **({"match_line_plot_path": match_line_plot_path} if match_line_plot_path is not None else {}),
        }

    def test_lro_dom_matching_pipeline_end_to_end_for_all_overlap_pairs(self):
        original_paths, _, dom_by_original = self._load_external_dataset_or_skip()
        """This test runs the full DOM-matching ControlNet pipeline end-to-end for every overlapping stereo pair discovered 
        from the provided original image list. The test directly calls the core functions for each step instead of using the CLI scripts, 
        and verifies the expected outputs at each stage.
        """

        with self._managed_output_directory("function_e2e") as temp_dir:
            overlap_list_path = temp_dir / "images_overlap.lis"
            scaled_dom_list_path = temp_dir / "doms_scaled.lis"
            gsd_report_path = temp_dir / "images_gsd.txt"
            scaled_dom_dir = temp_dir / "scaled_doms"
            merged_net_path = temp_dir / "merged_all_pairs.net"
            merge_script_path = temp_dir / "merge_all_controlnets.sh"
            batch_report_path = temp_dir / DEFAULT_BATCH_REPORT_NAME
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps(CONTROLNET_CONFIG, indent=2) + "\n", encoding="utf-8")
            config = read_controlnet_config(config_path)

            normalization = normalize_dom_list_gsd(
                [(dom_path, dom_path) for dom_path in dom_by_original.values()],
                scaled_dom_list_path,
                gsd_report_path=gsd_report_path,
                output_directory=scaled_dom_dir,
                tolerance_ratio=10.0,
                apply=False,
            )
            self.assertEqual(normalization["scaled_count"], 0)
            self.assertTrue(gsd_report_path.exists())
            self.assertTrue(scaled_dom_list_path.exists())

            overlap_pairs, bounds = find_overlapping_image_pairs(
                original_paths,
                grid_samples=4,
                grid_lines=4,
                min_valid_points=4,
            )
            self.assertTrue(overlap_pairs, "Expected at least one overlapping stereo pair from the provided original-image list.")
            self.assertEqual(set(bounds.keys()), set(original_paths))

            write_stereo_pair_list(overlap_list_path, overlap_pairs)
            self.assertEqual(read_stereo_pair_list(overlap_list_path), overlap_pairs)

            pair_results: list[dict[str, object]] = []
            pair_summaries: list[dict[str, object]] = []
            pair_report_paths: list[Path] = []
            for overlap_pair in overlap_pairs:
                left_dom_path = dom_by_original[overlap_pair.left]
                right_dom_path = dom_by_original[overlap_pair.right]

                with self.subTest(pair=overlap_pair.as_csv_line()):
                    result = self._run_e2e_for_pair(
                        temp_dir,
                        overlap_pair,
                        left_dom_path=left_dom_path,
                        right_dom_path=right_dom_path,
                        config=config,
                    )

                    left_samples, left_lines = self._open_cube_dimensions(left_dom_path)
                    right_samples, right_lines = self._open_cube_dimensions(right_dom_path)
                    self.assertGreater(result["match"]["shared_extent_width"], 0)
                    self.assertGreater(result["match"]["shared_extent_height"], 0)
                    self.assertLessEqual(result["match"]["shared_extent_width"], max(left_samples, right_samples))
                    self.assertLessEqual(result["match"]["shared_extent_height"], max(left_lines, right_lines))
                    pair_results.append(result)
                    pair_summaries.append(self._summarize_pair_result(overlap_pair, result))
                    pair_report_paths.append(self._write_pair_report(temp_dir, overlap_pair, result))

            merge_summary = generate_cnetmerge_shell_script(
                overlap_list_path,
                temp_dir,
                merged_net_path,
                merge_script_path,
                network_id=CONTROLNET_CONFIG["NetworkId"],
                description="External LRO NAC merged ControlNet shell",
            )
            self.assertTrue(merge_script_path.exists())
            self.assertEqual(merge_summary["included_count"], len(overlap_pairs))
            batch_report = write_batch_summary_report(pair_results, batch_report_path, source_reports=[str(path) for path in pair_report_paths])
            self.assertEqual(batch_report["pair_count"], len(overlap_pairs))
            self.assertEqual(batch_report["report_path"], str(batch_report_path))
            run_metadata_path = self._write_run_metadata(
                temp_dir,
                scenario_name="function_e2e",
                pair_results=pair_results,
                pair_report_paths=pair_report_paths,
                batch_report_path=batch_report_path,
                extra_paths={
                    "gsd_report_path": str(gsd_report_path),
                    "scaled_dom_list_path": str(scaled_dom_list_path),
                    "overlap_list_path": str(overlap_list_path),
                    "merge_script_path": str(merge_script_path),
                    "merged_net_path": str(merged_net_path),
                    "controlnet_config_path": str(config_path),
                },
            )
            self.assertTrue(run_metadata_path.exists())

        self.assertEqual(len(pair_results), len(overlap_pairs))
        self.assertTrue(all(result["controlnet"]["point_count"] > 0 for result in pair_results))
        self.assertGreater(sum(result["controlnet"]["point_count"] for result in pair_results), 0)
        print("Function E2E per-pair summary:")
        print(json.dumps(pair_summaries, indent=2, ensure_ascii=False))
        if self._preserved_output_root() is not None:
            print(f"Function E2E outputs preserved under: {temp_dir}")

   
    def test_lro_dom_matching_cli_batch_pipeline_for_all_overlap_pairs(self):
        original_paths, dom_paths, dom_by_original = self._load_external_dataset_or_skip()
        
        """This test runs the full DOM-matching ControlNet pipeline end-to-end for every overlapping stereo pair discovered
        from the provided original image list, using the CLI scripts as black boxes. 
        The test verifies the expected outputs at each stage, and generates JSON reports for each pair as well as a batch summary report for the entire run.        
        """ 

        with self._managed_output_directory("cli_e2e") as temp_dir:
            resolved_original_list_path = temp_dir / "resolved_original_images.lis"
            resolved_dom_list_path = temp_dir / "resolved_doms.lis"
            scaled_dom_list_path = temp_dir / "doms_scaled.lis"
            gsd_report_path = temp_dir / "images_gsd.txt"
            overlap_list_path = temp_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            merged_net_path = temp_dir / "merged_all_pairs.net"
            merge_script_path = temp_dir / "merge_all_controlnets.sh"
            batch_report_path = temp_dir / DEFAULT_BATCH_REPORT_NAME
            config_path.write_text(json.dumps(CONTROLNET_CONFIG, indent=2) + "\n", encoding="utf-8")

            self._write_resolved_path_list(resolved_original_list_path, original_paths)
            self._write_resolved_path_list(resolved_dom_list_path, dom_paths)

            prepare_summary = self._run_cli_json(
                str(DOM_PREPARE_SCRIPT),
                str(resolved_dom_list_path),
                str(scaled_dom_list_path),
                "--gsd-report",
                str(gsd_report_path),
                "--tolerance-ratio",
                "10.0",
                "--dry-run",
            )
            self.assertEqual(prepare_summary["scaled_count"], 0)
            self.assertTrue(scaled_dom_list_path.exists())
            self.assertTrue(gsd_report_path.exists())

            overlap_summary = self._run_cli_json(
                str(IMAGE_OVERLAP_SCRIPT),
                str(resolved_original_list_path),
                str(overlap_list_path),
                "--grid-samples",
                "4",
                "--grid-lines",
                "4",
                "--min-valid-points",
                "4",
            )
            self.assertTrue(overlap_list_path.exists())
            overlap_pairs = read_stereo_pair_list(overlap_list_path)
            self.assertGreater(len(overlap_pairs), 0)
            self.assertEqual(overlap_summary["overlap_pair_count"], len(overlap_pairs))

            cli_pair_summaries: list[dict[str, object]] = []
            cli_pair_results: list[dict[str, object]] = []
            cli_pair_report_paths: list[Path] = []
            for overlap_pair in overlap_pairs:
                left_dom_path = dom_by_original[overlap_pair.left]
                right_dom_path = dom_by_original[overlap_pair.right]
                pair_tag = _pair_tag(overlap_pair)

                left_dom_key_path = temp_dir / f"{pair_tag}_cli_left_dom.key"
                right_dom_key_path = temp_dir / f"{pair_tag}_cli_right_dom.key"
                merged_left_dom_key_path = temp_dir / f"{pair_tag}_cli_left_dom_merged.key"
                merged_right_dom_key_path = temp_dir / f"{pair_tag}_cli_right_dom_merged.key"
                left_original_key_path = temp_dir / f"{pair_tag}_cli_left_ori.key"
                right_original_key_path = temp_dir / f"{pair_tag}_cli_right_ori.key"
                left_failure_log_path = temp_dir / f"{pair_tag}_cli_left_dom2ori_failures.json"
                right_failure_log_path = temp_dir / f"{pair_tag}_cli_right_dom2ori_failures.json"
                output_net_path = temp_dir / f"{pair_tag}_cli.net"

                with self.subTest(cli_pair=overlap_pair.as_csv_line()):
                    match_summary = self._run_cli_json(
                        str(IMAGE_MATCH_SCRIPT),
                        str(left_dom_path),
                        str(right_dom_path),
                        str(left_dom_key_path),
                        str(right_dom_key_path),
                        "--max-image-dimension",
                        "2048",
                        "--sub-block-size-x",
                        "1024",
                        "--sub-block-size-y",
                        "1024",
                        "--overlap-size-x",
                        "128",
                        "--overlap-size-y",
                        "128",
                        "--min-valid-pixels",
                        "64",
                        "--ratio-test",
                        "0.9",
                        "--max-features",
                        "3000",
                        "--crop-expand-pixels",
                        "100",
                        "--min-overlap-size",
                        "16",
                    )
                    self.assertGreater(match_summary["point_count"], 0)

                    cli_match_line_plot_path = self._maybe_write_match_line_plot(
                        temp_dir,
                        overlap_pair,
                        left_dom_key_path,
                        right_dom_key_path,
                        prefix="cli_",
                        title_prefix="cli_e2e DOM matches: ",
                    )

                    merge_summary = self._run_cli_json(
                        str(MERGE_SCRIPT),
                        str(left_dom_key_path),
                        str(right_dom_key_path),
                        str(merged_left_dom_key_path),
                        str(merged_right_dom_key_path),
                        "--decimals",
                        "3",
                    )
                    self.assertGreater(merge_summary["unique_count"], 0)

                    left_conversion = self._run_cli_json(
                        str(DOM2ORI_SCRIPT),
                        str(merged_left_dom_key_path),
                        str(left_dom_path),
                        str(overlap_pair.left),
                        str(left_original_key_path),
                        "--failure-log",
                        str(left_failure_log_path),
                    )
                    right_conversion = self._run_cli_json(
                        str(DOM2ORI_SCRIPT),
                        str(merged_right_dom_key_path),
                        str(right_dom_path),
                        str(overlap_pair.right),
                        str(right_original_key_path),
                        "--failure-log",
                        str(right_failure_log_path),
                    )
                    self.assertEqual(left_conversion["output_count"], right_conversion["output_count"])
                    self.assertGreater(left_conversion["output_count"], 0)

                    controlnet_summary = self._run_cli_json(
                        str(CONTROLNET_SCRIPT),
                        "from-ori",
                        str(left_original_key_path),
                        str(right_original_key_path),
                        str(overlap_pair.left),
                        str(overlap_pair.right),
                        str(config_path),
                        str(output_net_path),
                    )
                    self.assertGreater(controlnet_summary["point_count"], 0)
                    self.assertEqual(controlnet_summary["measure_count"], controlnet_summary["point_count"] * 2)

                    left_samples, left_lines = self._open_cube_dimensions(left_dom_path)
                    right_samples, right_lines = self._open_cube_dimensions(right_dom_path)
                    self.assertGreater(match_summary["shared_extent_width"], 0)
                    self.assertGreater(match_summary["shared_extent_height"], 0)
                    self.assertLessEqual(match_summary["shared_extent_width"], max(left_samples, right_samples))
                    self.assertLessEqual(match_summary["shared_extent_height"], max(left_lines, right_lines))

                    cli_pair_result = {
                        "pair": overlap_pair.as_csv_line(),
                        "match": match_summary,
                        "merge": merge_summary,
                        "left_conversion": left_conversion,
                        "right_conversion": right_conversion,
                        "controlnet": controlnet_summary,
                        **({"match_line_plot_path": cli_match_line_plot_path} if cli_match_line_plot_path is not None else {}),
                    }
                    cli_pair_results.append(cli_pair_result)
                    cli_pair_report_paths.append(self._write_pair_report(temp_dir, overlap_pair, cli_pair_result, prefix="cli_"))

                    cli_pair_summaries.append(
                        {
                            "pair": overlap_pair.as_csv_line(),
                            "match_point_count": int(match_summary["point_count"]),
                            "merged_point_count": int(merge_summary["unique_count"]),
                            "dom2ori_retained_count": int(left_conversion["output_count"]),
                            "dom2ori_retention_rate": round(
                                _safe_ratio(int(left_conversion["output_count"]), int(merge_summary["unique_count"])),
                                6,
                            ),
                            "control_point_count": int(controlnet_summary["point_count"]),
                            "dimension_mismatch": bool(match_summary["dimension_mismatch"]),
                            "shared_extent_width": int(match_summary["shared_extent_width"]),
                            "shared_extent_height": int(match_summary["shared_extent_height"]),
                        }
                    )

            merge_cli_summary = self._run_cli_json(
                str(CONTROLNET_MERGE_SCRIPT),
                str(overlap_list_path),
                str(temp_dir),
                str(merged_net_path),
                str(merge_script_path),
                "--network-id",
                CONTROLNET_CONFIG["NetworkId"],
                "--description",
                "External LRO NAC merged ControlNet shell",
                "--pair-net-suffix",
                "_cli.net",
            )
            self.assertTrue(merge_script_path.exists())
            self.assertEqual(merge_cli_summary["included_count"], len(overlap_pairs))
            cli_batch_report = write_batch_summary_report(
                cli_pair_results,
                batch_report_path,
                source_reports=[str(path) for path in cli_pair_report_paths],
            )
            self.assertEqual(cli_batch_report["pair_count"], len(overlap_pairs))
            self.assertEqual(cli_batch_report["report_path"], str(batch_report_path))
            run_metadata_path = self._write_run_metadata(
                temp_dir,
                scenario_name="cli_e2e",
                pair_results=cli_pair_results,
                pair_report_paths=cli_pair_report_paths,
                batch_report_path=batch_report_path,
                extra_paths={
                    "resolved_original_list_path": str(resolved_original_list_path),
                    "resolved_dom_list_path": str(resolved_dom_list_path),
                    "scaled_dom_list_path": str(scaled_dom_list_path),
                    "gsd_report_path": str(gsd_report_path),
                    "overlap_list_path": str(overlap_list_path),
                    "merge_script_path": str(merge_script_path),
                    "merged_net_path": str(merged_net_path),
                    "controlnet_config_path": str(config_path),
                },
            )
            self.assertTrue(run_metadata_path.exists())

        self.assertEqual(len(cli_pair_summaries), len(overlap_pairs))
        self.assertTrue(all(summary["control_point_count"] > 0 for summary in cli_pair_summaries))
        print("CLI black-box per-pair summary:")
        print(json.dumps(cli_pair_summaries, indent=2, ensure_ascii=False))
        if self._preserved_output_root() is not None:
            print(f"CLI E2E outputs preserved under: {temp_dir}")


if __name__ == "__main__":
    unittest.main()
