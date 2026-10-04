# Findings & Decisions

## Requirements
- Audit Spice navigation and OSIRIS-REx camera bindings across ISIS 9 and ISIS 10.
- Preserve the existing ISIS-major-specific `set_distortion` signature checks.

## Research Findings
- `spice_navigation_unit_test.py` covers constructor, cache, polynomial, coordinate, and enum APIs without external kernel setup.
- OSIRIS-REx OCAMS and TAGCAMS tests already cover importability, distortion-map inheritance, methods, and ISIS 10 signature differences.
- Camera classes should explicitly remain both `FramingCamera` and `Camera` subclasses.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Add only base hierarchy assertions | This verifies pybind inheritance metadata and has no runtime side effects. |

## Issues Encountered
| Issue | Resolution |
|---|---|

## Resources
- `src/bind_spice_navigation.cpp`
- `tests/unitTest/spice_navigation_unit_test.py`
- `tests/unitTest/osirisrex_camera_unit_test.py`
