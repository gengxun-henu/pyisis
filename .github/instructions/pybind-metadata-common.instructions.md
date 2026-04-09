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
- Preserve prior meaningful `Updated:` history lines instead of overwriting them.
- When a file already keeps multiple `Updated:` entries, append the new one in chronological order and leave earlier entries intact.

## Shared update-summary rule

- When a meaningful update refreshes top-of-file metadata, append one short summary line near that metadata.
- The summary should state:
  - who made the update
  - the date
  - a concise description of what was exposed, fixed, or newly covered
- Do not delete earlier meaningful update lines just to keep only the most recent note.
- Keep each summary short and task-oriented; preserve a compact running history instead of turning file metadata into a verbose changelog.

Examples:

- `Updated: 2026-04-08  Geng Xun added ControlNetFilter regression coverage for newly exposed filters.`
- `// Updated: 2026-04-07  Geng Xun completed Apollo mission camera/helper binding fixes.`
- `Updated: 2026-04-09  Geng Xun fixed Intercept SurfacePoint regression expectations to match NAIF kilometer coordinates.`

## Scope note

- This file defines only the shared metadata defaults.
- Keep language-specific formatting and file-structure rules in:
  - `pybind-cpp-metadata.instructions.md`
  - `pybind-file-header.instructions.md`
  - `pybind-python-test-metadata.instructions.md`
