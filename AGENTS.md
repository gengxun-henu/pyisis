# AGENTS.md

## Purpose and Scope

These instructions are the primary agent-facing guidance for this repository.
They are written for Codex and other coding agents working in this checkout.

This repository provides standalone pybind11 bindings and tests for exposing
selected USGS ISIS functionality to Python. It currently maintains ISIS 9.0.0
and ISIS 10.0.0 targets and must remain extensible to later ISIS releases. The
core deliverable is `isis_pybind._isis_core`, a pybind11 extension module.

All dependencies are managed via conda. Do not introduce pip/npm workflows
unless the user explicitly asks for them.

## Operating Defaults

- Prefer replying in Chinese unless the user clearly requests another language.
- Default to acting without asking for confirmation for low-risk, reversible
  changes.
- Ask before destructive operations, secrets handling, irreversible changes, or
  changes that would overwrite unrelated user work.
- Execute the smallest useful step first, then report results concisely.
- Prefer repository-relative paths in notes, plans, reviews, and CI-facing
  guidance.
- Match existing repository style and local helper APIs before introducing new
  abstractions.

## Repository Context

- Project type: C++/Python binding project for USGS ISIS.
- Main extension module: `isis_pybind._isis_core`.
- ISIS 9.0.0 conda environment: `asp360_new`.
- ISIS 10.0.0 conda environment: `asp370` (USGS
  `isis 10.0.0 h1f94ec8_1`, CPython 3.13).
- Built module:
  `build/python/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so`.
- Mock ISISDATA path: `tests/data/isisdata/mockup`.

## Environment

Use the Python interpreter and compiler from the target ISIS conda environment.
Use `asp360_new` for the ISIS 9 baseline and shared compatibility work; use
`asp370` for ISIS 10-specific compile, link, import, and behavior validation.
Keep ISIS 10 on `csm 3.0.3.3`: unconstrained `csm 3.1.0` does not provide the
`libcsmapi.so.3` ABI required by the official ISIS 10.0.0 binary.

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
```

For deep-learning experiment scripts under `examples/experiment_methods/` that
depend on LightGlue, LoFTR, SuperGlue, or similar ML matcher stacks, prefer the
Python interpreter from the `deep-learning` conda environment when `asp360_new`
lacks the required packages.

## Build Commands

Configure only when needed, such as after changing `CMakeLists.txt` or build
settings.

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"

cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"

cmake --build build -j$(nproc)
```

## Running Tests

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"

# Smoke test, fast.
python tests/smoke_import.py

# Individual test modules, recommended for iteration.
python -m unittest tests.unitTest.<module_name> -v

# Full suite, slower.
python -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
```

The forward intersection example is the preferred full-stack hello-world check:

```bash
python examples/forward_intersection/forward_intersection.py \
  tests/data/mosrange/EN0108828322M_iof.cub \
  tests/data/mosrange/EN0108828327M_iof.cub \
  64.0 512.0
```

## Validation Strategy

- After modifying code, run the smallest relevant validation first.
- Prefer focused unit tests over broad validation when a targeted check exists.
- For pybind binding changes, validate import plus the relevant unit module.
- For CLI/example changes, run the specific script or a narrow smoke path.
- Run the full unit suite only when the change affects shared behavior or when
  the user asks for broad validation.
- Always set `ISISDATA` before running tests.

## Pybind Binding Defaults

- Treat the active conda ISIS headers and libraries as the source of truth for
  binding signatures and compile decisions.
- Use the optional `reference/upstream_isis/` checkout mainly for implementation
  and behavior reading, not as the final authority over the active conda API.
  Restore its pinned revision with `python tools/dev/sync_upstream_isis.py` when
  source reading is needed and the directory is absent.
- For QObject-derived ISIS classes, default to not binding Qt `signals` or
  `slots` into Python unless the user explicitly asks for that behavior.
- Prefer exposing stable data methods, mutators, queries, and enums over Qt
  observer/event plumbing.
- Add `#include <pybind11/pybind11.h>` and `#include <pybind11/stl.h>` when
  necessary.

## ISIS Version Expansion Policy

Before adding support for a new ISIS major or minor version, read and follow
`docs/isis-version-expansion-policy.md`. This policy is mandatory for Codex,
Claude Code, and other repository agents.

Core requirements:

- Record the exact upstream tag/commit and the exact conda package version,
  build string, channel, subdir, and target platform. A semantic version alone
  is not enough.
- Treat the active conda prefix as the compile/link authority. Use the official
  tag and `CHANGELOG.md` as important context, but do not assume they completely
  describe channel-specific patches or the installed API.
- Audit both directions: added, removed, renamed, and same-name changed headers.
  Also compare public classes, inheritance, constructors, methods, free
  functions, enums, default arguments, deprecation markers, application entry
  points, and installed library exports.
- Keep the automatically discovered raw diff separate from the curated binding
  queue. Every discovered item must be classified as bind, compatibility-only,
  replaced/renamed, internal/GUI/test-only, or blocked, with evidence and a
  reason. "All new functionality complete" means no unclassified item remains;
  it does not mean exposing unsafe third-party or internal APIs.
- Verify declarations against exported symbols before binding. Check Linux
  shared libraries and Windows DLL/import libraries independently.
- Prefer shared binding sources for compatible APIs and use explicit
  version-feature guards only for real API differences. Do not duplicate the
  ISIS 9 binding tree just to create an ISIS 10 tree.
