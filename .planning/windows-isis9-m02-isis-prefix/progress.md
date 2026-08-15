# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Progress: Build and verify the ISIS 9.0.0 native prefix

## Session Log

### Initialized 2026-08-15

- **Status:** pending
- Created the durable milestone plan from the reviewed manifest.

### Continued 2026-08-15

- Activated `windows-isis9-m02-isis-prefix` with the milestone manager.
- Read the root `AGENTS.md`, canonical registry, all three M2 planning files,
  and both declared source plans.
- Inspected the repository-root worktree, branch, dirty state, recent commits,
  and M1 prerequisite paths without treating historical validation as fresh M2
  evidence.
- Began the unique Next Step by identifying source fetch/identity verification
  as the first uncompleted valid-input task.
- The initial fetch was interrupted by the inspection command's 10-second
  timeout. Diagnosed the partial state: no surviving child process, correct
  pinned HEAD, and an unpopulated worktree. The repository script's supported
  existing-checkout path is the next recovery action.
- The supported Git resume also stalled at lazy blob download with no bytes
  received for about seven minutes. Verified and stopped only its four child
  Git processes. Preserved the partial checkout and selected the documented
  archive fallback at a separate path as the next alternative transport.
- The archive fallback exhausted all four bounded curl connection attempts with
  exit 28. Per the 3-strike rule, stopped transport retries and moved to a
  read-only search for an existing local copy at the pinned commit.
- No usable local source/object copy was found. Fresh hashes for all M1
  dependency evidence exactly matched the registry. No related fetch process
  remains, and no archive/source tree was produced by the fallback.
- The first checkpoint close was rolled back because `Next Step` was not one
  plain-text line. Read the milestone contract and corrected only that format.

### Resumed 2026-08-15

- Re-read the active planning state, repository rules, Git status, and the
  previous checkpoint.
- A fresh HTTPS probe to the ISIS archive URL returned HTTP 302 in under one
  second. The corresponding schema-1 resolution evidence was accepted, and the
  milestone transitioned from `blocked` back to `in_progress`.
- The bounded archive fetch began transferring, but the outer 15-minute runner
  timed out before it completed. Its orphaned curl child later reduced the
  archive to 0 bytes and reconnected without producing a usable source tree.
  Verified and stopped only that curl process. The archive transport blocker is
  therefore unresolved despite the successful HTTP probe.

### Continued 2026-08-15

- Re-read the active M2 plan, checkpoint, registry, repository state, and
  source-fetch history.
- A bounded 1 MiB archive Range probe received 0 bytes and ended with curl 56
  after 29.210310 seconds. It confirmed that the sustained-payload blocker is
  still active; no related process remains.
- The GitHub redirect target was confirmed as `codeload.github.com`. Its direct
  64 KiB Range probe returned HTTP 200 and transferred 648,725 bytes before the
  30-second timeout, demonstrating that codeload ignores the requested Range.
  This explains why curl `--continue-at -` is not a reliable recovery path for
  the archive script on this host.

### Continued 2026-08-15 — local-cache fallback audit

- Re-verified the milestone registry and active-plan pointer before resuming
  the sole source-fetch prerequisite.
- A new bounded 1 MiB payload probe received 0 bytes and failed with HTTP 000 /
  curl 56 after about 27.5 seconds; no full fetch or build was started.
- Searched the discovered conda/micromamba package caches and local Git refs for
  a reusable ISIS 9.0.0 source copy. None was found beyond the preserved partial
  checkout and incomplete archive.
- Checked official USGS distribution guidance for a second source mirror; the
  GitHub repository remains the documented primary source location.

### Continued 2026-08-15 — source recovered and patched

- Downloaded the complete official ISIS 9.0.0 tag archive using
  `Invoke-WebRequest` with a 15-minute command timeout; full tar validation
  passed for 11,998 entries.
- Extracted a new source tree without altering the preserved partial checkout.
  Verified HEAD at the pinned commit and matched 60/60 existing Windows
  patch-target files against the pinned Git blob IDs.
- Reproduced the CRLF patch application failure, added a focused failing test,
  updated `apply_patches.ps1` to ignore context whitespace changes, and observed
  that regression test pass.
- Applied all eight ISIS 9 Windows patches successfully. The next action is the
  MSVC/Ninja configure for the complete 150-APP target set.

## Session checkpoint — resumed 2026-08-15

- Primary workflow: `milestone-session-manager` with `planning-with-files`
- CWD: `D:\code\pyisis\pyisis`
- Branch/worktree: repository-root worktree, branch `main`, HEAD `0c6269e7`,
  four commits ahead of `origin/main`
