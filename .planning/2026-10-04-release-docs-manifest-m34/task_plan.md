# Task Plan: Release documentation and artifact manifest (M34)

## Goal
Create one current release-readiness document covering matrix state, artifact identity, installation boundaries, and blockers.

## Next Step
Use the document as the checklist for M35 CI dry-run hardening and M36 Windows release execution.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Compare existing release notes and install guides
- [x] Identify stale or distributed release-gate information
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Define a single matrix and artifact identity checklist
- **Status:** complete
### Phase 3: Implementation
- [x] Add `docs/releases/release-readiness.md`
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Run packaging contract tests from M32
- [x] Run `git diff --check`
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress
