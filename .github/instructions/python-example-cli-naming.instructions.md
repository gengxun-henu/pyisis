---
description: "Use when editing Python or Bash example CLIs, wrapper scripts, or their user-facing docs. Enforce kebab-case command-line options in examples/controlnet_construct and related scripts/docs. Keywords: argparse, shell option naming, kebab-case, snake_case, CLI flags, examples, usage.md."
applyTo: "{examples,scripts}/**/*.{py,sh,md}"
---

# Python Example CLI Naming Conventions

Use these rules when editing Python/Bash example programs, wrapper scripts, or their user-facing documentation in this repository.

## Core rule

- Public command-line option names must use `--kebab-case`.
- Do not expose mixed public spellings such as `--some_option` and `--some-option` unless the user explicitly requests a temporary compatibility window.
- For this repository's example CLIs, prefer a clean cutover to kebab-case over indefinite alias support.

## Internal naming remains Pythonic

- Keep internal Python variable names, `argparse` destinations, JSON keys, and shell variables in `snake_case` when that is the natural local style.
- It is valid for `argparse` to expose `--num-worker-parallel-cpu` while the parsed value is read as `args.num_worker_parallel_cpu`.

## Required synchronization

When you change a public CLI flag in an example program or wrapper script, also update the matching user-facing materials in the same task:

- shell `usage()` text
- Markdown usage guides such as `usage.md`
- command templates and snippets
- focused unit tests that assert CLI forwarding or help output

Do not leave code, help text, and docs using different spellings for the same public option.

## Scope guidance

- Apply this rule to user-facing CLIs under `examples/` and `scripts/`.
- Prefer repository-active docs and scripts over archived notes.
- Avoid broad cleanup of historical drafts or `nouse/` materials unless the user explicitly asks for archive synchronization too.

## Practical examples

- Prefer `--use-parallel-cpu` over `--use_parallel_cpu`
- Prefer `--num-worker-parallel-cpu` over `--num_worker_parallel_cpu`
- Prefer `--overlap-size-x` over `--overlap_size_x`

## Non-goals

- Do not rename internal Python variables purely to mirror CLI spelling.
- Do not add long-term underscore aliases just because `argparse` can support them.
- Do not use `applyTo: "**/*"`-style overly broad scope for this rule.