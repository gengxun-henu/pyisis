# Task Plan: GitHub-hosted dual-version release matrix (M36)

## Goal
Validate the full ISIS 9/10 Linux and Windows wheel matrix on GitHub-hosted runners while self-hosted infrastructure is unavailable.

## Next Step
Use the retained artifacts and reports to prepare a formal release dispatch when publication is authorized.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Confirm workflow supports GitHub-hosted Linux and Windows runners
- [x] Disable publication for the validation run
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Select `ubuntu-24.04` and `windows-2022`
- **Status:** complete
### Phase 3: Implementation
- [x] Dispatch the complete matrix
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Verify all build and clean-install jobs
- [x] Record artifact names and run identity
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Keep GitHub Release publication disabled | The matrix must be reviewed as evidence before any irreversible tag/asset publication. |
