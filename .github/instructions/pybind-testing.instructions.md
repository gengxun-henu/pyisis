---
description: "Use when editing or validating pybind11 bindings and tests in this repository. Covers the correct Python interpreter, extension-module compatibility, smoke-vs-unit-test scope, and environment-dependent test behavior."
applyTo: "**/*.{py,cpp,h}"
---

# ISIS Pybind11 Testing Conventions

Use these rules when editing, running, or validating pybind11 bindings and tests in this repository.

All paths below are relative to the repository root.

## Python interpreter and extension compatibility

- Prefer the `asp360_new` environment's Python interpreter for all build, test, and validation work in this repository.
- The standalone `isis_pybind` extension in this repository is currently built for CPython 3.12.
- Do not validate these tests with the default `base` Python 3.13 interpreter unless the extension has been rebuilt for that interpreter.
- If `import isis_pybind` succeeds but `isis_pybind._isis_core` is missing, first check for a Python-version mismatch before treating it as a binding regression.

## Preferred test structure

- Keep broad module-import and cross-module sanity coverage in `tests/smoke_import.py`.
- Put detailed behavior checks in small focused `unittest` files under `tests/unitTest/`.
- Prefer extending `_unit_test_support.py` for shared helpers, constants, temporary files, and common label builders instead of duplicating setup logic across tests.
- When adding tests for a new binding, follow the existing `distance_unit_test.py` style where practical: constructor coverage, accessors, mutators, enums, exceptions, and copy or conversion semantics.

For most value-like and utility bindings, prioritize constructor coverage, core accessors or mutators, exception translation, and Python-facing helpers such as `__repr__`, `to_string`, or static helpers. If the exposed Python API differs from the original C++ intuition, test the actual Python signature instead of assuming a copy constructor or overload exists.

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
- Finally run `tests/smoke_import.py` to confirm broad import and minimal integration coverage still works.
- If a failure appears only under Python 3.13 but not under the repository's CPython 3.12 test interpreter, do not report it as a binding failure without confirming the interpreter mismatch.

For more detailed validation guidance, use `.github/skills/isis-pybind/references/testing.md`.

## Non-goals

- Do not assume every C++ constructor or overload is exposed exactly the same way in Python.
- Do not treat missing external kernel data as proof that a pybind implementation is broken.
- Do not use the default shell interpreter for pybind validation when the built extension targets a different Python ABI.