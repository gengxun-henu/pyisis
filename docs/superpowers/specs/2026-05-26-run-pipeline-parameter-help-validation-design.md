# Run Pipeline Parameter Help And Validation Design

## Goal

Harden the user-facing parameter surface of
`examples/controlnet_construct/run_pipeline_example.sh` without changing the
pipeline behavior. The wrapper already has a catalog, grouped output, parameter
profiles, and validation plumbing. This slice turns that into a stable contract
for the main DOM ControlNet pipeline wrapper.

The immediate result should be a clearer normal `--help`, a complete detailed
`--print-parameter-groups` view, and consistent validation behavior for CLI,
config, profile, and preset values.

## Scope

In scope:

- Improve only `examples/controlnet_construct/run_pipeline_example.sh` and the
  catalog/validation modules it already calls.
- Keep `examples/controlnet_construct/parameter_catalog.py` as the canonical
  source for groups, allowed values, defaults, config paths, and entry-point
  ownership.
- Keep `examples/controlnet_construct/parameter_validation.py` as the canonical
  source for merged-value validation and cross-field checks.
- Add or update focused wrapper regressions for help output, grouped catalog
  output, validate-only behavior, layered warnings, strict validation, and CLI
  conflicts.
- Preserve current default behavior and priority order unless an existing bug is
  found and explicitly covered by a regression test.

Out of scope:

- Migrating the shell wrapper to Python.
- Changing matching, tiling, low-resolution offset, adaptive routing, deep-match,
  visualization, or ControlNet generation behavior.
- Extending this work to `run_ori_match_pipeline_example.sh`,
  `controlnet_stereopair.py`, or other Python entry points.
- Removing existing CLI flags or changing existing output file names.

## Current Context

`run_pipeline_example.sh` is the main end-to-end DOM ControlNet wrapper. It
parses user flags, reads selected defaults from `controlnet_config.example.json`,
applies optional match presets and parameter profiles, validates the effective
parameter set, and forwards values to:

- `examples/controlnet_construct/image_overlap.py`
- `examples/image_match/image_match.py`
- `examples/controlnet_construct/controlnet_stereopair.py from-dom-batch`
- `examples/controlnet_construct/controlnet_merge.py`
- optional post-merge control-measure tooling

The current code already includes:

- `--print-parameter-groups`
- `--validate-parameters-only`
- `--strict-parameter-validation`
- `--parameter-profile`
- `parameter_catalog.py`
- `parameter_validation.py`
- `print_parameter_catalog.py`

The remaining problem is consistency. The normal `--help` is still a long flat
surface; the wrapper's validation payload is manually assembled from many shell
variables; and catalog coverage can drift from the actual wrapper flags.

## User-Facing Help

The normal `--help` should stay familiar but become easier to scan.

Add a compact "Parameter groups" section near the top of the options section.
It should list the catalog groups in order:

- `inputs`
- `pipeline`
- `matching`
- `tile`
- `low_resolution`
- `adaptive_routing`
- `execution`
- `visualization`
- `controlnet`
- `reporting`

