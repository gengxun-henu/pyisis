# Tile-Aware Image I/O Cache Design

**Date:** 2026-05-04
**Status:** Draft
**Scope:** Optional tile-aware read cache for DOM matching pipeline

## Problem

Large planetary DOM images suffer from disk I/O bottleneck when reading arbitrary rectangular regions (bricks). ISIS cubes store data in tiles, but current code reads each brick via a separate `ip.Brick` call regardless of tile boundaries, causing:

- Re-reading the same storage tile for multiple overlapping bricks
- Inefficient disk access patterns when brick boundaries don't align with tile boundaries
- No memory caching between consecutive reads

## Solution Overview

A Python-side `TileCache` class that:
1. Reads data at storage tile granularity, not request brick granularity
2. Caches recently read tiles in memory with LRU eviction
3. Self-evaluates at startup to decide whether caching is beneficial (SSD vs HDD)
4. Opt-in via JSON configuration, zero impact on existing code paths

## Architecture

### Class Structure

```
TileCache
├── __init__(cube, cache_max_mb, adaptive params)
├── read_region(x, y, w, h, band=1) → np.ndarray
├── close()
│
├── _cube: ip.Cube                          # opened once, reused
├── _tile_w, _tile_h: int                   # storage tile dimensions from ISIS label
├── _cube_w, _cube_h: int                   # full cube dimensions
├── _cache: OrderedDict[TileCoord, np.ndarray]  # LRU cache
├── _cache_bytes: int                       # current memory usage
├── _cache_max_bytes: int                   # configured limit
├── _state: CacheState                       # WARMING_UP / ACTIVE / BYPASSED
├── _warmup_samples: list[timedelta]        # timing measurements
└── _total_warmup_bytes: int                # bytes read during warmup
```

### CacheState Enum

- **WARMING_UP**: First N reads. Cache operates normally while timing each read. After N reads, compute average throughput and decide state.
- **ACTIVE**: Cache is beneficial. Continue normal tile-cached reads.
- **BYPASSED**: Disk is fast enough (e.g., SSD with small images). Fall through to direct `_read_cube_window` for all subsequent calls.

### LRU Cache Key

```python
@dataclass(frozen=True)
class TileCoord:
    col: int    # tile column index
    row: int    # tile row index
    band: int   # band number (typically 1)
```

### Configuration (JSON)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_tile_cache` | `false` | Master switch. `true` enables TileCache |
| `tile_cache_max_mb` | `100` | Maximum cache memory in megabytes |
| `adaptive_warmup_count` | `10` | Number of reads to measure before decision |
| `adaptive_throughput_threshold_mbps` | `200.0` | Threshold for bypass decision |
| `adaptive_recheck_every` | `0` | In ACTIVE mode, re-evaluate every N reads. `0` = never recheck |

## Tile Reading Algorithm

### read_region(x, y, w, h, band) Flow

**1. Check adaptive state:**
- If `BYPASSED`: delegate to direct `ip.Brick` read, return immediately
- Otherwise: continue

**2. Compute covered tile range:**
```python
start_col = floor(x / tile_w)
end_col   = floor((x + w - 1) / tile_w)
start_row = floor(y / tile_h)
end_row   = floor((y + h - 1) / tile_h)
```

**3. Ensure all tiles are cached:**
For each `(col, row)` in range:
- If not in cache: read full tile from disk using `ip.Brick`
  - Tile position: `(col * tile_w, row * tile_h)`
  - Tile size: `(min(tile_w, cube_w - col*tile_w), min(tile_h, cube_h - row*tile_h))`
  - Add to OrderedDict front, update `cache_bytes`
  - While warmup: record elapsed time and bytes read

**4. LRU eviction (after each new tile):**
- While `cache_bytes > cache_max_bytes`: pop last entry from OrderedDict, subtract from `cache_bytes`

**5. Assemble output:**
- Allocate output array of shape `(h, w)` filled with 0.0
- For each covered tile:
  - Compute the overlap rectangle between the tile and the request region
  - Extract the overlapping pixels from the tile's numpy array
  - Copy into the correct position in the output array

### Edge Cases

**Edge tiles:** The last tile in each dimension may be smaller than the standard tile size. The algorithm uses `min(tile_size, remaining_pixels)` to clamp.

**Single-tile requests:** If the request region fits entirely within one tile, only one disk read is needed and the entire assembly is a single numpy slice.

**Multi-band:** The class assumes single-band reads (band=1), matching the current pipeline. Multi-band support can be added later via the `band` parameter.

## Integration Points

### Existing Code Paths (Unchanged)

- `tile_matching.py:_read_cube_window()` — remains the default read path
- `tile_validity.py:_read_cube_window_for_validity()` — remains unchanged

### New Optional Path

At the matching orchestration level (`image_match.py`, `tile_matching.py` worker functions):

```python
# Decide read function at startup
if config.get("use_tile_cache", False):
    cache = TileCache(cube, cache_max_mb=config.get("tile_cache_max_mb", 100),
                      adaptive_warmup_count=config.get("adaptive_warmup_count", 10),
                      adaptive_throughput_threshold_mbps=config.get("adaptive_throughput_threshold_mbps", 200.0),
                      adaptive_recheck_every=config.get("adaptive_recheck_every", 0))
    read_fn = cache.read_region
else:
    cache = None
    read_fn = _read_cube_window  # existing function
```

All downstream code calls `read_fn(x, y, w, h, band)` uniformly.

### Lifecycle

`TileCache` is created when a worker opens a cube and destroyed when the worker closes it. This matches the existing "open cube once per shard, process all tasks, close" pattern in the batched parallel path.

### New File

`examples/controlnet_construct/tile_cache.py` — contains the `TileCache` class and `CacheState` enum. No other files are created or modified in structure.

## Tile vs Brick Size Relationships

The algorithm handles all cases:

| Case | Tile size vs Brick size | Behavior |
|------|------------------------|----------|
| TILE < BRICK | e.g., tile=1024, brick=2048 | Read 4 tiles, assemble 1 brick |
| TILE > BRICK | e.g., tile=2048, brick=1024 | Read 1 tile, serve 4 bricks from cache |
| TILE != BRICK (misaligned) | e.g., tile=1500, brick=1024 | Read partial tiles at boundaries, crop and assemble |
| TILE == BRICK | Exact match | Direct read, cached for potential reuse |

## Throughput Measurement

During warmup:
```python
total_bytes = 0
total_seconds = 0.0

for each warmup read:
    t0 = time.monotonic()
    tile_data = disk_read(...)
    elapsed = time.monotonic() - t0
    total_bytes += tile_data.nbytes
    total_seconds += elapsed

avg_mbps = total_bytes / total_seconds / 1_048_576
```

Decision:
- `avg_mbps >= threshold` → `BYPASSED` (disk is fast enough, skip cache)
- `avg_mbps < threshold` → `ACTIVE` (cache will help)

## Dependencies

- Python standard library: `collections.OrderedDict`, `math`, `time`, `dataclasses`
- Project dependencies: `numpy` (for array slicing)
- ISIS pybind: `ip.Brick`, `ip.Cube` (used for disk reads)

No new external dependencies required.
