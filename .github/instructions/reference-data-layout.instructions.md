---
description: "Use when organizing, adding, or referencing upstream ISIS source mirrors, reference materials, test assets, fixture data, mock data, or repository samples. Explains what belongs in reference/ versus tests/data/ and what should not be committed. Keywords: reference, tests/data, fixture, upstream_isis, mock data, sample data, test asset, repository layout."
applyTo: "**/*"
---

# Reference vs Data Layout Rules

Use these rules when deciding where files should live in this repository.

## Core split

- Put human-read reference material in `reference/`.
- Put test runtime inputs in `tests/data/`.
- Do not mix reference-only material with files that unit tests or smoke tests read directly.

## Put in `reference/`

Use `reference/` for materials that help understand or implement bindings, but are not the primary runtime input for tests.

Typical examples:

- mirrored upstream ISIS source under `reference/upstream_isis/`
- upstream test source code and usage examples
- API reading notes, behavior summaries, lifecycle analysis, and design notes
- documents kept for comparison, review, or implementation guidance

## Put in `tests/data/`

Use `tests/data/` for files that repository tests actually open, parse, or depend on at runtime.

Typical examples:

- fixture cubes, labels, PVL files, and tables used by unit tests
- small derived samples copied or minimized from upstream test assets
- mock ISISDATA content such as `tests/data/isisdata/mockup/`
- stable runtime inputs used by `tests/unitTest/` or `tests/smoke_import.py`

## Preferred subdirectories

- `reference/upstream_isis/` for upstream ISIS source and upstream test code mirrors
- `reference/analysis/` or `reference/notes/` for local reading notes and behavior summaries
- `tests/data/upstream_derived/` for small test inputs derived from upstream assets
- `tests/data/isisdata/mockup/` for mock ISISDATA runtime content

## Path guidance

- In instructions, reviews, plans, and CI-facing notes, prefer repository-relative paths.
- For upstream mirrored source, prefer `reference/upstream_isis/...`.
- For test assets, prefer `tests/data/...`.
- Avoid machine-specific absolute paths in reusable guidance.

## Do not commit by default

Avoid committing these unless there is a strong, specific reason:

- full upstream test-data dumps when only a small subset is needed
- large mission products or bulky binary datasets not required for routine tests
- temporary debug outputs, generated cubes, logs, or crash artifacts
- data that only works through local absolute paths or personal environment setup

## Practical rule

Ask two questions:

1. Is this mainly for people to read or compare?
   - yes -> `reference/`
2. Will tests directly read this file at runtime?
   - yes -> `tests/data/`

If both seem true, prefer splitting the materials: keep source/reference context in `reference/` and place the minimized runtime fixture in `tests/data/`.
