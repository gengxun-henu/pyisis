# Windows ISIS 9 Native APP Implementation Milestone

# Progress: Build and validate the Windows ISIS native APP release

## Session Log

### Activated 2026-08-17

- **Status:** in progress
- Archived the complete immutable M05 registry and planning directory under `.planning/archive/windows-isis9-native-app-m05/`.
- Initialized, activated, and structurally verified M06 on branch `feature/m04-windows-pyisis-wheelhouse`.
- Adopted csv2table Task 1 commit `0a1781d2`, Task 2 commit `011f8d15`, the approved plan amendment `d7c7fff7`, and Task 3 commit `251d0fb5`.
- Task 1 review passed specification compliance with one deferred file-header metadata Minor for final review.
- Task 2 specification and quality review passed cleanly.
- Task 3 implementation passed 29 focused tests and real Windows ISIS 9 150-APP smoke; its independent review must be repeated because the prior reviewer session ended without a report.
- Repeated Task 3 review with a fresh agent after one reviewer environment failed. Specification compliance and task quality both passed; one non-blocking raw-`ValueError` CLI diagnostic Minor is deferred to final review.
- Task 4 commit `d9bdc82a` added the cross-platform native-process validator. RED observed seven missing-module errors; GREEN passed 7/7 tests, py_compile, help, and diff checks. Independent specification and quality review passed with no findings.
- Task 5 commits `318c173b` and `aaee08b0` collected and bound genuine ISIS 9/10 x Windows/Linux evidence; every native validator cell passed 3/0/0. Independent Task 5 review passed cleanly.
- Final csv2table review found one missing high-level absence regression and one stale metadata entry. The single fix wave `d8409ad2` closed both; re-review is Ready. The raw rank CLI `ValueError` remains an approved deferred Minor.
- Phase 1 is complete. Phase 2 begins with the shared Windows PE dependency engine.
- Native distribution Tasks 1-6 passed implementation and independent review after focused TDD repair waves. The shared dependency engine, 151-APP contract, launchers, transactional deterministic stager, strict validator, and runtime orchestrator are complete.
- A real local Windows 11 run produced 166/0/0 across 150 help probes, nine real operations, three GUI launches, external ISISDATA, and the two required negative paths. It is retained only as local evidence, not clean-host evidence.
- The deterministic ZIP contains 1,397 members and has SHA-256 `7ea41d54ba123d9f5a4aa57491a16ac3ebf1295010ec3e11df925ae4579b9e96`; its dependency report records 106 packaged files and zero unresolved dependencies.
- Clean-host GitHub run `32083043384` is building the ISIS 9 prefix. In parallel, an official Windows 11 Enterprise Evaluation VM is installing under QEMU TCG from an unattended floppy, with only the ZIP, release contract, and runtime script mapped on removable media.
- The first complete QEMU clean-host attempt reached the GUI phase and exposed a TCG-only startup-latency issue: the real `reduce.exe` appeared after 49.856 seconds and its visible window after 126.125 seconds. Commit `c90b16ce` raised the fail-closed GUI probe timeout from 30 to 300 seconds; focused tests passed 14/14 twice and the combined native suite passed 73/73.
- A subsequent clean attempt stopped at `cnetref -HELP` with `0xc0000005`. Windows event evidence identifies the faulting process as the outer `powershell.exe`, not `cnetref.exe`; a fresh extraction then ran the same packaged launcher three times successfully (exit 0 in 142.049, 49.770, and 45.670 seconds). This is classified as a guest/TCG transient, not a package defect.
- A stable `Nehalem-v1` QEMU CPU profile passed a 250/250 independent PowerShell-process stress gate with no Application Error events, isolating the earlier `0xc0000005` crashes to the prior QEMU CPU model rather than the package.
- The final isolated Windows 11 Enterprise Evaluation guest (10.0.26200.0 AMD64) consumed only the read-only release media, confirmed all forbidden development paths absent, and passed the complete runtime matrix: 150 CLI help probes, nine real operations, three GUI launches, one external-ISISDATA probe, and two required negative probes, for 166/0/0 with negative exits `[4,3]`.
- The strict validator bound raw runtime SHA-256 `14c3c4e55a79a577924bba9d59a880f9792d01dfcee54504cc575822ad481a8d` to ZIP SHA-256 `7ea41d54ba123d9f5a4aa57491a16ac3ebf1295010ec3e11df925ae4579b9e96` and dependency-report SHA-256 `426ff10ffa084815e196ac6248b4f8d71bbc83de34bb756a9853d6c413629738`. The retained validation report has SHA-256 `005b2de03d11876ed73eb348d133d0d6c97cc2d92dac58b52d8956c593924dc5`, and the transactional work directory is absent.
- Task 7 implementation is complete; its independent final review and the whole-plan review are the remaining gates before M06 registry closure.
- A fresh completion regression passed the csv2table focused selector with 47 passes, zero failures, and one pre-existing versioned-upstream-source skip; the tracked four-cell native matrix independently revalidated as 12/0/0.
- The final Windows native release selector passed 73/73. A newly exposed WinForms fixture-only ancestry race was corrected in `e7365943`: its worker now waits for the child GUI process, matching the production launcher's retained ancestry. Three consecutive targeted runs and the full selector passed; no product behavior was relaxed.
- Task 7 independent review and the whole native-distribution plan review are both Ready with zero Critical, Important, or Minor findings. The csv2table plan's earlier final review remains Ready, with only its approved deferred raw-`ValueError` diagnostic Minor.
- The exact Windows 11 self-hosted runner was started and came online. Its queued Actions clean job correctly failed closed because this development host contains the explicitly forbidden source-prefix path; it is not substituted for the isolated QEMU evidence.

