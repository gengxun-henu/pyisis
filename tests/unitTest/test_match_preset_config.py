"""Tests for neutral ControlNet match preset resolution.

Author: Geng Xun
Created: 2026-05-23
Last Modified: 2026-06-10
Updated: 2026-06-10  Geng Xun added GPU SIFT preset parameter consistency coverage.
Updated: 2026-06-10  Geng Xun aligned active ControlNet SIFT defaults on the BF route.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
CONTROLNET_EXAMPLES = PROJECT_ROOT / "examples" / "controlnet_construct"
if str(CONTROLNET_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(CONTROLNET_EXAMPLES))


class MatchPresetConfigUnitTest(unittest.TestCase):
    def setUp(self):
        self._temp_dirs: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self):
        for temp_dir in self._temp_dirs:
            temp_dir.cleanup()

    def _make_temp_dir(self, prefix: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory(prefix=prefix)
        self._temp_dirs.append(temp_dir)
        return Path(temp_dir.name)

    def _write_preset(self, payload: dict[str, object]) -> Path:
        temp_dir = self._make_temp_dir("match_preset_test_")
        preset_path = temp_dir / "preset.json"
        preset_path.write_text(json.dumps(payload), encoding="utf-8")
        return preset_path

    def test_package_import_works_with_examples_on_sys_path(self):
        original_sys_path = list(sys.path)
        removed_module = sys.modules.pop("controlnet_construct.match_preset_config", None)
        removed_deep_module = sys.modules.pop("deep_match_config", None)
        try:
            sys.path[:] = [path for path in sys.path if path != str(CONTROLNET_EXAMPLES)]
            if str(EXAMPLES_ROOT) not in sys.path:
                sys.path.insert(0, str(EXAMPLES_ROOT))

            import controlnet_construct.match_preset_config as match_preset_config

            self.assertEqual(match_preset_config.CLASSIC_SIFT_FEATURE_METHOD, "classic_sift")
        finally:
            if removed_module is not None:
                sys.modules["controlnet_construct.match_preset_config"] = removed_module
            if removed_deep_module is not None:
                sys.modules["deep_match_config"] = removed_deep_module
            sys.path[:] = original_sys_path

    def test_classic_sift_flann_preset_maps_to_image_match_defaults(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 0.75},
            }
        )

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "flann")
        self.assertIsNone(runtime.deep_match_config_path)
        self.assertEqual(
            runtime.image_match_defaults,
            {
                "match_preset_path": str(preset_path),
                "matcher_method": "flann",
                "deep_match_config_path": None,
                "max_features": 1000,
                "sift_octave_layers": 3,
                "sift_contrast_threshold": 0.04,
                "sift_edge_threshold": 10.0,
                "sift_sigma": 1.6,
                "ratio_test": 0.75,
            },
        )

    def test_classic_sift_bf_preset_maps_to_bf_matcher(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 2048,
                    "octave_layers": 4,
                    "contrast_threshold": 0.03,
                    "edge_threshold": 12.0,
                    "sigma": 1.4,
                },
                "matcher": {"method": "bf", "ratio_test": 0.8},
            }
        )

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "bf")
        self.assertEqual(runtime.image_match_defaults["matcher_method"], "bf")
        self.assertEqual(runtime.image_match_defaults["ratio_test"], 0.8)

    def test_shared_classic_sift_flann_preset_loads(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertEqual(runtime.matcher_method, "flann")
        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.image_match_defaults["max_features"], 1000)

    def test_shared_classic_sift_bf_preset_loads(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertEqual(runtime.matcher_method, "bf")
        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.image_match_defaults["ratio_test"], 0.75)

    def test_shared_classic_sift_presets_match_controlnet_example_sift_defaults(self):
        from match_preset_config import resolve_match_preset_runtime_config

        config_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "controlnet_config.example.json"
        image_match_config = json.loads(config_path.read_text(encoding="utf-8"))["ImageMatch"]
        expected = {
            "max_features": image_match_config["max_features"],
            "sift_octave_layers": image_match_config["sift_octave_layers"],
            "sift_contrast_threshold": image_match_config["sift_contrast_threshold"],
            "sift_edge_threshold": image_match_config["sift_edge_threshold"],
            "sift_sigma": image_match_config["sift_sigma"],
            "ratio_test": image_match_config["ratio_test"],
        }

        for preset_name in ("classic_sift_bf.json", "classic_sift_flann.json"):
            with self.subTest(preset_name=preset_name):
                preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / preset_name
                runtime = resolve_match_preset_runtime_config(preset_path)

                for key, value in expected.items():
                    self.assertEqual(runtime.image_match_defaults[key], value)

    def test_controlnet_example_config_declares_match_preset_path(self):
        config_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "controlnet_config.example.json"
        payload = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertIn("match_preset_path", payload["ImageMatch"])
        self.assertIsNone(payload["ImageMatch"]["match_preset_path"])
        self.assertIn("deep_matcher_config_path", payload["ImageMatch"])
        self.assertIsNone(payload["ImageMatch"]["deep_matcher_config_path"])
        self.assertEqual(payload["ImageMatch"]["matcher_method"], "bf")

    def test_active_controlnet_configs_default_to_classic_sift_bf(self):
        for config_name in ("controlnet_config.example.json", "controlnet_config.low_memory_lro.json"):
            with self.subTest(config_name=config_name):
                config_path = PROJECT_ROOT / "examples" / "controlnet_construct" / config_name
                payload = json.loads(config_path.read_text(encoding="utf-8"))

                self.assertEqual(payload["ImageMatch"]["matcher_method"], "bf")

    def test_active_parameter_profiles_default_to_classic_sift_bf(self):
        from parameter_profiles import PARAMETER_PROFILES

        for profile_name, values in PARAMETER_PROFILES.items():
            with self.subTest(profile_name=profile_name):
                self.assertEqual(values["matcher_method"], "bf")

    def test_deep_preset_maps_to_existing_deep_config_path(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_official_superpoint.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertTrue(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "lightglue")
        self.assertEqual(runtime.deep_match_config_path, str(preset_path))
        self.assertEqual(runtime.image_match_defaults["matcher_method"], "lightglue")
        self.assertEqual(runtime.image_match_defaults["deep_match_config_path"], str(preset_path))

    def test_classic_sift_rejects_lightglue_sift_name(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {"method": "lightglue_sift", "max_features": 1000},
                "matcher": {"method": "flann", "ratio_test": 0.75},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "classic_sift"):
            resolve_match_preset_runtime_config(preset_path)

    def test_classic_sift_rejects_invalid_ratio_test(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 1.5},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "ratio_test"):
            resolve_match_preset_runtime_config(preset_path)

    def test_classic_sift_rejects_non_integer_positive_int_options(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        for field_name, value in (("max_features", 3.0), ("octave_layers", True)):
            with self.subTest(field_name=field_name, value=value):
                feature_extractor = {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                }
                feature_extractor[field_name] = value
                preset_path = self._write_preset(
                    {
                        "feature_extractor": feature_extractor,
                        "matcher": {"method": "flann", "ratio_test": 0.75},
                    }
                )

                with self.assertRaisesRegex(MatchPresetConfigError, field_name):
                    resolve_match_preset_runtime_config(preset_path)

    def test_classic_sift_rejects_deep_only_sections(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 0.75},
                "device": {"prefer_gpu": True},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "deep-only"):
            resolve_match_preset_runtime_config(preset_path)

    def test_resolve_match_preset_path_prefers_config_relative_path(self):
        from match_preset_config import resolve_match_preset_path

        temp_dir = self._make_temp_dir("match_preset_path_test_")
        config_dir = temp_dir / "configs"
        preset_dir = config_dir / "presets"
        preset_dir.mkdir(parents=True)
        config_path = config_dir / "controlnet_config.json"
        preset_path = preset_dir / "classic_sift_flann.json"
        config_path.write_text("{}", encoding="utf-8")
        preset_path.write_text("{}", encoding="utf-8")

        resolved = resolve_match_preset_path(
            "presets/classic_sift_flann.json",
            config_path=config_path,
            repo_root=PROJECT_ROOT,
        )

        self.assertEqual(resolved, preset_path.resolve())


if __name__ == "__main__":
    unittest.main()
