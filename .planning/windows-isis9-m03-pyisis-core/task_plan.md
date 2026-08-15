# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Task Plan: Build and test isis_pybind._isis_core

## Goal

Complete milestone `windows-isis9-m03-pyisis-core` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-15-windows-isis9-pyisis-build-design.md#milestones`
- `ports/windows/README.md#stage-2-pyisis`
- `ports/windows/pyisis/README.md`

## Dependencies

- `windows-isis9-m02-isis-prefix`

## Completion Gate

The CPython 3.12 Windows extension builds against the verified ISIS 9.0.0 prefix, imports in a fresh process, and passes the Windows basic test set.

## Next Step

None — milestone complete.

## Current Phase

Phase 1

## Phases

### Phase 1: Milestone execution

- [x] Produce and verify the declared milestone evidence
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Prerequisite check reported `conda or mamba` missing | 1 | Added the verified base Conda Scripts path; the second preflight passed. |
| Planning-file patch context was stale after configure | 1 | Re-read all three M3 planning files and applied an exact-context update; no partial write occurred. |
| Milestone verification rejected a multiline Next Step while registry status was `in_progress` | 1 | Collapsed the completion-close action to one plain-text line before rerunning verification. |
