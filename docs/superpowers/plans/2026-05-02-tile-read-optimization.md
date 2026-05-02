# Tile Read Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly enabled DOM tile-read optimization that uses a reusable validity index to skip obviously invalid full-resolution tiles and reuses open cubes inside parallel worker batches.

**Architecture:** Add a focused `tile_validity.py` module for cache signatures, index construction, and conservative window filtering. Wire it into `image_match.py` after `_paired_windows(...)` and before tile execution, then replace the process-pool implementation in `tile_matching.py` with batched worker shards that open cubes once per shard.

**Tech Stack:** Python 3.12, `argparse`, JSON, NumPy `.npz`, ISIS `isis_pybind` Cube/Brick I/O, OpenCV SIFT, `unittest`, Bash wrappers, existing `asp360_new` conda environment.

---

## File structure

- Create `examples/controlnet_construct/tile_validity.py`
  - Owns `TileValidityIndex`, cache diagnostics, JSON/NPZ cache roundtrip, cell-size validation, cube scanning, and conservative `PairedTileWindow` filtering.
  - Does not call SIFT and does not know about key files or match visualization.
- Modify `examples/controlnet_construct/image_match.py`
  - Import tile-validity helpers.
  - Add API parameters, config fields, CLI flags, metadata fields, and default cache directory inference.
  - Insert prefiltering after `_paired_windows(...)`.
- Modify `examples/controlnet_construct/tile_matching.py`
  - Keep the public `_run_parallel_tile_match_tasks(...)` helper name.
  - Change its internals from one future per tile to one future per worker shard.
- Create `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`
  - Focused tests for cache signatures, conservative cell coverage, real cube scanning, and cache reuse.
- Modify `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Tests for API/CLI/config defaults, prefilter summary fields, and parallel backend diagnostics.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Only update fake config-default dispatchers if new config fields are asserted through wrapper tests.
- No C++ or pybind binding changes are required.

## Task 1: Add pure tile-validity tests

**Files:**
- Create: `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`
- Create in Task 2: `examples/controlnet_construct/tile_validity.py`

- [ ] **Step 1: Create the failing pure-helper test file**

Create `tests/unitTest/controlnet_construct_tile_validity_unit_test.py` with this content:

```python
"""Focused unit tests for DOM tile-validity cache and prefilter helpers.

Author: Geng Xun
Created: 2026-05-02
Last Modified: 2026-05-02
Updated: 2026-05-02  Geng Xun added regression coverage for conservative tile-validity prefilter decisions.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest

import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

tile_validity = importlib.import_module("controlnet_construct.tile_validity")
tiling = importlib.import_module("controlnet_construct.tiling")
tile_matching = importlib.import_module("controlnet_construct.tile_matching")


TileWindow = tiling.TileWindow
PairedTileWindow = tile_matching.PairedTileWindow


class ControlNetConstructTileValidityUnitTest(unittest.TestCase):
    def test_validate_tile_validity_cell_size_rejects_non_positive_values(self):
        self.assertEqual(tile_validity.validate_tile_validity_cell_size(32, field_name="tile_validity_cell_width"), 32)
        with self.assertRaisesRegex(ValueError, "tile_validity_cell_width must be positive"):
            tile_validity.validate_tile_validity_cell_size(0, field_name="tile_validity_cell_width")
        with self.assertRaisesRegex(ValueError, "tile_validity_cell_height must be positive"):
            tile_validity.validate_tile_validity_cell_size(-1, field_name="tile_validity_cell_height")

    def test_window_upper_bound_uses_covered_cell_valid_counts(self):
        index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[32, 0]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )

        upper_bound = tile_validity.window_valid_upper_bound(
            index,
            TileWindow(start_x=0, start_y=0, width=64, height=32),
        )

        self.assertEqual(upper_bound.valid_pixel_upper_bound, 32)
        self.assertEqual(upper_bound.window_pixel_count, 2048)
        self.assertAlmostEqual(upper_bound.valid_ratio_upper_bound, 32.0 / 2048.0)
        self.assertFalse(upper_bound.has_uncertain_cells)

    def test_prefilter_skips_only_when_upper_bound_cannot_meet_threshold(self):
        left_index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[16, 0]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        right_index = tile_validity.TileValidityIndex(
            dom_path="right.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[2048, 2048]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        windows = [
            PairedTileWindow(
                local_window=TileWindow(0, 0, 64, 32),
                left_window=TileWindow(0, 0, 64, 32),
                right_window=TileWindow(0, 0, 64, 32),
            )
        ]

        result = tile_validity.prefilter_paired_windows_by_validity(
            windows,
            left_index=left_index,
            right_index=right_index,
            valid_pixel_percent_threshold=0.05,
        )

        self.assertEqual(result.kept_windows, [])
        self.assertEqual(result.skipped_windows, windows)
        self.assertEqual(result.preindexed_skipped_tile_count, 1)
        self.assertEqual(result.skip_reasons["left_valid_upper_bound_below_threshold"], 1)

    def test_prefilter_keeps_threshold_zero_and_uncertain_cells(self):
        index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=32,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=1,
            grid_height=1,
            valid_counts=np.array([[0]], dtype=np.int64),
            total_counts=np.array([[1024]], dtype=np.int64),
            uncertain=np.array([[True]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        window = PairedTileWindow(
            local_window=TileWindow(0, 0, 32, 32),
            left_window=TileWindow(0, 0, 32, 32),
            right_window=TileWindow(0, 0, 32, 32),
        )

        zero_threshold_result = tile_validity.prefilter_paired_windows_by_validity(
            [window],
            left_index=index,
            right_index=index,
            valid_pixel_percent_threshold=0.0,
        )
        uncertain_result = tile_validity.prefilter_paired_windows_by_validity(
            [window],
            left_index=index,
            right_index=index,
            valid_pixel_percent_threshold=0.2,
        )

        self.assertEqual(zero_threshold_result.kept_windows, [window])
        self.assertEqual(zero_threshold_result.preindexed_skipped_tile_count, 0)
        self.assertEqual(uncertain_result.kept_windows, [window])
        self.assertEqual(uncertain_result.preindexed_skipped_tile_count, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_tile_validity_unit_test -v
```

Expected: fail with `ModuleNotFoundError: No module named 'controlnet_construct.tile_validity'`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/unitTest/controlnet_construct_tile_validity_unit_test.py
git commit -m "test: cover tile validity prefilter helpers" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 2: Implement pure tile-validity helpers

**Files:**
- Create: `examples/controlnet_construct/tile_validity.py`
- Test: `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`

- [ ] **Step 1: Create `tile_validity.py` with dataclasses and pure prefilter logic**

Create `examples/controlnet_construct/tile_validity.py` with this initial implementation:

```python
"""DOM tile-validity cache helpers for full-resolution matching prefilters.

