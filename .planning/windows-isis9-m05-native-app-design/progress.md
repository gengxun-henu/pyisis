# Windows ISIS 9 Native APP Distribution Milestone

# Progress: Design the native Windows ISIS APP release

## Session Log

### Activated 2026-08-16

- **Status:** in progress
- Ran planning session catch-up; no unsynced context was reported.
- Ran milestone verification successfully, inspected the branch, clean Git state, recent commits, M04 archived completion evidence, M05 source plan, and all three M05 planning files.
- Activated `windows-isis9-m05-native-app-design` with the milestone manager.
- Began the unique Next Step by separating the existing command-line APP manifest path from the required `qnet` GUI packaging question.
- Inspected the 150-entry tracked APP manifest and the actual 364-executable ISIS 9 prefix; confirmed all three mandatory executables exist while only `reduce` and `jigsaw` belong to the tracked CLI manifest.
- Brainstorming decision: user selected a portable ZIP for scientific/developer users as the first-release format.
- Brainstorming decision: user selected the tracked 150 CLI APPs plus `qnet` as the exact 151-APP public inventory.
- Brainstorming decision: user selected bundled minimal bootstrap/test ISISDATA plus an external complete-ISISDATA override.
- Brainstorming decision: user selected a prepared ISIS shell, one generic APP launcher, and a dedicated double-clickable `qnet` launcher.
- Brainstorming decision: user selected Windows 11 x64 as the only first-release clean-machine platform.
- Architecture approval: user selected approach A, a single curated portable ZIP staged from explicit APP and runtime dependency manifests.
- Design section 1 approved: prefix-like runtime layout, centralized launchers, explicit APP/file manifests, bundled minimal data, and exclusion of development/PyISIS-wheel content.
- Design section 2 approved: manifest-driven staging, recursive dependency closure, fixed retained artifact names, reproducible hashes, and fail-closed contamination/missing-file checks.
- Design section 3 approved: clean Windows 11 x64 CLI/GUI/data validation matrix and verified-artifact-first cleanup rules.
- Wrote `docs/superpowers/specs/2026-08-16-windows-isis-native-app-distribution-design.md`.
- Completed the brainstorming SPEC self-review: no placeholders were found, the explicit 150-name CLI inventory exactly matched the tracked manifest, the mandatory APP contract was present, and `git diff --check` passed.
- User reviewed and approved the committed written SPEC.
- Used `superpowers:writing-plans` to create `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md` with seven TDD-oriented tasks.
- Completed plan self-review: all required design tokens were covered, placeholder scan passed, seven tasks and 82 balanced code fences were present, and `git diff --check` passed. Two checker findings were logged and resolved in `task_plan.md`.

### Initialized 2026-08-16

- **Status:** pending
- Created the durable milestone plan from the reviewed manifest.
- Archived the completed M04 registry and evidence without deleting history.
- Established M05 as a pending design milestone; it has not been activated in this M04 session.
- Saved the requested new-session entry prompt at `new-session-prompt.md`; M05 remains pending and unactivated for the new session.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| M05 SPEC self-review inventory/consistency check | 1 | 0 | 0 | passed |
| M05 implementation-plan coverage/structure check | 1 | 0 | 0 | passed |

## External Prerequisites

| Path | Status | Evidence |
|---|---|---|
| `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/windows-isis9-m04-wheelhouse/completion-evidence.json` | verified | M04 completion evidence records 65 focused passes, 330 clean-install passes, exact artifacts/hashes, and final validation. |
| `build/windows/isis-prefix` | available | Existing ignored junction exposes the verified ISIS 9 prefix for later design validation; M05 must reverify before use. |

## Git Evidence

- Branch: `feature/m04-windows-pyisis-wheelhouse`
- Worktree: repository root (`.`)
- Commit: `ffff018c637b87a4f649657a0636489322b22920`

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Milestone `windows-isis9-m05-native-app-design` is pending |
| Where am I going? | Its declared completion gate |
| What's the goal? | See `task_plan.md` Goal |
| What have I learned? | M05 owns a separate native APP product and still needs explicit packaging decisions |
| What have I done? | Archived completed M04 and initialized M05 as pending |
| What am I about to do? | In a new session, activate M05 and brainstorm package format plus APP inventory |
