# Copilot workspace instructions

This repository provides standalone pybind11 bindings and tests for exposing selected USGS ISIS functionality to Python.

Core working directories include:

- `src/`
- `tests/`
- `python/`
- `class_bind_methods_details/`

All paths below are relative to the repository root unless noted otherwise.

## Working style

- Default to acting without asking for confirmation for low-risk, reversible changes.
- Only ask for confirmation before high-risk actions such as destructive operations, secrets handling, or irreversible changes.
- Prefer replying in Chinese unless the user clearly requests another language.
- Execute first and then report results concisely instead of repeatedly asking whether to continue.
- When information is incomplete but the next step is low-risk and reversible, proceed with the most reasonable assumption and state that assumption in the report.

## Environment and validation

- Prefer using the Python interpreter from the `asp360_new` environment for Python build, test, and validation tasks in this repository.
- After modifying code, default to running the smallest relevant test or validation for the changed area.
- Prefer focused unit tests over broad validation when a smaller targeted check is available.

## Additional instructions to follow

- For shared authored metadata conventions across pybind C++ files and Python unit tests, also follow `.github/instructions/pybind-metadata-common.instructions.md`.
- For pybind11 binding and test work, also follow `.github/instructions/pybind-testing.instructions.md`.
- For upstream ISIS API reading, lifecycle analysis, and behavior-driven test design, also follow `.github/instructions/pybind-upstream-source-reading.instructions.md`.
- For deciding what belongs in `reference/` versus `tests/data/`, also follow `.github/instructions/reference-data-layout.instructions.md`.
- For pybind source and helper header metadata conventions, also follow `.github/instructions/pybind-cpp-metadata.instructions.md`.
- For newly created or substantially rewritten binding C++ files, also follow `.github/instructions/pybind-file-header.instructions.md`.
- For Python unit-test metadata conventions, also follow `.github/instructions/pybind-python-test-metadata.instructions.md`.
- For C++ naming consistency, follow `.github/instructions/isis-cpp-naming.instructions.md` when editing relevant C++ files.
- When binding, add '#include <pybind11/pybind11.h>,#include <pybind11/stl.h>' when necessary.

## Pybind workflow routing

- For workflow-oriented pybind tasks, use `.github/skills/isis-pybind/SKILL.md` as the main task procedure.
- For queue-based continuous rollout work across unfinished classes (for example 5/10-class batches, one-class-at-a-time closure, retry limits, and blocker bookkeeping), use `.github/skills/pybind-rollout-execution/SKILL.md` as the companion rollout procedure.
- Use repository-relative paths such as `reference/upstream_isis/...` when referring to mirrored upstream ISIS source in notes, reviews, or CI-facing guidance.

