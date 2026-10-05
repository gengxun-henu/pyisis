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

## M39 Windows native APP validation (2026-10-05)

The GitHub-hosted `windows-isis-apps.yml` run `37260728860` passed on `windows-2022`. It built and installed the ISIS 10.0.0 allowlisted APP batch, smoke-tested all 150 configured applications, and passed the csv2table native behavior matrix (`3 passed, 0 failed, 0 skipped`). The run uploaded `windows-isis10-app-batch-smoke-logs` and `csv2table-native-app-isis10-windows`; both artifacts were unexpired when recorded.

## M40 self-hosted runner status (2026-10-05)

Sanity run `37266087196` still fails before checkout on the self-hosted pyisis runner. The workflow can detect the stale checkout, but the runner account cannot remove files under `/opt/actions-runner-pyisis/_work/pyisis/pyisis` because of host-level permissions. A host administrator must repair ownership/permissions or recreate the runner workspace before self-hosted validation can resume; GitHub-hosted M36/M38/M39 validation remains unaffected.

## M41 post-release regression audit (2026-10-05)

Both configured prereleases remain present and version-isolated. `v1.3.0rc3-isis9.0.0` exposes Linux/Windows CPython 3.12 wheelhouses; `v1.4.0rc3-isis10.0.0` exposes Linux/Windows CPython 3.13 wheelhouses. Each release is non-draft, marked prerelease, and has a two-entry `SHA256SUMS.txt` with valid SHA-256 records. The release manifests still point to their matching tags and retain prerelease mode.
