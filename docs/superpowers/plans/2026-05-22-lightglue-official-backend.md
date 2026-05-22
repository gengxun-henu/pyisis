# LightGlue Official Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit `backend: "official"` LightGlue runtime path that uses the official `lightglue` frontend and matcher stack while preserving existing LightGlue behavior by default.

**Architecture:** `examples/image_match` remains the runtime owner. `controlnet_construct.deep_match_config` validates and serializes backend-aware presets, `image_match.deep_frontends` builds official LightGlue feature dictionaries from tile arrays, `image_match.deep_matchers.LightGlueMatcher` routes between legacy and official matching semantics, and `image_match.deep_adapter.DeepMatcherAdapter` selects the correct feature extraction path from runtime config.

**Tech Stack:** Python 3.12, unittest/pytest-style existing tests, pybind/ISIS conda environment `asp360_new`, and a separate `deep-learning` conda environment for real LightGlue model execution.

---

## File Structure

- Modify: `examples/controlnet_construct/deep_match_config.py`
  - Add backend-aware LightGlue compatibility validation and allow `lightglue_sift` as an extractor only for `backend: "official"`.
- Modify: `examples/image_match/deep_frontends.py`
  - Add `OfficialLightGlueFrontend`, option validation helpers, official extractor construction, and tensor conversion behavior aligned with `run-lightglue.py`.
- Modify: `examples/image_match/deep_matchers.py`
  - Add backend-aware LightGlue option validation and official match normalization.
- Modify: `examples/image_match/deep_adapter.py`
  - Route `backend: "official"` LightGlue requests through `OfficialLightGlueFrontend`; keep current SuperPoint path for omitted backend.
- Create: five official preset JSON files under `examples/controlnet_construct/presets/`.
- Modify: `examples/controlnet_construct/PRESETS_README.md`
  - Document backend selection, official presets, and `lightglue_sift` semantics.
- Modify: `tests/unitTest/test_deep_match_config.py`
  - Add validation coverage for official frontend combinations, backend rejection, strict option rules, and preset loading.
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`
  - Add runtime routing tests for official frontend usage and legacy default behavior.
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Add matcher/frontend construction tests with mocked `lightglue` modules and verify existing non-official behavior remains.

## Environment Boundary

Most automated tests in this plan run inside `asp360_new` and must mock the
optional `lightglue` dependency. Do not require real LightGlue model imports,
weight downloads, or GPU access for the normal unit test path.

Real deep-learning execution belongs in the separate `deep-learning` conda
environment, where `run-lightglue.py` has already been validated. After the
mocked unit tests pass in `asp360_new`, run one manual smoke check in
`deep-learning` with an official preset if that environment is available.

## Task 1: Backend-Aware Config Validation

**Files:**
- Modify: `examples/controlnet_construct/deep_match_config.py`
- Modify: `tests/unitTest/test_deep_match_config.py`

- [ ] **Step 1: Write failing validation tests**

Add these tests to `tests/unitTest/test_deep_match_config.py` in `TestDeepMatchConfigValidation`:

```python
    def test_official_lightglue_accepts_supported_frontends(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        for extractor_method in ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift"):
            with self.subTest(extractor=extractor_method):
                validate_deep_match_config(
                    {
                        "feature_extractor": {"method": extractor_method},
                        "matcher": {"method": "lightglue", "backend": "official"},
                    }
                )

    def test_non_official_lightglue_still_rejects_non_superpoint_frontends(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        for extractor_method in ("disk", "aliked", "doghardnet", "lightglue_sift"):
            with self.subTest(extractor=extractor_method):
                with pytest.raises(ValueError, match="superpoint"):
                    validate_deep_match_config(
                        {
                            "feature_extractor": {"method": extractor_method},
                            "matcher": {"method": "lightglue"},
                        }
                    )

    def test_lightglue_rejects_unknown_backend(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="backend"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint"},
                    "matcher": {"method": "lightglue", "backend": "experimental"},
                }
            )

    def test_official_lightglue_rejects_unknown_options_and_feature_alias_conflict(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import validate_deep_match_config

        with pytest.raises(ValueError, match="unknown feature_extractor option"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint", "remove_borders": 4},
                    "matcher": {"method": "lightglue", "backend": "official"},
                }
            )
        with pytest.raises(ValueError, match="max_features.*max_keypoints"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint", "max_features": 1000, "max_keypoints": 1000},
                    "matcher": {"method": "lightglue", "backend": "official"},
                }
            )
        with pytest.raises(ValueError, match="unknown matcher option"):
            validate_deep_match_config(
                {
                    "feature_extractor": {"method": "superpoint"},
                    "matcher": {"method": "lightglue", "backend": "official", "prune_threshold": 4},
                }
            )
