# LoFTR External Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit LoFTR `matcher.backend: "external"` runtime path aligned with `examples/learning_methods/run-loftr.py` while preserving the existing kornia LoFTR default.

**Architecture:** `examples/image_match` remains the runtime owner. `controlnet_construct.deep_match_config` validates backend-aware LoFTR presets, `image_match.deep_frontends` prepares external LoFTR tensors and masks, `image_match.deep_matchers.LoFTRMatcher` routes between kornia and external LoFTR loading/matching, and `image_match.deep_adapter.DeepMatcherAdapter` forwards external preprocessing metadata into the matcher.

**Tech Stack:** Python 3.12, unittest/pytest-style existing tests, pybind/ISIS conda environment `asp360_new`, mocked optional LoFTR dependencies for automated tests, and a separate `deep-learning` conda environment for real external LoFTR smoke checks.

---

## File Structure

- Modify: `examples/controlnet_construct/deep_match_config.py`
  - Add backend-aware LoFTR validation, strict external option validation, alias checks, and dependency preflight behavior.
- Modify: `examples/image_match/deep_frontends.py`
  - Extend `LoFTRFrontend` with external preprocessing aligned with `run-loftr.py`: resize/pad alignment, valid-mask construction, coarse-mask metadata, and coordinate scale metadata.
- Modify: `examples/image_match/deep_matchers.py`
  - Extend `LoFTRMatcher` with backend routing, external LoFTR repository/checkpoint loading, inference execution, confidence/top-k/geometric filtering, and coordinate scaling.
- Modify: `examples/image_match/deep_adapter.py`
  - Forward LoFTR backend-specific preparation metadata to `LoFTRMatcher.match` without changing current kornia default behavior.
- Create: `examples/controlnet_construct/presets/loftr_external_outdoor.json`
- Create: `examples/controlnet_construct/presets/loftr_external_indoor.json`
- Modify: `examples/controlnet_construct/PRESETS_README.md`
  - Document kornia vs external LoFTR backend semantics, presets, machine-specific paths, and `deep-learning` environment boundary.
- Modify: `tests/unitTest/test_deep_match_config.py`
  - Add validation and preset coverage for external LoFTR.
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`
  - Add preprocessing and adapter metadata-forwarding coverage.
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Add mocked external LoFTR matcher construction/loading/filtering coverage.
- Modify: `tests/unitTest/deep_match_config_rehydration_unit_test.py`
  - Add rehydration coverage that preserves LoFTR backend and external options.

## Environment Boundary

Automated tests in this plan run inside `asp360_new` and must mock optional external LoFTR dependencies. Do not require real external LoFTR imports, checkpoint downloads, or GPU access for normal unit tests.

Real external LoFTR execution belongs in the separate `deep-learning` conda environment where `run-loftr.py` has already been validated. After mocked tests pass in `asp360_new`, run one optional smoke check in `deep-learning` if that environment and external LoFTR repository are available.

## Task 1: Backend-Aware LoFTR Config Validation

**Files:**
- Modify: `examples/controlnet_construct/deep_match_config.py`
- Modify: `tests/unitTest/test_deep_match_config.py`
- Modify: `tests/unitTest/deep_match_config_rehydration_unit_test.py`

- [ ] **Step 1: Write failing LoFTR validation tests**

Add these tests to `TestDeepMatchConfigValidation` in `tests/unitTest/test_deep_match_config.py`:

```python
    def test_loftr_accepts_default_kornia_and_external_backends(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        for matcher in (
            {"method": "loftr"},
            {"method": "loftr", "backend": "kornia"},
            {"method": "loftr", "backend": "external", "model_type": "outdoor", "temp_bug_fix": "auto"},
        ):
            with self.subTest(matcher=matcher):
                validate_deep_match_config(
                    {
                        "feature_extractor": {"method": "loftr", "preprocess_mode": "pad"},
                        "matcher": matcher,
                    }
                )

    def test_loftr_rejects_unknown_backend_and_non_loftr_extractor(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="LoFTR.*backend"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr"},
                    "matcher": {"method": "loftr", "backend": "experimental"},
                }
            )

        with pytest.raises(ValueError, match="feature_extractor.method.*loftr"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint"},
                    "matcher": {"method": "loftr", "backend": "external"},
                }
            )

    def test_external_loftr_rejects_unknown_options_and_invalid_enums(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        base = {
            "feature_extractor": {"method": "loftr", "preprocess_mode": "pad"},
            "matcher": {"method": "loftr", "backend": "external"},
        }

        config = {
            "feature_extractor": {"method": "loftr", "remove_borders": 4},
            "matcher": {"method": "loftr", "backend": "external"},
        }
        with pytest.raises(ValueError, match="unknown feature_extractor option"):
            validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "loftr"},
            "matcher": {"method": "loftr", "backend": "external", "weights_path": "ignored.ckpt"},
        }
        with pytest.raises(ValueError, match="unknown matcher option"):
            validate_deep_match_config(config)

        for field_name, bad_value, pattern in (
            ("model_type", "space", "model_type"),
            ("temp_bug_fix", "maybe", "temp_bug_fix"),
            ("geometric_filter", "essential", "geometric_filter"),
        ):
            config = {
                "feature_extractor": dict(base["feature_extractor"]),
                "matcher": dict(base["matcher"], **{field_name: bad_value}),
            }
            with self.subTest(field=field_name):
                with pytest.raises(ValueError, match=pattern):
                    validate_deep_match_config(config)

        config = {
            "feature_extractor": {"method": "loftr", "preprocess_mode": "crop"},
            "matcher": dict(base["matcher"]),
        }
        with pytest.raises(ValueError, match="preprocess_mode"):
            validate_deep_match_config(config)

    def test_external_loftr_rejects_checkpoint_alias_conflict_and_partial_resize(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="checkpoint.*checkpoint_path"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr"},
                    "matcher": {
                        "method": "loftr",
                        "backend": "external",
                        "checkpoint": "/tmp/a.ckpt",
                        "checkpoint_path": "/tmp/b.ckpt",
                    },
                }
            )

        with pytest.raises(ValueError, match="resize_width.*resize_height"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "loftr", "resize_width": 640},
                    "matcher": {"method": "loftr", "backend": "external"},
                }
            )
