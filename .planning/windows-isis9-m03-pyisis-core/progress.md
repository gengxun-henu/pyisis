# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Progress: Build and test isis_pybind._isis_core

## Session Log

### Initialized 2026-08-15

- **Status:** pending
- Created the durable milestone plan from the reviewed manifest.

### Activated 2026-08-15

- Activated M3 after the milestone manager verified M1 and M2 completion state.
- Reviewed all declared source plans plus the repository pybind workflow and
  scoped conda/testing instructions.
- Confirmed the CPython 3.12 interpreter and verified ISIS 9 prefix libraries
  exist; no `build/windows/pyisis-build` directory exists yet.
- Preserved the unrelated modified `print.prt` guardrail file.
- Reviewed all four Stage 2 scripts and the nine-module Windows basic test list;
  selected a fresh environment/prerequisite check as the exact next action.
- First prerequisite attempt stopped before configure because the manually
  assembled PATH omitted base Conda. No build directory was created.
- Corrected the PATH from M1 readiness evidence. The repository prerequisite
  check then passed, Python reported 3.12.13/`cpython-312`, both ISIS library
  hashes matched M2 evidence, and mock ISISDATA resolved successfully.
- Configured `build/windows/pyisis-build` successfully against the verified
  ISIS 9 prefix using MSVC 19.39 and CPython 3.12.13.
- Built the extension with Ninja `-j24`; all 42 build steps completed and the
  build script exited 0 after about 150 seconds.
- Hashed the required CPython 3.12 `.pyd` and ran the fresh-process smoke-import
  gate successfully with mock ISISDATA.
- Confirmed a fresh process loaded the exact M3 `.pyd`, then passed all nine
  Windows basic modules: 329 tests, 0 failed, 0 skipped, 1 expected failure.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| `pyisis-smoke-import` | 1 | 0 | 0 | passed |
| `pyisis-basic-tests` | 329 | 0 | 0 | passed (1 expected failure) |

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|
| `build/windows/isis-prefix/lib/isis.dll` | verified | SHA-256 `7291ff4ae9683bdae8c758ae9e615eb9f5cfb23da9253ad15d45a69583044420` |
| `D:\pyisis-win-env\python.exe` | verified | Python 3.12.13 / `cpython-312`; SHA-256 `32733c1f0c531b2a259a7003c9af5de6771427c4d7d90797a41d11d0ed708c90` |
| `tests/data/isisdata/mockup/base/kernels/lsk/naif0012.tls` | verified | mock ISISDATA leap-second kernel used by smoke/basic tests |

## Git Evidence

- Branch: `main`
- Worktree: repository root (`.`)
- Commit: `9eb48c6a3a737251997eb779c410c60e1a237c17`
- Status classification: M3 planning/lifecycle changes plus preserved unstaged
  `print.prt`; ignored Windows build artifacts are retained for reuse.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m03-pyisis-core` is `complete` |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | See `findings.md` |
| What have I done? | Verified completion evidence with 330 passed, 0 failed, and 0 skipped tests |
| What am I about to do? | No further action; milestone complete. |

## Session Close: 2026-08-15

- Outcome: `complete`
- Fresh test totals: 330 passed, 0 failed, 0 skipped
- Evidence verified at: `2026-08-15T11:58:13.6753058Z`
