# Task Plan: Linux dual-version release evidence (M32)

## Goal
Complete the Linux-side release evidence and packaging-contract audit while Windows execution remains unavailable.

## Next Step
Use the validated contracts and reports as inputs for the eventual Windows matrix rerun.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Locate Linux wheel build, ABI audit, and wheelhouse validator tools
- [x] Identify environment limitations
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Select reproducible local packaging test suite
- **Status:** complete
### Phase 3: Implementation
- [x] Record Linux release evidence
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run validator, ABI, policy, workflow, and packaging tests
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Do not claim a new ISIS 9 wheel build | `asp360_new` lacks `scikit_build_core`; creating an artifact would require changing the managed environment or using an unverified toolchain. |