```

- [ ] **Step 2: Write failing runtime rehydration test**

Add this test to `tests/unitTest/deep_match_config_rehydration_unit_test.py`:

```python
    def test_rehydrates_external_loftr_backend_options(self):
        from controlnet_construct.deep_match_config import deep_match_runtime_config_from_payload

        payload = {
            "matcher_method": "loftr",
            "feature_extractor_method": "loftr",
            "prefer_gpu": True,
            "device_dtype": "float32",
            "fallback_on_error": "sift_flann",
            "raw_config": {
                "feature_extractor": {
                    "method": "loftr",
                    "preprocess_mode": "pad",
                    "resize_width": 640,
                    "resize_height": 480,
                },
                "matcher": {
                    "method": "loftr",
                    "backend": "external",
                    "model_type": "outdoor",
                    "temp_bug_fix": "auto",
                    "top_k": 100,
                },
                "device": {"prefer_gpu": True, "dtype": "float32"},
            },
        }

        runtime = deep_match_runtime_config_from_payload(payload)

        self.assertEqual(runtime.matcher_method, "loftr")
        self.assertEqual(runtime.feature_extractor_method, "loftr")
        self.assertEqual(runtime.matcher_options["backend"], "external")
        self.assertEqual(runtime.matcher_options["model_type"], "outdoor")
        self.assertEqual(runtime.matcher_options["top_k"], 100)
        self.assertEqual(runtime.feature_options["preprocess_mode"], "pad")
        self.assertEqual(runtime.feature_options["resize_width"], 640)
        self.assertEqual(runtime.feature_options["resize_height"], 480)
```

- [ ] **Step 3: Run validation tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
python -m unittest tests.unitTest.deep_match_config_rehydration_unit_test -v
```

Expected: `test_deep_match_config.py` fails because LoFTR backend validation does not exist yet. The rehydration test may already pass because raw sections are preserved; keep it as regression coverage.

- [ ] **Step 4: Implement LoFTR backend validation**

In `examples/controlnet_construct/deep_match_config.py`, add constants near the existing LightGlue constants:

```python
LOFTR_BACKENDS = (None, "kornia", "external")
EXTERNAL_LOFTR_MODEL_TYPES = ("indoor", "outdoor")
EXTERNAL_LOFTR_TEMP_BUG_FIX_VALUES = ("auto", "true", "false")
EXTERNAL_LOFTR_PREPROCESS_MODES = ("pad", "resize")
EXTERNAL_LOFTR_GEOMETRIC_FILTERS = ("none", "homography", "fundamental")
EXTERNAL_LOFTR_FEATURE_OPTIONS = {"method", "preprocess_mode", "resize_width", "resize_height"}
EXTERNAL_LOFTR_MATCHER_OPTIONS = {
    "method",
    "backend",
    "loftr_root",
    "checkpoint",
    "checkpoint_path",
    "model_type",
    "temp_bug_fix",
    "coarse_threshold",
    "min_confidence",
    "top_k",
    "geometric_filter",
    "ransac_reproj_threshold",
    "ransac_confidence",
    "ransac_max_iters",
}
```

Add helpers near `_normalized_lightglue_backend`:

```python
def _normalized_backend(section: dict[str, Any], key: str = "backend") -> str | None:
    backend_value = section.get(key)
    if backend_value is None:
        return None
    normalized_backend = str(backend_value).strip().lower()
    return normalized_backend or None


def _validate_positive_number(*, option_name: str, option_value: Any) -> None:
    try:
        numeric_value = float(option_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{option_name} must be numeric.") from exc
    if numeric_value <= 0:
        raise ValueError(f"{option_name} must be positive.")


def _validate_positive_int(*, option_name: str, option_value: Any) -> None:
    try:
        integer_value = int(option_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{option_name} must be an integer.") from exc
    if integer_value <= 0:
        raise ValueError(f"{option_name} must be positive.")


def _validate_option_choice(
    *,
    option_name: str,
    option_value: Any,
    supported_values: tuple[str, ...],
) -> None:
    normalized_value = str(option_value).strip().lower()
    if normalized_value not in supported_values:
        supported_display = ", ".join(repr(value) for value in supported_values)
        raise ValueError(f"{option_name} must be one of ({supported_display}); got {normalized_value!r}.")
```

Replace `_normalized_lightglue_backend` body to delegate:

```python
def _normalized_lightglue_backend(matcher: dict[str, Any]) -> str | None:
    return _normalized_backend(matcher)
```

Add external LoFTR validation helpers:

```python
def _validate_external_loftr_options(
    *,
    matcher: dict[str, Any],
    feature_extractor: dict[str, Any],
) -> None:
    _reject_unknown_options(
        section_name="feature_extractor",
        section=feature_extractor,
        allowed_options=EXTERNAL_LOFTR_FEATURE_OPTIONS,
    )
    _reject_unknown_options(
        section_name="matcher",
        section=matcher,
        allowed_options=EXTERNAL_LOFTR_MATCHER_OPTIONS,
    )

    checkpoint = matcher.get("checkpoint")
    checkpoint_path = matcher.get("checkpoint_path")
    if checkpoint not in (None, "") and checkpoint_path not in (None, "") and str(checkpoint) != str(checkpoint_path):
        raise ValueError("external LoFTR accepts checkpoint or checkpoint_path, not conflicting values for both.")

    if "model_type" in matcher:
        _validate_option_choice(
            option_name="model_type",
            option_value=matcher["model_type"],
            supported_values=EXTERNAL_LOFTR_MODEL_TYPES,
        )
    if "temp_bug_fix" in matcher:
        _validate_option_choice(
            option_name="temp_bug_fix",
            option_value=matcher["temp_bug_fix"],
            supported_values=EXTERNAL_LOFTR_TEMP_BUG_FIX_VALUES,
        )
    if "geometric_filter" in matcher:
        _validate_option_choice(
            option_name="geometric_filter",
            option_value=matcher["geometric_filter"],
            supported_values=EXTERNAL_LOFTR_GEOMETRIC_FILTERS,
        )
    if "preprocess_mode" in feature_extractor:
        _validate_option_choice(
            option_name="preprocess_mode",
            option_value=feature_extractor["preprocess_mode"],
            supported_values=EXTERNAL_LOFTR_PREPROCESS_MODES,
        )

    resize_width_present = "resize_width" in feature_extractor
    resize_height_present = "resize_height" in feature_extractor
    if resize_width_present != resize_height_present:
        raise ValueError("external LoFTR requires resize_width and resize_height to be provided together.")
    if resize_width_present:
        _validate_positive_int(option_name="resize_width", option_value=feature_extractor["resize_width"])
        _validate_positive_int(option_name="resize_height", option_value=feature_extractor["resize_height"])

    for option_name in ("coarse_threshold", "min_confidence", "ransac_reproj_threshold", "ransac_confidence"):
        if option_name in matcher:
            _validate_positive_number(option_name=option_name, option_value=matcher[option_name])
    if "ransac_confidence" in matcher and float(matcher["ransac_confidence"]) > 1:
        raise ValueError("ransac_confidence must be in (0, 1].")
    for option_name in ("top_k", "ransac_max_iters"):
        if option_name in matcher:
            _validate_positive_int(option_name=option_name, option_value=matcher[option_name])
```

Modify `validate_matcher_feature_compatibility` so the LoFTR block runs before the generic `MATCHER_EXTRACTOR_REQUIREMENTS` check:

```python
    if normalized_matcher == "loftr":
        backend = _normalized_backend(matcher_dict)
        if backend not in LOFTR_BACKENDS:
            raise ValueError(
                f"Unsupported LoFTR matcher.backend={backend!r}; supported values: 'kornia', 'external'."
            )
        if normalized_extractor != "loftr":
            raise ValueError(
                f"matcher.method='loftr' requires feature_extractor.method to be 'loftr'; "
                f"got {normalized_extractor!r}."
            )
        if backend == "external":
            _validate_external_loftr_options(
                matcher=matcher_dict,
                feature_extractor=feature_extractor_dict,
            )
        return
```

Modify `check_deep_match_dependencies` so external LoFTR does not report missing `kornia.feature.LoFTR`:

```python
    if method == "loftr":
        backend = _normalized_backend(runtime_config.matcher_options)
        if backend == "external":
            message = _check_import("torch")
            return [] if message is None else [message]
        for message in (
            _check_import("torch"),
            _check_import("kornia.feature", attribute_name="LoFTR", missing_name="kornia.feature.LoFTR"),
        ):
            if message is not None:
                missing_messages.append(message)
        return missing_messages
```

- [ ] **Step 5: Run validation tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
python -m unittest tests.unitTest.deep_match_config_rehydration_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit config validation**

```bash
git add examples/controlnet_construct/deep_match_config.py tests/unitTest/test_deep_match_config.py tests/unitTest/deep_match_config_rehydration_unit_test.py
git commit -m "feat: validate external LoFTR backend config"
```

## Task 2: External LoFTR Preprocessing Helpers

**Files:**
- Modify: `examples/image_match/deep_frontends.py`
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`

- [ ] **Step 1: Write failing preprocessing tests**

Add this helper class near existing helper classes in `tests/unitTest/image_match_deep_adapter_unit_test.py`:

```python
class _TorchTensorStub:
    def __init__(self, array):
        self.array = np.asarray(array)
        self.shape = self.array.shape
        self.dtype = self.array.dtype
        self.device = None

    def to(self, *args, **kwargs):
        if args:
            self.device = args[0]
        if "device" in kwargs:
            self.device = kwargs["device"]
        return self

    def float(self):
        self.array = self.array.astype(np.float32, copy=False)
        self.dtype = self.array.dtype
        return self

    def __getitem__(self, item):
        return _TorchTensorStub(self.array[item])
```

Add this helper function near the helper classes:

```python
def _torch_frontend_stub():
    return SimpleNamespace(
        float32=np.float32,
        from_numpy=lambda array: _TorchTensorStub(array),
    )
```

Add these tests to `ImageMatchDeepAdapterUnitTest`:

```python
    def test_external_loftr_frontend_pad_mode_aligns_to_multiple_of_eight_and_keeps_scale(self):
        deep_frontends_module = __import__("image_match.deep_frontends", fromlist=["LoFTRFrontend"])
        frontend = deep_frontends_module.LoFTRFrontend(
            feature_options={"preprocess_mode": "pad"},
            matcher_options={"backend": "external"},
        )
        image = np.arange(30, dtype=np.float32).reshape(5, 6)
        invalid_mask = np.zeros((5, 6), dtype=bool)
        invalid_mask[2, 3] = True

        with mock.patch.dict(sys.modules, {"torch": _torch_frontend_stub()}, clear=False):
            prepared = frontend.prepare(image, image, device="cpu", left_mask=invalid_mask, right_mask=invalid_mask)

        self.assertEqual(prepared["left"].shape, (1, 1, 8, 8))
        self.assertEqual(prepared["right"].shape, (1, 1, 8, 8))
        self.assertEqual(prepared["left_valid_mask"].shape, (8, 8))
        self.assertFalse(bool(prepared["left_valid_mask"].array[2, 3]))
        self.assertFalse(bool(prepared["left_valid_mask"].array[7, 7]))
        self.assertEqual(prepared["left_meta"]["scale"], (1.0, 1.0))
        self.assertEqual(prepared["left_meta"]["infer_size"], (8, 8))
        self.assertEqual(prepared["left_meta"]["content_size"], (6, 5))

    def test_external_loftr_frontend_resize_mode_records_coordinate_scale(self):
        deep_frontends_module = __import__("image_match.deep_frontends", fromlist=["LoFTRFrontend"])
        frontend = deep_frontends_module.LoFTRFrontend(
            feature_options={"preprocess_mode": "resize", "resize_width": 8, "resize_height": 8},
            matcher_options={"backend": "external"},
        )
        image = np.arange(24, dtype=np.float32).reshape(4, 6)

        with mock.patch.dict(sys.modules, {"torch": _torch_frontend_stub()}, clear=False):
            prepared = frontend.prepare(image, image, device="cpu")

        self.assertEqual(prepared["left"].shape, (1, 1, 8, 8))
        self.assertIsNone(prepared["left_valid_mask"])
        self.assertEqual(prepared["left_meta"]["scale"], (0.75, 0.5))
        self.assertEqual(prepared["left_meta"]["original_size"], (6, 4))
        self.assertEqual(prepared["left_meta"]["content_size"], (8, 8))
```

- [ ] **Step 2: Run preprocessing tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_external_loftr_frontend_pad_mode_aligns_to_multiple_of_eight_and_keeps_scale \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_external_loftr_frontend_resize_mode_records_coordinate_scale \
  -v
```

Expected: FAIL because `LoFTRFrontend` does not accept feature/matcher options and does not return external metadata yet.

- [ ] **Step 3: Implement external preprocessing helpers**

In `examples/image_match/deep_frontends.py`, add `cv2` import near the existing imports:

```python
import cv2
```

Add constants near `SUPPORTED_DEEP_METHODS`:

```python
LOFTR_DIVISIBILITY = 8
LOFTR_PREPROCESS_MODES = {"pad", "resize"}
```

Replace `LoFTRFrontend` with this version:

```python
class LoFTRFrontend:
    def __init__(
        self,
        *,
        feature_options: dict[str, Any] | None = None,
        matcher_options: dict[str, Any] | None = None,
    ) -> None:
        self.feature_options = dict(feature_options or {})
        self.matcher_options = dict(matcher_options or {})
        self.backend = str(self.matcher_options.get("backend") or "kornia").strip().lower()
        self._torch = None

    def prepare(
        self,
        left_image,
        right_image,
        device: str,
        left_mask: np.ndarray | None = None,
        right_mask: np.ndarray | None = None,
    ):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="loftr",
                missing="torch",
                install_hint="pip install torch kornia",
            )

        self._torch = torch
        if self.backend == "external":
            left = self._prepare_external_image(left_image, invalid_mask=left_mask, device=device)
            right = self._prepare_external_image(right_image, invalid_mask=right_mask, device=device)
            return {
                "left": left["tensor"],
                "right": right["tensor"],
                "left_mask": left["coarse_mask"],
                "right_mask": right["coarse_mask"],
                "left_valid_mask": left["valid_mask"],
                "right_valid_mask": right["valid_mask"],
                "left_meta": left["meta"],
                "right_meta": right["meta"],
            }

        _require_kornia_feature(
            method="loftr",
            feature_name="SuperPoint",
            install_hint="pip install \"kornia[loftr]\"",
        )
        return {
            "left": self._as_tensor(left_image, device=device),
            "right": self._as_tensor(right_image, device=device),
            "left_mask": self._as_mask_tensor(left_mask, device=device),
            "right_mask": self._as_mask_tensor(right_mask, device=device),
        }

    def _prepare_external_image(self, image, *, invalid_mask: np.ndarray | None, device: str) -> dict[str, Any]:
        image_plane = self._as_float_plane(image)
        original_height, original_width = image_plane.shape[:2]
        resize_width = self.feature_options.get("resize_width")
        resize_height = self.feature_options.get("resize_height")
        content_width = int(resize_width) if resize_width is not None else original_width
        content_height = int(resize_height) if resize_height is not None else original_height
        content = self._resize_plane(image_plane, width=content_width, height=content_height)
        valid_content = self._valid_content_mask(
            invalid_mask,
            original_width=original_width,
            original_height=original_height,
            content_width=content_width,
            content_height=content_height,
        )
        preprocess_mode = str(self.feature_options.get("preprocess_mode", "pad") or "pad").strip().lower()
        if preprocess_mode not in LOFTR_PREPROCESS_MODES:
            raise DeepFrontendError(f"Unsupported LoFTR preprocess_mode={preprocess_mode!r}.")
        if preprocess_mode == "pad":
            infer_width = self._align_size(content_width, mode="ceil")
            infer_height = self._align_size(content_height, mode="ceil")
            infer_plane = np.zeros((infer_height, infer_width), dtype=np.float32)
            infer_plane[:content_height, :content_width] = content
            valid_mask = np.zeros((infer_height, infer_width), dtype=bool)
            valid_mask[:content_height, :content_width] = valid_content
        else:
            infer_width = self._align_size(content_width, mode="floor")
            infer_height = self._align_size(content_height, mode="floor")
            infer_plane = self._resize_plane(content, width=infer_width, height=infer_height)
            valid_mask = None
            content_width = infer_width
            content_height = infer_height

        tensor = self._torch.from_numpy(infer_plane)[None][None].float().to(device)
        valid_mask_tensor = None if valid_mask is None else self._torch.from_numpy(valid_mask).to(device)
        meta = {
            "original_size": (original_width, original_height),
            "content_size": (content_width, content_height),
            "infer_size": (infer_width, infer_height),
            "scale": (original_width / float(content_width), original_height / float(content_height)),
        }
        return {
            "tensor": tensor,
            "valid_mask": valid_mask_tensor,
            "coarse_mask": valid_mask_tensor,
            "meta": meta,
        }

    def _as_float_plane(self, image) -> np.ndarray:
        image_array = np.asarray(image, dtype=np.float32)
        if image_array.ndim == 0:
            image_plane = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_plane = image_array.reshape(1, -1)
        elif image_array.ndim == 2:
            image_plane = image_array
        else:
            image_plane = np.mean(image_array, axis=-1)
        image_plane = np.nan_to_num(image_plane, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_plane))) if image_plane.size > 0 else 0.0
        if scale > 0.0:
            image_plane = image_plane / scale
        return image_plane

    def _resize_plane(self, image_plane: np.ndarray, *, width: int, height: int) -> np.ndarray:
        if image_plane.shape[:2] == (height, width):
            return image_plane.astype(np.float32, copy=False)
        interpolation = cv2.INTER_AREA if width <= image_plane.shape[1] and height <= image_plane.shape[0] else cv2.INTER_LINEAR
        return cv2.resize(image_plane, (width, height), interpolation=interpolation).astype(np.float32, copy=False)

    def _valid_content_mask(
        self,
        invalid_mask: np.ndarray | None,
        *,
        original_width: int,
        original_height: int,
        content_width: int,
        content_height: int,
    ) -> np.ndarray:
        if invalid_mask is None:
            return np.ones((content_height, content_width), dtype=bool)
        valid_original = ~np.asarray(invalid_mask, dtype=bool)
        if valid_original.shape[:2] != (original_height, original_width):
            valid_original = valid_original[:original_height, :original_width]
        valid_uint8 = valid_original.astype(np.uint8)
        if valid_uint8.shape[:2] != (content_height, content_width):
            valid_uint8 = cv2.resize(valid_uint8, (content_width, content_height), interpolation=cv2.INTER_NEAREST)
        return valid_uint8.astype(bool)

    def _align_size(self, value: int, *, mode: str) -> int:
        if mode == "ceil":
            return max(LOFTR_DIVISIBILITY, ((int(value) + LOFTR_DIVISIBILITY - 1) // LOFTR_DIVISIBILITY) * LOFTR_DIVISIBILITY)
        if mode == "floor":
            return max(LOFTR_DIVISIBILITY, int(value) - (int(value) % LOFTR_DIVISIBILITY))
        raise DeepFrontendError(f"Unsupported LoFTR alignment mode={mode!r}.")
```

Keep existing `_as_tensor` and `_as_mask_tensor` methods after the new helper methods unchanged for the kornia backend.

- [ ] **Step 4: Update adapter construction for runtime options**

In `examples/image_match/deep_adapter.py`, change `DeepMatcherAdapter.__init__` LoFTR frontend construction from:

```python
        self._loftr_frontend = LoFTRFrontend()
```

to:

```python
        self._loftr_frontend = LoFTRFrontend(
            feature_options=dict(getattr(runtime_config, "feature_options", {}) or {}),
            matcher_options=dict(getattr(runtime_config, "matcher_options", {}) or {}),
        )
```

- [ ] **Step 5: Run preprocessing tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_external_loftr_frontend_pad_mode_aligns_to_multiple_of_eight_and_keeps_scale \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_external_loftr_frontend_resize_mode_records_coordinate_scale \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_match_pair_passes_prepared_loftr_masks_into_matcher \
  -v
