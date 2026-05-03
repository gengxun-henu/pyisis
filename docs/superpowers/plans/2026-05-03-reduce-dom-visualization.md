# Reduce DOM Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic reduced/cropped DOM match visualization so large LRO NAC post-RANSAC previews avoid full-resolution OOM while exposing coherent config/CLI controls.

**Architecture:** Keep public visualization entry points in `match_visualization.py`, but add small option/diagnostic dataclasses and preview-source helpers there. Reuse `lowres_offset.create_low_resolution_dom(...)` for ISIS `reduce`, then wire options through `image_match.py`, `controlnet_stereopair.py`, and `run_pipeline_example.sh`; derive low-resolution matching level from target-long-edge only when no explicit level is supplied.

**Tech Stack:** Python 3.12, ISIS `reduce`, `isis_pybind` Cube/Brick I/O, OpenCV `drawMatches`, `argparse`, JSON config, `unittest`, Bash wrapper tests.

---

## File structure

- Modify `examples/controlnet_construct/match_visualization.py`
  - Owns visualization mode/profile validation, target-long-edge level derivation, reduced preview cache selection/generation, crop-window calculation, coordinate transforms, and visualization diagnostics.
- Modify `examples/controlnet_construct/image_match.py`
  - Adds ImageMatch config/default parsing and CLI/API forwarding for visualization options and low-resolution matching target-long-edge.
- Modify `examples/controlnet_construct/lowres_offset.py`
  - Adds pair-common level derivation helper from target-long-edge.
- Modify `examples/controlnet_construct/controlnet_stereopair.py`
  - Adds post-RANSAC visualization options to Python API, CLI, per-pair report metadata, and batch wrapper call path.
- Modify `examples/controlnet_construct/run_pipeline_example.sh`
  - Adds kebab-case forwarding for post-RANSAC visualization options and config-default fallback probes.
- Modify `examples/controlnet_construct/controlnet_config.example.json`
  - Adds safe default visualization fields.
- Modify `examples/controlnet_construct/usage.md`
  - Documents reduced/cropped visualization controls.
- Modify tests:
  - `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

## Task 1: Add preview option and level-derivation tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify in Task 2: `examples/controlnet_construct/match_visualization.py`
- Modify in Task 2: `examples/controlnet_construct/lowres_offset.py`

- [ ] **Step 1: Add imports for the visualization module**

In `tests/unitTest/controlnet_construct_matching_unit_test.py`, after the existing `image_match = importlib.import_module(...)` line, add:

```python
match_visualization_module = importlib.import_module("controlnet_construct.match_visualization")
lowres_offset_module = importlib.import_module("controlnet_construct.lowres_offset")
```

- [ ] **Step 2: Add failing tests for profile validation and level derivation**

Append these methods inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_visualization_memory_profile_resolves_target_long_edges(self):
        high = match_visualization_module.resolve_visualization_options(memory_profile="high-memory")
        balanced = match_visualization_module.resolve_visualization_options(memory_profile="balanced")
        low = match_visualization_module.resolve_visualization_options(memory_profile="low-memory")

        self.assertEqual(high.visualization_target_long_edge, 4096)
        self.assertEqual(balanced.visualization_target_long_edge, 2048)
        self.assertEqual(low.visualization_target_long_edge, 1024)
        self.assertEqual(balanced.visualization_mode, "auto")
        self.assertEqual(balanced.preview_cache_source, "auto")

    def test_visualization_option_validation_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "visualization_mode"):
            match_visualization_module.resolve_visualization_options(visualization_mode="huge")
        with self.assertRaisesRegex(ValueError, "memory_profile"):
            match_visualization_module.resolve_visualization_options(memory_profile="tiny")
        with self.assertRaisesRegex(ValueError, "visualization_target_long_edge must be positive"):
            match_visualization_module.resolve_visualization_options(visualization_target_long_edge=0)
        with self.assertRaisesRegex(ValueError, "preview_crop_margin_pixels must be >= 0"):
            match_visualization_module.resolve_visualization_options(preview_crop_margin_pixels=-1)

    def test_reduce_level_from_target_long_edge_uses_pair_common_longest_edge(self):
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 4096), 1)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 2048), 2)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(1000, 2048), 0)
        self.assertEqual(
            lowres_offset_module.reduce_level_for_pair_target_long_edge(
                left_width=2048,
                left_height=1024,
                right_width=16384,
                right_height=512,
                target_long_edge=2048,
            ),
            3,
        )
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_visualization_memory_profile_resolves_target_long_edges \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_visualization_option_validation_rejects_invalid_values \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_reduce_level_from_target_long_edge_uses_pair_common_longest_edge \
  -v
```

