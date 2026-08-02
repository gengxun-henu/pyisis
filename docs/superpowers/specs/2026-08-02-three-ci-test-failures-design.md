# Three CI Test Failures Fix Design

Date: 2026-08-02

## Goal

Restore the full unit-test gate after the self-hosted runner exposed three
repository inconsistencies. The fix must not change the supported runtime API,
ControlNet matching behavior, or release packaging.

## Scope

1. Align the stale ControlNet pipeline assertion with the established
   `balanced` profile default of `bf`.
2. Restore a concise Chinese README section describing the supported deep-match
   `direct / export / import` workflows and linking the manifest and preset
   resources required by the documentation smoke test.
3. Make the optional-runtime-discovery unit test explicitly hide
   `isis_pybind._isis_core`, so its expected import boundary is deterministic
   whether or not CI has already built the extension.

## Design

The ControlNet fix changes only the outdated test expectation; production
profiles already consistently select `bf`. The README fix restores useful user
documentation rather than weakening the documentation test. The runtime fix
uses a temporary `sys.meta_path` finder inside the test to raise
`ModuleNotFoundError` specifically for `isis_pybind._isis_core`. This preserves
the original assertion that runtime discovery errors are ignored before normal
core-module resolution continues, while preventing a built extension from
changing the test result.

Test-file metadata will be updated according to repository conventions. No
binding source, packaging metadata, workflow, or public API will change.

## Validation

Run the three previously failing tests first, then their complete unit-test
modules, `tests/smoke_import.py`, and finally the full `tests/unitTest` discovery
suite using the `asp360_new` conda environment with `PYTHONPATH` and mock
`ISISDATA` configured as documented in `AGENTS.md`.

## Success Criteria

- All three formerly failing tests pass in a checkout with a built extension.
- Related unit modules and smoke import pass.
- The full unit-test suite has no failures attributable to these changes.
- The PR contains only the design/plan and the three scoped fixes.
