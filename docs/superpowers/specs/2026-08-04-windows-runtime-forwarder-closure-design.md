# Windows Runtime Forwarder Closure Design

## Problem

The Windows runtime wheel staging pipeline computes a reduced DLL closure from
`dumpbin /DEPENDENTS`. PE export-forwarder targets do not appear in that list.
As a result, the ISIS 9 `v1.3.0rc2` Windows runtime wheel included the
`libblas.dll`, `libcblas.dll`, and `liblapack.dll` forwarder DLLs but omitted
their shared `openblas.dll` target. A clean CPython 3.12 installation therefore
failed while importing `isis_pybind._isis_core` with a generic DLL-not-found
error.

ISIS 9 and ISIS 10 use the same Windows runtime staging implementation, so the
fix must apply to both release lines even though the reproduced failure came
from the ISIS 9 wheelhouse.

## Scope

- Fix dependency-closure staging for both Windows runtime distributions:
  `usgs-pyisis-runtime-win64` and
  `usgs-pyisis-runtime-isis10-win64`.
- Add focused regression coverage before changing production code.
- Record the packaging failure and corrected closure contract in the runtime
  packaging documentation and both current release-candidate notes.
- Do not change package versions, rebuild wheels, or replace published release
  assets.

## Design

Add a focused helper to `tools/packaging/stage_runtime_win64.py` that runs
`dumpbin /EXPORTS` and extracts DLL names referenced by PE forwarder entries.
The parser will accept case-insensitive names matching the existing DLL-name
policy, exclude Windows system DLLs using the existing system filters, remove
duplicates while preserving discovery order, and return an empty tuple when
`dumpbin` cannot inspect a file.

The dependency-closure walk will combine normal imports from
`dumpbin /DEPENDENTS` with forwarded-export targets from `dumpbin /EXPORTS`.
Every resolved target will follow the existing copy and queue behavior, so a
forwarded target such as `openblas.dll` is copied into its original relative
location and its own dependencies are traversed recursively. Pattern-copy mode
will remain unchanged.

This generic parsing approach is preferred over hard-coding `openblas.dll` or
copying the complete dependency prefix. It fixes the PE dependency model rather
than one library name and preserves the intentionally small runtime wheel.

## Tests

Extend `tests/unitTest/runtime_wheel_script_unit_test.py` using its existing
temporary-prefix and mocked-`dumpbin` patterns.

Regression coverage will verify:

1. the export parser recognizes an `openblas.dll` forwarder target, deduplicates
   repeated symbols, and ignores system DLL targets;
2. closure staging copies a forwarded target even when it is absent from the
   ordinary import list;
3. the copied target participates in recursive dependency traversal;
4. the shared staging behavior works independently of the ISIS 9 or ISIS 10
   runtime distribution name;
5. existing ordinary dependency-closure behavior remains unchanged.

The focused unit module will be run first, followed by the repository's full
Python unit-test discovery if the focused suite passes.

## Documentation

Update `packaging/runtime-win64/README.md` to state that the staged closure
includes both normal PE imports and forwarded-export targets. Add concise notes
to the ISIS 9 `v1.3.0rc2` and ISIS 10 `v1.4.0rc2` release documents explaining
the shared staging defect and that the source-level fix does not replace the
already published assets.

## Success Criteria

- A regression test fails against the current implementation because
  `openblas.dll` is not copied.
- The minimal implementation makes the new tests pass without changing pattern
  mode or hard-coding OpenBLAS.
- Existing runtime-wheel staging tests pass.
- Full Python unit-test discovery passes, or any unrelated baseline failure is
  reported with evidence.
- The diff is limited to the Windows staging script, its unit tests, and the
  agreed documentation.
