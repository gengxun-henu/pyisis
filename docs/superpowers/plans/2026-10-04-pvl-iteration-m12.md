# PVL Python Collection Iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing ISIS PVL bindings naturally iterable from Python while preserving stable value and object ownership semantics across ISIS 9 and ISIS 10.

**Architecture:** Add Python-facing `__iter__` methods to the already-bound `PvlKeyword`, `PvlContainer`, and `PvlObject` classes in `src/base/bind_base_pvl.cpp`. Each iterator materializes a short Python list of copies or references selected by the existing indexed APIs, avoiding exposure of Qt iterator types and keeping the lifetime owned by the parent binding.

**Tech Stack:** C++17, pybind11, ISIS PvlKeyword/PvlContainer/PvlObject, Python unittest.

**Spec:** `.planning/isis10-expansion/task_plan.md` PVL queue; active conda ISIS headers are authoritative.

## Global Constraints

- Use shared binding sources for compatible ISIS 9/10 APIs.
- Keep Qt iterator types out of the Python ABI.
- Validate in `asp360_new` first and run the focused PVL unit module.
- Do not alter `.gitignore` or `print.prt`.

## Review Focus

- Iterating an empty keyword/container/object returns an empty sequence.
- Keyword iteration preserves value order and returns strings.
- Container iteration preserves keyword order without exposing invalid references after container mutation.
- Object iteration exposes groups and nested objects independently and preserves their order.
- Existing indexed access and ISIS 9/10 version-gated APIs remain unchanged.

### Task 1: Define failing Python iteration tests

**Files:**
- Modify: `tests/unitTest/pvl_unit_test.py`

- [ ] Add tests for keyword values, container keywords, object groups, and nested objects.
- [ ] Run `python -m unittest tests.unitTest.pvl_unit_test.PvlUnitTest -v` and observe failures because the iterators are absent.

### Task 2: Implement stable pybind iterators

**Files:**
- Modify: `src/base/bind_base_pvl.cpp`

- [ ] Add `__iter__` for `PvlKeyword`, `PvlContainer`, and `PvlObject` using Python lists built through existing size/index accessors.
- [ ] Preserve current reference-returning indexed APIs and add metadata lines required by the C++ scoped instructions.
- [ ] Rebuild `_isis_core` and rerun the focused PVL tests.

### Task 3: Document and verify

**Files:**
- Modify: `README.md`
- Modify: `tests/unitTest/pvl_unit_test.py`
- Modify: `.planning/2026-10-04-pvl-iteration-m12/*`

- [ ] Add a concise README example showing iteration over keywords and groups.
- [ ] Run focused tests, smoke import, full unit suite, and `git diff --check`.
- [ ] Commit, push, open/merge a PR, and synchronize local `main`.
