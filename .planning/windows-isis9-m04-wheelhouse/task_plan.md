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

Execute and review implementation-plan Task 4: isolated wheel install, final validation reports, and narrow cleanup.

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
| Initial SDD implementer-template lookup used the nonexistent name `task-implementer-prompt.md` | 1 | Listed the skill directory and resolved the correct template as `implementer-prompt.md`; task brief generation still succeeded. |
| Task 2 plan named nonexistent adjacent test `test_windows_dependency_closure_fails_on_unresolved_non_system_dll` | 1 | Ran the repository's existing semantic equivalent `test_stage_runtime_closure_reports_unresolved_dependency`; validator plus adjacent coverage passed 6/6. |
| Task 3 prescribed the entire cross-platform runtime staging test module under Windows; 4 Linux staging tests errored because `ldd`/`readelf` are unavailable | 1 | Kept the failure evidence, excluded only the four platform-inapplicable Linux cases, and used all six Windows runtime staging tests plus the remaining prescribed M04 modules/methods as the pre-build gate. |
| First Task 3 build failed while decoding successful `dumpbin` output with the Windows GBK default (`UnicodeDecodeError` on byte `0xA5`) | 1 | Root cause traced to both unqualified `text=True` dumpbin subprocess calls; authorized a focused TDD fix with deterministic tolerant decoding before retrying the unchanged build command. |