```

- [ ] **Step 2: Run validation tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: FAIL because `lightglue_sift` is unsupported, official backend validation does not exist, and official option validation is not implemented.

- [ ] **Step 3: Implement backend-aware config validation**

In `examples/controlnet_construct/deep_match_config.py`, add constants near the existing method constants:

```python
LIGHTGLUE_BACKENDS = (None, "official")
OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift")
OFFICIAL_LIGHTGLUE_FEATURE_OPTIONS = {"method", "max_features", "max_keypoints"}
OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS = {
    "method",
    "backend",
    "filter_threshold",
    "depth_confidence",
    "width_confidence",
    "flash",
    "mp",
}
```

Extend `SUPPORTED_EXTRACTOR_METHODS` to include `lightglue_sift`:

```python
SUPPORTED_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift", "loftr")
```

Replace `validate_matcher_feature_compatibility` with a backend-aware signature:

```python
def _normalized_lightglue_backend(matcher: dict[str, Any] | None) -> str | None:
    backend = (matcher or {}).get("backend")
    if backend is None or str(backend).strip() == "":
        return None
    return str(backend).strip().lower()


def _validate_official_lightglue_options(*, extractor: dict[str, Any], matcher: dict[str, Any]) -> None:
    feature_options = set(extractor)
    matcher_options = set(matcher)
    unknown_feature_options = sorted(feature_options - OFFICIAL_LIGHTGLUE_FEATURE_OPTIONS)
    if unknown_feature_options:
        raise ValueError(f"unknown feature_extractor option(s) for official LightGlue: {', '.join(unknown_feature_options)}")
    if "max_features" in extractor and "max_keypoints" in extractor:
        raise ValueError("official LightGlue accepts max_features or max_keypoints, not both.")
    unknown_matcher_options = sorted(matcher_options - OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS)
    if unknown_matcher_options:
        raise ValueError(f"unknown matcher option(s) for official LightGlue: {', '.join(unknown_matcher_options)}")


def validate_matcher_feature_compatibility(
    *,
    matcher_method: str,
    feature_extractor_method: str,
    matcher: dict[str, Any] | None = None,
    extractor: dict[str, Any] | None = None,
) -> None:
    normalized_matcher = str(matcher_method or "").strip().lower()
    normalized_extractor = str(feature_extractor_method or "").strip().lower()
    if normalized_matcher == "lightglue":
        backend = _normalized_lightglue_backend(matcher)
        if backend is not None and backend != "official":
            raise ValueError(f"Unsupported LightGlue matcher.backend={backend!r}; supported values: 'official'.")
        if backend == "official":
            if normalized_extractor not in OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS:
                supported_display = ", ".join(repr(method) for method in OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS)
                raise ValueError(
                    f"matcher.method='lightglue' with matcher.backend='official' requires "
                    f"feature_extractor.method to be one of ({supported_display}); got {normalized_extractor!r}."
                )
            _validate_official_lightglue_options(extractor=dict(extractor or {}), matcher=dict(matcher or {}))
            return

    supported_extractors = MATCHER_EXTRACTOR_REQUIREMENTS.get(normalized_matcher)
    if supported_extractors is None or normalized_extractor in supported_extractors:
        return
    supported_display = ", ".join(repr(method) for method in supported_extractors)
    raise ValueError(
        f"matcher.method={normalized_matcher!r} requires feature_extractor.method to be one of "
        f"({supported_display}); got {normalized_extractor!r}."
    )
