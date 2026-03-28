---
description: "Use when doing USGS ISIS pybind binding, pybind11 unit tests, binding bug fixes, Cube/Camera lifecycle debugging, or upstream API reading. Read local inventory first, then upstream .h, then upstream .cpp, then upstream usage, so tests follow real ISIS behavior instead of signatures alone. Keywords: pybind, unit test, upstream .cpp, lifecycle, create/open order, IException, return policy."
applyTo: "**/*.{py,cpp,h}"
---

# ISIS Upstream Reading Order

Use this instruction when binding, testing, or debugging a USGS ISIS class.

## Canonical upstream source location

- In this repository, treat `reference/upstream_isis/` as the default mirror for upstream USGS ISIS source and upstream test code.
- When referring to upstream files in notes, plans, reviews, GitHub web discussions, or CI-oriented instructions, use repository-relative paths such as `reference/upstream_isis/...` instead of machine-specific absolute paths.
- This keeps the guidance portable across local development, GitHub web UI review, and GitHub Actions.
- If an expected upstream file is not present under `reference/upstream_isis/`, say so explicitly and do not invent a path.

## Read in this order

1. Local inventory and current repo context
	- `todo_pybind11.csv`
	- `class_bind_methods_details/methods_inventory_summary.csv`
	- target `*_methods.csv`
	- current binding in `src/`
	- similar tests in `tests/unitTest/`

2. Upstream `.h`
	- prefer the mirrored file under `reference/upstream_isis/`
	- API shape, overloads, enums, return types, inheritance

3. Upstream `.cpp`
	- prefer the mirrored file under `reference/upstream_isis/`
	- lifecycle rules
	- default values
	- exceptions and programmer-error guards
	- side effects, ownership, file I/O, data/plugin dependencies

4. Upstream usage
	- prefer upstream tests or call sites mirrored under `reference/upstream_isis/`
	- unit tests, apps, call sites, common call order

5. Local pybind mapping
	- existing style in `src/`
	- `python/isis_pybind/__init__.py`
	- similar binding and return-policy patterns

6. Behavior-driven tests
	- test what ISIS actually allows, not what the signature seems to allow

## Rules that matter

- Do not trust the `.h` alone for stateful classes.
- For `Cube`, `Camera`, factories, I/O classes, and manager classes, assume the `.cpp` is required.
- Use repository-relative paths in instructions and reports so the same guidance works in local runs, GitHub web review, and GitHub Actions.
- If a setter fails after `create()` or `open()`, treat it as a pre-create lifecycle method.
- If upstream usage contradicts your guess from the header, follow upstream usage.
- If Python behavior intentionally differs from raw C++, test the exported Python API.

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
