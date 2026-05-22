# Deep Match Handoff Notes

Author: Geng Xun / Codex
Created: 2026-05-21

This note records the current relationship between the standalone deep-learning
experiments under `examples/learning_methods/` and the ControlNet construction
deep-match path. It is intended as a quick handoff reference before future
cleanup or feature work.

## Short Answer

The ControlNet deep-learning matching pipeline does not directly call:

- `examples/learning_methods/run-lightglue.py`
- `examples/learning_methods/run-loftr.py`

Those two scripts are standalone two-image experiments for local diagnostics,
parameter tuning, visualization, and CSV output. They are useful references, but
they are not the runtime implementation used by ControlNet construction.

The ControlNet path uses the `examples/image_match` package for actual matching.
The offline deep-learning handoff uses `examples/learning_methods/run_deep_match_manifest.py`.

## Runtime Entry Points

### ControlNet / Image Match Runtime

The main deep matcher entry point is:

```text
examples/image_match/tile_matching.py
```

That module imports:

```python
from .deep_adapter import DeepMatcherAdapter
```

The adapter then routes to:

- `examples/image_match/deep_frontends.py`
- `examples/image_match/deep_matchers.py`

This is the code path used when `matcher_method` is one of:

- `superglue`
- `lightglue`
- `loftr`

### Export / Deep-Learning / Import Workflow

The three-stage handoff is:

1. `asp360_new`: export image tile tasks and invalid masks.
2. deep-learning environment: run exported manifests.
3. `asp360_new`: import `.npz` match results and write `.key` files.

The deep-learning execution script is:

```text
examples/learning_methods/run_deep_match_manifest.py
```

It imports:

```python
from image_match.deep_adapter import DeepMatcherAdapter
from controlnet_construct.deep_match_config import (
    check_deep_match_dependencies,
    deep_match_runtime_config_from_payload,
)
```

So even the manifest runner uses `image_match.deep_adapter` for matching. The
`controlnet_construct.deep_match_config` module is used for config rehydration,
validation, and dependency checks.

## Standalone Experiment Scripts

### `run-lightglue.py`

Role:

- Runs LightGlue or classic OpenCV SIFT on two image files.
- Supports visualization output.
- Supports invalid-pixel filtering aligned with the image-match preprocessing
  helpers.
- Supports feature frontends such as `superpoint`, `disk`, `aliked`, `sift`,
  and `doghardnet`.

Important difference from ControlNet runtime:

- The standalone script supports more LightGlue frontend combinations than the
  current ControlNet runtime.
- The current ControlNet runtime only accepts LightGlue with `superpoint`.

### `run-loftr.py`

Role:

- Runs LoFTR on two image files.
- Supports external LoFTR repository discovery.
- Supports custom checkpoints, padding/resize modes, confidence filtering,
  top-K filtering, CSV export, and match visualization.

Important difference from ControlNet runtime:

- The standalone script uses an external LoFTR repository and checkpoint files.
- The current ControlNet runtime uses `kornia.feature.LoFTR(pretrained=...)`.

This is an implementation difference, not a direct conflict.

## Current Support Matrix

The supported preset state is documented in:

```text
examples/controlnet_construct/PRESETS_README.md
```

Current runtime-supported combinations:

| Matcher | Feature extractor | Status |
| --- | --- | --- |
| `lightglue` | `superpoint` | Supported |
| `lightglue` | `disk` / `aliked` / `doghardnet` | Preset/reference only; rejected by validation |
| `superglue` | `superpoint` | Supported |
| `superglue` | `aliked` | Preset/reference only; rejected by validation |
| `loftr` | `loftr` | Supported |

The strict compatibility rules are in:

```text
examples/controlnet_construct/deep_match_config.py
```

The equivalent runtime checks also exist in:

```text
examples/image_match/deep_adapter.py
examples/image_match/deep_matchers.py
```

## Conflict Assessment

There is no direct call conflict between the standalone scripts and ControlNet
construction.

The real maintenance risks are:

1. Duplicate deep-match implementation files exist under both:
   - `examples/image_match/`
   - `examples/controlnet_construct/`
2. Standalone scripts support experimental capabilities that the ControlNet
   runtime currently rejects.
3. LoFTR has two different implementation styles:
   - external repo/checkpoint in `run-loftr.py`
   - Kornia pretrained model in ControlNet runtime
4. Parameter names and preprocessing options are not fully unified between
   experiment scripts and production-style manifest execution.

## Recommended Optimization Plan

### Phase 1: Low-Risk Cleanup

Goal: reduce duplicate code and make ownership clear.

Recommended actions:

- Treat `examples/image_match` as the owner of runtime deep matcher execution.
- Keep `examples/controlnet_construct/deep_match_config.py` as the owner of
  presets, config validation, runtime-config rehydration, and dependency
  preflight.
- Convert duplicate files under `examples/controlnet_construct/` into thin
  compatibility wrappers, or remove them if no tests/importers depend on them:
  - `deep_adapter.py`
  - `deep_frontends.py`
  - `deep_matchers.py`
- Add tests that confirm old import paths still resolve if wrappers are kept.

This phase should not change matcher behavior.

### Phase 2: Align Experiment Scripts With Runtime APIs

Goal: make experiments produce settings that can be moved into presets.

Recommended actions:

- Refactor `run-lightglue.py` so the matching path can optionally call
  `image_match.deep_adapter.DeepMatcherAdapter` or `image_match.deep_matchers`.
- Keep script-specific responsibilities in the script:
  - CLI parsing
  - image file loading
  - visualization
  - CSV/debug output
- Reuse runtime config structures where possible.
- Update sweep scripts to report preset-compatible parameter names.

This phase improves reproducibility between experiments and ControlNet runs.

### Phase 3: Expand Actual Runtime Support

Goal: promote selected experimental capabilities into ControlNet runtime.

Possible actions:

- Add `DISK`, `ALIKED`, and `DoGHardNet` frontends to
  `examples/image_match/deep_frontends.py`.
- Relax `MATCHER_EXTRACTOR_REQUIREMENTS` only after the frontends are actually
  implemented and covered by tests.
- Decide whether external LoFTR checkpoints are needed in the ControlNet path.
  If yes, add explicit preset fields and runtime support instead of relying on
  the standalone script.
- Add smoke tests for each newly supported matcher/extractor pair.

This phase changes behavior and should be done after Phase 1.

## Suggested Test Targets

For config and manifest behavior:

```bash
python -m unittest \
  tests.unitTest.test_deep_match_config \
  tests.unitTest.deep_match_config_rehydration_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test
```

For quick deep matcher import checks in a deep-learning environment:

```bash
python examples/learning_methods/test-lightglue.py
python examples/learning_methods/test-loftr.py
```

For full ControlNet-oriented validation, use the existing project commands in
`AGENTS.md`, starting with the smoke import before larger suites.

## Practical Recommendation

Start with Phase 1. It clarifies ownership without changing model behavior.
After that, use Phase 2 to make the experiment scripts feed directly into the
same runtime configuration model. Only then promote additional feature
extractors or external LoFTR checkpoint handling into the ControlNet runtime.
