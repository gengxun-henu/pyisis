# Tile-Aware Image I/O Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an optional tile-aware read cache that reduces disk I/O for large DOM image matching by reading at ISIS storage tile granularity with LRU memory caching and automatic throughput-based bypass.

**Architecture:** A Python `TileCache` class in `tile_cache.py` that wraps cube reads at tile granularity. Existing `_read_cube_window` functions remain unchanged. The cache is enabled via JSON config and activated through a `make_read_fn` factory at orchestration points in `tile_matching.py`, `tile_validity.py`, and `image_match.py`.

**Tech Stack:** Python 3.10+, NumPy, ISIS pybind11 (`ip.Brick`, `ip.Cube`, `ip.LineManager`, `ip.Format.Tile`), `collections.OrderedDict`

---

### File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tests/unitTest/_unit_test_support.py` | Modify | Add `make_tile_test_cube()` helper for tile-format cubes with known data |
| `examples/controlnet_construct/tile_cache.py` | Create | `TileCache` class, `CacheState` enum, `TileCoord`, `make_read_fn` factory |
| `tests/unitTest/controlnet_construct_tile_cache_unit_test.py` | Create | Unit tests for TileCache |
| `examples/controlnet_construct/tile_matching.py` | Modify | Add cache parameters to serial and batch worker paths |
| `examples/controlnet_construct/tile_validity.py` | Modify | Add cache parameter to `_compute_tile_validity_index` |
| `examples/controlnet_construct/image_match.py` | Modify | Add config fields, pass cache params to orchestration |

---

### Task 1: Test Helper for Tile-Format Cubes

The existing `make_test_cube` in `_unit_test_support.py` does not support tile dimensions or data injection. We need a new helper.

**Files:**
- Modify: `tests/unitTest/_unit_test_support.py` (append after `make_filled_cube`)

- [ ] **Step 1: Add `make_tile_test_cube` helper**

Append to `tests/unitTest/_unit_test_support.py` after the `make_filled_cube` function:

```python
def make_tile_test_cube(
    temp_dir,
    data: "np.ndarray",
    tile_samples: int,
    tile_lines: int,
    name: str = "test.cub",
) -> tuple:
    """Create a tile-format ISIS cube with known data.

    Args:
        temp_dir: temporary directory (Path)
        data: 2D numpy array (lines x samples) of float64 values
        tile_samples: tile width in samples
        tile_lines: tile height in lines
        name: output filename

    Returns:
        (cube, cube_path) — the cube is open and writable.
    """
    lines, samples = data.shape
    bands = 1

    cube_path = temp_dir / name
    cube = ip.Cube()
    cube.set_dimensions(samples, lines, bands)
    cube.set_pixel_type(ip.PixelType.Real)
    cube.set_format(ip.Format.Tile)
    cube.create(str(cube_path))

    # Write tile dimension keywords into the Core group.
    core = ip.PvlGroup("Core")
    core.add_keyword(ip.PvlKeyword("StartByte", str(cube.labelSize(actual=True))))
    core.add_keyword(ip.PvlKeyword("Format", "Tile"))
    core.add_keyword(ip.PvlKeyword("TileSamples", str(tile_samples)))
    core.add_keyword(ip.PvlKeyword("TileLines", str(tile_lines)))
    cube.put_group(core)

    # Fill data line by line.
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(data[line_index, index])
        cube.write(manager)
        manager.next()

    return cube, cube_path
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/high_level_cube_io_unit_test.py -v -k "test" --timeout=60 2>&1 | head -30
```

Expected: existing tests pass (no regression from the appended helper).

---

### Task 2: TileCache Core Class

**Files:**
- Create: `examples/controlnet_construct/tile_cache.py`
- Create: `tests/unitTest/controlnet_construct_tile_cache_unit_test.py`

- [ ] **Step 1: Write `tile_cache.py`**

Create the complete `examples/controlnet_construct/tile_cache.py`:

```python
"""Tile-aware image I/O cache for ISIS cube reads.

Reads data at ISIS storage tile granularity, caches tiles in memory
with LRU eviction, and self-evaluates throughput to decide whether
caching is beneficial.

Author: Geng Xun
Created: 2026-05-05
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
import math
import time
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TileCoord:
    """Cache key: tile column, row, and band."""
    col: int
    row: int
    band: int


class CacheState:
    """Possible states for the adaptive cache controller."""
    WARMING_UP = "warming_up"
    ACTIVE = "active"
    BYPASSED = "bypassed"


class TileCache:
    """Tile-aware read cache for ISIS cubes.

    Reads storage tiles from disk and caches them in memory.
    Automatically evaluates disk throughput during warmup and
    may switch to direct reads if the disk is fast enough.
    """

    def __init__(
        self,
        cube: Any,
        *,
        cache_max_mb: int = 100,
        adaptive_warmup_count: int = 10,
        adaptive_throughput_threshold_mbps: float = 200.0,
        adaptive_recheck_every: int = 0,
    ) -> None:
        self._cube = cube
        self._cache_max_bytes = cache_max_mb * 1024 * 1024

        # Read tile dimensions from the cube's Core group labels.
        core = cube.group("Core")
        self._tile_w = int(core["TileSamples"][0])
        self._tile_h = int(core["TileLines"][0])
        self._cube_w = int(cube.sample_count())
        self._cube_h = int(cube.line_count())

        # LRU cache: OrderedDict with move_to_end semantics.
        self._cache: OrderedDict[TileCoord, np.ndarray] = OrderedDict()
        self._cache_bytes: int = 0

        # Adaptive state.
        self._state = CacheState.WARMING_UP
        self._warmup_count = 0
        self._max_warmup = adaptive_warmup_count
        self._total_warmup_bytes: int = 0
        self._total_warmup_seconds: float = 0.0
        self._throughput_threshold = adaptive_throughput_threshold_mbps
        self._recheck_every = adaptive_recheck_every
        self._reads_since_recheck: int = 0

    def read_region(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        band: int = 1,
    ) -> np.ndarray:
        """Read a rectangular region from the cube, using tile cache."""
        import isis_pybind as ip

        # Fast path: bypassed.
        if self._state == CacheState.BYPASSED:
            return self._direct_read(x, y, w, h, band)

        # Compute covered tile range.
        start_col = x // self._tile_w
        end_col = (x + w - 1) // self._tile_w
        start_row = y // self._tile_h
        end_row = (y + h - 1) // self._tile_h

        # Ensure all tiles are cached.
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                key = TileCoord(col, row, band)
                if key not in self._cache:
                    self._load_tile(ip, col, row, band)

        # Assemble output from cached tiles.
        return self._assemble(x, y, w, h, start_col, end_col, start_row, end_row, band)

    def _load_tile(
        self,
        ip: Any,
        col: int,
        row: int,
        band: int,
    ) -> None:
        """Read a full storage tile from disk and cache it."""
        tile_x = col * self._tile_w
        tile_y = row * self._tile_h
        tile_w = min(self._tile_w, self._cube_w - tile_x)
        tile_h = min(self._tile_h, self._cube_h - tile_y)

        t0 = time.monotonic()
        brick = ip.Brick(self._cube, tile_w, tile_h, 1)
        brick.set_base_position(tile_x + 1, tile_y + 1, band)
        self._cube.read(brick)
        tile_data = np.asarray(brick.double_buffer(), dtype=np.float64).reshape((tile_h, tile_w))
        elapsed = time.monotonic() - t0

        key = TileCoord(col, row, band)
        self._cache[key] = tile_data
        self._cache_bytes += tile_data.nbytes

        # LRU eviction.
        while self._cache_bytes > self._cache_max_bytes:
            _, evicted = self._cache.popitem(last=False)
            self._cache_bytes -= evicted.nbytes

        # Warmup tracking.
        if self._state == CacheState.WARMING_UP:
            self._warmup_count += 1
            self._total_warmup_bytes += tile_data.nbytes
            self._total_warmup_seconds += elapsed

            if self._warmup_count >= self._max_warmup:
                self._decide_state()

        # Recheck tracking in ACTIVE state.
        if self._state == CacheState.ACTIVE and self._recheck_every > 0:
            self._reads_since_recheck += 1
            if self._reads_since_recheck >= self._recheck_every:
                self._reads_since_recheck = 0
                if self._total_warmup_seconds > 0:
                    avg_mbps = self._total_warmup_bytes / self._total_warmup_seconds / 1_048_576
                    if avg_mbps >= self._throughput_threshold:
                        self._state = CacheState.BYPASSED

    def _decide_state(self) -> None:
        """Evaluate warmup data and decide cache state."""
        if self._total_warmup_seconds <= 0:
            self._state = CacheState.BYPASSED
            return
        avg_mbps = self._total_warmup_bytes / self._total_warmup_seconds / 1_048_576
        if avg_mbps >= self._throughput_threshold:
            self._state = CacheState.BYPASSED
        else:
            self._state = CacheState.ACTIVE

    def _assemble(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        start_col: int,
        end_col: int,
        start_row: int,
        end_row: int,
        band: int,
    ) -> np.ndarray:
        """Assemble the output region from cached tile data."""
        output = np.zeros((h, w), dtype=np.float64)

        for row in range(start_row, end_row + 1):
            tile_y = row * self._tile_h
            tile_h_actual = min(self._tile_h, self._cube_h - tile_y)

            for col in range(start_col, end_col + 1):
                tile_x = col * self._tile_w
                tile_w_actual = min(self._tile_w, self._cube_w - tile_x)

                key = TileCoord(col, row, band)
                tile_data = self._cache[key]

                # Overlap between tile and requested region.
                src_x0 = max(0, x - tile_x)
                src_y0 = max(0, y - tile_y)
                src_x1 = min(tile_w_actual, x + w - tile_x)
                src_y1 = min(tile_h_actual, y + h - tile_y)

                dst_x0 = max(0, tile_x - x)
                dst_y0 = max(0, tile_y - y)
                dst_w = src_x1 - src_x0
                dst_h = src_y1 - src_y0

                if dst_w > 0 and dst_h > 0:
                    output[dst_y0:dst_y0 + dst_h, dst_x0:dst_x0 + dst_w] = \
                        tile_data[src_y0:src_y1, src_x0:src_x1]

        return output

    def _direct_read(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        band: int,
    ) -> np.ndarray:
        """Direct brick read without caching (BYPASSED state)."""
        import isis_pybind as ip
        brick = ip.Brick(self._cube, w, h, 1)
        brick.set_base_position(x + 1, y + 1, band)
        self._cube.read(brick)
        return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((h, w))

    def close(self) -> None:
        """Release cached data. Does NOT close the underlying cube."""
        self._cache.clear()
        self._cache_bytes = 0


def make_read_fn(
    cube: Any,
    *,
    use_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> tuple[Callable[[int, int, int, int, int], np.ndarray], "TileCache | None"]:
    """Factory: return (read_fn, cache_or_none).

    When use_cache=False, the returned function delegates to the
    existing _read_cube_window pattern. When use_cache=True, it
    returns the TileCache.read_region method.

    The caller is responsible for calling cache.close() when done.
    """
    import isis_pybind as ip

    if not use_cache:
        def direct_read(x: int, y: int, w: int, h: int, band: int = 1) -> np.ndarray:
            brick = ip.Brick(cube, w, h, 1)
            brick.set_base_position(x + 1, y + 1, band)
            cube.read(brick)
            return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((h, w))
        return direct_read, None

    cache = TileCache(
        cube,
        cache_max_mb=cache_max_mb,
        adaptive_warmup_count=adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=adaptive_recheck_every,
    )
    return cache.read_region, cache
```

