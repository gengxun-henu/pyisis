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

## Evidence-Based Inference

- None recorded.

## Unresolved Items

- Completion evidence has not yet been produced.
- The Task 1 source-contract tests do not replace the real clean-wheel installation scheduled for Task 4.
- Task 3 must freshly verify the exact prerequisite hashes before building retained artifacts.

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
