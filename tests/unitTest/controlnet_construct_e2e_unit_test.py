"""External-data end-to-end tests for the DOM matching ControlNet pipeline.

Author: Geng Xun
Created: 2026-04-17
Last Modified: 2026-04-17
Updated: 2026-04-17  Geng Xun added an LRO NAC DOM-matching E2E regression that runs overlap discovery, DOM matching, duplicate merge, dom2ori conversion, and ControlNet writing from the provided `.lis` inputs.
Updated: 2026-04-17  Geng Xun expanded the external LRO regression to batch-process every overlap pair written to `images_overlap.lis`.
Updated: 2026-04-17  Geng Xun added per-pair pipeline statistics and a CLI black-box batch regression that drives the full example workflow through script entrypoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.controlnet_stereopair import build_controlnet_for_stereo_pair, read_controlnet_config
from controlnet_construct.dom2ori import convert_dom_keypoints_to_original
from controlnet_construct.image_match import match_dom_pair_to_key_files
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
IMAGE_MATCH_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "image_match.py"
MERGE_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "tie_point_merge_in_overlap.py"
DOM2ORI_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "dom2ori.py"
CONTROLNET_SCRIPT = EXAMPLES_DIR / "controlnet_construct" / "controlnet_stereopair.py"


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
        )
        self.assertGreater(match_summary["point_count"], 0)
        self.assertTrue(left_dom_key_path.exists())
        self.assertTrue(right_dom_key_path.exists())

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
        }

    def test_lro_dom_matching_pipeline_end_to_end_for_all_overlap_pairs(self):
        original_paths, _, dom_by_original = self._load_external_dataset_or_skip()

        with temporary_directory() as temp_dir:
            overlap_list_path = temp_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps(CONTROLNET_CONFIG, indent=2) + "\n", encoding="utf-8")
            config = read_controlnet_config(config_path)

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
                    expected_dimension_mismatch = (
                        left_samples != right_samples or left_lines != right_lines
                    )
                    self.assertEqual(result["match"]["shared_extent_width"], min(left_samples, right_samples))
                    self.assertEqual(result["match"]["shared_extent_height"], min(left_lines, right_lines))

                    self.assertEqual(result["match"]["dimension_mismatch"], expected_dimension_mismatch)
                    pair_results.append(result)
                    pair_summaries.append(self._summarize_pair_result(overlap_pair, result))

        self.assertEqual(len(pair_results), len(overlap_pairs))
        self.assertTrue(all(result["controlnet"]["point_count"] > 0 for result in pair_results))
        self.assertGreater(sum(result["controlnet"]["point_count"] for result in pair_results), 0)
        print("Function E2E per-pair summary:")
        print(json.dumps(pair_summaries, indent=2, ensure_ascii=False))

    def test_lro_dom_matching_cli_batch_pipeline_for_all_overlap_pairs(self):
        original_paths, dom_paths, dom_by_original = self._load_external_dataset_or_skip()

        with temporary_directory() as temp_dir:
            resolved_original_list_path = temp_dir / "resolved_original_images.lis"
            resolved_dom_list_path = temp_dir / "resolved_doms.lis"
            overlap_list_path = temp_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps(CONTROLNET_CONFIG, indent=2) + "\n", encoding="utf-8")

            self._write_resolved_path_list(resolved_original_list_path, original_paths)
            self._write_resolved_path_list(resolved_dom_list_path, dom_paths)

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
                    )
                    self.assertGreater(match_summary["point_count"], 0)

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
                    self.assertEqual(match_summary["shared_extent_width"], min(left_samples, right_samples))
                    self.assertEqual(match_summary["shared_extent_height"], min(left_lines, right_lines))

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

        self.assertEqual(len(cli_pair_summaries), len(overlap_pairs))
        self.assertTrue(all(summary["control_point_count"] > 0 for summary in cli_pair_summaries))
        print("CLI black-box per-pair summary:")
        print(json.dumps(cli_pair_summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
