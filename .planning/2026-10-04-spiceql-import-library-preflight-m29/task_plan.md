# Task Plan: SpiceQL import-library preflight (M29)

## Goal
Catch a mismatched Windows SpiceQL import library before the ISIS `mgs.dll` link stage.

## Next Step
Run the enhanced preflight on the Windows runner and compare its symbol output with the ISIS link command.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Trace the historical unresolved-symbol failure
- [x] Confirm the existing DLL export and downstream link checks
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Add an import-library-specific check
- **Status:** complete
### Phase 3: Implementation
- [x] Update the PowerShell preflight and regression test
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run the packaging-tool unit test on Linux
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Inspect `SpiceQL.lib` with `dumpbin /linkermember:2` | The failure is an unresolved import-library symbol during `mgs.dll` linking, so a DLL-only export check is insufficient. |
