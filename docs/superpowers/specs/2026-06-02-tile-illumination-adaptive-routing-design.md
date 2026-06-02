# Tile-Level Physical Illumination Adaptive Routing Design

Date: 2026-06-02
Status: Draft for user review

## Goal

Add tile-level physical illumination evidence to adaptive matcher routing for LRO NAC DOM matching. The design lets long-strip polar image pairs select matchers per tile, while preserving a pair-center approximation for compact or non-tiled stereo pairs.

The central change is to separate radiometric matching masks from physical illumination sampling. Very dark shadowed pixels may be invalid for feature matching after percentile filtering, but they can still represent real terrain and should remain eligible for solar-geometry sampling if they can be projected to the DOM source camera.

## Scope

This design covers:

- tile-level representative-point selection for illumination sampling;
- DOM-to-ground-to-source-camera solar geometry extraction;
- source cube metadata needed to audit physical illumination;
- tile-level adaptive routing data models;
- grouped classic/deep execution so deep-learning work is not launched per tile;
- reporting fields needed for RANSAC-filtered benchmark summaries and figures.

This design does not implement the feature. It defines the contract for the follow-up implementation plan.

## Recommended Approach

Use a small set of illumination-specific models and keep them adjacent to existing image matching ownership.

`examples/image_match/` remains responsible for:

- tile diagnostics;
- representative-point selection;
- physical solar geometry extraction;
- tile-level routing decisions;
- grouped deep manifest export/import metadata.

`examples/controlnet_construct/` remains an orchestration and reporting consumer. It should pass source cube paths and adaptive options through, but it should not duplicate the routing logic.

## Validity Concepts

The implementation must keep three validity concepts separate.

### `pixel_available`

This is the minimum DOM-pixel existence check for illumination sampling.

A pixel is available when it is finite and not an ISIS special/no-data pixel. It may still be very dark or very bright. Shadowed pixels should normally remain eligible under this rule.

### `radiometric_valid_for_matching`

This is the matching mask rule. It includes the current percentile-based filtering, such as the 0.1/99.9 percent gray-value range, invalid mask expansion, and method-specific valid-pixel thresholds.

This rule is used for SIFT, LightGlue, LoFTR, texture/keypoint analysis, and match masking. It must not be used as a hard exclusion for illumination representative-point selection.

### `source_projectable`

This is the physical illumination requirement.

A DOM point is source-projectable when:

1. `DOM UniversalGroundMap(... ProjectionFirst).set_image(dom_sample, dom_line)` succeeds.
2. `source UniversalGroundMap(... CameraFirst).set_universal_ground(latitude, longitude)` succeeds.
3. `source_cube.camera().set_image(source_sample, source_line)` succeeds.
4. `sun_azimuth()` and `incidence_angle()` return finite values.

The selected illumination point must be both `pixel_available` and `source_projectable`.

## Data Model

### `RepresentativePoint`

Represents one selected point for tile or pair-center illumination sampling.

Fields:

- `status`: `center_projectable`, `nearest_projectable_pixel`, or `no_projectable_pixel`.
- `selection_reason`: concise explanation of why the point was selected or skipped.
- `local_x_0_based`, `local_y_0_based`: local tile coordinates when tiled.
- `dom_sample_1_based`, `dom_line_1_based`: ISIS DOM image coordinates.
- `pixel_available`: boolean.
- `radiometric_valid_for_matching`: boolean or null when not evaluated.
- `source_projectable`: boolean.
- `failure_reason`: null on success, otherwise one of:
  - `center_pixel_unavailable`;
  - `dom_ground_map_set_image_failed`;
  - `source_ground_map_set_universal_ground_failed`;
  - `source_camera_set_image_failed`;
  - `solar_geometry_missing_or_non_finite`;
  - `no_projectable_pixel`.

### `TileIlluminationSample`

Physical solar geometry for one tile side.

Fields:

- `side`: `left` or `right`.
- `dom_path`.
- `dom_source_cube`: the camera cube used to generate this DOM. It may be full-resolution original or REDUCED.
- `upstream_source_cube`: optional upstream full-resolution source, when available.
- `tile_index`.
- `tile_window_0_based`: `start_x`, `start_y`, `width`, `height`.
- `representative_point`: `RepresentativePoint`.
- `latitude`, `longitude`.
- `source_sample_1_based`, `source_line_1_based`.
- `sun_azimuth_degrees`.
- `incidence_angle_degrees`.
- `solar_elevation_degrees`: `90.0 - incidence_angle_degrees`.

On failure, geometry fields are null and `representative_point.status` records the skip reason.

### `TileIlluminationPair`

Combines left and right `TileIlluminationSample` records for one paired tile.

Fields:

- `tile_index`.
- `status`: `ok`, `left_failed`, `right_failed`, or `both_failed`.
- `left`, `right`.
- `azimuth_difference_degrees`: circular angular difference.
- `incidence_difference_degrees`.
- `elevation_difference_degrees`.
- `illumination_difference_score`: normalized score used by routing.

The score should be derived from physical angles, not DOM display brightness.

### `TileRoutingDecision`

One prior-only matcher decision for a tile.

Fields:

- `tile_index`.
- `texture_sparseness`.
- `texture_probe_keypoint_count_left`.
- `texture_probe_keypoint_count_right`.
- `texture_probe_keypoint_density_left`.
- `texture_probe_keypoint_density_right`.
- `illumination`: `TileIlluminationPair`.
- `selected_matcher`: `sift_flann`, `sift_lightglue`, `superpoint_lightglue`, or `loftr`.
- `selected_execution_environment`: `asp360_new` or `deep-learning`.
- `route_reason`.
- `route_confidence`.
- `no_post_match_fallback`: true.