Author: Geng Xun
Created: 2026-05-02
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .tiling import TileWindow
from .tile_matching import PairedTileWindow


CACHE_FORMAT_VERSION = 1
DEFAULT_TILE_VALIDITY_CELL_WIDTH = 1024
DEFAULT_TILE_VALIDITY_CELL_HEIGHT = 1024


@dataclass(frozen=True, slots=True)
class TileValidityIndex:
    dom_path: str
    image_width: int
    image_height: int
    cell_width: int
    cell_height: int
    grid_width: int
    grid_height: int
    valid_counts: np.ndarray
    total_counts: np.ndarray
    uncertain: np.ndarray
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TileValidityUpperBound:
    valid_pixel_upper_bound: int
    window_pixel_count: int
    valid_ratio_upper_bound: float
    has_uncertain_cells: bool


@dataclass(frozen=True, slots=True)
class TileValidityPrefilterResult:
    kept_windows: list[PairedTileWindow]
    skipped_windows: list[PairedTileWindow]
    preindexed_skipped_tile_count: int
    skip_reasons: dict[str, int]


def validate_tile_validity_cell_size(value: int, *, field_name: str) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved_value


def _covered_cell_range(start: int, length: int, cell_size: int, grid_size: int) -> range:
    if length <= 0:
        return range(0)
    first = max(0, start // cell_size)
    last = min(grid_size - 1, (start + length - 1) // cell_size)
    if first > last:
        return range(0)
    return range(first, last + 1)


def window_valid_upper_bound(index: TileValidityIndex, window: TileWindow) -> TileValidityUpperBound:
    x_cells = _covered_cell_range(window.start_x, window.width, index.cell_width, index.grid_width)
    y_cells = _covered_cell_range(window.start_y, window.height, index.cell_height, index.grid_height)
    valid_upper_bound = 0
    has_uncertain_cells = False
    for cell_y in y_cells:
        for cell_x in x_cells:
            valid_upper_bound += int(index.valid_counts[cell_y, cell_x])
            has_uncertain_cells = has_uncertain_cells or bool(index.uncertain[cell_y, cell_x])
    window_pixel_count = int(window.width * window.height)
    valid_ratio_upper_bound = 0.0 if window_pixel_count <= 0 else float(valid_upper_bound) / float(window_pixel_count)
    return TileValidityUpperBound(
        valid_pixel_upper_bound=valid_upper_bound,
        window_pixel_count=window_pixel_count,
        valid_ratio_upper_bound=valid_ratio_upper_bound,
        has_uncertain_cells=has_uncertain_cells,
    )


def _side_skip_reason(
    upper_bound: TileValidityUpperBound,
    *,
    side_name: str,
    valid_pixel_percent_threshold: float,
) -> str | None:
    if upper_bound.has_uncertain_cells:
        return None
    if valid_pixel_percent_threshold > 0.0 and upper_bound.valid_ratio_upper_bound < valid_pixel_percent_threshold:
        return f"{side_name}_valid_upper_bound_below_threshold"
    return None


def prefilter_paired_windows_by_validity(
    windows: list[PairedTileWindow],
    *,
    left_index: TileValidityIndex,
    right_index: TileValidityIndex,
    valid_pixel_percent_threshold: float,
) -> TileValidityPrefilterResult:
    if valid_pixel_percent_threshold <= 0.0:
        return TileValidityPrefilterResult(
            kept_windows=list(windows),
            skipped_windows=[],
            preindexed_skipped_tile_count=0,
            skip_reasons={},
        )

    kept_windows: list[PairedTileWindow] = []
    skipped_windows: list[PairedTileWindow] = []
    skip_reasons: dict[str, int] = {}
    for paired_window in windows:
        left_upper_bound = window_valid_upper_bound(left_index, paired_window.left_window)
        right_upper_bound = window_valid_upper_bound(right_index, paired_window.right_window)
        reason = _side_skip_reason(
            left_upper_bound,
            side_name="left",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        ) or _side_skip_reason(
            right_upper_bound,
            side_name="right",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        )
        if reason is None:
            kept_windows.append(paired_window)
            continue
        skipped_windows.append(paired_window)
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    return TileValidityPrefilterResult(
        kept_windows=kept_windows,
        skipped_windows=skipped_windows,
        preindexed_skipped_tile_count=len(skipped_windows),
        skip_reasons=skip_reasons,
    )


def default_tile_validity_cache_dir(
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    if metadata_output is not None:
        return Path(metadata_output).parent.parent / "tile_validity_cache"
    if left_output_key is not None:
        return Path(left_output_key).parent.parent / "tile_validity_cache"
    return Path.cwd() / "tile_validity_cache"
```

- [ ] **Step 2: Run pure helper tests and verify they pass**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_tile_validity_unit_test -v
```

Expected: pass all tests in `ControlNetConstructTileValidityUnitTest`.

- [ ] **Step 3: Commit pure helper implementation**

```bash
git add examples/controlnet_construct/tile_validity.py tests/unitTest/controlnet_construct_tile_validity_unit_test.py
git commit -m "feat: add conservative tile validity prefilter helpers" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 3: Add validity-index cache roundtrip tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`
- Modify in Task 4: `examples/controlnet_construct/tile_validity.py`

- [ ] **Step 1: Add cube-writing imports and helper**

Add these imports near the top of `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`:

```python
import json

from _unit_test_support import ip, make_test_cube, temporary_directory
```

Add this helper before the test class:

```python
def _write_array_to_cube(cube: ip.Cube, values: np.ndarray) -> None:
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(values[line_index, index])
        cube.write(manager)
        manager.next()
```

- [ ] **Step 2: Add cache roundtrip tests**

Append these methods inside `ControlNetConstructTileValidityUnitTest`:

```python
    def test_ensure_dom_validity_index_rebuilds_then_hits_cache(self):
        values = np.ones((16, 32), dtype=np.float64)
        values[:, 16:32] = 0.0

        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(
                temp_dir,
                name="validity_source.cub",
                samples=32,
                lines=16,
                bands=1,
                pixel_type=ip.PixelType.Real,
            )
            try:
                _write_array_to_cube(cube, values)
                cache_dir = temp_dir / "tile_validity_cache"

                first_index, first_diagnostics = tile_validity.ensure_dom_validity_index(
                    cache_dir=cache_dir,
                    dom_path=cube_path,
                    cube=cube,
                    band=1,
                    invalid_values=(0.0,),
                    special_pixel_abs_threshold=1.0e300,
                    invalid_pixel_radius=0,
                    cell_width=16,
                    cell_height=16,
                )
                second_index, second_diagnostics = tile_validity.ensure_dom_validity_index(
                    cache_dir=cache_dir,
                    dom_path=cube_path,
                    cube=cube,
                    band=1,
                    invalid_values=(0.0,),
                    special_pixel_abs_threshold=1.0e300,
                    invalid_pixel_radius=0,
                    cell_width=16,
                    cell_height=16,
                )
            finally:
                cube.close()

        self.assertEqual(first_diagnostics["status"], "rebuilt")
        self.assertEqual(second_diagnostics["status"], "hit")
        self.assertEqual(first_index.grid_width, 2)
        self.assertEqual(first_index.grid_height, 1)
        self.assertEqual(first_index.valid_counts.tolist(), [[256, 0]])
        self.assertEqual(second_index.valid_counts.tolist(), [[256, 0]])
        self.assertTrue(Path(first_diagnostics["manifest_path"]).exists())
        self.assertTrue(Path(first_diagnostics["data_path"]).exists())

    def test_ensure_dom_validity_index_rebuilds_when_parameters_change(self):
        values = np.ones((8, 8), dtype=np.float64)

        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(
                temp_dir,
                name="validity_parameter_change.cub",
                samples=8,
                lines=8,
                bands=1,
                pixel_type=ip.PixelType.Real,
            )
            try:
                _write_array_to_cube(cube, values)
                cache_dir = temp_dir / "tile_validity_cache"
                _, first_diagnostics = tile_validity.ensure_dom_validity_index(
                    cache_dir=cache_dir,
                    dom_path=cube_path,
                    cube=cube,
                    band=1,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    invalid_pixel_radius=0,
                    cell_width=8,
                    cell_height=8,
                )
                _, second_diagnostics = tile_validity.ensure_dom_validity_index(
                    cache_dir=cache_dir,
                    dom_path=cube_path,
                    cube=cube,
                    band=1,
                    invalid_values=(0.0,),
                    special_pixel_abs_threshold=1.0e300,
                    invalid_pixel_radius=0,
                    cell_width=8,
                    cell_height=8,
                )
            finally:
                cube.close()

        self.assertEqual(first_diagnostics["status"], "rebuilt")
        self.assertEqual(second_diagnostics["status"], "rebuilt")
        self.assertNotEqual(first_diagnostics["cache_key"], second_diagnostics["cache_key"])
```

- [ ] **Step 3: Run the new cache tests and verify they fail**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_tile_validity_unit_test.ControlNetConstructTileValidityUnitTest.test_ensure_dom_validity_index_rebuilds_then_hits_cache \
  tests.unitTest.controlnet_construct_tile_validity_unit_test.ControlNetConstructTileValidityUnitTest.test_ensure_dom_validity_index_rebuilds_when_parameters_change \
  -v
```

Expected: fail with `AttributeError` because `ensure_dom_validity_index` does not exist yet.

- [ ] **Step 4: Commit the failing cache tests**

```bash
git add tests/unitTest/controlnet_construct_tile_validity_unit_test.py
git commit -m "test: cover tile validity cache roundtrip" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 4: Implement validity-index cache building and loading

**Files:**
- Modify: `examples/controlnet_construct/tile_validity.py`
- Test: `tests/unitTest/controlnet_construct_tile_validity_unit_test.py`

- [ ] **Step 1: Add cache and cube-scan imports**

Update imports in `examples/controlnet_construct/tile_validity.py`:

```python
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .preprocess import expand_invalid_mask_for_radius, summarize_valid_pixels
from .runtime import bootstrap_runtime_environment
from .tiling import TileWindow
from .tile_matching import PairedTileWindow, _read_cube_window


bootstrap_runtime_environment()

import isis_pybind as ip
```

- [ ] **Step 2: Add manifest and cache path helpers**

Insert these helpers after `validate_tile_validity_cell_size(...)`:

```python
def _dom_file_fingerprint(dom_path: str | Path) -> dict[str, object]:
    resolved_path = Path(dom_path)
    stat = resolved_path.stat()
    return {
        "path": str(resolved_path.resolve()),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _index_manifest(
    *,
    dom_path: str | Path,
    image_width: int,
    image_height: int,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
) -> dict[str, object]:
    grid_width = int(math.ceil(image_width / cell_width))
    grid_height = int(math.ceil(image_height / cell_height))
    return {
        "format_version": CACHE_FORMAT_VERSION,
        "dom": _dom_file_fingerprint(dom_path),
        "image_width": int(image_width),
        "image_height": int(image_height),
        "band": int(band),
        "invalid_values": [float(value) for value in invalid_values],
        "special_pixel_abs_threshold": float(special_pixel_abs_threshold),
        "invalid_pixel_radius": int(invalid_pixel_radius),
        "cell_width": int(cell_width),
        "cell_height": int(cell_height),
        "grid_width": grid_width,
        "grid_height": grid_height,
    }


def _cache_key_for_manifest(manifest: dict[str, object]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_paths(cache_dir: str | Path, cache_key: str) -> tuple[Path, Path]:
    resolved_cache_dir = Path(cache_dir)
    return resolved_cache_dir / f"{cache_key}.json", resolved_cache_dir / f"{cache_key}.npz"
```

- [ ] **Step 3: Add index load, save, and build helpers**

Insert this code before `default_tile_validity_cache_dir(...)`:

```python
def _load_index_from_cache(manifest_path: Path, data_path: Path) -> TileValidityIndex:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with np.load(data_path) as payload:
        valid_counts = np.asarray(payload["valid_counts"], dtype=np.int64)
        total_counts = np.asarray(payload["total_counts"], dtype=np.int64)
        uncertain = np.asarray(payload["uncertain"], dtype=bool)
    return TileValidityIndex(
        dom_path=str(manifest["dom"]["path"]),
        image_width=int(manifest["image_width"]),
        image_height=int(manifest["image_height"]),
        cell_width=int(manifest["cell_width"]),
        cell_height=int(manifest["cell_height"]),
        grid_width=int(manifest["grid_width"]),
        grid_height=int(manifest["grid_height"]),
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest=manifest,
    )


def _save_index_to_cache(index: TileValidityIndex, manifest_path: Path, data_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(index.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    np.savez_compressed(
        data_path,
        valid_counts=index.valid_counts,
        total_counts=index.total_counts,
        uncertain=index.uncertain,
    )


def _cell_window_with_halo(
    *,
    image_width: int,
    image_height: int,
    cell_x: int,
    cell_y: int,
    cell_width: int,
    cell_height: int,
    invalid_pixel_radius: int,
) -> tuple[TileWindow, tuple[slice, slice], int, int]:
    cell_start_x = cell_x * cell_width
    cell_start_y = cell_y * cell_height
    actual_width = min(cell_width, image_width - cell_start_x)
    actual_height = min(cell_height, image_height - cell_start_y)
    halo = max(0, int(invalid_pixel_radius))
    read_start_x = max(0, cell_start_x - halo)
    read_start_y = max(0, cell_start_y - halo)
    read_end_x = min(image_width, cell_start_x + actual_width + halo)
    read_end_y = min(image_height, cell_start_y + actual_height + halo)
    inner_y = slice(cell_start_y - read_start_y, cell_start_y - read_start_y + actual_height)
    inner_x = slice(cell_start_x - read_start_x, cell_start_x - read_start_x + actual_width)
    return (
        TileWindow(read_start_x, read_start_y, read_end_x - read_start_x, read_end_y - read_start_y),
        (inner_y, inner_x),
        actual_width,
        actual_height,
    )


def _build_index_from_open_cube(
    *,
    dom_path: str | Path,
    cube: ip.Cube,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
    manifest: dict[str, object],
) -> TileValidityIndex:
    image_width = int(manifest["image_width"])
    image_height = int(manifest["image_height"])
    grid_width = int(manifest["grid_width"])
    grid_height = int(manifest["grid_height"])
    valid_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    total_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    uncertain = np.zeros((grid_height, grid_width), dtype=bool)

    for cell_y in range(grid_height):
        for cell_x in range(grid_width):
            read_window, inner_slices, actual_width, actual_height = _cell_window_with_halo(
                image_width=image_width,
                image_height=image_height,
                cell_x=cell_x,
                cell_y=cell_y,
                cell_width=cell_width,
                cell_height=cell_height,
                invalid_pixel_radius=invalid_pixel_radius,
            )
            values = _read_cube_window(cube, read_window, band=band)
            invalid_mask, _ = summarize_valid_pixels(
                values,
                invalid_values=invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
            )
            expanded_mask = expand_invalid_mask_for_radius(
                invalid_mask,
                invalid_pixel_radius=invalid_pixel_radius,
            )
            inner_mask = expanded_mask[inner_slices]
            total = int(actual_width * actual_height)
            invalid_count = int(inner_mask.sum())
            valid_counts[cell_y, cell_x] = total - invalid_count
            total_counts[cell_y, cell_x] = total

    return TileValidityIndex(
        dom_path=str(Path(dom_path)),
        image_width=image_width,
        image_height=image_height,
        cell_width=cell_width,
        cell_height=cell_height,
        grid_width=grid_width,
        grid_height=grid_height,
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest=manifest,
    )


def ensure_dom_validity_index(
    *,
    cache_dir: str | Path,
    dom_path: str | Path,
    cube: ip.Cube,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
) -> tuple[TileValidityIndex, dict[str, object]]:
    resolved_cell_width = validate_tile_validity_cell_size(cell_width, field_name="tile_validity_cell_width")
    resolved_cell_height = validate_tile_validity_cell_size(cell_height, field_name="tile_validity_cell_height")
    manifest = _index_manifest(
        dom_path=dom_path,
        image_width=int(cube.sample_count()),
        image_height=int(cube.line_count()),
        band=band,
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_pixel_radius=invalid_pixel_radius,
        cell_width=resolved_cell_width,
        cell_height=resolved_cell_height,
    )
    cache_key = _cache_key_for_manifest(manifest)
    manifest_path, data_path = _cache_paths(cache_dir, cache_key)
    diagnostics = {
        "cache_key": cache_key,
        "manifest_path": str(manifest_path),
        "data_path": str(data_path),
        "cell_width": resolved_cell_width,
        "cell_height": resolved_cell_height,
    }
    if manifest_path.exists() and data_path.exists():
        return _load_index_from_cache(manifest_path, data_path), {**diagnostics, "status": "hit"}

    index = _build_index_from_open_cube(
        dom_path=dom_path,
        cube=cube,
        band=band,
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_pixel_radius=invalid_pixel_radius,
        cell_width=resolved_cell_width,
        cell_height=resolved_cell_height,
        manifest=manifest,
    )
    _save_index_to_cache(index, manifest_path, data_path)
    return index, {**diagnostics, "status": "rebuilt"}
```

- [ ] **Step 4: Run tile-validity tests and verify they pass**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_tile_validity_unit_test -v
```

Expected: all pure and cache tests pass.

- [ ] **Step 5: Commit cache implementation**

```bash
git add examples/controlnet_construct/tile_validity.py tests/unitTest/controlnet_construct_tile_validity_unit_test.py
git commit -m "feat: cache DOM tile validity indexes" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 5: Add image-match integration tests for prefilter config and summary

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify in Task 6: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add API, parser, and config tests**

Append these methods inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_build_argument_parser_accepts_tile_validity_prefilter_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--enable-tile-validity-prefilter",
                "--tile-validity-cache-dir",
                "work/tile_validity_cache",
                "--tile-validity-cell-width",
                "512",
                "--tile-validity-cell-height",
                "256",
            ]
        )

        self.assertTrue(args.enable_tile_validity_prefilter)
        self.assertEqual(args.tile_validity_cache_dir, "work/tile_validity_cache")
        self.assertEqual(args.tile_validity_cell_width, 512)
        self.assertEqual(args.tile_validity_cell_height, 256)

    def test_load_image_match_defaults_from_config_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableTileValidityPrefilter": True,
                            "tileValidityCacheDir": "work/tile_validity_cache",
                            "tileValidityCellWidth": 512,
                            "tileValidityCellHeight": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertTrue(defaults["enable_tile_validity_prefilter"])
        self.assertEqual(defaults["tile_validity_cache_dir"], "work/tile_validity_cache")
        self.assertEqual(defaults["tile_validity_cell_width"], 512)
        self.assertEqual(defaults["tile_validity_cell_height"], 256)

    def test_print_image_match_config_default_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enable_tile_validity_prefilter": True,
                            "tile_validity_cell_width": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )

            enabled = image_match.print_image_match_config_default(config_path, "enable_tile_validity_prefilter")
            cell_width = image_match.print_image_match_config_default(config_path, "tile_validity_cell_width")

        self.assertEqual(enabled, "1")
        self.assertEqual(cell_width, "256")
