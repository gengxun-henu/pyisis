# Task Plan: Pybind inventory closure (M33)

## Goal
Close the local Linux-side Pybind compatibility inventory and reconcile stale planning text with the completed ledger.

## Next Step
Carry only Windows DLL/import-library validation into the runner-dependent release gate.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Inspect the compatibility ledger and current expansion plan
- [x] Identify stale pending statements
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Define the local versus Windows closure boundary
- **Status:** complete
### Phase 3: Implementation
- [x] Update the expansion plan to reflect the closed local ledger
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run inventory, API audit, and installation comparison tests
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Mark the 77-row Linux compatibility ledger complete | Every row is already `closed`; only Windows DLL/import-library evidence remains externally blocked. |
