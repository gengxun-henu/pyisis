# Windows PyISIS ISIS 9 Wheelhouse Milestone

# Findings: Build and release-validate the Windows PyISIS wheelhouse

## Verified Facts

- Milestone ID: `windows-isis9-m04-wheelhouse`.
- Prior M01-M03 state and evidence are preserved under `.planning/archive/windows-isis9-native-build-m01-m03/`.
- Active implementation worktree: `.worktrees/m04-windows-pyisis-wheelhouse` on branch `feature/m04-windows-pyisis-wheelhouse`.
- The verified ISIS 9 prefix is available at `build/windows/isis-prefix` through an ignored junction to the repository-root artifact.
- `D:/pyisis-win-env/python.exe` and the mock LSK prerequisite are present.
- Task 1 added a passed-only JSON evidence contract to `tools/packaging/test_wheel_install.py`; subprocess failures remain uncaught and cannot write a new passed report.
- Task 2 added strict exact-wheel, payload-boundary, dependency-closure, clean-install-check, and SHA-256 validation in `tools/packaging/validate_windows_wheelhouse.py`.
- The existing adjacent unresolved-runtime regression is named `test_stage_runtime_closure_reports_unresolved_dependency`; the implementation plan's alternative name does not exist.
- Windows `dumpbin` returned success and parseable DLL names, but Python's default GBK text decoding failed first on byte `0xA5`; dependency scanning therefore needs an explicit tolerant decoding policy at both dumpbin call sites.
- Task 3 produced the exact three-wheel CPython 3.12/Windows artifact set; the runtime dependency report has `unresolved=0`.
- Final Task 3 retained-input hashes: binding `8f1a923e62c12e98041bd7a5eebdffaaf00858597747cd9d4d690393451dcc00`; runtime `1d51ad225a238d70b6accc56989023ca9dbe7401e74f6dd62153c5c55e0556bf`; minimal data `43009899a9586e90bb2cbc042233f37c77c4f68fbf0d6036a5179bd1549388b5`; dependency JSON `fceb4b3b943530a53df3ef9fea684170ac9df1e3452e148f3703f5b79108a842`.
- The canonical runtime member is `pyisis_runtime/vendor/isis/lib/isis.dll`; the stager preserves prefix-relative layout and the runtime package explicitly registers `vendor/isis/lib` as a DLL directory.
- Task 4's isolated offline install passed all 11 recorded checks and reported package `1.3.0rc2` with ISIS `9.0.0` before final validator correction.
- Task 4 final validation passed with four retained-input hashes, exact three-wheel set, canonical runtime payload, no APP payload, and `unresolved=0`.
- The clean-install venv, runtime staging directory, and generated minimal-data egg-info were removed after evidence verification; wheelhouse and reports were retained.
- Task 5 documented the exact build/install commands, three wheel names, report paths, and the boundary excluding standalone ISIS APP executables/XML.
- Final Windows-focused source gate passed 51/51 with no warnings; both retained reports remain passed.
- Final hardening commit `9083f186` binds evidence to exact wheel bytes, enforces isolated pip/origins, truthful strict checks, canonical ZIP members/all-wheel APP exclusion, and dependency-report schema.
- Fresh controller verification passed 65/65 focused source tests, then a clean offline install recorded 330 passed, 0 failed, 0 skipped, and 1 expected failure across 11 checks.
- Fresh final validation passed with four matching retained hashes and `unresolved=0`; the disposable verification venv was removed again.

## Evidence-Based Inference

- None recorded.

## Unresolved Items

- None.

## Decisions

| Decision | Rationale |
|---|---|
| Keep M04 as the only canonical active milestone | The completed M01-M03 lifecycle is immutable archived evidence; M04 has its own completion contract. |
| Keep M05 out of the active registry until M04 closes | M05 product-format and APP-inventory decisions require a separate design session after the wheelhouse is complete. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- Archived registry: `.planning/archive/windows-isis9-native-build-m01-m03/milestones.v1.json`
- Design: `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md`
- Implementation plan: `docs/superpowers/plans/2026-08-16-windows-pyisis-wheelhouse.md`
