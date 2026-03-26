---
description: "Use when editing pybind11 C++ binding files under isis_pybind_standalone/src. Keeps file-level Created/Updated metadata stable and requires concise date tracking for meaningful binding additions or fixes."
applyTo: "isis_pybind_standalone/src/**/*.{cpp,h}"
---

# Pybind C++ Metadata Maintenance Rules

Use these rules when editing existing pybind11 C++ binding source or helper header files under `isis_pybind_standalone/src/`.

This instruction complements `pybind-file-header.instructions.md`:

- `pybind-file-header.instructions.md` focuses on **new files** or substantial rewrites.
- this file focuses on **ongoing metadata maintenance** for normal edits.

## Goal

Keep C++ binding metadata consistent over time so file history is visible without causing noisy comment churn.

## File-level metadata rules

- Preserve an existing `Created:` date when it is already present.
- Refresh `Updated:` or `Last Modified:` to the current date when the edit is meaningful, such as:
  - adding a new bound class
  - adding or removing a bound method or enum
  - changing a Python-visible signature or return policy
  - fixing a real binding bug or import/runtime issue
  - materially changing file-level documentation
- Do **not** churn metadata for whitespace-only edits, formatting-only edits, or trivial comment cleanup.
- Use `YYYY-MM-DD` date format.
- Default binding author metadata to `Geng Xun` unless the user explicitly requests otherwise.

## When metadata is missing

- If an existing pybind C++ file has no file-level metadata and you are making a substantial change, add a compact header or metadata block that matches nearby repository style.
- For a brand-new file, also follow `pybind-file-header.instructions.md`.
- Prefer concise metadata over long banner comments.

## Tracking additions inside a file

- When adding a new class binding block or a substantial new method group, prefer one concise inline date note near the start of that block when it helps future readers.
- Good cases for inline notes:
  - a newly added `py::class_` block
  - a new cluster of related `.def(...)` entries
  - a targeted bug fix that changes exposed behavior
- Avoid adding a date comment before every single `.def(...)` line.

Example:

- `// Added: 2026-03-26 - expose Cube::statistics overloads`

## Style guidance

- Match the existing indentation and comment style of the file.
- Keep metadata compact and near the top of the file unless nearby files use another established pattern.
- If both `Updated:` and `Last Modified:` styles appear in the repository, preserve the style already used by the file you are editing instead of mixing both.

## Non-goals

- Do not rewrite a stable file header only to rename metadata fields.
- Do not add timestamp comments to every minor edit.
- Do not fabricate upstream ISIS author metadata; use the dedicated file-header instruction when new-file upstream metadata is needed.