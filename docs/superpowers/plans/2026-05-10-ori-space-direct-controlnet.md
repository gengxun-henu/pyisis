# ORI Space Direct ControlNet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `examples/controlnet_construct` 中新增“原始影像空间直接匹配并构建 `.net`”单对闭环，支持 `sift/superpoint/superglue/loftr`，并保持现有 DOM 链路不回归。

**Architecture:** 复用现有 `tile_matching.py` 调度骨架与 `deep_adapter.py` 深度匹配分派，把“读窗来源”从 DOM 专用扩展为 DOM/ORI 后端可复用。`image_match.py` 新增 ORI 入口输出原始空间 `.key`，`controlnet_stereopair.py` 新增 `from-ori-match` 子命令串联匹配与构网。deep 依赖缺失时严格 fail-fast，不做跨算法回退。

**Tech Stack:** Python 3.12 (asp360_new), isis_pybind, OpenCV, optional Torch/Kornia/LightGlue/SuperGlue deps, unittest.

---

## File structure

- Modify: `examples/controlnet_construct/tile_matching.py`
  - 抽象窗口读取后端并复用现有 tile matching 执行器。
- Modify: `examples/controlnet_construct/image_match.py`
  - 新增 `match_ori_pair` / `match_ori_pair_to_key_files` 和 CLI 参数解析扩展。
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
  - 新增 `from-ori-match` 子命令及主流程串联。
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - ORI 匹配入口、superpoint 独立方法、依赖 fail-fast 回归。
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - `from-ori-match` 参数透传与 `.key -> .net` 闭环回归。

### Task 1: 建立 ORI 能力测试基线（先红）

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify in Task 3: `examples/controlnet_construct/image_match.py`
- Modify in Task 4: `examples/controlnet_construct/controlnet_stereopair.py`

- [ ] **Step 1: 写失败测试（ORI入口 + superpoint + fail-fast + 新CLI子命令）**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
def test_match_ori_pair_accepts_superpoint_method(self):
    with mock.patch.object(image_match, "_match_pair_generic", return_value=(KeypointFile(1, 1, ()), KeypointFile(1, 1, ()), {"status": "matched_no_points"})):
        _, _, summary = image_match.match_ori_pair("left.cub", "right.cub", matcher_method="superpoint")
    self.assertEqual(summary["matcher"]["matcher_method_requested"], "superpoint")

def test_match_ori_pair_deep_dependency_missing_fails_fast(self):
    with mock.patch("controlnet_construct.tile_matching._get_deep_matcher_adapter", side_effect=RuntimeError("missing torch")):
        with self.assertRaisesRegex(RuntimeError, "missing torch"):
            image_match.match_ori_pair("left.cub", "right.cub", matcher_method="superglue")
```

在 `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 增加：

```python
def test_controlnet_stereopair_from_ori_match_subcommand_routes_pipeline(self):
    parser = controlnet_stereopair.build_argument_parser()
    args = parser.parse_args(["from-ori-match", "left.cub", "right.cub", "cfg.json", "out.net"])
    self.assertEqual(args.command, "from-ori-match")
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_accepts_superpoint_method \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_deep_dependency_missing_fails_fast \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_from_ori_match_subcommand_routes_pipeline \
  -v
```

Expected: FAIL（`match_ori_pair` 或 `from-ori-match` 尚不存在）。

- [ ] **Step 3: 最小实现占位接口（仅让测试可达）**

在 `examples/controlnet_construct/image_match.py` 增加最小接口：

```python
def match_ori_pair(left_cube_path: str | Path, right_cube_path: str | Path, **kwargs):
    return _match_pair_generic(left_cube_path, right_cube_path, image_space="ori", **kwargs)
```

在 `examples/controlnet_construct/controlnet_stereopair.py` 增加子命令骨架：

```python
def _build_from_ori_match_parser(subparsers) -> None:
    parser = subparsers.add_parser("from-ori-match", help="Match original-image cubes and build ControlNet directly.")
    parser.add_argument("left_cube")
    parser.add_argument("right_cube")
    parser.add_argument("config")
    parser.add_argument("output_net")
```

- [ ] **Step 4: 复跑相同测试确认通过**

Run: 同 Step 2。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  tests/unitTest/controlnet_construct_matching_unit_test.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py \
  examples/controlnet_construct/image_match.py \
  examples/controlnet_construct/controlnet_stereopair.py
