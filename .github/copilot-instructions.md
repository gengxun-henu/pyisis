# Copilot workspace instructions

This repository provides standalone pybind11 bindings and tests for exposing selected USGS ISIS functionality to Python.

Keep this file intentionally short to reduce Copilot context usage. `AGENTS.md` is the shared Codex/Copilot source of truth for repository-wide agent behavior. Put detailed or low-frequency guidance in scoped files under `.github/instructions/`, workflow procedures under `.github/skills/`, and project notes under `reference/notes/`.

## Working defaults

- Default to acting without asking for confirmation for low-risk, reversible changes.
- Only ask before high-risk actions such as destructive operations, secrets handling, or irreversible changes.
- Prefer replying in Chinese unless the user clearly requests another language.
- Execute first, then report results concisely.
- Prefer repository-relative paths in notes, plans, reviews, and CI-facing guidance.
- Preserve unrelated local changes. Do not revert, delete, or reformat files outside the task scope.
- Match existing repository style and local helper APIs before introducing new abstractions.

## Environment and validation

- Prefer the Python interpreter from the `asp360_new` environment for build, test, and validation work.
- For deep-learning experiment scripts under `examples/experiment_methods/` that depend on LightGlue, LoFTR, SuperGlue, or similar ML matcher stacks, prefer the Python interpreter from the `deep-learning` conda environment and switch to it before validation when `asp360_new` lacks the required packages.
- After modifying code, run the smallest relevant validation first.
- Prefer focused unit tests over broad validation when a smaller targeted check is available.
- Always set `ISISDATA` before running tests.

## Pybind defaults

- For binding signatures and compile decisions, treat the active conda ISIS headers and libraries as the source of truth; use the optional `reference/upstream_isis/` checkout mainly for implementation and behavior reading, restoring it with `python tools/dev/sync_upstream_isis.py` when needed.
- For QObject-derived ISIS classes, default to **not** binding Qt `signals`/`slots` into Python unless the user explicitly asks for that behavior.
- Prefer exposing stable data methods, mutators, queries, and enums over Qt observer/event plumbing.
- When binding, add `#include <pybind11/pybind11.h>` and `#include <pybind11/stl.h>` when necessary.

## Git, worktree, and local-file guardrails

- Before publish, merge, cleanup, or PR work, start with `git status --short --branch`.
- For larger features, benchmarks, or design-heavy work, prefer an isolated branch under `.worktrees/` and report the exact worktree path and branch.
- If the user invokes a publish or merge-to-main workflow, complete the flow end-to-end: validate, commit, push, open/merge PR, sync local `main`, and clean up the linked worktree or branch when appropriate.
- If a PR is mergeable and local validation has already been reported, queued or pending GitHub gate jobs are not blocking.
- Treat `.gitignore` and `print.prt` as local guardrail files. Do not stage, commit, delete, restore, or otherwise modify them unless the user explicitly names the file and asks for that operation.

## Scoped instruction map

The files under `.github/instructions/` are shared Copilot/Codex scoped instructions. Keep path-specific rules there so both tools use the same file-header, metadata, naming, validation, and layout guidance.

- `src/**/*.{cpp,h}`: `pybind-cpp-metadata.instructions.md`, `pybind-file-header.instructions.md`, `isis-cpp-naming.instructions.md`
- `tests/unitTest/**/*.py`: `pybind-python-test-metadata.instructions.md`, `pybind-metadata-common.instructions.md`
- `examples/**` and `scripts/**`: `python-example-cli-naming.instructions.md`, `example-file-metadata.instructions.md`
- pybind work in `src/`, `python/`, `tests/unitTest/`, or `tests/smoke_import.py`: `pybind-testing.instructions.md`, `pybind-upstream-source-reading.instructions.md`, `pybind-conda-api-precedence.instructions.md`
- repeated cube/camera batch-style operations: `isis-cube-batch-operations.instructions.md`
- reference/test-data placement: `reference-data-layout.instructions.md`

## Workflow routing

- For workflow-oriented pybind tasks, use `.github/skills/isis-pybind/SKILL.md` as the main task procedure.
- For queue-based continuous rollout work across unfinished classes, use `.github/skills/pybind-rollout-execution/SKILL.md` as the companion rollout procedure.
- Keep low-frequency project memory in `reference/notes/copilot_project_memory.md` instead of expanding this file.
