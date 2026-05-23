"""Tests for ControlNet parameter validation."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))


class ControlNetParameterValidationUnitTest(unittest.TestCase):
    def test_cli_values_override_preset_config_and_defaults_with_provenance(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"matcher_method": "flann", "num_worker_parallel_cpu": 12},
            config_values={"matcher_method": "bf", "num_worker_parallel_cpu": 4},
            preset_values={"matcher_method": "lightglue"},
        )

        self.assertFalse(result.has_errors, result.error_text())
        self.assertEqual(result.values["matcher_method"], "flann")
        self.assertEqual(result.provenance["matcher_method"], "cli")
        self.assertEqual(result.values["num_worker_parallel_cpu"], 12)
        self.assertEqual(result.provenance["num_worker_parallel_cpu"], "cli")

    def test_deep_matcher_requires_deep_match_config_path(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters("run_pipeline_example", cli_values={"matcher_method": "lightglue"})

        self.assertTrue(result.has_errors)
        self.assertIn("deep matcher", result.error_text())
        self.assertIn("deep_match_config_path", result.error_text())

    def test_cli_match_preset_path_conflicts_with_cli_matcher_method(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"match_preset_path": "preset.json", "matcher_method": "bf"},
        )

        self.assertTrue(result.has_errors)
        self.assertIn("match_preset_path", result.error_text())
        self.assertIn("matcher_method", result.error_text())

    def test_cli_match_preset_path_conflicts_with_cli_deep_match_config_path(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"match_preset_path": "preset.json", "deep_match_config_path": "deep.json"},
        )

        self.assertTrue(result.has_errors)
        self.assertIn("match_preset_path", result.error_text())
        self.assertIn("deep_match_config_path", result.error_text())

    def test_inactive_low_resolution_values_warn_without_strict_validation(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"enable_low_resolution_offset_estimation": False, "low_resolution_level": 4},
        )

        self.assertFalse(result.has_errors, result.error_text())
        self.assertIn("low_resolution_level", result.warning_text())

    def test_strict_parameter_validation_promotes_low_resolution_warning_to_error(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={
                "enable_low_resolution_offset_estimation": False,
                "low_resolution_level": 4,
                "strict_parameter_validation": True,
            },
        )

        self.assertTrue(result.has_errors)
        self.assertIn("strict parameter validation", result.error_text())
        self.assertIn("low_resolution_level", result.error_text())

    def test_gpu_min_batch_size_must_not_exceed_gpu_max_batch_size(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters("image_match", cli_values={"gpu_min_batch_size": 8, "gpu_max_batch_size": 4})

        self.assertTrue(result.has_errors)
        self.assertIn("gpu_min_batch_size", result.error_text())
        self.assertIn("gpu_max_batch_size", result.error_text())

    def test_shell_assignments_quote_values(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"matcher_method": "bf", "work_dir": "work with space"},
        )

        self.assertFalse(result.has_errors, result.error_text())
        assignments = result.to_shell_assignments(["matcher_method", "work_dir"])
        self.assertIn("MATCHER_METHOD=bf", assignments)
        self.assertIn("WORK_DIR='work with space'", assignments)


if __name__ == "__main__":
    unittest.main()
