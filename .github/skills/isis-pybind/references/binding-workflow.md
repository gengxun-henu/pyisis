# Binding Workflow Reference

This reference explains the default sequence for implementing or extending pybind11 bindings for ISIS classes in `isis_pybind_standalone`.

## Start from inventory, not from guesswork

When the user does not provide a specific class, begin with:

1. `./todo_pybind11.csv`
2. `./class_bind_methods_details/methods_inventory_summary.csv`
3. `./pybind_progress_log.md`

Recommended prioritization:

- `Suggested Priority = High`
- fewer open items first
- classes that are already exported but still have missing methods
- classes with clear existing test patterns nearby
- use `pybind_progress_log.md` to avoid repeating recently completed work or rediscovering active blockers

## Class-level inspection sequence

For a chosen class:

1. open the matching `*_methods.csv`
2. inspect the corresponding C++ header under `isis/src/` or `SensorUtilities/`
3. inspect the current binding file under `./src/`
4. inspect similar bound classes for pybind11 style consistency
5. inspect Python exports in `./python/isis_pybind/__init__.py`

## Typical implementation flow

### 1. Confirm the target API surface

- Determine constructors, methods, static helpers, enums, and properties that should be exposed.
- Compare C++ declarations with the method CSV status columns.
- Note any overloads that need careful Python signatures.

### 2. Update the binding source

Common locations include:

- `./src/module.cpp`
- `./src/base/*.cpp`
- `./src/*.cpp`

Guidelines:

- follow the binding style already used in nearby files
- prefer explicit and readable `.def(...)` calls
- use lambdas only when needed for overload disambiguation or Pythonic adaptation
- preserve existing exposed names unless there is a good reason to change them

### 3. Update Python package exports

If the class or helper is intended for package-level access, update:

- `./python/isis_pybind/__init__.py`

### 4. Check exception behavior

When the bound API can fail, verify how the current binding surface translates exceptions, especially toward `ip.IException` or repository-standard Python-facing error behavior.

## Good implementation habits

- make small changes that are easy to validate
- reuse existing patterns before inventing new wrappers
- separate binding additions from unrelated refactors
- keep Python naming coherent with existing exports

## Common pitfalls

- assuming every C++ overload should be exposed exactly as-is
- adding bindings without updating package exports when needed
- exposing methods that require runtime data but providing no test strategy
- forgetting to sync task progress after the binding is complete