```

- [ ] **Step 2: Add prefilter summary integration tests**

Append these methods inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_match_dom_pair_prefilters_invalid_tiles_and_reports_summary(self):
        values = np.ones((32, 64), dtype=np.float64) * 100.0
        values[:, 32:64] = 0.0

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter.cub",
                right_name="right_prefilter.cub",
            )
            cache_dir = temp_dir / "tile_validity_cache"
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cache_dir=cache_dir,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

        self.assertTrue(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count"], 2)
        self.assertEqual(summary["tile_count_before_preindex_filter"], 2)
        self.assertEqual(summary["tile_count_after_preindex_filter"], 1)
        self.assertEqual(summary["preindexed_skipped_tile_count"], 1)
        self.assertEqual(summary["tile_validity_cache_dir"], str(cache_dir))
        self.assertEqual(summary["full_resolution_skipped_tile_count"], summary["skipped_tile_count"] - 1)
        self.assertIn(summary["left_tile_validity_index"]["status"], {"rebuilt", "hit"})
        self.assertIn(summary["right_tile_validity_index"]["status"], {"rebuilt", "hit"})

    def test_match_dom_pair_keeps_prefilter_disabled_by_default(self):
        values = np.ones((32, 64), dtype=np.float64) * 100.0

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_default.cub",
                right_name="right_prefilter_default.cub",
            )
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                valid_pixel_percent_threshold=0.2,
                invalid_pixel_radius=0,
                use_parallel_cpu=False,
            )

        self.assertFalse(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count_before_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["tile_count_after_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["preindexed_skipped_tile_count"], 0)
        self.assertIsNone(summary["tile_validity_cache_dir"])
```

