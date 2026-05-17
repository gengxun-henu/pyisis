"""Unit tests for deep_match_config module."""

import json
import tempfile
from pathlib import Path
import pytest

DEEP_MATCH_CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples" / "controlnet_construct" / "deep_match_config.py"


class TestDeepMatchConfigLoad:
    """Tests for load_deep_match_config()."""

    def test_load_valid_config(self, tmp_path):
        """Should load a valid preset JSON and return a dict."""
        config = {
            "feature_extractor": {"method": "superpoint", "max_keypoints": 4096},
            "matcher": {"method": "lightglue"},
            "device": {"prefer_gpu": True, "dtype": "float32"},
            "fallback": {"on_error": "sift_flann"},
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


class TestPresetFiles:
    """Verify all preset files are valid JSON and pass validation."""

    def _get_preset_files(self):
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"
        return sorted(presets_dir.glob("*.json"))

    def test_all_presets_load_successfully(self):
        """All preset files should load without errors."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        for preset_path in self._get_preset_files():
            config = load_deep_match_config(str(preset_path))
            assert "feature_extractor" in config
            assert "matcher" in config
            assert config["matcher"]["method"] in ("superglue", "lightglue", "loftr")

    def test_all_presets_have_fallback(self):
        """All preset files should have a fallback configured."""
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        for preset_path in self._get_preset_files():
            config = load_deep_match_config(str(preset_path))
            fallback = config.get("fallback")
            assert fallback is not None, f"{preset_path.name} missing fallback config"
            assert fallback.get("on_error") in ("sift_bf", "sift_flann"), \
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
