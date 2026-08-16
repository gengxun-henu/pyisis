# Windows PyISIS ISIS 9 Wheelhouse Milestone

# Task Plan: Build and release-validate the Windows PyISIS wheelhouse

## Goal

Complete milestone `windows-isis9-m04-wheelhouse` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md`
- `docs/superpowers/plans/2026-08-16-windows-pyisis-wheelhouse.md`

## Dependencies

- None

## Completion Gate

The exact CPython 3.12 Windows three-wheel wheelhouse builds against the verified ISIS 9.0.0 prefix, has no unresolved runtime DLLs or APP payloads, installs without build-time runtime paths, passes focused/basic tests, and has reproducible SHA-256 reports.

## Next Step

Dispatch and review implementation-plan Task 1: structured clean-install evidence.

## Current Phase

Phase 1

## Phases

### Phase 1: Milestone execution

- [ ] Produce and verify the declared milestone evidence
- **Status:** in_progress

## Decisions Made

| Decision | Rationale |
|---|---|
| Archive the verified M01-M03 registry before initializing M04 | Preserves all prior lifecycle evidence while giving M04 a clean canonical registry compatible with the milestone manager. |
| Execute M04 in `.worktrees/m04-windows-pyisis-wheelhouse` | Isolates release work from unrelated repository-root state. |
| Reuse the verified ISIS 9 prefix through an ignored directory junction | Avoids duplicating a large build artifact while keeping its original verified bytes authoritative. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Old-milestone verification from the isolated worktree could not resolve ignored root artifacts and rejected paths escaping through the prefix junction | 1 | Verified and archived M01-M03 from the repository root, initialized the new M04 registry there, then cherry-picked the lifecycle commit into this worktree. |
| A combined PowerShell cleanup command was rejected by the command safety policy | 1 | Performed no deletion; moved the temporary pre-manager planning draft into the ignored SDD workspace as a recoverable backup. |
