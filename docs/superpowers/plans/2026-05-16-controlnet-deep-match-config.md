# ControlNet 深度学习匹配配置实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ControlNet 流水线中为深度学习匹配（SuperGlue/LightGlue/LoFTR）增加独立 JSON 配置文件支持，将特征提取器与匹配器解耦，并提供 8 套预设配置。

**Architecture:** 新增 `deep_match_config.py` 加载预设 JSON，`run_pipeline_example.sh` 校验深度学习配置必填，`controlnet_config.example.json` 增加 `deep_matcher_config_path` 字段。传统 SIFT 路由保持不变。

**Tech Stack:** Python (json, pathlib, argparse), Bash, OpenCV, PyTorch/Kornia（深度学习匹配依赖）

---

## 文件清单

### 新增文件
| 文件 | 职责 |
|------|------|
| `examples/controlnet_construct/presets/superglue_default.json` | SuperPoint + SuperGlue 预设 |
| `examples/controlnet_construct/presets/lightglue_default.json` | SuperPoint + LightGlue 预设（推荐默认） |
| `examples/controlnet_construct/presets/loftr_default.json` | LoFTR 端到端预设 |
| `examples/controlnet_construct/presets/lightglue_high_recall.json` | SuperPoint + LightGlue 高召回 |
| `examples/controlnet_construct/presets/lightglue_disk.json` | DISK + LightGlue 预设 |
| `examples/controlnet_construct/presets/lightglue_aliked.json` | ALIKED + LightGlue 预设 |
| `examples/controlnet_construct/presets/lightglue_doghardnet.json` | DoGHardNet + LightGlue 预设 |
| `examples/controlnet_construct/presets/superglue_aliked.json` | ALIKED + SuperGlue 预设 |
| `examples/controlnet_construct/deep_match_config.py` | 深度学习配置加载与校验模块 |
| `examples/controlnet_construct/PRESETS_README.md` | 特征提取器和匹配器适用场景文档 |
| `tests/unitTest/test_deep_match_config.py` | 配置加载与校验单元测试 |

### 修改文件
| 文件 | 改动范围 |
|------|----------|
| `examples/controlnet_construct/controlnet_config.example.json` | 新增 `deep_matcher_config_path` 字段 |
| `examples/controlnet_construct/run_pipeline_example.sh` | 新增深度学习配置校验逻辑和参数传递 |
| `examples/controlnet_construct/image_match.py` | 修改为包装模式，增加深度学习配置校验入口 |

---

### Task 1: 新增 `controlnet_config.example.json` 字段

**Files:**
- Modify: `examples/controlnet_construct/controlnet_config.example.json`

- [ ] **Step 1: 在 `ImageMatch` 对象中新增 `deep_matcher_config_path` 字段**

在现有 `"matcher_method": "flann",` 之后（约第 27 行），添加：

```json
    "deep_matcher_config_path": null,
```

完整上下文（在 `"matcher_method": "flann",` 之后）：

```json
    "matcher_method": "flann",
    "deep_matcher_config_path": null,
    "ratio_test": 0.75,
```

- [ ] **Step 2: 提交**

```bash
git add examples/controlnet_construct/controlnet_config.example.json
git commit -m "feat: add deep_matcher_config_path field to controlnet config"
```

---

### Task 2: 创建 `deep_match_config.py` 配置加载模块

**Files:**
- Create: `examples/controlnet_construct/deep_match_config.py`
- Test: `tests/unitTest/test_deep_match_config.py`

- [ ] **Step 1: 编写单元测试（TDD）**

在 `tests/unitTest/test_deep_match_config.py` 中创建测试：

```python
"""Unit tests for deep_match_config module."""

import json
import tempfile
from pathlib import Path
import pytest

# We'll test via import after the module exists
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
        # Import dynamically since module path depends on repo setup
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
        with pytest.raises(ValueError, match="not found"):
            load_deep_match_config(str(tmp_path / "nonexistent.json"))

    def test_load_invalid_json_raises(self, tmp_path):
        """Should raise ValueError for malformed JSON."""
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{ invalid json }", encoding="utf-8")
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config
        with pytest.raises(ValueError, match="parse"):
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
        validate_deep_match_config(config)  # should not raise


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
        require_deep_config("flann", None)  # should not raise
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=examples/controlnet_construct python -m pytest tests/unitTest/test_deep_match_config.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'deep_match_config'"

- [ ] **Step 3: 实现 `deep_match_config.py`**

```python
"""深度学习匹配配置加载与校验模块。

加载预设 JSON 配置文件，验证必填字段，提供工具函数。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 支持的深度学习匹配器
DEEP_MATCHER_METHODS = ("superglue", "lightglue", "loftr")

# 支持的特征提取器（loftr 使用内置特征提取，不需要独立提取器）
SUPPORTED_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "loftr")


def load_deep_match_config(config_path: str | Path) -> dict[str, Any]:
    """加载并校验深度学习匹配预设 JSON 文件。

    Args:
        config_path: 预设 JSON 文件路径。

    Returns:
        解析后的配置字典（已通过必填字段校验）。

    Raises:
        ValueError: 文件不存在、JSON 解析失败或必填字段缺失。
    """
    resolved = Path(config_path)
    if not resolved.exists():
        raise ValueError(f"深度学习配置文件未找到: {resolved}")

    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"深度学习配置文件 JSON 解析失败: {resolved}: {exc}") from exc

    validate_deep_match_config(config)
    return config


def validate_deep_match_config(config: dict[str, Any]) -> None:
    """校验深度学习匹配配置字典的必填字段。

    Args:
        config: 解析后的 JSON 配置字典。

    Raises:
        ValueError: 必填字段缺失或值不合法。
    """
    # 校验 feature_extractor
    extractor = config.get("feature_extractor")
    if extractor is None:
        raise ValueError("配置缺少 'feature_extractor' 字段")
    extractor_method = str(extractor.get("method", "")).strip().lower()
    if not extractor_method:
        raise ValueError("feature_extractor 缺少必填字段 'method'")
    if extractor_method not in SUPPORTED_EXTRACTOR_METHODS:
        raise ValueError(
            f"不支持的特征提取器方法 '{extractor_method}'。"
            f"支持的提取器: {', '.join(SUPPORTED_EXTRACTOR_METHODS)}"
        )

    # 校验 matcher
    matcher = config.get("matcher")
    if matcher is None:
        raise ValueError("配置缺少 'matcher' 字段")
    matcher_method = str(matcher.get("method", "")).strip().lower()
    if not matcher_method:
        raise ValueError("matcher 缺少必填字段 'method'")
    if matcher_method not in DEEP_MATCHER_METHODS:
        raise ValueError(
            f"不支持的匹配器方法 '{matcher_method}'。"
            f"支持的匹配器: {', '.join(DEEP_MATCHER_METHODS)}"
        )

    # 可选校验 device 和 fallback（如果提供了但值不合法）
    device = config.get("device")
    if device is not None:
        dtype = device.get("dtype", "float32")
        if dtype not in ("float32", "float16", "bfloat16"):
            raise ValueError(
                f"不支持的 dtype '{dtype}'。支持的 dtype: float32, float16, bfloat16"
            )

    fallback = config.get("fallback")
    if fallback is not None:
        on_error = fallback.get("on_error")
        if on_error is not None and on_error not in ("sift_bf", "sift_flann", None):
            raise ValueError(
                f"不支持的 fallback 方法 '{on_error}'。"
                f"支持的 fallback: sift_bf, sift_flann, null"
            )


def is_deep_matcher(matcher_method: str) -> bool:
    """判断指定的匹配方法是否为深度学习匹配器。

    Args:
        matcher_method: 匹配方法名（如 "lightglue", "flann"）。

    Returns:
        True 如果是深度学习匹配器，否则 False。
    """
    return str(matcher_method).strip().lower() in DEEP_MATCHER_METHODS


def require_deep_config(matcher_method: str, config_path: str | None) -> None:
    """如果匹配器是深度学习匹配器，则要求配置文件路径不为空。

    Args:
        matcher_method: 匹配方法名。
        config_path: 深度学习配置文件路径，可为 None 或空字符串。

    Raises:
        ValueError: 深度学习匹配器但未指定配置文件。
    """
    if is_deep_matcher(matcher_method):
        if not config_path or not config_path.strip():
            raise ValueError(
                f"匹配方法 '{matcher_method}' 是深度学习匹配器，必须指定 "
                f"deep_matcher_config_path 配置文件。"
            )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
PYTHONPATH=examples/controlnet_construct python -m pytest tests/unitTest/test_deep_match_config.py -v
```
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add examples/controlnet_construct/deep_match_config.py tests/unitTest/test_deep_match_config.py
git commit -m "feat: add deep_match_config module with validation and helpers"
```

---

### Task 3: 创建 8 套预设 JSON 文件

**Files:**
- Create: `examples/controlnet_construct/presets/superglue_default.json`
- Create: `examples/controlnet_construct/presets/lightglue_default.json`
- Create: `examples/controlnet_construct/presets/loftr_default.json`
- Create: `examples/controlnet_construct/presets/lightglue_high_recall.json`
- Create: `examples/controlnet_construct/presets/lightglue_disk.json`
- Create: `examples/controlnet_construct/presets/lightglue_aliked.json`
- Create: `examples/controlnet_construct/presets/lightglue_doghardnet.json`
- Create: `examples/controlnet_construct/presets/superglue_aliked.json`

- [ ] **Step 1: 创建 presets 目录和所有预设文件**

```bash
mkdir -p examples/controlnet_construct/presets
```

**`presets/superglue_default.json`** — SuperPoint + SuperGlue，高精度标准场景：

```json
{
  "feature_extractor": {
    "method": "superpoint",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.0005,
    "remove_borders": 4,
    "detect_keypoints": true
  },
  "matcher": {
    "method": "superglue",
    "weights_path": null,
    "sinkhorn_iterations": 20
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": false
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/lightglue_default.json`** — SuperPoint + LightGlue，速度与精度平衡（推荐默认）：

```json
{
  "feature_extractor": {
    "method": "superpoint",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.0005,
    "remove_borders": 4,
    "detect_keypoints": true
  },
  "matcher": {
    "method": "lightglue",
    "weights_path": null,
    "flash": true,
    "prune_threshold": 4
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": true
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/loftr_default.json`** — LoFTR 端到端，弱纹理/大视角变化：

```json
{
  "feature_extractor": {
    "method": "loftr"
  },
  "matcher": {
    "method": "loftr",
    "weights_path": null
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": false
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/lightglue_high_recall.json`** — SuperPoint + LightGlue，高召回（更多特征点）：

```json
{
  "feature_extractor": {
    "method": "superpoint",
    "max_keypoints": 8192,
    "keypoint_threshold": 0.0001,
    "remove_borders": 2,
    "detect_keypoints": true
  },
  "matcher": {
    "method": "lightglue",
    "weights_path": null,
    "flash": true,
    "prune_threshold": 2
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": true
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/lightglue_disk.json`** — DISK + LightGlue，快速推理/低纹理结构明显：

```json
{
  "feature_extractor": {
    "method": "disk",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.001,
    "remove_borders": 4
  },
  "matcher": {
    "method": "lightglue",
    "weights_path": null,
    "flash": true,
    "prune_threshold": 4
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": true
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/lightglue_aliked.json`** — ALIKED + LightGlue，高分辨率遥感影像：

```json
{
  "feature_extractor": {
    "method": "aliked",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.0005,
    "remove_borders": 4
  },
  "matcher": {
    "method": "lightglue",
    "weights_path": null,
    "flash": true,
    "prune_threshold": 4
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": true
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/lightglue_doghardnet.json`** — DoGHardNet + LightGlue，抗光照变化：

```json
{
  "feature_extractor": {
    "method": "doghardnet",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.001,
    "remove_borders": 4
  },
  "matcher": {
    "method": "lightglue",
    "weights_path": null,
    "flash": true,
    "prune_threshold": 4
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": true
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

**`presets/superglue_aliked.json`** — ALIKED + SuperGlue，高精度高分辨率：

```json
{
  "feature_extractor": {
    "method": "aliked",
    "max_keypoints": 4096,
    "keypoint_threshold": 0.0005,
    "remove_borders": 4
  },
  "matcher": {
    "method": "superglue",
    "weights_path": null,
    "sinkhorn_iterations": 20
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": false
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

- [ ] **Step 2: 验证所有预设 JSON 格式合法**

```bash
for f in examples/controlnet_construct/presets/*.json; do python -c "import json; json.load(open('$f'))" && echo "OK: $f" || echo "FAIL: $f"; done
```
Expected: All 8 files show "OK"

- [ ] **Step 3: 提交**

```bash
git add examples/controlnet_construct/presets/
git commit -m "feat: add 8 deep match preset configs"
```

---

### Task 4: 创建 `PRESETS_README.md` 文档

**Files:**
- Create: `examples/controlnet_construct/PRESETS_README.md`

- [ ] **Step 1: 创建文档**

```markdown
# 深度学习匹配预设

本文档描述 `presets/` 目录下的预设配置文件，以及各特征提取器和匹配器的适用场景。

## 预设清单

| 预设文件 | 特征提取器 | 匹配器 | 适用场景 |
|---------|-----------|--------|---------|
| `superglue_default.json` | SuperPoint | SuperGlue | 高精度标准场景，基准对比。匹配质量最高但速度较慢。 |
| `lightglue_default.json` | SuperPoint | LightGlue | 速度与精度平衡，推荐默认使用。自适应特征裁剪。 |
| `loftr_default.json` | LoFTR(内置) | LoFTR(端到端) | 弱纹理区域、大视角变化场景。无需独立特征点。 |
| `lightglue_high_recall.json` | SuperPoint | LightGlue | 高召回需求，提取 8192 个特征点，降低检测阈值。 |
| `lightglue_disk.json` | DISK | LightGlue | 快速推理、低纹理但有明显结构特征的场景。内存占用低。 |
| `lightglue_aliked.json` | ALIKED | LightGlue | 高分辨率图像、行星/遥感影像优化。轻量高效。 |
| `lightglue_doghardnet.json` | DoGHardNet | LightGlue | 传统 DoG 检测 + HardNet 描述子，抗光照和季节变化强。 |
| `superglue_aliked.json` | ALIKED | SuperGlue | 高精度需求的高分辨率图像匹配。 |

## 特征提取器适用场景

### SuperPoint

- **类型:** 深度学习特征点检测器 + 描述子网络
- **适用场景:** 通用深度学习特征点检测，端点检测质量好。适合大多数行星空旷纹理场景。
- **配合匹配器:** LightGlue, SuperGlue
- **优点:** 检测质量高，端点特征描述准确
- **缺点:** 比传统方法慢，需要 GPU 加速效果最佳

### DISK

- **类型:** 基于 U-Net 的检测描述一体网络
- **适用场景:** 快速推理、低纹理但有明显结构特征的场景。
- **配合匹配器:** LightGlue
- **优点:** 推理速度快，内存占用低于 SuperPoint
- **缺点:** 对极弱纹理场景效果一般

### ALIKED

- **类型:** 轻量高效特征检测器
- **适用场景:** 高分辨率图像、行星/遥感影像优化。内存占用低，适合大型影像处理。
- **配合匹配器:** LightGlue, SuperGlue
- **优点:** 轻量高效，针对高分辨率优化
- **缺点:** 低分辨率图像可能不如 SuperPoint

### DoGHardNet

- **类型:** DoG（Difference of Gaussian）检测器 + HardNet 描述子
- **适用场景:** 传统检测与深度学习描述子混合，抗光照变化和季节性变化能力强。
- **配合匹配器:** LightGlue
- **优点:** 抗光照变化强，不需要训练模型
- **缺点:** 检测质量不如纯深度学习方法

### LoFTR (内置)

- **类型:** 端到端密集匹配网络（无独立特征提取器）
- **适用场景:** 弱纹理区域和大视角变化场景。特征提取在 LoFTR 网络内部完成。
- **配合匹配器:** 自身（端到端）
- **优点:** 无需独立特征点，适合弱纹理
- **缺点:** 速度慢，内存占用大

## 匹配器适用场景

### SuperGlue

- **类型:** 基于图神经网络的高精度匹配器
- **适用场景:** 对精度要求高、时间不敏感的场景。
- **优点:** 匹配质量最高
- **缺点:** 速度较慢，计算量大

### LightGlue

- **类型:** SuperGlue 的轻量加速版本
- **适用场景:** 速度与精度平衡，推荐作为默认深度学习匹配器。
- **优点:** 自适应特征裁剪，速度快
- **缺点:** 极限精度略低于 SuperGlue

### LoFTR (端到端)

- **类型:** Transformer 架构的无特征点密集匹配器
- **适用场景:** 弱纹理和大基线匹配。
- **优点:** 无需特征提取，直接端到端匹配
- **缺点:** 速度慢，需要 GPU

## 使用方法

在 `controlnet_config.json` 中指定预设路径：

```json
{
  "ImageMatch": {
    "matcher_method": "lightglue",
    "deep_matcher_config_path": "presets/lightglue_default.json",
    ...
  }
}
```

## 自定义预设

复制任一预设文件到自定义路径，修改参数后在 `deep_matcher_config_path` 中指定即可。

### 配置字段说明

**feature_extractor:**
- `method`: 特征提取器方法（`superpoint`, `disk`, `aliked`, `doghardnet`, `loftr`）
- `max_keypoints`: 最大特征点数（LoFTR 不需要）
- `keypoint_threshold`: 特征点检测阈值（LoFTR 不需要）
- `remove_borders`: 边界去除像素数（LoFTR 不需要）
- `detect_keypoints`: 是否启用特征点检测模式（仅 SuperPoint）

**matcher:**
- `method`: 匹配器方法（`superglue`, `lightglue`, `loftr`）
- `weights_path`: 模型权重路径，null 使用默认权重
- `flash`: 是否启用 Flash Attention 加速（仅 LightGlue）
- `prune_threshold`: 特征裁剪阈值（仅 LightGlue）
- `sinkhorn_iterations`: Sinkhorn 归一化迭代次数（仅 SuperGlue）

**device:**
- `prefer_gpu`: 是否优先使用 GPU
- `dtype`: 推理精度（`float32`, `float16`, `bfloat16`）
- `batch_inference`: 是否启用批量推理

**fallback:**
- `on_error`: 失败回退方法（`sift_bf`, `sift_flann`, null）
```

- [ ] **Step 2: 提交**

```bash
git add examples/controlnet_construct/PRESETS_README.md
git commit -m "docs: add deep match presets README with usage scenarios"
```

---

### Task 5: 修改 `run_pipeline_example.sh` 添加深度学习配置校验

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`

- [ ] **Step 1: 在 shell 脚本中新增 DEEP_MATCHER_CONFIG_PATH 变量和解析**

在变量声明区域（约第 885 行附近，`DEEP_MATCH_MODE` 声明之后），添加：

```bash
  DEEP_MATCHER_CONFIG_PATH=""
```

在参数解析区域（约第 992 行附近，`--deep-match-mode` 解析之后），添加：

```bash
      --deep-match-config-path)
        DEEP_MATCHER_CONFIG_PATH=$2
        shift 2
        ;;
```

在 USAGE/help 区域（约第 300 行附近），添加：

```bash
                                  --deep-match-config-path    Path to deep matcher preset JSON config.
                                                              Required when --matcher-method is
                                                              superglue, lightglue, or loftr.
                                                              Default: (read from config JSON)
```

- [ ] **Step 2: 在配置加载后添加深度学习配置校验逻辑**

在现有 `matcher_method` 从配置读取的逻辑之后（约第 1228 行附近），添加：

```bash
  # 加载深度学习配置文件路径（如果配置 JSON 中指定了）
  config_deep_matcher_config_path=$(extract_image_match_config_value "$CONFIG_PATH" "deep_matcher_config_path" "image-match-first")
  if [[ -n "$config_deep_matcher_config_path" && "$config_deep_matcher_config_path" != "null" && -z "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    DEEP_MATCHER_CONFIG_PATH="$config_deep_matcher_config_path"
  fi

  # 校验：深度学习匹配器必须指定配置文件
  case "$MATCHER_METHOD" in
    superglue|lightglue|loftr)
      if [[ -z "$DEEP_MATCHER_CONFIG_PATH" ]]; then
        die "matcher_method '$MATCHER_METHOD' is a deep matcher. You must specify deep_matcher_config_path in the config JSON or use --deep-match-config-path."
      fi
      # 验证文件存在
      if [[ ! -f "$DEEP_MATCHER_CONFIG_PATH" ]]; then
        die "deep matcher config file not found: $DEEP_MATCHER_CONFIG_PATH"
      fi
      # 使用 Python 验证 JSON 格式和必填字段
      "$PYTHON_EXECUTABLE" - "$DEEP_MATCHER_CONFIG_PATH" "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[2]) / "examples" / "controlnet_construct"))
from deep_match_config import load_deep_match_config
try:
    load_deep_match_config(sys.argv[1])
except ValueError as e:
    print(f"ERROR: Invalid deep match config: {e}", file=sys.stderr)
    sys.exit(1)
PY
      if [[ $? -ne 0 ]]; then
        die "Deep match config validation failed for: $DEEP_MATCHER_CONFIG_PATH"
      fi
      ;;
  esac
```

- [ ] **Step 3: 在匹配参数传递中添加 --deep-match-config-path**

在匹配参数构建区域（约第 699 行 `--matcher-method` 之后），添加：

```bash
    if [[ -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
      match_args+=(--deep-match-config-path "$DEEP_MATCHER_CONFIG_PATH")
    fi
```

- [ ] **Step 4: 提交**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh
git commit -m "feat: add deep match config validation in pipeline shell script"
```

---

### Task 6: 修改 `image_match.py` 增加深度学习配置校验入口

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`

当前 `image_match.py` 是一个简单的 re-export wrapper。需要修改为在导入共享模块之前先进行配置校验。

- [ ] **Step 1: 修改 `image_match.py` 为包装模式**

```python
"""Compatibility wrapper for the shared image_match CLI and API with deep match config validation.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example compatibility wrappers follow the repository's example-file header convention.
Updated: 2026-05-16  Geng Xun added deep match config path validation before delegating to shared image_match module.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Deep match config validation
_deep_matcher_config_path = None
for i, arg in enumerate(sys.argv):
    if arg == "--deep-match-config-path" and i + 1 < len(sys.argv):
        _deep_matcher_config_path = sys.argv[i + 1]
        break