Expected: fail with `AttributeError` for missing helper functions.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: cover visualization option resolution" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 2: Implement option validation and target-long-edge helpers

**Files:**
- Modify: `examples/controlnet_construct/match_visualization.py`
- Modify: `examples/controlnet_construct/lowres_offset.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add constants and dataclass to `match_visualization.py`**

Add after the `isis_pybind` import:

```python
SUPPORTED_VISUALIZATION_MODES = ("auto", "full", "reduced", "cropped", "reduced_cropped")
SUPPORTED_MEMORY_PROFILES = ("high-memory", "balanced", "low-memory")
SUPPORTED_PREVIEW_CACHE_SOURCES = ("auto", "matching_cache", "visualization_cache", "disabled")
MEMORY_PROFILE_TARGET_LONG_EDGES = {
    "high-memory": 4096,
    "balanced": 2048,
    "low-memory": 1024,
}
DEFAULT_VISUALIZATION_MODE = "auto"
DEFAULT_MEMORY_PROFILE = "balanced"
DEFAULT_PREVIEW_CROP_MARGIN_PIXELS = 256
DEFAULT_PREVIEW_CACHE_SOURCE = "auto"


@dataclass(frozen=True, slots=True)
class VisualizationOptions:
    visualization_mode: str = DEFAULT_VISUALIZATION_MODE
    memory_profile: str = DEFAULT_MEMORY_PROFILE
    visualization_target_long_edge: int = MEMORY_PROFILE_TARGET_LONG_EDGES[DEFAULT_MEMORY_PROFILE]
    max_preview_pixels: int | None = None
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS
    preview_cache_dir: Path | None = None
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE
    preview_force_regenerate: bool = False
    preview_level: int | None = None
```

Also add `from dataclasses import dataclass` to imports.

- [ ] **Step 2: Add validation helpers to `match_visualization.py`**

Add:

```python
def _normalize_choice(value: str, *, field_name: str, supported: tuple[str, ...]) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in supported:
        raise ValueError(f"{field_name} must be one of {supported}; got {value!r}.")
    return normalized


def _positive_int(value: int, *, field_name: str) -> int:
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved


def _non_negative_int(value: int, *, field_name: str) -> int:
    resolved = int(value)
    if resolved < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    return resolved


def resolve_visualization_options(
    *,
    visualization_mode: str = DEFAULT_VISUALIZATION_MODE,
    memory_profile: str = DEFAULT_MEMORY_PROFILE,
    visualization_target_long_edge: int | None = None,
    max_preview_pixels: int | None = None,
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
    preview_cache_dir: str | Path | None = None,
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE,
    preview_force_regenerate: bool = False,
    preview_level: int | None = None,
) -> VisualizationOptions:
    resolved_profile = _normalize_choice(memory_profile, field_name="memory_profile", supported=SUPPORTED_MEMORY_PROFILES)
    resolved_mode = _normalize_choice(visualization_mode, field_name="visualization_mode", supported=SUPPORTED_VISUALIZATION_MODES)
    resolved_cache_source = _normalize_choice(preview_cache_source, field_name="preview_cache_source", supported=SUPPORTED_PREVIEW_CACHE_SOURCES)
    resolved_target = (
        _positive_int(visualization_target_long_edge, field_name="visualization_target_long_edge")
        if visualization_target_long_edge is not None
        else MEMORY_PROFILE_TARGET_LONG_EDGES[resolved_profile]
    )
    resolved_max_pixels = None if max_preview_pixels is None else _positive_int(max_preview_pixels, field_name="max_preview_pixels")
    resolved_preview_level = None if preview_level is None else _non_negative_int(preview_level, field_name="preview_level")
    return VisualizationOptions(
        visualization_mode=resolved_mode,
        memory_profile=resolved_profile,
        visualization_target_long_edge=resolved_target,
        max_preview_pixels=resolved_max_pixels,
        preview_crop_margin_pixels=_non_negative_int(preview_crop_margin_pixels, field_name="preview_crop_margin_pixels"),
        preview_cache_dir=None if preview_cache_dir is None else Path(preview_cache_dir),
        preview_cache_source=resolved_cache_source,
        preview_force_regenerate=bool(preview_force_regenerate),
        preview_level=resolved_preview_level,
    )
