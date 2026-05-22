"""Unit tests for the ControlNet matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.experiments import matcher_comparison


def _write_minimal_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": "unit_run",
                "description": "unit test matcher comparison",
                "inputs": {
                    "original_images_list": "original_images.lis",
                    "doms_list": "doms_scaled.lis",
                    "controlnet_config": "examples/controlnet_construct/controlnet_config.example.json",
                },
                "execution": {
                    "asp360_env": "asp360_new",
                    "deep_learning_env": "deep-learning",
                    "device": "auto",
                    "skip_final_merge": True,
                    "keep_going": True,
                    "resume": True,
                },
                "methods": [
                    {"label": "sift_flann", "matcher_method": "flann"},
                    {
                        "label": "loftr",
                        "matcher_method": "loftr",
                        "deep_match_config_path": "examples/controlnet_construct/presets/loftr_default.json",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class MatcherComparisonConfigUnitTest(unittest.TestCase):
    def test_load_experiment_config_expands_inputs_execution_and_methods(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)

            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "unit_run")
        self.assertEqual(config.execution.asp360_env, "asp360_new")
        self.assertEqual(config.execution.deep_learning_env, "deep-learning")
        self.assertTrue(config.execution.skip_final_merge)
        self.assertEqual(config.inputs.original_images_list, PROJECT_ROOT / "original_images.lis")
        self.assertEqual(config.inputs.doms_list, PROJECT_ROOT / "doms_scaled.lis")
        self.assertEqual(config.methods[0].label, "sift_flann")
        self.assertFalse(config.methods[0].is_deep_method)
        self.assertEqual(
            config.methods[1].deep_match_config_path,
            PROJECT_ROOT / "examples/controlnet_construct/presets/loftr_default.json",
        )
        self.assertTrue(config.methods[1].is_deep_method)

    def test_load_experiment_config_rejects_duplicate_method_labels(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"].append({"label": "sift_flann", "matcher_method": "flann"})
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate method label"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_experiment_config_rejects_deep_method_without_preset(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"] = [{"label": "bad_lightglue", "matcher_method": "lightglue"}]
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requires deep_match_config_path"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
