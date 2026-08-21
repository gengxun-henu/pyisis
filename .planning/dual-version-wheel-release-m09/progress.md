# Progress: Dual-version wheel release (M09)

## Session: 2026-08-21

- Created the standalone M09 planning directory after verifying the canonical milestone registry.
- Preserved the immutable completed M06 registry and classified standalone M07/M08 planning as outside that registry.
- Confirmed M09 starts from merged `main` commit `addb839dc0b2622931926c60265c6c47aedd650f` and successful non-publishing run `32447419640`.

## Changed Files

- `.planning/dual-version-wheel-release-m09/task_plan.md`
- `.planning/dual-version-wheel-release-m09/findings.md`
- `.planning/dual-version-wheel-release-m09/progress.md`

## Commands and Evidence

- `verify_milestones.py --repo D:\code\pyisis\pyisis` — passed.
- `session-catchup.py D:\code\pyisis\pyisis` — no unsynced catch-up content reported.
- Inspected `.github/workflows/wheels.yml`, package-version references, remote tags, and GitHub releases.
- Confirmed the current rc2 ISIS 9 and ISIS 10 releases/tags already exist, while the workflow refuses release replacement.
- `D:/pyisis-conda/envs/isis9-v3/python.exe -m unittest <8 packaging modules> -v` — 124 run, 120 passed, 4 errors; all four errors are Linux staging tests invoking unavailable `ldd`/`readelf` on Windows, not version-contract failures.
- `D:/pyisis-conda/envs/isis9-v3/python.exe -m unittest <7 release-contract modules> -v` — 102 passed, 0 failed, 0 skipped.
- Parsed `.github/workflows/wheels.yml` with PyYAML and both release manifests with `tomllib`; both rc3 identities and release-note paths verified.
- `gh release view` confirmed both rc3 tags are available; `git diff --check` passed.
- Created branch `release/m09-dual-version-rc3` from merged `main`.
- Mechanically updated current build/package/release contracts and tests from rc2 to rc3 while excluding historical plans/specs and archived rc2 notes.
- Added new ISIS 9 and ISIS 10 rc3 release notes describing the validated M08 changes and supported matrices.

## Git Classification

- Pre-existing guarded modification: `print.prt`; untouched and excluded from all staging.
- M09 planning files are current-milestone changes.

## Reboot Check

- **Where am I?** Phase 2, publishing the verified release contract and dispatching releases.
- **Where am I going?** Publish and independently verify the dual-version release.
- **Goal?** A verified GitHub release with retained hashes and install evidence.
- **What have I learned?** The canonical registry cannot safely own M09; successful M08 evidence exists at run `32447419640`.
- **Next step?** Commit, PR, and merge the rc3 release contract, then dispatch ISIS 9 first.
