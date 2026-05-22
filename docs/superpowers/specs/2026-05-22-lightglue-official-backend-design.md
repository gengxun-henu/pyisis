# LightGlue Official Backend Design

Author: Geng Xun / Codex
Created: 2026-05-22

## Context

`examples/learning_methods/run-lightglue.py` has already been validated as a
working two-image LightGlue experiment path. It uses the official `lightglue`
package for both feature extraction and matching, exposes the parameters needed
for practical tuning, and supports multiple LightGlue frontend families.

The ControlNet deep-match runtime now has a single implementation owner under
`examples/image_match/`, with `examples/controlnet_construct/deep_*` kept as
compatibility wrappers. The current ControlNet LightGlue path uses
`lightglue.LightGlue` for matching, but its feature extraction path is still
limited to the existing runtime SuperPoint frontend. Existing validation only
accepts `lightglue + superpoint`; the DISK, ALIKED, and DoGHardNet LightGlue
presets remain reference-only.

This design makes the verified `run-lightglue.py` technical path available to
ControlNet without changing the default LightGlue behavior.

## Goal

Add a new ControlNet LightGlue backend that follows the verified official
LightGlue experiment path while preserving the existing backend as the default.

The new backend is selected explicitly through preset/config data:

```json
{
  "matcher": {
    "method": "lightglue",
    "backend": "official"
  }
}
```

When `backend` is omitted, current ControlNet LightGlue behavior remains
unchanged.

## Non-Goals

This phase does not:

- Modify `examples/learning_methods/run-lightglue.py`.
- Modify LoFTR behavior or add an external LoFTR backend.
- Change SuperGlue behavior.
- Change the default `lightglue` backend for existing presets.
- Change ControlNet tile, manifest, `.npz`, `.key`, or visualization output
  formats.
- Remove existing reference presets.

## Supported Frontends

The official backend supports these `feature_extractor.method` values:

| ControlNet method | Official LightGlue frontend |
| --- | --- |
| `superpoint` | `lightglue.SuperPoint` |
| `disk` | `lightglue.DISK` |
| `aliked` | `lightglue.ALIKED` |
| `doghardnet` | `lightglue.DoGHardNet` |
| `lightglue_sift` | `lightglue.SIFT` |

`lightglue_sift` is intentionally named differently from `sift` to avoid
confusion with the existing classic OpenCV SIFT matcher path. Documentation must
state that `lightglue_sift` means the official LightGlue SIFT frontend paired
with `lightglue.LightGlue`, not the classic ControlNet SIFT matcher.

## Configuration

### Backend Selection

Add `matcher.backend` handling for LightGlue:

- Omitted or legacy value: use the current ControlNet LightGlue backend.
- `"official"`: use the official LightGlue frontend and matcher backend.

The exact legacy backend label may be internal, but behavior for existing
presets must remain unchanged when `backend` is absent.

### Feature Options

The official backend supports:

- `max_features`
- `max_keypoints`

`max_keypoints` is accepted as a compatibility alias and maps to the official
LightGlue extractor argument `max_num_keypoints`. If both `max_features` and
`max_keypoints` are present, validation fails instead of choosing one
silently.

The official backend rejects unknown feature extractor options.

### Matcher Options

The official backend supports:

- `filter_threshold`
- `depth_confidence`
- `width_confidence`
- `flash`
- `mp`

The official backend rejects unknown matcher options. It must not
silently ignore parameters copied from existing runtime presets unless they are
explicitly supported by this design.

Existing non-official LightGlue behavior remains unchanged.

## Presets

Add new official backend presets without changing existing preset meanings:

- `examples/controlnet_construct/presets/lightglue_official_superpoint.json`
- `examples/controlnet_construct/presets/lightglue_official_disk.json`
- `examples/controlnet_construct/presets/lightglue_official_aliked.json`
- `examples/controlnet_construct/presets/lightglue_official_doghardnet.json`
- `examples/controlnet_construct/presets/lightglue_official_sift.json`

