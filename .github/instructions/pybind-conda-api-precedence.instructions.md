---
description: "Use when binding, testing, or debugging ISIS pybind code against the asp360_new conda environment. Treat the active conda ISIS headers/libs as the compile-time API source of truth, and use reference/upstream_isis mainly for implementation and behavior reading. Keywords: conda API, asp360_new, ISIS_PREFIX, reference mismatch, upstream mirror drift, BundleSolutionInfo."
applyTo: "**/*.{py,cpp,h}"
---

# ISIS Conda API Precedence

Use this instruction for USGS ISIS pybind work in this repository when the active build and test target is the conda-based ISIS environment, especially `asp360_new`.

## Core rule

- Treat the **active conda ISIS headers and linked libraries** as the source of truth for what may be bound and compiled.
- Treat `reference/upstream_isis/` as a **reference mirror for reading implementation, lifecycle, defaults, usage, and tests**, not as the primary authority for the compile-time API surface.

In practice, when these differ:

- **conda environment API wins** for binding signatures and compile decisions
- `reference/upstream_isis/` remains valuable for understanding behavior and for building wrappers from APIs that are actually present in conda

## Why this rule exists

- The conda environment provides the actual headers and libraries used by this repository during configure, compile, link, import, and test.
- The mirrored upstream source under `reference/upstream_isis/` is extremely useful, but it may be from a nearby rather than perfectly identical ISIS revision.
- Small API drift is uncommon but real, especially for helper methods added for local convenience or pybind-specific transfer helpers.

## Read in this order for API decisions

1. Local binding/test context
	- current binding in `src/`
	- Python exports in `python/isis_pybind/__init__.py`
	- related tests in `tests/unitTest/`

2. Active conda ISIS headers
	- prefer `${ISIS_PREFIX}/include/isis/...` or the equivalent active conda include path
	- confirm declarations, overloads, return types, and helper availability here first

3. Active conda-linked runtime expectations
	- if needed, confirm that the intended API shape is compatible with the linked runtime libraries
	- for compile/import issues, trust the build environment over the mirror

4. Mirrored upstream source under `reference/upstream_isis/`
	- read `.h` and `.cpp` for implementation details, lifecycle, exceptions, defaults, and side effects
	- read upstream tests and call sites for usage patterns

5. Local wrapper design
	- if the mirror shows useful behavior but the conda API surface differs, implement a pybind wrapper using APIs that are actually available in the conda environment

## Rules that matter

- Do not bind a method only because it exists in `reference/upstream_isis/...`.
- Before binding any member function, constructor, or helper, confirm it exists in the active conda header set used by the build.
- If a helper exists in the mirrored upstream header but not in the conda header, do **not** call it from local binding code.
- If a mirrored helper would be useful, prefer a local wrapper/lambda built from conda-available stable APIs.
- When mirrored upstream declarations and conda declarations differ, write the binding against the conda declaration.
- When compile errors mention a missing member, treat that first as an API drift problem between the mirror and the active conda environment.
- When import or link errors occur, prioritize the actual conda-linked library surface over assumptions from the mirror.

## Practical example

For `BundleSolutionInfo`, the mirrored upstream header may expose pybind-oriented helpers such as:

- `setOutputStatisticsForPyBind(...)`
- `cloneBundleResultsForPyBind()`

If those helpers are absent from the active conda header in `asp360_new`, do not bind against them directly even if the mirror contains them. Instead:

- use the conda-available API such as `setOutputStatistics(...)` and `bundleResults()` when safe
- or write a local wrapper based on the conda-visible API surface

## Recommended phrasing in reviews and notes

- "Compile-time API verified against active conda ISIS headers."
- "reference/upstream_isis used for implementation reading, not as the binding signature authority."
- "Mirror/conda API drift detected; binding follows conda-installed headers and libraries."

## Avoid

- assuming the mirrored upstream revision exactly matches the conda package revision
- copying helper-method calls from `reference/upstream_isis/` into bindings without checking conda headers first
- treating mirror-only APIs as binding regressions in the local codebase