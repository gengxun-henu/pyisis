---
description: "Use when editing C++ source files, Covers naming conventions for classes, methods, variables, members, enums."
applyTo: "*.{h,cpp}"
---

# ISIS C++ Naming Conventions

Follow the existing ISIS naming style in the file you are editing. Prefer modern ISIS naming for new code, but do not rename unrelated legacy identifiers just to enforce consistency.

## Default naming for new or modernized code

- Use `PascalCase` for class names, struct names, enum types, and file names.
- Use `lowerCamelCase` for methods, free functions, local variables, and parameter names.
- Use the `m_` prefix for member variables, followed by descriptive camelCase names.
- Prefer descriptive names over abbreviations unless the abbreviation is already standard in ISIS or domain code, such as `lat`, `lon`, `minX`, `maxX`, or `sn`.

## Examples from ISIS

- Modern methods: `setDegrees`, `setKilometers`, `serialNumberIndex`, `targetCenterDistance`
- Modern members: `m_radians`, `m_distanceInMeters`, `m_pairs`, `m_checkTarget`
- Class and file names: `Angle`, `Distance`, `SerialNumberList`, `SpiceRotation`

## Legacy compatibility rule

Many older ISIS files still use legacy naming conventions such as:

- `p_` member prefixes
- `PascalCase` method names like `SetBoxcarSize`, `StartProcess`, `PatternChip`, `Compose`

When editing a legacy file:

- preserve the local naming style unless there is a clear, scoped modernization effort
- avoid renaming unrelated methods or members
- keep new identifiers consistent with the surrounding file when the file is clearly legacy-styled

## Enums and constants

- Use `PascalCase` for enum types and usually for enum values.
- Preserve established domain-specific exceptions such as `WRT_RightAscension`.
- Preserve existing all-caps math and physical constants such as `PI`, `TWOPI`, and `DEG2RAD`.

## Practical rule for agents

When adding code:

1. Inspect nearby declarations in the same file.
2. Match the file's existing naming style.
3. If the file is already modernized, prefer `lowerCamelCase` methods and `m_` members.
4. Do not perform naming-only cleanup outside the requested change.

## Non-goals

- Do not mass-convert `p_` to `m_` unless the task is explicitly a naming modernization.
- Do not rename public APIs or long-standing ISIS identifiers without a strong reason.
- Do not mix `m_` and `p_` styles arbitrarily within the same local area.