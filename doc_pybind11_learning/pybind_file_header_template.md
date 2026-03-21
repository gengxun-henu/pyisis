# Pybind File Header Template

Use this template when creating a new binding file under `isis_pybind_standalone/src/`.

## Recommended header example

```cpp
/**
 * @file
 * @brief Pybind11 bindings for <ClassName>
 *
 * Source ISIS header: <path/to/original/header.h>
 * Source class: <ClassName>
 * Source header author(s): <Author Name(s)> 
 * Source header note: <optional short note, or omit if not needed>
 * Binding author: Geng Xun
 * Created: YYYY-MM-DD
 * Updated: YYYY-MM-DD
 * Version: <keep the repository's existing version metadata format here>
 * Purpose: Expose <ClassName> to Python via pybind11.
 */
```

## If upstream author metadata is missing

Use this exact line:

```cpp
 * Source header author(s): not explicitly stated in upstream header
```

## Minimal compact variant

If nearby files use a shorter style, this compact form is acceptable as long as the same metadata is retained:

```cpp
// Source ISIS header: <path/to/original/header.h>
// Source class: <ClassName>
// Source header author(s): <Author Name(s)>
// Binding author: Geng Xun
// Created: YYYY-MM-DD
// Updated: YYYY-MM-DD
// Version: <existing repository version metadata>
// Purpose: Expose <ClassName> to Python via pybind11.
```

## Notes

- Read the original ISIS header before filling this template.
- Keep upstream author information separate from the local binding author.
- Do not invent missing upstream author names.
- Preserve any repository-specific version field already required by existing pybind files.
