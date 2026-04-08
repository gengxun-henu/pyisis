---
description: "Use when creating or substantially rewriting pybind11 binding source/header files under src/. Ensures new pybind files include upstream header author metadata, current date, version info, and consistent file header structure."
applyTo: "src/**/*.{cpp,h}"
---

# Pybind File Header Conventions

Use these rules when creating a **new** pybind11 binding file, or when an existing binding file is being rewritten enough that its file header should be refreshed.

## Goal

Every newly created pybind file should include a short, consistent header comment that separates:

- the **upstream ISIS header/source metadata**
- the **local pybind binding author metadata**
- the **current creation/update date**

Default to one canonical source-file header layout so new files do not drift between multiple styles.

Shared author, date, and short update-summary defaults live in `pybind-metadata-common.instructions.md`.

## Required preparation

Before creating the new pybind file header:

1. Read the corresponding upstream ISIS header file first.
2. Extract any author / maintainer / copyright metadata that is explicitly present in that header.
3. Do **not** invent upstream author names if the header does not state them clearly.

## Required header fields for new pybind files

Unless the user explicitly requests a different format, include all of the following near the top of the new file:

- `Copyright ...` line at the very top of the file
- `SPDX-License-Identifier: MIT` immediately below copyright
- a blank line after SPDX before source metadata
- `Source ISIS header:` plus `Source class:` for a single-class binding file
- `Source ISIS headers:` plus `Source classes:` for a multi-class or utility binding file
- `Source header author(s):` author names from the upstream header, if explicitly present
- `Source header note:` use a clear note when upstream author metadata is absent
- `Binding author:` the local binding author
- `Created:` current date in `YYYY-MM-DD` format
- `Updated:` current date in `YYYY-MM-DD` format when appropriate
- one short update summary line near the header when meaningful work is added later
- a one-line `Purpose:` summary of what the binding file exposes

For upstream mirrored sources, prefer repository-relative paths under `reference/upstream_isis/...`.

## Rules for author metadata

- Keep upstream ISIS author metadata separate from the local pybind binding author.
- If the upstream header lists multiple authors, preserve the list in compact form.
- If no explicit upstream author is available, write:
  - `Source header author(s): not explicitly stated in upstream header`
- Never guess or hallucinate upstream authors from git history, nearby files, or copyright notices alone.

## Rules for date metadata

- For a brand-new file, set both `Created:` and `Updated:` to the current date.
- For edits to an existing file, preserve the original `Created:` value when present and refresh `Updated:` only when appropriate.
- When a meaningful later edit expands the binding surface, add or refresh a short human-readable update note close to the header.

## Style guidance

- Keep the header concise; do not create a large banner unless the surrounding file style already uses one.
- For new or refreshed pybind file headers, default to `//` line comments.
- Put copyright and SPDX first, then a blank line, then the source/binding metadata.
- For multi-class files, render `Source ISIS headers:` as a bullet list using `// - ...` lines.
- Prefer `reference/upstream_isis/...` repository-relative paths over `isis/src/...`, absolute paths, or machine-specific paths.
- Keep issue text or automation handoff notes as source content only; render the actual C++ file header using the canonical format below instead of pasting issue prose verbatim.

## Preferred fallback text

When upstream author metadata is missing, use this exact wording unless the user asks otherwise:

- `Source header author(s): not explicitly stated in upstream header`

## Template reference

Use this template as the default starting point:

- `doc_pybind11_learning/pybind_file_header_template.md`

## Canonical default templates

Single-class binding file:

`// Copyright (c) 2026 Geng Xun, Henan University`

`// SPDX-License-Identifier: MIT`

`//`

`// Source ISIS header: reference/upstream_isis/src/.../ClassName.h`

`// Source class: Isis::ClassName`

`// Source header author(s): ...`

`// Binding author: Geng Xun`

`// Created: YYYY-MM-DD`

`// Updated: YYYY-MM-DD  Geng Xun ...`

`// Purpose: Expose Isis::ClassName ...`

Multi-class or utility binding file:

`// Copyright (c) 2026 Geng Xun, Henan University`

`// SPDX-License-Identifier: MIT`

`//`

`// Source ISIS headers:`

`// - reference/upstream_isis/src/.../FirstClass.h`

`// - reference/upstream_isis/src/.../SecondClass.h`

`// Source classes: FirstClass, SecondClass`

`// Source header author(s): ...`

`// Binding author: Geng Xun`

`// Created: YYYY-MM-DD`

`// Updated: YYYY-MM-DD  Geng Xun ...`

`// Purpose: Expose ...`

## Non-goals

- Do not fabricate missing upstream metadata.
- Do not overwrite user-specified author metadata unless it conflicts with explicit instructions.
- Do not remove existing repository version fields that are already required by local conventions.
