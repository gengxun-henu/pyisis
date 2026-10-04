# Task Plan: Camera / Projection / Map compatibility audit (M20)

## Goal
Confirm camera and projection factories preserve their Python base-class relationships on ISIS 9 and ISIS 10.

## Next Step
Run focused camera, projection, map, and smoke validation, then publish the PR.

## Current Phase
Phase 4

## Phases
### Phase 1: Requirements & Discovery
- [x] Identify camera, projection, and ground-map bindings and existing tests
- [x] Record version and optional-feature constraints
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Select low-risk factory return-type assertions
- **Status:** complete
### Phase 3: Implementation
- [x] Add focused ProjectionFactory compatibility assertions
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
| Keep this milestone test-only | Existing camera, map, and projection bindings already expose the needed APIs; the remaining risk is cross-version return-type drift. |
