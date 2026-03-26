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

- For pybind11 binding and test work, also follow `.github/instructions/pybind-testing.instructions.md`.
- For pybind source and helper header metadata conventions, also follow `.github/instructions/pybind-cpp-metadata.instructions.md`.
- For newly created or substantially rewritten binding C++ files, also follow `.github/instructions/pybind-file-header.instructions.md`.
- For Python unit-test metadata conventions, also follow `.github/instructions/pybind-python-test-metadata.instructions.md`.
- For C++ naming consistency, follow `.github/instructions/isis-cpp-naming.instructions.md` when editing relevant C++ files.

## Task routing

- For binding implementation or extension, inspect `todo_pybind11.csv`, `class_bind_methods_details/`, and `src/` first.
- For Python validation or test additions, inspect `tests/` and `python/` first.
- For package-level exports, inspect `python/isis_pybind/__init__.py`.
- For progress tracking, update `pybind_progress_log.md` and `todo_pybind11.csv` when the tracked binding inventory or completion context changes.
- For workflow-oriented pybind tasks, also use `.github/skills/isis-pybind/SKILL.md`.

## Metadata defaults

- When adding authored comments or header metadata, default the author to `Geng Xun` unless the user specifies otherwise.
- Default date metadata to the current date unless the user specifies otherwise.

