# Deep Match Presets

This document describes the preset configuration files in `presets/` and the applicable scenarios for each feature extractor and matcher.

## Preset Catalog

| Preset File | Feature Extractor | Matcher | Use Case |
|-------------|-------------------|---------|----------|
| `superglue_default.json` | SuperPoint | SuperGlue | High-accuracy standard scenarios. Best match quality but slower. |
| `lightglue_default.json` | SuperPoint | LightGlue | Speed-accuracy balance, recommended default. Adaptive feature cropping. |
| `loftr_default.json` | LoFTR (built-in) | LoFTR (end-to-end) | Weak-texture areas, large viewpoint changes. No independent keypoints needed. |
| `lightglue_high_recall.json` | SuperPoint | LightGlue | High-recall needs, extracts 8192 keypoints with lower detection threshold. |
| `lightglue_disk.json` | DISK | LightGlue | Fast inference, low-texture but structurally distinct scenes. Low memory footprint. |
| `lightglue_aliked.json` | ALIKED | LightGlue | High-resolution images, planetary/remote sensing optimized. Lightweight and efficient. |
| `lightglue_doghardnet.json` | DoGHardNet | LightGlue | Traditional DoG detector + HardNet descriptor, strong resistance to illumination and seasonal changes. |
| `superglue_aliked.json` | ALIKED | SuperGlue | High-accuracy matching for high-resolution images. |

## Feature Extractors

### SuperPoint

- **Type:** Deep learning keypoint detector + descriptor network
- **Use case:** General-purpose deep feature detection, good endpoint quality. Suitable for most planetary sparse-texture scenes.
- **Pairs with:** LightGlue, SuperGlue
- **Pros:** High detection quality, accurate endpoint descriptors
- **Cons:** Slower than traditional methods, GPU recommended

### DISK

- **Type:** U-Net-based detection-description network
- **Use case:** Fast inference, low-texture but structurally distinct scenes.
- **Pairs with:** LightGlue
- **Pros:** Fast inference, lower memory than SuperPoint
- **Cons:** Average results on extremely weak-texture scenes

### ALIKED

- **Type:** Lightweight efficient feature detector
- **Use case:** High-resolution images, planetary/remote sensing optimized. Low memory, suitable for large image processing.
- **Pairs with:** LightGlue, SuperGlue
- **Pros:** Lightweight, optimized for high resolution
- **Cons:** May underperform SuperPoint on low-resolution images

### DoGHardNet

- **Type:** DoG (Difference of Gaussian) detector + HardNet descriptor
- **Use case:** Traditional detector with deep learning descriptor, strong resistance to illumination and seasonal changes.
- **Pairs with:** LightGlue
- **Pros:** Strong illumination invariance, no trained model needed
- **Cons:** Detection quality lower than pure deep learning methods

### LoFTR (built-in)

- **Type:** End-to-end dense matching network (no independent extractor)
- **Use case:** Weak-texture areas and large viewpoint changes. Feature extraction is done internally by the LoFTR network.
- **Pairs with:** Itself (end-to-end)
- **Pros:** No independent keypoints needed, good for weak texture
- **Cons:** Slow, high memory usage

## Matchers

### SuperGlue

- **Type:** Graph neural network-based high-precision matcher
- **Use case:** Precision-critical, time-insensitive scenarios.
- **Pros:** Highest match quality
- **Cons:** Slower, computationally intensive

### LightGlue

- **Type:** Lightweight accelerated version of SuperGlue
- **Use case:** Speed-accuracy balance, recommended as default deep learning matcher.
- **Pros:** Adaptive feature cropping, fast
- **Cons:** Slightly lower peak precision than SuperGlue

### LoFTR (end-to-end)

- **Type:** Transformer-based keypoint-free dense matcher
- **Use case:** Weak-texture and large-baseline matching.
- **Pros:** No feature extraction needed, direct end-to-end matching
- **Cons:** Slow, requires GPU

## Usage

Specify the preset path in the `ImageMatch` section of `controlnet_config.json`:

```json
{
  "ImageMatch": {
    "matcher_method": "lightglue",
    "deep_matcher_config_path": "presets/lightglue_default.json"
  }
}
```

Both wrapper entrypoints (`run_pipeline_example.sh` and `run_image_match_batch_example.sh`) use the same precedence for matching options:

1. explicit CLI flags such as `--matcher-method`, `--deep-match-config-path`, `--adaptive-routing`, or `--adaptive-routing-profile`
2. fields under config JSON `ImageMatch`
3. script defaults

When `ImageMatch.deep_matcher_config_path` is relative, the wrappers resolve it relative to the config file directory first. If that file does not exist, they fall back to resolving it relative to the repository root. The resolved path is printed in the wrapper log before it is forwarded to `examples/image_match/image_match.py`.

For example, if `examples/controlnet_construct/controlnet_config.example.json` contains `"deep_matcher_config_path": "presets/lightglue_default.json"`, it resolves to `examples/controlnet_construct/presets/lightglue_default.json`. If a custom config outside the repository uses the same relative value and has its own adjacent `presets/` directory, that adjacent preset wins.

## Custom Presets

Copy any preset file to a custom path, modify parameters, and specify it via `deep_matcher_config_path`.

### Configuration Fields

**feature_extractor:**
- `method`: Extractor method (`superpoint`, `disk`, `aliked`, `doghardnet`, `loftr`)
- `max_keypoints`: Maximum keypoints (not needed for LoFTR)
- `keypoint_threshold`: Detection threshold (not needed for LoFTR)
- `remove_borders`: Border removal pixels (not needed for LoFTR)
- `detect_keypoints`: Enable keypoint detection mode (SuperPoint only)

**matcher:**
- `method`: Matcher method (`superglue`, `lightglue`, `loftr`)
- `weights_path`: Model weight path, null uses default weights
- `flash`: Enable Flash Attention (LightGlue only)
- `prune_threshold`: Feature pruning threshold (LightGlue only)
- `sinkhorn_iterations`: Sinkhorn normalization iterations (SuperGlue only)

**device:**
- `prefer_gpu`: Prefer GPU execution
- `dtype`: Inference precision (`float32`, `float16`, `bfloat16`)
- `batch_inference`: Enable batch inference

**fallback:**
- `on_error`: Fallback method (`sift_bf`, `sift_flann`, null)