```

- [ ] **Step 3: Add level helpers to `lowres_offset.py`**

Add imports and helpers:

```python
import math


def reduce_level_for_target_long_edge(long_edge: int, target_long_edge: int) -> int:
    resolved_long_edge = int(long_edge)
    resolved_target = int(target_long_edge)
    if resolved_long_edge <= 0:
        raise ValueError("long_edge must be positive.")
    if resolved_target <= 0:
        raise ValueError("target_long_edge must be positive.")
    return max(0, int(math.ceil(math.log2(resolved_long_edge / resolved_target))))


def reduce_level_for_pair_target_long_edge(
    *,
    left_width: int,
    left_height: int,
    right_width: int,
    right_height: int,
    target_long_edge: int,
) -> int:
    pair_long_edge = max(int(left_width), int(left_height), int(right_width), int(right_height))
    return reduce_level_for_target_long_edge(pair_long_edge, target_long_edge)
```

- [ ] **Step 4: Run tests and verify they pass**

Run the Task 1 command again. Expected: all three tests pass.

- [ ] **Step 5: Commit implementation**

```bash
git add examples/controlnet_construct/match_visualization.py examples/controlnet_construct/lowres_offset.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: resolve visualization preview options" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 3: Add crop-window visualization tests and implementation

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/match_visualization.py`

- [ ] **Step 1: Add crop-window tests**

Append:

```python
    def test_visualization_crop_window_uses_keypoint_bounds_and_margin(self):
        points = (Keypoint(20.0, 30.0), Keypoint(80.0, 90.0))

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=120,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y, window.width, window.height), (9, 19, 81, 81))

    def test_visualization_crop_window_rejects_empty_points(self):
        with self.assertRaisesRegex(ValueError, "At least one keypoint"):
            match_visualization_module.crop_window_for_keypoints(
                (),
                image_width=100,
                image_height=100,
                margin_pixels=10,
            )
```

- [ ] **Step 2: Run crop tests and verify failure**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_visualization_crop_window_uses_keypoint_bounds_and_margin \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_visualization_crop_window_rejects_empty_points \
  -v
```

Expected: fail with missing `crop_window_for_keypoints`.

- [ ] **Step 3: Implement crop helper**

In `match_visualization.py`, import `TileWindow` from `.tiling` and add:

```python
def crop_window_for_keypoints(
    points: tuple[Keypoint, ...],
    *,
    image_width: int,
    image_height: int,
    margin_pixels: int,
) -> TileWindow:
    if not points:
        raise ValueError("At least one keypoint is required for cropped visualization.")
    resolved_width = _positive_int(image_width, field_name="image_width")
    resolved_height = _positive_int(image_height, field_name="image_height")
    margin = _non_negative_int(margin_pixels, field_name="preview_crop_margin_pixels")
    # TileWindow uses 0-based start plus exclusive end; convert keypoints before bounds.
    min_sample = min(point.sample - 1.0 for point in points)
    max_sample = max(point.sample - 1.0 for point in points)
    min_line = min(point.line - 1.0 for point in points)
    max_line = max(point.line - 1.0 for point in points)
    start_x = int(np.floor(min_sample)) - margin
    start_y = int(np.floor(min_line)) - margin
    end_x = int(np.ceil(max_sample)) + margin + 1
    end_y = int(np.ceil(max_line)) + margin + 1

    def clamp_window(start: int, end: int, limit: int) -> tuple[int, int]:
        if end <= 0:
            return 0, 1
        if start >= limit:
            return limit - 1, limit
        clamped_start = max(0, start)
        clamped_end = min(limit, end)
        if clamped_end <= clamped_start:
            clamped_end = min(limit, clamped_start + 1)
        return clamped_start, clamped_end

    start_x, end_x = clamp_window(start_x, end_x, resolved_width)
    start_y, end_y = clamp_window(start_y, end_y, resolved_height)
    return TileWindow(start_x=start_x, start_y=start_y, width=end_x - start_x, height=end_y - start_y)
```

- [ ] **Step 4: Run crop tests and commit**

Run the Task 3 command again. Expected: pass.