if _deep_matcher_config_path is not None:
    # Validate the deep match config before delegating
    from deep_match_config import load_deep_match_config
    try:
        load_deep_match_config(_deep_matcher_config_path)
    except ValueError as exc:
        print(f"ERROR: Deep match config validation failed: {exc}", file=sys.stderr)
        sys.exit(1)

_IMAGE_MATCH_MODULE = import_module("image_match.image_match")
sys.modules[__name__] = _IMAGE_MATCH_MODULE


if __name__ == "__main__":
    _IMAGE_MATCH_MODULE.main()
```

- [ ] **Step 2: 提交**

```bash
git add examples/controlnet_construct/image_match.py
git commit -m "feat: add deep match config validation to controlnet image_match wrapper"
```

---

### Task 7: 集成测试和最终验证

**Files:**
- Test: `tests/unitTest/test_deep_match_config.py`（扩展集成测试）
- Modify: `examples/controlnet_construct/controlnet_config.example.json`（用于测试）

- [ ] **Step 1: 在单元测试中添加集成测试**

在 `tests/unitTest/test_deep_match_config.py` 文件末尾添加：

```python
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
```

- [ ] **Step 2: 运行所有测试**

```bash
PYTHONPATH=examples/controlnet_construct python -m pytest tests/unitTest/test_deep_match_config.py -v
```
Expected: All tests PASS (including new preset file tests)

- [ ] **Step 3: 验证配置文件格式**

```bash
python -c "
import json, sys
sys.path.insert(0, 'examples/controlnet_construct')
from deep_match_config import load_deep_match_config
from pathlib import Path
for p in sorted(Path('examples/controlnet_construct/presets').glob('*.json')):
    cfg = load_deep_match_config(p)
    print(f'OK: {p.name} -> extractor={cfg[\"feature_extractor\"][\"method\"]}, matcher={cfg[\"matcher\"][\"method\"]}')
