# Findings & Decisions

## Requirements
- Audit Wave 2–4 manifest scope for Windows ISIS applications.
- Keep geometry, SPICE, and control-network anchors explicit.

## Research Findings
- The manifest has 150 entries: Wave 1 has 48, Wave 2 has 3, Wave 3 has 77, Wave 4 has 1, and 21 entries have no wave label.
- Wave 2 anchors are `spiceinit`, `cam2map`, and `pointreg`.
- Wave 3 contains the broad general/task import and processing queue.
- Wave 4 currently contains `csv2table`, whose Python/in-process exception path was addressed in the earlier milestone history.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Use manifest counts as the scope baseline | The Windows roadmap requires an explicit allowlist and prevents default all-app scans. |
| Defer executable claims to Windows CI | Linux can validate inventory, but not Windows PE closure or clean extraction. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Windows executable validation unavailable locally | Keep this as a scope audit and retain the M23/M24 build gate. |