```

Update the call inside `validate_deep_match_config`:

```python
    validate_matcher_feature_compatibility(
        matcher_method=matcher_method,
        feature_extractor_method=extractor_method,
        matcher=matcher,
        extractor=extractor,
    )
```

- [ ] **Step 4: Run validation tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit config validation**

```bash
git add examples/controlnet_construct/deep_match_config.py tests/unitTest/test_deep_match_config.py
git commit -m "feat: validate official LightGlue backend config"
```

## Task 2: Official LightGlue Frontend

**Files:**
- Modify: `examples/image_match/deep_frontends.py`
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`

- [ ] **Step 1: Write failing frontend construction and tensor-shape tests**

Add these helpers near existing helper classes in `tests/unitTest/image_match_deep_adapter_unit_test.py`:

```python
class _OfficialExtractorStub:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.device = None
        self.input_shapes: list[tuple[int, ...]] = []

    def eval(self):
        return self

    def to(self, device):
        self.device = device
        return self

    def extract(self, image):
        self.input_shapes.append(tuple(image.shape))
        import torch

        return {
            "keypoints": torch.tensor([[[1.0, 1.0], [2.0, 2.0]]], dtype=torch.float32),
            "descriptors": torch.ones((1, 2, 4), dtype=torch.float32),
        }
```

Add these tests to `ImageMatchDeepAdapterUnitTest`:

```python
    def test_official_lightglue_frontend_builds_expected_extractors_and_channel_shapes(self):
        deep_frontends_module = __import__("image_match.deep_frontends", fromlist=["OfficialLightGlueFrontend"])

        for method, class_name, expected_channels in (
            ("superpoint", "SuperPoint", 1),
            ("disk", "DISK", 3),
            ("aliked", "ALIKED", 3),
            ("doghardnet", "DoGHardNet", 1),
            ("lightglue_sift", "SIFT", 1),
        ):
            with self.subTest(method=method):
                constructed = {}

                def _constructor(**kwargs):
                    instance = _OfficialExtractorStub(**kwargs)
                    constructed[class_name] = instance
                    return instance

                lightglue_module = SimpleNamespace(
                    SuperPoint=mock.Mock(side_effect=_constructor if class_name == "SuperPoint" else lambda **kwargs: _OfficialExtractorStub(**kwargs)),
                    DISK=mock.Mock(side_effect=_constructor if class_name == "DISK" else lambda **kwargs: _OfficialExtractorStub(**kwargs)),
                    ALIKED=mock.Mock(side_effect=_constructor if class_name == "ALIKED" else lambda **kwargs: _OfficialExtractorStub(**kwargs)),
                    DoGHardNet=mock.Mock(side_effect=_constructor if class_name == "DoGHardNet" else lambda **kwargs: _OfficialExtractorStub(**kwargs)),
                    SIFT=mock.Mock(side_effect=_constructor if class_name == "SIFT" else lambda **kwargs: _OfficialExtractorStub(**kwargs)),
                )
                with mock.patch.dict(sys.modules, {"torch": __import__("torch"), "lightglue": lightglue_module}, clear=False):
                    frontend = deep_frontends_module.OfficialLightGlueFrontend(
                        feature_extractor_method=method,
                        feature_options={"max_features": 123},
                    )
                    features = frontend.extract(np.arange(16, dtype=np.float32).reshape(4, 4), device="cpu")

                extractor = constructed[class_name]
                self.assertEqual(extractor.kwargs["max_num_keypoints"], 123)
                self.assertEqual(extractor.input_shapes[-1][1], expected_channels)
                self.assertEqual(features["keypoints"].shape, (2, 2))
                self.assertEqual(features["descriptors"].shape[0], 2)

    def test_official_lightglue_frontend_rejects_feature_alias_conflict(self):
        deep_frontends_module = __import__("image_match.deep_frontends", fromlist=["OfficialLightGlueFrontend"])

        with self.assertRaisesRegex(ValueError, "max_features.*max_keypoints"):
            deep_frontends_module.OfficialLightGlueFrontend(
                feature_extractor_method="superpoint",
                feature_options={"max_features": 10, "max_keypoints": 20},
            )
```