```

Expected: PASS.

- [ ] **Step 6: Commit preprocessing helpers**

```bash
git add examples/image_match/deep_frontends.py examples/image_match/deep_adapter.py tests/unitTest/image_match_deep_adapter_unit_test.py
git commit -m "feat: prepare external LoFTR tile tensors"
```

## Task 3: External LoFTR Matcher Runtime

**Files:**
- Modify: `examples/image_match/deep_matchers.py`
- Modify: `examples/image_match/deep_adapter.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`

- [ ] **Step 1: Write failing mocked external matcher loading test**

Add this test near existing LoFTR matcher tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
    def test_external_loftr_matcher_loads_external_repo_checkpoint_and_config(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "LoFTR"
            (root / "src" / "loftr").mkdir(parents=True)
            (root / "src" / "loftr" / "__init__.py").write_text("", encoding="utf-8")
            checkpoint = root / "weights" / "outdoor.ckpt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"stub")

            loaded_state = {"state_dict": {"matcher.weight": object()}}
            matcher_instance = _EvalToDeviceModule()
            matcher_instance.load_state_dict = mock.Mock()
            matcher_constructor = mock.Mock(return_value=matcher_instance)
            loftr_module = _stub_module(
                "src.loftr",
                LoFTR=matcher_constructor,
                default_cfg={"coarse": {"temp_bug_fix": False, "d_model": 256}, "match_coarse": {}, "resolution": (8, 2)},
            )
            torch_module = _stub_module("torch", float32="torch.float32", load=mock.Mock(return_value=loaded_state))

            with mock.patch.dict(sys.modules, {"torch": torch_module, "src.loftr": loftr_module}, clear=False):
                matcher = deep_matchers_module.build_deep_matcher(
                    "loftr",
                    device="cpu",
                    feature_extractor_method="loftr",
                    matcher_options={
                        "backend": "external",
                        "loftr_root": str(root),
                        "checkpoint": str(checkpoint),
                        "model_type": "outdoor",
                        "temp_bug_fix": "true",
                        "coarse_threshold": 0.3,
                    },
                    device_options={"dtype": "float32"},
                )
                matcher._load_matcher()

        matcher_constructor.assert_called_once()
        config = matcher_constructor.call_args.kwargs["config"]
        self.assertIs(config["coarse"]["temp_bug_fix"], True)
        self.assertAlmostEqual(config["match_coarse"]["thr"], 0.3)
        torch_module.load.assert_called_once_with(checkpoint, map_location="cpu", weights_only=True)
        matcher_instance.load_state_dict.assert_called_once_with(loaded_state["state_dict"], strict=True)
```

Add imports at the top of `tests/unitTest/controlnet_construct_matching_unit_test.py` if missing:

```python
import tempfile
from pathlib import Path
```

- [ ] **Step 2: Write failing external match filtering and scaling test**

Add this test near the test from Step 1:

```python
    def test_external_loftr_matcher_filters_top_k_and_scales_points(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _InferenceMode:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, traceback):
                return False

        class _ExternalMatcher:
            config = {"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}}
            pos_encoding = SimpleNamespace(pe=np.zeros((1, 1, 8, 8), dtype=np.float32))

            def __call__(self, batch):
                batch["mkpts0_f"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32))))
                batch["mkpts1_f"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]], dtype=np.float32))))
                batch["mconf"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([0.2, 0.9, 0.5], dtype=np.float32))))

        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external", "min_confidence": 0.3, "top_k": 1},
        )
        matcher._matcher = _ExternalMatcher()

        torch_module = _stub_module("torch", inference_mode=lambda: _InferenceMode(), no_grad=lambda: _InferenceMode())
        with mock.patch.object(matcher, "_load_matcher", return_value=(torch_module, matcher._matcher)):
            left_points, right_points, scores = matcher.match(
                left_image=object(),
                right_image=object(),
                left_meta={"scale": (2.0, 3.0)},
                right_meta={"scale": (4.0, 5.0)},
            )

        np.testing.assert_allclose(left_points, np.array([[6.0, 12.0]], dtype=np.float32))
        np.testing.assert_allclose(right_points, np.array([[16.0, 25.0]], dtype=np.float32))
        np.testing.assert_allclose(scores, np.array([0.9], dtype=np.float32))
```

- [ ] **Step 3: Write failing adapter metadata forwarding test**

Add this test to `ImageMatchDeepAdapterUnitTest` in `tests/unitTest/image_match_deep_adapter_unit_test.py`:

```python
    def test_match_pair_passes_external_loftr_metadata_into_matcher(self):
        runtime = SimpleNamespace(
            prefer_gpu=False,
            matcher_method="loftr",
            feature_extractor_method="loftr",
            matcher_options={"backend": "external", "top_k": 10},
            feature_options={"preprocess_mode": "pad"},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )
        adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)
        matcher = _CapturingLoFTRMatcher()
        prepared = {
            "left": object(),
            "right": object(),
            "left_mask": object(),
            "right_mask": object(),
            "left_meta": {"scale": (1.0, 1.0)},
            "right_meta": {"scale": (2.0, 2.0)},
        }

        with mock.patch.object(adapter._loftr_frontend, "prepare", return_value=prepared), mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ):
            adapter.match_pair(
                matcher_method="loftr",
                left_image=np.ones((6, 6), dtype=np.float32),
                right_image=np.ones((6, 6), dtype=np.float32),
            )

        self.assertEqual(len(matcher.calls), 1)
        self.assertIs(matcher.calls[0]["left_meta"], prepared["left_meta"])
        self.assertIs(matcher.calls[0]["right_meta"], prepared["right_meta"])
```

- [ ] **Step 4: Run external matcher tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_external_loftr_matcher_loads_external_repo_checkpoint_and_config \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_external_loftr_matcher_filters_top_k_and_scales_points \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_match_pair_passes_external_loftr_metadata_into_matcher \
  -v
```

Expected: FAIL because external matcher loading, filtering/scaling, and adapter metadata forwarding are not implemented.

- [ ] **Step 5: Implement external matcher helpers**

In `examples/image_match/deep_matchers.py`, add imports near the top:

```python
import copy
import importlib
import math
from pathlib import Path
import sys
```

Add constants near `_MATCHER_FEATURE_EXTRACTOR_REQUIREMENTS`:

```python
LOFTR_BACKENDS = {"kornia", "external", ""}
LOFTR_SUPPORTED_MODEL_TYPES = {"indoor", "outdoor"}
LOFTR_SUPPORTED_GEOMETRIC_FILTERS = {"none", "homography", "fundamental"}
LOFTR_DEFAULT_SAMPLE_CHECKPOINTS = {
    "indoor": ("weights/indoor.ckpt", "weights/indoor_ds.ckpt", "weights/indoor_ds_new.ckpt"),
    "outdoor": ("weights/outdoor.ckpt", "weights/outdoor_ds.ckpt"),
}
```

Add helpers before `LoFTRMatcher`:

```python
def _valid_external_loftr_root(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "src" / "loftr" / "__init__.py").is_file()


def _find_external_loftr_root(explicit_root: Any) -> Path:
    if explicit_root not in (None, ""):
        candidate = Path(str(explicit_root)).expanduser().resolve()
        if _valid_external_loftr_root(candidate):
            return candidate
        raise DeepMatcherError(f"Invalid external LoFTR root: {candidate}")

    checked: set[Path] = set()
    module_path = Path(__file__).resolve()
    for ancestor in [module_path.parent, *module_path.parents]:
        for candidate in (ancestor / "LoFTR", ancestor.parent / "LoFTR"):
            if candidate in checked:
                continue
            checked.add(candidate)
            if _valid_external_loftr_root(candidate):
                return candidate.resolve()
    raise DeepMatcherError("Could not automatically locate external LoFTR repository. Set matcher.loftr_root.")


def _checkpoint_option(options: dict[str, Any]) -> Any:
    checkpoint = options.get("checkpoint")
    checkpoint_path = options.get("checkpoint_path")
    if checkpoint not in (None, ""):
        return checkpoint
    return checkpoint_path