### Initialized 2026-08-17

- **Status:** pending
- Created the durable milestone plan from the reviewed manifest.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| Task 1 csv2table boundary contract | 4 | 0 | 0 | passed |
| Task 1 installed-layout smoke import | 1 | 0 | 0 | passed |
| Task 2 ISIS 10 bind inventory | 7 | 0 | 1 | passed with upstream-source absence skip |
| Task 3 focused packaging/native APP contracts | 29 | 0 | 0 | passed |
| Windows ISIS 9 APP batch startup | 150 | 0 | 0 | passed |
| Windows ISIS 9 csv2table-to-tabledump behavior | 2 | 0 | 0 | passed |
| Task 4 native validator unit tests | 7 | 0 | 0 | passed |
| Task 5 focused matrix regression | 47 | 0 | 1 | passed with pre-existing upstream-source absence skip |
| ISIS 9 / Windows native validator | 3 | 0 | 0 | passed |
| ISIS 9 / Linux native validator | 3 | 0 | 0 | passed |
| ISIS 10 / Windows native validator | 3 | 0 | 0 | passed |
| ISIS 10 / Linux native validator | 3 | 0 | 0 | passed |
| Final csv2table boundary contract | 6 | 0 | 0 | passed |
| Windows native release focused regression | 73 | 0 | 0 | passed |
| Clean Windows 11 x64 runtime matrix | 166 | 0 | 0 | passed |
| QEMU CPU stability process stress | 250 | 0 | 0 | passed |
| Final Windows native release selector | 73 | 0 | 0 | passed |

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|
| `.planning/archive/windows-isis9-native-app-m05/milestones.v1.json` | verified | Archived registry records M05 `complete` with design evidence. |
| `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/windows-isis9-m04-wheelhouse/completion-evidence.json` | verified | Archived M04 wheelhouse completion evidence. |
| `build/windows/isis-prefix` | available and behavior-tested | ISIS 9 150-APP batch and csv2table/tabledump path passed after complete runtime PATH setup. |

## Git Evidence

- Branch: `feature/m04-windows-pyisis-wheelhouse`
- Worktree: repository root (`.`)
- Commit at activation: `251d0fb55c3578f00e8768c546b79d7beed80679`
- Classified dirty state: only guardrail file `print.prt` is unstaged; milestone registry initialization/activation changes are task-related and pending commit.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m06-native-app-implementation` is `complete` |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | See `findings.md` |
| What have I done? | Verified completion evidence with 298 passed, 0 failed, and 1 skipped tests |
| What am I about to do? | No further action; milestone complete. |

## Session Close: 2026-08-19

- Outcome: `complete`
- Fresh test totals: 298 passed, 0 failed, 1 skipped
- Evidence verified at: `2026-08-19T02:13:32.1806544Z`
