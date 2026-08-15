# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Progress: Prepare the Windows native build environment

## Session Log

### Initialized 2026-08-15

- **Status:** pending
- Created the durable milestone plan from the reviewed manifest.

### Environment creation attempt 1 — 2026-08-15

- Confirmed `D:\pyisis-win-env` and `D:\mamba\pyisis-isis9` were absent and D:
  had approximately 1629 GB free.
- Ran the pinned environment create command with micromamba.
- Dependency resolution succeeded, but extraction failed while creating
  `ucrtbase.dll` and `OpenCL.dll` in the package cache; exit code 1.
- Preserved the partial root and prefix for read-only diagnosis. No retry has
  been issued.

### Environment creation attempt 2 — 2026-08-15

- Switched to the repository-documented Conda classic fallback and placed the
  prospective package cache at `D:\conda-pkgs\pyisis-isis9`.
- Conda stopped before dependency solving because the user's global `.condarc`
  injects three Anaconda `defaults` channels whose ToS are not accepted.
- Did not accept the unrelated channel terms. The repository environment file
  declares only conda-forge, so the next diagnostic isolates configuration at
  command scope.
- Verified a command-scoped conda-forge-only condarc with a dry run. The ToS
  error disappeared; classic dependency solving exceeded the diagnostic
  command's 124-second timeout, so the formal create will use a longer limit.

### User-directed scope update — 2026-08-15

- Stopped the still-solving Conda process before it began package installation.
- User requested synchronizing the latest remote Windows ISIS/PyISIS release
  work and adding the 150-Windows-APP build scope.
- First `git fetch --prune origin` failed because the GitHub HTTPS connection
  was reset. Existing `origin/main` cannot yet be treated as current.
- GitHub API subsequently confirmed remote main SHA `ccea4240`, matching the
  local origin reference. No main pull was required.
- Audited open PR #356: it raises an earlier 149-APP ISIS 10 gate to 169 and is
  currently conflicting; it is not the requested 150-APP main baseline.
- Confirmed main contains exactly 150 manifest APPs with ISIS 9 supported
  metadata and expanded the future M2 plan to require their batch startup/Cube
  smoke.
- Synced and hash-verified the ISIS 9 rc2 Windows wheelhouse release baseline.

### Conda environment and toolchain verification — 2026-08-15

- Created `D:\pyisis-win-env` from
  `ports/windows/env/pyisis-isis-win64.yml` using Conda 26.5.3 classic solver,
  conda-forge-only command configuration, and
  `CONDA_PKGS_DIRS=D:\conda-pkgs\pyisis-isis9`.
- Installed Python 3.12.13, CMake 4.2.3, Ninja 1.13.2, pybind11 3.1.0, and CSM
  3.0.3.3.
- Activated Visual Studio 2022 Community x64 tools; `cl.exe` and `dumpbin.exe`
  resolve from MSVC 14.39.33519.
- `ports/windows/check_prereqs.ps1` exited 0 and printed
  `all prerequisite commands are available`.
- Wrote `build/windows/reports/environment-readiness.json` with exact paths,
  versions, remote main SHA, 150-APP manifest count, and reference release hash.
- Initial pre-close milestone structure verification found a multiline
  `Next Step`; normalized it to the required single plain-text line before
  completion evidence generation.
- First close attempt used a predicted post-close Git porcelain hash; the tool
  rejected it against the actual clean pre-transaction hash and made no
  lifecycle changes. Evidence generation was corrected to the observed clean
  state.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| Environment creation attempt 1 | 0 | 1 | 0 | failed during package extraction |
| Environment creation attempt 2 | 0 | 1 | 0 | stopped before solve by injected defaults-channel ToS gate |
| windows-prerequisite-check | 1 | 0 | 0 | passed |

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|
| `C:\Windows\System32\kernel32.dll` | verified | Windows 11 x64 OS path used for structured hash evidence |
| `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.39.33519\bin\HostX64\x64\cl.exe` | verified | MSVC x64 compiler resolved after repository activation script |
| `D:\tools\micromamba\micromamba.exe` | verified | Micromamba 2.8.1 diagnostic prerequisite; Conda classic used for host-safe extraction |

## Git Evidence

- Branch: `main`
- Worktree: repository root (`.`)
- Commit: `092e009a3ac625da95350b6dd8f9b241cf6d21b6`
- Planning initialization commit: `edec37f6`.
- Final M1 evidence records the live commit and classified closure-only Git
  status after the last task-related planning commit.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m01-environment` is `complete` |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | See `findings.md` |
| What have I done? | Verified completion evidence with 1 passed, 0 failed, and 0 skipped tests |
| What am I about to do? | No further action; milestone complete. |

## Session Close: 2026-08-15

- Outcome: `complete`
- Fresh test totals: 1 passed, 0 failed, 0 skipped
- Evidence verified at: `2026-08-15T04:28:33.2198359Z`
