# PyISIS Release Readiness

Updated: 2026-10-04

This page is the current release gate for the ISIS 9/10 binary lines. It keeps
artifact identity and validation commands in one place; it does not create or
publish release assets.

## Candidate matrix

| ISIS | Python | Linux | Windows | Current state |
|---|---|---|---|---|
| 9.0.0 | CPython 3.12 | manylinux wheel and clean-install evidence available | historical wheel evidence available | ready for revalidation |
| 10.0.0 | CPython 3.13 | manylinux wheel and clean-install evidence available | blocked in `mgs.dll` link (`SpiceQL::strSclkToEt`) | blocked |

A stable dual-version release requires all four platform/version cells to pass
in the same release cycle. Local Linux smoke tests do not replace the Windows
cells.

## Artifact identity

Every retained wheelhouse and report should record:

- ISIS version and exact conda build;
- operating system, architecture, and Python ABI;
- wheel filename and SHA-256;
- runtime/dependency report filename and SHA-256;
- clean-install report filename and test command;
- source commit and workflow run ID.

Use the repository validators before retaining an artifact:

```bash
python -m unittest \
  tests.unitTest.windows_wheelhouse_validation_unit_test \
  tests.unitTest.linux_wheel_audit_unit_test \
  tests.unitTest.auditwheel_policy_unit_test \
  tests.unitTest.wheel_workflow_unit_test \
  tests.unitTest.packaging_tools_unit_test -q
```

For a Linux wheelhouse, run the build script from the matching conda
prefix and then generate the ABI report with
`tools/packaging/audit_linux_wheelhouse.py`. Keep the resulting report beside
the wheelhouse and include its hash in the release manifest.

## Installation boundary

The PyISIS wheelhouse contains Python bindings, runtime libraries, and minimal
ISISDATA needed for import/smoke checks. Native ISIS applications such as
`reduce`, `jigsaw`, and `qnet` are distributed separately.

## Current blockers

1. The Windows ISIS 10 prefix must link `mgs.dll` successfully. The current
   failure is an unresolved decorated `SpiceQL::strSclkToEt` symbol.
2. The self-hosted runner workspace must be repaired or recreated. Strict
   sanity run `37190432546` reported missing `HEAD` and stale submodule metadata.

Do not tag or publish a stable dual-version release until both blockers are
cleared and the four matrix cells pass together.
