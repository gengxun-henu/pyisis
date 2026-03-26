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

### 3. Add focused validation

- Add or update the smallest relevant test first.
- Prefer focused `unittest` coverage in `tests/unitTest/`.
- Keep `tests/smoke_import.py` fast and broad; only add minimum symbol or integration checks there.
- Reuse `tests/unitTest/_unit_test_support.py` rather than duplicating fixtures.
- See [testing and validation reference](./references/testing.md) for detailed validation sequencing and reporting expectations.

### 4. Validate with the correct environment

Always prefer:

- the `asp360_new` environment's Python interpreter

Treat Python ABI mismatches or missing runtime data separately from binding regressions.

### 5. Maintain progress records

After a binding task is completed, update the relevant progress artifacts:

- `pybind_progress_log.md`
- `todo_pybind11.csv` when the pending binding inventory or tracked status source changes
- the relevant method inventory CSV if the task requires status synchronization

Record blockers or uncertainties explicitly. See [progress maintenance reference](./references/progress.md).

## Constraints and Non-goals

- Do not treat missing NAIF / SPICE / kernel data as automatic binding failures.
- Do not validate with the wrong Python ABI and report the result as a regression.
- Do not let `smoke_import.py` become the main detailed behavior test suite.
- Do not modify broad unrelated ISIS C++ source unless the user explicitly asks for changes outside the binding layer.
- Do not skip updating `pybind_progress_log.md` when pybind work meaningfully progresses.

## Completion Checklist

A pybind task is usually ready to report when all relevant items below are satisfied:

- binding code updated in `src/`
- package export updated if needed
- focused test added or updated
- smallest relevant validation run with the `asp360_new` Python interpreter
- progress note updated in `pybind_progress_log.md` when applicable
- blockers clearly separated from code regressions

## References

- [Binding workflow](./references/binding-workflow.md)
- [Testing and validation](./references/testing.md)
- [Progress maintenance](./references/progress.md)
