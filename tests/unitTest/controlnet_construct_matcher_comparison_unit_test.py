"""Unit tests for the ControlNet matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import subprocess
import unittest
from unittest import mock


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


def _write_config_with_temp_inputs(config_path: Path, temp_dir: Path) -> None:
    _write_minimal_config(config_path)
    original_images = temp_dir / "original_images.lis"
    doms = temp_dir / "doms_scaled.lis"
    original_images.write_text("image_1.cub\nimage_2.cub\n", encoding="utf-8")
    doms.write_text("dom_1.cub\ndom_2.cub\n", encoding="utf-8")

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["inputs"]["original_images_list"] = str(original_images)
    payload["inputs"]["doms_list"] = str(doms)
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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

    def test_load_experiment_config_rejects_path_traversal_run_id(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["run_id"] = "../escape"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "run_id must match"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_experiment_config_rejects_path_traversal_method_label(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"][0]["label"] = "bad/label"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "label must match"):
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
        preset_flag_index = command.index("--deep-match-config-path")
        self.assertEqual(
            command[preset_flag_index + 1],
            str(PROJECT_ROOT / "examples/controlnet_construct/presets/loftr_default.json"),
        )

    def test_build_method_command_deep_pipeline_keep_going_controls_failure_flags(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            method = config.methods[1]

            keep_going_command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=temp_dir / "loftr_keep_going",
                repo_root=PROJECT_ROOT,
                keep_going=True,
            )
            fail_fast_command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=temp_dir / "loftr_fail_fast",
                repo_root=PROJECT_ROOT,
                keep_going=False,
            )

        self.assertIn("--no-fail-fast", keep_going_command)
        self.assertIn("--continue-on-deep-failure", keep_going_command)
        self.assertNotIn("--no-fail-fast", fail_fast_command)
        self.assertNotIn("--continue-on-deep-failure", fail_fast_command)

    def test_run_deep_match_pipeline_dry_run_forwards_deep_match_config_path_to_export_and_import(self):
        with temporary_directory() as temp_dir:
            fake_bin = temp_dir / "bin"
            fake_bin.mkdir()
            fake_conda = fake_bin / "conda"
            fake_conda.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake_conda.chmod(0o755)
            preset_path = PROJECT_ROOT / "examples/controlnet_construct/presets/loftr_default.json"
            script_path = PROJECT_ROOT / "examples/controlnet_construct/run_deep_match_pipeline.sh"
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    "--dry-run",
                    "--work-dir",
                    str(temp_dir / "work"),
                    "--matcher-method",
                    "loftr",
                    "--deep-match-config-path",
                    str(preset_path),
                ],
                check=False,
                capture_output=True,
                encoding="utf-8",
                env=env,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = result.stdout + result.stderr
        self.assertEqual(output.count(f"--deep-match-config-path {preset_path}"), 2)


class MatcherComparisonRunUnitTest(unittest.TestCase):
    def _fake_command_for_method(self, method):
        if method.label == "sift_flann":
            return [
                sys.executable,
                "-c",
                "print('fake sift success')",
            ]
        return [
            sys.executable,
            "-c",
            "print('fake loftr success')",
        ]

    def test_run_experiment_dry_run_writes_manifest_and_command_scripts(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels=None,
                resume=False,
                keep_going=True,
            )

            self.assertEqual(result.run_dir, temp_dir / "out/unit_run")
            self.assertTrue((result.run_dir / "experiment_manifest.json").exists())
            self.assertTrue((result.run_dir / "methods/sift_flann/command.sh").exists())
            self.assertTrue((result.run_dir / "methods/loftr/command.sh").exists())
            self.assertEqual(
                (result.run_dir / "methods/sift_flann/work/original_images.lis").read_text(encoding="utf-8"),
                "image_1.cub\nimage_2.cub\n",
            )
            self.assertEqual(
                (result.run_dir / "methods/sift_flann/work/doms_scaled.lis").read_text(encoding="utf-8"),
                "dom_1.cub\ndom_2.cub\n",
            )
            self.assertFalse((result.run_dir / "methods/sift_flann/stdout.log").exists())
            self.assertFalse((result.run_dir / "methods/loftr/stdout.log").exists())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["dry_run"])
            self.assertEqual(result.status, "dry_run")
            self.assertEqual(manifest["status"], "dry_run")
            self.assertFalse(manifest["resume"])
            self.assertTrue(manifest["keep_going"])
            self.assertEqual(
                {method["label"]: method["status"] for method in manifest["methods"]},
                {"sift_flann": "dry_run", "loftr": "dry_run"},
            )

    def test_run_experiment_example_config_dry_run_allows_missing_input_lists(self):
        with temporary_directory() as temp_dir:
            config_path = PROJECT_ROOT / "examples/controlnet_construct/experiments/matcher_comparison.example.json"

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"sift_flann"},
                resume=False,
                keep_going=True,
            )

            self.assertTrue(result.manifest_path.exists())
            self.assertTrue((result.run_dir / "methods/sift_flann/command.sh").exists())
            self.assertFalse((result.run_dir / "methods/sift_flann/work/original_images.lis").exists())
            self.assertFalse((result.run_dir / "methods/sift_flann/work/doms_scaled.lis").exists())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["methods"][0]["warnings"],
                [
                    f"Dry-run input list missing; not copied: {PROJECT_ROOT / 'work/original_images.lis'}",
                    f"Dry-run input list missing; not copied: {PROJECT_ROOT / 'work/doms_scaled.lis'}",
                ],
            )

    def test_run_experiment_dry_run_missing_inputs_removes_stale_target_lists(self):
        with temporary_directory() as temp_dir:
            config_path = PROJECT_ROOT / "examples/controlnet_construct/experiments/matcher_comparison.example.json"
            stale_work_dir = temp_dir / "out/lro_batch_20260522/methods/sift_flann/work"
            stale_work_dir.mkdir(parents=True)
            (stale_work_dir / "original_images.lis").write_text("stale originals\n", encoding="utf-8")
            (stale_work_dir / "doms_scaled.lis").write_text("stale doms\n", encoding="utf-8")

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"sift_flann"},
                resume=False,
                keep_going=True,
            )

            self.assertFalse((stale_work_dir / "original_images.lis").exists())
            self.assertFalse((stale_work_dir / "doms_scaled.lis").exists())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["methods"][0]["warnings"],
                [
                    f"Dry-run input list missing; not copied: {PROJECT_ROOT / 'work/original_images.lis'}",
                    f"Dry-run input list missing; not copied: {PROJECT_ROOT / 'work/doms_scaled.lis'}",
                ],
            )

    def test_run_experiment_dry_run_command_script_quotes_paths_with_spaces(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out with spaces",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"sift_flann"},
                resume=False,
                keep_going=True,
            )

            command_script = (result.run_dir / "methods/sift_flann/command.sh").read_text(encoding="utf-8")
            expected_work_dir = temp_dir / "out with spaces/unit_run/methods/sift_flann/work"
            self.assertIn(f"'{expected_work_dir}'", command_script)

    def test_run_experiment_only_limits_methods(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"loftr"},
                resume=False,
                keep_going=True,
            )

            self.assertFalse((result.run_dir / "methods/sift_flann").exists())
            self.assertTrue((result.run_dir / "methods/loftr/command.sh").exists())

    def test_run_experiment_resume_skips_successful_metrics(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)
            method_dir = temp_dir / "out/unit_run/methods/sift_flann"
            method_dir.mkdir(parents=True)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            command = matcher_comparison.build_method_command(
                config,
                config.methods[0],
                method_dir=method_dir,
                repo_root=PROJECT_ROOT,
            )
            metrics_path = method_dir / "metrics.json"
            metrics_path.write_text(json.dumps({"status": "success", "command": command}), encoding="utf-8")

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels=None,
                resume=True,
                keep_going=True,
            )

            self.assertEqual(json.loads(metrics_path.read_text(encoding="utf-8"))["status"], "success")
            self.assertFalse((result.run_dir / "methods/sift_flann/command.sh").exists())
            self.assertTrue((result.run_dir / "methods/loftr/command.sh").exists())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["methods"][0]["status"], "skipped_success")
            self.assertEqual(manifest["methods"][1]["status"], "dry_run")

    def test_run_experiment_resume_regenerates_command_for_stale_success_metrics(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)
            method_dir = temp_dir / "out/unit_run/methods/sift_flann"
            method_dir.mkdir(parents=True)
            metrics_path = method_dir / "metrics.json"
            metrics_path.write_text(
                json.dumps({"status": "success", "command": ["bash", "old-command.sh"]}),
                encoding="utf-8",
            )

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"sift_flann"},
                resume=True,
                keep_going=True,
            )

            self.assertTrue((result.run_dir / "methods/sift_flann/command.sh").exists())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["methods"][0]["status"], "dry_run")
            self.assertNotEqual(manifest["methods"][0]["command"], ["bash", "old-command.sh"])

    def test_run_experiment_non_dry_run_executes_fake_commands_and_records_success(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            def fake_build_method_command(config, method, *, method_dir, repo_root, keep_going=None):
                return self._fake_command_for_method(method)

            with mock.patch.object(
                matcher_comparison,
                "build_method_command",
                side_effect=fake_build_method_command,
            ):
                result = matcher_comparison.run_experiment(
                    config_path,
                    output_root=temp_dir / "out",
                    repo_root=PROJECT_ROOT,
                    dry_run=False,
                    only_labels=None,
                    resume=False,
                    keep_going=True,
                )

            sift_dir = result.run_dir / "methods/sift_flann"
            loftr_dir = result.run_dir / "methods/loftr"
            self.assertTrue((sift_dir / "command.sh").exists())
            self.assertTrue((loftr_dir / "command.sh").exists())
            self.assertIn("fake sift success", (sift_dir / "stdout.log").read_text(encoding="utf-8"))
            self.assertIn("fake loftr success", (loftr_dir / "stdout.log").read_text(encoding="utf-8"))
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["dry_run"])
            self.assertEqual(result.status, "success")
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(
                {method["label"]: method["status"] for method in manifest["methods"]},
                {"sift_flann": "success", "loftr": "success"},
            )

    def test_run_experiment_non_dry_run_stops_after_failure_when_fail_fast(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            def fake_build_method_command(config, method, *, method_dir, repo_root, keep_going=None):
                if method.label == "sift_flann":
                    return [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"]
                return self._fake_command_for_method(method)

            with mock.patch.object(
                matcher_comparison,
                "build_method_command",
                side_effect=fake_build_method_command,
            ):
                result = matcher_comparison.run_experiment(
                    config_path,
                    output_root=temp_dir / "out",
                    repo_root=PROJECT_ROOT,
                    dry_run=False,
                    only_labels=None,
                    resume=False,
                    keep_going=False,
                )

            run_dir = temp_dir / "out/unit_run"
            self.assertIn("bad", (run_dir / "methods/sift_flann/stderr.log").read_text(encoding="utf-8"))
            self.assertFalse((run_dir / "methods/loftr/command.sh").exists())
            manifest = json.loads((run_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result.status, "failed")
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual([method["label"] for method in manifest["methods"]], ["sift_flann"])
            self.assertEqual(manifest["methods"][0]["status"], "failed")

    def test_run_experiment_non_dry_run_keeps_going_after_failure_when_enabled(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            def fake_build_method_command(config, method, *, method_dir, repo_root, keep_going=None):
                if method.label == "sift_flann":
                    return [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"]
                return self._fake_command_for_method(method)

            with mock.patch.object(
                matcher_comparison,
                "build_method_command",
                side_effect=fake_build_method_command,
            ):
                result = matcher_comparison.run_experiment(
                    config_path,
                    output_root=temp_dir / "out",
                    repo_root=PROJECT_ROOT,
                    dry_run=False,
                    only_labels=None,
                    resume=False,
                    keep_going=True,
                )

            run_dir = result.run_dir
            self.assertIn("bad", (run_dir / "methods/sift_flann/stderr.log").read_text(encoding="utf-8"))
            self.assertIn("fake loftr success", (run_dir / "methods/loftr/stdout.log").read_text(encoding="utf-8"))
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(result.status, "failed")
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(
                {method["label"]: method["status"] for method in manifest["methods"]},
                {"sift_flann": "failed", "loftr": "success"},
            )

    def test_main_returns_nonzero_when_keep_going_run_has_failed_method(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            def fake_build_method_command(config, method, *, method_dir, repo_root, keep_going=None):
                if method.label == "sift_flann":
                    return [sys.executable, "-c", "import sys; sys.exit(7)"]
                return self._fake_command_for_method(method)

            with mock.patch.object(
                matcher_comparison,
                "build_method_command",
                side_effect=fake_build_method_command,
            ):
                return_code = matcher_comparison.main(
                    [
                        str(config_path),
                        "--output-root",
                        str(temp_dir / "out"),
                        "--repo-root",
                        str(PROJECT_ROOT),
                        "--no-resume",
                        "--keep-going",
                    ]
                )

            self.assertEqual(return_code, 1)
            manifest = json.loads((temp_dir / "out/unit_run/experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")

    def test_main_returns_nonzero_when_fail_fast_run_has_failed_method(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            def fake_build_method_command(config, method, *, method_dir, repo_root, keep_going=None):
                if method.label == "sift_flann":
                    return [sys.executable, "-c", "import sys; sys.exit(7)"]
                return self._fake_command_for_method(method)

            with mock.patch.object(
                matcher_comparison,
                "build_method_command",
                side_effect=fake_build_method_command,
            ):
                return_code = matcher_comparison.main(
                    [
                        str(config_path),
                        "--output-root",
                        str(temp_dir / "out"),
                        "--repo-root",
                        str(PROJECT_ROOT),
                        "--no-resume",
                        "--fail-fast",
                    ]
                )

            self.assertEqual(return_code, 1)
            manifest = json.loads((temp_dir / "out/unit_run/experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual([method["label"] for method in manifest["methods"]], ["sift_flann"])

    def test_main_returns_zero_for_dry_run_manifest_generation(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_config_with_temp_inputs(config_path, temp_dir)

            return_code = matcher_comparison.main(
                [
                    str(config_path),
                    "--output-root",
                    str(temp_dir / "out"),
                    "--repo-root",
                    str(PROJECT_ROOT),
                    "--dry-run",
                    "--no-resume",
                ]
            )

            self.assertEqual(return_code, 0)
            manifest = json.loads((temp_dir / "out/unit_run/experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "dry_run")

    def test_run_matcher_comparison_script_exec_help(self):
        script_path = PROJECT_ROOT / "examples/controlnet_construct/experiments/run_matcher_comparison.py"
        self.assertTrue(os.access(script_path, os.X_OK))

        result = subprocess.run(
            [str(script_path), "--help"],
            check=False,
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Run a ControlNet matcher comparison experiment.", result.stdout)

    def test_parse_only_rejects_explicit_empty_filter(self):
        for value in ("", ",", " , "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "--only must include at least one method label"):
                    matcher_comparison._parse_only(value)


class MatcherComparisonMetricsUnitTest(unittest.TestCase):
    def test_collect_method_metrics_reads_pipeline_outputs_defensively(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "sift_flann"
            reports_dir = method_dir / "work/reports"
            pair_nets_dir = method_dir / "work/pair_nets"
            merge_dir = method_dir / "work/merge"
            reports_dir.mkdir(parents=True)
            pair_nets_dir.mkdir(parents=True)
            merge_dir.mkdir(parents=True)
            (reports_dir / "image_overlap_summary.json").write_text(
                json.dumps({"pair_count": 2}),
                encoding="utf-8",
            )
            (reports_dir / "controlnet_batch_summary.json").write_text(
                json.dumps(
                    {
                        "pair_count": 2,
                        "total_final_control_point_count": 15,
                        "total_dom2ori_retained_count": 12,
                    }
                ),
                encoding="utf-8",
            )
            (reports_dir / "pipeline_timing.json").write_text(
                json.dumps(
                    {
                        "pipeline": {"status": "success"},
                        "steps": [
                            {"name": "image_overlap", "duration_seconds": 10},
                            {"name": "image_match_batch", "duration_seconds": 12.5},
                            {"name": "pairwise_controlnets", "duration_seconds": "ignored"},
                            {"name": "merge_control_measure", "duration_seconds": True},
                            {"name": "merge", "duration_seconds": 22},
                            {"name": "post_merge_control_measure"},
                        ],
                        "pair_matches": [{"name": "S1", "duration_seconds": 99}],
                    }
                ),
                encoding="utf-8",
            )
            (pair_nets_dir / "S1.net").write_text("net 1\n", encoding="utf-8")
            (pair_nets_dir / "S2.net").write_text("net 2\n", encoding="utf-8")
            (merge_dir / "dom_matching_merged.net").write_text("merged\n", encoding="utf-8")

            metrics = matcher_comparison.collect_method_metrics("sift_flann", method_dir)

        self.assertEqual(metrics["label"], "sift_flann")
        self.assertEqual(metrics["pair_count"], 2)
        self.assertEqual(metrics["pairwise_controlnet_count"], 2)
        self.assertTrue(metrics["merged_controlnet_exists"])
        self.assertEqual(metrics["total_final_control_point_count"], 15)
        self.assertEqual(metrics["total_dom2ori_retained_count"], 12)
        self.assertEqual(metrics["pipeline_total_seconds"], 44.5)

    def test_collect_method_metrics_tolerates_missing_optional_outputs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "sift_flann"
            (method_dir / "work").mkdir(parents=True)

            metrics = matcher_comparison.collect_method_metrics("sift_flann", method_dir)

        self.assertEqual(metrics["pair_count"], None)
        self.assertEqual(metrics["pairwise_controlnet_count"], 0)
        self.assertFalse(metrics["merged_controlnet_exists"])
        self.assertTrue(metrics["warnings"])

    def test_collect_method_metrics_warns_when_timing_total_cannot_be_derived(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "sift_flann"
            reports_dir = method_dir / "work/reports"
            reports_dir.mkdir(parents=True)
            (reports_dir / "pipeline_timing.json").write_text(
                json.dumps(
                    {
                        "pipeline": {"status": "success"},
                        "steps": [
                            {"name": "image_overlap", "duration_seconds": "unknown"},
                            {"name": "image_match_batch"},
                        ],
                        "pair_matches": [],
                    }
                ),
                encoding="utf-8",
            )

            metrics = matcher_comparison.collect_method_metrics("sift_flann", method_dir)

        self.assertEqual(metrics["pipeline_total_seconds"], None)
        self.assertTrue(
            any("could not derive pipeline_total_seconds" in warning for warning in metrics["warnings"]),
            msg=metrics["warnings"],
        )


class MatcherComparisonExecutionUnitTest(unittest.TestCase):
    def test_execute_method_writes_success_metrics_and_logs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            command = [sys.executable, "-c", "print('hello from fake method')"]

            metrics = matcher_comparison.execute_method(
                label="fake_success",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "success")
            self.assertEqual(metrics["return_code"], 0)
            self.assertGreaterEqual(metrics["total_wall_seconds"], 0)
            self.assertIn("hello from fake method", (method_dir / "stdout.log").read_text(encoding="utf-8"))
            self.assertEqual((method_dir / "stderr.log").read_text(encoding="utf-8"), "")
            metrics_payload = json.loads((method_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics_payload["status"], "success")

    def test_execute_method_merges_collected_output_metrics_after_success(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            script = (
                "from pathlib import Path\n"
                "import json\n"
                f"method_dir = Path({str(method_dir)!r})\n"
                "reports_dir = method_dir / 'work/reports'\n"
                "pair_nets_dir = method_dir / 'work/pair_nets'\n"
                "merge_dir = method_dir / 'work/merge'\n"
                "reports_dir.mkdir(parents=True)\n"
                "pair_nets_dir.mkdir(parents=True)\n"
                "merge_dir.mkdir(parents=True)\n"
                "(reports_dir / 'image_overlap_summary.json').write_text(json.dumps({'pair_count': 2}), encoding='utf-8')\n"
                "(reports_dir / 'controlnet_batch_summary.json').write_text(json.dumps({'total_final_control_point_count': 15}), encoding='utf-8')\n"
                "(reports_dir / 'pipeline_timing.json').write_text(json.dumps({'total_seconds': 44.5}), encoding='utf-8')\n"
                "(pair_nets_dir / 'S1.net').write_text('net 1\\n', encoding='utf-8')\n"
                "(merge_dir / 'dom_matching_merged.net').write_text('merged\\n', encoding='utf-8')\n"
            )
            command = [sys.executable, "-c", script]

            metrics = matcher_comparison.execute_method(
                label="fake_success",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "success")
            self.assertEqual(metrics["return_code"], 0)
            self.assertEqual(metrics["pair_count"], 2)
            self.assertEqual(metrics["pairwise_controlnet_count"], 1)
            self.assertTrue(metrics["merged_controlnet_exists"])
            self.assertEqual(metrics["total_final_control_point_count"], 15)
            self.assertEqual(metrics["pipeline_total_seconds"], 44.5)
            metrics_payload = json.loads((method_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics_payload["status"], "success")
            self.assertEqual(metrics_payload["pair_count"], 2)

    def test_execute_method_writes_failed_metrics_and_logs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            command = [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"]

            metrics = matcher_comparison.execute_method(
                label="fake_failure",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "failed")
            self.assertEqual(metrics["return_code"], 7)
            self.assertIn("bad", (method_dir / "stderr.log").read_text(encoding="utf-8"))

    def test_execute_method_writes_failed_metrics_when_launch_fails(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            command = [str(temp_dir / "missing_executable")]

            metrics = matcher_comparison.execute_method(
                label="fake_launch_failure",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "failed")
            self.assertIsNone(metrics["return_code"])
            self.assertEqual(metrics["error_type"], "FileNotFoundError")
            stderr_text = (method_dir / "stderr.log").read_text(encoding="utf-8")
            self.assertIn("FileNotFoundError", stderr_text)
            self.assertIn(str(temp_dir / "missing_executable"), stderr_text)
            metrics_payload = json.loads((method_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics_payload["status"], "failed")
            self.assertEqual(metrics_payload["error_type"], "FileNotFoundError")


if __name__ == "__main__":
    unittest.main()
