# Findings & Decisions

## Requirements
- Add explicit `__iter__` to both bundle vector classes without changing existing indexing behavior.
- Keep the API shared between ISIS 9 and ISIS 10.
- Do not expose Qt iterator types or raw ownership.

## Research Findings
- Both classes already expose `__len__` and bounds-checked `__getitem__`.
- Python currently falls back to sequence iteration, but `hasattr(instance, "__iter__")` is false.
- `BundleObservationVector::operator[]` and `BundleLidarPointVector::operator[]` return shared-pointer types suitable for a Python snapshot list.
- RED test confirmed `hasattr(vector, "__iter__")` was false before the binding change.
- Both ISIS 9 and ISIS 10 builds accepted the snapshot iterator implementation.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
-| | |
| Use a small helper lambda per class | The two ISIS vector types have different pointer aliases; explicit lambdas keep type conversion clear. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