git commit -m "test: add ori matching and from-ori-match baseline tests" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: 在 tile_matching 抽象 DOM/ORI 读取后端（先红）

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: 写失败测试（后端抽象与坐标一致性）**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
def test_match_pair_generic_uses_ori_backend(self):
    backend = tile_matching.build_image_backend("ori")
    self.assertEqual(backend.space, "ori")

def test_match_pair_generic_uses_dom_backend(self):
    backend = tile_matching.build_image_backend("dom")
    self.assertEqual(backend.space, "dom")
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_pair_generic_uses_ori_backend \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_pair_generic_uses_dom_backend \
  -v
```

Expected: FAIL（`build_image_backend` 尚不存在）。

- [ ] **Step 3: 最小实现后端抽象**

在 `examples/controlnet_construct/tile_matching.py` 新增：

```python
@dataclass(frozen=True, slots=True)
class ImageSpaceBackend:
    space: str

def build_image_backend(image_space: str) -> ImageSpaceBackend:
    normalized = str(image_space).strip().lower()
    if normalized not in {"dom", "ori"}:
        raise ValueError(f"Unsupported image_space {image_space!r}.")
    return ImageSpaceBackend(space=normalized)
```

并把 `_build_tile_match_tasks` / `_run_serial_tile_match_tasks` / `_run_parallel_tile_match_tasks` 的入口参数增加 `image_space`（默认 `"dom"`），内部统一走同一套 matcher 分派。

- [ ] **Step 4: 复跑相同测试确认通过**

Run: 同 Step 2。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/tile_matching.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "refactor: add dom/ori image backend abstraction for tile matching" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: 实现 ORI 匹配入口与 `.key` 输出（先红）

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: 写失败测试（ORI入口输出结构）**

在 `tests/unitTest/controlnet_construct_matching_unit_test.py` 增加：

```python
def test_match_ori_pair_to_key_files_writes_ori_keys(self):
    with temporary_directory() as temp_dir:
        left_key = temp_dir / "left_ori.key"
        right_key = temp_dir / "right_ori.key"
        with mock.patch.object(image_match, "match_ori_pair", return_value=(KeypointFile(32, 32, ()), KeypointFile(32, 32, ()), {"status": "matched_no_points", "matcher": {"matcher_method_requested": "sift"}})):
            result = image_match.match_ori_pair_to_key_files("left.cub", "right.cub", left_key, right_key)
    self.assertEqual(result["left_output_key"], str(left_key))
    self.assertEqual(result["right_output_key"], str(right_key))
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_to_key_files_writes_ori_keys \
  -v
```

Expected: FAIL（`match_ori_pair_to_key_files` 尚不存在）。

- [ ] **Step 3: 最小实现 ORI 匹配 API**

在 `examples/controlnet_construct/image_match.py` 增加：

```python
def _match_pair_generic(left_path: str | Path, right_path: str | Path, *, image_space: str, **kwargs):
    # 复用现有 low-res + 分块 + matcher 调度，按 image_space 选择后端
    ...

def match_ori_pair(left_cube_path: str | Path, right_cube_path: str | Path, **kwargs):
    return _match_pair_generic(left_cube_path, right_cube_path, image_space="ori", **kwargs)

def match_ori_pair_to_key_files(left_cube_path: str | Path, right_cube_path: str | Path, left_output_key: str | Path, right_output_key: str | Path, **kwargs):
    left_key_file, right_key_file, summary = match_ori_pair(left_cube_path, right_cube_path, **kwargs)
    write_key_file(left_output_key, left_key_file)
    write_key_file(right_output_key, right_key_file)
    return {**summary, "left_output_key": str(left_output_key), "right_output_key": str(right_output_key)}
```

并将 `SUPPORTED_MATCHER_METHODS` 扩展为包含 `superpoint`，确保 `superpoint/superglue/loftr` 在 ORI 入口均可选。

- [ ] **Step 4: 复跑相同测试确认通过**

Run: 同 Step 2。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/image_match.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: add ori pair matching and key export APIs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: 新增 `from-ori-match` 子命令并接入构网（先红）

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`

- [ ] **Step 1: 写失败测试（CLI 到构网闭环）**

在 `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 增加：

```python
def test_from_ori_match_calls_image_match_then_build_controlnet(self):
    with mock.patch("controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files") as match_mock, \
         mock.patch("controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair") as net_mock:
        match_mock.return_value = {"left_output_key": "a.key", "right_output_key": "b.key", "status": "matched"}
        net_mock.return_value = {"point_count": 3, "measure_count": 6}
        controlnet_stereopair.main(["from-ori-match", "left.cub", "right.cub", "tests/data/cfg.json", "out.net"])
    match_mock.assert_called_once()
    net_mock.assert_called_once()
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_from_ori_match_calls_image_match_then_build_controlnet \
  -v
```

Expected: FAIL（主流程尚未实现 `from-ori-match` 分支）。

- [ ] **Step 3: 实现子命令与主流程分支**

在 `examples/controlnet_construct/controlnet_stereopair.py`：

```python
if __package__ in {None, ""}:
    from controlnet_construct.image_match import match_ori_pair_to_key_files
else:
    from .image_match import match_ori_pair_to_key_files
```

增加解析器构建与执行分支（示意）：

```python
def _build_from_ori_match_parser(subparsers) -> None:
    ...
    parser.add_argument("--matcher-method", default="sift")
    parser.add_argument("--left-output-key", default=None)
    parser.add_argument("--right-output-key", default=None)

elif args.command == "from-ori-match":
    config = _apply_cli_pair_id_override(read_controlnet_config(args.config), args.pair_id)
    match_result = match_ori_pair_to_key_files(...)
    controlnet_result = build_controlnet_for_stereo_pair(...)
    result = {"mode": "from-ori-match", "match": match_result, "controlnet": controlnet_result}
```

- [ ] **Step 4: 复跑相同测试确认通过**

Run: 同 Step 2。  
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/controlnet_stereopair.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: add from-ori-match command for direct controlnet build" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 5: 参数透传、回归与文档收尾

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/image_match.py`
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify (if needed): `examples/controlnet_construct/run_pipeline_example.sh`

- [ ] **Step 1: 写失败测试（参数透传与回归约束）**

增加断言：

```python
def test_from_ori_match_forwards_matcher_method_and_gpu_flags(self):
    parser = controlnet_stereopair.build_argument_parser()
    args = parser.parse_args(["from-ori-match", "l.cub", "r.cub", "cfg.json", "out.net", "--matcher-method", "loftr", "--use-gpu"])
    self.assertEqual(args.matcher_method, "loftr")
    self.assertTrue(args.use_gpu)
```

并补充“from-dom 命令保持可用”的回归断言。

- [ ] **Step 2: 跑失败测试确认红灯**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  -v
```

Expected: 至少新增断言失败。

- [ ] **Step 3: 实现参数透传与摘要字段对齐**

在 `from-ori-match` 分支将关键参数透传到 `match_ori_pair_to_key_files`：

```python
match_ori_pair_to_key_files(
    args.left_cube,
    args.right_cube,
    resolved_left_output_key,
    resolved_right_output_key,
    matcher_method=args.matcher_method,
    use_gpu=args.use_gpu,
    ...
)
```

并在 result JSON 中补齐：

```python
result = {
    "mode": "from-ori-match",
    "match": match_result,
    "controlnet": controlnet_result,
}
```

- [ ] **Step 4: 运行完整相关测试确认绿灯**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add \
  examples/controlnet_construct/image_match.py \
  examples/controlnet_construct/controlnet_stereopair.py \
  tests/unitTest/controlnet_construct_matching_unit_test.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: finalize ori direct matching controlnet pipeline" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Spec coverage checklist (self-review)

1. **ORI 直接匹配并构网单对闭环** → Task 3 + Task 4 覆盖。  
2. **支持 sift/superpoint/superglue/loftr** → Task 1 + Task 3 + Task 5 覆盖。  
3. **复用现有分块并行/GPU/摘要架构** → Task 2 + Task 3 覆盖。  
4. **deep 依赖缺失 fail-fast，无跨算法回退** → Task 1 + Task 3 覆盖。  
5. **DOM 链路不回归** → Task 5 回归项覆盖。

## Placeholder scan (self-review)

- 未使用 TBD/TODO/“implement later” 占位语。
- 每个任务均含具体文件、测试命令、实现代码片段与 commit 命令。

## Type/name consistency (self-review)

- 统一使用 `match_ori_pair` / `match_ori_pair_to_key_files` / `from-ori-match` 命名。
- `image_space` 取值统一为 `"dom"` / `"ori"`。
- `matcher_method` 在测试与实现计划中保持同名。
