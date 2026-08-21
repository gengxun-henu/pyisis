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
| Packaging/workflow/self-hosted suite after optimization | 50 | 0 | 0 | passed |
| Windows PE closure focused suite | 5 | 0 | 0 | passed |
| Windows self-hosted proxy contract RED | 0 | 1 | 0 | expected failure before workflow change |
| Wheel workflow module after proxy repair | 17 | 0 | 0 | passed |
| Workflow YAML parse after proxy repair | 1 | 0 | 0 | passed |
| Packaging/workflow/self-hosted relevant suite after proxy repair | 54 | 0 | 0 | passed |
| Windows Miniforge tool-volume contract RED | 0 | 1 | 0 | expected failure before workflow change |
| Wheel workflow module after Miniforge path repair | 18 | 0 | 0 | passed |
| Packaging/workflow/self-hosted relevant suite after Miniforge path repair | 55 | 0 | 0 | passed |

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

### Replacement run and balanced runner optimization 2026-08-21

- Replacement run `32433373707` proved both Linux wheel lanes and all six hosted Ubuntu clean-install jobs pass at `ea1e3627f841b124842d1e9bc0d2f3a740128693`.
- Windows ISIS 10 successfully built and verified ISIS 10.0.0, then wheel staging failed on six unclassified Windows SDK DLL imports. A focused RED test reproduced all six; the system-DLL allowlist repair is GREEN.
- Removed workflow-level `-Jobs 2`; Windows now uses its script default of `min(24, ProcessorCount)` (16 on this workstation).
- Changed shared Linux runner profiles to `build_jobs: auto`; reusable builds and wheel builds compute `min(24, available logical processors)` at run time.
- Linux wheel build jobs now default to `pyisis-ubuntu26`, retain the manylinux container, and reuse a 20 GB local ccache plus ISIS-version-specific scikit-build trees. Hosted Ubuntu clean-install jobs remain unchanged.
- Windows self-hosted jobs now use fingerprinted local ISIS 9/10 prefixes below the runner tool cache. Hosted `windows-2022` jobs retain GitHub Actions prefix restore/save behavior.
- Verification passed: YAML parsing, Bash syntax, `git diff --check`, the 50-test packaging/workflow/self-hosted suite, and five focused Windows PE closure tests.
- A broad local invocation of the entire cross-platform runtime module reached four Linux-only fixture errors because Windows lacks `ldd`/`readelf`; the Windows PE-focused cases passed and the hosted Linux lanes were already green remotely.
- GitHub rejected the first optimized dispatch at commit `0754f87f` before creating a run because the `runner` context is unavailable in job-level `env`. Cache paths now resolve from `RUNNER_TOOL_CACHE` inside runner shell steps and flow through `GITHUB_ENV`.
- Run `32436286625` reached `pyisis-ubuntu26`, but both manylinux jobs failed before checkout with `docker: command not found`. The replacement workflow probes Docker command/daemon access on the requested runner and automatically selects hosted `ubuntu-24.04` when the self-hosted machine cannot launch job containers.
- Run `32436488892` proved the Linux capability fallback works, then the Windows ISIS 10 self-hosted job stalled in `actions/checkout@v7`. The run was cancelled so its serial Windows runner slot could be reused.
- Added job-level `HTTP_PROXY` and `HTTPS_PROXY` for both Windows wheel jobs, conditional on the self-hosted scope output, with `NO_PROXY` for localhost. The focused contract was RED before the edit and the complete 17-test workflow module is GREEN afterward; YAML parsing and `git diff --check` also pass.
- One combined local validation wrapper timed out after the 17 tests had already reported `OK`; the remaining YAML and whitespace checks were rerun separately and passed immediately.
- An over-broad 59-test command also included five Linux account-setup shell tests that cannot decode Git Bash output under the Windows GBK locale; those five failed in the subprocess reader before assertions. They do not cover this workflow edit. The intended four-module packaging/workflow/self-hosted suite was rerun separately and passed 54/54.
- Run `32437219483` confirmed checkout now succeeds, then both Windows jobs failed extracting Miniforge into the SYSTEM profile on C:. Added the action-supported `installation-dir` input pointing at `${{ runner.tool_cache }}\pyisis-miniforge3`; focused contract was RED first, then the complete workflow module passed 18/18 with YAML and whitespace checks also passing.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | M08 second repair and runner-performance phase after run `32433373707`. |
| Where am I going? | Tested repair followed by fresh four-lane evidence. |
| What's the goal? | Revalidate wheels without publishing a release. |
| What have I learned? | Linux is now remotely green; Windows ISIS compilation dominates cache misses, and runtime staging must explicitly classify OS-owned DLLs. |
| What is next? | Commit and push the repaired/optimized SHA, then dispatch the non-publishing matrix on both dedicated self-hosted build runners. |
