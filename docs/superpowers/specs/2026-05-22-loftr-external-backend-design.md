# LoFTR External Backend Design

Author: Geng Xun / Codex
Created: 2026-05-22

## Context

`examples/learning_methods/run-loftr.py` has already been validated as a
working two-image LoFTR experiment path. It uses an external LoFTR repository
and explicit checkpoint files, and it exposes practical runtime controls for
model family, preprocessing, confidence filtering, top-k filtering, and optional
geometric filtering.

The ControlNet deep-match runtime is owned by `examples/image_match/`, with
configuration and preset validation owned by
`examples/controlnet_construct/deep_match_config.py`. The existing ControlNet
LoFTR path uses `kornia.feature.LoFTR(pretrained=...)`. That path is useful and
already covered by existing tests, but it is not the same technical path as the
validated `run-loftr.py` script.

This design adds an explicit external LoFTR backend for ControlNet while
preserving the current kornia LoFTR behavior as the default.

## Goal

Add a new ControlNet LoFTR backend that follows the verified external LoFTR
experiment path without changing existing LoFTR preset behavior.

The new backend is selected explicitly through preset/config data:

```json
{
  "feature_extractor": {
    "method": "loftr"
  },
  "matcher": {
    "method": "loftr",
    "backend": "external"
  }
}
```

When `backend` is omitted, current ControlNet LoFTR behavior remains unchanged
and continues to use `kornia.feature.LoFTR(pretrained=...)`.

## Non-Goals

This phase does not:

- Modify `examples/learning_methods/run-loftr.py`.
- Replace the existing kornia LoFTR default backend.
- Change LightGlue or SuperGlue behavior.
- Change ControlNet tile, manifest, `.npz`, `.key`, or visualization output
  formats.
- Require real LoFTR model imports, checkpoint downloads, or GPU access in the
  normal `asp360_new` unit-test path.
- Add batch scheduling or multi-GPU execution.

## Backend Selection

Add `matcher.backend` handling for LoFTR:

- Omitted or empty backend: use the current kornia LoFTR backend.
- `"kornia"`: optional explicit spelling for the current backend.
- `"external"`: use the external LoFTR repository/checkpoint path aligned with
  `run-loftr.py`.

Unknown backend values fail validation.

The external backend keeps `feature_extractor.method: "loftr"` because LoFTR is
an end-to-end matcher with internal feature extraction.

## Configuration

The external backend supports a strict subset of options from
`run-loftr.py`. Unknown options fail validation instead of being silently
ignored.

### Matcher Options

Supported `matcher` fields for `backend: "external"`:

- `method`
- `backend`
- `loftr_root`
- `checkpoint`
- `checkpoint_path`
- `model_type`
- `temp_bug_fix`
- `coarse_threshold`
- `min_confidence`
- `top_k`
- `geometric_filter`
- `ransac_reproj_threshold`
- `ransac_confidence`
- `ransac_max_iters`

`checkpoint` and `checkpoint_path` are aliases for the same concept. If both are
provided with different non-empty values, validation fails.

`model_type` accepts `indoor` or `outdoor`. It controls default checkpoint
discovery when an explicit checkpoint is not provided.

`temp_bug_fix` accepts `auto`, `true`, or `false`, matching `run-loftr.py`.

`geometric_filter` accepts `none`, `homography`, or `fundamental`. It is applied
after confidence and top-k filtering, matching the standalone script.

### Feature Options

Supported `feature_extractor` fields for `backend: "external"`:

- `method`
- `preprocess_mode`
- `resize_width`
- `resize_height`

`preprocess_mode` accepts `pad` or `resize`, matching `run-loftr.py`.

`resize_width` and `resize_height` must be provided together and must be
positive when present.

### Device Options

Existing device fields remain valid:

- `prefer_gpu`
- `dtype`
- `batch_inference`
- `type`

The external LoFTR backend initially executes one image pair at a time. If
`batch_inference` is present, it is preserved in runtime config but not used to
change execution behavior in this phase.

## Presets

Add new external LoFTR presets without changing `loftr_default.json`:

- `examples/controlnet_construct/presets/loftr_external_outdoor.json`
- `examples/controlnet_construct/presets/loftr_external_indoor.json`

The outdoor preset sets:

```json
{
  "feature_extractor": {
    "method": "loftr",
    "preprocess_mode": "pad"
  },
  "matcher": {
    "method": "loftr",
    "backend": "external",
    "model_type": "outdoor",
    "temp_bug_fix": "auto",
    "geometric_filter": "none"
  }
}
```

The indoor preset uses `"model_type": "indoor"` and otherwise follows the same
shape.

`loftr_root` and checkpoint paths are intentionally omitted from the shared
presets so users can keep machine-specific paths in local copies or wrapper
configuration.

## Runtime Design

The implementation keeps ControlNet runtime ownership in `examples/image_match/`.

Recommended structure:

- Extend `examples/controlnet_construct/deep_match_config.py` with backend-aware
  LoFTR validation and strict external option validation.
- Extend `examples/image_match/deep_frontends.py` with reusable LoFTR image
  preparation helpers aligned with `run-loftr.py`:
  - grayscale conversion
  - optional resize
  - pad or resize alignment to multiples of 8
  - valid mask generation for padded regions
  - scale metadata for mapping matches back to original tile coordinates
- Extend `examples/image_match/deep_matchers.py` so `LoFTRMatcher` routes
  between the existing kornia backend and the external backend based on
  `matcher.backend`.
- Keep `examples/image_match/deep_adapter.py` responsible for tile-level
  orchestration, invalid-mask forwarding, fallback behavior, and
  `DeepMatchResult` normalization.