def _resolve_external_loftr_checkpoint(options: dict[str, Any], *, loftr_root: Path, model_type: str) -> Path:
    explicit_checkpoint = _checkpoint_option(options)
    if explicit_checkpoint not in (None, ""):
        resolved = Path(str(explicit_checkpoint)).expanduser().resolve()
        if not resolved.is_file():
            raise DeepMatcherError(f"External LoFTR checkpoint file does not exist: {resolved}")
        return resolved
    for relative_path in LOFTR_DEFAULT_SAMPLE_CHECKPOINTS[model_type]:
        candidate = loftr_root / relative_path
        if candidate.is_file():
            return candidate.resolve()
    searched = ", ".join(str(loftr_root / path) for path in LOFTR_DEFAULT_SAMPLE_CHECKPOINTS[model_type])
    raise DeepMatcherError(f"Could not find default external LoFTR {model_type} checkpoint. Checked: {searched}")


def _resolve_external_temp_bug_fix(option: Any, *, model_type: str) -> bool:
    normalized = str(option or "auto").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    if normalized == "auto":
        return model_type == "indoor"
    raise DeepMatcherError(f"Unsupported external LoFTR temp_bug_fix={option!r}.")


def _scale_loftr_points(points: np.ndarray, meta: dict[str, Any] | None) -> np.ndarray:
    point_array = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    if not meta:
        return point_array
    scale_x, scale_y = meta.get("scale", (1.0, 1.0))
    scaled = point_array.copy()
    scaled[:, 0] *= float(scale_x)
    scaled[:, 1] *= float(scale_y)
    return scaled.astype(np.float32, copy=False)
```

- [ ] **Step 6: Modify `LoFTRMatcher` backend routing**

In `LoFTRMatcher.__init__`, add:

```python
        self.backend = str(self.matcher_options.get("backend") or "kornia").strip().lower()
```

Replace `_loftr_pretrained` with:

```python
    def _loftr_pretrained(self) -> str:
        options = _copy_options(self.matcher_options)
        backend = str(options.pop("backend", self.backend) or "kornia").strip().lower()
        if backend == "external":
            return "external"
        if backend not in {"kornia", ""}:
            _raise_unsupported_option(method=self.method, option_name="backend", option_value=backend)
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="weights_path",
            ignored_parameters=self.ignored_parameters,
        )
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="checkpoint_path",
            ignored_parameters=self.ignored_parameters,
        )
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="checkpoint",
            ignored_parameters=self.ignored_parameters,
        )
        pretrained = str(options.pop("pretrained", "outdoor") or "outdoor").strip()
        _reject_unknown_options(method=self.method, options=options, allowed=set())
        return pretrained or "outdoor"
```

Add external options helper inside `LoFTRMatcher`:

```python
    def _external_options(self) -> dict[str, Any]:
        options = _copy_options(self.matcher_options)
        options.pop("backend", None)
        allowed = {
            "loftr_root",
            "checkpoint",
            "checkpoint_path",
            "model_type",
            "temp_bug_fix",
            "coarse_threshold",
            "min_confidence",
            "top_k",
            "geometric_filter",
            "ransac_reproj_threshold",
            "ransac_confidence",
            "ransac_max_iters",
        }
        _reject_unknown_options(method=self.method, options=options, allowed=allowed)
        model_type = str(options.get("model_type", "outdoor") or "outdoor").strip().lower()
        if model_type not in LOFTR_SUPPORTED_MODEL_TYPES:
            _raise_unsupported_option(method=self.method, option_name="model_type", option_value=model_type)
        options["model_type"] = model_type
        return options
```

Modify `_load_matcher` so it routes to external loader before importing kornia:

```python
        if self.backend == "external":
            return self._load_external_matcher()
```

Add `_load_external_matcher`:

```python
    def _load_external_matcher(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch",
            )
        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if self._matcher is None:
            options = self._external_options()
            model_type = options["model_type"]
            loftr_root = _find_external_loftr_root(options.get("loftr_root"))
            checkpoint_path = _resolve_external_loftr_checkpoint(options, loftr_root=loftr_root, model_type=model_type)
            loftr_root_str = str(loftr_root)
            if loftr_root_str not in sys.path:
                sys.path.insert(0, loftr_root_str)
            try:
                loftr_module = importlib.import_module("src.loftr")
            except Exception:
                raise _missing_dependency_error(
                    method=self.method,
                    missing="src.loftr",
                    install_hint="clone the LoFTR repository and set matcher.loftr_root",
                )
            config = copy.deepcopy(loftr_module.default_cfg)
            config["coarse"]["temp_bug_fix"] = _resolve_external_temp_bug_fix(
                options.get("temp_bug_fix", "auto"),
                model_type=model_type,
            )
            if options.get("coarse_threshold") is not None:
                config["match_coarse"]["thr"] = float(options["coarse_threshold"])
            matcher = loftr_module.LoFTR(config=config)
            try:
                state_dict = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
            except TypeError:
                state_dict = torch.load(checkpoint_path, map_location=self.device)
            if isinstance(state_dict, dict) and "state_dict" in state_dict:
                state_dict = state_dict["state_dict"]
            matcher.load_state_dict(state_dict, strict=True)
            self._matcher = matcher.eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._matcher
```

- [ ] **Step 7: Implement external inference and filtering**

Modify `LoFTRMatcher.match` signature to accept metadata:

```python
        left_meta: dict[str, Any] | None = None,
        right_meta: dict[str, Any] | None = None,
```

At the beginning of `match`, after loading matcher, route external backend:

```python
        if self.backend == "external":
            return self._match_external(
                torch=torch,
                matcher=matcher,
                left_image=left_image,
                right_image=right_image,
                left_mask=left_mask,
                right_mask=right_mask,
                left_meta=left_meta,
                right_meta=right_meta,
            )
