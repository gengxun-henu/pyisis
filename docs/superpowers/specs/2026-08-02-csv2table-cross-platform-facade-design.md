# Cross-Platform `csv2table` Python Facade Design

> **Historical / superseded:** The 2026-08-17 native-APP unification supersedes
> this facade design. PyISIS publishes no `csv2table` Python helper or
> in-process binding.

**Date:** 2026-08-02
**Status:** Historical / superseded
**Scope:** ISIS 10 only

## Context

ISIS 10 adds the public application entry point:

```cpp
void Isis::csv2table(Isis::UserInterface &ui, Isis::Pvl *log = nullptr);
```

The official Linux conda package `isis 10.0.0 h1f94ec8_1` exports this symbol
from `libisis10.0.0.so`. The repository's Windows ISIS 10 port intentionally
keeps application implementations out of `isis.dll`; selected applications are
built as independent executables instead. Consequently, a direct binding is
available on Linux but cannot be linked from the Windows `_isis_core.pyd`.

The selected design provides one Python-facing operation with two internal
backends:

- Linux calls the exported ISIS library function in process.
- Windows calls the native `csv2table.exe` without a shell or GUI.

This is not a Python rewrite of the ISIS algorithm. Both backends continue to
use the upstream C++ implementation and the upstream application XML contract.

## Goals

- Expose the same `csv2table` Python call on Linux and Windows ISIS 10 builds.
- Preserve native ISIS CSV parsing, table construction, label handling, and
  error validation.
- Keep the Windows process-launching helper private and narrowly scoped.
- Avoid exposing `UserInterface`, Qt signals/slots, or GUI behavior to Python.
- Establish a reusable internal process boundary without publishing a general
  `run_app()` API in this change.

## Non-goals

- Reimplementing `csv2table` in Python or local C++.
- Publishing Python wrappers for all ISIS applications.
- Supporting interactive ISIS GUI applications.
- Adding `csv2table` to ISIS 9, whose installed API does not provide the same
  application entry point.
- Guaranteeing byte-identical diagnostic text between the in-process and
  executable backends.

## Public API

The public call is:

```python
isis_pybind.csv2table(
    csv,
    to,
    tablename,
    *,
    label=None,
    coltypes=None,
)
```

`pyisis.csv2table` resolves to the same public operation through the existing
high-level facade's lazy forwarding to `isis_pybind`.

Parameters:

- `csv`: `str` or `os.PathLike`; input CSV file.
- `to`: `str` or `os.PathLike`; existing cube that receives the table.
- `tablename`: non-empty `str`; table name written to the cube.
- `label`: optional `str` or `os.PathLike`; flat PVL file whose keywords are
  copied to the table label.
- `coltypes`: optional sequence of strings accepted by the ISIS 10 XML:
  `Double`, `Integer`, `Float`, or `Text`.

The function returns `None` after the table has been written successfully.
Paths containing spaces remain single command arguments. The Python layer
normalizes path-like values and basic container types but leaves scientific and
file-content validation to ISIS.

The symbol is exported only when the loaded core reports ISIS major version 10
or later. ISIS 9 imports remain unchanged and do not advertise `csv2table` in
`isis_pybind.__all__`.

## Linux Backend

`src/bind_isis10.cpp` exposes a private low-level function named
`_csv2table_native` when both conditions hold:

- `PYISIS_ISIS10_API` is defined.
- The target is not Windows.

The adapter:

1. Converts the normalized Python parameters to `QVector<QString>` entries in
   ISIS `KEY=VALUE` form.
2. Resolves the installed `csv2table.xml` from the configured ISIS runtime.
3. Constructs `Isis::UserInterface` using the vector constructor.
4. Calls `Isis::csv2table(ui, nullptr)`.

The public Python wrapper calls `_csv2table_native`; users never receive or own
a `UserInterface` object. ISIS C++ exceptions continue through the repository's
existing exception translation and are wrapped at the public facade boundary
with operation context.

## Windows Backend

The Windows public wrapper calls a private Python helper, conceptually:

```python
_run_isis_app("csv2table", parameters)
```

The helper is internal implementation detail and is not included in
`isis_pybind.__all__` or `pyisis.__all__`. It performs only the process concerns
needed by this facade:

1. Locate `csv2table.exe` under the configured ISIS prefix/runtime directories,
   with `PATH` lookup as a final fallback.
2. Convert normalized parameters to individual `KEY=VALUE` arguments.
3. Execute with `subprocess.run(..., shell=False, capture_output=True,
   text=True)`.
4. Return normally on exit code zero.
5. Raise a Python runtime error containing the application name, exit code, and
   available stderr/stdout context on failure.

No empty-argument invocation and no `-GUI` option are used, so this path does
not start an ISIS graphical interface.

The Windows ISIS application manifest must include `csv2table` for ISIS 10 so
the hosted prefix contains the executable and its XML file. If a newer APP-wave
branch is merged first, this change must be rebased before editing the manifest
to preserve that branch's accumulated application list.

## Shared Parameter Encoding

Both backends use one Python normalization path before platform dispatch:

- Scalar paths and strings become `KEY=value`.
- `coltypes` becomes the ISIS list form
  `COLTYPES=(Double,Integer,Text)`.
- `None` omits the optional parameter entirely.
- The wrapper rejects an empty `tablename` and unsupported `coltypes` values
  before dispatch so both platforms fail consistently for these API-level
  errors.
- Arguments are never concatenated into a shell command string.

The Linux C++ adapter receives already normalized values rather than duplicating
Python validation. ISIS remains authoritative for CSV contents, PVL contents,
cube access, indexed column rules, and table replacement behavior.

## Error Contract

Public facade failures use a consistent Python `RuntimeError`-compatible error
with `csv2table` context. The original exception is chained when the Linux
backend fails. The Windows message includes the exit code and captured native
diagnostic output.

The contract guarantees the same error category and operation context, not the
same native text. This avoids parsing unstable ISIS diagnostic wording.

## Packaging and Source Changes

Expected implementation areas are:

- `src/bind_isis10.cpp`: Linux-only private native adapter.
- `python/isis_pybind/`: public facade and private executable runner.
- `CMakeLists.txt`: copy/install any new private Python module.
- `ports/windows/isis/windows-app-manifest.json`: add the ISIS 10 Windows APP
  target without altering unrelated APP records.
- `reference/isis10_bind_candidates/`: classify `csv2table` as bound and
  classify `ocams2isis`/`eisstitch` as native-APP-only rather than unclassified.
- Relevant README/API compatibility documentation.

The implementation must not modify `.gitignore` or `print.prt`.

## Test Strategy

Development follows test-driven development.

### Pure Python facade tests

- Path-like values and spaces are preserved.
- Required and optional parameters encode correctly.
- `coltypes` list encoding and validation behave as specified.
- Windows executable resolution prefers the configured ISIS runtime.
- The runner uses an argument list with `shell=False`.
- Non-zero exit status becomes the documented Python error.
- ISIS 9 does not advertise the public symbol.

These tests mock process execution and run on Linux CI as well as Windows CI.

### Linux ISIS 10 tests

- Import exposes `isis_pybind.csv2table` and the private native entry point.
- A temporary CSV is attached to a temporary writable cube.
- The written table name, fields, records, values, and optional table-label
  keywords are read back through existing `Cube`/`Table` bindings.
- `coltypes` exercises at least numeric and text conversion when supported by
  the installed ISIS 10 XML/API.

### ISIS 9 compatibility tests

- The package imports successfully.
- Existing smoke/unit tests remain green.
- `csv2table` is absent from the advertised ISIS 9 public surface.

### Windows ISIS 10 tests

- The APP manifest and prefix verification confirm `csv2table.exe` and its XML
  are installed.
- Wheel/package import exposes `csv2table` but not the Linux-only private native
  symbol.
- A focused hosted smoke test runs the executable backend against a writable
  test cube and verifies the attached table.

## Acceptance Criteria

- One documented Python signature behaves consistently on Linux and Windows
  ISIS 10.
- Linux links and calls the exported `Isis::csv2table` implementation.
- Windows calls the independently built native executable without a shell or
  GUI.
- ISIS 9 builds/imports without new link or public-API regressions.
- Focused facade, Linux integration, inventory, and Windows hosted checks pass.
- No generic public APP runner and no unrelated APP wrappers are introduced.
