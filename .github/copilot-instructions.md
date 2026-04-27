# Copilot workspace instructions

This repository provides standalone pybind11 bindings and tests for exposing selected USGS ISIS functionality to Python.

Keep this file intentionally short to reduce Copilot context usage. Put detailed or low-frequency guidance in scoped files under `.github/instructions/`, workflow procedures under `.github/skills/`, and project notes under `reference/notes/`.

## Working defaults

- Default to acting without asking for confirmation for low-risk, reversible changes.
- Only ask before high-risk actions such as destructive operations, secrets handling, or irreversible changes.
- Prefer replying in Chinese unless the user clearly requests another language.
- Execute first, then report results concisely.
- Prefer repository-relative paths in notes, plans, reviews, and CI-facing guidance.

## Environment and validation

- Prefer the Python interpreter from the `asp360_new` environment for build, test, and validation work.
- After modifying code, run the smallest relevant validation first.
- Prefer focused unit tests over broad validation when a smaller targeted check is available.

## Pybind defaults

- For binding signatures and compile decisions, treat the active conda ISIS headers and libraries as the source of truth; use `reference/upstream_isis/` mainly for implementation and behavior reading.
- For QObject-derived ISIS classes, default to **not** binding Qt `signals`/`slots` into Python unless the user explicitly asks for that behavior.
- Prefer exposing stable data methods, mutators, queries, and enums over Qt observer/event plumbing.
- When binding, add `#include <pybind11/pybind11.h>` and `#include <pybind11/stl.h>` when necessary.

## Scoped instruction map

- `src/**/*.{cpp,h}`: `pybind-cpp-metadata.instructions.md`, `pybind-file-header.instructions.md`, `isis-cpp-naming.instructions.md`
- `tests/unitTest/**/*.py`: `pybind-python-test-metadata.instructions.md`, `pybind-metadata-common.instructions.md`
- `examples/**` and `scripts/**`: `python-example-cli-naming.instructions.md`
- pybind work in `src/`, `python/`, `tests/unitTest/`, or `tests/smoke_import.py`: `pybind-testing.instructions.md`, `pybind-upstream-source-reading.instructions.md`, `pybind-conda-api-precedence.instructions.md`
- repeated cube/camera batch-style operations: `isis-cube-batch-operations.instructions.md`
- reference/test-data placement: `reference-data-layout.instructions.md`

## Workflow routing

- For workflow-oriented pybind tasks, use `.github/skills/isis-pybind/SKILL.md` as the main task procedure.
- For queue-based continuous rollout work across unfinished classes, use `.github/skills/pybind-rollout-execution/SKILL.md` as the companion rollout procedure.
- Keep low-frequency project memory in `reference/notes/copilot_project_memory.md` instead of expanding this file.

