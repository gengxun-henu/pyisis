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

    def test_load_experiment_config_rejects_unsupported_matcher_method(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"] = [{"label": "bad_matcher", "matcher_method": "orb"}]
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "Unsupported matcher_method.*orb.*bf.*flann.*superpoint.*superglue.*lightglue.*loftr",
            ):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_experiment_config_accepts_superpoint_without_deep_preset(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"] = [{"label": "superpoint_baseline", "matcher_method": "superpoint"}]
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.methods[0].label, "superpoint_baseline")
        self.assertEqual(config.methods[0].matcher_method, "superpoint")
        self.assertIsNone(config.methods[0].deep_match_config_path)
        self.assertFalse(config.methods[0].is_deep_method)

    def test_load_experiment_config_rejects_string_false_for_skip_final_merge(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["execution"]["skip_final_merge"] = "false"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "skip_final_merge must be a boolean"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_experiment_config_prefers_existing_config_relative_path(self):
        with temporary_directory() as temp_dir:
            config_dir = temp_dir / "config_dir"
            config_dir.mkdir()
            original_images = config_dir / "original_images.lis"
            original_images.write_text("config relative input\n", encoding="utf-8")
            config_path = config_dir / "experiment.json"
            _write_minimal_config(config_path)

            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.inputs.original_images_list, original_images.resolve())

    def test_example_config_loads_with_seven_methods(self):
        config_path = PROJECT_ROOT / "examples/controlnet_construct/experiments/matcher_comparison.example.json"

        config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "lro_batch_20260522")
        self.assertEqual(len(config.methods), 7)

    def test_prepare_method_workspace_copies_input_lists_to_wrapper_default_names(self):
        with temporary_directory() as temp_dir:
            source_original = temp_dir / "source_originals.lis"
            source_doms = temp_dir / "source_doms.lis"
            source_original.write_text("original 1\noriginal 2\n", encoding="utf-8")
            source_doms.write_text("dom 1\ndom 2\n", encoding="utf-8")
            method_dir = temp_dir / "method"

            work_dir = matcher_comparison.prepare_method_workspace(
                method_dir,
                original_images_list=source_original,
                doms_list=source_doms,
            )

            self.assertEqual(work_dir, method_dir.resolve() / "work")
            self.assertEqual(
                (method_dir / "work/original_images.lis").read_text(encoding="utf-8"),
                "original 1\noriginal 2\n",
            )
            self.assertEqual(
                (method_dir / "work/doms_scaled.lis").read_text(encoding="utf-8"),
                "dom 1\ndom 2\n",
            )

    def test_build_method_command_uses_plain_pipeline_for_flann(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            method = config.methods[0]
            method_dir = temp_dir / "sift_flann"

            command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=method_dir,
                repo_root=PROJECT_ROOT,
            )

        self.assertIn("bash", command)
        self.assertIn(
            str(PROJECT_ROOT / "examples/controlnet_construct/run_pipeline_example.sh"),
            command,
        )
        self.assertIn("--work-dir", command)
        self.assertIn(str(method_dir.resolve() / "work"), command)
        self.assertIn("--matcher-method", command)
        self.assertIn("flann", command)
        self.assertIn("--skip-final-merge", command)
        self.assertNotIn(
            str(PROJECT_ROOT / "examples/controlnet_construct/run_deep_match_pipeline.sh"),
            command,
        )

    def test_build_method_command_uses_deep_pipeline_for_loftr(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            method = config.methods[1]
            method_dir = temp_dir / "loftr"

            command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=method_dir,
                repo_root=PROJECT_ROOT,
            )

        self.assertIn(
            str(PROJECT_ROOT / "examples/controlnet_construct/run_deep_match_pipeline.sh"),
            command,
        )
        self.assertIn("--asp360-env", command)
        self.assertIn("asp360_new", command)
        self.assertIn("--deep-learning-env", command)
        self.assertIn("deep-learning", command)
        self.assertIn("--device", command)
        self.assertIn("auto", command)
        self.assertIn("--matcher-method", command)
        self.assertIn("loftr", command)


if __name__ == "__main__":
    unittest.main()