- [ ] **Step 3: Run the new integration tests and verify they fail**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_tile_validity_prefilter_options \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_load_image_match_defaults_from_config_reads_tile_validity_fields \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_tile_validity_fields \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_prefilters_invalid_tiles_and_reports_summary \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_keeps_prefilter_disabled_by_default \
  -v
```

Expected: fail because parser fields, API parameters, config defaults, and summary keys do not exist yet.

- [ ] **Step 4: Commit the failing integration tests**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: cover image match tile validity prefilter integration" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 6: Wire tile-validity prefilter into `image_match.py`

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Import tile-validity helpers in both import branches**

In both the script-mode and package-mode import branches, add imports equivalent to:

```python
    from controlnet_construct.tile_validity import (
        DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
        DEFAULT_TILE_VALIDITY_CELL_WIDTH,
        default_tile_validity_cache_dir,
        ensure_dom_validity_index,
        prefilter_paired_windows_by_validity,
        validate_tile_validity_cell_size,
    )
```

and:

```python
    from .tile_validity import (
        DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
        DEFAULT_TILE_VALIDITY_CELL_WIDTH,
        default_tile_validity_cache_dir,
        ensure_dom_validity_index,
        prefilter_paired_windows_by_validity,
        validate_tile_validity_cell_size,
    )