- [ ] **Step 2: Write unit tests**

Create `tests/unitTest/controlnet_construct_tile_cache_unit_test.py`:

```python
"""Unit tests for tile_cache.py — TileCache LRU, adaptive bypass, and assembly.

Author: Geng Xun
Created: 2026-05-05
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

from _unit_test_support import ip, make_tile_test_cube, temporary_directory  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

tile_cache_mod = importlib.import_module("controlnet_construct.tile_cache")
TileCache = tile_cache_mod.TileCache
TileCoord = tile_cache_mod.TileCoord
CacheState = tile_cache_mod.CacheState
make_read_fn = tile_cache_mod.make_read_fn


class TestTileCoord(unittest.TestCase):
    def test_tile_coord_is_hashable(self):
        c1 = TileCoord(0, 0, 1)
        c2 = TileCoord(0, 0, 1)
        c3 = TileCoord(1, 0, 1)
        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)
        d = {c1: "a"}
        self.assertEqual(d[c2], "a")


class TestTileCacheTileDimensions(unittest.TestCase):
    """Test that TileCache correctly reads tile dimensions from cube labels."""

    def test_tile_dimensions_from_cube(self):
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, np.zeros((8, 8)), tile_samples=4, tile_lines=4)
            try:
                cache = TileCache(cube, cache_max_mb=10)
                self.assertEqual(cache._tile_w, 4)
                self.assertEqual(cache._tile_h, 4)
                self.assertEqual(cache._cube_w, 8)
                self.assertEqual(cache._cube_h, 8)
            finally:
                if cube.is_open():
                    cube.close()


class TestTileCacheReadRegion(unittest.TestCase):
    """Test read_region assembly from cached tiles."""

    def _make_cube_with_data(self, data, tile_samples, tile_lines):
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=tile_samples, tile_lines=tile_lines)
            return cube

    def test_single_tile_read(self):
        """Reading a region within one tile should return correct data."""
        data = np.arange(64, dtype=np.float64).reshape((8, 8))
        cube = self._make_cube_with_data(data, tile_samples=8, tile_lines=8)
        try:
            cache = TileCache(cube, cache_max_mb=10)
            result = cache.read_region(0, 0, 4, 4)
            np.testing.assert_array_equal(result, data[0:4, 0:4])
        finally:
            if cube.is_open():
                cube.close()

    def test_multi_tile_assembly(self):
        """Reading across tile boundary should assemble correctly."""
        data = np.arange(64, dtype=np.float64).reshape((8, 8))
        cube = self._make_cube_with_data(data, tile_samples=4, tile_lines=4)
        try:
            cache = TileCache(cube, cache_max_mb=10)
            # Read across tile boundary: covers tiles (0,0), (1,0), (0,1), (1,1)
            result = cache.read_region(2, 2, 4, 4)
            np.testing.assert_array_equal(result, data[2:6, 2:6])
        finally:
            if cube.is_open():
                cube.close()

    def test_edge_tile_read(self):
        """Reading near image edge should handle partial tiles."""
        data = np.arange(30, dtype=np.float64).reshape((5, 6))
        cube = self._make_cube_with_data(data, tile_samples=4, tile_lines=4)
        try:
            cache = TileCache(cube, cache_max_mb=10)
            # Read last 2 rows and 3 cols — crosses tile boundaries
            result = cache.read_region(3, 3, 3, 2)
            np.testing.assert_array_equal(result, data[3:5, 3:6])
        finally:
            if cube.is_open():
                cube.close()


class TestTileCacheLRU(unittest.TestCase):
    """Test LRU eviction behavior."""

    def test_lru_evicts_oldest(self):
        """When cache is full, oldest tile should be evicted."""
        data = np.arange(64, dtype=np.float64).reshape((8, 8))
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                cache = TileCache(cube, cache_max_mb=1)
                # 4 tiles of 4x4, each tile = 4*4*8 = 128 bytes
                # Set cache to exactly 3 tiles (384 bytes).
                cache._cache_max_bytes = 384

                # Read 3 tiles — should all be cached.
                cache.read_region(0, 0, 4, 4)   # tile (0,0)
                cache.read_region(4, 0, 4, 4)   # tile (1,0)
                cache.read_region(0, 4, 4, 4)   # tile (0,1)
                self.assertEqual(len(cache._cache), 3)

                # Read 4th tile — should evict oldest (0,0).
                cache.read_region(4, 4, 4, 4)   # tile (1,1)
                self.assertEqual(len(cache._cache), 3)
                self.assertNotIn(TileCoord(0, 0, 1), cache._cache)
                self.assertIn(TileCoord(1, 0, 1), cache._cache)
            finally:
                if cube.is_open():
                    cube.close()


class TestTileCacheAdaptiveBypass(unittest.TestCase):
    """Test adaptive warmup -> bypass decision."""

    def test_fast_disk_triggers_bypass(self):
        """Very low threshold should trigger BYPASSED state."""
        data = np.zeros((16, 16), dtype=np.float64)
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                cache = TileCache(
                    cube,
                    cache_max_mb=10,
                    adaptive_warmup_count=3,
                    adaptive_throughput_threshold_mbps=0.0001,
                )
                for i in range(3):
                    cache.read_region(i * 4, 0, 4, 4)
                self.assertEqual(cache._state, CacheState.BYPASSED)
            finally:
                if cube.is_open():
                    cube.close()

    def test_slow_disk_stays_active(self):
        """Very high threshold should keep cache ACTIVE."""
        data = np.zeros((16, 16), dtype=np.float64)
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                cache = TileCache(
                    cube,
                    cache_max_mb=10,
                    adaptive_warmup_count=3,
                    adaptive_throughput_threshold_mbps=1e15,
                )
                for i in range(3):
                    cache.read_region(i * 4, 0, 4, 4)
                self.assertEqual(cache._state, CacheState.ACTIVE)
            finally:
                if cube.is_open():
                    cube.close()


class TestMakeReadFn(unittest.TestCase):
    """Test the make_read_fn factory."""

    def test_without_cache_returns_direct_read(self):
        data = np.arange(16, dtype=np.float64).reshape((4, 4))
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                read_fn, cache = make_read_fn(cube, use_cache=False)
                self.assertIsNone(cache)
                result = read_fn(0, 0, 2, 2)
                np.testing.assert_array_equal(result, data[0:2, 0:2])
            finally:
                if cube.is_open():
                    cube.close()

    def test_with_cache_returns_tilecache(self):
        data = np.arange(16, dtype=np.float64).reshape((4, 4))
        with temporary_directory() as tmp:
            cube, _ = make_tile_test_cube(tmp, data, tile_samples=4, tile_lines=4)
            try:
                read_fn, cache = make_read_fn(cube, use_cache=True)
                self.assertIsInstance(cache, TileCache)
                result = read_fn(0, 0, 2, 2)
                np.testing.assert_array_equal(result, data[0:2, 0:2])
                cache.close()
            finally:
                if cube.is_open():
                    cube.close()
```

