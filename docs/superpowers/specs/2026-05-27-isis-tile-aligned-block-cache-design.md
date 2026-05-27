# ISIS Tile-Aligned Block Cache Optimization Design

Author: Geng Xun
Created: 2026-05-27

## Goal

Improve full-resolution DOM/controlnet tile matching throughput by making matching blocks cooperate with ISIS cube storage tiles instead of fighting them. The first optimization target is the Python pipeline: choose or derive block windows that align with each cube's `Core/TileSamples` and `Core/TileLines`, preserve current CLI/config compatibility, and add enough diagnostics to prove whether the change helps before considering a C++ cache rewrite.

## Current Behavior

The current image-match path generates local matching windows from configured `block_width`, `block_height`, `overlap_x`, and `overlap_y`. Those local windows are mapped to left/right DOM crop windows by adding each side's projected-overlap offset.

`TileCache` already reads ISIS storage tiles: it looks up `TileSamples` and `TileLines`, loads missed storage tiles with `Brick`, stores them in an LRU cache, and assembles each requested window from cached tiles. However, the requested matching block can start at arbitrary absolute cube offsets and have arbitrary dimensions. A single matching block may therefore touch many storage tiles and force repeated partial-tile assembly. In process-pool mode, each worker owns its own cube handles and cache, so spatially adjacent windows can lose cache locality if they are distributed across workers.

## Design Assumptions

- DOM cubes are ISIS tiled cubes with valid `Core/TileSamples` and `Core/TileLines`; when these labels are absent or invalid, the pipeline must keep the existing configured block behavior.
- Existing users can continue passing explicit `block_width`, `block_height`, `overlap_x`, and `overlap_y`.
- The optimization should be opt-in or safely auto-resolved behind a mode, not a silent behavior change that makes old configs hard to reproduce.
- The first implementation should stay in Python. C++ should be considered only after profiling shows Python tile-cache assembly or object churn is the dominant cost.
- The left and right projected-overlap crop offsets can have different remainders relative to each cube's storage tile grid. The resolver must account for absolute cube coordinates, not only local crop-relative coordinates.

## Approaches Considered

### Approach A: Profile only

Add read/cache/matcher timing and benchmark scripts, but do not change tiling. This is the lowest-risk path and gives better data, but it leaves the likely misalignment bottleneck untouched.

### Approach B: Auto-align matching blocks to ISIS storage tiles

Add a block-sizing resolver that inspects left/right cube storage tile dimensions and derives effective matching block and overlap sizes. This keeps the current matching architecture, improves cache locality, and is the recommended first optimization.

### Approach C: Full I/O scheduling redesign

Combine tile-aligned block sizing, worker spatial sharding, richer cache metrics, and possibly a C++ read helper. This has the highest upside, but it is too broad for the first step and risks making it hard to isolate which change produced a speedup.

## Recommended Approach

Use Approach B as the core change and include minimal profiling hooks from Approach A. Defer C++ and broader worker scheduling until the aligned-block behavior is measured.

## User-Facing Behavior

Add a new block alignment mode with these effective values recorded in match metadata:

- `tile_block_alignment_mode`: `off`, `auto`, or `isis-storage`.
- `requested_block_width`, `requested_block_height`, `requested_overlap_x`, `requested_overlap_y`.
- `effective_block_width`, `effective_block_height`, `effective_overlap_x`, `effective_overlap_y`.
- `left_storage_tile_width`, `left_storage_tile_height`, `right_storage_tile_width`, `right_storage_tile_height`.
- `block_alignment_reason`: concise explanation of the selected mode or fallback.

Default behavior should initially remain compatible. The safest rollout is:

1. `off` preserves exact current behavior.
2. `auto` enables storage alignment only when both DOMs report compatible storage tile sizes and the derived block still satisfies matching constraints.
3. `isis-storage` requires storage alignment and raises a clear error if cube tile metadata cannot support it.

If an existing config explicitly sets block or overlap values, `auto` may still derive aligned values, but metadata must record both requested and effective values. Tests should cover that explicit values are not silently lost.

## Block Alignment Rules

The resolver should operate before `_paired_windows()` calls `generate_tiles()`.

