# Findings & Decisions

## Requirements
- Audit CameraFactory and ProjectionFactory return types across ISIS 9 and ISIS 10.
- Preserve existing camera-backed and projection-backed UniversalGroundMap coverage.

## Research Findings
- Camera hierarchy and camera maps already have broad focused coverage in `camera_unit_test.py`, `camera_maps_unit_test.py`, and `universal_ground_map_unit_test.py`.
- ProjectionFactory has stable label-based construction paths; the new checks explicitly require `ip.Projection` results.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Add only base-class assertions | This directly detects binding inheritance regressions without changing runtime behavior. |

## Issues Encountered
| Issue | Resolution |
|---|---|

## Resources
- `src/bind_camera_factory.cpp`
- `src/bind_camera_maps.cpp`
- `src/base/bind_base_projection.cpp`
- `tests/unitTest/camera_unit_test.py`
- `tests/unitTest/projection_unit_test.py`
- `tests/unitTest/universal_ground_map_unit_test.py`
