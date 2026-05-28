# Step1 Spiced Isis2std Design

## Goal

Extend `examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh`
with a dedicated pre-`cam2map` TIFF export stage for the current working cube.
The new stage should let operators export a quick-look TIFF from the same cube
that downstream Step1 processing is using, whether that cube is the original
`<base>.cub` or `REDUCED_<base>.cub`.

## Scope

In scope:

- Add a new Step1 stage named `isis2std-spiced`.
- Place that stage after `spiceinit` and before `cam2map` in the canonical
  stage order.
- Make the stage follow the current working cube:
  - without `--use-reduce`: `<base>.cub -> <base>.tif`
  - with `--use-reduce`: `REDUCED_<base>.cub -> REDUCED_<base>.tif`
- Preserve the existing `isis2std` stage as the DOM export step:
  `dom_<working_base>.cub -> dom_8bpp<working_base>.tif`.
- Extend `--step`, `--skip-step`, and `--resume-from` to understand the new
  stage.
- Update focused unit tests and the two Step1 usage documents.

Out of scope:

- Changing the semantics of the existing DOM `isis2std` stage.
- Requiring `--include-spiceinit` as a hard validation precondition for the new
  export stage.
- Adding new list files or downstream consumers for the generated TIFF.
- Changing how `append-lists` or `cleanup` behave.

## Selected Design

Use a dedicated stage name instead of overloading the existing `isis2std`
meaning.

Preferred stage model:

- `isis2std-spiced`: export the current working cube to TIFF before `cam2map`
- `isis2std`: export the map-projected DOM cube to TIFF after `cam2map`

This is preferred over a flag-only design or a dual-output `isis2std` stage
because it keeps the CLI stage model explicit and lets resume/skip semantics
stay mechanically consistent.

## Stage Order

The canonical Step1 stage order should become:

- `init-lists`
- `lronac2isis`
- `reduce`
- `lronaccal`
- `lronacecho`
- `spiceinit`
- `isis2std-spiced`
- `cam2map`
- `isis2std`
- `append-lists`
- `cleanup`

This ordering ensures that:

- `--resume-from spiceinit` includes the new TIFF export.
- `--resume-from cam2map` skips the new TIFF export.
- `--step all` emits both the quick-look TIFF export and the DOM TIFF export in
  a stable order.

## Command Generation

The new stage should emit one command per input image with this form:

- `isis2std from=<working_cub> to=<working_base>.tif format=tiff minpercent=0.1 maxpercent=99.9`

Where:

- `<working_cub>` is the same cube selected for `lronaccal`, `lronacecho`,
  `spiceinit`, and `cam2map`
- `<working_base>` is:
  - `<base>` without `--use-reduce`
  - `REDUCED_<base>` with `--use-reduce`

Examples:

- original chain:
  `isis2std from=M1389689680LE.cub to=M1389689680LE.tif format=tiff minpercent=0.1 maxpercent=99.9`
- reduced chain:
  `isis2std from=REDUCED_M1389689680LE.cub to=REDUCED_M1389689680LE.tif format=tiff minpercent=0.1 maxpercent=99.9`

The existing DOM export command remains unchanged:

- `isis2std from=dom_<working_base>.cub to=dom_8bpp<working_base>.tif format=tiff minpercent=0.1 maxpercent=99.9`

## CLI Semantics

### `--step`

Add `isis2std-spiced` to the supported step names.

Expected behavior:

- `--step isis2std-spiced` emits only the working-cube TIFF export.
- `--step isis2std` emits only the DOM TIFF export.
- `--step all` emits both exports.

### `--skip-step`

Add `isis2std-spiced` to the valid skip list.

Example:

- `--skip-step isis2std-spiced` should suppress only the pre-`cam2map` TIFF
  export while keeping `cam2map` and DOM `isis2std` eligible.

### `--resume-from`

Add `isis2std-spiced` into the canonical resume order.

Examples:

- `--resume-from spiceinit` should still emit:
  - `spiceinit`
  - `isis2std-spiced`
  - `cam2map`
  - `isis2std`
- `--resume-from cam2map` should not emit `isis2std-spiced`.

## Validation Boundary

The wrapper should continue behaving as a command generator rather than an
execution validator.

Therefore, the design does not add a hard check that `spiceinit` must be
explicitly emitted whenever `isis2std-spiced` is requested. The new stage is
positioned after `spiceinit` in the stage model, but operators may still use it
when SPICE has already been prepared outside the generated command file.

## Documentation Updates

Update these files:

- `examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh`
- `examples/controlnet_construct/usage.md`
- `examples/controlnet_construct/recommended_batch_templates.md`

Documentation should clearly distinguish:

- `isis2std-spiced` = working cube TIFF export before `cam2map`
- `isis2std` = DOM TIFF export after `cam2map`

At least one example should show:

- `--step isis2std-spiced`
- a `--resume-from spiceinit` flow that includes the new stage

## Testing

Add focused unit coverage in
`tests/unitTest/controlnet_construct_pipeline_unit_test.py` for:

- direct `--step isis2std-spiced` command generation in both original and
  reduced modes
- resume ordering:
  - `--resume-from spiceinit` includes `isis2std-spiced`
  - `--resume-from cam2map` excludes `isis2std-spiced`
- docs/help discoverability for `isis2std-spiced`

The tests should remain lightweight and continue using synthetic `.IMG` files in
`temporary_directory()`.

## Acceptance Criteria

- Step1 supports a new `isis2std-spiced` stage.
- The new stage exports the current working cube to `<working_base>.tif`.
- The existing DOM `isis2std` stage keeps its current meaning and output names.
- `--step`, `--skip-step`, and `--resume-from` all recognize the new stage.
- `--resume-from spiceinit` includes the new stage; `--resume-from cam2map`
  skips it.
- Help text, usage docs, and batch templates mention the new stage.
- Focused tests cover command generation, resume behavior, and doc visibility.
