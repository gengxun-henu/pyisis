# ControlNet Deep Matcher Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace duplicate `controlnet_construct.deep_*` runtime implementations with compatibility wrappers around `image_match.deep_*`.

**Architecture:** `examples/image_match` remains the single runtime implementation owner for deep matcher adapters, frontends, and matchers. `examples/controlnet_construct/deep_adapter.py`, `deep_frontends.py`, and `deep_matchers.py` become small re-export modules with explicit `__all__` lists so old import paths continue to work.

**Tech Stack:** Python 3.12, unittest, conda environment `asp360_new`, existing `examples` package import layout.

---

## File Structure

- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Add focused regression coverage proving the old `controlnet_construct.deep_*` names are the same objects exported by `image_match.deep_*`.
- Modify: `examples/controlnet_construct/deep_adapter.py`
  - Replace implementation with a wrapper that re-exports adapter APIs from `image_match.deep_adapter` plus exception/result symbols used through the legacy path.
- Modify: `examples/controlnet_construct/deep_frontends.py`
  - Replace implementation with a wrapper that re-exports frontend APIs from `image_match.deep_frontends`.
- Modify: `examples/controlnet_construct/deep_matchers.py`
  - Replace implementation with a wrapper that re-exports matcher APIs from `image_match.deep_matchers`.

## Task 1: Add Compatibility Identity Tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add failing tests for legacy wrapper identity**

Add these test methods near the existing deep adapter/frontend/matcher tests in `ControlNetConstructMatchingUnitTest`:

```python
    def test_controlnet_deep_adapter_reexports_image_match_adapter_api(self):
        controlnet_adapter = importlib.import_module("controlnet_construct.deep_adapter")
        image_match_adapter = importlib.import_module("image_match.deep_adapter")
        image_match_frontends = importlib.import_module("image_match.deep_frontends")
        image_match_matchers = importlib.import_module("image_match.deep_matchers")

        self.assertIs(controlnet_adapter.DeepMatcherAdapter, image_match_adapter.DeepMatcherAdapter)
        self.assertIs(controlnet_adapter.DeepDependencyError, image_match_frontends.DeepDependencyError)
        self.assertIs(controlnet_adapter.DeepMatcherError, image_match_matchers.DeepMatcherError)
        self.assertIs(controlnet_adapter.DeepMatchResult, image_match_matchers.DeepMatchResult)
        self.assertIn("DeepMatcherAdapter", controlnet_adapter.__all__)
        self.assertIn("build_deep_matcher", controlnet_adapter.__all__)

    def test_controlnet_deep_frontends_reexports_image_match_frontend_api(self):
        controlnet_frontends = importlib.import_module("controlnet_construct.deep_frontends")
        image_match_frontends = importlib.import_module("image_match.deep_frontends")

        for name in (
            "DeepDependencyError",
            "DeepFrontendError",
            "LoFTRFrontend",
            "SUPPORTED_DEEP_METHODS",
            "SuperPointFrontend",
            "normalize_deep_method",
            "resolve_torch_device",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(controlnet_frontends, name), getattr(image_match_frontends, name))
                self.assertIn(name, controlnet_frontends.__all__)

    def test_controlnet_deep_matchers_reexports_image_match_matcher_api(self):
        controlnet_matchers = importlib.import_module("controlnet_construct.deep_matchers")
        image_match_matchers = importlib.import_module("image_match.deep_matchers")

        for name in (
            "DeepMatchResult",
            "DeepMatcherError",
            "LightGlueMatcher",
            "LoFTRMatcher",
            "SuperGlueMatcher",
            "_default_feature_extractor_for_matcher",
            "build_deep_matcher",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(controlnet_matchers, name), getattr(image_match_matchers, name))
                self.assertIn(name, controlnet_matchers.__all__)
```

- [ ] **Step 2: Run tests to verify they fail before wrapper conversion**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_adapter_reexports_image_match_adapter_api tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_frontends_reexports_image_match_frontend_api tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_matchers_reexports_image_match_matcher_api -v
```

Expected: FAIL because at least one `assertIs` compares a duplicate `controlnet_construct.deep_*` object with the separate `image_match.deep_*` object.

- [ ] **Step 3: Commit the failing regression tests**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: cover ControlNet deep wrapper compatibility"
```

## Task 2: Convert ControlNet Deep Modules To Wrappers

**Files:**
- Modify: `examples/controlnet_construct/deep_adapter.py`
- Modify: `examples/controlnet_construct/deep_frontends.py`
- Modify: `examples/controlnet_construct/deep_matchers.py`

- [ ] **Step 1: Replace `deep_frontends.py` with explicit re-exports**

Replace the full contents of `examples/controlnet_construct/deep_frontends.py` with:

```python
"""Compatibility wrapper for deep matcher frontend helpers.

Author: Geng Xun / Codex
Created: 2026-05-11
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

from image_match.deep_frontends import (
    SUPPORTED_DEEP_METHODS,
    DeepDependencyError,
    DeepFrontendError,
    LoFTRFrontend,
    SuperPointFrontend,
    normalize_deep_method,
    resolve_torch_device,
)

__all__ = [
    "SUPPORTED_DEEP_METHODS",
    "DeepDependencyError",
    "DeepFrontendError",
    "LoFTRFrontend",
    "SuperPointFrontend",
    "normalize_deep_method",
    "resolve_torch_device",
]
```

- [ ] **Step 2: Replace `deep_matchers.py` with explicit re-exports**

Replace the full contents of `examples/controlnet_construct/deep_matchers.py` with:

```python
"""Compatibility wrapper for deep matcher runtime implementations.

Author: Geng Xun / Codex
Created: 2026-05-19
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

from image_match.deep_matchers import (
    DeepMatchResult,
    DeepMatcherError,
    LightGlueMatcher,
    LoFTRMatcher,
    SuperGlueMatcher,
    _default_feature_extractor_for_matcher,
    build_deep_matcher,
)

__all__ = [
    "DeepMatchResult",
    "DeepMatcherError",
    "LightGlueMatcher",
    "LoFTRMatcher",
    "SuperGlueMatcher",
    "_default_feature_extractor_for_matcher",
    "build_deep_matcher",
]
```

- [ ] **Step 3: Replace `deep_adapter.py` with explicit re-exports**

Replace the full contents of `examples/controlnet_construct/deep_adapter.py` with:

```python
"""Compatibility wrapper for deep matcher adapter routing.

Author: Geng Xun / Codex
Created: 2026-05-11
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

from image_match.deep_adapter import (
    DeepMatcherAdapter,
    _filter_feature_dict_by_invalid_mask,
    _runtime_feature_extractor_method,
    _valid_mask_keep,
    _validate_runtime_matcher_compatibility,
)
from image_match.deep_frontends import (
    DeepDependencyError,
    DeepFrontendError,
    LoFTRFrontend,
    SuperPointFrontend,
    normalize_deep_method,
    resolve_torch_device,
)
from image_match.deep_matchers import (
    DeepMatchResult,
    DeepMatcherError,
    _default_feature_extractor_for_matcher,
    build_deep_matcher,
)

__all__ = [
    "DeepMatcherAdapter",
    "DeepDependencyError",
    "DeepFrontendError",
    "LoFTRFrontend",
    "SuperPointFrontend",
    "normalize_deep_method",
    "resolve_torch_device",
    "DeepMatchResult",
    "DeepMatcherError",
    "_default_feature_extractor_for_matcher",
    "build_deep_matcher",
    "_filter_feature_dict_by_invalid_mask",
    "_runtime_feature_extractor_method",
    "_valid_mask_keep",
    "_validate_runtime_matcher_compatibility",
]
```

- [ ] **Step 4: Run the focused wrapper tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_adapter_reexports_image_match_adapter_api tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_frontends_reexports_image_match_frontend_api tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_controlnet_deep_matchers_reexports_image_match_matcher_api -v
```

Expected: PASS.

- [ ] **Step 5: Commit the wrapper conversion**

```bash
git add examples/controlnet_construct/deep_adapter.py examples/controlnet_construct/deep_frontends.py examples/controlnet_construct/deep_matchers.py
git commit -m "refactor: wrap ControlNet deep matcher modules"
```

## Task 3: Verify Existing Deep-Match Behavior

**Files:**
- No source changes expected.

- [ ] **Step 1: Run smoke import**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: PASS with successful import of `isis_pybind`.

- [ ] **Step 2: Run ControlNet matching regression module**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS. Existing tests that patch or import `controlnet_construct.deep_*` continue to pass through the wrapper modules.

- [ ] **Step 3: Run focused config and manifest tests from the spec**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.test_deep_match_config \
  tests.unitTest.deep_match_config_rehydration_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test \
  -v
```

Expected: PASS. Strict matcher/extractor compatibility validation remains unchanged.

- [ ] **Step 4: Inspect git diff for unintended behavior changes**

Run:

```bash
git diff --stat HEAD
git diff HEAD -- examples/controlnet_construct/deep_adapter.py examples/controlnet_construct/deep_frontends.py examples/controlnet_construct/deep_matchers.py tests/unitTest/controlnet_construct_matching_unit_test.py
```

Expected: only the three wrapper conversions and the compatibility identity tests are present.

- [ ] **Step 5: Commit any verification-only fixes**

If verification exposed a small import/export omission, add only the missing re-export and its test assertion, then run the failed command again and commit:

```bash
git add examples/controlnet_construct/deep_adapter.py examples/controlnet_construct/deep_frontends.py examples/controlnet_construct/deep_matchers.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "fix: preserve ControlNet deep wrapper API"
```

If no fixes were needed, do not create an empty commit.

## Task 4: Final Review

**Files:**
- No source changes expected.

- [ ] **Step 1: Confirm spec coverage**

Check these requirements manually against the final diff:

```text
examples/image_match remains the runtime implementation owner.
controlnet_construct.deep_adapter is a wrapper only.
controlnet_construct.deep_frontends is a wrapper only.
controlnet_construct.deep_matchers is a wrapper only.
Old controlnet_construct.deep_* imports still resolve.
MATCHER_EXTRACTOR_REQUIREMENTS is unchanged.
No DISK, ALIKED, DoGHardNet, LoFTR checkpoint, manifest, NPZ, key, or standalone script behavior changed.
```

- [ ] **Step 2: Confirm clean staged state**

Run:

```bash
git status --short
```

Expected: no staged or unstaged tracked changes remain. The pre-existing untracked `examples/controlnet_construct/deep_match_handoff.md` may still appear and should not be added unless the user explicitly requests it.

- [ ] **Step 3: Prepare completion summary**

Report:

```text
Implemented ControlNet deep matcher compatibility wrappers.
Tests run:
- python tests/smoke_import.py
- python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
- python -m unittest tests.unitTest.test_deep_match_config tests.unitTest.deep_match_config_rehydration_unit_test tests.unitTest.image_match_deep_manifest_unit_test tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
Remaining note: examples/controlnet_construct/deep_match_handoff.md is still untracked unless intentionally added.
```
