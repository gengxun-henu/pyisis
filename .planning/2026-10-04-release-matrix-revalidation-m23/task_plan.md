# Task Plan: Release matrix revalidation (M23)

## Goal
Revalidate the dual-version release matrix and record the exact CI blockers before any formal release claim.

## Next Step
Publish the matrix evidence and carry the external CI blockers into M24 release gating.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Inspect current release workflow and historical matrix
- [x] Identify Linux, Windows, ISIS 9, and ISIS 10 results
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Define release gate evidence and blocker record
- **Status:** complete
### Phase 3: Implementation
- [x] Record revalidation report
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Inspect latest CI failure details
- [x] Compare historical wheel matrix results
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Do not publish a stable dual-version release yet | The ISIS 10 Windows wheel lane still fails at the upstream `mgs.dll` link stage. |
| Keep M24 release work gated | Linux ISIS 9/10 and Windows ISIS 9 evidence is green in run `30066283510`; Windows ISIS 10 remains unresolved. |
