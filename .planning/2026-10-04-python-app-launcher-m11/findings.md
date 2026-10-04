# Findings: PyISIS Python app launcher integration (M11)

## Verified Facts

- `python/pyisis/apps.py` implements `run(name, *args, env=None, cwd=None, check=True, capture_output=False)`.
- `CMakeLists.txt` synchronizes and installs `apps.py`; README and focused tests cover the public contract.
- Local full suite previously passed 2726 tests with 52 skipped and 1 expected failure.
- PR #383 passes Linux cp312/cp313 wheel builds, Linux install smoke, metadata audit, and cross-Ubuntu tests.
- PR #383 self-hosted ISIS 9/10 gates fail before checkout completes because stale files under the runner workspace cannot be removed due to permissions.
- PR #383 Windows wheel jobs remain queued because no online Windows runner is registered.
- The canonical M06 registry is currently unverifiable because its required ignored ZIP artifact is absent from the workspace.

## Evidence-based Inference

- `actions/checkout` default cleanup is the direct trigger for the self-hosted failure; disabling only that cleanup should allow the runner to proceed while preserving later build cleanup.

## Unresolved Items

- Whether the repository's Windows runner will return before PR merge.
- Full local validation after the workflow change: 2727 tests, 0 failures, 52 skipped, 1 expected failure; smoke import passed.
- Whether the self-hosted runner can build successfully after checkout cleanup is disabled.
- Restoration of the historical M06 ZIP needed for canonical registry verification.

## Decisions

- Keep this milestone standalone because the existing canonical registry contains an immutable completed milestone and no supported append-milestone command; do not hand-edit that registry.
- Treat missing M06 evidence as a separate legacy issue, not as a reason to alter the new feature's completion evidence.