The external backend should reuse logic from `run-loftr.py` by copying small,
runtime-safe helpers or importing shared helpers only if doing so does not pull
CLI side effects into the runtime. The standalone `run-loftr.py` script itself
must remain unchanged.

## External LoFTR Loading

For `backend: "external"`:

1. Resolve `loftr_root`.
   - If `loftr_root` is provided, validate that it contains
     `src/loftr/__init__.py`.
   - If omitted, use the same ancestor/sibling discovery strategy as
     `run-loftr.py`.
2. Resolve checkpoint.
   - If `checkpoint` or `checkpoint_path` is provided, it must exist.
   - If omitted, search the same default candidates as `run-loftr.py` for the
     selected `model_type`.
3. Import `src.loftr` from the resolved repository.
4. Build config from `default_cfg`, `temp_bug_fix`, and optional
   `coarse_threshold`.
5. Load checkpoint state dict strictly.
6. Execute inference with `torch.inference_mode()`.

Missing external repo, missing checkpoint, missing `torch`, or missing LoFTR
module should surface as dependency/setup errors that the ControlNet deep-match
fallback machinery can report clearly.

## Preprocessing and Geometry

The external backend follows the `run-loftr.py` preprocessing model:

- Convert each tile to grayscale float tensor.
- Optionally resize to `resize_width` and `resize_height`.
- With `preprocess_mode: "pad"`, preserve content geometry and pad the
  bottom/right border to the next multiple of 8.
- With `preprocess_mode: "resize"`, resize the inference image to an
  8-aligned size.
- Build coarse masks for padded valid regions when both sides have masks.
- Ensure LoFTR positional encoding capacity before inference.
- Scale returned match coordinates back to the original tile coordinate system.

Existing ControlNet invalid masks remain part of the adapter API. For the
external backend, invalid masks must combine with the LoFTR valid-region masks
so matches from no-data pixels and padded borders are rejected.

## Filtering

The external backend supports post-inference filtering aligned with
`run-loftr.py`:

- `min_confidence`
- `top_k`
- `geometric_filter`
- `ransac_reproj_threshold`
- `ransac_confidence`
- `ransac_max_iters`

Filtering returns the same normalized tuple shape currently consumed by
`DeepMatcherAdapter`: left points, right points, and confidence scores.

## Environment Boundary

Most automated tests run inside `asp360_new` and must mock optional external
LoFTR dependencies. Unit tests must not require real model imports, checkpoint
downloads, or GPU access.

Real external LoFTR execution belongs in the separate `deep-learning` conda
environment where `run-loftr.py` has already been validated. After mocked tests
pass in `asp360_new`, run one manual smoke check in `deep-learning` if that
environment and external LoFTR repository are available.

## Validation Rules

Existing compatibility rules remain:

- `lightglue` without its official backend supports only `superpoint`.
- `superglue` supports only `superpoint`.
- `loftr` supports only `loftr`.

LoFTR backend rules:

- `matcher.method = "loftr"`
- `feature_extractor.method = "loftr"`
- omitted backend or `"kornia"` uses current kornia behavior
- `"external"` uses the new external backend
- unknown backend values fail validation
- external backend rejects unknown matcher and feature options
- external backend validates aliases and enumerated option values

## Testing

Unit tests cover:

- Config validation accepts omitted backend, `"kornia"`, and `"external"` for
  LoFTR.
- Config validation rejects unknown LoFTR backend values.
- Config validation rejects unknown external LoFTR feature and matcher options.
- Config validation rejects conflicting `checkpoint` and `checkpoint_path`.
- Config validation rejects invalid `model_type`, `temp_bug_fix`,
  `preprocess_mode`, and `geometric_filter` values.
- Config validation rejects resize width/height when only one is provided.
- External preset files exist and load.
- Existing `loftr_default.json` remains kornia/default behavior.
- `LoFTRMatcher` preserves current kornia behavior when backend is omitted.
- `LoFTRMatcher` with `backend: "external"` loads external LoFTR using mocked
  modules and forwards supported options.
- External preprocessing produces 8-aligned tensors, valid masks, and scale
  metadata.
- External match output is confidence/top-k filtered and normalized to the
  existing `DeepMatchResult` contract.
- Existing manifest rehydration keeps backend and external options.

Recommended focused verification:

```bash
python tests/smoke_import.py
python -m pytest tests/unitTest/test_deep_match_config.py -q
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
python -m unittest \
  tests.unitTest.deep_match_config_rehydration_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test \
  -v
```

Optional deep-learning smoke:

```bash
conda activate deep-learning
python examples/learning_methods/test-loftr.py
```

If the `deep-learning` environment or external LoFTR repository is unavailable
in the current session, record the smoke as skipped and do not block the mocked
`asp360_new` unit-test completion.

## Documentation

Update `examples/controlnet_construct/PRESETS_README.md` to document:

- The new `matcher.backend: "external"` selector for LoFTR.
- The distinction between existing kornia LoFTR and external LoFTR.
- The two new external presets.
- Machine-specific `loftr_root` and checkpoint guidance.
- The `deep-learning` environment boundary for real external LoFTR execution.

## Acceptance Criteria

- Existing `loftr_default.json` behavior is unchanged when `backend` is omitted.
- New external LoFTR presets validate successfully.
- External LoFTR can be selected through runtime config and manifest
  rehydration.
- External LoFTR runtime follows the validated `run-loftr.py` source path and
  option semantics without modifying `run-loftr.py`.
- Unit tests cover validation, routing, preprocessing, filtering, and mocked
  external model loading.
- Real external LoFTR execution is documented as a `deep-learning` environment
  smoke check.
