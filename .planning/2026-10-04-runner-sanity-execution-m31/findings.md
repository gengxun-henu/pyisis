# Findings & Decisions

## Requirements
- Execute the strict runner sanity workflow after M30.
- Preserve the exact run evidence needed for the Windows build gate.

## Research Findings
- Run `37190432546` completed on `main` with failure as expected under `fail_on_findings=true`.
- The runner reported `HEAD is missing` for `/opt/actions-runner-pyisis/_work/pyisis/pyisis` and entered stale-workspace self-heal.
- The new M30 check reported invalid or stale submodule metadata before checkout.
- The job stopped before checkout probe completion, so the runner workspace must be repaired before another build attempt.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Treat this as a confirmed infrastructure blocker | The failure is now reproduced on the actual self-hosted runner, independently of source compilation. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Missing HEAD and stale submodule state | Requires runner-side workspace recreation or ownership repair; do not mask it in the workflow. |
