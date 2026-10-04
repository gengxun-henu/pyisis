# Task Plan: Spice / OSIRIS-REx compatibility audit (M21)

## Goal
Confirm Spice core APIs and OSIRIS-REx camera bindings preserve expected Python hierarchy and versioned signatures on ISIS 9 and ISIS 10.

## Next Step
Run focused Spice and OSIRIS-REx tests plus smoke imports, then publish the PR.

## Current Phase
Phase 4

## Phases
### Phase 1: Requirements & Discovery
- [x] Identify Spice and OSIRIS-REx binding/test surfaces
- [x] Record versioned signature coverage
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Select hierarchy assertions that do not require mission kernels
- **Status:** complete
### Phase 3: Implementation
- [x] Add camera-to-base hierarchy assertions
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
| Keep kernel-independent assertions | The repository already has extensive Spice lifecycle tests; hierarchy checks isolate binding regressions without requiring additional kernel data. |
