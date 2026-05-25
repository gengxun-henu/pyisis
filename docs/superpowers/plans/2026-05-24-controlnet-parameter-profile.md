# ControlNet Parameter Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in ControlNet pipeline parameter profile that applies conservative, balanced, or aggressive matching defaults without changing current behavior.

**Architecture:** Store profile definitions in a small Python module near the existing parameter catalog. The shell wrapper applies a selected profile only when a field was not explicitly set by CLI or resolved from config/preset, then the existing validation layer checks the final values.

**Tech Stack:** Bash wrapper, Python stdlib, unittest.

---

### Task 1: Profile Catalog

**Files:**
- Create: `examples/controlnet_construct/parameter_profiles.py`
- Modify: `examples/controlnet_construct/parameter_catalog.py`
- Test: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`

- [x] Add tests that assert `parameter_profile` is cataloged for `run_pipeline_example` with allowed values `conservative`, `balanced`, and `aggressive`.
- [x] Add `parameter_profiles.py` with immutable profile definitions for the existing documented parameter combinations.
- [x] Add `parameter_profile` to the catalog as an opt-in pipeline field.
- [x] Run `python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v`.

### Task 2: Wrapper Application

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [x] Add wrapper regression tests for `--parameter-profile balanced --validate-parameters-only`.
- [x] Add wrapper regression tests proving explicit CLI values override profile values.
- [x] Add wrapper regression tests proving config values override profile values.
- [x] Parse `--parameter-profile`, apply the profile after config/preset resolution, and keep profile application pre-validation only.
- [x] Run selected pipeline wrapper tests that exercise the new behavior.

### Task 3: Validation and Docs

**Files:**
- Modify: `examples/controlnet_construct/parameter_validation.py`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`

- [x] Add validation tests that reject an unknown profile and preserve valid profile values.
- [x] Include `PARAMETER_PROFILE` in validate-only summaries.
- [x] Update grouped help and usage text for the new flag.
- [x] Run parameter catalog, parameter validation, and focused pipeline tests.
