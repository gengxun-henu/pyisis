# Findings & Decisions

## Requirements
- Audit the public ShapeModel hierarchy and Target shape factory behavior across ISIS 9 and ISIS 10.
- Verify concrete factories return ShapeModel-compatible objects, optional Embree behavior remains conditional, and surface-point lifecycle tests remain green.
- Keep the change focused on evidence and compatibility; do not add speculative bindings.

## Research Findings
- `src/base/bind_base_shape.cpp` already binds the ShapeModel hierarchy, including EllipsoidShape, DemShape, PlaneShape, NaifDskShape, optional EmbreeShapeModel, and BulletShapeModel.
- `src/base/bind_base_target.cpp` already exposes target shape factories and surface-point lifecycle methods.
- Existing target and shape support tests pass on both active build trees: 12 passed, 1 skipped per version.
- The new audit asserts every available factory result is an `ip.ShapeModel` and retains the optional Embree guard.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Test-only compatibility milestone | The active conda APIs and current bindings already satisfy the intended contract; adding C++ without a demonstrated gap would increase risk. |
| Preserve conditional Embree coverage | The class is optional by build configuration and is already skipped when unavailable. |

## Issues Encountered
| Issue | Resolution |
|-------|-----------|
| First ISIS 10 invocation imported the ISIS 9 extension | Corrected environment selection with `ISIS_PYBIND_BUILD_DIR` and a version-specific `PYTHONPATH`; the rerun passed. |

## Resources
- `src/base/bind_base_shape.cpp`
- `src/base/bind_base_target.cpp`
- `tests/unitTest/target_shape_unit_test.py`
- `tests/unitTest/shape_support_unit_test.py`
