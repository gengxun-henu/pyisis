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

        strict = PARAMETER_BY_NAME["strict_parameter_validation"]
        self.assertEqual(strict.group, "reporting")
        self.assertEqual(strict.cli_flag, "--strict-parameter-validation")
        self.assertIn("run_pipeline_example", strict.entrypoints)

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
