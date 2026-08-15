# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Task Plan: Prepare the Windows native build environment

## Goal

Complete milestone `windows-isis9-m01-environment` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-15-windows-isis9-pyisis-build-design.md#milestones`
- `ports/windows/README.md#prerequisites`

## Dependencies

- None

## Completion Gate

The short-path conda environment and Visual Studio 2022 x64 toolchain are reproducible and all repository Windows prerequisite checks pass.

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
| Use Miniconda with `--solver classic` and `CONDA_PKGS_DIRS=D:\conda-pkgs\pyisis-isis9` | This is the repository-documented supported path for this host's endpoint-security restriction and keeps large caches off C:. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| micromamba could not create `ucrtbase.dll` or `OpenCL.dll` under `D:\mamba\pyisis-isis9\pkgs\https\...`, then reported missing/empty `info/index.json` | Environment creation attempt 1 | Root cause matches `.github/workflows/README.md`: host endpoint security blocks Micromamba UCRT extraction but permits Conda. Use Conda classic without disabling protection. |
| Conda raised `CondaToSNonInteractiveError` for `repo.anaconda.com/pkgs/main`, `pkgs/r`, and `pkgs/msys2` before solving | Environment creation attempt 2 | Global `C:\Users\gx\.condarc` injects `defaults` although the repository YAML declares only conda-forge. Diagnose a command-scoped conda-forge-only configuration; do not accept unrelated ToS. |
| `git fetch --prune origin` failed with `Recv failure: Connection was reset` after the user expanded scope to remote Windows releases and 150 APPs | Remote synchronization attempt 1 | Verify the remote main SHA through GitHub API, then retry fetch with HTTP/1.1 before trusting ahead/behind output. |
| Milestone verification rejected a three-line `Next Step` | M1 pre-close structure verification | Rewrote the same action as exactly one plain-text line, as required by the milestone contract. |
| First completion close declared the predicted post-transaction Git status, but validation observed the clean pre-transaction status | M1 completion close attempt 1 | No lifecycle writes occurred. Record the actual clean status hash because `close_session.py` validates evidence before applying its transaction. |