"
```
Expected: 8 lines showing OK with extractor and matcher methods

- [ ] **Step 4: 提交**

```bash
git add tests/unitTest/test_deep_match_config.py
git commit -m "test: add integration tests for preset file validation"
```

---

## 自审检查

### Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 新增 `deep_matcher_config_path` 字段 | Task 1 |
| 创建 `deep_match_config.py` 加载校验模块 | Task 2 |
| 8 套预设 JSON 文件 | Task 3 |
| `PRESETS_README.md` 适用场景文档 | Task 4 |
| Shell 脚本校验逻辑 | Task 5 |
| `image_match.py` 校验入口 | Task 6 |
| 传统 SIFT 路由不变 | 所有 Task 不修改 tile_matching.py 路由逻辑 |
| CLI 不新增深度学习参数 | Shell 脚本仅传递 `--deep-match-config-path`（配置路径，非模型参数） |
| 深度学习匹配必须指定配置文件 | Task 2 (require_deep_config) + Task 5 (shell case 校验) |
| 向后兼容 | Task 1 默认 null, Task 5 仅对 deep matchers 校验 |

### 占位符扫描
无 "TBD", "TODO", "implement later" 等占位符。

### 类型一致性
- 所有预设 JSON 使用一致的字段名：`feature_extractor.method`, `matcher.method`, `device.dtype`, `fallback.on_error`
- `is_deep_matcher()` 和 `require_deep_config()` 使用统一的 `DEEP_MATCHER_METHODS` 常量
- Shell 脚本中的 `case` 匹配与 Python 中的常量列表一致

### 无冗余
- 未引入 YAGNI 的功能
- 遵循 DRY 原则，校验逻辑集中在 `deep_match_config.py`