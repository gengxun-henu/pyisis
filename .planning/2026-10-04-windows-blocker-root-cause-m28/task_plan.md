# Task Plan: Windows release blocker root-cause audit (M28)

## Goal
Turn the Windows ISIS 10 linker and self-hosted checkout failures into actionable, bounded follow-up items.

## Next Step
Apply the remediation on a Windows runner, then rerun the release matrix.

## Current Phase
Phase 5

## Phases
### Phase 1: Requirements & Discovery
- [x] Inspect the Windows SpiceQL build script and patch
- [x] Inspect self-hosted checkout workflow and recent CI logs
- **Status:** complete
### Phase 2: Planning & Structure
- [x] Separate dependency ABI diagnosis from runner hygiene
- **Status:** complete
### Phase 3: Implementation
- [x] Record remediation hypotheses and validation commands
- **Status:** complete
### Phase 4: Testing & Verification
- [x] Confirm exact historical error signatures
- **Status:** complete
### Phase 5: Delivery
- [ ] Commit, PR, merge, and sync local main
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|---|---|
| Do not patch ISIS or SpiceQL blindly from Linux | The unresolved symbol and Windows import-library selection must be inspected with MSVC `dumpbin` on the target runner. |
| Treat runner cleanup as a separate fix | Checkout permission/submodule failures happen before the build and can mask source-level results. |
