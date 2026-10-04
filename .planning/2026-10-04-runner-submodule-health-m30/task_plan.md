# Task Plan: self-hosted runner workspace health (M30)

## Goal
Expose stale submodule metadata before checkout so runner failures are diagnosable and strict sanity checks can stop early.

## Next Step
Run the manual runner sanity workflow with strict findings after correcting workspace ownership.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Inspect recent self-hosted checkout failures
- [x] Locate the runner sanity workflow
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Add workspace submodule diagnostics without altering build behavior
- **Status:** complete
### Phase 3: Implementation
- [x] Flag invalid `git submodule status` as a runner finding
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run workflow policy regression tests and diff checks
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress
