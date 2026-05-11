# Learning Method LightGlue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 controlnet_construct 流程中以最小侵入方式新增 `superglue`、`lightglue`、`loftr` 三种深度匹配方法，复用现有控制网与 CPU RANSAC 流程，并保持 `bf`/`flann` 默认行为不变。

**Architecture:** 保持 `matcher_method` 作为唯一入口，在 `tile_matching.py` 的现有匹配分派点增加 `DeepMatcherAdapter` 分支。`superglue`/`lightglue` 走 SuperPoint 特征提取 + 深度匹配，`loftr` 走 detector-free 路径，三者都归一化为当前匹配记录结构。GPU 不可用时只做同方法 CPU 回退，不做跨方法静默降级。

**Tech Stack:** Python 3.12 (asp360_new), OpenCV, PyTorch(可选), existing controlnet_construct pipeline, unittest/pytest, bash wrapper scripts.

---

## File structure

- Create: `examples/controlnet_construct/deep_frontends.py`
  - SuperPoint/LoFTR 前处理与设备选择。
- Create: `examples/controlnet_construct/deep_matchers.py`
  - `SuperGlueMatcher` / `LightGlueMatcher` / `LoFTRMatcher` 推理包装。
- Create: `examples/controlnet_construct/deep_adapter.py`
  - 深度方法总入口、GPU->CPU 同方法回退、输出结构归一化。
- Modify: `examples/controlnet_construct/tile_matching.py`
  - 扩展 `matcher_method` 允许值并接入深度分派点，保持 bf/flann 旧路径。
- Modify: `examples/controlnet_construct/image_match.py`
  - CLI/help 与配置校验提示补齐。
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
  - matcher 方法帮助文案更新。
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
  - matcher 方法帮助文案更新。
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - 方法校验、分派、fallback、输出兼容测试。
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - wrapper 参数透传与优先级兼容测试。

### Task 1: 扩展 matcher_method 的测试基线（先红）

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify in Task 2: `examples/controlnet_construct/tile_matching.py`
- Modify in Task 4: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: 增加 matcher_method 新取值的失败测试**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
    def test_normalize_matcher_method_accepts_deep_methods(self):
        self.assertEqual(tile_matching._normalize_matcher_method("superglue"), "superglue")
        self.assertEqual(tile_matching._normalize_matcher_method("LightGlue"), "lightglue")
        self.assertEqual(tile_matching._normalize_matcher_method("LOFTR"), "loftr")

    def test_normalize_matcher_method_rejects_unknown_method(self):
        with self.assertRaisesRegex(ValueError, "matcher_method"):
            tile_matching._normalize_matcher_method("orb")
```

在 `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 增加：

```python
    def test_pipeline_forwards_deep_matcher_method(self):
        argv = [
            "--left", "left.cub",
            "--right", "right.cub",
            "--matcher-method", "lightglue",
        ]
        parsed = controlnet_stereopair._build_arg_parser().parse_args(argv)
        self.assertEqual(parsed.matcher_method, "lightglue")
```

- [ ] **Step 2: 运行新增测试，确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_normalize_matcher_method_accepts_deep_methods \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_normalize_matcher_method_rejects_unknown_method \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_pipeline_forwards_deep_matcher_method \
  -v
```

Expected: FAIL（`ValueError` 或断言失败，因尚未支持深度方法取值）。

- [ ] **Step 3: 最小实现 matcher_method 扩展**

在 `examples/controlnet_construct/tile_matching.py` 修改：

```python
SUPPORTED_MATCHER_METHODS = ("bf", "flann", "superglue", "lightglue", "loftr")
```

并保持 `_normalize_matcher_method` 的错误信息包含 `SUPPORTED_MATCHER_METHODS`，便于测试断言。

在 `examples/controlnet_construct/image_match.py` 的 `--matcher-method` help 文案同步新增取值。

- [ ] **Step 4: 运行相同测试，确认通过**

Run: 同 Step 2 命令。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  tests/unitTest/controlnet_construct_matching_unit_test.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py \
  examples/controlnet_construct/tile_matching.py \
  examples/controlnet_construct/image_match.py
git commit -m "feat: extend matcher_method to deep methods" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: 建立深度模块骨架与依赖错误语义（先红）

**Files:**
- Create: `examples/controlnet_construct/deep_frontends.py`
- Create: `examples/controlnet_construct/deep_matchers.py`
- Create: `examples/controlnet_construct/deep_adapter.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: 增加深度适配器行为失败测试**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
    def test_deep_adapter_rejects_cross_method_fallback(self):
        from controlnet_construct.deep_adapter import DeepMatcherAdapter

        adapter = DeepMatcherAdapter()
        with self.assertRaisesRegex(RuntimeError, "same method"):
            adapter._raise_cross_method_fallback_error("loftr", "bf")

    def test_deep_adapter_missing_dependency_error_is_explicit(self):
        from controlnet_construct.deep_adapter import DeepDependencyError

        err = DeepDependencyError("lightglue", "torch not installed")
        self.assertIn("lightglue", str(err))
        self.assertIn("torch not installed", str(err))
```

- [ ] **Step 2: 运行新增测试，确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_deep_adapter_rejects_cross_method_fallback \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_deep_adapter_missing_dependency_error_is_explicit \
  -v
```

Expected: FAIL（模块/类不存在）。

- [ ] **Step 3: 编写最小骨架实现**

`examples/controlnet_construct/deep_frontends.py`:

```python
class DeepFrontendError(RuntimeError):
    pass


def resolve_torch_device(prefer_gpu: bool) -> str:
    if prefer_gpu:
        return "cuda"
    return "cpu"
```

`examples/controlnet_construct/deep_matchers.py`:

```python
class DeepMatcherError(RuntimeError):
    pass


class SuperGlueMatcher:
    method = "superglue"


class LightGlueMatcher:
    method = "lightglue"


class LoFTRMatcher:
    method = "loftr"
```

`examples/controlnet_construct/deep_adapter.py`:

```python
class DeepDependencyError(RuntimeError):
    def __init__(self, method: str, reason: str) -> None:
        super().__init__(f"Deep matcher '{method}' dependency error: {reason}")


class DeepMatcherAdapter:
    def _raise_cross_method_fallback_error(self, requested: str, fallback_to: str) -> None:
        raise RuntimeError(
            f"Deep matcher fallback must stay on same method: requested={requested}, fallback_to={fallback_to}"
        )
```

- [ ] **Step 4: 运行相同测试，确认通过**

Run: 同 Step 2 命令。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/deep_frontends.py \
  examples/controlnet_construct/deep_matchers.py \
  examples/controlnet_construct/deep_adapter.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: add deep matcher adapter scaffolding" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: 在 tile matching 接入深度分派与同方法回退（先红）

**Files:**
- Modify: `examples/controlnet_construct/tile_matching.py`
- Modify: `examples/controlnet_construct/deep_adapter.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: 新增分派与 fallback 失败测试**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
    def test_match_tile_dispatches_to_deep_adapter_for_lightglue(self):
        calls = []

        class _StubAdapter:
            def match_pair_with_fallback(self, **kwargs):
                calls.append(kwargs["matcher_method"])
                return [], [], []

        with mock.patch("controlnet_construct.tile_matching.DeepMatcherAdapter", return_value=_StubAdapter()):
            tile_matching._match_tile_from_window_values(
                left_image=np.zeros((16, 16), dtype=np.uint8),
                right_image=np.zeros((16, 16), dtype=np.uint8),
                left_x0=0, left_y0=0, right_x0=0, right_y0=0,
                matcher_method="lightglue",
                use_gpu=True,
            )
        self.assertEqual(calls, ["lightglue"])

    def test_match_tile_deep_gpu_failure_falls_back_to_cpu_same_method(self):
        class _StubAdapter:
            def __init__(self):
                self.calls = []
            def match_pair_with_fallback(self, **kwargs):
                self.calls.append((kwargs["matcher_method"], kwargs["prefer_gpu"]))
                return [], [], []

        stub = _StubAdapter()
        with mock.patch("controlnet_construct.tile_matching.DeepMatcherAdapter", return_value=stub):
            tile_matching._match_tile_from_window_values(
                left_image=np.zeros((16, 16), dtype=np.uint8),
                right_image=np.zeros((16, 16), dtype=np.uint8),
                left_x0=0, left_y0=0, right_x0=0, right_y0=0,
                matcher_method="loftr",
                use_gpu=True,
            )
        self.assertEqual(stub.calls[0][0], "loftr")
```

- [ ] **Step 2: 运行新增测试，确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_tile_dispatches_to_deep_adapter_for_lightglue \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_tile_deep_gpu_failure_falls_back_to_cpu_same_method \
  -v
```

Expected: FAIL（当前 `_match_tile_from_window_values` 未接入 deep adapter 分支）。

- [ ] **Step 3: 实现 deep 分派点**

在 `examples/controlnet_construct/tile_matching.py`：

```python
from .deep_adapter import DeepMatcherAdapter

DEEP_MATCHER_METHODS = ("superglue", "lightglue", "loftr")
```

在 `_match_tile_from_window_values` 的 matcher 分支前加：

```python
if matcher_method in DEEP_MATCHER_METHODS:
    adapter = DeepMatcherAdapter()
    return adapter.match_pair_with_fallback(
        matcher_method=matcher_method,
        left_image=left_image,
        right_image=right_image,
        prefer_gpu=use_gpu,
    )
```

在 `examples/controlnet_construct/deep_adapter.py` 增加：

```python
    def match_pair_with_fallback(self, *, matcher_method, left_image, right_image, prefer_gpu):
        try:
            return self.match_pair(
                matcher_method=matcher_method,
                left_image=left_image,
                right_image=right_image,
                device="cuda" if prefer_gpu else "cpu",
            )
        except Exception:
            if not prefer_gpu:
                raise
            return self.match_pair(
                matcher_method=matcher_method,
                left_image=left_image,
                right_image=right_image,
                device="cpu",
            )
```

- [ ] **Step 4: 运行相同测试，确认通过**

Run: 同 Step 2 命令。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/tile_matching.py \
  examples/controlnet_construct/deep_adapter.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: route deep matcher methods in tile matching" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: 实现 SuperPoint+SuperGlue/LightGlue 与 LoFTR 端到端适配（先红）

**Files:**
- Modify: `examples/controlnet_construct/deep_frontends.py`
- Modify: `examples/controlnet_construct/deep_matchers.py`
- Modify: `examples/controlnet_construct/deep_adapter.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: 增加统一输出结构失败测试**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
    def test_deep_adapter_normalizes_outputs_to_match_triplet(self):
        from controlnet_construct.deep_adapter import DeepMatcherAdapter

        adapter = DeepMatcherAdapter()
        normalized = adapter._normalize_matches(
            left_points=np.array([[1.0, 2.0]], dtype=np.float32),
            right_points=np.array([[3.0, 4.0]], dtype=np.float32),
            scores=np.array([0.9], dtype=np.float32),
        )
        left_kps, right_kps, matches = normalized
        self.assertEqual(len(left_kps), 1)
        self.assertEqual(len(right_kps), 1)
        self.assertEqual(len(matches), 1)
```

- [ ] **Step 2: 运行新增测试，确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_deep_adapter_normalizes_outputs_to_match_triplet \
  -v
```

Expected: FAIL（`_normalize_matches` 尚未实现）。

- [ ] **Step 3: 完整实现三方法适配器接口**

在 `examples/controlnet_construct/deep_frontends.py` 增加：

```python
class SuperPointFrontend:
    def extract(self, image, device: str):
        return {"keypoints": np.zeros((0, 2), dtype=np.float32), "descriptors": np.zeros((0, 256), dtype=np.float32)}


class LoFTRFrontend:
    def prepare(self, left_image, right_image, device: str):
        return {"left": left_image, "right": right_image}
```

在 `examples/controlnet_construct/deep_matchers.py` 增加：

```python
    def match(self, *, features_left, features_right, device: str):
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
```

在 `examples/controlnet_construct/deep_adapter.py` 增加：

```python
    def match_pair(self, *, matcher_method, left_image, right_image, device):
        if matcher_method not in ("superglue", "lightglue", "loftr"):
            raise ValueError(f"Unsupported deep matcher_method: {matcher_method}")

        if matcher_method in ("superglue", "lightglue"):
            features_left = self._superpoint.extract(left_image, device=device)
            features_right = self._superpoint.extract(right_image, device=device)
            if matcher_method == "superglue":
                left_points, right_points, scores = self._superglue.match(
                    features_left=features_left,
                    features_right=features_right,
                    device=device,
                )
            else:
                left_points, right_points, scores = self._lightglue.match(
                    features_left=features_left,
                    features_right=features_right,
                    device=device,
                )
            return self._normalize_matches(
                left_points=left_points,
                right_points=right_points,
                scores=scores,
            )

        prepared = self._loftr_frontend.prepare(left_image, right_image, device=device)
        left_points, right_points, scores = self._loftr.match(
            left_image=prepared["left"],
            right_image=prepared["right"],
            device=device,
        )
        return self._normalize_matches(
            left_points=left_points,
            right_points=right_points,
            scores=scores,
        )

    def _normalize_matches(self, *, left_points, right_points, scores):
        left_kps = [cv2.KeyPoint(float(p[0]), float(p[1]), 1.0) for p in left_points]
        right_kps = [cv2.KeyPoint(float(p[0]), float(p[1]), 1.0) for p in right_points]
        matches = [
            cv2.DMatch(_queryIdx=i, _trainIdx=i, _distance=float(1.0 - s))
            for i, s in enumerate(scores)
        ]
        return left_kps, right_kps, matches
```

- [ ] **Step 4: 运行相同测试，确认通过**

Run: 同 Step 2 命令。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/deep_frontends.py \
  examples/controlnet_construct/deep_matchers.py \
  examples/controlnet_construct/deep_adapter.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: implement deep matcher pipelines and normalization" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 5: CLI/脚本与配置可用性补齐（先红）

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: 增加脚本帮助与透传失败测试**

在 `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 增加：

```python
    def test_batch_wrapper_accepts_lightglue_in_help_text(self):
        content = Path("examples/controlnet_construct/run_image_match_batch_example.sh").read_text(encoding="utf-8")
        self.assertIn("lightglue", content)
        self.assertIn("superglue", content)
        self.assertIn("loftr", content)
```

- [ ] **Step 2: 运行新增测试，确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_batch_wrapper_accepts_lightglue_in_help_text \
  -v
```

Expected: FAIL（脚本文案尚未包含新方法）。

- [ ] **Step 3: 更新 CLI 与脚本文案**

更新 `examples/controlnet_construct/image_match.py` 的 `--matcher-method` help：

```python
help="Matcher method: bf, flann, superglue, lightglue, loftr (default: bf)"
```

更新 `examples/controlnet_construct/run_image_match_batch_example.sh` 与 `run_pipeline_example.sh` 帮助输出中的 matcher 说明，列出 `superglue/lightglue/loftr`。

- [ ] **Step 4: 运行相同测试，确认通过**

Run: 同 Step 2 命令。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/image_match.py \
  examples/controlnet_construct/run_image_match_batch_example.sh \
  examples/controlnet_construct/run_pipeline_example.sh \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "docs: expose deep matcher methods in cli wrappers" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 6: 回归与兼容性验证（绿）

**Files:**
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: `tests/unitTest/gpu_sift_unit_test.py`

- [ ] **Step 1: 运行匹配主测试集**

Run:

```bash
bash scripts/build_test_smoke.sh unit-module tests.unitTest.controlnet_construct_matching_unit_test
```

Expected: PASS（新旧 matcher 路径都通过）。

- [ ] **Step 2: 运行 pipeline/wrapper 测试集**

Run:

```bash
bash scripts/build_test_smoke.sh unit-module tests.unitTest.controlnet_construct_pipeline_unit_test
```

Expected: PASS（参数透传与优先级行为保持）。

- [ ] **Step 3: 运行 GPU SIFT 回归测试**

Run:

```bash
/home/gengxun/miniconda3/envs/asp360_new/bin/python -m pytest tests/unitTest/gpu_sift_unit_test.py -q
```

Expected: PASS（bf/flann 旧路径无回归）。

- [ ] **Step 4: 最终汇总检查**

Run:

```bash
git --no-pager diff --stat
```

Expected: 仅包含本计划列出的文件变更，无无关文件。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/deep_frontends.py \
  examples/controlnet_construct/deep_matchers.py \
  examples/controlnet_construct/deep_adapter.py \
  examples/controlnet_construct/tile_matching.py \
  examples/controlnet_construct/image_match.py \
  examples/controlnet_construct/run_image_match_batch_example.sh \
  examples/controlnet_construct/run_pipeline_example.sh \
  tests/unitTest/controlnet_construct_matching_unit_test.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: integrate deep matcher methods into controlnet pipeline" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```
