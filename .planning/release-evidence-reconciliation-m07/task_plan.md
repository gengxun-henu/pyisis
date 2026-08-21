# Task Plan: Release evidence reconciliation (M07)

## Goal

Reconcile the durable records for the ISIS 9/10 Linux/Windows release matrix and determine whether a new Windows ISIS 10 wheel revalidation milestone is actually required.

## Scope

- Read and compare committed plans, release notes, workflow definitions, retained evidence, and local artifacts.
- Do not rebuild ISIS, wheels, or native APP artifacts during this audit.
- Do not reopen M06 or modify `.gitignore` or `print.prt`.

## Dependencies

- `windows-isis9-m06-native-app-implementation` is complete.
- Existing release evidence and historical Git commits are available for inspection.

## Completion Gate

Every four-matrix claim is classified as verified, historical-but-insufficient, absent, or contradictory; the legacy ISIS 10 expansion plan has a documented disposition; and exactly one concrete next step is recorded.

## Next Step

Start `post-m06-dual-version-wheel-revalidation-m08`: rebuild and validate the four wheel lanes at the current HEAD before any new release decision.

## Current Phase

Phase 1: Evidence inventory

## Phases

### Phase 1: Evidence inventory

- [x] Map every claimed release-matrix result to a committed report, artifact, workflow run, or retained hash.
- **Status:** complete

### Phase 2: Reconciliation and decision

- [x] Classify discrepancies and select the smallest justified follow-up milestone, if any.
- **Status:** complete

### Phase 3: Durable handoff

- [x] Record the conclusion, Git classification, and unique Next Step.
- **Status:** complete

## Decisions

| Decision | Rationale |
|---|---|
| Start with evidence reconciliation rather than rebuilding SpiceQL | The current source already contains the historical Windows export patch and downstream link probe, while newer records show an ISIS 10 Windows native-APP run passed. |
| Require a current-HEAD four-lane wheel revalidation before a new release decision | The existing ISIS 10 prerelease is verified but predates M06's Python/native-APP boundary changes. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| None | 0 | Not applicable. |
