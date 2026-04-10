# Testing and Validation Reference

This reference focuses on how to validate ISIS pybind11 work without confusing environment issues for binding regressions.

All paths below are relative to the repository root.

## Interpreter rule

Prefer this Python interpreter for all validation work in this repository:

- the `asp360_new` environment's Python interpreter

Reason:

- the built extension targets CPython 3.12
- using another interpreter may produce false failures due to ABI mismatch

## Validation order

After modifying a binding or test, use this default order:

1. run the smallest relevant focused unit test
2. run the related unit test group if needed
3. run `tests/smoke_import.py`
4. if the task touches installation expectations, verify install-tree import too

## Focused unit test expectations

Prefer small `unittest` files under `tests/unitTest/`.

For most value-like or utility bindings, verify:

1. default constructor or invalid state behavior
2. main constructors and enum-backed constructors
3. getters, setters, or conversion helpers
4. exception translation
5. Python-facing helpers such as `__repr__`, `to_string`, or static helpers

Reuse:

- `tests/unitTest/_unit_test_support.py`

## Smoke test expectations

Keep `tests/smoke_import.py`:

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

## Common failure signatures and what they usually mean

Use this quick triage when a pybind task fails after apparently small binding edits.

### Compile-time signature mismatch

Typical symptoms:

- `no matching function for call to ...`
- `no known conversion from 'std::string' to 'QString'`

Usual cause:

- the binding exposed a `std::string` constructor or method directly even though upstream expects `QString`

Preferred fix:

- replace the direct binding with a lambda or wrapper that converts through `QString::fromStdString(...)`

### Import-time `undefined symbol`

Typical symptoms:

- `ImportError: ... _isis_core...so: undefined symbol: ...`

Usual causes:

- the header declares a method but the linked runtime does not export it
- the constructor exists in upstream source but is absent from the linked shared library
- a copy constructor is declared but not exported in the runtime used by this repository

Preferred checks:

- inspect the mirrored upstream header and `.cpp`
- check whether the symbol is present in the linked library with `nm -D ... | c++filt`
- if missing, replace the direct binding with a wrapper built from exported methods instead of binding the absent symbol

Examples seen in this repository:

- `HiLab(Cube *)`
- `HiLab::getCcd()`
- `PixelFOV(const PixelFOV &)`

### Import-time `generic_type ... already defined`

Typical symptom:

- `generic_type: cannot initialize type "...": an object with that name is already defined`

Usual cause:

- the same Python type name was registered in two binding files, or a derived registration and module order are inconsistent

Preferred checks:

- grep for duplicate `py::class_<...>(..., "SameName")`
- confirm base types are registered before derived types in `src/module.cpp`

Example seen in this repository:

- `GaussianStretch` registered in both `src/base/bind_base_filters.cpp` and `src/bind_statistics.cpp`

### Python test segfault on a default-constructed object

Typical symptom:

- focused unit test or `ctest` crashes instead of raising a Python exception

Usual cause:

- the wrapper called an upstream method that assumes internal state is initialized, but the Python-visible constructor does not establish that state

Preferred checks:

- reproduce with the smallest Python snippet possible
- inspect the upstream `.cpp` for raw pointer dereferences or null-sensitive member access
- add a Python-safe guard or fallback in the binding layer

Example seen in this repository:

- `ImageOverlap.area()` on a default-constructed overlap with no polygon backing store

### Python `TypeError: Unregistered type : QString`

Typical symptom:

- pybind reports it cannot convert a return value or argument involving `QString`

Usual cause:

- a binding returns raw `QString` or accepts it without an explicit conversion wrapper

Preferred fix:

- convert to `std::string` on return and from `std::string` on input at the binding boundary

Example seen in this repository:

- `PolygonSeeder.algorithm()` returning `QString`

## Reporting expectations

When summarizing validation:

- name the interpreter used
- name the exact test file or smoke test executed
- state whether failures are binding regressions or environment-related
- mention any skipped tests and why
