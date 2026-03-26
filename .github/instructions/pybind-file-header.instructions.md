---
description: "Use when creating or substantially rewriting pybind11 binding source/header files under isis_pybind_standalone/src. Ensures new pybind files include upstream header author metadata, current date, version info, and consistent file header structure."
applyTo: "isis_pybind_standalone/src/**/*.{cpp,h}"
---

# Pybind File Header Conventions

Use these rules when creating a **new** pybind11 binding file, or when an existing binding file is being rewritten enough that its file header should be refreshed.

## Goal

Every newly created pybind file should include a short, consistent header comment that separates:

- the **upstream ISIS header/source metadata**
- the **local pybind binding author metadata**
- the **current creation/update date**
- the **version information already used by this repository**

## Required preparation

Before creating the new pybind file header:

1. Read the corresponding upstream ISIS header file first.
2. Extract any author / maintainer / copyright metadata that is explicitly present in that header.
3. Do **not** invent upstream author names if the header does not state them clearly.

## Required header fields for new pybind files

Unless the user explicitly requests a different format, include all of the following near the top of the new file:

- `Source ISIS header:` absolute or repository-relative path to the original ISIS header
- `Source class:` the ISIS class being exposed
- `Source header author(s):` author names from the upstream header, if explicitly present
- `Source header note:` use a clear note when upstream author metadata is absent
- `Binding author:` default to `Geng Xun` unless the user specifies otherwise
- `Created:` current date in `YYYY-MM-DD` format
- `Updated:` current date in `YYYY-MM-DD` format when appropriate
- existing repository version information, if this repository already places version metadata in the file header
- a one-line `Purpose:` summary of what the binding file exposes

## Rules for author metadata

- Keep upstream ISIS author metadata separate from the local pybind binding author.
- If the upstream header lists multiple authors, preserve the list in compact form.
- If no explicit upstream author is available, write:
  - `Source header author(s): not explicitly stated in upstream header`
- Never guess or hallucinate upstream authors from git history, nearby files, or copyright notices alone.

## Rules for date metadata

- Use `YYYY-MM-DD` format.
- For a brand-new file, set both `Created:` and `Updated:` to the current date.
- For edits to an existing file, preserve the original `Created:` value when present and refresh `Updated:` only when appropriate.

## Style guidance

- Keep the header concise; do not create a large banner unless the surrounding file style already uses one.
- Prefer line comments or a compact C-style block that matches nearby binding files.
- Preserve any existing required version metadata already used in the repository.
- If a nearby module already has an accepted header style, follow that style while still including the required metadata above.

## Preferred fallback text

When upstream author metadata is missing, use this exact wording unless the user asks otherwise:

- `Source header author(s): not explicitly stated in upstream header`

## Template reference

Use this template as the default starting point:

- `isis_pybind_standalone/doc_pybind11_learning/pybind_file_header_template.md`

## Non-goals

- Do not fabricate missing upstream metadata.
- Do not overwrite user-specified author metadata unless it conflicts with explicit instructions.
- Do not remove existing repository version fields that are already required by local conventions.