- [ ] **Step 2: Run frontend tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_official_lightglue_frontend_builds_expected_extractors_and_channel_shapes tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_official_lightglue_frontend_rejects_feature_alias_conflict -v
```

Expected: FAIL because `OfficialLightGlueFrontend` does not exist.

- [ ] **Step 3: Implement `OfficialLightGlueFrontend`**

In `examples/image_match/deep_frontends.py`, add constants and the class after `SuperPointFrontend`:

```python
OFFICIAL_LIGHTGLUE_FRONTEND_CLASSES = {
    "superpoint": "SuperPoint",
    "disk": "DISK",
    "aliked": "ALIKED",
    "doghardnet": "DoGHardNet",
    "lightglue_sift": "SIFT",
}
OFFICIAL_LIGHTGLUE_RGB_FRONTENDS = {"disk", "aliked"}


class OfficialLightGlueFrontend:
    def __init__(
        self,
        *,
        feature_extractor_method: str,
        feature_options: dict[str, Any] | None = None,
    ) -> None:
        self.feature_extractor_method = str(feature_extractor_method or "").strip().lower()
        if self.feature_extractor_method not in OFFICIAL_LIGHTGLUE_FRONTEND_CLASSES:
            raise DeepFrontendError(f"Unsupported official LightGlue frontend: {self.feature_extractor_method!r}.")
        self.feature_options = dict(feature_options or {})
        self.max_num_keypoints = self._resolve_max_num_keypoints(self.feature_options)
        self._extractor = None

    def _resolve_max_num_keypoints(self, options: dict[str, Any]) -> int:
        has_max_features = "max_features" in options
        has_max_keypoints = "max_keypoints" in options
        if has_max_features and has_max_keypoints:
            raise ValueError("official LightGlue accepts max_features or max_keypoints, not both.")
        value = options.get("max_features", options.get("max_keypoints", 2048))
        return int(value)

    def _build_extractor(self, device: str):
        try:
            import lightglue
        except Exception:
            _raise_missing_dependency(
                method="lightglue",
                missing="lightglue",
                install_hint="pip install lightglue",
            )
        class_name = OFFICIAL_LIGHTGLUE_FRONTEND_CLASSES[self.feature_extractor_method]
        constructor = getattr(lightglue, class_name)
        return constructor(max_num_keypoints=self.max_num_keypoints).eval().to(device)

    def _image_tensor(self, image, *, device: str):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="lightglue",
                missing="torch",
                install_hint="pip install torch lightglue",
            )
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
        if self.feature_extractor_method in OFFICIAL_LIGHTGLUE_RGB_FRONTENDS:
            image_hwc = np.repeat(image_plane[..., None], 3, axis=2)
            image_chw = np.transpose(image_hwc, (2, 0, 1))
        else:
            image_chw = image_plane[None, :, :]
        return torch.from_numpy(image_chw).to(device=device, dtype=torch.float32)[None]

    def extract(self, image, device: str):
        if self._extractor is None:
            self._extractor = self._build_extractor(device)
        tensor = self._image_tensor(image, device=device)
        features = self._extractor.extract(tensor)
        feature_map = dict(features or {})
        keypoints = feature_map.get("keypoints", np.zeros((0, 2), dtype=np.float32))
        if hasattr(keypoints, "detach"):
            if keypoints.ndim == 3 and keypoints.shape[0] == 1:
                keypoints = keypoints[0]
            keypoints_array = keypoints.detach().cpu().numpy().astype(np.float32, copy=False).reshape(-1, 2)
        else:
            keypoints_array = np.asarray(keypoints, dtype=np.float32).reshape(-1, 2)
        normalized = {"keypoints": keypoints_array}
        for key, value in feature_map.items():
            if key == "keypoints":
                continue
            if hasattr(value, "detach"):
                resolved = value[0] if value.ndim >= 2 and value.shape[0] == 1 else value
                normalized[key] = resolved.detach().cpu().numpy()
            else:
                normalized[key] = value
        return normalized
