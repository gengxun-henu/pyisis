# Pybind File Header Template

Use this template when creating a new binding file under `isis_pybind_standalone/src/`.

## Canonical default header example for single-class files

```cpp
// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS header: reference/upstream_isis/src/<mission_or_base>/objs/<ClassName>/<ClassName>.h
// Source class: Isis::<ClassName>
// Source header author(s): <Author Name(s)>
// Source header note: <optional short note, or omit if not needed>
// Binding author: Geng Xun
// Created: YYYY-MM-DD
// Updated: YYYY-MM-DD  Geng Xun <short update summary>
// Purpose: Expose Isis::<ClassName> to Python via pybind11.
```

## Canonical default header example for multi-class utility files

```cpp
// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/<mission_or_base>/objs/<FirstClass>/<FirstClass>.h
// - reference/upstream_isis/src/<mission_or_base>/objs/<SecondClass>/<SecondClass>.h
// Source classes: FirstClass, SecondClass
// Source header author(s): <Author Name(s), or note to see individual headers>
// Binding author: Geng Xun
// Created: YYYY-MM-DD
// Updated: YYYY-MM-DD  Geng Xun <short update summary>
// Purpose: Expose related ISIS utility bindings via pybind11.
```

## If upstream author metadata is missing

Use this exact line:

```cpp
// Source header author(s): not explicitly stated in upstream header
```

## Required ordering

- Put copyright and SPDX first.
- Keep one blank comment separator line before the source metadata block.
- Use `Source ISIS header:` / `Source class:` for single-class files.
- Use `Source ISIS headers:` / `Source classes:` for multi-class files.
- Prefer repository-relative upstream mirror paths under `reference/upstream_isis/...`.

## Issue/automation handoff note

Issue forms and automation may carry the source metadata content, but source files should still render that content using the canonical `//` header format above. Do not paste issue prose directly into a C++ file header.

## Notes

- Read the original ISIS header before filling this template.
- Keep upstream author information separate from the local binding author.
- Do not invent missing upstream author names.
- Preserve any repository-specific version field only if a nearby file already requires it.
- Block comment file headers are legacy-acceptable when preserving an old file, but they are no longer the default template for new or refreshed pybind binding files.
