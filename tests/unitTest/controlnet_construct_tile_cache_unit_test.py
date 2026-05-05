"""Unit tests for tile_cache.py -- TileCache LRU, adaptive bypass, and assembly.

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

from _unit_test_support import (  # noqa: E402
    ip,
    make_tile_test_cube,
    temporary_directory,
)

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
            # Read last 2 rows and 3 cols -- crosses tile boundaries
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

                # Read 3 tiles -- should all be cached.
                cache.read_region(0, 0, 4, 4)   # tile (0,0)
                cache.read_region(4, 0, 4, 4)   # tile (1,0)
                cache.read_region(0, 4, 4, 4)   # tile (0,1)
                self.assertEqual(len(cache._cache), 3)

                # Read 4th tile -- should evict oldest (0,0).
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
