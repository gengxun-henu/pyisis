# ControlNet Parameter Catalog Design

## Goal

The ControlNet construction command line has grown into a long list of options
spread across shell wrappers and Python entry points. Add a shared parameter
catalog and validation layer so users can see parameters by group, get
consistent legal-value checks, and keep CLI overrides aligned with JSON config
and preset defaults.

This design keeps the existing pipeline behavior intact. It organizes and
validates the surface area before any later cleanup or wrapper rewrite.

## Current Context

The existing end-to-end DOM pipeline is driven by
`examples/controlnet_construct/run_pipeline_example.sh`. It forwards options to
`examples/image_match/image_match.py`, `controlnet_stereopair.py from-dom-batch`,
`controlnet_merge.py`, and optional post-merge tooling.

Several important validation rules already exist, but they are split across
multiple files:

- `examples/image_match/image_match.py` validates many image-match ranges and
  allowed values, including matcher names, low-resolution options, worker
  counts, visualization options, and deep-match modes.
- `examples/controlnet_construct/deep_match_config.py` validates deep matcher
  preset JSON files and matcher/extractor compatibility.
- `examples/controlnet_construct/controlnet_stereopair.py` validates a subset
  of from-DOM and from-ORI wrapper options.
- `run_pipeline_example.sh` contains separate bash parsing, fallback, and
  combination checks.

The result is hard to read and easy to drift. A parameter added to one layer can
miss help grouping, config mapping, wrapper forwarding, or validation in another
layer.

## Scope

In scope:

- Add a shared Python catalog for ControlNet pipeline parameters.
- Add a shared Python validation/normalization layer.
- Keep complete CLI support and config-file support in parallel.
- Provide parameter grouping output for users and documentation.
- Add `--validate-parameters-only` for fast config/CLI validation.
- Add `--strict-parameter-validation` to promote warnings to errors.
- Connect the shell wrapper first, then align the Python CLIs.
- Cover existing high-risk groups first: matcher/deep/preset,
  low-resolution, adaptive routing, tile options, execution, visualization, and
  deep-match mode.

Out of scope:

- Rewriting `run_pipeline_example.sh` as Python.
- Changing matching algorithms, ControlNet generation, output paths, or default
  behavior.
- Removing existing CLI flags.
- Inventing new sampling policy or workflow policy.
- Enforcing new ranges on legacy fields whose valid range is not yet clear.

## Proposed Modules

Add `examples/controlnet_construct/parameter_catalog.py`.

This module declares the user-facing parameter catalog. Each parameter record
should include:

- canonical field name
- CLI flag name
- config field name, when applicable
- group name
- type
- default source
- allowed values or numeric range, when known
- entry points that support it
- active/inactive dependency rules
- conflict rules
- short help text

Add `examples/controlnet_construct/parameter_validation.py`.

This module merges and validates values for a named entry point. It accepts the
entry point name, explicit CLI values, config defaults, preset-expanded values,
and validation mode. It returns normalized values plus structured warnings and
errors.

Add `examples/controlnet_construct/print_parameter_catalog.py`.

This small CLI is used by shell wrappers and docs. It should support:

- printing grouped parameter help
- printing a JSON summary of the catalog
- validating a JSON payload of parsed values
- returning shell assignments for normalized values when called by
  `run_pipeline_example.sh`

The module boundaries are intentionally small. The catalog describes what is
valid; the validator decides whether a concrete invocation is valid; entry
points still own orchestration.

## Parameter Groups

The first catalog pass should group existing options as follows.

`inputs`:

- `work_dir`
- `original_list`
- `dom_list`
- `config`
- `python`

`pipeline`:

- `deep_match_mode`
- `deep_match_temp_root_dir`
- `deep_match_manifest_dir`
- `deep_match_manifest_summary`
- `skip_final_merge`
- `post_merge_control_measure`
- `post_merge_output`
- `post_merge_decimals`

`matching`:

- `matcher_method`
- `match_preset_path`
- `deep_match_config_path`
- `ratio_test`
- `max_features`
- `sift_octave_layers`
- `sift_contrast_threshold`
- `sift_edge_threshold`
- `sift_sigma`

`tile`:

- `max_image_dimension`
- `sub_block_size_x`
- `sub_block_size_y`
- `overlap_size_x`
- `overlap_size_y`
- `enable_tile_validity_prefilter`
- `tile_validity_cache_dir`
- `tile_validity_cell_width`
- `tile_validity_cell_height`

