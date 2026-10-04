# Findings & Decisions

## Requirements
- Make stale submodule metadata visible before checkout.
- Preserve the existing optional strict-failure behavior.

## Research Findings
- Recent self-hosted logs report an invalid `.deps/opencv-cuda/src/opencv` submodule mapping before the build starts.
- The manual runner sanity workflow already gathers git/SSH diagnostics and supports `fail_on_findings`.
- The new check records workspace submodule status and marks invalid metadata as a finding; it does not delete files or change ownership.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Diagnose, do not auto-delete | Permission failures make destructive cleanup unsafe; the runner owner should repair or recreate the workspace. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| YAML parser is not installed in the Linux environment | Used targeted workflow regression tests and `git diff --check`; GitHub Actions remains the authoritative syntax/runtime check. |
