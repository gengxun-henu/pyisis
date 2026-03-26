---
description: "Use when editing or validating isis_pybind_standalone pybind11 bindings and tests. Covers the correct Python interpreter, extension-module compatibility, smoke-vs-unit-test scope, and environment-dependent test behavior."
applyTo: "isis_pybind_standalone/**/*.{py,cpp,h}"
---

# ISIS Pybind11 Testing Conventions

Use these rules when editing, running, or validating `isis_pybind_standalone` bindings and tests.

## Python interpreter and extension compatibility

- Prefer the `asp360_new` environment's Python interpreter for all `isis_pybind_standalone` build, test, and validation work.
- The standalone `isis_pybind` extension in this repository is currently built for CPython 3.12.
- Do not validate `isis_pybind_standalone` tests with the default `base` Python 3.13 interpreter unless the extension has been rebuilt for that interpreter.
- If `import isis_pybind` succeeds but `isis_pybind._isis_core` is missing, first check for a Python-version mismatch before treating it as a binding regression.

## Preferred test structure

- Keep broad module-import and cross-module sanity coverage in `isis_pybind_standalone/tests/smoke_import.py`.
- Put detailed behavior checks in small focused `unittest` files under `isis_pybind_standalone/tests/unitTest/`.
- Prefer extending `_unit_test_support.py` for shared helpers, constants, temporary files, and common label builders instead of duplicating setup logic across tests.
- When adding tests for a new binding, follow the existing `distance_unit_test.py` style where practical: constructor coverage, accessors, mutators, enums, exceptions, and copy or conversion semantics.

## What to verify first in pybind tests

For value-like and utility bindings, prefer checking these behaviors first:

1. default constructor or invalid state behavior
2. primary constructors and enum-backed constructors
3. getters and setters or conversion methods
4. exception translation to `ip.IException` where applicable
5. Python-facing helpers such as `__repr__`, `to_string`, or static helpers

When a bound API differs from the original C++ intuition, update the test to reflect the actual exposed Python signature instead of assuming a copy constructor or overload exists.

## Environment-dependent behavior

- Treat missing runtime data dependencies as environment issues, not automatic binding failures.
- `ip.iTime` depends on ISIS leap second kernel data such as `naif*.tls`.
- If the runtime environment lacks the required leap second kernels, unit tests for `iTime` should skip gracefully instead of failing as regressions.
- Apply the same principle to other bindings that depend on external kernels, labels, or data products: prefer controlled skips or clearly scoped smoke checks over brittle hard failures.

## Smoke versus unit-test scope

- `smoke_import.py` should stay fast and stable.
- Use smoke coverage for:
  - module import success
  - symbol presence
  - a small number of cross-module minimum-viable integration paths
- Do not let `smoke_import.py` grow into the main place for detailed behavioral assertions once dedicated unit tests exist.
- When a behavior gets its own focused unit test, prefer removing redundant detailed assertions from the smoke test.

## Practical validation workflow

- After modifying or adding a pybind test, first run the smallest relevant test file with the `asp360_new` Python interpreter.
- Then run the related `unitTest` group.
- Finally run `isis_pybind_standalone/tests/smoke_import.py` to confirm broad import and minimal integration coverage still works.
- If a failure appears only under Python 3.13 but not under the repository's CPython 3.12 test interpreter, do not report it as a binding failure without confirming the interpreter mismatch.

## Non-goals

- Do not assume every C++ constructor or overload is exposed exactly the same way in Python.
- Do not treat missing external kernel data as proof that a pybind implementation is broken.
- Do not use the default shell interpreter for pybind validation when the built extension targets a different Python ABI.