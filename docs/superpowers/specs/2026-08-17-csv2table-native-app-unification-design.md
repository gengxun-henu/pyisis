# `csv2table` Native APP Unification Design

## Status

Approved in principle on 2026-08-17. Written-spec review is pending.

This design supersedes the active recommendation in
`2026-08-02-csv2table-cross-platform-facade-design.md`. The older document is
retained as historical implementation context; it no longer defines the
supported interface.

## Decision

Treat `csv2table` exclusively as a native ISIS application in every supported
combination:

- ISIS 9 on Windows;
- ISIS 9 on Linux;
- ISIS 10 on Windows; and
- ISIS 10 on Linux.

Users invoke the installed or packaged `csv2table` executable directly. PyISIS
does not expose `isis_pybind.csv2table`, `pyisis.csv2table`, a private
`_isis_core._csv2table_native` binding, or a general Python APP runner.

This deliberately favors one application boundary over a superficially
uniform Python function. `csv2table` is an ISIS APP with an XML-defined
command-line contract and is already built as an executable on Windows ISIS 9.
Using the executable everywhere avoids a special ISIS 10/Linux link-time path,
keeps ISIS 9 and ISIS 10 behavior aligned, and matches how the repository
distributes every other native APP.

## Alternatives Considered

### Selected: native APP only

All four platform/version cells call `csv2table` as a separate process. There
is no PyISIS API. This has the smallest maintenance surface and preserves the
native ISIS application lifecycle, diagnostics, preferences, XML validation,
and exit status.

### Rejected: one Python wrapper that always launches a process

A thin wrapper would make the backend uniform but would still give
`csv2table` a unique convenience API that other ISIS APPs do not receive. It
would also require PyISIS to own executable discovery, argument encoding,
environment setup, output capture, and error translation without adding an
algorithmic binding.

### Rejected: retain the hybrid facade

The current facade links the ISIS 10 function in-process on Linux and launches
an executable on Windows. ISIS 9 has no equivalent installed library API. The
result is a version- and platform-dependent implementation with two error
models and an unnecessary C++ adapter.

## Public Interface and Invocation

The supported interface is the native ISIS application syntax:

```text
csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
```

Optional parameters such as `LABEL` and `COLTYPES` follow the installed
`csv2table.xml` for the selected ISIS version. PyISIS does not normalize,
validate, or translate these arguments.

On Linux, users run the application from an activated ISIS environment or an
equivalent configured runtime:

```bash
csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
```

In the portable Windows native-APP archive, users run it through the common
launcher used by all CLI applications:

```bat
launch\isis-app.cmd csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
```

Direct execution of `csv2table.exe` remains valid when the caller has already
established the required ISIS runtime environment. No per-APP launcher or
Python helper is introduced.

## Component Changes

Implementation removes only the special PyISIS path and preserves unrelated
bindings:

- remove `python/isis_pybind/_csv2table.py`;
- remove `python/isis_pybind/_app_runner.py`, because repository analysis shows
  that it exists only for the `csv2table` facade;
- remove the conditional `csv2table` export from
  `python/isis_pybind/__init__.py` and from its public symbol list;
- remove copy/install rules for both deleted Python modules from
  `CMakeLists.txt`;
- remove the Linux ISIS 10 `_csv2table_native` adapter and its csv2table-only
  headers/helpers from `src/bind_isis10.cpp`, without changing other ISIS 10
  bindings;
- replace facade-specific unit tests with native-APP inventory, build,
  packaging, and behavior coverage;
- update current README and compatibility/inventory documentation so
  `csv2table` is classified as `native-app-only`, not `bound`; and
- update the inventory generator or its source classification so regeneration
  cannot restore the obsolete `bound` classification.

The historical 2026-08-02 design and implementation plan remain unchanged as
an audit trail. Current documentation must point to this superseding decision.

## Build and Distribution Contract

`csv2table` is a normal member of each supported native ISIS APP inventory.
It receives no exception in build, staging, launcher, or packaging code.

- Windows ISIS 9 uses the already verified installed executable and XML as the
  starting point, then records their actual build and smoke evidence.
- Windows ISIS 10 builds and installs the application from the matching ISIS
  source/API before its support status is promoted.
- Linux ISIS 9 and ISIS 10 use the executable and XML delivered by the selected
  ISIS environment, subject to focused validation.
- The Windows portable archive includes `csv2table.exe` and
  `bin/xml/csv2table.xml` through the same manifest-driven path as the other
  command-line APPs.

