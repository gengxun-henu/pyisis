---
description: "Use when editing pybind11 binding sources or Python unit tests that carry authored metadata. Centralizes shared author, date, and short update-summary conventions used across C++ and Python files."
applyTo: "{src/**/*.{cpp,h},tests/unitTest/**/*.py}"
---

# Shared Pybind Metadata Defaults

Use these shared rules when maintaining authored metadata in pybind C++ files under `src/` and Python unit tests under `tests/unitTest/`.

## Shared defaults

- Use `YYYY-MM-DD` date format unless the user explicitly requests another format.
- Default authored metadata to `Geng Xun` unless the user explicitly requests another author.
- Preserve an existing `Created:` date when it is already present.
- Refresh `Updated:` or `Last Modified:` only for meaningful code or test changes, not for whitespace-only or formatting-only edits.

## Shared update-summary rule

- When a meaningful update refreshes top-of-file metadata, add or refresh one short summary line near that metadata.
- The summary should state:
  - who made the update
  - the date
  - a concise description of what was exposed, fixed, or newly covered
- Keep the summary short and task-oriented; do not turn file metadata into a changelog.

Examples:

- `Updated: 2026-04-08  Geng Xun added ControlNetFilter regression coverage for newly exposed filters.`
- `// Updated: 2026-04-07  Geng Xun completed Apollo mission camera/helper binding fixes.`

## Scope note

- This file defines only the shared metadata defaults.
- Keep language-specific formatting and file-structure rules in:
  - `pybind-cpp-metadata.instructions.md`
  - `pybind-file-header.instructions.md`
  - `pybind-python-test-metadata.instructions.md`
