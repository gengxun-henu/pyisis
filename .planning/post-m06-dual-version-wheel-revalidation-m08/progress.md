# Progress: Post-M06 dual-version wheel revalidation (M08)

## Session Log

### Started 2026-08-20

- Implementation design approved; no build, remote workflow dispatch, release, or product-code modification has occurred.
- The M08 implementation plan is `docs/superpowers/plans/2026-08-20-post-m06-dual-version-wheel-revalidation.md`.

### Task 1 completed 2026-08-20

- Frozen validation SHA: `07b87e389c09ad838b65dae3456927d66b289cd8` (`feature/m04-windows-pyisis-wheelhouse`).
- Pre-remote state: only pre-existing guarded `print.prt` was unstaged; `git diff --check` passed with no output.
- Contract command passed: `python -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test -v` (33 passed, 0 failed, 0 skipped).
- Planned evidence output directory: `build\\windows\\m08-release-evidence`.
- The plan and initial M08 records were already committed by `07b87e38` (`docs: plan post-M06 wheel revalidation`); this task creates no empty commit and commits only the substantive Task 1 record updates.

### Task 3 dispatch correction 2026-08-20

- Corrected the invalid planned input `release_line=none` to the supported `release_line=isis10`.
- The planned dispatch now explicitly sets `publish_testpypi=false` and `publish_github_release=false`; the GitHub-release job also requires `main`, so the feature-branch validation dispatch creates no release.
- The M08 objective remains four-lane validation with no publication and a stop at the first failed layer.

## Test Results

| Test | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---|
| Workflow contract tests | 33 | 0 | 0 | passed |
| M08 remote workflow run `32373382592` | 3 build/scope jobs | 8 install/bootstrap jobs | 1 release job | failed; no publication |
| Repair-focused RED tests | 0 | 3 | 0 | expected failure: missing behavior |
| Repair-focused GREEN tests | 3 | 0 | 0 | passed |
| Full packaging/workflow modules after repair | 35 | 0 | 0 | passed |

### Failed validation and repair authorization 2026-08-21

- Run `32373382592` completed with failure at exact SHA `b50506e365b1af6d80fdbefbba919d70b5779197`.
- Linux: six clean-install jobs failed because the metadata probe hard-coded Windows and ISIS 9 distribution names.
- Windows: cp312 failed downloading Python with `ECONNRESET`; cp313 failed checkout after DNS/connectivity errors.
- User explicitly requested root-cause repair and revalidation. Repair phase is active; no release is authorized.

### Repair implementation 2026-08-21

- Added package-derived installed-distribution expectations and repeatable `--additional-distribution` runtime checks.
- Windows ISIS 9/10 clean installs explicitly verify their matching runtime distributions.
- Removed redundant Windows `actions/setup-python`; setup-miniconda supplies the version-pinned build interpreter.
- RED: three focused tests failed for the absent behavior. GREEN: the same three passed. Full packaging/workflow modules passed 35/35.
- Independent review found the code fix correct and requested this planning-state correction before commit.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | M08 repair phase after failed run `32373382592`. |
| Where am I going? | Tested repair followed by fresh four-lane evidence. |
| What's the goal? | Revalidate wheels without publishing a release. |
| What have I learned? | Historical rc2 evidence cannot validate M06-era changes; the tracked contract maps four required lanes to existing workflow jobs and passed locally. |
| What is next? | Commit and push the repaired SHA, then dispatch the non-publishing matrix with `windows_runner=windows-2022`. |