Each official preset sets:

```json
{
  "matcher": {
    "method": "lightglue",
    "backend": "official"
  }
}
```

The SIFT preset must use:

```json
{
  "feature_extractor": {
    "method": "lightglue_sift"
  }
}
```

## Runtime Design

The implementation keeps ControlNet runtime ownership in
`examples/image_match/`.

Recommended structure:

- Extend `examples/image_match/deep_frontends.py` with an official LightGlue
  frontend helper that constructs official `lightglue` extractors and converts
  tile image arrays into the tensor shapes expected by each frontend.
- Extend `examples/image_match/deep_matchers.py` so the LightGlue matcher can
  route between the legacy backend and the official backend based on
  `matcher.backend`.
- Keep `examples/image_match/deep_adapter.py` responsible for tile-level
  orchestration, invalid-mask filtering, and result normalization.
- Keep `examples/controlnet_construct/deep_match_config.py` responsible for
  preset validation and runtime-config rehydration.

The official backend follows `run-lightglue.py` behavior where relevant:

- Official frontend classes come from the `lightglue` package.
- `max_features` / `max_keypoints` maps to `max_num_keypoints`.
- Grayscale images are normalized to `float32` in `[0, 1]`.
- DISK and ALIKED receive 3-channel tensors.
- SuperPoint, DoGHardNet, and LightGlue-SIFT receive single-channel tensors
  unless the official implementation requires otherwise.
- Invalid keypoints are removed after feature extraction using the ControlNet
  invalid mask.

## Validation Rules

Current non-official compatibility rules remain unchanged:

- `lightglue` without `backend: "official"` supports only `superpoint`.
- `superglue` supports only `superpoint`.
- `loftr` supports only `loftr`.

Official LightGlue compatibility rules:

- `matcher.method = "lightglue"`
- `matcher.backend = "official"`
- `feature_extractor.method` must be one of:
  - `superpoint`
  - `disk`
  - `aliked`
  - `doghardnet`
  - `lightglue_sift`

Unknown backend values fail validation.

## Testing

Unit tests cover:

- Config validation accepts the new official LightGlue frontend combinations.
- Config validation still rejects `disk` / `aliked` / `doghardnet` when
  `backend: "official"` is absent.
- Config validation rejects unknown backend values.
- Official backend rejects unknown feature/matcher options.
- `max_features` and `max_keypoints` map to `max_num_keypoints`; specifying
  both fails.
- Official frontend construction uses the expected `lightglue` classes for each
  frontend method.
- DISK and ALIKED receive 3-channel input tensors; the other frontends receive
  the intended input shape.
- Invalid-mask filtering removes feature rows consistently with the existing
  adapter behavior.
- Official LightGlue matcher output is normalized to the existing
  `DeepMatchResult` contract.
- Existing non-official LightGlue tests continue to pass.

Recommended focused verification:

```bash
python tests/smoke_import.py
python -m unittest tests.unitTest.test_deep_match_config -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test -v
```

In a deep-learning environment that has `lightglue` installed, run at least one
manual or smoke check with an official preset.

## Documentation

Update `examples/controlnet_construct/PRESETS_README.md` to document:

- The new `backend: "official"` selector.
- The five official LightGlue presets.
- The distinction between `lightglue_sift` and classic SIFT.
- Existing presets remain unchanged unless they explicitly select the official
  backend.

## Acceptance Criteria

- Existing LightGlue presets behave as before when `backend` is omitted.
- New official LightGlue presets validate successfully.
- Reference-only old DISK / ALIKED / DoGHardNet presets keep their existing
  semantics unless explicitly changed in a later phase.
- The official backend can be selected through runtime config and manifest
  rehydration.
- Tests cover strict option validation and frontend routing.
- No LoFTR behavior changes are included in this phase.