- [ ] **Step 3: Run tests**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/controlnet_construct_tile_cache_unit_test.py -v 2>&1 | tail -30
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add examples/controlnet_construct/tile_cache.py tests/unitTest/_unit_test_support.py tests/unitTest/controlnet_construct_tile_cache_unit_test.py
git commit -m "feat: add tile-aware image I/O cache with LRU and adaptive bypass

Add TileCache class that reads ISIS cubes at storage tile granularity
with in-memory LRU caching. Includes adaptive throughput evaluation
that bypasses caching on fast disks (e.g. SSD). Add make_tile_test_cube
helper for creating tile-format test cubes with known data.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Integrate Cache into `tile_matching.py`

**Files:**
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: Add import for make_read_fn**

In `tile_matching.py`, after the existing imports (around line 23, after `from .runtime import bootstrap_runtime_environment`):

```python
from .tile_cache import make_read_fn, TileCache
```

- [ ] **Step 2: Modify `_match_tile_task_with_open_cubes` to accept read functions**

Current signature (line 601-608):
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
```

Replace with:
```python
def _match_tile_task_with_open_cubes(
    task: TileMatchTask,
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    read_fn: Callable[[Any, TileWindow, int], np.ndarray] | None = None,
) -> TileMatchResult:
    _read = read_fn if read_fn is not None else _read_cube_window
    left_values = _read(left_cube, task.paired_window.left_window, band=task.band)
    right_values = _read(right_cube, task.paired_window.right_window, band=task.band)