```

Add these methods inside `LoFTRMatcher`:

```python
    def _match_external(
        self,
        *,
        torch: Any,
        matcher: Any,
        left_image: Any,
        right_image: Any,
        left_mask: Any = None,
        right_mask: Any = None,
        left_meta: dict[str, Any] | None = None,
        right_meta: dict[str, Any] | None = None,
    ):
        if left_image is None or right_image is None:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        self._ensure_external_position_encoding(matcher, left_meta=left_meta, right_meta=right_meta)
        batch = {
            "image0": left_image.to(device=self.device),
            "image1": right_image.to(device=self.device),
        }
        if left_mask is not None and right_mask is not None:
            batch["mask0"] = left_mask.to(self.device)
            batch["mask1"] = right_mask.to(self.device)
        context = torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
        with context:
            matcher(batch)
        left_points = batch["mkpts0_f"].detach().cpu().numpy().astype(np.float32, copy=False)
        right_points = batch["mkpts1_f"].detach().cpu().numpy().astype(np.float32, copy=False)
        scores = batch["mconf"].detach().cpu().numpy().astype(np.float32, copy=False)
        left_points = _scale_loftr_points(left_points, left_meta)
        right_points = _scale_loftr_points(right_points, right_meta)
        return self._filter_external_matches(left_points, right_points, scores)

    def _ensure_external_position_encoding(
        self,
        matcher: Any,
        *,
        left_meta: dict[str, Any] | None,
        right_meta: dict[str, Any] | None,
    ) -> None:
        if not hasattr(matcher, "pos_encoding") or not hasattr(matcher.pos_encoding, "pe"):
            return
        if not hasattr(matcher, "config") or "resolution" not in matcher.config:
            return
        left_size = (left_meta or {}).get("infer_size")
        right_size = (right_meta or {}).get("infer_size")
        if not left_size or not right_size:
            return
        current_height = int(matcher.pos_encoding.pe.shape[-2])
        current_width = int(matcher.pos_encoding.pe.shape[-1])
        coarse_divisor = int(matcher.config["resolution"][0])
        required_height = int(math.ceil(max(int(left_size[1]), int(right_size[1])) / float(coarse_divisor)))
        required_width = int(math.ceil(max(int(left_size[0]), int(right_size[0])) / float(coarse_divisor)))
        if required_height <= current_height and required_width <= current_width:
            return
        pos_encoding_cls = matcher.pos_encoding.__class__
        matcher.pos_encoding = pos_encoding_cls(
            matcher.config["coarse"]["d_model"],
            max_shape=(max(current_height, required_height), max(current_width, required_width)),
            temp_bug_fix=matcher.config["coarse"]["temp_bug_fix"],
        ).to(self.device)

    def _filter_external_matches(self, left_points: np.ndarray, right_points: np.ndarray, scores: np.ndarray):
        options = self._external_options()
        if options.get("min_confidence") is not None:
            keep = scores >= float(options["min_confidence"])
            left_points = left_points[keep]
            right_points = right_points[keep]
            scores = scores[keep]
        if scores.size > 0:
            order = np.argsort(-scores)
            if options.get("top_k") is not None:
                order = order[: int(options["top_k"])]
            left_points = left_points[order]
            right_points = right_points[order]
            scores = scores[order]
        geometric_filter = str(options.get("geometric_filter", "none") or "none").strip().lower()
        if geometric_filter != "none":
            left_points, right_points, scores = self._apply_external_geometric_filter(
                left_points,
                right_points,
                scores,
                method=geometric_filter,
                reproj_threshold=float(options.get("ransac_reproj_threshold", 3.0)),
                confidence=float(options.get("ransac_confidence", 0.999)),
                max_iters=int(options.get("ransac_max_iters", 10000)),
            )
        return left_points.astype(np.float32, copy=False), right_points.astype(np.float32, copy=False), scores.astype(np.float32, copy=False)

    def _apply_external_geometric_filter(
        self,
        left_points: np.ndarray,
        right_points: np.ndarray,
        scores: np.ndarray,
        *,
        method: str,
        reproj_threshold: float,
        confidence: float,
        max_iters: int,
    ):
        import cv2

        required_points = 4 if method == "homography" else 8
        if scores.size < required_points:
            return left_points, right_points, scores
        cv_method = cv2.USAC_MAGSAC if hasattr(cv2, "USAC_MAGSAC") else cv2.RANSAC
        if method == "homography":
            _, mask = cv2.findHomography(
                left_points.astype(np.float64),
                right_points.astype(np.float64),
                method=cv_method,
                ransacReprojThreshold=float(reproj_threshold),
                confidence=float(confidence),
                maxIters=int(max_iters),
            )
        elif method == "fundamental":
            _, mask = cv2.findFundamentalMat(
                left_points.astype(np.float64),
                right_points.astype(np.float64),
                method=cv_method,
                ransacReprojThreshold=float(reproj_threshold),
                confidence=float(confidence),
                maxIters=int(max_iters),
            )
        else:
            _raise_unsupported_option(method=self.method, option_name="geometric_filter", option_value=method)
        if mask is None:
            return left_points[:0], right_points[:0], scores[:0]
        keep = mask.reshape(-1).astype(bool)
        keep = keep[: scores.shape[0]]
        return left_points[keep], right_points[keep], scores[keep]
```

- [ ] **Step 8: Forward metadata from adapter**

In `examples/image_match/deep_adapter.py`, modify the LoFTR matcher call:

```python
                left_points, right_points, scores = matcher.match(
                    left_image=prepared["left"],
                    right_image=prepared["right"],
                    left_mask=prepared.get("left_mask"),
                    right_mask=prepared.get("right_mask"),
                    left_meta=prepared.get("left_meta"),
                    right_meta=prepared.get("right_meta"),
                    device=device,
                )
```

- [ ] **Step 9: Run external matcher tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_external_loftr_matcher_loads_external_repo_checkpoint_and_config \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_external_loftr_matcher_filters_top_k_and_scales_points \
  tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_match_pair_passes_external_loftr_metadata_into_matcher \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_loftr_matcher_uses_preset_pretrained_option \
  -v
```

Expected: PASS, including the existing kornia preset test.

- [ ] **Step 10: Commit external matcher runtime**

```bash
git add examples/image_match/deep_matchers.py examples/image_match/deep_adapter.py tests/unitTest/controlnet_construct_matching_unit_test.py tests/unitTest/image_match_deep_adapter_unit_test.py
git commit -m "feat: add external LoFTR runtime backend"
```

## Task 4: External LoFTR Presets

**Files:**
- Create: `examples/controlnet_construct/presets/loftr_external_outdoor.json`
- Create: `examples/controlnet_construct/presets/loftr_external_indoor.json`
- Modify: `tests/unitTest/test_deep_match_config.py`

- [ ] **Step 1: Write failing preset test**

Add this test to `TestPresetFiles` in `tests/unitTest/test_deep_match_config.py`:

```python
    def test_external_loftr_presets_exist_and_load(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config

        expected = {
            "loftr_external_outdoor.json": "outdoor",
            "loftr_external_indoor.json": "indoor",
        }
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"
        for preset_name, model_type in expected.items():
            with self.subTest(preset=preset_name):
                config = load_deep_match_config(str(presets_dir / preset_name))
                assert config["feature_extractor"]["method"] == "loftr"
                assert config["feature_extractor"]["preprocess_mode"] == "pad"
                assert config["matcher"]["method"] == "loftr"
                assert config["matcher"]["backend"] == "external"
                assert config["matcher"]["model_type"] == model_type
```

- [ ] **Step 2: Run preset test and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: FAIL because external preset files do not exist.

- [ ] **Step 3: Add outdoor preset**

Create `examples/controlnet_construct/presets/loftr_external_outdoor.json`:

```json
{
  "feature_extractor": {
    "method": "loftr",
    "preprocess_mode": "pad"
  },
  "matcher": {
    "method": "loftr",
    "backend": "external",
    "model_type": "outdoor",
    "temp_bug_fix": "auto",
    "geometric_filter": "none",
    "ransac_reproj_threshold": 3.0,
    "ransac_confidence": 0.999,
    "ransac_max_iters": 10000
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": false
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

- [ ] **Step 4: Add indoor preset**

Create `examples/controlnet_construct/presets/loftr_external_indoor.json`:

```json
{
  "feature_extractor": {
    "method": "loftr",
    "preprocess_mode": "pad"
  },
  "matcher": {
    "method": "loftr",
    "backend": "external",
    "model_type": "indoor",
    "temp_bug_fix": "auto",
    "geometric_filter": "none",
    "ransac_reproj_threshold": 3.0,
    "ransac_confidence": 0.999,
    "ransac_max_iters": 10000
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32",
    "batch_inference": false
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

- [ ] **Step 5: Run preset tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit presets**

```bash
git add tests/unitTest/test_deep_match_config.py examples/controlnet_construct/presets/loftr_external_outdoor.json examples/controlnet_construct/presets/loftr_external_indoor.json
git commit -m "feat: add external LoFTR presets"
```

## Task 5: Documentation

**Files:**
- Modify: `examples/controlnet_construct/PRESETS_README.md`

- [ ] **Step 1: Update preset catalog and support matrix**

In `examples/controlnet_construct/PRESETS_README.md`, add these rows to the preset catalog:

```markdown
| `loftr_external_outdoor.json` | LoFTR (built-in) | LoFTR external backend | Outdoor external LoFTR repository/checkpoint path aligned with `run-loftr.py`. |
| `loftr_external_indoor.json` | LoFTR (built-in) | LoFTR external backend | Indoor external LoFTR repository/checkpoint path aligned with `run-loftr.py`. |
```

Add these rows to the real support matrix:

```markdown
| `loftr_external_outdoor.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows when external LoFTR dependencies are available | `direct`: environment with ISIS + `torch` + external LoFTR repo/checkpoint; `export`/`import`: `asp360_new`, plus `deep-learning` for manifest execution | Uses `matcher.backend="external"` and the outdoor checkpoint family from `run-loftr.py`; `loftr_root` and checkpoint paths are machine-specific and should be supplied in local config when auto-discovery is not enough. |
| `loftr_external_indoor.json` | LoFTR | LoFTR (built-in) | Supported in `direct`, `export`, and `import` workflows when external LoFTR dependencies are available | Same as `loftr_external_outdoor.json` | Uses the indoor checkpoint family and `temp_bug_fix:auto`; GPU is recommended for real runs. |
```

- [ ] **Step 2: Add External LoFTR Backend section**

Add this section after the LoFTR matcher description:

```markdown
## External LoFTR Backend

LoFTR presets whose matcher section contains `"backend": "external"` use the
external LoFTR repository and checkpoint workflow validated by
`examples/learning_methods/run-loftr.py`.

Existing LoFTR presets without `backend: "external"` keep the current
ControlNet runtime behavior based on `kornia.feature.LoFTR(pretrained=...)`.
This allows side-by-side comparison between the kornia backend and the external
backend.

External LoFTR supports these preset/runtime options:

- `matcher.model_type`: `outdoor` or `indoor`
- `matcher.loftr_root`: optional path to the external LoFTR repository
- `matcher.checkpoint` or `matcher.checkpoint_path`: optional explicit checkpoint
- `matcher.temp_bug_fix`: `auto`, `true`, or `false`
- `matcher.coarse_threshold`
- `matcher.min_confidence`
- `matcher.top_k`
- `matcher.geometric_filter`: `none`, `homography`, or `fundamental`
- `feature_extractor.preprocess_mode`: `pad` or `resize`
- `feature_extractor.resize_width` and `feature_extractor.resize_height`

Shared presets omit `loftr_root` and checkpoint paths because those values are
machine-specific. If auto-discovery cannot find the sibling external LoFTR
repository, copy the preset and add `matcher.loftr_root` locally.

Real external LoFTR execution should run in the separate `deep-learning` conda
environment. The `asp360_new` environment remains the recommended environment
for ControlNet preparation, export, import, and unit tests.
```

- [ ] **Step 3: Update custom configuration field lists**

In the `Configuration Fields` section, update matcher and feature extractor bullets so they include:

```markdown
- `preprocess_mode`: LoFTR external preprocessing mode (`pad` or `resize`)
- `resize_width`, `resize_height`: optional LoFTR external resize dimensions; must be provided together
- `backend`: Deep matcher backend selector (`official` for LightGlue, `external` or `kornia` for LoFTR)
- `loftr_root`: external LoFTR repository path for `backend: external`
- `checkpoint`, `checkpoint_path`: external LoFTR checkpoint path aliases
- `model_type`: LoFTR external checkpoint family (`outdoor` or `indoor`)
- `temp_bug_fix`, `coarse_threshold`, `min_confidence`, `top_k`, `geometric_filter`: LoFTR external tuning options
```

- [ ] **Step 4: Run documentation-adjacent smoke test**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.deep_match_pipeline_smoke_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit documentation**

```bash
git add examples/controlnet_construct/PRESETS_README.md
git commit -m "docs: document external LoFTR backend"
```

## Task 6: Final Verification

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

Expected: PASS with `smoke import ok`.

- [ ] **Step 2: Run focused config tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: PASS.

- [ ] **Step 3: Run focused adapter tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Run ControlNet matching tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS. If this command fails due to `multiprocessing.Manager()` socket permissions, rerun it in an allowed unsandboxed context and record both the restricted-context failure and the pass.

- [ ] **Step 5: Run manifest regression tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.deep_match_config_rehydration_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test \
  -v
```

Expected: PASS.

- [ ] **Step 6: Run optional real LoFTR smoke in `deep-learning`**

Run only if the separate `deep-learning` conda environment and external LoFTR repository/checkpoints are available:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate deep-learning
export PYTHONPATH="$PWD/examples:$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/learning_methods/test-loftr.py
```

Expected: PASS in the `deep-learning` environment. If the environment, external repository, or checkpoints are unavailable in the current session, record this as skipped and do not block mocked `asp360_new` unit-test completion.

- [ ] **Step 7: Inspect final diff**

Run:

```bash
git status --short
git log --oneline main..HEAD
```

Expected: only commits from this LoFTR branch appear; no unstaged tracked changes remain.

- [ ] **Step 8: Prepare completion summary**

Report:

```text
Implemented external LoFTR backend behind matcher.backend="external".
Existing loftr_default.json remains on the kornia backend.
Added external LoFTR presets for outdoor and indoor model families.
Tests run:
- python tests/smoke_import.py
- python -m pytest tests/unitTest/test_deep_match_config.py -q
- python -m unittest tests.unitTest.image_match_deep_adapter_unit_test -v
- python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
- python -m unittest tests.unitTest.deep_match_config_rehydration_unit_test tests.unitTest.image_match_deep_manifest_unit_test tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
- python examples/learning_methods/test-loftr.py in deep-learning, or skipped because deep-learning / external LoFTR assets were unavailable
```
