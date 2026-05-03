# Tile Read Optimization Design

## Problem

`examples/controlnet_construct` currently reads full-resolution DOM tiles before it can decide whether each tile has enough valid pixels for SIFT matching. The serial path keeps the left and right cubes open, but still reads every candidate tile. The parallel path is more expensive: each tile is submitted as an independent process-pool task, and every task reopens both DOM cubes before reading one tile.

For large DOMs, especially 10 GB class files with large invalid regions, this creates avoidable random I/O and repeated cube open/close overhead. The goal is to reduce end-to-end wall time while keeping the existing behavior as the default baseline.

## Goals

- Keep the current matching behavior as the default unless the new optimization is explicitly enabled.
- Add a workflow-level, single-DOM validity index cache that can be reused across multiple DOM pairs.
- Conservatively prefilter full-resolution tile candidates before reading tile data.
- Rework the parallel CPU path so each worker opens the left and right cubes once per batch instead of once per tile.
- Record enough summary and metadata fields to compare the old path, validity prefilter only, and validity prefilter plus batched parallel execution.

## Non-goals

- Do not preload large groups of full-resolution tiles into memory.
- Do not replace the process pool with a thread pool in this phase.
- Do not merge the low-resolution offset cache with the full-resolution validity index. They solve different problems and should remain separate.
- Do not make the optimization the default path until real workflow benchmarks justify it.

## Recommended approach

Use an explicitly enabled optimization path with three layers:

1. A per-DOM validity index cache stored in a workflow-level cache directory.
2. A conservative tile prefilter inserted after `_paired_windows(...)` and before serial or parallel tile matching.
3. A batched process-pool executor where each worker opens the left and right cubes once and processes a shard of remaining tiles.

This combines the two highest-value optimizations: reducing full-resolution tile reads and avoiding repeated cube reopen work in the parallel path.

## Validity index cache

The cache is keyed by a single DOM and the parameters that affect valid-pixel semantics. It should be stored under a workflow-level directory, such as `<work-dir>/tile_validity_cache`, so a DOM used in many pair matches pays the scan cost once.

The cache should use a small JSON manifest plus a NumPy data file. The manifest records:

- DOM path
- file size and `mtime_ns`
- band
- coarse cell width and height
- invalid values
- special-pixel absolute threshold
- invalid-pixel radius
- grid width and height
- cache format version

The NumPy data file stores one row per coarse cell:

- valid pixel count
- total pixel count
- valid pixel ratio
- uncertain flag

The initial default coarse cell size should be 1024 x 1024. The size should be configurable so performance tests can compare larger or smaller grids without changing code.

## Index construction

Index construction opens each DOM once, scans it cell by cell, and computes valid-pixel statistics using the same semantics as the current full-resolution tile path:

- `summarize_valid_pixels(...)`
- `expand_invalid_mask_for_radius(...)`

For `invalid_pixel_radius > 0`, cell-edge effects must be handled conservatively. A cell whose expanded invalid mask may depend on neighboring cells should be marked uncertain near the boundary rather than treated as a safe skip candidate.

If the manifest does not match the DOM fingerprint or valid-pixel parameters, the cache is invalid and must be rebuilt before prefiltering. Cache failures should surface as explicit errors while the optimization is enabled; they should not silently fall back to the old path.

## Tile prefiltering

`match_dom_pair(...)` should call the prefilter immediately after building `windows = _paired_windows(...)` and before creating tile-match tasks.

For each `PairedTileWindow`, the prefilter maps the left and right tile windows to the coarse cells they cover. A tile can be pre-skipped only when at least one side is certainly below `valid_pixel_percent_threshold` across all covered cells. If any covered cell is uncertain, the tile crosses a boundary that cannot be evaluated safely, or the threshold is zero, the tile must be kept and the existing full-resolution read-and-check path remains the source of truth.

Prefilter skips must be tracked separately from full-resolution tile skips. They should not be reported as matched tiles, and they should not be mixed into the existing `skipped_tile_count` without also exposing a separate `preindexed_skipped_tile_count`.

