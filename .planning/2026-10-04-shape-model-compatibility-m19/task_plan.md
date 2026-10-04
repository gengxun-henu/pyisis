# Task Plan: Shape / Target compatibility audit (M19)

## Goal
Confirm that the ShapeModel hierarchy, target shape factories, and surface-point lifecycle expose stable Python behavior on ISIS 9 and ISIS 10.

## Next Step
Run the focused dual-version tests and smoke imports, then publish the audit PR.

## Current Phase
Phase 4

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints
- [x] Document in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define approach
- [x] Create project structure
- **Status:** complete

### Phase 3: Implementation
- [x] Execute the plan
- [x] Write to files before executing
- **Status:** complete

### Phase 4: Testing & Verification
- [ ] Verify requirements met
- [ ] Document test results
- **Status:** in_progress

### Phase 5: Delivery
- [ ] Review outputs
- [ ] Deliver to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Keep the existing shared ShapeModel facade | Both active ISIS prefixes already expose the required hierarchy and factory behavior; no version-specific C++ change is justified. |
| Test optional Embree conditionally | Embree bindings are build-dependent and must not make the cross-version audit brittle. |

## Errors Encountered
| Error | Resolution |
|-------|-----------|
| Initial ISIS 10 test used the default ISIS 9 build directory | Re-ran with `ISIS_PYBIND_BUILD_DIR=build-isis10/python` and the correct `PYTHONPATH`. |
