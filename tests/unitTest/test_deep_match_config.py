"""Unit tests for deep_match_config module."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pytest

DEEP_MATCH_CONFIG_PATH = Path(__file__).resolve().parents[2] / "examples" / "controlnet_construct" / "deep_match_config.py"


class TestDeepMatchConfigLoad:
    """Tests for load_deep_match_config()."""

    def test_load_valid_config(self, tmp_path):
        """Should load a valid preset JSON and return a dict."""
        config = {
            "feature_extractor": {"method": "superpoint", "max_keypoints": 4096},
            "matcher": {"method": "lightglue"},
            "device": {"prefer_gpu": True, "dtype": "float32"},
            "fallback": {"on_error": "sift_bf"},
        }
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        result = load_deep_match_config(str(cfg_path))
        assert result["feature_extractor"]["method"] == "superpoint"
        assert result["matcher"]["method"] == "lightglue"

    def test_load_missing_file_raises(self, tmp_path):
        """Should raise ValueError for missing config file."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="未找到"):
            load_deep_match_config(str(tmp_path / "nonexistent.json"))

    def test_load_invalid_json_raises(self, tmp_path):
        """Should raise ValueError for malformed JSON."""
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{ invalid json }", encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="解析失败"):
            load_deep_match_config(str(bad_path))

    def test_missing_feature_extractor_raises(self, tmp_path):
        """Should raise ValueError when feature_extractor.method is missing."""
        config = {"matcher": {"method": "lightglue"}}
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="feature_extractor"):
            load_deep_match_config(str(cfg_path))

    def test_missing_matcher_raises(self, tmp_path):
        """Should raise ValueError when matcher.method is missing."""
        config = {"feature_extractor": {"method": "superpoint"}}
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="matcher"):
            load_deep_match_config(str(cfg_path))

    def test_invalid_extractor_method_raises(self, tmp_path):
        """Should raise ValueError for unsupported extractor method."""
        config = {
            "feature_extractor": {"method": "invalid_extractor"},
            "matcher": {"method": "lightglue"},
        }
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="extractor"):
            load_deep_match_config(str(cfg_path))

    def test_invalid_matcher_method_raises(self, tmp_path):
        """Should raise ValueError for unsupported matcher method."""
        config = {
            "feature_extractor": {"method": "superpoint"},
            "matcher": {"method": "invalid_matcher"},
        }
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="matcher"):
            load_deep_match_config(str(cfg_path))

    def test_loftr_does_not_require_extractor(self, tmp_path):
        """LoFTR preset should not require feature_extractor.method."""
        config = {
            "feature_extractor": {"method": "loftr"},
            "matcher": {"method": "loftr"},
            "device": {"prefer_gpu": True},
        }
        cfg_path = tmp_path / "test_config.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        result = load_deep_match_config(str(cfg_path))
        assert result["matcher"]["method"] == "loftr"


