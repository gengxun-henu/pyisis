---
name: isis-pybind
description: 'Implement, extend, test, or maintain pybind11 bindings for USGS ISIS in this repository. Use when the user asks to 继续做 ISIS pybind 绑定, 给某个 ISIS 类写 pybind11 绑定, 补 unit test / smoke test, 分析 todo_pybind11.csv / methods_inventory_summary.csv, 或更新 pybind_progress_log.md progress.'
argument-hint: '[class or task] e.g. Cube binding, camera tests, update todo_pybind11'
user-invocable: true
---

# ISIS Pybind Workflow
Use this skill for repeatable pybind11 work in this repository, especially when the request involves:

- binding a new ISIS C++ class or method into Python
- extending an existing binding in `src/`
- adding or fixing Python tests in `tests/`
- reviewing binding coverage from `class_bind_methods_details/`
- updating `pybind_progress_log.md` after implementation progress

All paths below are relative to the repository root unless noted otherwise.

This skill is **workflow-oriented**. It does not replace the repository-wide rules in:

- `../../copilot-instructions.md`
- `../../instructions/pybind-testing.instructions.md`

Follow those existing instructions in addition to this skill.

## When to Use

Use this skill for requests about pybind bindings, pybind tests, binding coverage inventory, progress tracking, or exposing a specific ISIS class to Python. Do **not** use it for general ISIS C++ development unless the request is clearly about Python exposure or pybind validation.

If the task becomes a queue-based campaign across many unfinished classes with one-class-at-a-time closure, retry counting, and stop-loss bookkeeping, pair this skill with `.github/skills/pybind-rollout-execution/SKILL.md`.

## Default Inputs to Inspect First

Before changing code, inspect these files in this order:

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. the target class detail CSV under `class_bind_methods_details/`
4. `pybind_progress_log.md`
5. similar binding implementations under `src/`
6. Python exports under `isis_pybind/__init__.py`
7. similar tests under `tests/unitTest/`

If a target class is not specified, start from the summary CSV and prefer high-priority, low-open-item targets.

## Standard Procedure

### 1. Select and scope the target

- Identify the ISIS class, methods, or module to bind.
- Use `methods_inventory_summary.csv` to find candidate classes.
- Open the matching `*_methods.csv` file to understand which methods are still marked `N` or `Partial`.
- Check whether the binding already exists in `src/` before adding anything new.

See [binding workflow reference](./references/binding-workflow.md).

### 2. Implement or extend the binding

- Follow existing pybind11 patterns already used in this repository.
- Prefer the smallest safe change.
- Preserve existing Python-facing names unless the task requires a new exposure.
- If the class is already exported, extend its method surface before inventing alternate wrappers.
- Update `python/isis_pybind/__init__.py` when a symbol must be re-exported at package level.

#### Recurring binding hazards to check before compiling

- Do not bind Qt signal emitters, signal-forwarding helpers, or observer plumbing as default Python API.
	- Example: `emitMeasureModified(ControlMeasure *measure, ControlMeasure::ModType modType, QVariant oldValue, QVariant newValue)` should be treated as internal Qt notification flow, not as ordinary Python-facing functionality to expose.
	- Apply the same rule to `emit*` methods, `signals`/`slots`, and helpers whose primary role is dispatching events with `QVariant` or similar Qt event payloads.
	- If Python eventually needs notifications, prefer a small wrapper or callback-oriented facade instead of mirroring the raw Qt signal surface.
- Audit Qt string boundaries explicitly at the Python/C++ seam.
	- Constructors or methods that take `QString` should not be bound directly with `std::string` template signatures and assumed to convert automatically.
	- Example: `PushFrameCameraCcdLayout::FrameletInfo(...)` and `ReseauDistortionMap(...)` compile-failed when bound as `std::string` constructors even though Python naturally passes `str`.
	- Prefer a lambda or local wrapper that converts `std::string` to `QString` with `QString::fromStdString(...)`.
	- Apply the same rule to return values: if an API returns `QString`, convert it to `std::string` in the binding instead of returning raw Qt types to Python.
	- Example: `PolygonSeeder::Algorithm()` must be wrapped to return Python `str`, otherwise pybind reports `Unregistered type: QString`.
