---
description: "Use when creating or editing example Python or Bash code under examples/ or scripts/. Require concise top-of-file metadata headers so generated example code carries purpose, author, created date, and update history. Keywords: example header, module docstring, shell header, Author, Created, Updated, examples, scripts."
applyTo: "{examples,scripts}/**/*.{py,sh}"
---

# Example File Metadata Rules

Use these rules when creating or meaningfully editing runnable example code under `examples/` or `scripts/`.

## Goal

Keep example entrypoints and helper modules self-describing so newly generated example code does not appear without a recognizable file header.

## Python example files

- New Python example files should begin with a module docstring that includes:
  - a short purpose line
  - `Author:`
  - `Created:`
  - at least one `Updated:` line for meaningful additions or follow-up fixes
- Prefer the compact pattern:

  - `"""Short purpose line.`
  - ``
  - `Author: Geng Xun`
  - `Created: YYYY-MM-DD`
  - `Updated: YYYY-MM-DD  Geng Xun ...`
  - `"""`

- Keep the docstring at the true file top, before imports and executable code.
- If the file is a thin compatibility wrapper, it should still carry the same metadata block.
- For package-level `__init__.py` files, a concise metadata docstring is still preferred when the file exposes workflow-facing helpers.

## Shell example files

- Shell example scripts should keep the shebang on line 1.
- Immediately after the shebang, add a concise comment header that includes:
  - one-line purpose summary
  - `Author:`
  - `Created:`
  - `Updated:`
- Prefer the compact pattern:

  - `#!/usr/bin/env bash`
  - `# Short purpose line.`
  - `#`
  - `# Author: Geng Xun`
  - `# Created: YYYY-MM-DD`
  - `# Updated: YYYY-MM-DD  Geng Xun ...`

## Update behavior

- Preserve an existing `Created:` date when present.
- Append new `Updated:` lines for meaningful changes; do not delete earlier useful history.
- Use `YYYY-MM-DD` date format unless the user explicitly requests another format.
- Do not churn metadata for whitespace-only or formatting-only edits.

## Scope notes

- Apply this rule to runnable example code and shell entrypoints under `examples/` and `scripts/`.
- Keep user-facing CLI spelling rules in `python-example-cli-naming.instructions.md`; this file only governs top-of-file metadata.
- Favor concise headers over long narrative blocks. Detailed design notes belong in Markdown docs, not in every file header.