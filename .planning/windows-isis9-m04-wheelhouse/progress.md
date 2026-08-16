# Windows PyISIS ISIS 9 Wheelhouse Milestone

# Progress: Build and release-validate the Windows PyISIS wheelhouse

## Session Log

### Initialized 2026-08-16

- **Status:** in_progress
- Created the durable milestone plan from the reviewed manifest.

### Activated 2026-08-16

- Verified and archived completed M01-M03 lifecycle state.
- Activated M04 as the sole current milestone.
- Restored the approved design and five-task implementation plan in an isolated worktree.
- Next action is implementation-plan Task 1: structured clean-install evidence.
- Generated the Task 1 SDD brief at `.superpowers/sdd/2026-08-16-windows-pyisis-wheelhouse/task-1-brief.md` from base commit `3a713b74`.

### Task 1 completed 2026-08-16

- Added successful clean-install JSON evidence generation and source-contract coverage.
- Changed: `tools/packaging/test_wheel_install.py`, `tests/unitTest/packaging_tools_unit_test.py`.
- Commit: `7c269533 feat: report clean Windows wheel installs`.
- Independent task review: spec compliant, quality approved, no findings.

### Task 2 completed 2026-08-16

- Added the strict Windows wheelhouse validator and six focused validator tests.
- Changed: `tools/packaging/validate_windows_wheelhouse.py`, `tests/unitTest/windows_wheelhouse_validation_unit_test.py`.
- Commits: `ac43513b feat: validate Windows PyISIS wheelhouses`; `0919af97 fix: require passed Windows clean-install checks`.
- Review fix round 1 closed the fail-closed clean-install evidence gap; scoped re-review found no new breakage.

### Task 3 completed 2026-08-16

- Verified CPython 3.12.13, exact Python/ISIS DLL hashes, and mock LSK prerequisite.
- Windows-focused pre-build gate passed 49/49; after the dumpbin regression fix it passed 51/51.
- Fixed Windows dumpbin output decoding in commit `627fcb3b fix: decode Windows dumpbin output robustly`; independent task review approved with no findings.
- Final exact build retry exited 0 in 270.7 seconds and produced three wheels plus dependency JSON with `unresolved=0`.
- Retained hashes: binding `8f1a923e62c12e98041bd7a5eebdffaaf00858597747cd9d4d690393451dcc00`; runtime `1d51ad225a238d70b6accc56989023ca9dbe7401e74f6dd62153c5c55e0556bf`; minimal `43009899a9586e90bb2cbc042233f37c77c4f68fbf0d6036a5179bd1549388b5`; dependency JSON `fceb4b3b943530a53df3ef9fea684170ac9df1e3452e148f3703f5b79108a842`.

### Task 4 completed 2026-08-16

- Fresh offline wheelhouse installation passed all 11 checks; package version `1.3.0rc2` and ISIS version `9.0.0` loaded from the clean venv.
- Corrected the validator's canonical runtime member to `vendor/isis/lib/isis.dll` in commit `cbb34d70 fix: validate canonical Windows ISIS runtime layout`.
- Final validator report passed with four retained artifacts and `unresolved=0`; independent hashes matched.
- Removed and verified absent only the disposable clean venv, runtime staging, and generated minimal-data egg-info; retained the wheelhouse and both reports.
- Independent Task 4 review approved with no findings.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| `D:/pyisis-win-env/python.exe -m unittest tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_installs_from_wheelhouse -v` | 1 | 0 | 0 | baseline passed |
| Task 1 four focused `PackagingToolsUnitTest` tests | 4 | 0 | 0 | passed |
| `D:/pyisis-win-env/python.exe -m py_compile tools/packaging/test_wheel_install.py` | 1 | 0 | 0 | passed |
| Task 2 validator plus two adjacent runtime tests | 8 | 0 | 0 | passed after fix round 1 |
| Task 3 original cross-platform pre-build selector | 52 | 0 | 4 | Linux-only staging cases errored on Windows; classified platform-inapplicable |
| Task 3 Windows-focused pre-build selector | 49 | 0 | 0 | passed |
| Task 3 Windows-focused selector after dumpbin regression tests | 51 | 0 | 0 | passed |
| Task 4 isolated wheel install checks | 11 | 0 | 0 | passed |
| Task 4 validator plus adjacent runtime tests after layout correction | 8 | 0 | 0 | passed |

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|
| `build/windows/isis-prefix/lib/isis.dll` | present | Verified path resolves through the ignored prefix junction. |
| `D:/pyisis-win-env/python.exe` | present | CPython executable exists; exact version/hash verification is scheduled in Task 3. |
| `tests/data/isisdata/mockup/base/kernels/lsk/naif0012.tls` | present | Required minimal ISISDATA input exists. |
| `build/windows/isis-prefix/lib/isis.dll` | verified | SHA-256 `7291ff4ae9683bdae8c758ae9e615eb9f5cfb23da9253ad15d45a69583044420`. |
| `D:/pyisis-win-env/python.exe` | verified | CPython 3.12.13; SHA-256 `32733c1f0c531b2a259a7003c9af5de6771427c4d7d90797a41d11d0ed708c90`. |

## Git Evidence

- Branch: `feature/m04-windows-pyisis-wheelhouse`
- Worktree: `.worktrees/m04-windows-pyisis-wheelhouse`
- Activation baseline commit: `9370577d`

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m04-wheelhouse` is active in its isolated worktree |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | See `findings.md` |
| What have I done? | Archived M01-M03, activated M04, and completed/reviewed Tasks 1-4 through release-grade wheelhouse evidence |
| What am I about to do? | Document M04 usage, run final verification, and prepare structured close evidence |
