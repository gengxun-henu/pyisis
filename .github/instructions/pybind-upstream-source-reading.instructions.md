---
description: "Use when doing USGS ISIS pybind binding, pybind11 unit tests, binding bug fixes, Cube/Camera lifecycle debugging, or upstream API reading. Read local inventory first, then upstream .h, then upstream .cpp, then upstream usage, so tests follow real ISIS behavior instead of signatures alone. Keywords: pybind, unit test, upstream .cpp, lifecycle, create/open order, IException, return policy."
applyTo: "**/*.{py,cpp,h}"
---

# ISIS Upstream Reading Order

Use this instruction when binding, testing, or debugging a USGS ISIS class.

## Compile-surface precedence

- For this repository's actual pybind compile and test work, treat the active conda ISIS environment referenced by `ISIS_PREFIX` / `CONDA_PREFIX` as the source of truth for available headers and bindable API surface.
- Treat `reference/upstream_isis/` as the preferred mirror for upstream implementation reading, lifecycle analysis, and usage/reference study.
- If the mirrored upstream API and the active conda headers differ, bind against the **conda-installed API**, not the mirrored one.
- Use the mirror to understand behavior and to design wrappers, but do not assume mirror-only helpers are safe to call from binding code.

## Canonical upstream source location

- In this repository, treat `reference/upstream_isis/` as the default mirror for upstream USGS ISIS source and upstream test code.
- When referring to upstream files in notes, plans, reviews, GitHub web discussions, or CI-oriented instructions, use repository-relative paths such as `reference/upstream_isis/...`.
- Keep broader repository layout decisions aligned with `reference-data-layout.instructions.md`.
- If an expected upstream file is not present under `reference/upstream_isis/`, say so explicitly and do not invent a path.

## Read in this order

1. Local inventory and current repo context
	- `todo_pybind11.csv`
	- `class_bind_methods_details/methods_inventory_summary.csv`
	- target `*_methods.csv`
	- current binding in `src/`
	- similar tests in `tests/unitTest/`

2. Active conda ISIS `.h`
	- prefer the headers actually used by the active build, such as `${ISIS_PREFIX}/include/isis/...`
	- compile-time declarations, overloads, helper availability, return types, inheritance

3. Upstream mirrored `.h`
	- prefer the mirrored file under `reference/upstream_isis/`
	- compare against conda headers when needed; use primarily for nearby upstream context

4. Upstream `.cpp`
	- prefer the mirrored file under `reference/upstream_isis/`
	- lifecycle rules
	- default values
	- exceptions and programmer-error guards
	- side effects, ownership, file I/O, data/plugin dependencies

5. Upstream usage
	- prefer upstream tests or call sites mirrored under `reference/upstream_isis/`
	- unit tests, apps, call sites, common call order

6. Local pybind mapping
	- existing style in `src/`
	- `python/isis_pybind/__init__.py`
	- similar binding and return-policy patterns

7. Behavior-driven tests
	- test what ISIS actually allows, not what the signature seems to allow

## Rules that matter

- Do not trust the `.h` alone for stateful classes.
- Do not trust the mirrored upstream `.h` over the active conda headers for binding signatures.
- For `Cube`, `Camera`, factories, I/O classes, and manager classes, assume the `.cpp` is required.
- When a binding or binding-status change is completed, sync the tracking artifacts in the same task: `todo_pybind11.csv`, `class_bind_methods_details/methods_inventory_summary.csv`, and the target `class_bind_methods_details/*_methods.csv`.
- Treat code plus the target `*_methods.csv` as the immediate source of truth while editing, and do not leave `methods_inventory_summary.csv` stale after a class is newly bound or its coverage materially changes.
- If a setter fails after `create()` or `open()`, treat it as a pre-create lifecycle method.
- If upstream usage contradicts your guess from the header, follow upstream usage.
- If Python behavior intentionally differs from raw C++, test the exported Python API.
- Before binding a method directly, confirm that it has a real implementation in the mirrored upstream source or is otherwise present in the linked runtime library; a declaration alone is not enough.
- Before binding a helper method or pybind-oriented convenience API, confirm that it exists in the active conda header set, not only in the upstream mirror.
- For older ISIS mission-camera and helper classes, assume that some methods may be declared in `.h` but absent from the compiled library until you verify otherwise.
- If a method is declared upstream but you cannot find an inline definition in the header, cannot find an implementation under `reference/upstream_isis/...`, and cannot confirm that the symbol is exported by the linked library, do not bind the member-function pointer directly.
- Treat pybind import-time `undefined symbol` failures as a linkability-audit problem first, not automatically as a Python packaging, import-path, or test-discovery problem.
- When investigating this class of failure, check in order: local binding line, mirrored upstream `.h`, mirrored upstream `.cpp`, upstream usage sites, and then the actual shared-library exports if needed.
- If the desired Python API is still useful but the upstream method is unavailable, prefer a local pybind wrapper or lambda built from already-implemented stable APIs instead of exposing a missing C++ symbol.
- If the desired Python API is still useful but the mirrored helper is unavailable in the conda headers, prefer a local pybind wrapper or lambda built from conda-available stable APIs instead of exposing the mirrored helper directly.
- If a method is declared in `.h` but has no inline definition in the header and no corresponding implementation in upstream source, record that reason in the target `class_bind_methods_details/*_methods.csv`, account for it explicitly when updating coverage instead of treating it as ordinary unfinished binding work, and add a brief note in `todo_pybind11.csv`.
- Example: if `ApolloPanoramicCamera::intOriResidualsReport()` is declared in `reference/upstream_isis/src/apollo/objs/ApolloPanoramicCamera/ApolloPanoramicCamera.h` but has no inline header definition and no implementation in upstream source, do not mark it as a routine missing binding item. In `class_bind_methods_details/apollo_apollo_panoramic_camera_methods.csv`, note that the direct method binding is unavailable because upstream provides no implementation and that Python uses a wrapper if one is added. When updating coverage, account for that item explicitly instead of treating it as ordinary unfinished exposure work. In `todo_pybind11.csv`, keep the note short, for example: `头文件声明但上游无实现；直接符号未绑定，Python 侧如需接口则改用 wrapper`.

## Testing guidance

- Pre-create setters should usually be tested before `create()`.
- Post-open operations should only be tested after valid `open()` or `create()` paths.
- A test that matches a signature but violates real ISIS lifecycle rules is a test bug, not automatically a binding bug.
- Environment-heavy behavior should be scoped carefully or skipped when external data is required.

## Avoid

- binding methods only because they appear in the header
- using `/home/...`-style absolute paths in reusable instructions when `reference/upstream_isis/...` works
- writing tests from method names alone
- reporting upstream lifecycle constraints as pybind regressions without evidence that the Python layer changed them
