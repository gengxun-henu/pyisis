---
description: "Use when editing Python unit tests under tests/unitTest/. Keeps module docstrings and Created/Last Modified metadata consistent for new or meaningfully expanded test files."
applyTo: "tests/unitTest/**/*.py"
---

# Pybind Python Test Metadata Rules

Use these rules when creating or editing Python unit test files under `tests/unitTest/`.

## Goal

Keep Python test files self-describing with lightweight metadata while preserving clean `unittest` discovery and avoiding excessive docstring churn.

Shared author, date, and short update-summary defaults live in `pybind-metadata-common.instructions.md`.

## Module docstring rules

- New unit test files should begin with a module docstring that includes:
  - a short purpose line
  - `Author:`
  - `Created:`
  - `Last Modified:`
- When a test file is meaningfully updated, add one short update-summary line near the top metadata stating:
  - a concise summary of the new coverage or expectation change

Recommended pattern:

- `"""`
- `Unit tests for ISIS [category] bindings`
- ``
- `Author: Geng Xun`
- `Created: 2026-03-26`
- `Last Modified: 2026-03-26`
- `Updated: 2026-03-26  Geng Xun added focused regression coverage for Cube construction and pre-create setters.`
- `Updated: 2026-04-09  Geng Xun fixed follow-up geometry assertions to preserve the intended API contract.`
- `"""`

## Updating existing test files

- If a file already has `Created:` / `Last Modified:` metadata, preserve `Created:` and update `Last Modified:` when the test logic changes meaningfully, such as:
  - adding a new test class
  - adding important new test coverage
  - changing expectations because the binding surface changed
  - fixing an actual test bug or environment-handling bug
- When you update `Last Modified:` for a meaningful test change, also append one short top-of-file update note summarizing the change in plain language.
- Preserve earlier meaningful `Updated:` lines instead of replacing them with the newest note.
- Keep each note short and coverage-focused; allow a compact running history, but avoid turning the module docstring into a long-form changelog.
- Do **not** update metadata for trivial formatting-only edits.

## When metadata is missing

- If an existing test file lacks a module docstring and you are substantially extending it, add a concise module docstring at the top.
- If the file already has an established project-specific module docstring, extend it instead of replacing it wholesale.

## Class and method tracking

- New substantial test classes may include a short class docstring with an `Added:` date when helpful.
- New nontrivial test methods may include a short docstring describing behavior under test; include an `Added:` date only when chronology is useful.
- Avoid repetitive timestamp docstrings on every tiny assertion-oriented method.

Example:

- `"""Test suite for Cube binding regression coverage. Added: 2026-03-26."""`

## Test-structure guardrails

- Keep files compatible with `python -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v`.
- Avoid import-time side effects beyond the existing shared test setup patterns used by `_unit_test_support.py`.
- Prefer concise docstrings and focused comments over large narrative blocks.

## Non-goals

- Do not rewrite stable test modules only to add metadata.
- Do not force `Added:` annotations onto every test method.
- Do not duplicate broad workflow guidance that already belongs in `pybind-testing.instructions.md`.