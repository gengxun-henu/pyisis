"""Unit tests for adaptive fast pipeline summary and runner packaging.

Author: Geng Xun
Created: 2026-05-27
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun made adaptive-fast summary fixtures portable on Windows.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.experiments import summarize_adaptive_fast_pipeline as summary_tool


RUNNER_PATH = (
    PROJECT_ROOT
    / "examples"
    / "controlnet_construct"
    / "experiments"
    / "run_pipe_test2_adaptive_fast_pipeline.sh"
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_synthetic_pipeline_output(root: Path) -> None:
    _write_json(
        root / "reports" / "pipeline_timing.json",
        {
            "pipeline": {"status": "success", "total_duration_seconds": 12.5},
            "steps": [
                {"name": "prepare", "status": "success", "duration_seconds": 1.25},
                {"name": "match", "status": "success", "duration_seconds": 2.5},
            ],
            "pair_matches": [
                {"name": "pair:PAIR_A", "status": "success", "duration_seconds": 0.75}
            ],
        },
    )
    _write_json(
        root / "reports" / "controlnet_batch_summary.json",
        {
            "pair_count": 2,
            "total_merge_point_count": 21,
            "total_dom2ori_retained_count": 18,
            "total_final_control_point_count": 17,
            "average_dom2ori_retention_rate": 0.75,
            "overall_dom2ori_retention_rate": 0.857,
        },
    )
    (root / "merge").mkdir(parents=True, exist_ok=True)
    (root / "merge" / "dom_matching_merged.net").write_text("synthetic net\n", encoding="utf-8")
    _write_json(
        root / "match_results" / "PAIR_A.json",
        {
            "status": "success",
            "matched_point_count": 10,
            "tile_count": 8,
            "matched_tile_count": 6,
            "skipped_tile_count": 2,
            "adaptive_routing_profile": "balanced",
            "adaptive_routing": {
                "status": "selected",
                "selected_initial_matcher": "sift",
                "selected_final_matcher": "flann",
                "route_reason": "texture-ok",
                "sidecar": {
                    "texture_sparseness": {
                        "pair_texture_sparseness": 0.125,
                        "weaker_side": "left",
                    },
                    "lighting_difference": {
                        "lighting_difference_score": 0.25,
                        "reason": "matched",
                    },
                },
            },
        },
    )
    _write_json(
        root / "match_results" / "PAIR_B.json",
        {
            "pair": "PAIR|B",
            "status": "success",
            "point_count": 7,
            "adaptive_routing_profile": "balanced",
            "adaptive_routing": {
                "status": "selected",
                "selected_initial_matcher": "sift|fast",
                "selected_final_matcher": "flann\nverified",
                "reason": "fallback field",
                "texture_sparseness": {"pair_texture_sparseness": 0.5},
                "lighting_difference": {
                    "lighting_difference_score": 0.75,
                    "reason": "large\nchange",
                },
            },
        },
    )


class AdaptiveFastSummaryUnitTest(unittest.TestCase):
    def test_main_writes_json_and_markdown_outputs_from_synthetic_tree(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "pipeline"
            _write_synthetic_pipeline_output(root)
            json_output = root / "reports" / "adaptive_fast_summary.json"
            markdown_output = root / "reports" / "adaptive_fast_summary.md"

            status = summary_tool.main(
                [
                    str(root),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                ]
            )

            self.assertEqual(status, 0)
            self.assertTrue(json_output.exists())
            self.assertTrue(markdown_output.exists())
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["controlnet_batch"]["total_final_control_point_count"], 17)
            self.assertEqual(payload["merged_net"]["size_bytes"], (root / "merge" / "dom_matching_merged.net").stat().st_size)
            markdown_text = markdown_output.read_text(encoding="utf-8")
            self.assertIn("# Adaptive Fast Pipeline Summary", markdown_text)
            self.assertIn("| PAIR_A | 10 | sift -> flann | 0.125 | 0.25 |", markdown_text)

    def test_summarize_output_rejects_missing_pipeline_root(self):
        with tempfile.TemporaryDirectory() as temp_name:
            missing_root = Path(temp_name) / "missing"

            with self.assertRaisesRegex(FileNotFoundError, "pipeline output directory not found"):
                summary_tool.summarize_output(missing_root)

    def test_summarize_output_rejects_missing_match_results_directory(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "pipeline"
            _write_json(root / "reports" / "pipeline_timing.json", {"steps": []})
            _write_json(root / "reports" / "controlnet_batch_summary.json", {})

            with self.assertRaisesRegex(FileNotFoundError, "pair-result directory not found"):
                summary_tool.summarize_output(root)

    def test_summarize_output_computes_route_counts_and_pair_rows(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "pipeline"
            _write_synthetic_pipeline_output(root)

            payload = summary_tool.summarize_output(root)

        self.assertEqual(payload["route_counts"], {"sift->flann": 1, "sift|fast->flann\nverified": 1})
        self.assertEqual([pair["pair"] for pair in payload["pairs"]], ["PAIR_A", "PAIR|B"])
        self.assertEqual(payload["pairs"][0]["matched_point_count"], 10)
        self.assertEqual(payload["pairs"][1]["matched_point_count"], 7)
        self.assertEqual(payload["pairs"][0]["adaptive_routing"]["route_reason"], "texture-ok")
        self.assertEqual(payload["pairs"][1]["adaptive_routing"]["route_reason"], "fallback field")
        self.assertEqual(payload["pairs"][0]["adaptive_routing"]["texture_weaker_side"], "left")
        self.assertEqual(payload["pairs"][1]["adaptive_routing"]["lighting_difference_score"], 0.75)

    def test_markdown_table_escapes_pipe_and_newline_content(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "pipeline"
            _write_synthetic_pipeline_output(root)
            payload = summary_tool.summarize_output(root)

            markdown_text = summary_tool._markdown_table(payload)

        self.assertIn("| PAIR\\|B | 7 | sift\\|fast -> flann<br>verified | 0.5 | 0.75 |", markdown_text)


class AdaptiveFastRunnerPackagingUnitTest(unittest.TestCase):
    def test_runner_script_exists_and_is_executable(self):
        self.assertTrue(RUNNER_PATH.is_file())
        if os.name == "nt":
            self.skipTest("POSIX executable bits are not meaningful on native Windows.")
        mode = RUNNER_PATH.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)
        self.assertTrue(os.access(RUNNER_PATH, os.X_OK))

    def test_runner_script_packages_expected_adaptive_fast_flags(self):
        script_text = RUNNER_PATH.read_text(encoding="utf-8")

        self.assertIn("--matcher-method flann", script_text)
        self.assertIn("--adaptive-routing", script_text)
        self.assertIn("--adaptive-routing-profile", script_text)
        self.assertIn("--validate-only", script_text)
        self.assertIn("--validate-parameters-only", script_text)
        self.assertIn("run_final_merge=0", script_text)
        self.assertIn("--run-final-merge", script_text)
        self.assertIn("--skip-final-merge", script_text)
        self.assertIn("summarize_adaptive_fast_pipeline.py", script_text)
        self.assertIn("--json-output", script_text)
        self.assertIn("--markdown-output", script_text)


if __name__ == "__main__":
    unittest.main()
