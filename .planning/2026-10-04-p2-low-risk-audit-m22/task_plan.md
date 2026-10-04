# Task Plan: P2 low-risk binding audit (M22)

## Goal
Close a measured audit of low-risk Math, PolygonSeeder, Statistics, and Support bindings without claiming unverified API completeness.

## Next Step
Run the grouped tests on ISIS 9 and ISIS 10, then publish the evidence record.

## Current Phase
Phase 4

## Phases
### Phase 1: Requirements & Discovery
- [x] Identify remaining low-risk binding groups and focused tests
- [x] Define evidence boundary
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Select grouped regression suite
- **Status:** complete
### Phase 3: Implementation
- [x] Prepare audit records
- **Status:** complete
### Phase 4: Testing & Verification
- [ ] Run both ISIS versions and smoke imports
- [ ] Record results
- **Status:** in_progress
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|---|---|
| Report tested surfaces only | The expansion policy requires every discovered item to be classified; this milestone records verified groups without inferring that all P2 APIs are complete. |
