# Three CI Test Failures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the full unit-test gate by correcting two stale repository contracts and making one import-boundary test independent of built artifacts.

**Architecture:** Keep production behavior unchanged. Update the ControlNet assertion to the established BF default, restore concise user-facing deep-match documentation, and isolate the runtime import test by masking only `isis_pybind._isis_core` in `sys.modules` for the duration of that assertion.

**Tech Stack:** Python 3.12 `unittest`, Bash-driven ControlNet wrapper tests, Markdown documentation, conda environment `asp360_new`.

## Global Constraints

- Do not change the supported runtime API, ControlNet matching behavior, or release packaging.
- Use only the `asp360_new` conda environment for validation.
- Set `PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"` and `ISISDATA="$PWD/tests/data/isisdata/mockup"` before tests.
- Preserve `.gitignore`, `print.prt`, and unrelated user files.
- Update test-file metadata for meaningful changes using date `2026-08-02` and author `Geng Xun`.

---

### Task 1: Align the ControlNet balanced-profile regression

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

**Interfaces:**
- Consumes: `examples/controlnet_construct/parameter_profiles.py::PARAMETER_PROFILES["balanced"]["matcher_method"]`, currently `"bf"`.
- Produces: A regression assertion matching the current public profile behavior.

- [ ] **Step 1: Confirm the existing regression is red**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_parameter_profile_applies_balanced_defaults -v
```

Expected: FAIL because stdout contains `MATCHER_METHOD=bf` while the test expects `MATCHER_METHOD=flann`.

- [ ] **Step 2: Update the stale expectation and metadata**

Change the assertion to:

```python
self.assertIn("MATCHER_METHOD=bf", result.stdout)
```

Set `Last Modified: 2026-08-02` and append:

```text
Updated: 2026-08-02  Geng Xun aligned the balanced-profile matcher regression with the established BF default.
```

- [ ] **Step 3: Verify the focused regression is green**

Run the command from Step 1.

Expected: PASS.

- [ ] **Step 4: Commit the independently reviewable fix**

```bash
git add tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: align balanced profile matcher expectation"
```

### Task 2: Restore Chinese deep-match workflow documentation

**Files:**
- Modify: `README.zh-CN.md`
- Modify: `tests/unitTest/deep_match_pipeline_smoke_unit_test.py`

**Interfaces:**
- Consumes: Existing documentation smoke contract requiring `direct / export / import`, `run_deep_match_manifest.py`, `deep_match_manifests.json`, and `PRESETS_README.md`.
- Produces: A concise Chinese README section that directs users to the maintained deep-match tools and support table.

- [ ] **Step 1: Confirm the documentation regression is red**

Run:

```bash
python -m unittest tests.unitTest.deep_match_pipeline_smoke_unit_test.DeepMatchPipelineSmokeUnitTest.test_readme_zh_documents_recommended_deep_match_workflows -v
```

Expected: FAIL because the release-oriented README no longer contains the four required workflow references.

- [ ] **Step 2: Restore a concise deep-match subsection**

Add a `### 深度匹配工作流` subsection after the basic usage examples. State that the three modes are `direct / export / import`, explain that `examples/learning_methods/run_deep_match_manifest.py` executes exported manifests in the deep-learning environment, identify `deep_match_manifests.json` as the import/export summary, and link `examples/controlnet_construct/PRESETS_README.md` for runtime support and limitations.

- [ ] **Step 3: Refresh the documentation-test metadata**

Set `Last Modified: 2026-08-02` and append:

```text
Updated: 2026-08-02  Geng Xun restored Chinese README coverage for the recommended deep-match workflows.
```

- [ ] **Step 4: Verify the focused documentation regression is green**

Run the command from Step 1.

Expected: PASS.

- [ ] **Step 5: Commit the independently reviewable fix**

```bash
git add README.zh-CN.md tests/unitTest/deep_match_pipeline_smoke_unit_test.py
git commit -m "docs: restore Chinese deep-match workflow guide"
```

### Task 3: Isolate optional runtime-discovery import coverage

**Files:**
- Modify: `tests/unitTest/pyisis_runtime_unit_test.py`

**Interfaces:**
- Consumes: `sys.modules`, `unittest.mock.patch.dict`, and the existing fake `pyisis._runtime` module.
- Produces: A deterministic test that reaches normal `_isis_core` resolution after swallowing `configure_runtime()` failure, regardless of whether the extension was built earlier in the CI job.

- [ ] **Step 1: Confirm the existing regression is red with a built extension**

Run:

```bash
python -m unittest tests.unitTest.pyisis_runtime_unit_test.PyisisRuntimeUnitTest.test_isis_pybind_import_ignores_runtime_discovery_failure -v
```

Expected: FAIL or ERROR because the built `_isis_core` is discoverable instead of raising the expected `ModuleNotFoundError`.

- [ ] **Step 2: Mask only the core extension during the assertion**

Wrap the existing import assertion with:

```python
with mock.patch.dict(sys.modules, {"isis_pybind._isis_core": None}):
    with self.assertRaises(ModuleNotFoundError) as context:
        importlib.import_module("isis_pybind")
```

Keep the existing assertions that `configure_runtime()` was called exactly once and that the missing module name is `isis_pybind._isis_core`.

- [ ] **Step 3: Refresh test metadata**

Set `Last Modified: 2026-08-02` and append:

```text
Updated: 2026-08-02  Geng Xun isolated optional runtime-discovery import coverage from built extension artifacts.
```

- [ ] **Step 4: Verify the focused runtime regression is green**

Run the command from Step 1.

Expected: PASS with the extension present in `build/python`.

- [ ] **Step 5: Commit the independently reviewable fix**

```bash
git add tests/unitTest/pyisis_runtime_unit_test.py
git commit -m "test: isolate runtime discovery import failure"
```

### Task 4: Validate and publish the repair branch

**Files:**
- Verify: all files changed in Tasks 1-3

**Interfaces:**
- Consumes: The three scoped commits and the repository's conda-based validation commands.
- Produces: A pushed branch and reviewable GitHub PR with evidence for focused and broad test coverage.

- [ ] **Step 1: Run all three formerly failing tests together**

```bash
python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_parameter_profile_applies_balanced_defaults \
  tests.unitTest.deep_match_pipeline_smoke_unit_test.DeepMatchPipelineSmokeUnitTest.test_readme_zh_documents_recommended_deep_match_workflows \
  tests.unitTest.pyisis_runtime_unit_test.PyisisRuntimeUnitTest.test_isis_pybind_import_ignores_runtime_discovery_failure \
  -v
```

Expected: 3 tests pass.

- [ ] **Step 2: Run the three complete affected modules**

```bash
python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  tests.unitTest.deep_match_pipeline_smoke_unit_test \
  tests.unitTest.pyisis_runtime_unit_test \
  -v
```

Expected: all tests pass, allowing documented platform skips.

- [ ] **Step 3: Run import smoke coverage**

```bash
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 4: Run the full unit-test suite**

```bash
python -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
```

Expected: no failures or errors; documented skips and expected failures are allowed.

- [ ] **Step 5: Review branch scope**

```bash
git diff --check origin/main...HEAD
git status --short --branch
git log --oneline origin/main..HEAD
```

Expected: only the design, plan, README, and three scoped test files are changed; the worktree is clean.

- [ ] **Step 6: Push and create the PR**

```bash
git push -u origin fix/three-ci-test-failures
gh pr create --base main --head fix/three-ci-test-failures
```

The PR body must summarize all three fixes and list the focused, module-level, smoke, and full-suite validation results.
