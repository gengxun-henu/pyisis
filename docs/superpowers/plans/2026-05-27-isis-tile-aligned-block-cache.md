# ISIS Tile-Aligned Block Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in ISIS storage-tile block-alignment mode for full-resolution DOM/controlnet matching, with metadata and cache diagnostics that prove whether aligned blocks improve read/cache behavior.

**Architecture:** Keep the first implementation in Python. Add a focused block-alignment helper that inspects ISIS `Core/TileSamples` and `Core/TileLines`, resolves effective block/overlap settings from crop offsets, and leaves existing tiling behavior unchanged when alignment is off or unsupported. Thread the resolved settings into `match_dom_pair()` before paired windows are built, and add lightweight `TileCache` counters for metadata-safe profiling.

**Tech Stack:** Python 3.12, `isis_pybind`, NumPy, `unittest`, existing `asp360_new` conda environment, existing `examples/image_match` and `examples/controlnet_construct` wrapper layout.

---

## File Structure

- Create `examples/image_match/tile_block_alignment.py`: owns alignment-mode constants, dataclasses, storage-tile metadata reading, block/overlap resolution, and aligned local-start generation.
- Create `examples/controlnet_construct/tile_block_alignment.py`: compatibility wrapper that re-exports `image_match.tile_block_alignment`, matching existing wrapper modules.
- Modify `examples/image_match/tiling.py`: add optional explicit-axis-start support while preserving `generate_tiles()` defaults.
- Modify `examples/image_match/tile_matching.py`: allow `_paired_windows()` to accept precomputed local windows and keep old behavior when omitted.
- Modify `examples/image_match/tile_cache.py`: add counters/timing and a `summary()` method without changing read results.
- Modify `examples/image_match/image_match.py`: add public `tile_block_alignment_mode` parameter/CLI/config parsing, call resolver after pair preparation, pass effective windows to `_paired_windows()`, and record metadata.
- Modify `examples/controlnet_construct/parameter_catalog.py`: document the new config/CLI parameter in the catalog.
- Create `tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py`: focused resolver and tiling tests.
- Modify `tests/unitTest/controlnet_construct_tile_cache_unit_test.py`: assert cache diagnostics counters.
- Modify `tests/unitTest/controlnet_construct_matching_unit_test.py`: assert `match_dom_pair()` metadata and fallback behavior.

## Task 1: Add tile-alignment resolver

**Files:**
- Create: `examples/image_match/tile_block_alignment.py`
- Create: `examples/controlnet_construct/tile_block_alignment.py`
- Test: `tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py`

- [ ] **Step 1: Write failing resolver tests**

Add this file:

```python
"""Unit tests for ISIS storage-tile block alignment helpers.

Author: Geng Xun
Created: 2026-05-27
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

alignment = importlib.import_module("controlnet_construct.tile_block_alignment")
StorageTileShape = alignment.StorageTileShape
resolve_tile_aligned_block_config = alignment.resolve_tile_aligned_block_config
generate_aligned_axis_starts = alignment.generate_aligned_axis_starts


class TestTileBlockAlignmentResolver(unittest.TestCase):
    def test_off_preserves_requested_values(self):
        result = resolve_tile_aligned_block_config(
            mode="off",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=7,
            left_offset_y=9,
            right_offset_x=13,
            right_offset_y=15,
            requested_block_width=1000,
            requested_block_height=900,
            requested_overlap_x=120,
            requested_overlap_y=80,
            common_width=5000,
            common_height=4000,
        )

        self.assertEqual(result.mode, "off")
        self.assertFalse(result.aligned)
        self.assertEqual(result.effective_block_width, 1000)
        self.assertEqual(result.effective_block_height, 900)
        self.assertEqual(result.effective_overlap_x, 120)
        self.assertEqual(result.effective_overlap_y, 80)
        self.assertIsNone(result.local_windows)

    def test_auto_aligns_when_offsets_share_storage_remainder(self):
        result = resolve_tile_aligned_block_config(
            mode="auto",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=256,
            left_offset_y=128,
            right_offset_x=512,
            right_offset_y=384,
            requested_block_width=1000,
            requested_block_height=900,
            requested_overlap_x=120,
            requested_overlap_y=80,
            common_width=2600,
            common_height=1800,
        )

        self.assertEqual(result.mode, "auto")
        self.assertTrue(result.aligned)
        self.assertEqual(result.effective_block_width, 1024)
        self.assertEqual(result.effective_block_height, 896)
        self.assertEqual(result.effective_overlap_x, 128)
        self.assertEqual(result.effective_overlap_y, 128)
        self.assertGreater(len(result.local_windows or ()), 1)
        for window in result.local_windows[:-1]:
            self.assertEqual((256 + window.start_x) % 128, 0)
            self.assertEqual((512 + window.start_x) % 128, 0)
            self.assertEqual((128 + window.start_y) % 128, 0)
            self.assertEqual((384 + window.start_y) % 128, 0)

    def test_auto_falls_back_when_offset_remainders_conflict(self):
        result = resolve_tile_aligned_block_config(
            mode="auto",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=0,
            left_offset_y=0,
            right_offset_x=64,
            right_offset_y=0,
            requested_block_width=512,
            requested_block_height=512,
            requested_overlap_x=128,
            requested_overlap_y=128,
            common_width=2048,
            common_height=2048,
        )

        self.assertFalse(result.aligned)
        self.assertEqual(result.fallback_reason_code, "incompatible_offset_remainders")
        self.assertIsNone(result.local_windows)

    def test_required_mode_raises_when_offset_remainders_conflict(self):
        with self.assertRaisesRegex(ValueError, "cannot align both DOM windows"):
            resolve_tile_aligned_block_config(
                mode="isis-storage",
                left_shape=StorageTileShape(width=128, height=128),
                right_shape=StorageTileShape(width=128, height=128),
                left_offset_x=0,
                left_offset_y=0,
                right_offset_x=64,
                right_offset_y=0,
                requested_block_width=512,
                requested_block_height=512,
                requested_overlap_x=128,
                requested_overlap_y=128,
                common_width=2048,
                common_height=2048,
            )

    def test_generate_aligned_axis_starts_keeps_full_coverage(self):
        starts = generate_aligned_axis_starts(
            size=2300,
            block_size=512,
            overlap_size=128,
            left_offset=256,
            right_offset=512,
            left_tile_size=128,
            right_tile_size=128,
        )

        self.assertEqual(starts[0], 0)
        self.assertEqual(starts[-1], 1788)
        for start in starts[:-1]:
            self.assertEqual((256 + start) % 128, 0)
            self.assertEqual((512 + start) % 128, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_block_alignment_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'controlnet_construct.tile_block_alignment'`.

