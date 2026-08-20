# Task Plan: Post-M06 dual-version wheel revalidation (M08)

## Goal

Validate frozen current HEAD `07b87e389c09ad838b65dae3456927d66b289cd8` across Linux/Windows × ISIS 9/10 wheels without publishing a release.

## Scope

- Execute only the approved workflow and collect its current-HEAD evidence.
- Stop at the first failed layer; do not make a repair without a new approved design.

## Dependencies

- M06 is complete.
- M07 reconciliation is recorded in `.planning/release-evidence-reconciliation-m07/`.

## Completion Gate

Four successful workflow lanes with retained hashes, install/import/test evidence, and no release publication.

## Next Step

Dispatch the non-publishing remote `wheels.yml` workflow at frozen SHA `07b87e389c09ad838b65dae3456927d66b289cd8` after its branch ref is available remotely.

## Current Phase

Phase 1: Freeze inputs

## Phases

### Phase 1: Freeze inputs

- [x] Record exact HEAD and classified Git state.
- [x] Run workflow contract tests.
- [x] Record four-lane workflow-job mapping.
- **Status:** completed 2026-08-20

### Frozen workflow-job mapping

| Required lane | Committed `wheels.yml` job ID(s) |
|---|---|
| `linux-isis9` | `linux-cp312-build`, `linux-cp312-clean-install` |
| `linux-isis10-cp313` | `linux-isis10-cp313-build`, `linux-isis10-cp313-clean-install` |
| `windows-cp312` | `windows-cp312` |
| `windows-isis10-cp313` | `windows-isis10-cp313` |

### Phase 2: Dispatch and monitor

- [ ] Push the frozen commit normally and dispatch `wheels.yml` at that ref.
- [ ] Record one workflow run and its job outcomes.
- **Status:** pending

### Phase 3: Evidence and outcome

- [ ] Retain four-lane hashes and report a non-publishing readiness decision.
- **Status:** pending

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| None | 0 | Not applicable. |
