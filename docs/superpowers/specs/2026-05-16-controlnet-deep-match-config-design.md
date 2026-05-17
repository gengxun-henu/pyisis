# ControlNet 深度学习匹配配置设计

## 背景

当前 `controlnet_config.example.json` 中通过 `matcher_method` 字段选择匹配方法，但特征提取器与匹配器隐式耦合，无法独立配置。深度学习匹配（SuperGlue/LightGlue/LoFTR）的参数通过代码默认值或 CLI 传递，缺少结构化的配置管理。

## 目标

- 将特征提取器与匹配器解耦，在配置中分别指定
- 深度学习匹配的参数统一由独立 JSON 配置文件管理
- 提供 8 套预设配置文件，覆盖常用特征提取器和匹配器组合
- 传统 SIFT 匹配（bf/flann）保持现有逻辑不变
- CLI 不新增深度学习相关参数

## 架构

### 路由逻辑

```
matcher_method 判断 →
  ├── "bf" / "flann" / "superpoint" → 传统路由（保持现有）
  └── "superglue" / "lightglue" / "loftr" → 深度路由
        ├── deep_matcher_config_path 不为空 → 加载预设 JSON，执行深度学习匹配
        └── deep_matcher_config_path 为空 → 报错退出（必须指定配置文件）
```

### 配置新增字段

在 `controlnet_config.example.json` 的 `ImageMatch` 对象中新增：

```json
"deep_matcher_config_path": null
```

- 类型：`string | null`
- 默认值：`null`
- 语义：当 `matcher_method` 为 `superglue`/`lightglue`/`loftr` 时**必填**，否则忽略
- 值：预设 JSON 文件的绝对或相对路径

### 深度学习预设 JSON 结构

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

## 预设文件清单

存放位置：`examples/controlnet_construct/presets/`

| 文件名 | 提取器 | 匹配器 | 适用场景 |
|--------|--------|--------|----------|
| `superglue_default.json` | SuperPoint | SuperGlue | 高精度标准场景，基准对比 |
| `lightglue_default.json` | SuperPoint | LightGlue | 速度与精度平衡，推荐默认 |
| `loftr_default.json` | LoFTR(内置) | LoFTR(端到端) | 弱纹理区域、大视角变化 |
| `lightglue_high_recall.json` | SuperPoint | LightGlue | 更多特征点（8192 keypoints），高召回需求 |
| `lightglue_disk.json` | DISK | LightGlue | 快速推理、低纹理但结构明显场景 |
| `lightglue_aliked.json` | ALIKED | LightGlue | 高分辨率图像、行星/遥感影像优化 |
| `lightglue_doghardnet.json` | DoGHardNet | LightGlue | 传统DoG检测+HardNet描述子，抗光照变化强 |
| `superglue_aliked.json` | ALIKED | SuperGlue | 高精度需求的高分辨率图像匹配 |

## 特征提取器适用场景

- **SuperPoint:** 通用深度学习特征点检测，端点检测质量好，适合大多数行星空旷纹理场景。与 LightGlue/SuperGlue 配合使用。

- **DISK:** 基于 U-Net 的检测描述一体网络，推理速度快，适合低纹理但有明显结构特征的场景。内存占用低于 SuperPoint。

- **ALIKED:** 轻量高效特征检测器，针对高分辨率遥感影像优化，内存占用低，适合大型影像处理。

- **DoGHardNet:** DoG（Difference of Gaussian）检测器 + HardNet 描述子，传统检测与深度学习描述子混合，抗光照变化和季节性变化能力强。

- **LoFTR (内置):** 端到端密集匹配，无独立特征点概念，适合弱纹理区域和大视角变化场景。特征提取在 LoFTR 网络内部完成。

## 匹配器适用场景

- **SuperGlue:** 基于图神经网络的高精度匹配器，匹配质量好但速度较慢，适合对精度要求高、时间不敏感的场景。

- **LightGlue:** SuperGlue 的轻量加速版本，自适应特征裁剪，速度与精度平衡，推荐作为默认深度学习匹配器。

- **LoFTR (端到端):** Transformer 架构的无特征点密集匹配器，无需独立特征提取，适合弱纹理和大基线匹配。

## 代码改动

### 新增文件

1. `examples/controlnet_construct/presets/` — 8 套预设 JSON
2. `examples/controlnet_construct/deep_match_config.py` — 深度学习配置加载与校验模块

### 修改文件

1. `examples/controlnet_construct/controlnet_config.example.json` — 新增 `deep_matcher_config_path` 字段
2. `examples/controlnet_construct/run_pipeline_example.sh` — 深度学习匹配时校验配置文件是否指定
3. `examples/controlnet_construct/image_match.py` — 路由逻辑：深度学习匹配时加载预设 JSON，校验必填

## 预设 JSON 参数说明

### feature_extractor 字段

| 参数 | 类型 | 适用提取器 | 说明 |
|------|------|-----------|------|
| `method` | string | 全部 | `superpoint`, `disk`, `aliked`, `doghardnet`（LoFTR 不需要此字段） |
| `max_keypoints` | int | SuperPoint/DISK/ALIKED | 最大特征点数 |
| `keypoint_threshold` | float | SuperPoint/DISK/ALIKED | 特征点检测阈值 |
| `remove_borders` | int | SuperPoint/DISK/ALIKED | 边界去除像素数 |
| `detect_keypoints` | bool | SuperPoint | 是否启用特征点检测模式 |

### matcher 字段

| 参数 | 类型 | 适用匹配器 | 说明 |
|------|------|-----------|------|
| `method` | string | 全部 | `superglue`, `lightglue`, `loftr` |
| `weights_path` | string\|null | 全部 | 模型权重路径，null 使用默认权重 |
| `flash` | bool | LightGlue | 是否启用 Flash Attention 加速 |
| `prune_threshold` | int | LightGlue | 特征裁剪阈值 |
| `sinkhorn_iterations` | int | SuperGlue | Sinkhorn 归一化迭代次数 |

### device 字段

| 参数 | 类型 | 说明 |
|------|------|------|
| `prefer_gpu` | bool | 是否优先使用 GPU |
| `dtype` | string | 推理精度：`float32`, `float16`, `bfloat16` |
| `batch_inference` | bool | 是否启用批量推理 |

### fallback 字段

| 参数 | 类型 | 说明 |
|------|------|------|
| `on_error` | string | 深度学习匹配失败时回退的传统方法：`sift_bf`, `sift_flann`，或 null 不 fallback |

## 向后兼容

- 传统 `matcher_method`（bf/flann/superpoint）完全不受影响，使用原有参数和逻辑
- `deep_matcher_config_path` 为 null 时深度学习匹配不触发
- 现有 `run_pipeline_example.sh` 中 `--matcher-method` 为传统匹配时行为不变
- 深度学习匹配必须显式指定配置文件，不使用隐式默认值