- [ ] **Step 3: Implement the resolver module**

Create `examples/image_match/tile_block_alignment.py`:

```python
"""ISIS storage-tile block alignment helpers for DOM matching."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .tiling import TileWindow, generate_tiles_from_starts

SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES = ("off", "auto", "isis-storage")
DEFAULT_TILE_BLOCK_ALIGNMENT_MODE = "off"


@dataclass(frozen=True, slots=True)
class StorageTileShape:
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class TileBlockAlignmentResult:
    mode: str
    aligned: bool
    requested_block_width: int
    requested_block_height: int
    requested_overlap_x: int
    requested_overlap_y: int
    effective_block_width: int
    effective_block_height: int
    effective_overlap_x: int
    effective_overlap_y: int
    left_storage_tile_width: int | None
    left_storage_tile_height: int | None
    right_storage_tile_width: int | None
    right_storage_tile_height: int | None
    left_offset_remainder_x: int | None
    left_offset_remainder_y: int | None
    right_offset_remainder_x: int | None
    right_offset_remainder_y: int | None
    fallback_reason_code: str | None
    reason: str
    local_windows: tuple[TileWindow, ...] | None = None

    def to_metadata(self) -> dict[str, object]:
        payload = asdict(self)
        payload["local_windows"] = None if self.local_windows is None else [asdict(window) for window in self.local_windows]
        return payload


def normalize_tile_block_alignment_mode(mode: str) -> str:
    normalized = str(mode).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES:
        raise ValueError(
            "tile_block_alignment_mode must be one of "
            f"{SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES}; got {mode!r}."
        )
    return normalized


def storage_tile_shape_from_cube(cube: Any) -> StorageTileShape | None:
    try:
        core = cube.group("Core")
        width = int(core.find_keyword("TileSamples")[0])
        height = int(core.find_keyword("TileLines")[0])
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    return StorageTileShape(width=width, height=height)


def _ceil_to_multiple(value: int, multiple: int) -> int:
    if value <= 0:
        raise ValueError("value must be positive.")
    if multiple <= 0:
        raise ValueError("multiple must be positive.")
    return ((value + multiple - 1) // multiple) * multiple


def _round_overlap_to_multiple(value: int, multiple: int, block_size: int) -> int:
    if value < 0:
        raise ValueError("overlap must be non-negative.")
    rounded = _ceil_to_multiple(max(1, value), multiple) if value > 0 else 0
    if rounded >= block_size:
        rounded = max(0, block_size - multiple)
    return rounded


def _compatible_axis_remainders(
    *,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> bool:
    limit = left_tile_size * right_tile_size
    for local_start in range(0, limit, min(left_tile_size, right_tile_size)):
        if (left_offset + local_start) % left_tile_size == 0 and (right_offset + local_start) % right_tile_size == 0:
            return True
    return False


def _first_aligned_start(
    *,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> int | None:
    limit = left_tile_size * right_tile_size
    for local_start in range(0, limit, min(left_tile_size, right_tile_size)):
        if (left_offset + local_start) % left_tile_size == 0 and (right_offset + local_start) % right_tile_size == 0:
            return local_start
    return None


def _shared_tile_size(left_size: int, right_size: int) -> int | None:
    larger = max(left_size, right_size)
    smaller = min(left_size, right_size)
    if larger % smaller != 0:
        return None
    return larger


def generate_aligned_axis_starts(
    *,
    size: int,
    block_size: int,
    overlap_size: int,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> list[int]:
    if size <= 0:
        raise ValueError("size must be positive.")
    if block_size <= 0:
        raise ValueError("block_size must be positive.")
    if overlap_size < 0 or overlap_size >= block_size:
        raise ValueError("overlap_size must be within [0, block_size).")
    if size <= block_size:
        return [0]

    first = _first_aligned_start(
        left_offset=left_offset,
        right_offset=right_offset,
        left_tile_size=left_tile_size,
        right_tile_size=right_tile_size,
    )
    if first is None:
        raise ValueError("Offsets cannot align both DOM windows to storage tile boundaries.")

    step = block_size - overlap_size
    last_start = size - block_size
    starts = [0]
    current = first if first > 0 and first < last_start else step
    while current < last_start:
        if current > starts[-1]:
            starts.append(current)
        current += step
    if starts[-1] != last_start:
        starts.append(last_start)
    return starts


def resolve_tile_aligned_block_config(
    *,
    mode: str,
    left_shape: StorageTileShape | None,
    right_shape: StorageTileShape | None,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    requested_block_width: int,
    requested_block_height: int,
    requested_overlap_x: int,
    requested_overlap_y: int,
    common_width: int,
    common_height: int,
) -> TileBlockAlignmentResult:
    resolved_mode = normalize_tile_block_alignment_mode(mode)
    base_kwargs = {
        "mode": resolved_mode,
        "requested_block_width": int(requested_block_width),
        "requested_block_height": int(requested_block_height),
        "requested_overlap_x": int(requested_overlap_x),
        "requested_overlap_y": int(requested_overlap_y),
        "effective_block_width": int(requested_block_width),
        "effective_block_height": int(requested_block_height),
        "effective_overlap_x": int(requested_overlap_x),
        "effective_overlap_y": int(requested_overlap_y),
        "left_storage_tile_width": None if left_shape is None else left_shape.width,
        "left_storage_tile_height": None if left_shape is None else left_shape.height,
        "right_storage_tile_width": None if right_shape is None else right_shape.width,
        "right_storage_tile_height": None if right_shape is None else right_shape.height,
        "left_offset_remainder_x": None if left_shape is None else int(left_offset_x) % left_shape.width,
        "left_offset_remainder_y": None if left_shape is None else int(left_offset_y) % left_shape.height,
        "right_offset_remainder_x": None if right_shape is None else int(right_offset_x) % right_shape.width,
        "right_offset_remainder_y": None if right_shape is None else int(right_offset_y) % right_shape.height,
    }
    if resolved_mode == "off":
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code=None, reason="Tile block alignment is disabled.", local_windows=None, **base_kwargs)
    if left_shape is None or right_shape is None:
        if resolved_mode == "isis-storage":
            raise ValueError("tile_block_alignment_mode='isis-storage' requires valid ISIS storage tile metadata.")
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code="missing_storage_tile_metadata", reason="Storage tile metadata is unavailable; using requested block geometry.", local_windows=None, **base_kwargs)

    shared_w = _shared_tile_size(left_shape.width, right_shape.width)
    shared_h = _shared_tile_size(left_shape.height, right_shape.height)
    compatible_x = _compatible_axis_remainders(left_offset=left_offset_x, right_offset=right_offset_x, left_tile_size=left_shape.width, right_tile_size=right_shape.width)
    compatible_y = _compatible_axis_remainders(left_offset=left_offset_y, right_offset=right_offset_y, left_tile_size=left_shape.height, right_tile_size=right_shape.height)
    if shared_w is None or shared_h is None or not compatible_x or not compatible_y:
        reason = "Requested crop offsets cannot align both DOM windows to ISIS storage tile boundaries."
        if resolved_mode == "isis-storage":
            raise ValueError(reason)
        code = "incompatible_storage_tile_sizes" if shared_w is None or shared_h is None else "incompatible_offset_remainders"
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code=code, reason=reason, local_windows=None, **base_kwargs)

    effective_block_width = _ceil_to_multiple(requested_block_width, shared_w)
    effective_block_height = _ceil_to_multiple(requested_block_height, shared_h)
    effective_overlap_x = _round_overlap_to_multiple(requested_overlap_x, shared_w, effective_block_width)
    effective_overlap_y = _round_overlap_to_multiple(requested_overlap_y, shared_h, effective_block_height)
    x_starts = generate_aligned_axis_starts(size=common_width, block_size=effective_block_width, overlap_size=effective_overlap_x, left_offset=left_offset_x, right_offset=right_offset_x, left_tile_size=left_shape.width, right_tile_size=right_shape.width)
    y_starts = generate_aligned_axis_starts(size=common_height, block_size=effective_block_height, overlap_size=effective_overlap_y, left_offset=left_offset_y, right_offset=right_offset_y, left_tile_size=left_shape.height, right_tile_size=right_shape.height)
    local_windows = tuple(
        TileWindow(start_x=x, start_y=y, width=min(effective_block_width, common_width - x), height=min(effective_block_height, common_height - y))
        for y in y_starts
        for x in x_starts
    )
    return TileBlockAlignmentResult(
        aligned=True,
        fallback_reason_code=None,
        reason="Using ISIS storage-tile-aligned matching blocks.",
        local_windows=local_windows,
        **{
            **base_kwargs,
            "effective_block_width": effective_block_width,
            "effective_block_height": effective_block_height,
            "effective_overlap_x": effective_overlap_x,
            "effective_overlap_y": effective_overlap_y,
        },
    )
```

Create `examples/controlnet_construct/tile_block_alignment.py`:

```python
"""Compatibility wrapper for shared ISIS tile-block alignment helpers.

Author: Geng Xun
Created: 2026-05-27
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SHARED_MODULE = import_module("image_match.tile_block_alignment")
sys.modules[__name__] = _SHARED_MODULE
```

- [ ] **Step 4: Run tests to verify resolver passes**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_block_alignment_unit_test -v
```

Expected: PASS, all 5 tests pass.

- [ ] **Step 5: Commit resolver**

```bash
git add examples/image_match/tile_block_alignment.py examples/controlnet_construct/tile_block_alignment.py tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py
git commit -m "feat(image-match): resolve ISIS tile-aligned block geometry" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 2: Thread aligned windows through tiling and tile matching

**Files:**
- Modify: `examples/image_match/tiling.py`
- Modify: `examples/image_match/tile_matching.py`
- Test: `tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py`

- [ ] **Step 1: Add failing tests for explicit local starts and paired windows**

Append these tests to `TestTileBlockAlignmentResolver` in `tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py`:

```python
    def test_generate_tiles_from_explicit_starts(self):
        tiling = importlib.import_module("image_match.tiling")
        tiles = tiling.generate_tiles_from_starts(
            image_width=1000,
            image_height=900,
            x_starts=[0, 384, 488],
            y_starts=[0, 384],
            block_width=512,
            block_height=512,
        )

        self.assertEqual([(tile.start_x, tile.start_y, tile.width, tile.height) for tile in tiles], [
            (0, 0, 512, 512),
            (384, 0, 512, 512),
            (488, 0, 512, 512),
            (0, 384, 512, 512),
            (384, 384, 512, 512),
            (488, 384, 512, 512),
        ])

    def test_paired_windows_accept_precomputed_local_windows(self):
        tile_matching = importlib.import_module("image_match.tile_matching")
        tiling = importlib.import_module("image_match.tiling")
        local_windows = [
            tiling.TileWindow(start_x=0, start_y=0, width=512, height=512),
            tiling.TileWindow(start_x=384, start_y=0, width=512, height=512),
        ]

        paired = tile_matching._paired_windows(
            left_offset_x=128,
            left_offset_y=256,
            right_offset_x=384,
            right_offset_y=512,
            common_width=1024,
            common_height=512,
            max_image_dimension=1,
            block_width=100,
            block_height=100,
            overlap_x=10,
            overlap_y=10,
            local_windows=local_windows,
        )

        self.assertEqual(len(paired), 2)
        self.assertEqual(paired[0].left_window.start_x, 128)
        self.assertEqual(paired[0].right_window.start_x, 384)
        self.assertEqual(paired[1].left_window.start_x, 512)
        self.assertEqual(paired[1].right_window.start_x, 768)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_block_alignment_unit_test -v
```

