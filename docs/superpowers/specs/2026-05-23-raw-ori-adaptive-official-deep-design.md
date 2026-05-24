# Raw Original Image Adaptive Official Deep Matching Design

Author: Geng Xun / Codex
Created: 2026-05-23

## Goal

Extend the raw/original image space ControlNet path so it can use adaptive
texture and lighting analysis during pair matching, while narrowing the
recommended deep-learning matcher surface to official LightGlue and external
official LoFTR.

The target ControlNet construction stack should be:

- classic SIFT `bf` / `flann` as the reliable baseline and fallback;
- official LightGlue presets for learned sparse matching;
- external official LoFTR presets for difficult, weak-texture, or
  high-lighting-difference pairs.

The existing DOM pipeline already has adaptive routing. This design adds the
same decision capability to the raw image space wrapper without assuming DOM
previews, DOM low-resolution offset products, or DOM-to-original coordinate
conversion.

## Current Context

The raw image space wrapper exists at:

```text
examples/controlnet_construct/run_ori_match_pipeline_example.sh
```

It currently runs:

1. `image_overlap.py` to build image pairs from `original_images.lis`.
2. `controlnet_stereopair.py from-ori-match` for each pair.
3. `controlnet_merge.py` for final merge preparation and optional execution.

The first raw wrapper version intentionally rejects `--adaptive-routing`,
`--deep-match-config-path`, and `--deep-match-mode`. The documentation also
states that the raw wrapper does not yet connect deep matchers or adaptive
routing.

The DOM matching path already computes adaptive diagnostics in
`examples/image_match/image_match.py`:

- image texture probes;
- pair texture sparseness;
- solar lighting difference from cube labels;
- matcher routing and fallback cascade;
- adaptive sidecar metadata.

That DOM implementation currently depends on low-resolution preview DOMs from
the coarse-offset stage or explicit preview DOM inputs. Raw original images need
their own preview and diagnostic source because they do not have DOM projection
space and should not require DOM preparation.

## Scope

In scope:

- Add raw image space adaptive routing to the design of
  `run_ori_match_pipeline_example.sh`.
- Support texture sparseness and lighting-difference diagnostics from original
  ISIS cubes.
- Allow raw pair matching to choose among classic SIFT, official LightGlue, and
  external official LoFTR.
- Keep default raw wrapper behavior conservative: classic `flann` remains the
  default when adaptive routing is not enabled.
- Define a preset cleanup target that removes non-recommended deep matcher
  presets after references and tests have been updated.
- Preserve existing DOM pipeline behavior.

Out of scope for the first implementation plan derived from this spec:

- Deleting deep matcher code before references are inventoried.
- Changing scientific overlap semantics or adding sampling policy.
- Replacing the existing `from-ori-match` ControlNet writer.
- Requiring GPU or external model downloads in the normal unit-test path.
- Claiming full photometric modeling. The first raw adaptive pass uses
  lightweight texture and available solar/camera lighting diagnostics.

## Recommended Matcher Surface

### Keep As Recommended

Classic presets:

- `examples/controlnet_construct/presets/classic_sift_bf.json`
- `examples/controlnet_construct/presets/classic_sift_flann.json`

Official LightGlue presets:

- `examples/controlnet_construct/presets/lightglue_official_superpoint.json`
- `examples/controlnet_construct/presets/lightglue_official_disk.json`
- `examples/controlnet_construct/presets/lightglue_official_aliked.json`
- `examples/controlnet_construct/presets/lightglue_official_doghardnet.json`
- `examples/controlnet_construct/presets/lightglue_official_sift.json`

External official LoFTR presets:

- `examples/controlnet_construct/presets/loftr_external_outdoor.json`
- `examples/controlnet_construct/presets/loftr_external_indoor.json`

For normal ControlNet construction, the default learned matcher recommendation
is:

- official LightGlue SuperPoint for moderate pairs;
- external official LoFTR outdoor for weak texture or large lighting
  difference, unless the mission/dataset clearly needs the indoor checkpoint.

### Keep Only As Compatibility During Migration

- `examples/controlnet_construct/presets/loftr_default.json`

This preset uses the Kornia LoFTR backend. It is useful as a compatibility
fallback, but it is not the official LoFTR repository/checkpoint path selected
for the target ControlNet stack.

### Deprecate Then Remove

Legacy non-official LightGlue presets:

- `examples/controlnet_construct/presets/lightglue_default.json`
- `examples/controlnet_construct/presets/lightglue_high_recall.json`
- `examples/controlnet_construct/presets/lightglue_disk.json`
- `examples/controlnet_construct/presets/lightglue_aliked.json`
- `examples/controlnet_construct/presets/lightglue_doghardnet.json`

SuperGlue presets:

- `examples/controlnet_construct/presets/superglue_default.json`
- `examples/controlnet_construct/presets/superglue_aliked.json`

`superglue_aliked.json` is not an official LightGlue or official LoFTR preset.
It combines ALIKED with SuperGlue and belongs outside the recommended raw/DOM
ControlNet construction path.

The cleanup must be staged: first update docs, examples, experiment configs,
and tests to avoid these presets; then remove preset files and any dead
SuperGlue or legacy LightGlue runtime paths that no longer have supported
callers.

## Raw Adaptive Diagnostics

Raw adaptive routing should use a raw-preview diagnostic layer instead of DOM
preview DOMs.

### Texture

Texture sparseness should reuse the existing
`examples/image_match/texture_sparseness.py` semantics:

- `0` means texture-rich;
- `1` means texture-sparse;
- pair sparseness is based on the weaker side.

The raw path should compute texture from original image tiles or reduced raw
preview reads. It should avoid loading a full large cube into memory when tile
or window readers are available.