Each group should include one short description and a few representative flags.
The normal help should explicitly tell users to run:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh --print-parameter-groups
```

for the full catalog with allowed values, defaults, and config paths.

Do not replace the existing option list in this slice. The goal is to add an
index and make the detailed catalog discoverable, while keeping existing user
muscle memory intact.

## Detailed Catalog Output

`--print-parameter-groups` remains the detailed view. It should be backed by
`parameter_catalog.py`, not hand-written shell text.

For each supported `run_pipeline_example` parameter, the detailed output should
show:

- CLI flag or canonical name
- group
- short help text
- allowed values when known
- default when explicitly declared
- config path when a config field can provide the value

The text output is optimized for humans. The existing JSON format from
`print_parameter_catalog.py --format json` remains the machine-readable view.

## Validation Model

Validation uses layered sources:

1. profile values
2. config values
3. preset values
4. explicit CLI values

The effective value is the highest-priority non-empty value. The validator must
also keep provenance so warnings and errors can distinguish explicit CLI input
from lower-priority defaults.

The selected strategy is "layered first":

- Explicit CLI conflicts are errors by default.
- Config, preset, or profile values that are valid but inactive in the current
  mode are warnings by default.
- `--strict-parameter-validation` promotes warnings to errors.
- Clearly illegal values are always errors, regardless of source.

Examples of default errors:

- `--match-preset-path` combined with explicit `--matcher-method`.
- `--match-preset-path` combined with explicit `--deep-match-config-path`.
- deep matcher selected without a required deep match config path.
- unsupported choice values such as unknown matcher methods or invalid
  visualization modes.
- invalid numeric ranges such as negative worker counts or invalid probability
  values.
- `--post-merge-control-measure` with `--skip-final-merge`.

Examples of default warnings:

- low-resolution parameters supplied by config/profile while low-resolution
  offset estimation is disabled.
- GPU batch parameters supplied by config/profile while GPU mode is disabled.
- deep-match manifest paths supplied while `deep_match_mode` is `direct`.
- preview-cache parameters supplied while visualization mode uses the full
  source image.

If the same inactive-setting situation comes from an explicit CLI flag, it
should become an error in this slice when the wrapper can reliably identify that
source.

## Validate-Only Behavior

`--validate-parameters-only` should run the same resolution and validation path
that a real pipeline run uses, then exit before executing pipeline stages.

The output should include a concise effective-parameter summary for the wrapper
operator. It should include at least:

- work/config/list paths
- selected parameter profile
- matcher method
- worker count
- valid-pixel threshold
- invalid-pixel radius
- low-resolution enablement and key gates
- visualization mode
- strict validation state

Warnings should go to stderr through `print_parameter_catalog.py`; errors should
return a nonzero exit status and stop before any pipeline stage.

## Catalog Coverage Checks

The catalog must cover every high-risk `run_pipeline_example.sh` flag that
affects matching, routing, execution, visualization, validation, or ControlNet
merge behavior.

Coverage does not mean every possible path-like value needs a complicated rule.
The first hardening pass should prioritize:

- allowed values
- numeric type and range checks
- mode dependencies
- mutually exclusive options
- source provenance
- config path documentation

For low-risk free-form strings and output paths, catalog presence and help text
are enough unless the wrapper already enforces a rule.

## Implementation Boundaries

`run_pipeline_example.sh` remains responsible for shell parsing, path resolution,
stage orchestration, and forwarding commands.

`parameter_catalog.py` owns the declarative parameter list. It should not import
heavy runtime dependencies or open cubes.

`parameter_validation.py` owns value normalization, allowed-value checks,
numeric range checks, cross-field rules, and inactive-parameter warnings.

`print_parameter_catalog.py` owns rendering and the validation CLI used by the
wrapper. It must keep `examples` at the front of `sys.path` when run as a script
so imports resolve to the package modules rather than a local name collision.

## Testing

Add or update focused tests in existing unit-test files rather than adding a
large end-to-end data dependency.

Required coverage:

- `run_pipeline_example.sh --help` shows the compact group index and the
  `--print-parameter-groups` hint.
- `run_pipeline_example.sh --print-parameter-groups` includes the expected group
  names and representative parameters.
- `run_pipeline_example.sh --validate-parameters-only` exits before pipeline
  execution and prints the effective summary.
- Explicit CLI conflict for preset plus matcher is an error.
- Config/profile inactive low-resolution or GPU options are warnings by
  default.
- `--strict-parameter-validation` promotes those warnings to errors.
- Catalog tests assert key flags are assigned to the expected groups and have
  expected allowed values.
- Validation tests assert source precedence and provenance-driven severity.

Verification commands for the implementation plan should include:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

If code changes touch `image_match.py` parsing or forwarding, also run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

## Acceptance Criteria

- Normal `--help` has a compact parameter-group index and still preserves the
  existing practical option references.
- Detailed grouped output comes from the catalog and includes allowed values,
  defaults, and config paths where available.
- Validate-only uses the same effective values that a real run would use.
- Explicit CLI conflicts fail before any pipeline stage.
- Inactive config/profile values warn by default and fail with strict validation.
- Focused unit tests cover help, catalog, validation, and wrapper behavior.
- The root checkout's unrelated `.gitignore` and `print.prt` changes remain
  untouched.
