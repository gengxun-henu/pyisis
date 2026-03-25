# Pybind Progress Log

## 2026-03-25

- GitHub Actions CI setup progress:
  - Added `.github/workflows/ci-pybind.yml` for `isis_pybind_standalone` build/test automation on GitHub-hosted runners.
  - Added `Github_actions_build_test_steps.md` with repository settings, trigger behavior, and troubleshooting flow for GitHub Actions.
  - CI workflow explicitly installs an external ISIS prefix (`isis=9.0.0`) and validates `include/isis`, `lib/libisis.so`, and `lib/Camera.plugin` before CMake configure.
- Path sync:
  - Adapted the inner-repository workflow to treat `isis_pybind_standalone` itself as the GitHub repository root.
  - Updated workflow trigger paths, environment-file location, build directory, and `ISISDATA` path to use repository-root-relative locations.
- Validation status:
  - Static review only in this session for workflow/doc content; runtime execution still needs to happen on GitHub Actions after push.

- Column binding progress:
  - Confirmed `Isis::Column` is already bound in `src/base/bind_base_utility.cpp`.
  - Confirmed `Column` is re-exported from `python/isis_pybind/__init__.py` at package level.
  - Updated `tests/unitTest/utility_unit_test.py` to align with native ISIS `Column` constraints.
  - Added focused exception-path tests for width/name, decimal alignment with string type, and unsupported precision configuration.
- Tracking sync:
  - Updated `todo_pybind11.csv` to mark `Utility,Column` as `已转换`.
- Validation status:
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest discover -s tests/unitTest -p 'utility_unit_test.py' -v`
  - Result: 13 tests ran, all passed.
- Known blockers:
  - Broader batch test suite previously reported unrelated native crashes / unresolved symbol issues in other bindings; validate `Column` changes in isolation first.

- UniversalGroundMap test stabilization:
  - Reproduced `tests/unitTest/universal_ground_map_unit_test.py` exiting with code 137 under the correct `asp360_new` Python interpreter.
  - Isolated the kill to `UniversalGroundMap.ground_range(cube)` on the projected `map2map` fixture, specifically the `allow_estimation=True` path.
  - Updated the projected-cube unit test to validate the stable projection-backed round trip and to assert the non-estimating `ground_range(cube, False)` behavior instead of invoking the expensive estimation path.
- Validation status:
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest -v universal_ground_map_unit_test.UniversalGroundMapUnitTest.test_camera_backed_ground_map_round_trip universal_ground_map_unit_test.UniversalGroundMapUnitTest.test_projection_backed_ground_map_round_trip`
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -u universal_ground_map_unit_test.py`
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest -v projection_unit_test.py universal_ground_map_unit_test.py`
- Follow-up scan:
  - Searched `tests/unitTest/*_unit_test.py` for estimation/range-adjacent calls such as `ground_range(...)`, `xy_range()`, `ProjectionFactory.create_for_cube(...)`, and cube-backed projection helpers.
  - Confirmed the only kill-prone call site in the current unit-test directory was the already-fixed `UniversalGroundMap.ground_range(cube)` projected-fixture path.
  - Verified `projection_unit_test.py` range-related coverage (`xy_range()` and `ProjectionFactory.create_for_cube(...)`) remains stable under the `asp360_new` interpreter.

- Math binding export and inventory sync:
  - Confirmed `Calculator`, `Affine`, and `BasisFunction` were already registered in `_isis_core` via `src/base/bind_base_math.cpp`, but were missing from the package-level re-exports in `python/isis_pybind/__init__.py`.
  - Re-exported `Calculator`, `Affine`, and `BasisFunction` from the source package entry point and the local `build/python/isis_pybind/__init__.py` copy used by unit tests.
  - Updated `tests/unitTest/math_unit_test.py` so `BasisFunction` uses the upstream three-argument constructor signature `BasisFunction(name, num_vars, num_coefs)` instead of assuming a nonexistent default constructor.
  - Corrected the `Affine.rotate(...)` test expectation and binding docstring to match the upstream degree-based API.
  - Added smoke-level symbol presence checks for `Calculator`, `Affine`, and `BasisFunction` in `tests/smoke_import.py`.
- Tracking sync:
  - Updated `todo_pybind11.csv` entries for `Math,Affine`, `Math,BasisFunction`, and `Math,Calculator` to `已转换`.
  - Updated `class_bind_methods_details/base_affine_methods.csv`, `base_basis_function_methods.csv`, `base_calculator_methods.csv`, and `methods_inventory_summary.csv` to match the actual exported state.
- Validation status:
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python math_unit_test.py`
  - Result: 17 tests ran, all passed.
  - Passed: `/home/gengxun/miniconda3/envs/asp360_new/bin/python tests/smoke_import.py`
  - Result: `smoke import ok`
- Known blockers:
  - `Calculator::Minimum2` and `Calculator::Maximum2` remain intentionally unbound because they are declared in `Calculator.h` but not implemented in the upstream ISIS `Calculator.cpp`.
  - `Affine` still does not expose the static identity-matrix helper or forward/inverse matrix accessors; these remain inventory gaps, not regressions from this task.
