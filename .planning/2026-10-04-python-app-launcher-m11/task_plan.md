# Task Plan: PyISIS Python app launcher integration (M11)

## Goal

Integrate the new `pyisis.apps.run()` facade into the release branch, make self-hosted checkout resilient to stale permission-owned build files, and complete the change through PR validation and local `main` synchronization.

## Scope

- Preserve and validate `python/pyisis/apps.py`, its CMake installation path, documentation, and focused tests.
- Add a narrow checkout configuration guard for the known self-hosted runner cleanup failure.
- Run focused and full local validation, update durable evidence, push the current PR, and merge only after required checks are acceptable.
- Keep the historical M06 registry immutable; its missing retained ZIP is recorded as a separate legacy verification blocker.

## Source Plans

- `.planning/dual-version-wheel-release-m09/`
- `.planning/linux-runner-docker-maintenance-m10/`
- `AGENTS.md`
- `.github/workflows/reusable-pybind-build-self-hosted.yml`

## Dependencies

- PR #383 branch `feat/native-app-launcher-facade`.
- Local focused/full tests already pass for the Python facade.
- Self-hosted runner currently has stale permission-owned files; Windows wheel runners are currently unavailable.

## Completion Gate

The app launcher facade and checkout-resilience change are committed on a PR branch; focused tests and the local full unit suite pass with recorded counts; the PR is merged when repository checks permit it; and local `main` is synchronized to the merge commit without touching `print.prt`.

## Next Step

None — M11 is complete and merged as `f4ddebb650543e5f332ef0acaa5ee917b2e39cac`.

## Current Phase

Phase 3: PR integration and synchronization

## Phases

### Phase 1: Contract and regression coverage

- [x] Add focused workflow regression coverage for checkout cleanup behavior.
- [x] Record the existing M06 registry artifact-verification blocker and current PR check state.
- **Status:** complete 2026-10-04

### Phase 2: Implementation and validation

- [x] Apply the minimal self-hosted checkout resilience setting.
- [x] Run focused tests, full unit tests, smoke import, and diff checks.
- **Status:** complete 2026-10-04

### Phase 3: PR integration and synchronization

- [x] Commit and push task-scoped changes to PR #383.
- [x] Monitor checks and merge through the protected PR path when allowed.
- [x] Synchronize local `main` and record the final merge evidence.
- **Status:** complete 2026-10-04

## Decisions

- Keep the Python facade API unchanged: ISIS application arguments remain an argument list such as `"from=image.cub"`.
- Use `clean: false` only for the self-hosted reusable checkout because the observed failure occurs in checkout's automatic `git clean`; the subsequent build/cache cleanup remains responsible for disposable outputs.
- Do not bypass required checks or fabricate Windows coverage while the Windows runner is unavailable.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Canonical milestone verification failed because the completed M06 ZIP is absent | 1 | Preserve the immutable registry and record this as a legacy evidence blocker; do not rewrite completed evidence in this milestone. |
| Self-hosted PR gates failed during checkout cleanup with permission denied | 1 | Add regression coverage and a targeted `clean: false` workflow setting, then rerun the gates. |

## Reboot Check

- **Where am I?** Phase 1, before workflow change.
- **Where am I going?** Complete the app launcher PR and synchronize `main`.
- **Goal?** A merged, locally synchronized PR with fresh validation evidence.
- **What have I learned?** Local code is healthy; current remote failures are infrastructure-related.
- **Next step?** Add the checkout cleanup regression test.

## Completion Evidence

- Merge commit: `f4ddebb650543e5f332ef0acaa5ee917b2e39cac`.
- Focused tests: 50 passed, 0 failed, 0 skipped.
- Smoke import: passed.
- Full unit suite: 2727 run, 0 failed, 52 skipped, 1 expected failure.
- `git diff --check`: passed.
- Local `main`: synchronized with `origin/main` at `f4ddebb6`; guarded `print.prt` remained untouched.
- Remaining environment note: Windows wheel jobs were queued because no Windows runner was online; the PR merge did not bypass a failed check.
