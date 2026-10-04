# Findings & Decisions

## Requirements
- Use the official USGS ISIS 10 environment `asp370` as compile/link authority.
- Validate `IProj`, `OsirisRexOcamsOpenCVDistortionMap`, `ImageIoHandler`, and `GdalIoHandler` through the existing Python tests.
- Preserve ISIS 9 behavior and do not alter the canonical completed milestone registry.

## Research Findings
- `src/bind_isis10.cpp` already binds the six ISIS 10-only classes behind `PYISIS_ISIS10_API`.
- `tests/unitTest/isis10_api_unit_test.py` already covers projection methods, inheritance, null-parent rejection, GTiff reads, labels, and invalid input.
- ISIS 10-specific tests are skipped under ISIS 9, so a successful `asp370` build/import is the missing evidence.
- The long-running `.planning/isis10-expansion/task_plan.md` still marks these bindings as pending and needs a factual update after validation.
- Official `asp370` build succeeded with the repository's standard CMake configuration.
- The smoke script must receive `ISIS_PYBIND_BUILD_DIR=build-isis10/python` when validating the ISIS 10 artifact; otherwise it correctly rejects the ISIS 9 module selected from the default `build/python` path.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
-| Validate the existing facade first | It is a concrete deliverable with tests already defining the Python contract. |
| Keep raw GDAL pointers and Qt observer plumbing excluded | Existing binding policy requires stable Python-owned values and avoids unsafe/internal APIs. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
-| Canonical milestone verifier reports missing legacy M06 Windows ZIP | Record as pre-existing evidence issue; do not edit the immutable registry. |

## Resources
-
