# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Task Plan: Build and verify the ISIS 9.0.0 native prefix

## Goal

Complete milestone `windows-isis9-m02-isis-prefix` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-15-windows-isis9-pyisis-build-design.md#milestones`
- `ports/windows/isis/README.md`

## Dependencies

- `windows-isis9-m01-environment`

## Completion Gate

The patched upstream ISIS 9.0.0 source builds and installs with MSVC, the prefix
verification passes, representative ISIS applications pass their smoke tests,
and all 150 main-branch Windows APP manifest entries pass the ISIS 9 batch
startup gate plus its selected real Cube operations.

## Next Step

Review the source plans and begin the first uncompleted valid-input task.

## Current Phase

Phase 1

## Phases

### Phase 1: Milestone execution

- [ ] Fetch ISIS tag `9.0.0` at commit `950a5606ffeaa13ddb40101fbf25a8737e88902a`
- [ ] Apply the tracked ISIS 9 Windows patch queue
- [ ] Configure and build the complete ISIS 9 Windows target set with MSVC/Ninja and `-j 1`
- [ ] Install and pass `verify_isis_prefix.ps1`
- [ ] Pass `test_isis_apps_smoke.ps1`
- [ ] Confirm `windows-app-manifest.json` contains exactly 150 ISIS 9 supported APPs
- [ ] Pass `test_isis_app_batch_smoke.ps1 -IsisVersion 9.0.0` for all 150 executables and selected Cube operations
- [ ] Produce and verify the declared milestone evidence, including the additional 150-APP batch result
- **Status:** pending

## Decisions Made

| Decision | Rationale |
|---|---|
| Lock the expanded APP gate to the 150-entry manifest already present on `main` | The user requested 150 APPs. PR #356 is an unmerged, conflicting 169-APP ISIS 10 follow-up and is outside this ISIS 9 build scope. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