### `PairIlluminationSummary`

Pair-level aggregation for reports and figures.

Fields:

- `illumination_granularity`: `tile` or `pair_center`.
- `tile_count`.
- `projectable_tile_count`.
- `skipped_tile_count`.
- `skip_reasons`.
- `azimuth_difference_summary`.
- `incidence_difference_summary`.
- `elevation_difference_summary`.
- `illumination_difference_score_summary`.
- `route_distribution_by_tile`.
- `route_distribution_by_projectable_tile`.

## Representative-Point Selection

For tiled matching, selection runs independently for each left/right tile. For compact or non-tiled matching, selection runs once at the pair overlap center.

Selection algorithm:

1. Try the geometric center of the tile or pair overlap.
2. If the center is `pixel_available`, attempt the full source projection and solar-geometry chain.
3. If the center succeeds, use it even if it is not `radiometric_valid_for_matching`.
4. If the center is unavailable or not source-projectable, search nearby DOM pixels that are `pixel_available`.
5. Candidate order is deterministic by increasing squared distance from center, then row, then column.
6. Stop at the first candidate that is source-projectable.
7. If no candidate succeeds, mark the side as `no_projectable_pixel`.

The search is bounded to the current tile or pair-overlap window. It should not compute solar geometry for every image pixel outside that bounded region. The implementation may stop after the first projectable candidate because the goal is a representative illumination sample, not a per-pixel illumination field.

## Source Cube Metadata

Every DOM used for physical illumination must carry its source camera cube path.

Required metadata fields:

- `dom_path`.
- `dom_source_cube`.
- `upstream_source_cube`, optional.
- `dom_source_kind`: `full_resolution_original`, `reduced`, or `unknown`.

For the current reduced-10m experiment, `reduced_selected_pair_paths.csv` provides:

- `source_echo_cal_cube`: upstream full-resolution original echo/cal cube.
- `echo_cal_cube`: the REDUCED source cube used to generate the 10 m DOM.
- `source_dom_cube`: upstream original-GSD DOM.
- `dom_cube`: reduced 10 m DOM used by matching.

Future match sidecars should embed `dom_source_cube` directly so routing and reports do not depend on an external CSV lookup.

## Routing Behavior

Adaptive routing remains prior-only. It selects one matcher from texture/keypoint evidence plus physical illumination evidence. It does not retry another matcher after a failed match.

Default routing intent:

- Rich texture and small physical illumination difference: `sift_flann`.
- Moderate-to-rich texture and moderate illumination difference: `sift_lightglue`.
- Weak-to-moderate texture with non-extreme illumination difference: `superpoint_lightglue`.
- Very low texture/keypoint evidence or weak texture with large illumination difference: `loftr`.

The existing hard rule for very low texture-probe keypoint count/density remains before softer texture/illumination bins.

## Deep Manifest Grouping

Tile-level routing should not create one deep-learning process per tile.

Execution order:

1. In `asp360_new`, resolve source cubes, compute illumination metadata, route tiles, run all selected `sift_flann` tiles, and export grouped deep manifests.
2. Switch once to `deep-learning`.
3. Run all required grouped manifests for `sift_lightglue`, `superpoint_lightglue`, and `loftr`, using `torch_num_threads=8` and `num_workers=1` by default.
4. Return to `asp360_new`.
5. Import deep results, merge tile keypoints, run RANSAC filtering, summarize, and plot.

Grouping shape:

- one route metadata file per stereo pair;
- one classic result group for SIFT+FLANN tiles;
- up to one manifest group per deep matcher per stereo pair;
- merged pair-level key files after import.

Deep task records should preserve `tile_index`, selected matcher, representative-point status, and physical illumination diagnostics in metadata.

## Reporting and Figures

Reports should keep pair-level and tile-level evidence separate.

Required reporting additions:

- route distribution by tile;
- route distribution by projectable tile;
- skipped illumination tile count and reasons;
- physical illumination difference summaries;
- RANSAC-retained match counts per method and pair;
- source cube path audit fields.

DOM display brightness and 0.1/99.9 percentile masks may be reported as visualization or matching diagnostics, but they should not be described as physical lighting measurements.

## Backward Compatibility

Older sidecars without tile illumination metadata remain loadable.

Compatibility behavior:

- Missing `tile_illumination` means no physical tile routing evidence is available.
- Existing pair-level adaptive summaries remain interpretable as legacy pair-level routing.
- Report generation should not fail when physical illumination fields are absent; it should mark them as missing.

## Testing Plan

Focused tests should cover:

- center `pixel_available` and source-projectable selects `center_projectable`;
- center shadowed or radiometrically invalid for matching can still be selected when source-projectable;
- center projection failure falls back to nearest `pixel_available` projectable pixel;
- no projectable candidate yields `no_projectable_pixel`;
- `solar_elevation_degrees` equals `90.0 - incidence_angle_degrees`;
- circular azimuth difference handles wraparound;
- source cube path metadata is embedded in sidecars;
- deep manifest round-trip preserves tile route and illumination metadata;
- legacy sidecars without tile illumination still load.

Real-data smoke validation should reuse the Phase 1 sample pair where the right tile succeeded and the left center projection failed, because it exercises both successful and fallback-needed behavior.

## Non-Goals

- Do not compute per-pixel solar geometry for all pixels.
- Do not use 0.1/99.9 radiometric matching masks to reject physical illumination samples.
- Do not make adaptive routing a post-match cascade.
- Do not require every DOM to be generated from a REDUCED cube.
- Do not change deep matcher model internals.