- Do not publish a dual-version release until the required Linux/Windows ×
  ISIS-version build, wheel-install, import, and focused-test matrix passes.
  Release assets and reports must identify the ISIS version/build, OS,
  architecture, Python ABI, and wheel hash.

## Git and Worktree Rules

- Before publish, merge, cleanup, or PR work, start with
  `git status --short --branch`.
- Preserve unrelated local changes. Do not revert, delete, or reformat files
  outside the task scope.
- For larger features, benchmarks, or design-heavy work, prefer an isolated
  branch under `.worktrees/` and report the exact worktree path and branch.
- For paper-related coding tasks (especially experiment plotting, paper-specific
  data processing, and manuscript-support scripts), default to placing runnable
  scripts under `docs/paper/` (for example `docs/paper/scripts/`) rather than
  under general `examples/` or `tools/` paths, unless the user explicitly asks
  for a reusable repository-wide utility.
- If the user invokes a publish or merge-to-main workflow, complete the flow
  end-to-end: validate, commit, push, open/merge PR, sync local `main`, and
  clean up the linked worktree or branch when appropriate.
- In this repository, if a PR is mergeable and local validation has already
  been reported, queued or pending GitHub gate jobs are not blocking.

## Disk Space and Build Cleanup

- This workstation has limited disk space. After a build has completed and the
  required result has been verified, retain only artifacts needed for later
  use (for example wheels, shared libraries/DLLs, install packages, and reports)
  and promptly remove disposable build trees, downloaded CI copies, extracted
  staging directories, caches created only for that build, and other temporary
  files. Resolve and preserve the exact final artifacts before cleanup; never
  delete user files, reusable source/reference checkouts, or an active build.

## Local File Guardrails

- Treat `.gitignore` and `print.prt` as local guardrail files.
- Do not stage, commit, delete, restore, or otherwise modify `.gitignore` or
  `print.prt` unless the user explicitly names the file and asks for that
  operation.
- `print.prt` can be generated as an ISIS side effect. Keep it out of commits
  and PRs by default.

## Scoped Instruction Map

The files under `.github/instructions/` are shared Copilot/Codex scoped
instructions. Copilot may apply them automatically. Codex must read the relevant
file explicitly before creating or meaningfully editing a matching path, then
follow both `AGENTS.md` and the scoped instruction.

Use the `applyTo` front matter in each scoped instruction as the authority for
which files it covers. When multiple scoped instructions match, apply all of
them unless they conflict; if they conflict, prefer the more specific rule.

Consult these scoped instructions when relevant instead of expanding this file
with low-frequency details:

- `src/**/*.{cpp,h}`:
  `.github/instructions/pybind-cpp-metadata.instructions.md`,
  `.github/instructions/pybind-file-header.instructions.md`,
  `.github/instructions/isis-cpp-naming.instructions.md`
- `tests/unitTest/**/*.py`:
  `.github/instructions/pybind-python-test-metadata.instructions.md`,
  `.github/instructions/pybind-metadata-common.instructions.md`
- `examples/**` and `scripts/**`:
  `.github/instructions/python-example-cli-naming.instructions.md`,
  `.github/instructions/example-file-metadata.instructions.md`
- Pybind work in `src/`, `python/`, `tests/unitTest/`, or
  `tests/smoke_import.py`:
  `.github/instructions/pybind-testing.instructions.md`,
  `.github/instructions/pybind-upstream-source-reading.instructions.md`,
  `.github/instructions/pybind-conda-api-precedence.instructions.md`
- Repeated cube/camera batch-style operations:
  `.github/instructions/isis-cube-batch-operations.instructions.md`
- Reference/test-data placement:
  `.github/instructions/reference-data-layout.instructions.md`

For workflow-oriented pybind tasks, use `.github/skills/isis-pybind/SKILL.md`
as the main task procedure. For queue-based continuous rollout work across
unfinished classes, use `.github/skills/pybind-rollout-execution/SKILL.md`.

Keep low-frequency project memory in `reference/notes/copilot_project_memory.md`
instead of expanding this file.

## Coding Discipline

- State important assumptions. If multiple interpretations would change the
  implementation, surface the tradeoff before editing.
- Prefer the minimum code that solves the requested problem. Avoid speculative
  flexibility and single-use abstractions.
- Make surgical changes. Touch only files and lines that trace directly to the
  task.
- Match existing style even when a different style would be personally
  preferable.
- Clean up imports, variables, helpers, and generated artifacts introduced by
  your own change. Do not remove pre-existing dead code unless asked.
- Convert tasks into verifiable success criteria, then loop until the relevant
  check passes or the blocker is explicit.

## Gotchas

- The system compiler (`/usr/bin/c++`) cannot link against the conda
  environment's libstdc++. Always use the conda compiler
  (`x86_64-conda-linux-gnu-c++`) explicitly via `-DCMAKE_CXX_COMPILER`.
- `build_test_smoke.sh` hardcodes `/home/gengxun/miniconda3` as the conda path.
  Use `PYISIS_CONDA_SH=$HOME/miniconda3/etc/profile.d/conda.sh` to override.
- The full unit test suite is slow. Use `tests/smoke_import.py` or selected
  test modules for quick validation.
- After rebuilding, no server restart is needed. The `.so` is loaded fresh each
  time Python imports `isis_pybind`.
