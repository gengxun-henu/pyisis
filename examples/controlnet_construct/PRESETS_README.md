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

## Real Support Status by Preset

| Preset file | Matcher | Extractor | Runtime support | Required environment | Known limitations |
| --- | --- | --- | --- | --- | --- |
| `lightglue_default.json` | LightGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia` + `lightglue`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Best-supported default preset on this branch; `export`/`import` is recommended when `asp360_new` lacks model deps. |
| `lightglue_high_recall.json` | LightGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | Same as `lightglue_default.json` | Higher keypoint count raises runtime and memory cost. |
| `superglue_default.json` | SuperGlue | SuperPoint | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia` + `superglue-pretrained-network`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Slower than LightGlue and usually the heaviest sparse preset. |
| `loftr_default.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows | `direct`: environment with ISIS + `torch` + `kornia`; `export`/`import`: `asp360_new`, plus a deep-learning env for `run_deep_match_manifest.py` | Dense end-to-end matcher; CPU works for smoke validation, but GPU is strongly recommended for real runs. |
| `lightglue_disk.json` | LightGlue | DISK | Config validates, but runtime is not implemented on this branch | No supported runtime path yet | `feature_extractor.method="disk"` is accepted by config validation, but the current adapter only executes SuperPoint for LightGlue/SuperGlue. |
| `lightglue_aliked.json` | LightGlue | ALIKED | Config validates, but runtime is not implemented on this branch | No supported runtime path yet | `feature_extractor.method="aliked"` currently raises a frontend/runtime error before matching starts. |
| `lightglue_doghardnet.json` | LightGlue | DoGHardNet | Config validates, but runtime is not implemented on this branch | No supported runtime path yet | Traditional-extractor preset file exists, but the current deep adapter does not execute DoGHardNet extraction yet. |
| `superglue_aliked.json` | SuperGlue | ALIKED | Config validates, but runtime is not implemented on this branch | No supported runtime path yet | Same extractor limitation as above; SuperGlue execution currently depends on SuperPoint-only extraction support. |

## Wrapper Option Precedence

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