```

Add the import at the top of the file:
```python
from typing import Any, Callable
```
(Verify `Callable` is not already imported. If `Callable` is already imported via `collections.abc`, adjust accordingly.)

- [ ] **Step 3: Create a cache-aware read wrapper function**

Add this helper function before `_match_tile_task_with_open_cubes`:

```python
def _make_tile_read_fn(
    cube: ip.Cube,
    *,
    use_tile_cache: bool,
    cache_max_mb: int,
    adaptive_warmup_count: int,
    adaptive_throughput_threshold_mbps: float,
    adaptive_recheck_every: int,
) -> tuple[Callable[[Any, TileWindow, int], np.ndarray], TileCache | None]:
    """Create a read function compatible with _match_tile_task_with_open_cubes."""
    read_fn_or_method, cache = make_read_fn(
        cube,
        use_cache=use_tile_cache,
        cache_max_mb=cache_max_mb,
        adaptive_warmup_count=adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=adaptive_recheck_every,
    )

    if use_tile_cache and cache is not None:
        # TileCache.read_region takes (x, y, w, h, band).
        # We need a wrapper that takes (cube, window, band).
        def cached_read(cube: Any, window: TileWindow, band: int) -> np.ndarray:
            return read_fn_or_method(
                window.start_x, window.start_y, window.width, window.height, band,
            )
        return cached_read, cache
    else:
        return _read_cube_window, None
