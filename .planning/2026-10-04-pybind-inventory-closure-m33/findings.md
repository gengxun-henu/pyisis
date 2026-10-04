# Findings & Decisions

## Requirements
- Reconcile planning status with the actual compatibility ledger.
- Preserve the distinction between local Linux closure and runner-dependent Windows ABI closure.

## Research Findings
- `reference/compatibility/isis9-isis10-binding-review.csv` contains 77 rows and all 77 have `status=closed`.
- The ledger classifications cover shared, wrapped, version-gated, renamed, and ISIS 10-only cases with no open row.
- The focused inventory/API/install comparison suite under `asp370` passes 16 tests with 1 designed skip.
- The remaining unresolved item is Windows DLL/import-library export verification, already tracked in the release gate.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Update only stale planning status | The binding work is already implemented and tested; duplicating code changes would add risk. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Expansion plan still described the compatibility queue as in progress | Updated it to `complete_for_local_linux` and retained the Windows ABI boundary. |
