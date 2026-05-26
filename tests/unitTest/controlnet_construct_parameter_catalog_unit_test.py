"""Tests for the shared ControlNet parameter catalog."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))


class ControlNetParameterCatalogUnitTest(unittest.TestCase):
    def test_catalog_cli_prints_grouped_pipeline_help(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--entrypoint",
                "run_pipeline_example",
                "--format",
                "text",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Parameter groups for run_pipeline_example", result.stdout)
        self.assertIn("Matching", result.stdout)
        self.assertIn("--matcher-method", result.stdout)
        self.assertIn("Low Resolution", result.stdout)
        self.assertIn("--low-resolution-level", result.stdout)

    def test_catalog_text_prints_canonical_names_defaults_allowed_values_and_config_paths(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--entrypoint",
                "run_pipeline_example",
                "--format",
                "text",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--matcher-method", result.stdout)
        self.assertIn("name: matcher_method", result.stdout)
        self.assertIn("allowed: bf", result.stdout)
        self.assertIn("config: ImageMatch.matcher_method", result.stdout)
        self.assertIn("--strict-parameter-validation", result.stdout)
        self.assertIn("default: False", result.stdout)

    def test_run_pipeline_catalog_marks_config_only_parameters_without_cli_flags(self):
        from controlnet_construct.parameter_catalog import parameter_catalog_as_dict

        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--entrypoint",
                "run_pipeline_example",
                "--format",
                "text",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("  ratio_test:", result.stdout)
        self.assertIn("  use_gpu:", result.stdout)
        self.assertIn("cli: config-only for run_pipeline_example", result.stdout)
        self.assertNotIn("  --ratio-test:", result.stdout)
        self.assertNotIn("  --use-gpu:", result.stdout)

        catalog = parameter_catalog_as_dict(entrypoint="run_pipeline_example")
        parameters = {parameter["name"]: parameter for parameter in catalog["parameters"]}
        self.assertIsNone(parameters["ratio_test"]["cli_flag"])
        self.assertIsNone(parameters["use_gpu"]["cli_flag"])
        self.assertEqual(parameters["matcher_method"]["cli_flag"], "--matcher-method")

    def test_catalog_cli_validates_payload_json(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"
        payload = {
            "entrypoint": "run_pipeline_example",
            "cli_values": {
                "matcher_method": "bf",
                "work_dir": "work with space",
                "validate_parameters_only": True,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--validate-json",
                    str(payload_path),
                    "--shell-assignments",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MATCHER_METHOD=bf", result.stdout)
        self.assertIn("WORK_DIR='work with space'", result.stdout)

    def test_catalog_cli_rejects_unknown_payload_field(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"
        payload = {
            "entrypoint": "run_pipeline_example",
            "cli_values": {"matcher_mtehod": "bf"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--validate-json",
                    str(payload_path),
                    "--shell-assignments",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("matcher_mtehod", result.stderr)

    def test_catalog_cli_rejects_unknown_entrypoint_for_catalog_printing(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--entrypoint",
                "unknown_entrypoint",
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown_entrypoint", result.stderr)

    def test_required_groups_are_declared_in_expected_order(self):
        from controlnet_construct.parameter_catalog import PARAMETER_GROUPS

        self.assertEqual(
            tuple(group.name for group in PARAMETER_GROUPS),
            (
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
            ),
        )

    def test_core_fields_have_group_cli_config_and_entrypoints(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME

        matcher = PARAMETER_BY_NAME["matcher_method"]
        self.assertEqual(matcher.group, "matching")
        self.assertEqual(matcher.cli_flag, "--matcher-method")
        self.assertEqual(matcher.config_path, "ImageMatch.matcher_method")
        self.assertIn("run_pipeline_example", matcher.entrypoints)
        self.assertIn("image_match", matcher.entrypoints)
        self.assertIn("controlnet_stereopair.from-ori-match", matcher.entrypoints)

        low_res = PARAMETER_BY_NAME["low_resolution_level"]
        self.assertEqual(low_res.group, "low_resolution")
        self.assertEqual(low_res.cli_flag, "--low-resolution-level")
        self.assertEqual(low_res.config_path, "ImageMatch.low_resolution_level")
        self.assertEqual(low_res.min_value, 0)

        invalid_pixel_radius = PARAMETER_BY_NAME["invalid_pixel_radius"]
        self.assertEqual(invalid_pixel_radius.group, "tile")
        self.assertEqual(invalid_pixel_radius.cli_flag, "--invalid-pixel-radius")
        self.assertEqual(invalid_pixel_radius.config_path, "ImageMatch.invalid_pixel_radius")
        self.assertEqual(invalid_pixel_radius.min_value, 0)
        self.assertEqual(invalid_pixel_radius.max_value, 100)

        valid_pixel_threshold = PARAMETER_BY_NAME["valid_pixel_percent_threshold"]
        self.assertEqual(valid_pixel_threshold.group, "tile")
        self.assertEqual(valid_pixel_threshold.cli_flag, "--valid-pixel-percent-threshold")
        self.assertEqual(valid_pixel_threshold.config_path, "ImageMatch.valid_pixel_percent_threshold")
        self.assertEqual(valid_pixel_threshold.min_value, 0.0)
        self.assertEqual(valid_pixel_threshold.max_value, 1.0)

        pair_id_start = PARAMETER_BY_NAME["pair_id_start"]
        self.assertEqual(pair_id_start.group, "controlnet")
        self.assertEqual(pair_id_start.cli_flag, "--pair-id-start")
        self.assertEqual(pair_id_start.min_value, 1)

        strict = PARAMETER_BY_NAME["strict_parameter_validation"]
        self.assertEqual(strict.group, "reporting")
        self.assertEqual(strict.cli_flag, "--strict-parameter-validation")
        self.assertIn("run_pipeline_example", strict.entrypoints)

        profile = PARAMETER_BY_NAME["parameter_profile"]
        self.assertEqual(profile.group, "pipeline")
        self.assertEqual(profile.cli_flag, "--parameter-profile")
        self.assertEqual(profile.allowed_values, ("conservative", "balanced", "aggressive"))
        self.assertIn("run_pipeline_example", profile.entrypoints)

    def test_run_pipeline_catalog_covers_wrapper_validation_surface(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME

        expected_fields = {
            "deep_match_mode",
            "deep_match_temp_root_dir",
            "deep_match_manifest_dir",
            "deep_match_manifest_summary",
            "match_preset_path",
            "matcher_method",
            "deep_match_config_path",
            "valid_pixel_percent_threshold",
            "invalid_pixel_radius",
            "enable_low_resolution_offset_estimation",
            "low_resolution_level",
            "low_resolution_max_mean_reprojection_error_pixels",
            "low_resolution_min_retained_match_count",
            "low_resolution_max_mean_projected_offset_meters",
            "adaptive_routing_profile",
            "use_parallel_cpu",
            "num_worker_parallel_cpu",
            "visualization_mode",
            "memory_profile",
            "visualization_target_long_edge",
            "preview_crop_margin_pixels",
            "preview_cache_source",
            "pair_id_start",
            "merged_net",
            "merge_script",
            "merge_log",
            "pair_list",
            "timing_json",
            "skip_final_merge",
            "post_merge_control_measure",
            "post_merge_output",
            "post_merge_decimals",
            "strict_parameter_validation",
        }

        missing = sorted(field for field in expected_fields if field not in PARAMETER_BY_NAME)
        self.assertEqual(missing, [])
        for field in expected_fields:
            self.assertIn("run_pipeline_example", PARAMETER_BY_NAME[field].entrypoints, field)

    def test_run_pipeline_catalog_uses_actual_wrapper_adaptive_routing_flag(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME

        adaptive = PARAMETER_BY_NAME["enable_adaptive_routing"]
        self.assertEqual(adaptive.cli_flag, "--adaptive-routing")
        self.assertIn("run_pipeline_example", adaptive.entrypoints)

    def test_allowed_values_match_runtime_constants(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME
        from image_match.adaptive_routing import SUPPORTED_ADAPTIVE_ROUTING_PROFILES
        from image_match.image_match import SUPPORTED_DEEP_MATCH_MODES
        from image_match.match_visualization import (
            SUPPORTED_MEMORY_PROFILES,
            SUPPORTED_PREVIEW_CACHE_SOURCES,
            SUPPORTED_VISUALIZATION_MODES,
        )
        from image_match.tile_matching import SUPPORTED_MATCHER_METHODS

        self.assertEqual(PARAMETER_BY_NAME["matcher_method"].allowed_values, tuple(SUPPORTED_MATCHER_METHODS))
        self.assertEqual(PARAMETER_BY_NAME["deep_match_mode"].allowed_values, tuple(SUPPORTED_DEEP_MATCH_MODES))
        self.assertEqual(
            PARAMETER_BY_NAME["adaptive_routing_profile"].allowed_values,
            tuple(SUPPORTED_ADAPTIVE_ROUTING_PROFILES),
        )
        self.assertEqual(PARAMETER_BY_NAME["visualization_mode"].allowed_values, tuple(SUPPORTED_VISUALIZATION_MODES))
        self.assertEqual(PARAMETER_BY_NAME["memory_profile"].allowed_values, tuple(SUPPORTED_MEMORY_PROFILES))
        self.assertEqual(
            PARAMETER_BY_NAME["preview_cache_source"].allowed_values,
            tuple(SUPPORTED_PREVIEW_CACHE_SOURCES),
        )

    def test_grouped_catalog_filters_by_entrypoint(self):
        from controlnet_construct.parameter_catalog import grouped_parameters_for_entrypoint

        grouped = grouped_parameters_for_entrypoint("run_pipeline_example")
        self.assertIn("matching", grouped)
        self.assertIn("matcher_method", [parameter.name for parameter in grouped["matching"]])
        self.assertIn("pipeline", grouped)
        self.assertIn("deep_match_mode", [parameter.name for parameter in grouped["pipeline"]])

        image_match_grouped = grouped_parameters_for_entrypoint("image_match")
        self.assertNotIn("controlnet", image_match_grouped)

    def test_deep_match_import_manifest_parameters_are_entrypoint_specific(self):
        from controlnet_construct.parameter_catalog import parameters_for_entrypoint

        run_pipeline_names = {parameter.name for parameter in parameters_for_entrypoint("run_pipeline_example")}
        image_match_names = {parameter.name for parameter in parameters_for_entrypoint("image_match")}

        self.assertIn("deep_match_manifest_dir", run_pipeline_names)
        self.assertNotIn("deep_match_manifest", run_pipeline_names)
        self.assertIn("deep_match_manifest", image_match_names)
        self.assertNotIn("deep_match_manifest_dir", image_match_names)


if __name__ == "__main__":
    unittest.main()