Commit:

```bash
git add examples/controlnet_construct/match_visualization.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: compute match visualization crop windows" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 4: Add automatic full vs cropped rendering tests and implementation

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/match_visualization.py`

- [ ] **Step 1: Add rendering-mode tests using mocked cube readers**

Append:

```python
    def test_write_match_visualization_auto_uses_cropped_mode_for_large_images(self):
        left_key_file = KeypointFile(4000, 3000, (Keypoint(100.0, 100.0), Keypoint(120.0, 120.0)))
        right_key_file = KeypointFile(4000, 3000, (Keypoint(105.0, 105.0), Keypoint(125.0, 125.0)))
        read_windows: list[tuple[int, int, int, int]] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append((window.start_x, window.start_y, window.width, window.height))
            return np.full((window.height, window.width), 128, dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4000, 3000),
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="auto",
                max_preview_pixels=10_000,
                preview_crop_margin_pixels=10,
            )

        self.assertEqual(result["visualization_mode_used"], "cropped")
        self.assertEqual(read_windows, [(89, 89, 42, 42), (94, 94, 42, 42)])

    def test_write_match_visualization_preserves_full_mode_for_small_images(self):
        left_key_file = KeypointFile(32, 32, (Keypoint(10.0, 10.0),))
        right_key_file = KeypointFile(32, 32, (Keypoint(11.0, 11.0),))
        read_windows: list[object | None] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((32, 32), 128, dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(32, 32),
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="auto",
                max_preview_pixels=4096,
            )

        self.assertEqual(result["visualization_mode_used"], "full")
        self.assertEqual(read_windows, [None, None])
```

- [ ] **Step 2: Run rendering-mode tests and verify failure**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_write_match_visualization_auto_uses_cropped_mode_for_large_images \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_write_match_visualization_preserves_full_mode_for_small_images \
  -v
```

Expected: fail because `write_stereo_pair_match_visualization` does not accept new options.

- [ ] **Step 3: Extend full-image reader for optional windows**

Change `_read_cube_as_stretched_byte(...)` signature to accept:

```python
    window: TileWindow | None = None,
```

Inside it, replace full-window assignment with:

```python
        read_window = window if window is not None else _full_image_window(cube.sample_count(), cube.line_count())
        values = _read_cube_window(cube, read_window, band=band)
```

- [ ] **Step 4: Add `_cube_dimensions` and mode selection**

Add:

```python
def _cube_dimensions(cube_path: str | Path) -> tuple[int, int]:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        return int(cube.sample_count()), int(cube.line_count())
    finally:
        if cube.is_open():
            cube.close()


def _auto_visualization_mode(
    *,
    image_width: int,
    image_height: int,
    options: VisualizationOptions,
    has_keypoints: bool,
) -> str:
    pixel_count = int(image_width) * int(image_height)
    if options.max_preview_pixels is not None and pixel_count > options.max_preview_pixels and has_keypoints:
        return "cropped"
    if max(image_width, image_height) > options.visualization_target_long_edge and has_keypoints:
        return "cropped"
    return "full"
```

- [ ] **Step 5: Wire cropped/full logic in `write_stereo_pair_match_visualization(...)`**

Add keyword parameters matching `resolve_visualization_options(...)`.

Before reading images:

```python
    options = resolve_visualization_options(...)
    left_width, left_height = _cube_dimensions(left_dom_path)
    right_width, right_height = _cube_dimensions(right_dom_path)
    mode_used = options.visualization_mode
    if mode_used == "auto":
        mode_used = _auto_visualization_mode(
            image_width=max(left_width, right_width),
            image_height=max(left_height, right_height),
            options=options,
            has_keypoints=bool(left_key_file.points),
        )
```

For `mode_used == "cropped"`, compute separate left/right crop windows and pass them to `_read_cube_as_stretched_byte(...)`; subtract crop start from keypoint draw coordinates by adding a helper:

```python
def _offset_keypoint_file(key_file: KeypointFile, *, start_x: int, start_y: int, width: int, height: int) -> KeypointFile:
    return KeypointFile(
        width,
        height,
        tuple(Keypoint(point.sample - start_x, point.line - start_y) for point in key_file.points),
    )