Expected: FAIL with missing `generate_tiles_from_starts` and `_paired_windows()` unexpected `local_windows`.

- [ ] **Step 3: Add explicit-start tiling helper**

Modify `examples/image_match/tiling.py` by adding this function after `generate_tiles()`:

```python
def generate_tiles_from_starts(
    image_width: int,
    image_height: int,
    *,
    x_starts: list[int],
    y_starts: list[int],
    block_width: int,
    block_height: int,
) -> list[TileWindow]:
    """Generate full-coverage tiles from precomputed axis starts."""
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image dimensions must be positive.")
    if block_width <= 0 or block_height <= 0:
        raise ValueError("Block dimensions must be positive.")
    if not x_starts or not y_starts:
        raise ValueError("x_starts and y_starts must be non-empty.")

    tiles: list[TileWindow] = []
    for start_y in y_starts:
        if start_y < 0 or start_y >= image_height:
            raise ValueError(f"Invalid y start {start_y} for image height {image_height}.")
        tile_height = min(block_height, image_height - start_y)
        for start_x in x_starts:
            if start_x < 0 or start_x >= image_width:
                raise ValueError(f"Invalid x start {start_x} for image width {image_width}.")
            tile_width = min(block_width, image_width - start_x)
            tiles.append(TileWindow(start_x=start_x, start_y=start_y, width=tile_width, height=tile_height))
    return tiles
```

