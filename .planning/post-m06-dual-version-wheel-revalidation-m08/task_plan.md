# Task Plan: Post-M06 dual-version wheel revalidation (M08)

## Goal

Validate and repair current HEAD across Linux/Windows × ISIS 9/10 wheels without publishing a release.

## Scope

- Execute only the approved workflow and collect its current-HEAD evidence.
- Diagnose the failed M08 run, implement the smallest tested repair authorized by the user, and revalidate without publishing.
- Apply the approved balanced self-hosted performance design without weakening clean-host portability gates.

## Dependencies

- M06 is complete.
- M07 reconciliation is recorded in `.planning/release-evidence-reconciliation-m07/`.

## Completion Gate

Four successful workflow lanes with retained hashes, install/import/test evidence, and no release publication.

## Next Step

Commit and normally push the tested repair, freeze its exact SHA, then dispatch one replacement `wheels.yml` run using both dedicated self-hosted build runners, `release_line=isis10`, `publish_testpypi=false`, and `publish_github_release=false`.

## Current Phase

Phase 2: Diagnose and repair failed validation

## Phases

### Phase 1: Freeze inputs

- [x] Record exact HEAD and classified Git state.
- [x] Run workflow contract tests.
- [x] Record four-lane workflow-job mapping.
- **Status:** completed 2026-08-20

### Frozen workflow-job mapping

| Required lane | Committed `wheels.yml` job ID(s) |
|---|---|
| `linux-isis9` | `linux-cp312-build`, `linux-cp312-clean-install` |
| `linux-isis10-cp313` | `linux-isis10-cp313-build`, `linux-isis10-cp313-clean-install` |
| `windows-cp312` | `windows-cp312` |
| `windows-isis10-cp313` | `windows-isis10-cp313` |

### Phase 2: Dispatch and monitor

- [x] Push the frozen commit normally and dispatch `wheels.yml` at that ref with `release_line=isis10`, `publish_testpypi=false`, and `publish_github_release=false`.
- [x] Record workflow run `32373382592` and its job outcomes.
- [x] Repair deterministic Linux metadata validation and Windows bootstrap/network resilience with focused tests (35 passed).
- [x] Diagnose replacement run `32433373707`: Linux passed; Windows ISIS 10 failed because six Windows SDK DLLs were missing from the system-DLL allowlist.
- [x] Implement the approved runner optimization: runtime `min(24, logical processors)`, Linux ccache/scikit-build reuse, and fingerprinted Windows local prefix reuse.
- [ ] Dispatch and monitor a replacement non-publishing run.
- **Status:** in progress

### Phase 3: Evidence and outcome

- [ ] Retain four-lane hashes and report a non-publishing readiness decision.
- **Status:** pending

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Run `32373382592`: six Linux clean-install jobs failed | 1 | Replaced hard-coded distribution names with package-derived expectations plus explicit additional runtime distributions; regression passed. |
| Run `32373382592`: Windows cp312 setup-python failed | 1 | Removed the redundant Windows `setup-python`; conda environment supplies the target interpreter. |
| Run `32373382592`: Windows cp313 checkout failed | 1 | Replacement validation will use supported GitHub-hosted `windows-2022`; self-hosted network remediation remains operational, outside product code. |
| Run `32433373707`: Windows ISIS 10 runtime staging rejected six SDK DLLs | 2 | Classified `authz.dll`, `d3d12.dll`, `dwrite.dll`, `odbc32.dll`, `psapi.dll`, and `winhttp.dll` as Windows system dependencies; focused regression passes. |
| Dispatch at `0754f87f`: workflow parser rejected `runner.tool_cache` in job-level `env` | 3 | Resolve `RUNNER_TOOL_CACHE` inside runner shell steps and export derived paths through `GITHUB_ENV`; no workflow run was created. |
| Run `32436286625`: Linux self-hosted jobs failed at setup | 4 | Runner log proved `docker: command not found`; add a capability probe that falls back to hosted Ubuntu while preserving the manylinux container and future automatic self-hosted enablement. |
| Run `32436488892`: Windows self-hosted checkout stalled | 5 | Runner diagnostics showed the checkout Node process remained active while direct GitHub traffic was unreliable; route all Windows self-hosted job bootstrap traffic through the workstation proxy, leaving hosted fallback proxy values empty. |
| Run `32437219483`: both Windows Miniforge installations failed during package extraction | 6 | Checkout succeeded through the job proxy, isolating the next failure. `setup-miniconda` selected the service account's system-profile directory on C:, while the runner tool cache is on capacious D:. Pin `installation-dir` to `${{ runner.tool_cache }}\pyisis-miniforge3` for both Windows jobs. |
| Run `32437828115`: Miniforge installer also failed extracting on D: | 7 | The installation-volume hypothesis was disproved. Use setup-miniconda's documented bundled-Conda path on the self-hosted runner by supplying the preinstalled `C:\Users\gx\miniconda3` and an empty Miniforge version; keep latest Miniforge installation for hosted Windows. |
| Run `32438209261`: conditional empty Miniforge version evaluated to `latest` | 8 | GitHub's `condition && value || fallback` idiom cannot select a falsy empty string. Replace it with two explicit, mutually exclusive setup-miniconda steps for self-hosted bundled Conda and hosted Miniforge. |
| Run `32438639372`: bundled Conda selected, then `conda init` failed | 9 | The service account cannot persist all user shell initialization changes. CI uses explicit interpreter paths, so disable `run-init` only for the self-hosted bundled-Conda steps. |
