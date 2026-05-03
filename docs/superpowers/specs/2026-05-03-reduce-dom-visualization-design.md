# Reduce DOM Visualization Design

## Problem

`examples/controlnet_construct/match_visualization.py` currently reads full-resolution DOM cubes into memory before stretch, resize, and `cv2.drawMatches(...)`. For large LRO NAC DOMs this can trigger OOM during post-RANSAC visualization, even when image matching itself has already completed.

## Goals

1. Avoid default full-resolution visualization reads for large DOMs.
2. Add an automatic visualization decision layer with `full`, `reduced`, `cropped`, and `reduced_cropped` modes.
3. Prefer ISIS `reduce`-generated preview cubes so Mapping/projection labels remain usable.
4. Reuse existing low-resolution matching caches when they satisfy visualization requirements.
5. Expose coherent Python API, JSON config, and CLI/wrapper options using snake_case internally and kebab-case publicly.
6. Emit metadata/report diagnostics describing the actual visualization path.

## Non-goals

- Do not replace the existing ISIS command-line `reduce` path with pybind `Reduce` in this phase.
- Do not reintroduce `gdal_translate` for visualization preview generation.
- Do not change DOM GSD normalization behavior in `dom_prepare.py`.

## Recommended approach

Use a staged full implementation:

1. Introduce focused preview decision helpers in `match_visualization.py`, keeping public entry points compatible.
2. Add reduced-preview cube generation/reuse using `lowres_offset.create_low_resolution_dom(...)` and `_validate_projection_ready_cube(...)`.
3. Add keypoint-bounding-box crop rendering as a second-level fallback.
4. Wire options through `image_match.py`, `controlnet_stereopair.py`, and `run_pipeline_example.sh`.
5. Add low-resolution matching target-long-edge configuration and derive `low_resolution_level` when an explicit level is not provided.

This keeps each behavior testable while still implementing the complete draft scope.

## Configuration model

### Shared profile

`memory_profile` maps to target long edges:

| memory_profile | visualization_target_long_edge | low_resolution_matching_target_long_edge |
| --- | ---: | ---: |
| `high-memory` | 4096 | 4096 |
| `balanced` | 2048 | 2048 |
| `low-memory` | 1024 | 1024 |

### Visualization options

- `visualization_mode`: `auto | full | reduced | cropped | reduced_cropped`
- `visualization_target_long_edge`: positive integer target for preview longest edge
- `max_preview_pixels`: optional positive integer pixel budget
- `preview_crop_margin_pixels`: non-negative integer margin around keypoint bounding boxes
- `preview_cache_dir`: optional reduced-preview cache directory
- `preview_cache_source`: `auto | matching_cache | visualization_cache | disabled`
- `preview_force_regenerate`: boolean
- `preview_level`: optional non-negative integer advanced override

### Low-resolution matching options

- `low_resolution_matching_target_long_edge`: positive integer target
- Existing `low_resolution_level` remains supported as the highest-priority explicit override.

## Priority rules

1. If visualization output is disabled, skip all preview decisions.
2. Explicit `visualization_mode` beats `auto`.
3. Explicit `preview_level` beats `visualization_target_long_edge`.
4. Explicit target long edge beats `memory_profile`.
5. `preview_cache_source=auto` checks matching cache first, then visualization cache, then generates.
6. If requested `full` would exceed safety limits, return a diagnostic fallback to reduced/cropped unless force behavior is explicitly added in a future design.

## Data flow

### Post-RANSAC visualization

`controlnet_stereopair.py from-dom-batch` passes visualization settings into `write_stereo_pair_match_visualization_from_key_files(...)`.

The visualization helper:

1. Opens DOM metadata only to decide dimensions.
2. Resolves mode and preview level from profile/target/level.
3. Chooses source images:
   - full cube for small images;
   - matching low-resolution cache when suitable;
   - visualization reduced cache when available;
   - newly generated reduced cache when needed;
   - crop windows when mode or budget requires it.
4. Adjusts keypoint draw coordinates by source scale and crop offset.
5. Writes PNG and returns diagnostics.

### Image-match visualization

`image_match.py` uses the same helper and forwards the same options so pre-RANSAC and post-RANSAC previews share behavior.

### Low-resolution matching target

When low-resolution offset estimation is enabled:

1. If `low_resolution_level` is explicitly supplied, preserve current behavior.
2. Otherwise derive a pair-common level from the larger longest edge of the left/right DOMs and `low_resolution_matching_target_long_edge`.
3. Persist the resolved level in existing low-resolution summary metadata.

## Diagnostics

Visualization result dictionaries and controlnet reports include:

- `visualization_mode_requested`
- `visualization_mode_used`
- `memory_profile`
- `preview_level`
- `preview_cache_hit`
- `preview_cache_source`
- `preview_dimensions`
- `crop_window`
- `source_scale_factor`
- `output_path`

Existing fields such as `point_count`, `scale_factor`, and `highlighted_match_count` remain.

## Error handling

- Invalid enum values raise `ValueError` or `argparse` errors at parse boundaries.
- Missing `reduce` command surfaces the existing explicit runtime error.
- Cache validation failures regenerate when possible and record diagnostics.
- If no keypoints are available for crop mode, auto mode falls back to reduced/full based on size; explicit crop mode raises a clear `ValueError`.

## Testing plan

1. Unit tests for target-long-edge to reduce-level calculation.
2. Unit tests for profile/default resolution and validation.
3. Visualization tests that prove large images choose reduced/cropped instead of full reads.
4. Tests for keypoint crop coordinate adjustment.
5. Config/CLI tests in `image_match.py`, `controlnet_stereopair.py`, and `run_pipeline_example.sh`.
6. Metadata/report assertions for visualization diagnostics.
7. Focused regression suite for matching, stereopair, and pipeline wrappers.

## Implementation boundaries

- Keep preview decision helpers close to `match_visualization.py` unless size forces extraction.
- Reuse `lowres_offset.py` helpers instead of duplicating reduce command execution.
- Keep public CLI flags kebab-case and JSON/Python fields snake_case.
- Preserve existing defaults for small images and disabled visualization paths.
