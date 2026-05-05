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
        self._tile_w = int(core.find_keyword("TileSamples")[0])
        self._tile_h = int(core.find_keyword("TileLines")[0])
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
        # Rolling accumulators for recheck (reset after each evaluation).
        self._recheck_bytes: int = 0
        self._recheck_seconds: float = 0.0

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

        # Ensure all tiles are cached (and promote accessed tiles in LRU order).
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                key = TileCoord(col, row, band)
                if key in self._cache:
                    self._cache.move_to_end(key)
                else:
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
        self._recheck_bytes += tile_data.nbytes
        self._recheck_seconds += elapsed
        if self._state == CacheState.ACTIVE and self._recheck_every > 0:
            self._reads_since_recheck += 1
            if self._reads_since_recheck >= self._recheck_every:
                self._reads_since_recheck = 0
                if self._recheck_seconds > 0:
                    avg_mbps = self._recheck_bytes / self._recheck_seconds / 1_048_576
                    if avg_mbps >= self._throughput_threshold:
                        self._state = CacheState.BYPASSED
                self._recheck_bytes = 0
                self._recheck_seconds = 0.0

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
) -> tuple[Callable[[int, int, int, int, int], np.ndarray], TileCache | None]:
    """Factory: return (read_fn, cache_or_none).

    When use_cache=False, the returned function does a direct
    Brick read. When use_cache=True, it returns the
    TileCache.read_region method.

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