- [ ] **Step 4: Add local-window support to `_paired_windows()`**

Modify `examples/image_match/tile_matching.py`:

```python
def _paired_windows(
    *,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    common_width: int,
    common_height: int,
    max_image_dimension: int,
    block_width: int,
    block_height: int,
    overlap_x: int,
    overlap_y: int,
    local_windows: list[TileWindow] | tuple[TileWindow, ...] | None = None,
) -> list[PairedTileWindow]:
    if common_width <= 0 or common_height <= 0:
        return []

    if local_windows is not None:
        resolved_local_windows = list(local_windows)
    elif requires_tiling(common_width, common_height, max_dimension=max_image_dimension):
        resolved_local_windows = generate_tiles(
            common_width,
            common_height,
            block_width=block_width,
            block_height=block_height,
            overlap_x=overlap_x,
            overlap_y=overlap_y,
        )
    else:
        resolved_local_windows = [_full_image_window(common_width, common_height)]

    return [
        PairedTileWindow(
            local_window=local_window,
            left_window=TileWindow(
                start_x=left_offset_x + local_window.start_x,
                start_y=left_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
            right_window=TileWindow(
                start_x=right_offset_x + local_window.start_x,
                start_y=right_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
        )
        for local_window in resolved_local_windows
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_block_alignment_unit_test -v
```

Expected: PASS, all 7 tests pass.

- [ ] **Step 6: Commit tiling integration**

```bash
git add examples/image_match/tiling.py examples/image_match/tile_matching.py tests/unitTest/controlnet_construct_tile_block_alignment_unit_test.py
git commit -m "feat(image-match): support precomputed aligned tile windows" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 3: Add TileCache diagnostics

**Files:**
- Modify: `examples/image_match/tile_cache.py`
- Test: `tests/unitTest/controlnet_construct_tile_cache_unit_test.py`

- [ ] **Step 1: Write failing diagnostics tests**

Append this test class to `tests/unitTest/controlnet_construct_tile_cache_unit_test.py`:

```python
class TestTileCacheDiagnostics(unittest.TestCase):
    def test_summary_reports_hits_misses_and_assembly(self):
        data = np.arange(64, dtype=np.float64).reshape((8, 8))
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                cache = TileCache(cube, cache_max_mb=10)
                cache.read_region(0, 0, 4, 4)
                cache.read_region(0, 0, 4, 4)
                summary = cache.summary()

                self.assertEqual(summary["read_window_count"], 2)
                self.assertEqual(summary["cache_miss_count"], 1)
                self.assertEqual(summary["cache_hit_count"], 1)
                self.assertEqual(summary["assembled_tile_reference_count"], 2)
                self.assertIn(summary["state"], {CacheState.WARMING_UP, CacheState.ACTIVE, CacheState.BYPASSED})
                self.assertGreaterEqual(summary["load_seconds"], 0.0)
                self.assertGreaterEqual(summary["assembly_seconds"], 0.0)
            finally:
                if cube.is_open():
                    cube.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_cache_unit_test.TestTileCacheDiagnostics -v
```

Expected: FAIL with `AttributeError: 'TileCache' object has no attribute 'summary'`.

- [ ] **Step 3: Add counters and summary method**

Modify `TileCache.__init__()` in `examples/image_match/tile_cache.py` by adding:

```python
        self._read_window_count = 0
        self._cache_hit_count = 0
        self._cache_miss_count = 0
        self._assembled_tile_reference_count = 0
        self._load_seconds = 0.0
        self._assembly_seconds = 0.0