- Audit member-function qualifiers before wrapping operators or arithmetic helpers.
	- Example: `Quaternion::operator*(const double &)` is **not** `const` in upstream ISIS.
	- Do not bind it with a lambda that takes `const Isis::Quaternion &` and then calls `a * scalar` directly.
	- Prefer copying into a mutable local wrapper/object first, or exposing an equivalent const-safe lambda built from a mutable copy.
- Keep explicit pybind lambda return types internally consistent across all branches.
	- Example: an `Area3D.__repr__` lambda cannot return `std::string` in one branch and a string literal (`const char *`) in another branch, or C++ will fail to deduce a single return type.
	- When a lambda returns strings, prefer returning `std::string(...)` from every branch, or add an explicit trailing return type when appropriate.
- Do not bind upstream `protected` members directly with pybind lambdas.
	- Example: `PvlFormat::addQuotes(...)`, `PvlFormat::isSingleUnit(...)`, `PvlTranslationTable::hasInputDefault(...)`, `IsAuto(...)`, `IsOptional(...)`, `OutputName(...)`, and `OutputPosition(...)` are protected helpers, not public API.
	- If Python still needs those semantics, expose them through a local helper subclass or wrapper that safely forwards the protected call, or reimplement a stable public-facing wrapper when the behavior is simple and well verified.
	- Before adding such wrappers, verify the behavior against `reference/upstream_isis/...` instead of assuming a declaration is callable from pybind.
- Audit constructors and copy constructors for linkability, not just ordinary methods.
	- A class may look safe to bind because the header declares a constructor or helper, but the linked ISIS runtime may not export that symbol.
	- Example: `HiLab(Cube *)`, `HiLab::getCcd()`, and `PixelFOV(const PixelFOV &)` caused import-time `undefined symbol` failures even though the headers exposed them.
	- If the constructor or helper is missing from the linked runtime, do not bind it directly; replace it with a local wrapper class or lambda built from the exported surface.
- Avoid duplicate type registration and respect base-before-derived registration order.
	- If a class is registered twice with the same Python name, module import will fail with `generic_type: ... already defined`.
	- Example: `GaussianStretch` was bound in both `src/base/bind_base_filters.cpp` and `src/bind_statistics.cpp`.
	- Keep one canonical registration site per Python type, and if the type inherits another bound class, ensure the base binding is registered earlier in `src/module.cpp`.
- Guard Python-facing wrappers around upstream methods that assume internal state is already initialized.
	- Some ISIS methods are safe only after internal pointers, polygons, or runtime-owned buffers are populated.
	- Example: `ImageOverlap::Area()` dereferences the polygon pointer and can segfault on a default-constructed Python `ImageOverlap` with no polygon.
	- Prefer a Python-safe wrapper that returns a stable fallback or raises a clear exception rather than exposing a raw crash path.
- For `AutoReg`-family constructors and factory tests, match upstream PVL shape exactly.
	- `AutoReg(Pvl &)` first calls `pvl.findObject("AutoRegistration")`, then parses nested `Algorithm`, `PatternChip`, and `SearchChip` groups.
	- Do **not** build a flat `PvlGroup("AutoRegistration")` and pass it as the whole config; that will fail with `Unable to find PVL object [AutoRegistration]`.
	- Prefer copying the structure from `reference/upstream_isis/src/base/objs/MinimumDifference/unitTest.cpp` or `reference/upstream_isis/src/base/objs/AutoReg/unitTest.cpp` when adding `MaximumCorrelation`, `MinimumDifference`, `Gruen`, or factory regressions.

### 3. Add focused validation

