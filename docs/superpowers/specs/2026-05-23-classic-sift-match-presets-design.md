# Classic SIFT Match Presets Design

## Goal

Add reusable ControlNet match presets for the original OpenCV SIFT matching path,
while keeping the user-facing configuration shape close to the existing learning
matcher presets such as `lightglue_official_superpoint.json`.

The new presets must make these two routes clearly distinct:

- `classic_sift_*`: OpenCV SIFT descriptor extraction plus BF or FLANN matching.
- `lightglue_official_sift.json`: `lightglue.SIFT` extraction plus
  `lightglue.LightGlue` matching.

## Current Context

The deep-learning presets under `examples/controlnet_construct/presets/` use a
compact structure:

```json
{
  "feature_extractor": {
    "method": "superpoint",
    "max_features": 4096
  },
  "matcher": {
    "method": "lightglue",
    "backend": "official"
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32"
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

Classic SIFT settings currently live under `ImageMatch` in
`controlnet_config.example.json` and are forwarded through
`run_pipeline_example.sh` into `examples/image_match/image_match.py`.

The runtime already supports the classic matcher methods `bf` and `flann`.
FLANN uses OpenCV's KD-tree matcher path; BF uses `cv2.BFMatcher` with L2
descriptor distance. Both share the same SIFT detector parameters and ratio
test.

## Proposed Approach

Introduce a neutral match preset concept that can represent both learning
matchers and classic SIFT matchers.

The first implementation should add these shared presets:

- `examples/controlnet_construct/presets/classic_sift_flann.json`
- `examples/controlnet_construct/presets/classic_sift_bf.json`

Each file should use the same top-level shape as the learning presets:

```json
{
  "feature_extractor": {
    "method": "classic_sift",
    "max_features": 1000,
    "octave_layers": 3,
    "contrast_threshold": 0.04,
    "edge_threshold": 10.0,
    "sigma": 1.6
  },
  "matcher": {
    "method": "flann",
    "ratio_test": 0.75
  }
}
```

The BF preset should differ only in `matcher.method`.

This keeps the ControlNet configuration model consistent: users select a
feature extraction method and a matching method by choosing a preset, regardless
of whether the implementation is classic OpenCV or learning-based.

## Interface

Add a neutral preset entry point:

- CLI: `--match-preset-path PATH`
- Config JSON: `ImageMatch.match_preset_path`

Existing interfaces remain valid:

- `ImageMatch.matcher_method`
- `ImageMatch.deep_matcher_config_path`
- `--matcher-method`
- `--deep-match-config-path`

The wrapper should use this precedence:

1. `--match-preset-path`, when provided on the CLI.
2. `ImageMatch.match_preset_path`, when present in config JSON.
3. Existing CLI flags such as `--matcher-method` and
   `--deep-match-config-path`.
4. Existing `ImageMatch.matcher_method` and `ImageMatch.deep_matcher_config_path`.
5. Existing script defaults.

`--match-preset-path` should be treated as a complete matcher selection. If it
is combined with old matcher-selection CLI flags such as `--matcher-method` or
`--deep-match-config-path`, the wrapper should fail with a clear error instead
of guessing precedence. In config JSON, `ImageMatch.match_preset_path` should
take precedence over legacy `ImageMatch.matcher_method` and
`ImageMatch.deep_matcher_config_path` fields so older config templates can be
upgraded incrementally without deleting every legacy key immediately.

When `--match-preset-path` or `ImageMatch.match_preset_path` points at a
learning preset, the wrapper should derive and forward the current deep matcher
arguments. When it points at a classic SIFT preset, the wrapper should derive and
forward the existing classic SIFT arguments.

## Classic SIFT Mapping

For `feature_extractor.method == "classic_sift"`:

- `feature_extractor.max_features` maps to `ImageMatch.max_features`.
- `feature_extractor.octave_layers` maps to `ImageMatch.sift_octave_layers`.
- `feature_extractor.contrast_threshold` maps to
  `ImageMatch.sift_contrast_threshold`.
- `feature_extractor.edge_threshold` maps to `ImageMatch.sift_edge_threshold`.
- `feature_extractor.sigma` maps to `ImageMatch.sift_sigma`.
- `matcher.method` maps to `ImageMatch.matcher_method` and must be `bf` or
  `flann`.
- `matcher.ratio_test` maps to `ImageMatch.ratio_test`.

Classic SIFT presets must not trigger deep matcher export, import, or direct
deep-learning execution.

## Deep Matcher Mapping

For learning presets:

- `matcher.method` must remain one of the existing deep matcher methods:
  `superglue`, `lightglue`, or `loftr`.
- The preset file continues to be consumed by the existing deep matcher config
  layer.
- `run-lightglue.py` and `run-loftr.py` stay unchanged. The ControlNet wrapper
  should align with their validated option semantics instead of modifying them.

This preserves the already validated learning-method entry points and only adds
a common ControlNet selection surface.

## Validation

Classic SIFT preset validation should fail fast when:

- `feature_extractor.method` is not `classic_sift`.
- `matcher.method` is not `bf` or `flann`.
- `matcher.ratio_test` is not in `(0, 1]`.
- `feature_extractor.max_features` or `feature_extractor.octave_layers` is not a
  positive integer.
- `feature_extractor.contrast_threshold`, `feature_extractor.edge_threshold`, or
  `feature_extractor.sigma` is not a positive number.
- Classic SIFT presets include deep-only fields such as `device`, `fallback`, or
  deep matcher backend options.

Learning preset validation should continue to use the existing deep matcher
validation rules.

## Documentation

Update `examples/controlnet_construct/PRESETS_README.md` with a separate
Classic SIFT section.

The documentation should state:

- `classic_sift_flann.json` uses OpenCV SIFT descriptors plus FLANN matching.
- `classic_sift_bf.json` uses OpenCV SIFT descriptors plus BF matching.
- `lightglue_official_sift.json` is not classic SIFT; it uses `lightglue.SIFT`
  plus `lightglue.LightGlue`.
- Classic SIFT runs in the normal `asp360_new` environment and does not require
  the separate `deep-learning` conda environment.
- Learning presets keep the existing `direct`, `export`, and `import` behavior.

## Tests

Implementation should add focused tests for:

- Loading and validating `classic_sift_flann.json`.
- Loading and validating `classic_sift_bf.json`.
- Rejecting invalid classic SIFT matcher methods.
- Rejecting invalid SIFT detector and ratio-test values.
- Wrapper forwarding from `ImageMatch.match_preset_path` for classic SIFT.
- CLI `--match-preset-path` taking precedence over config values.
- Classic SIFT presets not requiring `deep_matcher_config_path`.
- Deep presets still forwarding through the existing deep matcher path when used
  through `match_preset_path`.

## Non-Goals

This change should not:

- Modify `run-lightglue.py` or `run-loftr.py`.
- Replace `deep_matcher_config_path` immediately.
- Remove existing `matcher_method` config support.
- Change the BF or FLANN matching algorithms.
- Add a deep-learning environment requirement for classic SIFT.