Manifest status fields describe observed evidence only. They must not claim
`compiled`, `installed`, `smoke-tested`, or an equivalent state until that
specific version/platform cell has passed the corresponding check.

## Data Flow and Error Contract

The data flow is identical in principle across platforms:

1. The caller establishes the ISIS runtime environment.
2. The caller starts `csv2table` with separate `KEY=VALUE` arguments.
3. The native application loads its installed XML contract and ISIS runtime.
4. ISIS reads the CSV and optional label, modifies the target cube, and emits
   native diagnostics.
5. The caller receives the native process exit code, standard output, and
   standard error.

The application exit code is the success/failure authority. Launchers preserve
it. They must not parse or rewrite ISIS diagnostic text, invoke through a shell
string, or translate failures into Python exception classes. Missing
executables, missing XML/runtime data, loader failures, invalid parameters, and
scientific/data errors therefore remain distinguishable through native process
diagnostics.

## Compatibility and Migration

Removing `isis_pybind.csv2table` and `pyisis.csv2table` is an intentional
breaking change to the repository's pre-release ISIS 10 facade. There is no
deprecation shim because retaining one would preserve the exceptional API this
design removes.

Migration is explicit:

```python
# Removed
isis_pybind.csv2table(csv_path, cube_path, "MyTable")
```

becomes an external native APP invocation owned by the user's workflow, for
example through Python's standard `subprocess` module when Python orchestration
is desired. PyISIS does not publish or maintain that orchestration helper.

ISIS 9 users gain no Python symbol; they gain the same documented native APP
availability and validation contract as ISIS 10 users.

## Validation Matrix

Support requires evidence for every ISIS-version/OS cell:

| Check | ISIS 9 Linux | ISIS 9 Windows | ISIS 10 Linux | ISIS 10 Windows |
|---|---:|---:|---:|---:|
| Executable and XML present | Required | Required | Required | Required |
| `csv2table -HELP` succeeds | Required | Required | Required | Required |
| CSV is attached to a writable cube | Required | Required | Required | Required |
| `tabledump` verifies table content | Required | Required | Required | Required |
| Manifest/inventory classification | Required | Required | Required | Required |

In addition:

- import tests assert that `csv2table` is absent from `isis_pybind.__all__`,
  absent from the high-level `pyisis` facade, and absent from `_isis_core` for
  both ISIS 9 and ISIS 10;
- source/build checks assert that the obsolete adapter and private runner are
  not packaged;
- Windows source builds verify compilation and installation before portable
  archive staging;
- Windows archive tests invoke `launch\isis-app.cmd csv2table` from a clean,
  space-containing extraction path; and
- required support cells have zero failures and zero skips. A missing test
  environment is reported as incomplete evidence, not counted as a pass.

The focused behavior fixture uses a small CSV and disposable writable cube. It
verifies the resulting table name, schema, record count, and representative
values through the native `tabledump` APP, avoiding dependence on the removed
Python binding.

## Baseline Corrections Required Before Feature Work

The current native APP manifest contains 150 CLI APPs including `csv2table`,
while one packaging assertion still expects 149 and the generated priority
inventory still marks `csv2table` as absent. Implementation first aligns those
derived expectations with the tracked manifest and regenerates the inventory.

Four runtime-wheel tests use Linux-only tools (`ldd` and `readelf`) and
currently error when the exact combined suite is run on Windows. The Windows
selector must exclude those Linux-only tests while preserving their Linux
semantics. These baseline corrections are part of making the cross-platform
validation signal truthful; they do not relax native APP acceptance criteria.

## Acceptance Criteria

- No `csv2table` symbol or convenience facade is published by `isis_pybind`,
  `pyisis`, or `_isis_core`.
- No csv2table-specific Python runner or in-process C++ adapter is installed.
- Current inventories classify `csv2table` as a native APP for ISIS 9 and
  ISIS 10 on Windows and Linux.
- Native help and real CSV-to-table-to-tabledump checks pass in all four
  required cells with zero skips.
- Windows portable packaging treats `csv2table` exactly like the other CLI
  APPs and preserves its exit code and diagnostics.
- Documentation gives native invocation and migration guidance and no current
  document advertises the removed Python API.
- Focused tests and the relevant packaging/runtime suite pass on their intended
  platforms.

## Non-goals

- A public or private PyISIS APP execution framework.
- A Python reimplementation of `csv2table`.
- Stable Python exception translation for native APP errors.
- Identical diagnostic wording across ISIS versions or operating systems.
- Rewriting historical design records to conceal the superseded facade.
- Changing unrelated bindings or exposing Qt `UserInterface` APIs.
