# Deep Match Presets

This document summarizes the deep-match preset JSON files in `examples/controlnet_construct/presets/`, the real runtime support state on this branch, and the recommended `direct` / `export` / `import` workflows.

## Recommended Execution Modes

The wrappers support three deep-match execution modes:

- `direct`: run deep matching inline in the current environment. Use this only when the current Python environment already has the required deep-learning dependencies.
- `export`: run the normal overlap / tiling stage in `asp360_new`, but stop after writing manifest workspaces and `deep_match_manifests.json`.
- `import`: resume in `asp360_new` after a deep-learning environment has written NPZ results for every exported manifest task.

Recommended commands:

### 1. Direct mode

Use this when one environment already contains both ISIS runtime access and the needed deep-learning packages.

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode direct \
  --deep-match-config-path examples/controlnet_construct/presets/lightglue_default.json
```

### 2. Export mode

Use this in `asp360_new` when the current environment can prepare overlap crops and manifests but should not import Torch / model packages.

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode export \
  --deep-match-config-path examples/controlnet_construct/presets/lightglue_default.json
```

This writes per-pair workspaces under `work/deep_match_workspaces/` and a compact summary file at `work/deep_match_manifests.json`.

### 3. Manifest execution + import mode

Run the exported manifests in a deep-learning environment first:

```bash
python examples/learning_methods/run_deep_match_manifest.py \
  work/deep_match_workspaces/left__right/tasks.json \
  --device cpu \
  --summary-output work/deep_match_workspaces/left__right/manifest_run_summary.json
```

Then switch back to `asp360_new` and import the written NPZ results:

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode import \
  --deep-match-manifest-dir work/deep_match_workspaces \
  --deep-match-manifest-summary work/deep_match_manifests.json
```

`run_pipeline_example.sh` forwards the same deep-match mode flags and uses `work/reports/deep_match_manifests.json` by default.

## Preset Catalog

| Preset File | Feature Extractor | Matcher | Use Case |
|-------------|-------------------|---------|----------|
| `superglue_default.json` | SuperPoint | SuperGlue | High-accuracy standard scenarios. Best match quality but slower. |
| `lightglue_default.json` | SuperPoint | LightGlue | Speed-accuracy balance, recommended default. Adaptive feature cropping. |
| `loftr_default.json` | LoFTR (built-in) | LoFTR (end-to-end) | Weak-texture areas, large viewpoint changes. No independent keypoints needed. |
| `loftr_external_outdoor.json` | LoFTR (built-in) | LoFTR external backend | Outdoor external LoFTR repository/checkpoint path aligned with `run-loftr.py`. |
| `loftr_external_indoor.json` | LoFTR (built-in) | LoFTR external backend | Indoor external LoFTR repository/checkpoint path aligned with `run-loftr.py`. |
| `lightglue_high_recall.json` | SuperPoint | LightGlue | High-recall needs, extracts 8192 keypoints with lower detection threshold. |
| `lightglue_disk.json` | DISK | LightGlue | Compatibility reference preset only. Current runtime rejects it because LightGlue execution is limited to SuperPoint-backed extraction. |
| `lightglue_aliked.json` | ALIKED | LightGlue | Compatibility reference preset only. Current runtime rejects it because LightGlue execution is limited to SuperPoint-backed extraction. |
| `lightglue_doghardnet.json` | DoGHardNet | LightGlue | Compatibility reference preset only. Current runtime rejects it because LightGlue execution is limited to SuperPoint-backed extraction. |
| `superglue_aliked.json` | ALIKED | SuperGlue | Compatibility reference preset only. Current runtime rejects it because SuperGlue execution is limited to SuperPoint-backed extraction. |

## Real Support Status by Preset

| Preset file | Matcher | Extractor | Runtime support | Required environment | Known limitations |
| --- | --- | --- | --- | --- | --- |
| `lightglue_default.json` | LightGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia` + `lightglue`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Best-supported default preset on this branch; `export`/`import` is recommended when `asp360_new` lacks model deps. |
| `lightglue_high_recall.json` | LightGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | Same as `lightglue_default.json` | Higher keypoint count raises runtime and memory cost. |
| `superglue_default.json` | SuperGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia` + `superglue-pretrained-network`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Slower than LightGlue and usually the heaviest sparse preset. |
| `loftr_default.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Dense end-to-end matcher; CPU works for smoke validation, but GPU is strongly recommended for real runs. |
| `loftr_external_outdoor.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows when external LoFTR dependencies are available | `direct`: environment with ISIS + `torch` + external LoFTR repo/checkpoint; `export`/`import`: `asp360_new`, plus `deep-learning` for manifest execution | Uses `matcher.backend="external"` and the outdoor checkpoint family from `run-loftr.py`; `loftr_root` and checkpoint paths are machine-specific and should be supplied in local config when auto-discovery is not enough. |
| `loftr_external_indoor.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows when external LoFTR dependencies are available | Same as `loftr_external_outdoor.json` | Uses the indoor checkpoint family and `temp_bug_fix:auto`; GPU is recommended for real runs. |
| `lightglue_disk.json` | LightGlue | DISK | Unsupported by the current runtime on this branch | No supported runtime path yet | Official LightGlue preset validation may accept future extractor names, but this branch's runtime fails fast for non-SuperPoint LightGlue extraction. |
| `lightglue_aliked.json` | LightGlue | ALIKED | Unsupported by the current runtime on this branch | No supported runtime path yet | Official LightGlue preset validation may accept future extractor names, but this branch's runtime fails fast for non-SuperPoint LightGlue extraction. |
| `lightglue_doghardnet.json` | LightGlue | DoGHardNet | Unsupported by the current runtime on this branch | No supported runtime path yet | Official LightGlue preset validation may accept future extractor names, but this branch's runtime fails fast for non-SuperPoint LightGlue extraction. |
| `superglue_aliked.json` | SuperGlue | ALIKED | Rejected during config validation on this branch | No supported runtime path yet | Strict compatibility validation requires `feature_extractor.method="superpoint"` for SuperGlue. |

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
- **Pairs with:** Planned LightGlue integration; current runtime validation rejects this pairing.
- **Pros:** Fast inference, lower memory than SuperPoint
- **Cons:** Average results on extremely weak-texture scenes