```

- [ ] **Step 4: Modify `_match_single_paired_window_worker` to use cache**

Current code (lines 637-656):
```python
def _match_single_paired_window_worker(task: TileMatchTask) -> TileMatchResult:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(task.left_dom_path, "r")
    right_cube.open(task.right_dom_path, "r")
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, task.invalid_values)
        return _match_tile_task_with_open_cubes(
            task,
            left_cube=left_cube,
            right_cube=right_cube,
            left_invalid_values=left_invalid_values,
            right_invalid_values=right_invalid_values,
        )
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()
```

Replace with:
```python
def _match_single_paired_window_worker(
    task: TileMatchTask,
    *,
    use_tile_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> TileMatchResult:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(task.left_dom_path, "r")
    right_cube.open(task.right_dom_path, "r")
    left_cache: TileCache | None = None
    right_cache: TileCache | None = None
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, task.invalid_values)
        left_read_fn, left_cache = _make_tile_read_fn(
            left_cube,
            use_tile_cache=use_tile_cache,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        right_read_fn, right_cache = _make_tile_read_fn(
            right_cube,
            use_tile_cache=use_tile_cache,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        # Single-task worker: pass left read_fn only (right is read symmetrically).
        # Since _match_tile_task_with_open_cubes uses one read_fn for both cubes,
        # we need separate reads. Create a combined wrapper.
        def combined_read(cube: Any, window: TileWindow, band: int) -> np.ndarray:
            if cube is left_cube:
                return left_read_fn(cube, window, band)
            return right_read_fn(cube, window, band)

        return _match_tile_task_with_open_cubes(
            task,
            left_cube=left_cube,
            right_cube=right_cube,
            left_invalid_values=left_invalid_values,
            right_invalid_values=right_invalid_values,
            read_fn=combined_read if use_tile_cache else None,
        )
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()
        if left_cache is not None:
            left_cache.close()
        if right_cache is not None:
            right_cache.close()
```

- [ ] **Step 5: Modify `_match_tile_task_batch_worker` to use cache**

Current code (lines 776-812):
```python
def _match_tile_task_batch_worker(
    indexed_tasks: tuple[IndexedTileMatchTask | tuple[int, dict[str, Any]], ...],
    progress_queue: Any | None = None,
) -> tuple[tuple[int, TileMatchResult], ...]:
    if not indexed_tasks:
        return ()
    resolved_indexed_tasks = tuple(_indexed_tile_match_task_from_payload(indexed_task) for indexed_task in indexed_tasks)
    first_task = resolved_indexed_tasks[0].task
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(first_task.left_dom_path, "r")
    right_cube.open(first_task.right_dom_path, "r")
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, first_task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, first_task.invalid_values)
        results: list[tuple[int, TileMatchResult]] = []
        for indexed_task in resolved_indexed_tasks:
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
            if progress_queue is not None:
                progress_queue.put(1)
        return tuple(results)
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()
```

Replace with:
```python
def _match_tile_task_batch_worker(
    indexed_tasks: tuple[IndexedTileMatchTask | tuple[int, dict[str, Any]], ...],
    progress_queue: Any | None = None,
    *,
    use_tile_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> tuple[tuple[int, TileMatchResult], ...]:
    if not indexed_tasks:
        return ()
    resolved_indexed_tasks = tuple(_indexed_tile_match_task_from_payload(indexed_task) for indexed_task in indexed_tasks)
    first_task = resolved_indexed_tasks[0].task
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(first_task.left_dom_path, "r")
    right_cube.open(first_task.right_dom_path, "r")
    left_cache: TileCache | None = None
    right_cache: TileCache | None = None
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, first_task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, first_task.invalid_values)
        left_read_fn, left_cache = _make_tile_read_fn(
            left_cube,
            use_tile_cache=use_tile_cache,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        right_read_fn, right_cache = _make_tile_read_fn(
            right_cube,
            use_tile_cache=use_tile_cache,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        def combined_read(cube: Any, window: TileWindow, band: int) -> np.ndarray:
            if cube is left_cube:
                return left_read_fn(cube, window, band)
            return right_read_fn(cube, window, band)

        read_fn = combined_read if use_tile_cache else None
        results: list[tuple[int, TileMatchResult]] = []
        for indexed_task in resolved_indexed_tasks:
            results.append(
                (
                    indexed_task.index,
                    _match_tile_task_with_open_cubes(
                        indexed_task.task,
                        left_cube=left_cube,
                        right_cube=right_cube,
                        left_invalid_values=left_invalid_values,
                        right_invalid_values=right_invalid_values,
                        read_fn=read_fn,
                    ),
                )
            )
            if progress_queue is not None:
                progress_queue.put(1)
        return tuple(results)
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()
        if left_cache is not None:
            left_cache.close()
        if right_cache is not None:
            right_cache.close()
```

- [ ] **Step 6: Modify `_run_parallel_tile_match_tasks` to pass cache config to workers**

Current code (line 815-819):
```python
def _run_parallel_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    max_workers: int,
    progress_callback: Callable[[], None] | None = None,
) -> list[TileMatchResult]:
```

Add cache parameters:
```python
def _run_parallel_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    max_workers: int,
    progress_callback: Callable[[], None] | None = None,
    use_tile_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> list[TileMatchResult]:
```

Find where `_match_tile_task_batch_worker` is called via `executor.submit` or `executor.map`. Look for the call pattern in this function. The worker is invoked with `functools.partial` or directly. Pass the cache kwargs through.

Search for `_match_tile_task_batch_worker` call in `_run_parallel_tile_match_tasks`:

The call is likely through `executor.submit` or `executor.map`. Add a `functools.partial` wrapper:

```python
# Inside _run_parallel_tile_match_tasks, where the worker is submitted:
worker_fn = functools.partial(
    _match_tile_task_batch_worker,
    use_tile_cache=use_tile_cache,
    cache_max_mb=cache_max_mb,
    adaptive_warmup_count=adaptive_warmup_count,
    adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
    adaptive_recheck_every=adaptive_recheck_every,
)
```

If `functools` is not imported, add:
```python
import functools
```
at the top of the file.

- [ ] **Step 7: Modify `_run_serial_tile_match_tasks` to accept cache params**

Current signature (check the function definition around line 860+):
```python
def _run_serial_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    ...
) -> list[TileMatchResult]:
```

Add cache parameters and internal cache creation. The function calls `_read_cube_window` directly. Replace the direct call with a cached read path.

Add parameters to the function signature:
```python
def _run_serial_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
    progress_callback: Callable[[], None] | None = None,
    use_tile_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> list[TileMatchResult]:
```

Inside the function body, before the loop:
```python
    left_cache: TileCache | None = None
    right_cache: TileCache | None = None
    if use_tile_cache:
        left_read_fn, left_cache = _make_tile_read_fn(
            left_cube,
            use_tile_cache=True,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        right_read_fn, right_cache = _make_tile_read_fn(
            right_cube,
            use_tile_cache=True,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
        def combined_read(cube: Any, window: TileWindow, band: int) -> np.ndarray:
            if cube is left_cube:
                return left_read_fn(cube, window, band)
            return right_read_fn(cube, window, band)
    else:
        combined_read = None
    try:
        ...  # existing loop body
```

And in the loop where `left_values = _read_cube_window(left_cube, ...)` appears:
```python
    # Replace both occurrences of:
    #   left_values = _read_cube_window(left_cube, paired_window.left_window, band=band)
    #   right_values = _read_cube_window(right_cube, paired_window.right_window, band=band)
    # With:
    if combined_read is not None:
        left_values = combined_read(left_cube, paired_window.left_window, band)
        right_values = combined_read(right_cube, paired_window.right_window, band)
    else:
        left_values = _read_cube_window(left_cube, paired_window.left_window, band=band)
        right_values = _read_cube_window(right_cube, paired_window.right_window, band=band)
```

Wrap the entire function body in a try/finally to clean up caches:
```python
    try:
        tile_results: list[TileMatchResult] = []
        for paired_window in windows:
            # ... existing body with conditional read ...
        return tile_results
    finally:
        if left_cache is not None:
            left_cache.close()
        if right_cache is not None:
            right_cache.close()
```

- [ ] **Step 8: Run existing tests to verify no regression**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/controlnet_construct_matching_unit_test.py -v -k "serial or batch" --timeout=120 2>&1 | tail -30
```

Expected: All existing serial/batch tests PASS (default `use_tile_cache=False` means no behavior change).

- [ ] **Step 9: Commit**

```bash
git add examples/controlnet_construct/tile_matching.py
git commit -m "feat: integrate tile cache into serial and batch matching paths

Add optional tile-aware caching to _run_serial_tile_match_tasks,
_match_tile_task_batch_worker, and _match_single_paired_window_worker.
Default is use_tile_cache=False, so existing behavior is unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Integrate Cache into `tile_validity.py`

**Files:**
- Modify: `examples/controlnet_construct/tile_validity.py`

- [ ] **Step 1: Add import**

After existing imports (around line 20):
```python
from .tile_cache import make_read_fn, TileCache
```

- [ ] **Step 2: Add cache parameter to `_compute_tile_validity_index`**

Find the function `_compute_tile_validity_index` (around line 468+). Add a `use_tile_cache` parameter with cache config:

```python
def _compute_tile_validity_index(
    *,
    cube: Any,
    dom_path: str | Path,
    image_width: int,
    image_height: int,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    manifest: dict[str, object],
    use_tile_cache: bool = False,
    cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
) -> TileValidityIndex:
```

- [ ] **Step 3: Add cache creation at function start**

After the local variable setup (around the `valid_counts = np.zeros(...)` line):

```python
    cache: TileCache | None = None
    if use_tile_cache:
        _, cache = make_read_fn(
            cube,
            use_cache=True,
            cache_max_mb=cache_max_mb,
            adaptive_warmup_count=adaptive_warmup_count,
            adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
            adaptive_recheck_every=adaptive_recheck_every,
        )
    try:
```

- [ ] **Step 4: Replace `_read_cube_window_for_validity` call with cached version**

Find the call site (line 514):
```python
            values = _read_cube_window_for_validity(cube, read_window, band=band)
```

Replace with:
```python
            if cache is not None:
                values = cache.read_region(
                    read_window.start_x, read_window.start_y,
                    read_window.width, read_window.height, band=band,
                )
            else:
                values = _read_cube_window_for_validity(cube, read_window, band=band)
```

- [ ] **Step 5: Add cache cleanup at function end**

Wrap the computation loop in the try/finally:

```python
    try:
        for cell_y in range(grid_height):
            for cell_x in range(grid_width):
                # ... existing loop body with conditional read ...
    finally:
        if cache is not None:
            cache.close()

    return TileValidityIndex(...)
```

- [ ] **Step 6: Run existing tests**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/ -v -k "validity" --timeout=120 2>&1 | tail -30
```

Expected: All existing validity tests PASS (default `use_tile_cache=False` means no behavior change).

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/tile_validity.py
git commit -m "feat: add optional tile cache to validity index computation

Integrate TileCache into _compute_tile_validity_index with opt-in
parameter. Default path uses existing _read_cube_window_for_validity.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Wire Cache Config into `image_match.py`

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add config field specs**

In the `field_specs` tuple (around line 449-519), after the existing config fields (around line 530 area), add:

```python
        (
            "use_tile_cache",
            ("use_tile_cache", "useTileCache", "UseTileCache"),
            lambda value: _coerce_config_bool(value, field_name="use_tile_cache"),
        ),
        ("tile_cache_max_mb", ("tile_cache_max_mb", "tileCacheMaxMb", "TileCacheMaxMb"), lambda value: int(value)),
        (
            "adaptive_warmup_count",
            ("adaptive_warmup_count", "adaptiveWarmupCount", "AdaptiveWarmupCount"),
            lambda value: int(value),
        ),
        (
            "adaptive_throughput_threshold_mbps",
            ("adaptive_throughput_threshold_mbps", "adaptiveThroughputThresholdMbps", "AdaptiveThroughputThresholdMbps"),
            lambda value: float(value),
        ),
        (
            "adaptive_recheck_every",
            ("adaptive_recheck_every", "adaptiveRecheckEvery", "AdaptiveRecheckEvery"),
            lambda value: int(value),
        ),
```

- [ ] **Step 2: Add parameters to `match_dom_pair` function signature**

After the last parameter (`show_progress: bool = False,`):

```python
    use_tile_cache: bool = False,
    tile_cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
```

- [ ] **Step 3: Pass cache params to `_run_serial_tile_match_tasks`**

Find the two calls to `_run_serial_tile_match_tasks` (around lines 1110 and 1140). Add cache parameters to both calls:

```python
    tile_results = _run_serial_tile_match_tasks(
        candidate_windows,
        left_cube=left_cube,
        right_cube=right_cube,
        band=band,
        # ... all existing params ...
        progress_callback=progress_bar.update if progress_bar is not None else None,
        use_tile_cache=use_tile_cache,
        cache_max_mb=tile_cache_max_mb,
        adaptive_warmup_count=adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=adaptive_recheck_every,
    )
```

- [ ] **Step 4: Pass cache params to `_run_parallel_tile_match_tasks`**

Find the call to `_run_parallel_tile_match_tasks` (around line 1076). Add cache parameters:

```python
    tile_results = _run_parallel_tile_match_tasks(
        _build_tile_match_tasks(...),
        max_workers=candidate_worker_count,
        progress_callback=progress_bar.update if progress_bar is not None else None,
        use_tile_cache=use_tile_cache,
        cache_max_mb=tile_cache_max_mb,
        adaptive_warmup_count=adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=adaptive_recheck_every,
    )
```

- [ ] **Step 5: Pass cache params to `_compute_tile_validity_index`**

Find where `ensure_dom_validity_index` is called (around lines 1028-1048). Add cache parameters to both left and right calls:

```python
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
        use_tile_cache=use_tile_cache,
        cache_max_mb=tile_cache_max_mb,
        adaptive_warmup_count=adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=adaptive_recheck_every,
    )
```

Same for `right_tile_validity_index`.

- [ ] **Step 6: Propagate cache params through `ensure_dom_validity_index`**

Find the `ensure_dom_validity_index` function in `tile_validity.py` (search for `def ensure_dom_validity_index`). Add cache parameters to its signature and pass them through to `_compute_tile_validity_index`.

- [ ] **Step 7: Add CLI argument**

In the CLI argument parser (`build_argument_parser` function), add:

```python
    parser.add_argument(
        "--use-tile-cache",
        action="store_true",
        default=False,
        help="Enable tile-aware I/O caching for DOM image reads",
    )
    parser.add_argument(
        "--tile-cache-max-mb",
        type=int,
        default=100,
        help="Maximum tile cache memory in MB (default: 100)",
    )
    parser.add_argument(
        "--adaptive-warmup-count",
        type=int,
        default=10,
        help="Number of reads to measure before deciding cache vs bypass",
    )
    parser.add_argument(
        "--adaptive-throughput-threshold-mbps",
        type=float,
        default=200.0,
        help="Throughput threshold (MB/s) for bypass decision",
    )
    parser.add_argument(
        "--adaptive-recheck-every",
        type=int,
        default=0,
        help="Re-evaluate bypass decision every N reads (0=never)",
    )
```

- [ ] **Step 8: Pass CLI args to `match_dom_pair`**

In the main function where `match_dom_pair` is called with `args.*`, add:

```python
    use_tile_cache=args.use_tile_cache,
    tile_cache_max_mb=args.tile_cache_max_mb,
    adaptive_warmup_count=args.adaptive_warmup_count,
    adaptive_throughput_threshold_mbps=args.adaptive_throughput_threshold_mbps,
    adaptive_recheck_every=args.adaptive_recheck_every,
```

- [ ] **Step 9: Run full test suite**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/ -v -k "matching or validity" --timeout=120 2>&1 | tail -40
```

Expected: All tests PASS.

- [ ] **Step 10: Commit**

```bash
git add examples/controlnet_construct/image_match.py examples/controlnet_construct/tile_validity.py
git commit -m "feat: wire tile cache config into image_match.py CLI and orchestration

Add use_tile_cache and adaptive parameters to match_dom_pair,
CLI parser, and pass through to serial, parallel, and validity paths.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Verify End-to-End with Cache Enabled

- [ ] **Step 1: Run E2E test with cache disabled (sanity)**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m pytest tests/unitTest/controlnet_construct_e2e_unit_test.py -v --timeout=300 2>&1 | tail -20
```

Expected: E2E test passes with default config (cache disabled).

- [ ] **Step 2: Verify CLI help shows new options**

```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m controlnet_construct.image_match --help 2>&1 | grep -A1 "tile-cache"
```

Expected: Shows `--use-tile-cache`, `--tile-cache-max-mb`, `--adaptive-warmup-count`, `--adaptive-throughput-threshold-mbps`, `--adaptive-recheck-every`.

- [ ] **Step 3: Commit**

No code changes, just verification.