```

- [ ] **Step 2: Add config default fields**

In `load_image_match_defaults_from_config(...)`, add these field specs after `invalid_pixel_radius`:

```python
        (
            "enable_tile_validity_prefilter",
            ("enable_tile_validity_prefilter", "enableTileValidityPrefilter", "EnableTileValidityPrefilter"),
            lambda value: _coerce_config_bool(value, field_name="enable_tile_validity_prefilter"),
        ),
        (
            "tile_validity_cache_dir",
            ("tile_validity_cache_dir", "tileValidityCacheDir", "TileValidityCacheDir"),
            lambda value: str(value),
        ),
        (
            "tile_validity_cell_width",
            ("tile_validity_cell_width", "tileValidityCellWidth", "TileValidityCellWidth"),
            lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_width"),
        ),
        (
            "tile_validity_cell_height",
            ("tile_validity_cell_height", "tileValidityCellHeight", "TileValidityCellHeight"),
            lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_height"),
        ),
```

- [ ] **Step 3: Add API parameters**

Add parameters to `match_dom_pair(...)` after `invalid_pixel_radius`:

```python
    enable_tile_validity_prefilter: bool = False,
    tile_validity_cache_dir: str | Path | None = None,
    tile_validity_cell_width: int = DEFAULT_TILE_VALIDITY_CELL_WIDTH,
    tile_validity_cell_height: int = DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
```

Add the same keyword parameters to `match_dom_pair_to_key_files(...)` so callers can provide them directly:

```python
    enable_tile_validity_prefilter: bool = False,
    tile_validity_cache_dir: str | Path | None = None,
    tile_validity_cell_width: int = DEFAULT_TILE_VALIDITY_CELL_WIDTH,
    tile_validity_cell_height: int = DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
```

- [ ] **Step 4: Resolve validation and default cache directory**

Inside `match_dom_pair(...)`, near the other resolved settings, add:

```python
        resolved_tile_validity_cell_width = validate_tile_validity_cell_size(
            tile_validity_cell_width,
            field_name="tile_validity_cell_width",
        )
        resolved_tile_validity_cell_height = validate_tile_validity_cell_size(
            tile_validity_cell_height,
            field_name="tile_validity_cell_height",
        )
        resolved_tile_validity_cache_dir = (
            Path(tile_validity_cache_dir)
            if tile_validity_cache_dir is not None
            else default_tile_validity_cache_dir()
        )
```

Inside `match_dom_pair_to_key_files(...)`, before calling `match_dom_pair(...)`, add:

```python
    if enable_tile_validity_prefilter and tile_validity_cache_dir is None:
        tile_validity_cache_dir = default_tile_validity_cache_dir(
            metadata_output=metadata_output,
            left_output_key=left_output_key,
        )
```

- [ ] **Step 5: Insert prefiltering after `_paired_windows(...)`**

Immediately after `windows = _paired_windows(...)`, add:

```python
            tile_count_before_preindex_filter = len(windows)
            preindexed_skipped_tile_count = 0
            tile_validity_skip_reasons: dict[str, int] = {}
            left_tile_validity_index_summary: dict[str, object] | None = None
            right_tile_validity_index_summary: dict[str, object] | None = None
            candidate_windows = windows

            if enable_tile_validity_prefilter and windows:
                left_tile_validity_index, left_tile_validity_index_summary = ensure_dom_validity_index(
                    cache_dir=resolved_tile_validity_cache_dir,
                    dom_path=left_dom_path,
                    cube=left_cube,
                    band=band,
                    invalid_values=left_invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                    invalid_pixel_radius=resolved_invalid_pixel_radius,
                    cell_width=resolved_tile_validity_cell_width,
                    cell_height=resolved_tile_validity_cell_height,
                )
                right_tile_validity_index, right_tile_validity_index_summary = ensure_dom_validity_index(
                    cache_dir=resolved_tile_validity_cache_dir,
                    dom_path=right_dom_path,
                    cube=right_cube,
                    band=band,
                    invalid_values=right_invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                    invalid_pixel_radius=resolved_invalid_pixel_radius,
                    cell_width=resolved_tile_validity_cell_width,
                    cell_height=resolved_tile_validity_cell_height,
                )
                prefilter_result = prefilter_paired_windows_by_validity(
                    windows,
                    left_index=left_tile_validity_index,
                    right_index=right_tile_validity_index,
                    valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                )
                candidate_windows = prefilter_result.kept_windows
                preindexed_skipped_tile_count = prefilter_result.preindexed_skipped_tile_count
                tile_validity_skip_reasons = prefilter_result.skip_reasons
```

Then replace tile execution references in that block from `windows` to `candidate_windows`:

```python
            if candidate_windows:
                progress_bar = (
                    _TileProgressBar(
                        left_dom_path=left_dom_path,
                        right_dom_path=right_dom_path,
                        total_tiles=len(candidate_windows),
                    )
                    if show_progress
                    else None
                )
                ...
                if parallel_cpu_requested and len(candidate_windows) > 1:
                    candidate_worker_count = min(len(candidate_windows), resolved_num_worker_parallel_cpu)
                    ...
                                    candidate_windows,
                    ...
                            candidate_windows,
