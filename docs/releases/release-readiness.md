# PyISIS Release Readiness

Updated: 2026-10-04

This page is the current release gate for the ISIS 9/10 binary lines. It keeps
artifact identity and validation commands in one place; it does not create or
publish release assets.

## Candidate matrix

| ISIS | Python | Linux | Windows | Current state |
|---|---|---|---|---|
| 9.0.0 | CPython 3.12 | manylinux wheel and clean-install evidence available | passed in fallback run `37215760300` | matrix passed |
| 10.0.0 | CPython 3.13 | manylinux wheel and clean-install evidence available | passed in fallback run `37215760300` | matrix passed |

A stable dual-version release requires all four platform/version cells to pass
in the same release cycle. Run `37215760300` passed all four build cells and
all six Linux clean-install jobs. The formal GitHub Release step was skipped
because publication was disabled for this validation run.

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

## Current status

- The Windows ISIS 10 `mgs.dll` link gate passed in fallback run `37215760300`.
- The self-hosted runner remains unhealthy, but the matrix was verified on
  GitHub-hosted `windows-2022` and `ubuntu-24.04`/22.04/26.04 runners.
- Stable publication is still a separate action; this run intentionally left
  `publish_github_release=false`.

## Existing prereleases

The configured prerelease tags already exist and contain the expected assets:

- `v1.3.0rc3-isis9.0.0`: Linux wheelhouse, Windows wheelhouse, and `SHA256SUMS.txt`.
- `v1.4.0rc3-isis10.0.0`: Linux wheelhouse, Windows wheelhouse, and `SHA256SUMS.txt`.

The M38 publication step safely refused to overwrite the existing ISIS 9 tag.