```

- [ ] **Step 4: Run frontend tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_official_lightglue_frontend_builds_expected_extractors_and_channel_shapes tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_official_lightglue_frontend_rejects_feature_alias_conflict -v
```

Expected: PASS.

- [ ] **Step 5: Commit official frontend**

```bash
git add examples/image_match/deep_frontends.py tests/unitTest/image_match_deep_adapter_unit_test.py
git commit -m "feat: add official LightGlue frontend"
```

## Task 3: Backend-Aware Matcher and Adapter Routing

**Files:**
- Modify: `examples/image_match/deep_matchers.py`
- Modify: `examples/image_match/deep_adapter.py`
- Modify: `tests/unitTest/image_match_deep_adapter_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing adapter routing test**

Add this test to `tests/unitTest/image_match_deep_adapter_unit_test.py`:

```python
    def test_deep_matcher_adapter_uses_official_lightglue_frontend_when_backend_is_official(self):
        runtime = SimpleNamespace(
            prefer_gpu=False,
            matcher_method="lightglue",
            feature_extractor_method="disk",
            matcher_options={"backend": "official", "filter_threshold": 0.05},
            feature_options={"max_features": 64},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )
        adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)
        matcher = _CapturingFeatureMatcher()
        official_frontend = mock.Mock()
        official_frontend.extract.side_effect = [
            {"keypoints": np.array([[1.0, 1.0]], dtype=np.float32), "descriptors": np.ones((1, 4), dtype=np.float32)},
            {"keypoints": np.array([[2.0, 2.0]], dtype=np.float32), "descriptors": np.ones((1, 4), dtype=np.float32)},
        ]

        with mock.patch("image_match.deep_adapter.OfficialLightGlueFrontend", return_value=official_frontend) as frontend_constructor, mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ) as build_matcher_mock:
            adapter.match_pair(
                matcher_method="lightglue",
                left_image=np.zeros((8, 8), dtype=np.float32),
                right_image=np.zeros((8, 8), dtype=np.float32),
            )

        frontend_constructor.assert_called_once_with(
            feature_extractor_method="disk",
            feature_options={"max_features": 64},
        )
        self.assertEqual(official_frontend.extract.call_count, 2)
        build_matcher_mock.assert_called_once_with(
            "lightglue",
            device="cpu",
            feature_extractor_method="disk",
            matcher_options={"backend": "official", "filter_threshold": 0.05},
            feature_options={"max_features": 64},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )
```

- [ ] **Step 2: Write failing matcher construction test**

Add this test to `tests/unitTest/controlnet_construct_matching_unit_test.py` near the existing LightGlue matcher tests:

```python
    def test_official_lightglue_matcher_uses_official_options_and_frontend_name(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        lightglue_constructor = mock.Mock(return_value=_EvalToDeviceModule())
        torch_module = _stub_module("torch")
        lightglue_module = _stub_module("lightglue", LightGlue=lightglue_constructor)

        with mock.patch.dict(sys.modules, {"torch": torch_module, "lightglue": lightglue_module}, clear=False):
            matcher = deep_matchers_module.build_deep_matcher(
                "lightglue",
                device="cpu",
                feature_extractor_method="lightglue_sift",
                matcher_options={
                    "backend": "official",
                    "filter_threshold": 0.05,
                    "depth_confidence": -1,
                    "width_confidence": -1,
                    "flash": True,
                    "mp": False,
                },
                feature_options={"max_features": 128},
                device_options={"dtype": "float32"},
            )
            matcher._load_matcher()

        lightglue_constructor.assert_called_once_with(
            features="sift",
            filter_threshold=0.05,
            depth_confidence=-1,
            width_confidence=-1,
            flash=True,
            mp=False,
        )
```

- [ ] **Step 3: Run routing tests and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_deep_matcher_adapter_uses_official_lightglue_frontend_when_backend_is_official tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_official_lightglue_matcher_uses_official_options_and_frontend_name -v
```

Expected: FAIL because adapter routing and official matcher backend handling are not implemented.

- [ ] **Step 4: Implement matcher backend handling**

In `examples/image_match/deep_matchers.py`, add helper constants near `LightGlueMatcher`:

```python
OFFICIAL_LIGHTGLUE_FRONTEND_ALIASES = {"lightglue_sift": "sift"}
OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS = {"filter_threshold", "depth_confidence", "width_confidence", "flash", "mp"}
```

Modify `LightGlueMatcher.__init__` to capture backend:

```python
        self.backend = str(self.matcher_options.get("backend") or "legacy").strip().lower()
```

Modify `_lightglue_options`:

```python
    def _lightglue_options(self) -> dict[str, Any]:
        options = _copy_options(self.matcher_options)
        backend = str(options.pop("backend", self.backend) or "legacy").strip().lower()
        if backend == "official":
            _reject_unknown_options(
                method=self.method,
                options=options,
                allowed=OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS,
            )
            return options
        if backend not in {"legacy", ""}:
            _raise_unsupported_option(method=self.method, option_name="backend", option_value=backend)
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="weights_path",
            ignored_parameters=self.ignored_parameters,
        )
        _reject_unknown_options(
            method=self.method,
            options=options,
            allowed={"weights", "flash", "prune_threshold", "filter_threshold", "depth_confidence", "width_confidence"},
        )
        return options
```

Modify `_load_matcher` compatibility and LightGlue feature name:

```python
        if self.backend == "official":
            lightglue_feature_name = OFFICIAL_LIGHTGLUE_FRONTEND_ALIASES.get(
                self.feature_extractor_method,
                self.feature_extractor_method,
            )
        else:
            if self.feature_extractor_method != "superpoint":
                raise DeepMatcherError(
                    f"Deep matcher '{self.method}' currently only supports feature_extractor_method='superpoint', "
                    f"got {self.feature_extractor_method!r}."
                )
            lightglue_feature_name = self.feature_extractor_method
```

Use `features=lightglue_feature_name` in the constructor.

- [ ] **Step 5: Implement adapter routing**

In `examples/image_match/deep_adapter.py`, import `OfficialLightGlueFrontend`:

```python
from .deep_frontends import DeepDependencyError, DeepFrontendError, LoFTRFrontend, OfficialLightGlueFrontend, SuperPointFrontend, normalize_deep_method, resolve_torch_device
```

Add a helper:

```python
def _runtime_matcher_backend(runtime_config: Any | None) -> str | None:
    matcher_options = getattr(runtime_config, "matcher_options", {}) if runtime_config is not None else {}
    backend = (matcher_options or {}).get("backend")
    if backend is None or str(backend).strip() == "":
        return None
    return str(backend).strip().lower()
```

In `DeepMatcherAdapter.__init__`, add:

```python
        self._official_lightglue_frontend = None
```

Add:

```python
    def _get_official_lightglue_frontend(self, extractor_method: str) -> OfficialLightGlueFrontend:
        if self._official_lightglue_frontend is None:
            self._official_lightglue_frontend = OfficialLightGlueFrontend(
                feature_extractor_method=extractor_method,
                feature_options=dict(getattr(self._runtime_config, "feature_options", {}) or {}),
            )
        return self._official_lightglue_frontend
```

Modify the `method in ("superglue", "lightglue")` block so LightGlue official backend uses the official frontend:

```python
                backend = _runtime_matcher_backend(self._runtime_config)
                if method == "lightglue" and backend == "official":
                    frontend = self._get_official_lightglue_frontend(extractor_method)
                    features_left = frontend.extract(left_image, device=device)
                    features_right = frontend.extract(right_image, device=device)
                else:
                    if extractor_method != "superpoint":
                        raise DeepFrontendError(
                            f"feature_extractor.method={extractor_method!r} is validated but not yet implemented for {method!r}."
                        )
                    features_left = self._superpoint.extract(left_image, device=device)
                    features_right = self._superpoint.extract(right_image, device=device)
```

Keep the existing invalid-mask filtering immediately after feature extraction.

- [ ] **Step 6: Run routing tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test.ImageMatchDeepAdapterUnitTest.test_deep_matcher_adapter_uses_official_lightglue_frontend_when_backend_is_official tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_official_lightglue_matcher_uses_official_options_and_frontend_name -v
```

Expected: PASS.

- [ ] **Step 7: Commit routing implementation**

```bash
git add examples/image_match/deep_matchers.py examples/image_match/deep_adapter.py tests/unitTest/image_match_deep_adapter_unit_test.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: route official LightGlue backend"
```

## Task 4: Official Presets

**Files:**
- Create: `examples/controlnet_construct/presets/lightglue_official_superpoint.json`
- Create: `examples/controlnet_construct/presets/lightglue_official_disk.json`
- Create: `examples/controlnet_construct/presets/lightglue_official_aliked.json`
- Create: `examples/controlnet_construct/presets/lightglue_official_doghardnet.json`
- Create: `examples/controlnet_construct/presets/lightglue_official_sift.json`
- Modify: `tests/unitTest/test_deep_match_config.py`

- [ ] **Step 1: Write failing preset existence test**

Add this test to `TestPresetFiles` in `tests/unitTest/test_deep_match_config.py`:

```python
    def test_official_lightglue_presets_exist_and_load(self):
        import sys
        sys.path.insert(0, str(DEEP_MATCH_CONFIG_PATH.parent))
        from deep_match_config import load_deep_match_config

        expected = {
            "lightglue_official_superpoint.json": "superpoint",
            "lightglue_official_disk.json": "disk",
            "lightglue_official_aliked.json": "aliked",
            "lightglue_official_doghardnet.json": "doghardnet",
            "lightglue_official_sift.json": "lightglue_sift",
        }
        presets_dir = DEEP_MATCH_CONFIG_PATH.parent / "presets"
        for preset_name, extractor_method in expected.items():
            with self.subTest(preset=preset_name):
                config = load_deep_match_config(str(presets_dir / preset_name))
                assert config["feature_extractor"]["method"] == extractor_method
                assert config["matcher"]["method"] == "lightglue"
                assert config["matcher"]["backend"] == "official"
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

Expected: FAIL because the new preset files do not exist.

- [ ] **Step 3: Add official preset files**

Create `examples/controlnet_construct/presets/lightglue_official_superpoint.json`:

```json
{
  "feature_extractor": {
    "method": "superpoint",
    "max_features": 4096
  },
  "matcher": {
    "method": "lightglue",
    "backend": "official",
    "filter_threshold": 0.05,
    "depth_confidence": -1,
    "width_confidence": -1,
    "flash": true,
    "mp": true
  },
  "device": {
    "prefer_gpu": true,
    "dtype": "float32"
  },
  "fallback": {
    "on_error": "sift_flann"
  }
}
```

Create `examples/controlnet_construct/presets/lightglue_official_disk.json` with `"method": "disk"` and the same other fields.

Create `examples/controlnet_construct/presets/lightglue_official_aliked.json` with `"method": "aliked"` and the same other fields.

Create `examples/controlnet_construct/presets/lightglue_official_doghardnet.json` with `"method": "doghardnet"` and the same other fields.

Create `examples/controlnet_construct/presets/lightglue_official_sift.json` with `"method": "lightglue_sift"` and the same other fields.

- [ ] **Step 4: Run preset tests and verify pass**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m pytest tests/unitTest/test_deep_match_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit presets**

```bash
git add tests/unitTest/test_deep_match_config.py examples/controlnet_construct/presets/lightglue_official_superpoint.json examples/controlnet_construct/presets/lightglue_official_disk.json examples/controlnet_construct/presets/lightglue_official_aliked.json examples/controlnet_construct/presets/lightglue_official_doghardnet.json examples/controlnet_construct/presets/lightglue_official_sift.json
git commit -m "feat: add official LightGlue presets"
```

## Task 5: Documentation

**Files:**
- Modify: `examples/controlnet_construct/PRESETS_README.md`

- [ ] **Step 1: Update preset documentation**

In `examples/controlnet_construct/PRESETS_README.md`, add official presets to the catalog and support table. Add a section named `Official LightGlue Backend` with this content:

```markdown
## Official LightGlue Backend

LightGlue presets whose matcher section contains `"backend": "official"` use the
same LightGlue package family validated by `examples/learning_methods/run-lightglue.py`:

- `lightglue.SuperPoint`
- `lightglue.DISK`
- `lightglue.ALIKED`
- `lightglue.DoGHardNet`
- `lightglue.SIFT`
- `lightglue.LightGlue`

Existing LightGlue presets without `backend: "official"` keep the current
ControlNet runtime behavior. This allows side-by-side comparison between the
legacy backend and the official backend.

`feature_extractor.method: "lightglue_sift"` means the official LightGlue SIFT
frontend paired with `lightglue.LightGlue`. It is not the classic ControlNet
OpenCV SIFT matcher path.
```

Document the five new preset files:

```markdown
| `lightglue_official_superpoint.json` | SuperPoint | LightGlue official backend | Uses `lightglue.SuperPoint` + `lightglue.LightGlue`. |
| `lightglue_official_disk.json` | DISK | LightGlue official backend | Uses `lightglue.DISK` + `lightglue.LightGlue`. |
| `lightglue_official_aliked.json` | ALIKED | LightGlue official backend | Uses `lightglue.ALIKED` + `lightglue.LightGlue`. |
| `lightglue_official_doghardnet.json` | DoGHardNet | LightGlue official backend | Uses `lightglue.DoGHardNet` + `lightglue.LightGlue`. |
| `lightglue_official_sift.json` | LightGlue SIFT frontend | LightGlue official backend | Uses `lightglue.SIFT` + `lightglue.LightGlue`; not classic OpenCV SIFT. |
```

- [ ] **Step 2: Run documentation smoke test if available**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.deep_match_pipeline_smoke_unit_test -v
```

Expected: PASS.

- [ ] **Step 3: Commit documentation**

```bash
git add examples/controlnet_construct/PRESETS_README.md
git commit -m "docs: document official LightGlue backend"
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

Expected: PASS. If this command fails in a sandbox due to `multiprocessing.Manager()` socket permissions, rerun it outside the sandbox or with an allowed unsandboxed command context and record both the sandbox failure and the unsandboxed pass.

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

- [ ] **Step 6: Run optional real LightGlue smoke in `deep-learning`**

Run only if the separate `deep-learning` conda environment is available and has
the official `lightglue` package installed:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate deep-learning
export PYTHONPATH="$PWD/examples:$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/learning_methods/test-lightglue.py
```

Expected: PASS in the `deep-learning` environment. If the environment is not
available in the current machine/session, record this as skipped and do not
block the mocked `asp360_new` unit-test completion.

- [ ] **Step 7: Inspect final diff**

Run:

```bash
git status --short
git diff --stat main
```

Expected: no unstaged tracked changes from this plan. Existing unrelated `pyisis_development.code-workspace` local changes may appear and must not be included unless the user explicitly requests it.

- [ ] **Step 8: Prepare completion summary**

Report:

```text
Implemented official LightGlue backend behind matcher.backend=\"official\".
Existing LightGlue presets remain on the legacy backend.
Added official presets for superpoint, disk, aliked, doghardnet, and lightglue_sift.
Tests run:
- python tests/smoke_import.py
- python -m pytest tests/unitTest/test_deep_match_config.py -q
- python -m unittest tests.unitTest.image_match_deep_adapter_unit_test -v
- python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
- python -m unittest tests.unitTest.deep_match_config_rehydration_unit_test tests.unitTest.image_match_deep_manifest_unit_test tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
- python examples/learning_methods/test-lightglue.py in deep-learning, or skipped because deep-learning was unavailable
```