### Lighting

The first raw adaptive pass should use available ISIS cube metadata:

- solar elevation and azimuth from labels when present;
- tile-level lighting summaries from camera/sample functions when available in
  a low-cost form;
- explicit diagnostic reasons when fields are missing.

The routing contract must tolerate partial lighting data. Missing lighting
should not abort matching; it should reduce routing confidence and leave the
texture decision active.

### Sidecar

Every raw adaptive pair should write diagnostics into the pair report and batch
summary:

- adaptive status;
- preview sources;
- texture sparseness summary;
- lighting difference summary;
- selected initial matcher;
- selected final matcher;
- fallback cascade attempts;
- quality gate result.

This should mirror the DOM adaptive metadata shape where practical so later
reporting tools can compare DOM and raw runs without special-case parsing.

## Raw Routing Policy

Raw adaptive routing should use the same conservative policy as the DOM route:

- rich texture and small lighting difference:
  - start with the requested classic matcher, normally `flann`;
  - fallback to official LightGlue and then external LoFTR if quality gates
    fail.
- moderate texture sparseness or moderate lighting difference:
  - start with official LightGlue;
  - fallback to external LoFTR.
- high texture sparseness or large lighting difference:
  - start with external official LoFTR.

Quality gates should use the existing adaptive routing profiles:

- `balanced`
- `strict`
- `relaxed`
- `fast`

The raw wrapper default remains adaptive routing off. Users opt in through CLI
or config.

## CLI and Config Surface

Add raw wrapper support for:

- `--adaptive-routing` / `--no-adaptive-routing`
- `--adaptive-routing-profile VALUE`
- `--deep-match-config-path PATH`
- `--adaptive-routing-deep-preset KEY=PATH` or equivalent config-only mapping
- `--deep-match-mode direct`

The first raw adaptive implementation should support direct execution only.
Deep export/import can be added later if the raw direct path proves stable.

Config should use the existing `ImageMatch` keys where their meaning is shared:

- `enable_adaptive_routing`
- `adaptive_routing_profile`
- `adaptive_routing_deep_presets`
- `deep_matcher_config_path`
- `matcher_method`

Raw-specific diagnostic options should be added only when the existing
`ImageMatch` key would be misleading.

## Data Flow

1. `run_ori_match_pipeline_example.sh` reads config and CLI values.
2. For each overlap pair, it calls `controlnet_stereopair.py from-ori-match`
   with adaptive and deep config options.
3. `from-ori-match` invokes raw image matching with an explicit image-space
   value of `ori`.
4. The raw image matching layer builds raw diagnostics:
   - texture sparseness;
   - solar/camera lighting diagnostics;
   - route decision.
5. The matcher runs the selected cascade:
   - classic SIFT;
   - official LightGlue;
   - external official LoFTR.
6. Accepted raw-image keypoints are written directly as original-image
   measures.
7. Pairwise ControlNets are built without DOM-to-original conversion.
8. Batch summary records adaptive diagnostics and final matcher choice.

## Error Handling

Adaptive diagnostics are best-effort:

- missing solar geometry records a diagnostic and continues;
- failed texture preview records a diagnostic and falls back to the requested
  matcher;
- missing official LightGlue dependency triggers the existing deep matcher
  fallback when configured;
- missing external LoFTR repository or checkpoint is reported clearly and can
  fall back to classic SIFT if `fallback.on_error` is configured.

The wrapper must fail fast for invalid preset paths, unsupported profiles, or
unsupported deep-match modes.

## Cleanup Strategy

The cleanup should happen after raw adaptive routing can use official
LightGlue and external LoFTR presets.

Phase 1: mark non-recommended presets as deprecated in docs and preset lists.

Phase 2: update tests, examples, and matcher-comparison configs so the
recommended surface is classic, official LightGlue, and external LoFTR.

Phase 3: remove deprecated preset files once no supported docs/tests reference
them.

Phase 4: remove dead runtime code only when static search and tests show no
supported caller remains. SuperGlue and legacy non-official LightGlue code are
cleanup candidates, not first-step deletions.

## Testing

Focused tests should cover:

- raw wrapper forwards adaptive routing, profile, and official deep preset
  paths in dry-run command generation;
- raw wrapper still defaults to classic `flann` when adaptive routing is off;
- raw image diagnostics compute texture sparseness from tile/window readers;
- raw lighting diagnostics handle complete, partial, and missing solar
  metadata;
- raw routing chooses classic, official LightGlue, or external LoFTR for low,
  moderate, and high difficulty synthetic diagnostics;
- adaptive fallback cascade records initial and final matcher decisions;
- official LightGlue and external LoFTR preset validation remains strict;
- deprecated preset references are absent from recommended docs and examples
  before file deletion.

Recommended verification for implementation work:

```bash
python tests/smoke_import.py
python -m unittest tests.unitTest.image_match_texture_sparseness_unit_test -v
python -m unittest tests.unitTest.image_match_lighting_difference_unit_test -v
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k ori -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k adaptive -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -k adaptive -v
```

## Success Criteria

- The raw wrapper can opt into adaptive routing without requiring DOM products.
- Raw adaptive reports include texture, lighting, route, cascade, and final
  matcher diagnostics.
- Recommended deep-learning ControlNet docs point to official LightGlue and
  external official LoFTR only.
- `loftr_default.json` is clearly documented as Kornia compatibility, not the
  official LoFTR route.
- `superglue_aliked.json` and other SuperGlue presets are no longer presented
  as recommended ControlNet construction presets.
- Legacy non-official LightGlue presets are deprecated before removal.
- Existing DOM pipeline behavior remains unchanged.
