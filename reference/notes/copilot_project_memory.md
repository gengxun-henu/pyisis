# Copilot project memory

This file is a lightweight, low-frequency memory note for this repository.
It should be referenced on demand instead of expanding always-on instructions.

## Stable repo facts

- Use the `asp360_new` Python interpreter for build, import, and test validation.
- For binding signatures and compile decisions, conda-installed ISIS headers/libs are the source of truth.
- Use `reference/upstream_isis/` mainly for implementation reading, lifecycle analysis, and upstream usage study.
- Prefer repository-relative paths in notes, plans, and reviews.

## Pybind defaults

- Prefer focused unit tests before broader validation.
- Treat missing external runtime data as an environment issue first, not automatically as a binding regression.
- Do not bind Qt `signals`/`slots` by default for QObject-derived ISIS classes unless explicitly needed.
- Prefer stable data methods and wrappers over Qt observer/event plumbing.

## Good candidates to store here later

- recurring build or import pitfalls
- common linker or undefined-symbol diagnosis patterns
- environment-specific skips or data dependencies
- directory conventions that are important but not needed in every chat