```

Return diagnostics:

```python
        "visualization_mode_requested": options.visualization_mode,
        "visualization_mode_used": mode_used,
        "memory_profile": options.memory_profile,
        "preview_level": options.preview_level,
        "preview_cache_hit": False,
        "preview_cache_source": "disabled" if mode_used in {"full", "cropped"} else options.preview_cache_source,
        "preview_dimensions": {"left": list(left_image.shape[::-1]), "right": list(right_image.shape[::-1])},
        "crop_window": None if mode_used == "full" else {"left": {...}, "right": {...}},
        "source_scale_factor": 1.0,
```

- [ ] **Step 6: Run rendering tests and commit**

Run the Task 4 command. Expected: pass.

Commit:

```bash
git add examples/controlnet_construct/match_visualization.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: auto-crop large match visualizations" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 5: Add reduced-preview cache tests and implementation

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/match_visualization.py`

- [ ] **Step 1: Add tests for reduced mode using mocked reduce helper**

Append:

```python
    def test_write_match_visualization_reduced_mode_generates_preview_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[tuple[str, str, int]] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append((str(source), str(output), level))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4096, 4096),
        ), mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            return_value=np.full((64, 64), 128, dtype=np.uint8),
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced",
                preview_cache_dir=temp_dir / "preview_cache",
                visualization_target_long_edge=1024,
            )

        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["preview_level"], 2)
        self.assertFalse(result["preview_cache_hit"])
        self.assertEqual(len(generated), 2)
```

- [ ] **Step 2: Run reduced test and verify failure**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_write_match_visualization_reduced_mode_generates_preview_cache \
  -v
```

Expected: fail because reduced mode is not implemented.

- [ ] **Step 3: Implement reduced cache helpers**

In `match_visualization.py`, import:

```python
from .lowres_offset import create_low_resolution_dom, reduce_level_for_pair_target_long_edge
```

Add:

```python
def _preview_cache_path(cache_dir: str | Path, source_path: str | Path, *, level: int) -> Path:
    return Path(cache_dir) / f"level{int(level)}" / f"{Path(source_path).stem}.cub"


def _ensure_preview_cube(
    source_path: str | Path,
    *,
    cache_dir: str | Path,
    level: int,
    force_regenerate: bool,
) -> tuple[Path, bool]:
    output_path = _preview_cache_path(cache_dir, source_path, level=level)
    if output_path.exists() and not force_regenerate:
        return output_path, True
    output = create_low_resolution_dom(source_path, output_path, level=level)
    return output, False
```

- [ ] **Step 4: Wire `reduced` and `reduced_cropped` modes**

When mode is `reduced` or `reduced_cropped`, compute:

```python
resolved_level = options.preview_level
if resolved_level is None:
    resolved_level = reduce_level_for_pair_target_long_edge(
        left_width=left_width,
        left_height=left_height,
        right_width=right_width,
        right_height=right_height,
        target_long_edge=options.visualization_target_long_edge,
    )
```

Use `options.preview_cache_dir or resolved_output_path.parent / "preview_cache"` as cache root, ensure left/right previews, read from preview cubes, and set `source_scale_factor = 1.0 / float(2 ** resolved_level)`.

For `reduced_cropped`, crop coordinates by multiplying original keypoints by `source_scale_factor` before computing crop windows.

- [ ] **Step 5: Run reduced test and commit**

Run the Task 5 command. Expected: pass.

Commit:

```bash
git add examples/controlnet_construct/match_visualization.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: render match visualizations from reduced previews" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 6: Wire visualization options through `image_match.py`

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add ImageMatch config and parser tests**

Add tests asserting `build_argument_parser()` accepts:

```text
--visualization-mode reduced
--memory-profile low-memory
--visualization-target-long-edge 1024
--max-preview-pixels 1000000
--preview-crop-margin-pixels 128
--preview-cache-dir work/preview_cache
--preview-cache-source visualization-cache
--preview-force-regenerate
--preview-level 3
--low-resolution-matching-target-long-edge 1024
```

Assert parsed destinations are snake_case and config JSON aliases are read by `load_image_match_defaults_from_config(...)`.

- [ ] **Step 2: Implement imports, config field specs, parser flags, and forwarding**

In `image_match.py`, import visualization constants/validation via `resolve_visualization_options`. Add field specs for every visualization option and low-resolution matching target. Add CLI flags with kebab-case names. Forward values to `write_stereo_pair_match_visualization(...)`.

- [ ] **Step 3: Derive low-resolution level when not explicit**

In `match_dom_pair(...)`, add parameter:

```python
low_resolution_matching_target_long_edge: int | None = None
```

When low-resolution offset estimation is enabled and no explicit `low_resolution_level` override is intended by CLI/config, derive the level using `reduce_level_for_pair_target_long_edge(...)`. Persist `low_resolution_matching_target_long_edge` and `resolved_low_resolution_level` in summary.

- [ ] **Step 4: Run focused tests and commit**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Commit:

```bash
git add examples/controlnet_construct/image_match.py examples/controlnet_construct/lowres_offset.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: expose visualization preview options in image match" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 7: Wire post-RANSAC visualization options through `controlnet_stereopair.py`

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`

- [ ] **Step 1: Add report-forwarding test**

Add a test that patches `write_stereo_pair_match_visualization_from_key_files`, calls `build_controlnet_for_dom_stereo_pair(...)` with `write_match_visualization=True` and new preview options, and asserts the mock receives those options and the returned result includes the visualization diagnostics.

- [ ] **Step 2: Implement API parameters and metadata**

Add keyword parameters to `build_controlnet_for_dom_stereo_pair(...)` and batch builder for each visualization option. Forward them into `write_stereo_pair_match_visualization_from_key_files(...)`. Include returned diagnostics under the existing report key.

- [ ] **Step 3: Add CLI parser flags**

In `controlnet_stereopair.py from-dom` and `from-dom-batch` parsers, add kebab-case flags matching the design. Forward parsed args into builder functions.

- [ ] **Step 4: Run pipeline unit tests and commit**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Commit:

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: expose reduced post-ransac visualizations" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 8: Wire wrapper config/default forwarding

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`

- [ ] **Step 1: Add wrapper forwarding test**

Extend the fake dispatcher in a pipeline wrapper test so `image_match.py --print-config-default` returns visualization fields. Assert the `controlnet_stereopair.py from-dom-batch` command includes:

```text
--visualization-mode auto
--memory-profile low-memory
--visualization-target-long-edge 1024
--preview-crop-margin-pixels 128
--preview-cache-source auto
```

- [ ] **Step 2: Implement wrapper variables and config probes**

In `run_pipeline_example.sh`, add variables, usage text, CLI parsing, config fallback probes, and forwarding into the from-dom-batch command.

- [ ] **Step 3: Run wrapper tests and commit**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Commit:

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: forward visualization preview options in pipeline wrapper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 9: Update docs and example config

**Files:**
- Modify: `examples/controlnet_construct/controlnet_config.example.json`
- Modify: `examples/controlnet_construct/controlnet_config.low_memory_lro.json`
- Modify: `examples/controlnet_construct/usage.md`

- [ ] **Step 1: Add example JSON fields**

Add fields under `ImageMatch`:

```json
"visualization_mode": "auto",
"memory_profile": "balanced",
"visualization_target_long_edge": 2048,
"low_resolution_matching_target_long_edge": 2048,
"preview_crop_margin_pixels": 256,
"preview_cache_source": "auto"
```

Use `"memory_profile": "low-memory"` and target `1024` in `controlnet_config.low_memory_lro.json`.

- [ ] **Step 2: Document CLI/config behavior**

In `usage.md`, add a short section explaining auto/reduced/cropped visualization and the target-long-edge/profile priority rules.

- [ ] **Step 3: Commit docs**

```bash
git add examples/controlnet_construct/controlnet_config.example.json examples/controlnet_construct/controlnet_config.low_memory_lro.json examples/controlnet_construct/usage.md
git commit -m "docs: document reduced DOM visualization options" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 10: Final focused verification

**Files:**
- No planned code changes.

- [ ] **Step 1: Run focused regression suite**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  -v
```

Expected: all tests pass.

- [ ] **Step 2: Run a smoke visualization command**

Run a small fixture smoke with `write_stereo_pair_match_visualization_from_key_files(...)`, `visualization_mode="auto"`, and a low `max_preview_pixels` so cropped mode is selected. Expected: PNG exists and result reports `visualization_mode_used == "cropped"`.

- [ ] **Step 3: Inspect final diff and status**

Run:

```bash
git --no-pager status --short
git --no-pager diff --stat origin/feat/optimize-image-match-20260502..HEAD
```

Expected: only intentional commits and no uncommitted tracked changes.