```

Modify `read_region()` so it increments counters:

```python
        self._read_window_count += 1
        if self._state == CacheState.BYPASSED:
            return self._direct_read(x, y, w, h, band)

        start_col = x // self._tile_w
        end_col = (x + w - 1) // self._tile_w
        start_row = y // self._tile_h
        end_row = (y + h - 1) // self._tile_h

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                key = TileCoord(col, row, band)
                if key in self._cache:
                    self._cache_hit_count += 1
                    self._cache.move_to_end(key)
                else:
                    self._cache_miss_count += 1
                    self._load_tile(ip, col, row, band)
```

Modify `_load_tile()` after elapsed is computed:

```python
        self._load_seconds += elapsed
```

Wrap `_assemble()` with timing and tile-reference counting:

```python
        t0 = time.monotonic()
        output = np.zeros((h, w), dtype=np.float64)
        tile_reference_count = 0
```

Inside the `if dst_w > 0 and dst_h > 0:` block, add:

```python
                    tile_reference_count += 1
```

Before returning from `_assemble()`, add:

```python
        self._assembled_tile_reference_count += tile_reference_count
        self._assembly_seconds += time.monotonic() - t0
        return output
```

Add this method before `close()`:

```python
    def summary(self) -> dict[str, object]:
        """Return lightweight cache diagnostics for metadata and profiling."""
        return {
            "state": self._state,
            "tile_width": self._tile_w,
            "tile_height": self._tile_h,
            "cache_entry_count": len(self._cache),
            "cache_bytes": self._cache_bytes,
            "cache_max_bytes": self._cache_max_bytes,
            "read_window_count": self._read_window_count,
            "cache_hit_count": self._cache_hit_count,
            "cache_miss_count": self._cache_miss_count,
            "assembled_tile_reference_count": self._assembled_tile_reference_count,
            "load_seconds": self._load_seconds,
            "assembly_seconds": self._assembly_seconds,
        }
```

- [ ] **Step 4: Run diagnostics test**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_cache_unit_test.TestTileCacheDiagnostics -v
```

Expected: PASS.

- [ ] **Step 5: Run full tile-cache unit test module**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_tile_cache_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit diagnostics**

```bash
git add examples/image_match/tile_cache.py tests/unitTest/controlnet_construct_tile_cache_unit_test.py
git commit -m "feat(image-match): report tile cache diagnostics" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 4: Integrate alignment mode into `match_dom_pair()`

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `examples/controlnet_construct/parameter_catalog.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing metadata tests**

Add these tests near the other `match_dom_pair()` metadata tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
    def test_match_dom_pair_reports_tile_block_alignment_off_by_default(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_alignment_default.cub",
                right_name="right_alignment_default.cub",
            )

            _, _, summary = match_dom_pair(left_path, right_path, min_valid_pixels=8)

        alignment = summary["tile_block_alignment"]
        self.assertEqual(alignment["mode"], "off")
        self.assertFalse(alignment["aligned"])
        self.assertEqual(alignment["requested_block_width"], 1024)
        self.assertEqual(alignment["effective_block_width"], 1024)

    def test_match_dom_pair_auto_alignment_records_effective_geometry(self):
        image = _build_textured_test_image(128, 128)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_alignment_auto.cub",
                right_name="right_alignment_auto.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=30,
                block_height=30,
                overlap_x=4,
                overlap_y=4,
                min_valid_pixels=8,
                tile_block_alignment_mode="auto",
            )

        alignment = summary["tile_block_alignment"]
        self.assertEqual(alignment["mode"], "auto")
        self.assertIn("aligned", alignment)
        self.assertEqual(alignment["requested_block_width"], 30)
        self.assertEqual(alignment["requested_block_height"], 30)
        self.assertGreaterEqual(alignment["effective_block_width"], 30)
        self.assertGreaterEqual(alignment["effective_block_height"], 30)
        self.assertIn("left_storage_tile_width", alignment)
        self.assertIn("block_alignment_reason", summary)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_tile_block_alignment_off_by_default tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_auto_alignment_records_effective_geometry -v
```

Expected: FAIL because `tile_block_alignment` metadata and `tile_block_alignment_mode` parameter are not implemented.

- [ ] **Step 3: Import alignment helpers**

In both import branches of `examples/image_match/image_match.py`, import:

```python
    from image_match.tile_block_alignment import (
        DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES,
        normalize_tile_block_alignment_mode,
        resolve_tile_aligned_block_config,
        storage_tile_shape_from_cube,
    )
```

and in the package-relative branch:

```python
    from .tile_block_alignment import (
        DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES,
        normalize_tile_block_alignment_mode,
        resolve_tile_aligned_block_config,
        storage_tile_shape_from_cube,
    )