- Goal: Build and verify the native Windows ISIS 9.0.0 prefix, including the
  150-APP gate
- Current phase or plan task: Phase 1, fetch pinned ISIS tag `9.0.0` at commit
  `950a5606ffeaa13ddb40101fbf25a8737e88902a`
- Completed: verified a fresh HTTPS redirect probe, supplied accepted
  resolution evidence, resumed M2, and ran the sole archive-fetch action
- Files changed: M2 planning files plus `resolution-evidence.json`; lifecycle
  files remain manager-owned changes only
- Validation completed: HTTPS probe returned HTTP 302; archive transfer wrote
  bytes but did not complete; no M2 build/test gate ran
- Review status: no code review; no product code changed
- Running processes: none related to ISIS fetch
- Do not repeat: do not consider an HTTP redirect proof of archive-transfer
  health; do not start patches or builds without a verified source tree
- Remaining risks: the archive transport failed to complete within the runner
  window, and prior partial-clone state remains only diagnostic data
- Exact next action: after a sustained GitHub archive payload transfer is
  available, run the one-line archive fetch command in `task_plan.md`
- Recommended resume skill: `milestone-session-manager`

## Session checkpoint

- Primary workflow: `milestone-session-manager` with `planning-with-files`
- CWD: `D:\code\pyisis\pyisis`
- Branch/worktree: repository-root worktree, branch `main`, HEAD `0c6269e7`,
  four commits ahead of `origin/main`
- Goal: Build and verify the native Windows ISIS 9.0.0 prefix, including the
  150-APP gate
- Current phase or plan task: Phase 1, fetch pinned ISIS tag `9.0.0` at commit
  `950a5606ffeaa13ddb40101fbf25a8737e88902a`
- Completed: activated M2; read all required durable/source plans; verified Git
  state and M1 dependency hashes; diagnosed three fetch attempts; preserved the
  partial Git metadata checkout
- Files changed: M2 `task_plan.md`, `findings.md`, and `progress.md`; lifecycle
  files already changed by M1 close/M2 activation remain preserved
- Validation completed: M1 evidence hashes matched 4/4; upstream tag ref and
  partial checkout HEAD both resolve to the pinned commit; no M2 build/test gate
  has run
- Review status: no code review; no product code changed
- Running processes: none related to ISIS fetch
- Do not repeat: do not retry partial-clone checkout or alter network knobs
  without new connectivity evidence; do not treat README history as fresh M2
  validation
- Remaining risks: GitHub HTTPS is unavailable; the partial checkout contains
  only Git metadata and a stale lock/temp pack; M2 build and all APP gates remain
  unstarted
- Exact next action: after GitHub HTTPS connectivity is restored, run the
  bounded archive-fetch command recorded in `task_plan.md`
- Recommended resume skill: `milestone-session-manager`

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|

## Git Evidence