1. Read each cube's storage tile dimensions from the `Core` group and the left/right crop offsets produced by projected-overlap preparation.
2. Resolve a shared storage tile size:
   - if left and right tile sizes match, use that size;
   - if they differ, use alignment only when one size is an integer multiple of the other and the selected common size remains practical;
   - otherwise fall back in `auto` or raise in `isis-storage`.
3. Derive effective block dimensions as integer multiples of the shared storage tile size.
4. Derive effective overlap as integer multiples of the shared storage tile size where possible.
5. Keep `overlap < block`; if the requested overlap would collapse the step, clamp to the largest valid aligned overlap and record the reason.
6. Check whether a common local start sequence can make both absolute windows align to storage tile boundaries:
   - left absolute start is `left_offset + local_start`;
   - right absolute start is `right_offset + local_start`;
   - both should be divisible by their respective storage tile sizes for interior windows.
7. If the left/right offset remainders are compatible, generate aligned local starts. If they are incompatible, `auto` should fall back to the existing start sequence and record the reason; `isis-storage` should fail clearly.
8. Generate windows with the existing full-coverage semantics, including edge windows that may be smaller at image boundaries.

The key invariant is that non-edge windows should start on storage-tile boundaries in absolute cube coordinates for both left and right images when the crop offsets allow it. Edge windows may be clipped by the shared extent but should still avoid unnecessary interior misalignment.

## Pipeline Integration

Add a small resolver module or focused helper near tiling/tile matching, for example:

- `resolve_tile_aligned_block_config(...)` reads storage tile metadata, crop offsets, requested block parameters, and returns a dataclass containing effective dimensions, mode, reason, offset-remainder diagnostics, and metadata.
- `match_dom_pair()` calls the resolver after cubes are open and after pair preparation has produced crop offsets, but before final paired windows are generated.
- `_paired_windows()` receives either effective block/overlap values or a precomputed aligned local-start sequence.
- Summary metadata records both requested and effective values.

This keeps window generation separate from cube metadata inspection and avoids embedding alignment policy inside `TileCache`.

## Diagnostics and Profiling

Add lightweight counters rather than a heavy profiler:

- number of read windows;
- number of storage-tile cache hits/misses;
- number of assembled storage tiles per requested window;
- cache state (`warming_up`, `active`, `bypassed`);
- total cache read/load/assembly seconds when diagnostics are enabled.

Diagnostics should be optional and metadata-safe. Existing quiet CLI output should not become noisy.

## Testing Strategy

Unit tests should cover:

- block resolver derives aligned multiples for matching left/right storage tile sizes;
- fallback behavior when tile metadata is missing or incompatible;
- `isis-storage` mode raises on unsupported metadata;
- generated paired windows use effective block/overlap values and keep full coverage;
- metadata records requested and effective values;
- existing TileCache read correctness tests still pass.

Focused validation should use the existing asp360_new environment and unit tests around tile cache, tiling, and controlnet matching. Performance validation should compare at least:

- cache off vs cache on;
- alignment off vs auto;
- one worker vs multiple workers;
- representative small fixture and one larger real DOM pair when available.

## C++ Decision Gate

Do not implement a C++ TileCache in this phase. Revisit C++ only if profiling shows that Python cache lookup, assembly copying, or object creation is a significant share of total wall time after aligned-block optimization. If C++ is justified, the useful boundary is a helper that owns tile cache plus assembly and returns a ready NumPy array, not a thin wrapper around a single `Brick` read.

## Implementation Plan

1. Add the alignment-mode API and metadata schema.
2. Implement the storage tile metadata reader and block alignment resolver.
3. Thread effective block/overlap values into `match_dom_pair()` and `_paired_windows()`.
4. Add optional TileCache diagnostics counters.
5. Add focused unit tests for resolver, window generation, metadata, and cache diagnostics.
6. Run focused validation and record benchmark guidance in the final handoff.

## Out of Scope

- Rewriting TileCache in C++.
- Changing SIFT/deep matcher behavior.
- Sharing cache memory across process workers.
- Changing default matching semantics without explicit mode selection.
