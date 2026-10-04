# Findings & Decisions

## Requirements
- Validate Linux release tooling independently of the unavailable Windows runner.
- Preserve accurate boundaries between contract tests and produced artifacts.

## Research Findings
- The repository contains working validators for Windows wheelhouse boundaries and Linux ABI/auditwheel policy.
- ISIS 10 (`asp370`) provides `build`, `pybind11`, `scikit_build_core`, and `wheel`; the ISIS 9 (`asp360_new`) environment lacks `scikit_build_core`.
- The combined Linux packaging contract suite passes under `asp370`.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Record contract evidence, not unbuilt wheel artifacts | The release policy requires artifact hashes and matrix identity; no new artifact was generated in this milestone. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| `asp360_new` missing `scikit_build_core` | Keep the result as a tooling limitation and retain existing build outputs; do not introduce pip installation. |

## Resources
- `tools/packaging/build_wheels_linux.sh`
- `tools/packaging/audit_linux_wheelhouse.py`
- `tools/packaging/validate_windows_wheelhouse.py`
- `tests/unitTest/windows_wheelhouse_validation_unit_test.py`
- `tests/unitTest/linux_wheel_audit_unit_test.py`
- `tests/unitTest/auditwheel_policy_unit_test.py`
- `tests/unitTest/wheel_workflow_unit_test.py`
- `tests/unitTest/packaging_tools_unit_test.py`
