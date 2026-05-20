"""Focused regression tests for deep-match runtime config rehydration."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.deep_match_config import deep_match_runtime_config_from_payload


class DeepMatchConfigRehydrationUnitTest(unittest.TestCase):
    def test_payload_rehydration_preserves_serialized_option_dictionaries(self):
        payload = {
            "matcher_method": "lightglue",
            "feature_extractor_method": "superpoint",
            "prefer_gpu": False,
            "device_dtype": "float32",
            "fallback_on_error": "sift_flann",
            "matcher_options": {"weights": "superpoint_lightglue", "flash": False},
            "feature_options": {"max_keypoints": 4096, "keypoint_threshold": 0.0005},
            "device_options": {"prefer_gpu": False, "dtype": "float32", "batch_inference": True},
            "raw_config": {"matcher": {"method": "lightglue"}},
        }

        runtime_config = deep_match_runtime_config_from_payload(payload)

        self.assertIsNotNone(runtime_config)
        self.assertEqual(runtime_config.matcher_options, payload["matcher_options"])
        self.assertEqual(runtime_config.feature_options, payload["feature_options"])
        self.assertEqual(runtime_config.device_options, payload["device_options"])


if __name__ == "__main__":
    unittest.main()