```

In the `else` for `preparation.status != "ready"`, initialize:

```python
            windows = []
            candidate_windows = []
            tile_count_before_preindex_filter = 0
            preindexed_skipped_tile_count = 0
            tile_validity_skip_reasons = {}
            left_tile_validity_index_summary = None
            right_tile_validity_index_summary = None
```

- [ ] **Step 6: Add summary and metadata fields**

Before building `summary`, compute:

```python
        full_resolution_skipped_tile_count = sum(1 for tile in tile_summaries if tile.status != "matched")
```

Update summary fields:

```python
            "tile_count": len(windows),
            "tile_count_before_preindex_filter": tile_count_before_preindex_filter,
            "tile_count_after_preindex_filter": len(candidate_windows),
            "preindexed_skipped_tile_count": preindexed_skipped_tile_count,
            "full_resolution_skipped_tile_count": full_resolution_skipped_tile_count,
            "matched_tile_count": sum(1 for tile in tile_summaries if tile.status == "matched"),
            "skipped_tile_count": preindexed_skipped_tile_count + full_resolution_skipped_tile_count,
            "tile_validity_prefilter_enabled": bool(enable_tile_validity_prefilter),
            "tile_validity_cache_dir": str(resolved_tile_validity_cache_dir) if enable_tile_validity_prefilter else None,
            "tile_validity_cell_width": resolved_tile_validity_cell_width,
            "tile_validity_cell_height": resolved_tile_validity_cell_height,
            "tile_validity_skip_reasons": tile_validity_skip_reasons,
            "left_tile_validity_index": left_tile_validity_index_summary,
            "right_tile_validity_index": right_tile_validity_index_summary,
```

In `match_dom_pair_to_key_files(...)`, add these keys to `metadata_payload["image_match"]`:

```python
            "tile_count_before_preindex_filter": summary["tile_count_before_preindex_filter"],
            "tile_count_after_preindex_filter": summary["tile_count_after_preindex_filter"],
            "preindexed_skipped_tile_count": summary["preindexed_skipped_tile_count"],
            "full_resolution_skipped_tile_count": summary["full_resolution_skipped_tile_count"],
            "tile_validity_prefilter_enabled": summary["tile_validity_prefilter_enabled"],
            "tile_validity_cache_dir": summary["tile_validity_cache_dir"],
            "tile_validity_cell_width": summary["tile_validity_cell_width"],
            "tile_validity_cell_height": summary["tile_validity_cell_height"],
            "tile_validity_skip_reasons": summary["tile_validity_skip_reasons"],
            "left_tile_validity_index": summary["left_tile_validity_index"],
            "right_tile_validity_index": summary["right_tile_validity_index"],
