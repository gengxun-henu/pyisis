# Task Plan: CI release-gate hardening (M35)

## Goal
Strengthen static workflow checks so a Release cannot silently soften platform failures or omit the Windows ISIS 10 SpiceQL preflight.

## Next Step
Use the hardened workflow contract when the Windows runner is restored.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Inspect release job dependencies and Windows ISIS 10 steps
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Define failure-policy and preflight assertions
- **Status:** complete
### Phase 3: Implementation
- [x] Add workflow regression tests
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run wheel workflow unit tests and diff checks
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress
