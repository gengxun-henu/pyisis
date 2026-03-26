# Testing and Validation Reference

This reference focuses on how to validate ISIS pybind11 work without confusing environment issues for binding regressions.

## Interpreter rule

Prefer this Python interpreter for all `isis_pybind_standalone` validation work:

- the `asp360_new` environment's Python interpreter

Reason:

- the built extension targets CPython 3.12
- using another interpreter may produce false failures due to ABI mismatch

## Validation order

After modifying a binding or test, use this default order:

1. run the smallest relevant focused unit test
2. run the related unit test group if needed
3. run `isis_pybind_standalone/tests/smoke_import.py`
4. if the task touches installation expectations, verify install-tree import too

## Focused unit test expectations

Prefer small `unittest` files under `isis_pybind_standalone/tests/unitTest/`.

For most value-like or utility bindings, verify:

1. default constructor or invalid state behavior
2. main constructors and enum-backed constructors
3. getters, setters, or conversion helpers
4. exception translation
5. Python-facing helpers such as `__repr__`, `to_string`, or static helpers

Reuse:

- `./tests/unitTest/_unit_test_support.py`

## Smoke test expectations

Keep `./tests/smoke_import.py`:

- fast
- stable
- focused on import success, symbol presence, and minimal viable paths

Do not use the smoke test as the primary location for detailed behavioral assertions once focused unit tests exist.

## Environment-sensitive bindings

Some ISIS APIs depend on external runtime resources such as:

- NAIF or leap second kernels
- SPICE data
- camera or projection plugins
- mission-specific cube fixtures

Rules:

- if data is missing, prefer a clear skip strategy
- do not label missing runtime data as a binding regression
- keep the report explicit about whether the issue is code, ABI, or environment

## Reporting expectations

When summarizing validation:

- name the interpreter used
- name the exact test file or smoke test executed
- state whether failures are binding regressions or environment-related
- mention any skipped tests and why