- Add or update the smallest relevant test first.
- Prefer focused `unittest` coverage in `tests/unitTest/`.
- Keep `tests/smoke_import.py` fast and broad; only add minimum symbol or integration checks there.
- Reuse `tests/unitTest/_unit_test_support.py` rather than duplicating fixtures.
- When a unit test imports `_unit_test_support.py`, follow `../../instructions/pybind-testing.instructions.md` so the test also works from repo-root `python -m unittest tests.unitTest...` execution.
- See [testing and validation reference](./references/testing.md) for detailed validation sequencing and reporting expectations.

### 4. Validate with the correct environment

Always prefer:

- the `asp360_new` environment's Python interpreter

Treat Python ABI mismatches or missing runtime data separately from binding regressions.

If validation fails, classify the failure layer before changing code:

1. compile failure
2. link failure
3. import-time undefined symbol
4. focused unit-test failure
5. smoke-test failure
6. environment/runtime-data issue

For repeated failures on a single class, prefer these repair patterns before broad rewrites:

- if a method is declared in headers but missing in the linked implementation, avoid binding the raw member-function pointer; prefer a wrapper built from stable APIs
- if a constructor or copy constructor is declared in headers but missing from the linked runtime, replace the direct binding with a local wrapper class instead of forcing the symbol into `_isis_core`
- if the class is abstract or pure-virtual, expose the usable surface without forcing unsafe construction
- if Qt containers or ISIS-specific types are Python-hostile, adapt them to Python-friendly values
- if a method returns `QString` or accepts `QString`, convert it explicitly at the binding boundary instead of relying on implicit pybind support
- if import fails with `generic_type: ... already defined`, search for duplicate `py::class_<...>(..., "SameName")` registrations and for registration-order issues between base and derived types
- if a Python test segfaults on a default-constructed object, suspect an upstream method that assumes initialized internal state and add a Python-safe wrapper before exposing that path
- if lifetimes are involved, inspect `keep_alive`, return policies, and temporary object hazards
- if runtime data is missing, treat it as environment-dependent and use stable skips or narrower smoke coverage where appropriate

If the task has become a queue-based repair campaign with retry tracking or stop-loss decisions, switch to or pair with `.github/skills/pybind-rollout-execution/SKILL.md` instead of improvising ad-hoc bookkeeping.

### 5. Maintain progress records

After a binding task is completed, or whenever you update class-level ledger/progress status, update the relevant progress artifacts together:

- `pybind_progress_log.md`
- `todo_pybind11.csv` when the pending binding inventory or tracked status source changes
- the relevant method inventory CSV; when a class status changes, explicitly inspect and sync the matching `class_bind_methods_details/*_methods.csv`, not only the higher-level ledgers

Record blockers or uncertainties explicitly. See [progress maintenance reference](./references/progress.md).

## Constraints and Non-goals

- Do not treat missing NAIF / SPICE / kernel data as automatic binding failures.
- Do not validate with the wrong Python ABI and report the result as a regression.
- Do not let `smoke_import.py` become the main detailed behavior test suite.
- Do not modify broad unrelated ISIS C++ source unless the user explicitly asks for changes outside the binding layer.
- Do not skip updating `pybind_progress_log.md` when pybind work meaningfully progresses.
- Do not turn single-class work into an untracked retry spiral; if the task becomes campaign-like, use the rollout skill's retry and stop-loss rules.

## Completion Checklist

A pybind task is usually ready to report when all relevant items below are satisfied:

- binding code updated in `src/`
- package export updated if needed
- focused test added or updated
- smallest relevant validation run with the `asp360_new` Python interpreter
- progress note updated in `pybind_progress_log.md` when applicable
- matching `class_bind_methods_details/*_methods.csv` reviewed and synchronized when class-level status or coverage changed
- blockers clearly separated from code regressions

## References

- [Binding workflow](./references/binding-workflow.md)
- [Testing and validation](./references/testing.md)
- [Progress maintenance](./references/progress.md)