```

- [ ] **Step 4: Add parser helper and function parameter**

Add near other parse helpers:

```python
def _parse_tile_block_alignment_mode(value: str) -> str:
    try:
        return normalize_tile_block_alignment_mode(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
```

Add to `match_dom_pair()` parameters after `overlap_y`:

```python
    tile_block_alignment_mode: str = DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
```

Add to `match_dom_pair_to_key_files()` signature and pass-through call:

```python
    tile_block_alignment_mode: str = DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
```

and:

```python
        tile_block_alignment_mode=tile_block_alignment_mode,
```

- [ ] **Step 5: Resolve alignment after pair preparation**

In `match_dom_pair()`, after `preparation = prepare_dom_pair_for_matching(...)`, add:

```python
        resolved_tile_block_alignment_mode = normalize_tile_block_alignment_mode(tile_block_alignment_mode)
        tile_block_alignment = resolve_tile_aligned_block_config(
            mode=resolved_tile_block_alignment_mode,
            left_shape=storage_tile_shape_from_cube(left_cube),
            right_shape=storage_tile_shape_from_cube(right_cube),
            left_offset_x=preparation.left.offset_sample,
            left_offset_y=preparation.left.offset_line,
            right_offset_x=preparation.right.offset_sample,
            right_offset_y=preparation.right.offset_line,
            requested_block_width=block_width,
            requested_block_height=block_height,
            requested_overlap_x=overlap_x,
            requested_overlap_y=overlap_y,
            common_width=preparation.shared_width,
            common_height=preparation.shared_height,
        )
```

Modify the `_paired_windows()` call:

```python
            windows = _paired_windows(
                left_offset_x=preparation.left.offset_sample,
                left_offset_y=preparation.left.offset_line,
                right_offset_x=preparation.right.offset_sample,
                right_offset_y=preparation.right.offset_line,
                common_width=preparation.shared_width,
                common_height=preparation.shared_height,
                max_image_dimension=max_image_dimension,
                block_width=tile_block_alignment.effective_block_width,
                block_height=tile_block_alignment.effective_block_height,
                overlap_x=tile_block_alignment.effective_overlap_x,
                overlap_y=tile_block_alignment.effective_overlap_y,
                local_windows=tile_block_alignment.local_windows,
            )
```

Add summary fields:

```python
            "tile_block_alignment_mode": tile_block_alignment.mode,
            "block_alignment_reason": tile_block_alignment.reason,
            "tile_block_alignment": tile_block_alignment.to_metadata(),
```

- [ ] **Step 6: Add config and CLI parsing**

In `_load_config_defaults()` mapping near tile/cache options, add:

```python
        (
            "tile_block_alignment_mode",
            ("tile_block_alignment_mode", "tileBlockAlignmentMode", "TileBlockAlignmentMode"),
            lambda value: normalize_tile_block_alignment_mode(value),
        ),
```

In `build_argument_parser()`, add after overlap/block options:

```python
    parser.add_argument(
        "--tile-block-alignment-mode",
        type=_parse_tile_block_alignment_mode,
        default=DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        help=(
            "Full-resolution block alignment mode. "
            f"Supported values: {_format_supported_values(SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES)}. "
            f"Default: {DEFAULT_TILE_BLOCK_ALIGNMENT_MODE}."
        ),
    )
```

In `main()`, pass:

```python
        tile_block_alignment_mode=args.tile_block_alignment_mode,
```

- [ ] **Step 7: Update parameter catalog**

In `examples/controlnet_construct/parameter_catalog.py`, import fallback constants:

```python
    from image_match.tile_block_alignment import DEFAULT_TILE_BLOCK_ALIGNMENT_MODE, SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES
```

and fallback values in the `except ImportError` block:

```python
    DEFAULT_TILE_BLOCK_ALIGNMENT_MODE = "off"
    SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES = ("off", "auto", "isis-storage")
```

Add this spec after overlap specs:

```python
    _spec(
        "tile_block_alignment_mode",
        "tile",
        config_path=_image_match_path("tile_block_alignment_mode"),
        default=DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        allowed_values=tuple(SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES),
        entrypoints=_MATCH_ENTRYPOINTS,
        help="Full-resolution block alignment mode for ISIS storage tile boundaries.",
    ),
```

- [ ] **Step 8: Run metadata tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_tile_block_alignment_off_by_default tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_auto_alignment_records_effective_geometry -v
```

Expected: PASS.

- [ ] **Step 9: Commit pipeline integration**

```bash
git add examples/image_match/image_match.py examples/controlnet_construct/parameter_catalog.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat(image-match): expose ISIS tile block alignment mode" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 5: Record cache summaries in match metadata

**Files:**
- Modify: `examples/image_match/tile_matching.py`
- Modify: `examples/image_match/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing metadata test**

Add this test near the alignment metadata tests:

```python
    def test_match_dom_pair_reports_tile_cache_diagnostics_when_enabled(self):
        image = _build_textured_test_image(96, 96)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_cache_diag.cub",
                right_name="right_cache_diag.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=48,
                block_height=48,
                overlap_x=0,
                overlap_y=0,
                min_valid_pixels=8,
                use_parallel_cpu=False,
                use_tile_cache=True,
            )

        cache_summary = summary["tile_cache"]
        self.assertTrue(cache_summary["enabled"])
        self.assertIn("left", cache_summary)
        self.assertIn("right", cache_summary)
        self.assertGreaterEqual(cache_summary["left"]["read_window_count"], 1)
        self.assertGreaterEqual(cache_summary["right"]["read_window_count"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_tile_cache_diagnostics_when_enabled -v
```

Expected: FAIL because `summary["tile_cache"]` is missing.

- [ ] **Step 3: Return cache summaries from serial tile matching**

Add this dataclass to `examples/image_match/tile_matching.py` near `TileMatchResult`:

```python
@dataclass(frozen=True, slots=True)
class TileMatchBatchResult:
    results: list[TileMatchResult]
    tile_cache_summary: dict[str, object] | None = None
```

Update `_run_serial_tile_match_tasks()` to return `TileMatchBatchResult` and replace its final return:

```python
        cache_summary = None
        if use_tile_cache:
            cache_summary = {
                "enabled": True,
                "left": None if left_cache is None else left_cache.summary(),
                "right": None if right_cache is None else right_cache.summary(),
            }
        return TileMatchBatchResult(results=tile_results, tile_cache_summary=cache_summary)
```

For `_run_parallel_tile_match_tasks()`, keep returning a list for now and handle it as no shared summary in `image_match.py`.

- [ ] **Step 4: Normalize serial return in `image_match.py`**

In `run_tile_matching_pass()` inside `match_dom_pair()`, initialize:

```python
                        nonlocal parallel_cpu_used, parallel_cpu_backend, parallel_cpu_worker_count, tile_match_backend, tile_cache_summary
```

Before defining `run_tile_matching_pass()`, add:

```python
                    tile_cache_summary: dict[str, object] | None = None
```

In the serial path, replace:

```python
                            pass_results = _run_serial_tile_match_tasks(
```

with:

```python
                            serial_batch = _run_serial_tile_match_tasks(
```

and after the call:

```python
                            pass_results = serial_batch.results
                            tile_cache_summary = serial_batch.tile_cache_summary
```

In the final summary dictionary, add:

```python
            "tile_cache": tile_cache_summary if tile_cache_summary is not None else {"enabled": bool(use_tile_cache)},
```

- [ ] **Step 5: Run cache metadata test**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_dom_pair_reports_tile_cache_diagnostics_when_enabled -v
```

Expected: PASS.

- [ ] **Step 6: Commit cache metadata**

```bash
git add examples/image_match/tile_matching.py examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat(image-match): include tile cache diagnostics in metadata" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 6: Focused validation and benchmark guidance

**Files:**
- Modify only if previous tasks reveal direct test breakage in touched files.

- [ ] **Step 1: Run focused resolver and cache tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_tile_block_alignment_unit_test \
  tests.unitTest.controlnet_construct_tile_cache_unit_test \
  -v
```

Expected: PASS.

- [ ] **Step 2: Run focused matching tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS. If this module is too slow for the current machine, run the three new test methods by fully qualified name and record that full-module validation was deferred.

- [ ] **Step 3: Run smoke import**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 4: Commit validation-only fixes if needed**

Only run this if Step 1, Step 2, or Step 3 required a code/test fix:

```bash
git add examples/image_match examples/controlnet_construct tests/unitTest
git commit -m "fix(image-match): stabilize tile-alignment validation" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 5: Final handoff includes benchmark command template**

Include this template in the implementation handoff message:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/controlnet_construct/image_match.py LEFT.cub RIGHT.cub left.key right.key \
  --metadata-output aligned.json \
  --use-tile-cache \
  --tile-block-alignment-mode auto \
  --sub-block-size-x 1024 \
  --sub-block-size-y 1024 \
  --overlap-size-x 128 \
  --overlap-size-y 128
```

Compare that with `--tile-block-alignment-mode off` on the same pair and inspect `tile_block_alignment`, `tile_cache.left`, and `tile_cache.right` in the metadata JSON.

## Self-Review

- Spec coverage: Tasks 1-2 implement block alignment and absolute-offset handling; Task 3 implements diagnostics counters; Task 4 exposes API/CLI/config and metadata; Task 5 records cache summaries; Task 6 covers validation and benchmark guidance. C++ is explicitly deferred.
- Placeholder scan: no unresolved markers or unspecified implementation steps remain.
- Type consistency: `StorageTileShape`, `TileBlockAlignmentResult`, `TileMatchBatchResult`, `tile_block_alignment_mode`, and metadata keys are named consistently across tasks.
