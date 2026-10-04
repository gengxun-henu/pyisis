# Task Plan: Windows APP Wave 0–1 audit (M25)

## Goal
Turn the existing Windows APP Wave 0–1 roadmap into an evidence-backed implementation baseline.

## Next Step
Carry the manifest and smoke-tier evidence into Wave 2–4 planning.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Read the Windows APP roadmap and manifest schema
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Identify Wave 0/1 anchor apps and release constraints
- **Status:** complete
### Phase 3: Implementation
- [x] Record current manifest evidence
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Validate manifest structure and anchor entries locally
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Keep native APP packaging separate from PyISIS wheels | Existing roadmap and package tests require standalone launchers, XML, and runtime closure. |