`low_resolution`:

- `enable_low_resolution_offset_estimation`
- `low_resolution_level`
- `low_resolution_matching_target_long_edge`
- `low_resolution_trim_fraction_each_side`
- `low_resolution_max_mean_reprojection_error_pixels`
- `low_resolution_min_retained_match_count`
- `low_resolution_max_mean_projected_offset_meters`
- `left_low_resolution_dom`
- `right_low_resolution_dom`

`adaptive_routing`:

- `enable_adaptive_routing`
- `adaptive_routing_profile`
- `adaptive_routing_deep_presets`

`execution`:

- `use_parallel_cpu`
- `num_worker_parallel_cpu`
- `use_gpu`
- `gpu_batch_size`
- `gpu_dynamic_batch`
- `gpu_min_batch_size`
- `gpu_max_batch_size`

`visualization`:

- `write_match_visualization`
- `match_visualization_output_path`
- `match_visualization_output_dir`
- `match_visualization_scale`
- `visualization_mode`
- `memory_profile`
- `visualization_target_long_edge`
- `max_preview_pixels`
- `preview_crop_margin_pixels`
- `preview_cache_dir`
- `preview_cache_source`
- `preview_force_regenerate`
- `preview_level`

`controlnet`:

- `pair_id`
- `pair_id_prefix`
- `pair_id_start`
- `network_id`
- `description`
- `binary`
- `merged_net`
- `merge_script`
- `merge_log`
- `pair_list`
- `cnetmerge`

`reporting`:

- `metadata_output`
- `result_output`
- `report_path`
- `report_dir`
- `timing_json`
- `omit_tile_details`
- `omit_detail_records`
- `log_level`

These groups affect help, docs, validation messages, and future generated
summaries. They do not change command semantics.

## Value Precedence

Use one merge rule everywhere:

```text
explicit CLI value > preset-expanded value > config value > entrypoint default
```

The validator should keep provenance for every normalized value. Error and
warning messages should name the source when useful, for example:

```text
matcher_method=lightglue came from config ImageMatch.matcher_method, but no
deep_match_config_path was provided.
```

This matters because users often combine config JSON with a small number of CLI
overrides. The system should explain the effective values, not only the raw CLI.

## Validation Policy

Default mode is layered validation.

Hard errors:

- unknown matcher method, adaptive-routing profile, visualization mode,
  memory profile, preview-cache source, or deep-match mode
- numeric range violations already enforced by existing Python helpers
- `match_preset_path` explicitly combined with `matcher_method`
- `match_preset_path` explicitly combined with `deep_match_config_path`
- deep matcher selected without a deep matcher config or preset-resolved config
- deep matcher config path missing or failing `load_deep_match_config`
- `deep_match_mode=import` without `deep_match_manifest_dir` or equivalent
  manifest source
- GPU minimum batch size greater than GPU maximum batch size
- paired options where only one side is provided, such as left/right
  low-resolution DOM inputs
- `post_merge_control_measure` combined with `skip_final_merge`

Warnings:

- low-resolution thresholds are set while
  `enable_low_resolution_offset_estimation` is false
- visualization options that only affect reduced previews are set while the
  effective visualization mode is full
- GPU batch options are set while GPU execution is disabled
- `num_worker_parallel_cpu` is set while CPU parallelism is disabled
- deep-match export/import paths are set while `deep_match_mode=direct`
- post-merge output or decimals are set while post-merge is disabled

`--strict-parameter-validation` promotes warnings to errors. This gives CI and
fixed production runs a stricter mode without making exploratory command lines
too brittle.

## Entrypoint Integration

### `run_pipeline_example.sh`

Integrate the shell wrapper first because it has the largest user-facing
surface.

The shell wrapper should still parse CLI flags and preserve current defaults.
After reading config and preset defaults, it should call the Python validation
entry point with a JSON payload containing:

- entry point name: `run_pipeline_example`
- explicit CLI values
- config defaults
- preset values, if a preset was selected
- strict mode

The Python validator should return normalized shell assignments plus structured
warnings. The shell wrapper then forwards only normalized values to downstream
commands.

Add wrapper flags:

- `--print-parameter-groups`
- `--validate-parameters-only`
- `--strict-parameter-validation`

`--print-parameter-groups` prints grouped help and exits. It should be backed by
the catalog, not by a second hand-written list in bash.

`--validate-parameters-only` resolves config defaults, applies presets, runs
validation, prints a compact effective-value summary, and exits before creating
pipeline artifacts or running matching work.

### `image_match.py`

Keep the existing argparse entry point. Move repeated type/range helpers toward
the shared validator incrementally. The first alignment should cover:

- matcher method
- deep-match mode
- adaptive-routing profile
- valid-pixel threshold
- invalid-pixel radius
- low-resolution values
- parallel worker count
- visualization values
- preview cache source

Existing direct unit tests should continue to pass. Error surfaces should remain
clean `argparse` or `SystemExit` failures, not tracebacks.

### `controlnet_stereopair.py`

Keep the subcommands and existing parser shape. Align shared options for:

- `from-ori-match`
- `from-dom`
- `from-dom-batch`

The first pass should cover matcher/adaptive/execution options for
`from-ori-match`, and RANSAC/visualization/reporting-related shared options for
`from-dom` and `from-dom-batch` where they overlap with the catalog.

## Testing

Add `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`.

Cover:

- required groups exist
- important fields have group, CLI name, entrypoint membership, and help text
- allowed values match runtime constants for matcher, deep-match mode, adaptive
  profile, visualization mode, memory profile, and preview cache source
- known numeric ranges match existing helper behavior
- config field mappings are present for ImageMatch-backed fields

Add `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`.

Cover:

- CLI/config/preset/default precedence
- deep matcher requires config
- match preset conflicts
- strict mode converts warnings to errors
- inactive low-resolution, GPU, parallel CPU, visualization, and deep-match
  fields produce warnings
- GPU min/max batch consistency
- paired low-resolution DOM path consistency
- deep-match import manifest requirement

Extend `tests/unitTest/controlnet_construct_pipeline_unit_test.py`.

Cover:

- `run_pipeline_example.sh --print-parameter-groups`
- `run_pipeline_example.sh --validate-parameters-only`
- shell wrapper reports warnings without failing by default
- shell wrapper fails on the same warning under strict validation
- shell wrapper still forwards current normalized values to image-match and
  controlnet stages

Extend existing Python CLI tests only where the shared validator changes the
source of validation. Do not expand unrelated end-to-end coverage.

## Documentation

Update `examples/controlnet_construct/PRESETS_README.md` or add a focused
parameter document near the pipeline wrappers after the catalog is connected.
The documentation should describe groups, config precedence, strict validation,
and common examples.

The catalog CLI should be able to generate a machine-readable summary so future
docs can be refreshed without manually auditing all argparse and bash entries.

## Rollout Plan

Phase 1: Add catalog and validation modules with tests only.

Phase 2: Connect `run_pipeline_example.sh` to the validator and add
`--print-parameter-groups`, `--validate-parameters-only`, and
`--strict-parameter-validation`.

Phase 3: Align `image_match.py` validation helpers with the shared layer while
preserving current parser behavior.

Phase 4: Align `controlnet_stereopair.py` shared options.

Phase 5: Update docs and examples after behavior is verified.

Each phase should be commit-sized and behavior-preserving unless a test
explicitly covers a new validation error or warning.

## Risks

The main risk is changing effective defaults while trying to centralize them.
Mitigation: preserve current defaults in tests before replacing any local helper
or shell fallback.

The second risk is making exploratory scripts too strict. Mitigation: default
warnings remain non-fatal, and strict mode is opt-in.

The third risk is over-modeling every legacy option before the design proves
useful. Mitigation: first catalog high-risk shared groups and allow descriptive
records for unclear legacy fields without adding new hard constraints.

## Success Criteria

- Users can inspect grouped ControlNet pipeline parameters from the command
  line.
- Users can validate a config plus CLI overrides without running the pipeline.
- The shell wrapper, image-match CLI, and ControlNet stereo-pair CLI share the
  same allowed values for overlapping parameters.
- Existing defaults and output paths remain unchanged.
- Invalid combinations produce clear messages before expensive processing
  begins.
- Unit tests cover both the catalog shape and the validation behavior.

## Implementation Note

The implementation plan is stored at
`docs/superpowers/plans/2026-05-23-controlnet-parameter-catalog.md`.