- Branch: `main`
- Worktree: repository root (`.`)
- Commit: `092e009a3ac625da95350b6dd8f9b241cf6d21b6`

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m02-isis-prefix` is `complete` |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | See `findings.md` |
| What have I done? | Verified completion evidence with 189 passed, 0 failed, and 0 skipped tests |
| What am I about to do? | No further action; milestone complete. |

## Session Close: 2026-08-15

- Outcome: `blocked`
- Next Step: After github.com:443 HTTPS connectivity is restored, run the bounded archive fetch command recorded in .planning/windows-isis9-m02-isis-prefix/task_plan.md.

## Session Close: 2026-08-15

- Outcome: `blocked`
- Next Step: After a sustained GitHub archive payload transfer is available, run the one-line archive fetch command in .planning/windows-isis9-m02-isis-prefix/task_plan.md.

## Build resumed: 2026-08-15

- Recovered the official ISIS 9.0.0 source archive and verified pinned commit
  `950a5606ffeaa13ddb40101fbf25a8737e88902a` plus all 60 existing patch-target blobs.
- Applied all eight Windows patches after adding CRLF-safe `git apply`
  handling; the focused packaging regression test passed.
- Configured the MSVC/Ninja build with all 150 ISIS 9 manifest APP names.
- The user explicitly changed the build from one job to Ninja `-j24`; the
  incremental full build completed at `[1295/1295]` with exit code 0.
- Repository C++ build defaults now use `min(24, available logical processors)`
  in the ISIS, SpiceQL, and PyISIS Windows build scripts; focused tests passed
  2/2 and `git diff --check` passed.
- Next Step: install into `build/windows/isis-prefix` and run the fresh prefix
  verifier for ISIS 9.0.0.

## Prefix verification and APP-smoke blocker: 2026-08-15

- `cmake --install` completed with exit code 0; the upstream install tail emitted
  non-fatal Linux-only `cp/ln libisis.so` messages on Windows.
- `verify_isis_prefix.ps1 -ExpectedVersion 9.0.0` passed, including a real
  `isis.dll` load; it found the header/import library/runtime DLL and created
  364 missing `.exe.xml` aliases.
- `test_isis_apps_smoke.ps1` passed `stats` and `getkey`, then could not start
  `catlab.exe` because the file was removed during process launch.
- Reproduced four times with the original installed file, a fresh copy, a
  renamed copy, and a copy processed by `editbin /release`; each existed before
  launch, disappeared after about 60 seconds, and Windows reported file not found.
- The build-tree `catlab.exe` remains intact with SHA-256
  `3AC1600EBFC32C55FB565ADBEF95AE41B399195C6EE0BD210C41685943A69AFF`.
- Defender, AppLocker, and Code Integrity logs contain no matching event. Windows
  Security Center reports Lenovo Anti-Virus powered by Huorong Security and 360
  Security in addition to Defender, so an external allow/exclusion action is
  required before APP execution can be validated.
- No security product setting was changed automatically.

## Antivirus resolution and representative smoke: 2026-08-15

- The user authorized a scoped antivirus allow operation and added
  `D:\code\pyisis` to the 360 Trojan Scan trusted area; the UI records an add
  time of 18:07:41 and the entry covers the ISIS prefix.
- A fresh reinstall returned 0. `catlab -help` returned 0, the executable
  remained present, and its SHA-256 stayed
  `3AC1600EBFC32C55FB565ADBEF95AE41B399195C6EE0BD210C41685943A69AFF`.
- The milestone manager accepted updated blocker-resolution evidence and
  transitioned M2 back to `in_progress`.
- `test_isis_apps_smoke.ps1` passed 9/9 commands with exit code 0: `stats`,
  `getkey`, `catlab`, `reduce`, `campt`, `cam2map`, `isis2std`, `cubeit`, and
  `fx`. Logs and outputs are under `build/windows/isis-command-smoke`.

## Final M2 gates: 2026-08-15

- Fresh manifest validation found 150 total APPs, 150 ISIS 9 supported APPs,
  150 unique names, and zero duplicates.
- The first batch attempt showed ISIS 9 rejects the ISIS 10-only `crop`
  parameter `OVERHANG`; the next attempt showed ISIS 9 also rejects the
  ISIS 10-only `csv2table` parameter `COLTYPES`.
- Added `Test-IsisAppParameter`, which reads the active installed APP XML as
  the parameter authority. A focused regression test was observed failing
  before the helper existed and passing afterward.
- The batch probe now uses `OVERHANG` and mixed-type CSV data only when the
  installed APP XML declares the corresponding parameter.
- Fresh `test_isis_app_batch_smoke.ps1 -IsisVersion 9.0.0` passed 150/150 APP
  startup checks plus 23/23 selected Cube/table operations, all with exit 0.
  There are 150 startup logs, 23 Cube-operation logs, and zero missing
  manifest startup logs under `build/windows/isis-app-batch-smoke`.
- Fresh completion verification passed prefix verification (1/1),
  representative APP smoke (9/9), and focused Windows packaging/smoke unit
  tests (6/6). `git diff --check` passed for all task product/test files.
- Required artifact hashes: `isis.dll`
  `7291ff4ae9683bdae8c758ae9e615eb9f5cfb23da9253ad15d45a69583044420`;
  `isis.lib`
  `1582d80acd2d5d9b479cee1b24ee88065b37399be712cc92ab119051e2216a3d`.

## Session Close: 2026-08-15

- Outcome: `blocked`
- Next Step: After a sustained GitHub archive payload transfer is available, run the one-line archive fetch command in .planning/windows-isis9-m02-isis-prefix/task_plan.md.

## Session Close: 2026-08-15

- Outcome: `blocked`
- Next Step: After the local third-party antivirus allows the locally built ISIS executables, reinstall catlab.exe and rerun test_isis_apps_smoke.ps1 against build/windows/isis-prefix.

## Session Close: 2026-08-15

- Outcome: `complete`
- Fresh test totals: 189 passed, 0 failed, 0 skipped
- Evidence verified at: `2026-08-15T10:20:00.1074251Z`
