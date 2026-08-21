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
- PR #372 merged the rc3 release contract to `main` as `977b106c9321f2154684f1a8fa10e0e72b9d1229`.
- Formal ISIS 9 run `32474949786` completed successfully and published `v1.3.0rc3-isis9.0.0`.
- Formal ISIS 10 run `32477095364` completed successfully and published `v1.4.0rc3-isis10.0.0`.
- Both runs passed four platform/version build lanes and six Ubuntu clean-install jobs before their release jobs executed.
- Downloaded all four published ZIP assets; each SHA-256 matched its release checksum and GitHub digest.
- Published Windows ISIS 9 install report: 330 passed, 0 failed, 0 skipped, 1 expected failure; report SHA-256 `77b058693d4dec4fa539a48f0ccd73e6cbd2def72ef4b116e57ac63ddd7a0214`.
- Published Windows ISIS 10 install report: 330 passed, 0 failed, 0 skipped, 1 expected failure; report SHA-256 `48c427d9cc1418dce0d3751a50820b4ef46920340543626685b3106bd0b44517`.
- Temporary downloaded ZIPs, extracted wheelhouses, venvs, logs, and reports are under `D:\actions-runner-pyisis\_work\_temp\m09-release-verify` and are disposable after this evidence commit.

## Git Classification

- Pre-existing guarded modification: `print.prt`; untouched and excluded from all staging.
- M09 planning files are current-milestone changes.

## Reboot Check

- **Where am I?** M09 complete.
- **Where am I going?** No remaining M09 work.
- **Goal?** A verified GitHub release with retained hashes and install evidence.
- **What have I learned?** Sequential full-matrix runs safely published both release lines; downloaded public assets reproduce their declared digests and install cleanly on Windows.
- **Next step?** None for M09; Linux runner Docker maintenance is separate.
