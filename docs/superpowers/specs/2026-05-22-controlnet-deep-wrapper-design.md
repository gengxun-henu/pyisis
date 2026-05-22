# ControlNet Deep Matcher Wrapper Design

Author: Geng Xun / Codex
Created: 2026-05-22

## Context

The deep-learning match handoff notes at
`examples/controlnet_construct/deep_match_handoff.md` identify
`examples/image_match` as the owner of runtime deep matcher execution. The
ControlNet package still contains three deep matcher implementation files:

- `examples/controlnet_construct/deep_adapter.py`
- `examples/controlnet_construct/deep_frontends.py`
- `examples/controlnet_construct/deep_matchers.py`

The current code comparison shows that the ControlNet copies are behaviorally
the same as the `examples/image_match` modules, with only file-header metadata
differences in two files. Existing tests and callers still import the
`controlnet_construct.deep_*` paths, so removing the files would create
unnecessary compatibility risk.

## Goal

Convert the three `controlnet_construct.deep_*` modules into thin compatibility
wrappers that re-export the corresponding `image_match.deep_*` APIs. This keeps
old import paths working while making `examples/image_match` the single runtime
implementation owner.

## Non-Goals

This step must not change matcher behavior or expand supported deep-learning
capabilities.

Specifically, it will not:

- Change `MATCHER_EXTRACTOR_REQUIREMENTS`.
- Add runtime support for DISK, ALIKED, or DoGHardNet.
- Change LoFTR checkpoint handling.
- Modify `run-lightglue.py`, `run-loftr.py`, or sweep scripts.
- Change manifest, `.npz`, `.key`, or ControlNet output formats.
- Remove the old `controlnet_construct.deep_*` import paths.

## Proposed Approach

Each compatibility module should import public symbols from the matching
`image_match` module and expose an explicit `__all__` list for the API that
existing tests and callers use.

The intended mapping is:

- `controlnet_construct.deep_adapter` -> `image_match.deep_adapter`
- `controlnet_construct.deep_frontends` -> `image_match.deep_frontends`
- `controlnet_construct.deep_matchers` -> `image_match.deep_matchers`

The wrappers should remain small and should contain no matching, frontend, or
device-selection implementation logic. Any future runtime behavior changes
should happen under `examples/image_match`.

## Compatibility Requirements

Existing imports through `controlnet_construct.deep_*` must continue to work for
the classes, functions, and exceptions that current tests use.

The wrapper modules should preserve these names at minimum:

- `DeepMatcherAdapter`
- `DeepDependencyError`
- `DeepFrontendError`
- `LoFTRFrontend`
- `SuperPointFrontend`
- `normalize_deep_method`
- `resolve_torch_device`
- `DeepMatchResult`
- `DeepMatcherError`
- `_default_feature_extractor_for_matcher`
- `build_deep_matcher`

Private helper re-exporting is acceptable where tests already rely on those
names. The wrapper step should avoid broad behavior refactoring; any API cleanup
belongs in a separate design and implementation step.

## Testing

The first verification target is the focused deep-match set from the handoff
notes:

```bash
python -m unittest \
  tests.unitTest.test_deep_match_config \
  tests.unitTest.deep_match_config_rehydration_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test
```

Because current tests also cover the old ControlNet import paths, run the
ControlNet matching test module or a narrowed subset that includes the
`controlnet_construct.deep_*` tests:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Run the smoke import before broader testing:

```bash
python tests/smoke_import.py
```

## Implementation Boundary

This is one small programming step. Stop after wrapper conversion and tests.
Do not start Phase 2 experiment-script alignment or Phase 3 runtime expansion in
the same change.