class TestDeepMatchConfigValidation:
    """Tests for validate_deep_match_config()."""

    def _make_minimal_config(self, extractor="superpoint", matcher="lightglue"):
        return {
            "feature_extractor": {"method": extractor},
            "matcher": {"method": matcher},
        }

    def test_valid_config_no_exception(self, tmp_path):
        """Valid config should not raise."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config
        config = self._make_minimal_config()
        validate_deep_match_config(config)

    def test_official_lightglue_accepts_supported_frontends(self):
        """Official LightGlue backend should accept all supported official frontends."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config
        for extractor in ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift"):
            config = {
                "feature_extractor": {"method": extractor},
                "matcher": {"method": "lightglue", "backend": "official"},
            }
            validate_deep_match_config(config)

    def test_non_official_lightglue_still_rejects_non_superpoint_frontends(self):
        """Legacy LightGlue validation should still only accept SuperPoint."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config
        for extractor in ("disk", "aliked", "doghardnet", "lightglue_sift"):
            config = self._make_minimal_config(extractor=extractor, matcher="lightglue")
            with pytest.raises(ValueError, match="superpoint"):
                validate_deep_match_config(config)

    def test_lightglue_rejects_unknown_backend(self):
        """LightGlue backend values should be restricted to supported backends."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config
        config = {
            "feature_extractor": {"method": "superpoint"},
            "matcher": {"method": "lightglue", "backend": "experimental"},
        }
        with pytest.raises(ValueError, match="backend"):
            validate_deep_match_config(config)

    def test_official_lightglue_rejects_unknown_options_and_feature_alias_conflict(self):
        """Official LightGlue backend should reject unsupported options and aliases used together."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        config = {
            "feature_extractor": {"method": "superpoint", "remove_borders": 4},
            "matcher": {"method": "lightglue", "backend": "official"},
        }
        with pytest.raises(ValueError, match="unknown feature_extractor option"):
            validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "superpoint", "max_features": 4096, "max_keypoints": 4096},
            "matcher": {"method": "lightglue", "backend": "official"},
        }
        with pytest.raises(ValueError, match="max_features.*max_keypoints"):
            validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "superpoint"},
            "matcher": {"method": "lightglue", "backend": "official", "prune_threshold": 0.1},
        }
        with pytest.raises(ValueError, match="unknown matcher option"):
            validate_deep_match_config(config)

    def test_loftr_accepts_default_kornia_and_external_backends(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        for matcher in (
            {"method": "loftr"},
            {"method": "loftr", "backend": "kornia"},
            {"method": "loftr", "backend": "external", "model_type": "outdoor", "temp_bug_fix": "auto"},
        ):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr", "preprocess_mode": "pad"},
                    "matcher": matcher,
                }
            )

    def test_loftr_rejects_unknown_backend_and_non_loftr_extractor(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="LoFTR.*backend"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr"},
                    "matcher": {"method": "loftr", "backend": "experimental"},
                }
            )

        with pytest.raises(ValueError, match="feature_extractor.method.*loftr"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint"},
                    "matcher": {"method": "loftr", "backend": "external"},
                }
            )

    def test_external_loftr_rejects_unknown_options_and_invalid_enums(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        base = {
            "feature_extractor": {"method": "loftr", "preprocess_mode": "pad"},
            "matcher": {"method": "loftr", "backend": "external"},
        }

        config = {
            "feature_extractor": {"method": "loftr", "remove_borders": 4},
            "matcher": {"method": "loftr", "backend": "external"},
        }
        with pytest.raises(ValueError, match="unknown feature_extractor option"):
            validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "loftr"},
            "matcher": {"method": "loftr", "backend": "external", "weights_path": "ignored.ckpt"},
        }
        with pytest.raises(ValueError, match="unknown matcher option"):
            validate_deep_match_config(config)

        for field_name, bad_value, pattern in (
            ("model_type", "space", "model_type"),
            ("temp_bug_fix", "maybe", "temp_bug_fix"),
            ("geometric_filter", "essential", "geometric_filter"),
        ):
            config = {
                "feature_extractor": dict(base["feature_extractor"]),
                "matcher": dict(base["matcher"], **{field_name: bad_value}),
            }
            with pytest.raises(ValueError, match=pattern):
                validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "loftr", "preprocess_mode": "crop"},
            "matcher": dict(base["matcher"]),
        }
        with pytest.raises(ValueError, match="preprocess_mode"):
            validate_deep_match_config(config)

    def test_external_loftr_rejects_checkpoint_alias_conflict_and_partial_resize(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="checkpoint.*checkpoint_path"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr"},
                    "matcher": {
                        "method": "loftr",
                        "backend": "external",
                        "checkpoint": "/tmp/a.ckpt",
                        "checkpoint_path": "/tmp/b.ckpt",
                    },
                }
            )

        with pytest.raises(ValueError, match="resize_width.*resize_height"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr", "resize_width": 640},
                    "matcher": {"method": "loftr", "backend": "external"},
                }
            )

    def test_external_loftr_rejects_invalid_numeric_ranges(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        base = {
            "feature_extractor": {"method": "loftr"},
            "matcher": {"method": "loftr", "backend": "external"},
        }

        for bad_value in (1.1, float("inf"), float("nan")):
            config = {
                "feature_extractor": dict(base["feature_extractor"]),
                "matcher": dict(base["matcher"], ransac_confidence=bad_value),
            }
            with pytest.raises(ValueError, match="ransac_confidence"):
                validate_deep_match_config(config)

        for field_name, bad_value in (
            ("coarse_threshold", float("inf")),
            ("min_confidence", float("nan")),
            ("ransac_reproj_threshold", float("inf")),
        ):
            config = {
                "feature_extractor": dict(base["feature_extractor"]),
                "matcher": dict(base["matcher"], **{field_name: bad_value}),
            }
            with pytest.raises(ValueError, match=field_name):
                validate_deep_match_config(config)


class TestDeepMatchConfigHelpers:
    """Tests for helper functions."""

    def test_is_deep_matcher_true_for_deep_methods(self):
        """Should return True for superglue, lightglue, loftr."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import is_deep_matcher
        assert is_deep_matcher("superglue") is True
        assert is_deep_matcher("lightglue") is True
        assert is_deep_matcher("loftr") is True

    def test_is_deep_matcher_false_for_traditional(self):
        """Should return False for bf, flann, superpoint."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import is_deep_matcher
        assert is_deep_matcher("bf") is False
        assert is_deep_matcher("flann") is False
        assert is_deep_matcher("superpoint") is False

    def test_require_deep_config_raises_when_null(self):
        """Should raise when matcher is deep but config path is None."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import require_deep_config
        with pytest.raises(ValueError, match="必须指定"):
            require_deep_config("lightglue", None)

    def test_require_deep_config_ok_when_traditional(self):
        """Should not raise when matcher is traditional even with None config."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import require_deep_config
        require_deep_config("flann", None)

    def test_external_loftr_dependency_check_skips_kornia_loftr(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        import deep_match_config
        from deep_match_config import DeepMatchRuntimeConfig, check_deep_match_dependencies

        runtime_config = DeepMatchRuntimeConfig(
            matcher_method="loftr",
            feature_extractor_method="loftr",
            prefer_gpu=False,
            device_dtype="float32",
            fallback_on_error=None,
            raw_config={"matcher": {"method": "loftr", "backend": "external"}},
            matcher_options={"backend": "external"},
        )

        def _fake_import(name, package=None):
            if name in {"torch", "kornia.feature"}:
                raise ModuleNotFoundError(name=name)
            return object()

        with patch.object(deep_match_config.importlib, "import_module", side_effect=_fake_import):
            assert check_deep_match_dependencies(runtime_config) == ["missing torch"]


class TestPresetFiles(unittest.TestCase):
    """Verify all preset files are valid JSON and pass validation."""

    def _get_preset_files(self):
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"
        return sorted(presets_dir.glob("*.json"))

    def _read_preset_config(self, preset_path):
        return json.loads(preset_path.read_text(encoding="utf-8"))

    def _is_legacy_unsupported_preset(self, preset_path):
        config = self._read_preset_config(preset_path)
        extractor_method = config["feature_extractor"]["method"]
        matcher = config["matcher"]
        matcher_method = matcher["method"]
        matcher_backend = matcher.get("backend")
        if matcher_method == "lightglue" and not matcher_backend:
            return extractor_method != "superpoint"
        if matcher_method == "superglue":
            return extractor_method != "superpoint"
        return False

    def test_supported_presets_load_successfully(self):
        """Supported preset files should load without errors."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        for preset_path in self._get_preset_files():
            if self._is_legacy_unsupported_preset(preset_path):
                continue
            config = load_deep_match_config(str(preset_path))
            assert "feature_extractor" in config
            assert "matcher" in config
            assert config["matcher"]["method"] in ("superglue", "lightglue", "loftr")

    def test_external_loftr_presets_exist_and_load(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config

        expected = {
            "loftr_external_outdoor.json": "outdoor",
            "loftr_external_indoor.json": "indoor",
        }
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"
        for preset_name, model_type in expected.items():
            with self.subTest(preset=preset_name):
                config = load_deep_match_config(str(presets_dir / preset_name))
                assert config["feature_extractor"]["method"] == "loftr"
                assert config["feature_extractor"]["preprocess_mode"] == "pad"
                assert config["matcher"]["method"] == "loftr"
                assert config["matcher"]["backend"] == "external"
                assert config["matcher"]["model_type"] == model_type

    def test_legacy_unsupported_presets_fail_validation(self):
        """Legacy non-SuperPoint matcher presets should fail until they declare a supported backend."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        unsupported_presets = [p for p in self._get_preset_files() if self._is_legacy_unsupported_preset(p)]
        assert unsupported_presets
        for preset_path in unsupported_presets:
            with pytest.raises(ValueError, match="superpoint"):
                load_deep_match_config(str(preset_path))

    def test_official_lightglue_presets_exist_and_load(self):
        """Official LightGlue presets should exist and load with the expected frontend."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config

        expected_presets = {
            "lightglue_official_superpoint.json": "superpoint",
            "lightglue_official_disk.json": "disk",
            "lightglue_official_aliked.json": "aliked",
            "lightglue_official_doghardnet.json": "doghardnet",
            "lightglue_official_sift.json": "lightglue_sift",
        }
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"

        for preset_name, expected_method in expected_presets.items():
            config = load_deep_match_config(str(presets_dir / preset_name))
            assert config["feature_extractor"]["method"] == expected_method
            assert config["matcher"]["method"] == "lightglue"
            assert config["matcher"]["backend"] == "official"

    def test_all_presets_have_fallback(self):
        """All preset files should have a fallback configured."""
        for preset_path in self._get_preset_files():
            config = self._read_preset_config(preset_path)
            fallback = config.get("fallback")
            assert fallback is not None, f"{preset_path.name} missing fallback config"
            assert fallback.get("on_error") in ("sift_bf", None), \
                f"{preset_path.name} has invalid fallback: {fallback.get('on_error')}"

    def test_loftr_presets_use_loftr_extractor(self):
        """LoFTR presets should have method=loftr for feature_extractor."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        loftr_presets = [p for p in self._get_preset_files() if "loftr" in p.name]
        for preset_path in loftr_presets:
            config = load_deep_match_config(str(preset_path))
            assert config["feature_extractor"]["method"] == "loftr"
            assert config["matcher"]["method"] == "loftr"
