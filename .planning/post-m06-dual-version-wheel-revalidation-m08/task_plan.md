# Task Plan: Post-M06 dual-version wheel revalidation (M08)

## Goal

Validate the current HEAD across Linux/Windows × ISIS 9/10 wheels without publishing a release.

## Scope

- Execute only the approved workflow and collect its current-HEAD evidence.
- Stop at the first failed layer; do not make a repair without a new approved design.

## Dependencies

- M06 is complete.
- M07 reconciliation is recorded in `.planning/release-evidence-reconciliation-m07/`.

## Completion Gate

Four successful workflow lanes with retained hashes, install/import/test evidence, and no release publication.

## Next Step

Freeze the current Git state and run the workflow-contract tests.

## Current Phase

Phase 1: Freeze inputs

## Phases

### Phase 1: Freeze inputs

- [ ] Record exact HEAD and classified Git state.
- [ ] Run workflow contract tests.
- **Status:** in_progress

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