## Parallel execution

The parallel path should keep the process-pool model and avoid thread-safety assumptions for ISIS, pybind, OpenCV, or NumPy.

Instead of submitting one tile per future, the caller should partition remaining tile tasks into worker shards. Each worker should:

1. Open the left and right cubes once.
2. Resolve invalid values for each cube once.
3. Loop over its assigned tile windows.
4. Read each left and right tile window.
5. Call `_match_tile_from_window_values(...)`.
6. Close both cubes in a `finally` block.

The parent process then merges results back into original tile order. Exceptions from workers should propagate; they must not be swallowed or converted into successful empty results.

The existing serial path should remain `open once + read on demand`. Users who pass `--no-parallel-cpu` should still benefit from the validity prefilter when it is enabled.

## API and CLI

The Python API should keep old behavior by default and add explicit options:

- `enable_tile_validity_prefilter: bool = False`
- `tile_validity_cache_dir: str | Path | None = None`
- `tile_validity_cell_width: int = 1024`
- `tile_validity_cell_height: int = 1024`

The CLI should expose kebab-case equivalents:

- `--enable-tile-validity-prefilter`
- `--tile-validity-cache-dir`
- `--tile-validity-cell-width`
- `--tile-validity-cell-height`

If the optimization is enabled and no cache directory is provided, the default cache directory should be derived from the workflow or pair output context, similar in spirit to the low-resolution output directory defaults, but at workflow scope so a DOM can be reused across pairs.

## Summary and metadata

The summary returned by `match_dom_pair(...)` and written by `match_dom_pair_to_key_files(...)` should include:

- `tile_count_before_preindex_filter`
- `tile_count_after_preindex_filter`
- `preindexed_skipped_tile_count`
- `tile_validity_prefilter_enabled`
- `tile_validity_cache_dir`
- left and right cache hit/miss/rebuilt diagnostics
- coarse cell width and height
- `parallel_cpu_backend`, using a distinct value such as `process_pool_batched_cube_reuse` when the new batched parallel path runs
- existing `matched_tile_count`, `skipped_tile_count`, and `point_count`

This lets benchmarks distinguish fewer candidate tiles from faster execution of the remaining tiles.

## Error handling

Parameter validation should reject non-positive cell sizes and invalid cache configuration early.

Cache mismatches should rebuild the index. Corrupt cache files should produce a clear error or be replaced only through an explicit rebuild path; the implementation should not silently fall back to old behavior when the user explicitly enabled the optimization.

Worker failures should propagate to the caller. Cleanup should close opened cubes in `finally` blocks.

## Testing strategy

Focused tests should cover the new logic before broad workflow tests:

1. Pure unit tests for cache signatures, tile-to-cell mapping, and conservative skip/keep decisions.
2. Small-cube `match_dom_pair(...)` tests that verify summary fields, prefilter skip counts, and threshold-zero behavior.
3. Parallel batched-worker tests that verify each worker opens the left and right cubes once per shard, preserves result order, updates progress per tile, and propagates exceptions.
4. CLI/config tests for the new kebab-case options and default-disabled behavior.

Real workflow validation should compare:

1. Existing baseline.
2. Serial or `--no-parallel-cpu` with validity prefilter enabled.
3. Parallel CPU with validity prefilter and batched cube reuse enabled.

Each run should record wall time, original tile count, prefiltered tile count, pre-skipped tile count, actual read tile count, matched tile count, skipped tile count, worker count, and cache hit/miss status.

## Implementation slices

The implementation can be delivered in two independently verifiable slices:

1. Add the validity index cache and conservative prefilter, wire it into `match_dom_pair(...)`, and expose API/CLI/config options.
2. Replace the per-tile process-pool execution path with batched per-worker cube reuse while preserving serial behavior and result ordering.

This split keeps the optimization measurable and allows either slice to be evaluated or reverted independently.