### ALIKED

- **Type:** Lightweight efficient feature detector
- **Use case:** High-resolution images, planetary/remote sensing optimized. Low memory, suitable for large image processing.
- **Pairs with:** Planned LightGlue/SuperGlue integration; current runtime validation rejects these pairings.
- **Pros:** Lightweight, optimized for high resolution
- **Cons:** May underperform SuperPoint on low-resolution images

### DoGHardNet

- **Type:** DoG (Difference of Gaussian) detector + HardNet descriptor
- **Use case:** Traditional detector with deep learning descriptor, strong resistance to illumination and seasonal changes.
- **Pairs with:** Planned LightGlue integration; current runtime validation rejects this pairing.
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

## External LoFTR Backend

LoFTR presets whose matcher section contains `"backend": "external"` use the
external LoFTR repository and checkpoint workflow validated by
`examples/learning_methods/run-loftr.py`.

Existing LoFTR presets without `backend: "external"` keep the current
ControlNet runtime behavior based on `kornia.feature.LoFTR(pretrained=...)`.
This allows side-by-side comparison between the kornia backend and the external
backend.

External LoFTR supports these preset/runtime options:

- `matcher.model_type`: `outdoor` or `indoor`
- `matcher.loftr_root`: optional path to the external LoFTR repository
- `matcher.checkpoint` or `matcher.checkpoint_path`: optional explicit checkpoint
- `matcher.temp_bug_fix`: `auto`, `true`, or `false`
- `matcher.coarse_threshold`
- `matcher.min_confidence`
- `matcher.top_k`
- `matcher.geometric_filter`: `none`, `homography`, or `fundamental`
- `matcher.ransac_reproj_threshold`
- `matcher.ransac_confidence`
- `matcher.ransac_max_iters`
- `feature_extractor.preprocess_mode`: `pad` or `resize`
- `feature_extractor.resize_width` and `feature_extractor.resize_height`

Shared presets omit `loftr_root` and checkpoint paths because those values are
machine-specific. If auto-discovery cannot find the sibling external LoFTR
repository, copy the preset and add `matcher.loftr_root` locally.

Real external LoFTR execution should run in the separate `deep-learning` conda
environment. The `asp360_new` environment remains the recommended environment
for ControlNet preparation, export, import, and unit tests.

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

## Wrapper Option Precedence

Both wrapper entrypoints (`run_pipeline_example.sh` and `run_image_match_batch_example.sh`) use the same precedence for matching options:

1. explicit CLI flags such as `--matcher-method`, `--deep-match-config-path`, `--adaptive-routing`, or `--adaptive-routing-profile`
2. fields under config JSON `ImageMatch`
3. script defaults

When `ImageMatch.deep_matcher_config_path` is relative, the wrappers resolve it relative to the config file directory first. If that file does not exist, they fall back to resolving it relative to the repository root. The resolved path is printed in the wrapper log before it is forwarded to `examples/image_match/image_match.py`.

Current runtime support boundaries are:

- `lightglue` runtime support currently requires `feature_extractor.method: superpoint`; official LightGlue preset validation may accept future extractor names, but this branch's runtime fails fast for non-SuperPoint.
- `superglue` requires `feature_extractor.method: superpoint`
- `loftr` requires `feature_extractor.method: loftr`

Presets that violate those combinations are kept as reference examples for future extractor rollouts, but they now fail during config validation instead of being ignored at runtime.

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
- `preprocess_mode`: LoFTR external preprocessing mode (`pad` or `resize`)
- `resize_width`, `resize_height`: optional LoFTR external resize dimensions; must be provided together

**matcher:**
- `method`: Matcher method (`superglue`, `lightglue`, `loftr`)
- `weights_path`: Model weight path, null uses default weights
- `flash`: Enable Flash Attention (LightGlue only)
- `prune_threshold`: Feature pruning threshold (LightGlue only)
- `sinkhorn_iterations`: Sinkhorn normalization iterations (SuperGlue only)
- `backend`: LoFTR backend selector (`external` or `kornia`); LightGlue currently uses its existing default runtime path and shared presets should omit `backend` unless a runtime path explicitly documents it.
- `loftr_root`: external LoFTR repository path for `backend: external`
- `checkpoint`, `checkpoint_path`: external LoFTR checkpoint path aliases
- `model_type`: LoFTR external checkpoint family (`outdoor` or `indoor`)
- `temp_bug_fix`, `coarse_threshold`, `min_confidence`, `top_k`, `geometric_filter`, `ransac_reproj_threshold`, `ransac_confidence`, `ransac_max_iters`: LoFTR external tuning options

**device:**
- `prefer_gpu`: Prefer GPU execution
- `dtype`: Inference precision (`float32`, `float16`, `bfloat16`)
- `batch_inference`: Enable batch inference

**fallback:**
- `on_error`: Fallback method (`sift_bf`, `sift_flann`, null)