```

- [ ] **Step 7: Add CLI flags and main forwarding**

In `build_argument_parser(...)`, after `--invalid-pixel-radius`, add:

```python
    parser.add_argument("--enable-tile-validity-prefilter", dest="enable_tile_validity_prefilter", action="store_true", help="Enable workflow-level DOM validity index prefiltering before full-resolution tile reads.")
    parser.add_argument("--tile-validity-cache-dir", default=None, help="Directory for reusable per-DOM tile-validity index cache files.")
    parser.add_argument("--tile-validity-cell-width", type=lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_width"), default=DEFAULT_TILE_VALIDITY_CELL_WIDTH, help=f"Coarse validity-index cell width. Default: {DEFAULT_TILE_VALIDITY_CELL_WIDTH}.")
    parser.add_argument("--tile-validity-cell-height", type=lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_height"), default=DEFAULT_TILE_VALIDITY_CELL_HEIGHT, help=f"Coarse validity-index cell height. Default: {DEFAULT_TILE_VALIDITY_CELL_HEIGHT}.")
```

Update `parser.set_defaults(...)`:

```python
    parser.set_defaults(write_match_visualization=True, use_parallel_cpu=True, enable_low_resolution_offset_estimation=False, enable_tile_validity_prefilter=False, show_progress=True)
```

Forward parsed args in `main(...)`:

```python
        enable_tile_validity_prefilter=args.enable_tile_validity_prefilter,
        tile_validity_cache_dir=args.tile_validity_cache_dir,
        tile_validity_cell_width=args.tile_validity_cell_width,
        tile_validity_cell_height=args.tile_validity_cell_height,
```

- [ ] **Step 8: Run focused image-match integration tests**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_tile_validity_prefilter_options \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_load_image_match_defaults_from_config_reads_tile_validity_fields \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_tile_validity_fields \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_prefilters_invalid_tiles_and_reports_summary \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_keeps_prefilter_disabled_by_default \
  -v
```

Expected: all five tests pass.

- [ ] **Step 9: Run tile-validity tests again**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_tile_validity_unit_test -v
```

Expected: all tile-validity tests still pass.

- [ ] **Step 10: Commit image-match prefilter integration**

```bash
git add examples/controlnet_construct/image_match.py examples/controlnet_construct/tile_validity.py tests/unitTest/controlnet_construct_matching_unit_test.py tests/unitTest/controlnet_construct_tile_validity_unit_test.py
git commit -m "feat: prefilter invalid DOM tiles before matching" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 7: Add batched parallel worker tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify in Task 8: `examples/controlnet_construct/tile_matching.py`
- Modify in Task 8: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add direct worker-batch test**

Append this method inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_parallel_tile_batch_worker_reuses_open_cubes_for_task_shard(self):
        open_paths: list[str] = []
        close_count = 0

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, path, mode):
                open_paths.append(str(path))
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                nonlocal close_count
                close_count += 1
                self._open = False

        tasks = [
            tile_matching_module.IndexedTileMatchTask(
                index=0,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
            tile_matching_module.IndexedTileMatchTask(
                index=1,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
        ]

        def fake_match_task_with_open_cubes(task, **kwargs):
            return tile_matching_module.TileMatchResult(
                stats=tile_matching_module.TileMatchStats(
                    local_start_x=task.paired_window.local_window.start_x,
                    local_start_y=task.paired_window.local_window.start_y,
                    width=task.paired_window.local_window.width,
                    height=task.paired_window.local_window.height,
                    left_start_x=task.paired_window.left_window.start_x,
                    left_start_y=task.paired_window.left_window.start_y,
                    right_start_x=task.paired_window.right_window.start_x,
                    right_start_y=task.paired_window.right_window.start_y,
                    left_valid_pixel_count=64,
                    right_valid_pixel_count=64,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_insufficient_matches",
                ),
                left_points=(),
                right_points=(),
            )

        with mock.patch.object(tile_matching_module.ip, "Cube", FakeCube), mock.patch.object(
            tile_matching_module,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching_module,
            "_match_tile_task_with_open_cubes",
            side_effect=fake_match_task_with_open_cubes,
        ):
            results = tile_matching_module._match_tile_task_batch_worker(tuple(tasks))

        self.assertEqual(open_paths, ["left.cub", "right.cub"])
        self.assertEqual(close_count, 2)
        self.assertEqual([index for index, _ in results], [0, 1])
```

- [ ] **Step 2: Add backend diagnostic test**

Append this method inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_match_dom_pair_reports_batched_parallel_backend(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            )
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_batched_parallel.cub",
                right_name="right_batched_parallel.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ):
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                )

        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 2)
```

- [ ] **Step 3: Run the new batched parallel tests and verify they fail**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_parallel_tile_batch_worker_reuses_open_cubes_for_task_shard \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_batched_parallel_backend \
  -v
```

Expected: fail because `IndexedTileMatchTask`, `_match_tile_task_batch_worker`, `_match_tile_task_with_open_cubes`, and the new backend diagnostic do not exist yet.

- [ ] **Step 4: Commit failing batched parallel tests**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: cover batched parallel tile matching" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 8: Implement batched process-pool cube reuse

**Files:**
- Modify: `examples/controlnet_construct/tile_matching.py`
- Modify: `examples/controlnet_construct/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add indexed task dataclass and chunking helper**

In `examples/controlnet_construct/tile_matching.py`, add this dataclass after `TileMatchTask`:

```python
@dataclass(frozen=True, slots=True)
class IndexedTileMatchTask:
    index: int
    task: TileMatchTask
```

Add this helper near `_tile_match_process_pool_context()`:

```python
def _chunk_indexed_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    max_workers: int,
) -> list[tuple[IndexedTileMatchTask, ...]]:
    if not tasks:
        return []
    worker_count = max(1, min(max_workers, len(tasks)))
    chunks: list[list[IndexedTileMatchTask]] = [[] for _ in range(worker_count)]
    for index, task in enumerate(tasks):
        chunks[index % worker_count].append(IndexedTileMatchTask(index=index, task=task))
    return [tuple(chunk) for chunk in chunks if chunk]
```

- [ ] **Step 2: Extract single-task matching with open cubes**

Add this helper before `_match_single_paired_window_worker(...)`:

```python
def _match_tile_task_with_open_cubes(
    task: TileMatchTask,
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
) -> TileMatchResult:
    left_values = _read_cube_window(left_cube, task.paired_window.left_window, band=task.band)
    right_values = _read_cube_window(right_cube, task.paired_window.right_window, band=task.band)
    return _match_tile_from_window_values(
        left_values=left_values,
        right_values=right_values,
        local_window=task.paired_window.local_window,
        left_window=task.paired_window.left_window,
        right_window=task.paired_window.right_window,
        minimum_value=task.minimum_value,
        maximum_value=task.maximum_value,
        lower_percent=task.lower_percent,
        upper_percent=task.upper_percent,
        left_invalid_values=left_invalid_values,
        right_invalid_values=right_invalid_values,
        special_pixel_abs_threshold=task.special_pixel_abs_threshold,
        min_valid_pixels=task.min_valid_pixels,
        valid_pixel_percent_threshold=task.valid_pixel_percent_threshold,
        invalid_pixel_radius=task.invalid_pixel_radius,
        ratio_test=task.ratio_test,
        matcher_method=task.matcher_method,
        max_features=task.max_features,
        sift_octave_layers=task.sift_octave_layers,
        sift_contrast_threshold=task.sift_contrast_threshold,
        sift_edge_threshold=task.sift_edge_threshold,
        sift_sigma=task.sift_sigma,
    )
```

Then replace the body of `_match_single_paired_window_worker(...)` with a thin compatibility wrapper that calls this helper after opening cubes.

- [ ] **Step 3: Add batched worker**

Add this function after `_match_single_paired_window_worker(...)`:

```python
def _match_tile_task_batch_worker(
    indexed_tasks: tuple[IndexedTileMatchTask, ...],
) -> tuple[tuple[int, TileMatchResult], ...]:
    if not indexed_tasks:
        return ()
    first_task = indexed_tasks[0].task
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(first_task.left_dom_path, "r")
    right_cube.open(first_task.right_dom_path, "r")
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, first_task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, first_task.invalid_values)
        results: list[tuple[int, TileMatchResult]] = []
        for indexed_task in indexed_tasks:
            results.append(
                (
                    indexed_task.index,
                    _match_tile_task_with_open_cubes(
                        indexed_task.task,
                        left_cube=left_cube,
                        right_cube=right_cube,
                        left_invalid_values=left_invalid_values,
                        right_invalid_values=right_invalid_values,
                    ),
                )
            )
        return tuple(results)
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()
```

- [ ] **Step 4: Replace `_run_parallel_tile_match_tasks(...)` internals**

Replace the function body with:

```python
def _run_parallel_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    max_workers: int,
    progress_callback: Callable[[], None] | None = None,
) -> list[TileMatchResult]:
    if not tasks:
        return []
    chunks = _chunk_indexed_tile_match_tasks(tasks, max_workers=max_workers)
    with ProcessPoolExecutor(max_workers=min(max_workers, len(chunks)), mp_context=_tile_match_process_pool_context()) as executor:
        futures = {executor.submit(_match_tile_task_batch_worker, chunk): chunk for chunk in chunks}
        ordered_results: list[TileMatchResult | None] = [None] * len(tasks)
        for future in as_completed(futures):
            indexed_results = future.result()
            for index, result in indexed_results:
                ordered_results[index] = result
                if progress_callback is not None:
                    progress_callback()
        return [result for result in ordered_results if result is not None]
```

- [ ] **Step 5: Update image-match backend diagnostic**

In `examples/controlnet_construct/image_match.py`, change the backend assignment after successful `_run_parallel_tile_match_tasks(...)` from:

```python
                        parallel_cpu_backend = "process_pool"
```

to:

```python
                        parallel_cpu_backend = "process_pool_batched_cube_reuse"
```

Update older tests that asserted `"process_pool"` to expect `"process_pool_batched_cube_reuse"` when they exercise the parallel path.

- [ ] **Step 6: Run batched parallel tests**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_parallel_tile_batch_worker_reuses_open_cubes_for_task_shard \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_batched_parallel_backend \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_uses_process_pool_parallel_by_default_for_multiple_tiles \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_respects_requested_parallel_worker_limit \
  -v
```

Expected: all listed tests pass.

- [ ] **Step 7: Commit batched parallel implementation**

```bash
git add examples/controlnet_construct/tile_matching.py examples/controlnet_construct/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: reuse DOM cubes in parallel tile workers" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 9: Add metadata-output and CLI smoke coverage

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py` only if wrapper fake dispatchers assert new config-default lookups.
- Modify: `examples/controlnet_construct/image_match.py` if any metadata field is missing.

- [ ] **Step 1: Add metadata sidecar assertion**

Append this method inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_match_dom_pair_to_key_files_writes_tile_validity_metadata(self):
        values = np.ones((32, 64), dtype=np.float64) * 100.0
        values[:, 32:64] = 0.0

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_metadata.cub",
                right_name="right_prefilter_metadata.cub",
            )
            left_key = temp_dir / "dom_keys" / "left.key"
            right_key = temp_dir / "dom_keys" / "right.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"

            match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key,
                right_key,
                metadata_output=metadata_output,
                write_match_visualization=False,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        image_match_payload = payload["image_match"]
        self.assertTrue(image_match_payload["tile_validity_prefilter_enabled"])
        self.assertEqual(image_match_payload["preindexed_skipped_tile_count"], 1)
        self.assertEqual(image_match_payload["tile_count_before_preindex_filter"], 2)
        self.assertEqual(image_match_payload["tile_count_after_preindex_filter"], 1)
        self.assertTrue(str(image_match_payload["tile_validity_cache_dir"]).endswith("tile_validity_cache"))
```

- [ ] **Step 2: Run metadata test and fix any missing fields**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_to_key_files_writes_tile_validity_metadata \
  -v
```

Expected: pass. If it fails with a missing metadata key, add the missing key to `metadata_payload["image_match"]` exactly as named in the assertion.

- [ ] **Step 3: Run CLI parser/config focused tests**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_tile_validity_prefilter_options \
  tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_tile_validity_fields \
  -v
```

Expected: pass.

- [ ] **Step 4: Commit metadata and CLI coverage**

```bash
git add examples/controlnet_construct/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: cover tile validity metadata output" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 10: Run focused regression suite and update documentation

**Files:**
- Modify: `examples/controlnet_construct/usage.md` if it already documents image-match flags.
- Modify: `examples/controlnet_construct/controlnet_config.low_memory_lro.json` only if you want the LRO low-memory example to opt in explicitly.
- Test: all files changed by earlier tasks.

- [ ] **Step 1: Search whether user-facing docs list image-match flags**

Run:

```bash
rg "valid-pixel-percent-threshold|num-worker-parallel-cpu|low-resolution|image_match.py" examples/controlnet_construct -g "*.md" -n
```

Expected: if `examples/controlnet_construct/usage.md` lists image-match flags, update it in the next step. If there is no matching user-facing flag list, skip Step 2 and do not create new docs.

- [ ] **Step 2: Add usage text when an existing flag list is present**

If `examples/controlnet_construct/usage.md` contains an image-match flag list, add this text next to the other image-match performance flags:

```markdown
- `--enable-tile-validity-prefilter`: explicitly enables the workflow-level DOM validity-index cache before full-resolution tile reads. Disabled by default so existing runs remain a baseline.
- `--tile-validity-cache-dir PATH`: stores reusable per-DOM validity index files. If omitted, image matching derives a workflow-level `tile_validity_cache` directory from the output context.
- `--tile-validity-cell-width N` and `--tile-validity-cell-height N`: control the coarse validity grid size. Defaults are 1024 x 1024.
```

- [ ] **Step 3: Run focused Python regression tests**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_tile_validity_unit_test \
  tests.unitTest.controlnet_construct_matching_unit_test \
  -v
```

Expected: all tests in both modules pass.

- [ ] **Step 4: Run pipeline wrapper regression tests if wrapper files changed**

Run this only if `examples/controlnet_construct/run_pipeline_example.sh`, `examples/controlnet_construct/run_image_match_batch_example.sh`, or `tests/unitTest/controlnet_construct_pipeline_unit_test.py` changed:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: all pipeline wrapper tests pass.

- [ ] **Step 5: Run a small real-cube smoke test**

Run:

```bash
conda run -n asp360_new python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT / "examples"))

from controlnet_construct.image_match import match_dom_pair

left = PROJECT_ROOT / "tests/data/hidtmgen/ortho/PSP_002118_1510_1m_o_forPDS_cropped.cub"
right = PROJECT_ROOT / "tests/data/hidtmgen/ortho/PSP_002118_1510_25cm_o_forPDS_cropped.cub"
with TemporaryDirectory() as temp_dir:
    _, _, summary = match_dom_pair(
        left,
        right,
        min_valid_pixels=16,
        invalid_pixel_radius=0,
        valid_pixel_percent_threshold=0.05,
        enable_tile_validity_prefilter=True,
        tile_validity_cache_dir=Path(temp_dir) / "tile_validity_cache",
        tile_validity_cell_width=32,
        tile_validity_cell_height=32,
        use_parallel_cpu=False,
    )
print(summary["tile_validity_prefilter_enabled"], summary["tile_count_before_preindex_filter"], summary["tile_count_after_preindex_filter"])
PY
```

Expected: prints `True` followed by two integer tile counts, and exits with status 0.

- [ ] **Step 6: Commit documentation or final test adjustments**

If Step 2 changed docs or Step 4 changed wrapper tests, commit them:

```bash
git add examples/controlnet_construct/usage.md examples/controlnet_construct/controlnet_config.low_memory_lro.json examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_image_match_batch_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "docs: document tile validity prefilter options" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

If none of those files changed, do not create an empty commit.

## Task 11: Final verification and handoff

**Files:**
- No planned code changes.
- Verify all changed files.

- [ ] **Step 1: Inspect final diff**

Run:

```bash
git --no-pager diff --stat main...HEAD
git --no-pager status --short
```

Expected: status is clean except for intentional uncommitted changes made after the last task. If uncommitted changes remain, either commit them with the trailer or explain why they are intentionally uncommitted.

- [ ] **Step 2: Run the final focused suite**

Run:

```bash
conda run -n asp360_new python -m unittest \
  tests.unitTest.controlnet_construct_tile_validity_unit_test \
  tests.unitTest.controlnet_construct_matching_unit_test \
  -v
```

Expected: all tests pass.

- [ ] **Step 3: Record manual performance commands for the user**

Provide these commands in the final handoff so the user can benchmark their selected LRO workflow:

```bash
export work=/media/gengxun/Elements/data/lro/test_controlnet_python/MULTIPLE_IMGS
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir "${work}" \
  --original-list "${work}/original_images.lis" \
  --dom-list "${work}/doms.lis" \
  --config examples/controlnet_construct/controlnet_config.low_memory_lro.json \
  --no-parallel-cpu
```

Then create a copy of the config with `ImageMatch.enable_tile_validity_prefilter`, `ImageMatch.tile_validity_cache_dir`, `ImageMatch.tile_validity_cell_width`, and `ImageMatch.tile_validity_cell_height` set, and rerun the same command to compare `tile_count_before_preindex_filter`, `tile_count_after_preindex_filter`, `preindexed_skipped_tile_count`, and wall time.
