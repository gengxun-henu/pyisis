# Findings: Tile-Level Physical Illumination Adaptive Routing

## User Intent

The user wants to redesign the current adaptive routing experiment because the existing pair-level or grayscale-proxy lighting evidence is not strong enough for LRO NAC long-strip polar images. The desired method should:

- use physical solar geometry at the tile level where tiled matching is used;
- keep a pair-center approximation for compact low/mid-latitude stereo pairs;
- handle failed DOM centers by selecting one nearest pixel-available and source-projectable point rather than computing many solar-angle samples;
- support DOM-space lunar south-pole data with large invalid/no-data regions and shadows;
- preserve deep-learning environment separation while minimizing conda environment switches, then rerun the five-method comparison.

## Current Architecture Observations

- `examples/image_match/adaptive_routing.py` currently exposes pair-level routing types such as `PairRoutingDecision`, sidecar builders, and prior-only matcher selection.
- `examples/image_match/image_match.py` currently performs adaptive prepass logic before full-resolution matching and records adaptive sidecars in pair metadata.
- `examples/image_match/tile_matching.py` already represents matching work as `TileMatchTask`, `PairedTileWindow`, and `TileMatchResult`.
- `examples/image_match/deep_match_manifest.py` already exports deep-learning work as per-pair manifests containing multiple tile task records.
- Current deep-learning handoff can therefore support per-tile routing if tasks are partitioned into method groups before manifest export.
- Existing polar benchmark outputs show that fixed deep methods run all 96 tile tasks for 16 pairs, and adaptive routing currently reports pair-level selected method distribution.

## Phase 1 Minimal PyISIS Geometry Validation

Validation was performed with temporary Python only; no `examples/`, `tests/`, or `tools/` code was modified.

### Data Used

- Case metadata:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602/tile_case_comparison_latest_params/rich_texture_small_lighting_gap/rich_texture_small_lighting_gap_metadata.json`
- Source mapping table:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`

### Confirmed PyISIS API Chain

The minimum working chain is:

1. Open DOM cube and source/original cube with `ip.Cube().open(path, "r")`.
2. Build DOM ground map:
   - `ip.UniversalGroundMap(dom_cube, ip.UniversalGroundMap.CameraPriority.ProjectionFirst)`
3. Build source/original ground map:
   - `ip.UniversalGroundMap(source_cube, ip.UniversalGroundMap.CameraPriority.CameraFirst)`
4. Convert DOM pixel to ground:
   - `dom_ground_map.set_image(dom_sample, dom_line)`
   - `dom_ground_map.universal_latitude()`
   - `dom_ground_map.universal_longitude()`
5. Project ground to source/original cube:
   - `source_ground_map.set_universal_ground(latitude, longitude)`
   - `source_ground_map.sample()`
   - `source_ground_map.line()`
6. Compute solar geometry:
   - `camera = source_cube.camera()`
   - `camera.set_image(source_sample, source_line)`
   - `camera.sun_azimuth()`
   - `camera.incidence_angle()`
   - `solar_elevation = 90.0 - incidence_angle`

Coordinates are 1-based ISIS sample/line when passed to `set_image`.

### Successful Right-Tile Result

- Side: right
- Product ID: `M110881352RE`
- DOM:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/doms_10m/dom_REDUCED_M110881352RE.cub`
- Source cube used for solar geometry:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_cubes/REDUCED_M110881352RE.echo.cal.cub`
- Upstream full-resolution source:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/M110881352RE.echo.cal.cub`
- Tile window, 0-based:
  - `start_x=7168`, `start_y=2048`, `width=1024`, `height=1024`
- Representative point:
  - source: `center`
  - local x/y, 0-based: `512`, `512`
  - DOM sample/line, 1-based: `7681.0`, `2561.0`
- Ground:
  - latitude: `-88.5690777294848`
  - longitude: `123.06565999195881`
- Source/original image point:
  - sample: `234.50167129021804`
  - line: `1513.9141017113047`
- Solar geometry:
  - sun azimuth: `232.70515244608052`
  - incidence angle: `87.03439723962823`
  - solar elevation: `2.965602760371766`

### Failed Left-Tile Boundary Case

- Side: left
- Product ID: `M110860982RE`
- DOM:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/doms_10m/dom_REDUCED_M110860982RE.cub`
- Source cube used for solar geometry:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_cubes/REDUCED_M110860982RE.echo.cal.cub`
- Representative point:
  - source: `center`
  - DOM sample/line, 1-based: `7681.0`, `2618.0`
- DOM ground lookup succeeded:
  - latitude: `-88.60489080469283`
  - longitude: `119.62813470400582`
- Source/original projection failed:
  - `source_ground_map.set_universal_ground_failed`

This is an important design result: representative point selection should not stop at DOM valid-pixel status. It must also require successful projection into the corresponding source/original camera cube. A future implementation should treat source-projection failure as either:

- a reason to select the nearest valid-and-projectable pixel; or
- a skip status such as `no_source_projectable_representative_point`.

### Source Path Metadata Finding

Current fixed/adaptive match metadata does not directly preserve `source_echo_cal_cube`, `echo_cal_cube`, `source_cube`, or `original_cube` paths.

- `sift_flann/match_metadata/...json` stores DOM paths and overlap/crop metadata.
- `adaptive/match_metadata/...json` stores adaptive/deep import/export status and image-match summaries.
- The authoritative DOM-to-source mapping is currently in `reduced_selected_pair_paths.csv`, with columns:
  - `source_echo_cal_cube`: upstream full-resolution original echo/cal cube.
  - `echo_cal_cube`: the cube used to generate the reduced DOM in this experiment.
  - `source_dom_cube`: upstream original-GSD DOM.
  - `dom_cube`: reduced 10 m DOM used by matching.

Future sidecars should embed `dom_source_cube` or `source_cube` directly so tile illumination does not depend on external CSV lookup.

## Why the Architecture Must Change

This is not a threshold-only update. It changes the unit of routing:

- Current unit: one route decision per stereo pair.
- Needed unit: one route decision per tile for tiled long-strip data, with pair-center fallback for compact data.

This affects:

- adaptive-routing data model;
- tile task construction;
- valid-pixel mask handling;
- DOM-to-ground and ground-to-original camera geometry;
- deep manifest export/import;
- pair-level `.key` merge and provenance;
- reports, figures, and paper claims.

## Proposed Data Flow

1. Generate paired tile windows as before.
2. For each tile, keep three validity concepts separate:
   - `pixel_available`: finite DOM pixel and not true ISIS no-data/special pixel;
   - `radiometric_valid_for_matching`: percentile/mask rule for matching, texture, keypoint, and visualization only;
   - `source_projectable`: DOM point projects through the corresponding source/original camera and returns finite solar geometry.
3. Select a representative point:
   - center if pixel-available and source-projectable;
   - nearest pixel-available and source-projectable point if center fails;
   - skip tile if there is no source-projectable representative point.
4. For the representative point:
   - convert DOM pixel to ground coordinates;
   - project the ground point into each DOM's corresponding source/original cube;
   - compute solar azimuth, incidence angle, and elevation.
5. Compute tile-level texture and keypoint-density evidence.
6. Select one matcher for the tile using prior-only adaptive rules.
7. Partition tile tasks by selected matcher.
8. In `asp360_new`, complete all classic SIFT+FLANN work and export all grouped deep manifests needed for the benchmark batch.
9. Switch once to `deep-learning` and run all required deep manifests for SIFT+LightGlue, SuperPoint+LightGlue, and LoFTR.
10. Switch back to `asp360_new`, import/merge tile results into pair-level key files.
11. Apply RANSAC and summarize success using RANSAC-retained counts.

## Matching Method Organization

Recommended organization for one long-strip pair:

- `pair_id/route_metadata.json`: all tile-level route decisions and evidence.
- `pair_id/classic/sift_flann`: tile tasks selected for classic matching in `asp360_new`, completed before deep-learning execution begins.
- `pair_id/deep/sift_lightglue/tasks.json`: grouped deep manifest for SIFT+LightGlue tiles.
- `pair_id/deep/superpoint_lightglue/tasks.json`: grouped deep manifest for SuperPoint+LightGlue tiles.
- `pair_id/deep/loftr/tasks.json`: grouped deep manifest for LoFTR tiles.
- `pair_id/imported_keys/`: merged pair-level `.key` files with per-tile provenance available in metadata.

This avoids per-tile process startup and repeated conda switching while preserving per-tile routing.

## Source Cube Policy

Do not assume the source camera cube for solar geometry is always a `REDUCED_*.cub`.

- If the DOM was generated from a full-resolution original cube, use that original cube for camera solar geometry.
- If the DOM was generated from a REDUCED cube, use the REDUCED cube for camera solar geometry.
- Metadata should name this as `source_cube` or `dom_source_cube`, not `reduced_cube`.
- Reports should preserve both DOM path and source/original cube path so tile illumination is auditable.

## Environment Execution Policy

The benchmark should minimize conda activation overhead:

- Run all `asp360_new` work first for the selected benchmark batch:
  - source-cube path resolution;
  - physical illumination metadata extraction;
  - SIFT+FLANN/classic work;
  - grouped deep manifest export.
- Then switch once to `deep-learning`:
  - run all required SIFT+LightGlue manifests;
  - run all required SuperPoint+LightGlue manifests;
  - run all required LoFTR manifests;
  - keep `torch_num_threads=8` and `num_workers=1`.
- Then return to `asp360_new` for import, RANSAC filtering, summaries, and figures.

The implementation should avoid switching environments per tile, per method, or repeatedly inside a single stereo-pair batch.

## Implementation Findings Through Task 6

- Tile route identity must be separate from backend matcher identity:
  - `sift_flann` uses backend `flann`;
  - `sift_lightglue` uses backend `lightglue`;
  - `superpoint_lightglue` uses backend `lightglue`;
  - `loftr` uses backend `loftr`.
- Missing or non-finite texture probe keypoint count/density is treated as missing evidence and routes conservatively to LoFTR.
- Very low keypoint count or density is a hard LoFTR rule.
- Extreme single-axis texture sparseness or physical illumination difference also routes to LoFTR.
- `TileMatchTask.route_metadata` is now preserved in both tile task payloads and deep manifest task records.
- Legacy deep manifest payloads without `route_metadata` remain loadable and restore `None`.
- `_build_tile_route_metadata()` is pure and does not open cubes; it converts illumination evidence to payload and delegates routing to `route_matcher_for_tile()`.
- `_apply_tile_route_metadata_to_tasks()` creates new task objects and leaves original tasks unchanged.
- Future integration must avoid mixing global tile indexes with filtered candidate-window order. Route metadata should either be generated after prefiltering in the same order as `TileMatchTask` construction, or use explicit stable tile IDs carried through both structures.
- `image_match.py` metadata currently stores `match_visualization` at top level in the metadata sidecar, not under `image_match`. Reporting code that wants RANSAC fallback counts must check top-level `metadata["match_visualization"]["ransac"]`.
- Polar adaptive summary rows use prefixed `tile_illumination_*` fields to avoid overwriting existing generic `tile_count` and `skipped_tile_count` fields.
- Focused validation passed for the scaffolded tile illumination modules, adaptive routing helpers, deep manifest preservation, pipeline option forwarding, and polar summary extraction:
  - 205 tests OK, 1 skipped for the combined image-match/pipeline suite.
  - `tests/smoke_import.py` passed under `MPLBACKEND=Agg`.
  - 51 matcher comparison tests passed, including tile illumination and RANSAC summary extraction.
- `image_match.py` now computes and attaches physical tile illumination metadata after candidate-window prefiltering:
  - `adaptive_routing.tile_illumination.source_metadata`;
  - `adaptive_routing.tile_illumination.summary`;
  - `adaptive_routing.tile_illumination.pairs`.
- Physical tile illumination sampling is currently metadata-only. It does not yet alter matcher execution. The next implementation boundary is to combine these `TileIlluminationPair` records with per-tile texture/keypoint evidence, build route metadata, and partition execution by selected matcher.
- Physical tile illumination route metadata is now generated:
  - per-tile left/right texture probes are computed from the actual DOM windows;
  - `texture_sparseness = 1.0 - mean(left.real_texture_score, right.real_texture_score)`;
  - route metadata records `selected_route`, backend `selected_matcher`, execution environment, keypoint counts/densities, and the physical illumination payload;
  - summary records route distributions by all sampled tiles and by fully projectable tiles.
- The runtime still executes one matcher for the pair. The next boundary is execution grouping: split tile tasks by `selected_route`/`selected_matcher`, run classic SIFT+FLANN in `asp360_new`, export/run/import deep groups in `deep-learning`, then merge per-tile results.
- Task 11 now splits export-mode tile tasks by per-tile route metadata:
  - `sift_flann` remains a classic `asp360_new` group and is reported in export metadata as classic group/task counts;
  - `sift_lightglue`, `superpoint_lightglue`, and `loftr` are deep-learning groups;
  - each deep group receives its own manifest workspace, so routes that share the same backend matcher such as `sift_lightglue` and `superpoint_lightglue` do not collide;
  - every deep manifest task preserves the original per-tile `route_metadata`, including selected route, backend matcher, execution environment, and deep preset path.
- Export mode remains backward-compatible:
  - when no tile route metadata is present, the previous single deep-matcher manifest export path is used;
  - grouped export only activates when at least one candidate tile has route metadata.
- The remaining architecture boundary is executing/importing mixed results:
  - classic tile matching for `sift_flann` groups still needs a batch runner path in `asp360_new`;
  - deep grouped manifest execution still occurs in the separate `deep-learning` environment;
  - imported deep results and classic results still need to be merged into one pair-level `.key` output with per-tile provenance.
- Task 12 added the minimal helper layer for that boundary:
  - `_run_classic_route_groups()` executes classic `asp360_new` tile groups through the existing tile matcher call boundary and summarizes group/task/match counts;
  - `import_grouped_deep_match_manifest_results()` imports multiple grouped deep manifests and merges their keypoints into one pair-level keypoint set, with per-manifest route summaries;
  - `_merge_classic_and_deep_tile_results()` merges classic `TileMatchResult` points and imported deep `KeypointFile` pairs into one final left/right keypoint pair.
- The end-to-end orchestration is still intentionally not complete:
  - export mode can group deep manifests and now has a classic execution helper, but it does not yet persist classic tile results across a later `deep-learning` run;
  - CLI import mode still imports one manifest path by default;
  - the next step should wire grouped manifest paths plus persisted classic results into a single import/merge workflow before any full 16-pair benchmark rerun.
- Task 13 wires that workflow at the image-match CLI/API level:
  - during mixed-route export, classic `sift_flann` groups run in `asp360_new` and persist classic key files under the deep-match temp root; the paths are recorded in `deep_match_export.classic_results`;
  - after `deep-learning` fills the grouped manifests, import mode can combine repeated `--grouped-deep-match-manifest` paths with `--classic-left-key` and `--classic-right-key`;
  - the final import writes one pair-level left/right `.key` output and reports `mixed_route_import.classic_point_count` and `mixed_route_import.deep_point_count`;
  - the old single-manifest import path remains available for fixed-method deep runs.
- Remaining boundary before full benchmark:
  - run a small real-data mixed-route smoke with one pair and limited tiles;
  - verify the deep-learning runner accepts each grouped manifest and writes NPZ files;
  - verify the returned import command uses the persisted classic key paths and all grouped manifest paths;
  - only then rerun the selected 16-pair benchmark.
- Task 14 real-data smoke completed the grouped deep export -> deep-learning NPZ -> import `.key` loop on a reduced real LRO NAC pair:
  - output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/tile_illumination_mixed_route_smoke_20260603`;
  - export route distribution for `dom_REDUCED_M110860982RE.cub` vs `dom_REDUCED_M110881352RE.cub`: `{"loftr": 12}`;
  - grouped LoFTR export produced 7 valid task arrays and skipped 5 invalid/nonprojectable tasks;
  - a 512x512 real-data crop smoke in `deep-learning` produced 236 LoFTR matches with `invalid_mask_removed_count=0`;
  - import returned `status=merged_mixed_route_results` and wrote 236-point `final_512_left.key` / `final_512_right.key`.
- The Task 14 smoke did not naturally produce classic `sift_flann` key files:
  - the first sparse-consistent pair routed all 12 tiles to LoFTR;
  - a second rich-consistent pair with 4096 tiles also routed all 4 tiles to LoFTR;
  - this suggests the current hard keypoint/sparseness rules are conservative on the tested real DOMs, or the current texture evidence still underestimates usable SIFT texture after radiometric masking.
- Two real integration defects were fixed before full benchmark:
  - CLI default mixed-import args were leaking into non-import `match_dom_pair()`;
  - grouped LoFTR manifests had correct top-level route config but stale SIFT+LightGlue task-level runtime config, which caused the deep-learning runner to reject the manifest.
- LoFTR smoke size matters:
  - the full 2048x2048 LoFTR task exited without NPZ/log output on CPU;
  - the 512x512 real crop completed successfully;
  - full benchmark execution should either use smaller deep tiles, GPU, or a guarded per-task size policy before running many LoFTR tasks.
- Task 15 identified why real routing was previously all LoFTR:
  - rich tiles already had high keypoint evidence, so the hard keypoint-count/density rule was not the main cause;
  - the main cause was `real_texture_score = valid_pixel_ratio * texture_components`, which penalized partially valid polar DOM tiles even when their valid pixels were strongly textured;
  - after removing the direct valid-pixel-ratio multiplier, the same sparse-consistent real pair produced a true mixed route distribution: `{"superpoint_lightglue": 2, "sift_lightglue": 2, "sift_flann": 3, "loftr": 5}`.
- Task 15 true mixed-route smoke succeeded:
  - export persisted classic SIFT+FLANN keys with 2853 points;
  - deep manifests were generated for SIFT+LightGlue and SuperPoint+LightGlue;
  - SuperPoint+LightGlue 512x512 real crop produced 7 matches with no invalid-mask removals;
  - final import merged classic and deep outputs into `final_mixed_left.key` / `final_mixed_right.key` with 2860 points.
- SIFT+LightGlue still needs follow-up:
  - the 512x512 real crop failed in `deep-learning` with `ValueError: array is not broadcastable to correct shape`;
  - import handled the failed manifest correctly, but this backend-specific failure should be debugged before using SIFT+LightGlue as a production route in the full benchmark.
- Real-data geometry smoke must use a real ISISDATA tree, not the unit-test mock tree. With `ISISDATA=/media/gengxun/My Passport/data`, a single tile produced one fully projectable pair:
  - left DOM sample/line: `(2768.0, 1200.0)`;
  - right DOM sample/line: `(2768.0, 1143.0)`;
  - azimuth difference: `1.3686125681990404` degrees;
  - elevation difference: `0.025346435004621526` degrees.
- The same smoke tile currently routes to LoFTR because the 33x33 diagnostic window has low keypoint evidence:
  - left keypoints: `20`;
  - right keypoints: `9`;
  - route distribution: `{"loftr": 1}`.

## Representative Point Policy

The proposed policy is intentionally bounded:

- exactly one physical solar-geometry sample per tile or compact pair;
- deterministic center-first selection;
- nearest pixel-available and source-projectable fallback only once;
- no random sampling;
- no iterative unlimited solar-angle calls;
- no per-pixel solar geometry.

This is appropriate for lunar south-pole DOMs, where tile centers may lie in black/no-data regions but valid image strips may cross tile boundaries.

Phase 2 refines the validity model:

- `pixel_available`: finite DOM pixel and not true ISIS no-data/special pixel.
- `radiometric_valid_for_matching`: passes matching masks such as 0.1/99.9 percentile filtering.
- `source_projectable`: DOM point projects to the source/original camera and can produce finite solar geometry.

Representative-point selection must use `pixel_available + source_projectable`. It must not use `radiometric_valid_for_matching` as a hard exclusion, because shadowed terrain can be invalid for feature matching while still physically meaningful for illumination sampling.

The design SPEC is written at:

- `docs/superpowers/specs/2026-06-02-tile-illumination-adaptive-routing-design.md`

## Scientific Framing

The manuscript should distinguish:

- physical tile illumination: computed from the DOM source/original cube camera geometry and suitable for adaptive routing evidence;
- display brightness gap: useful for visual explanation but not a physical lighting proxy.

Suggested claim boundary:

> An illumination-aware tile-level adaptive routing strategy was used for long-strip polar NAC images, while a pair-center approximation was retained for compact lower-latitude stereo pairs.

## Affected Areas

- Adaptive routing:
  - pair-level decision model must be extended or complemented by tile-level decisions.
- Tile matching:
  - `TileMatchTask` may need route metadata or a sidecar mapping keyed by tile index.
- Deep manifests:
  - task records should preserve tile illumination evidence and selected route provenance.
- ControlNet experiments:
  - batch orchestrators need to run grouped manifests and import multiple selected methods per pair.
- Figures:
  - method comparison should include route distribution by tile and success after RANSAC.
- Tests:
  - coordinate basis, invalid center fallback, no valid tile skip, manifest round-trip, and route grouping need coverage.

## Risks

- DOM-to-ground-to-original projection can fail near invalid projection areas or outside original image bounds.
- Camera calls may be expensive if accidentally performed per pixel rather than per tile.
- Hard-coding REDUCED cube path patterns would fail for DOMs generated from full-resolution original images.
- Repeated conda switching inside method or tile loops would add avoidable wall-time overhead and make benchmark timing harder to interpret.
- Mixed-method tile results can complicate `.key` merge and provenance unless tile IDs remain stable.
- Pair-level summary may hide tile-level route diversity unless reports include both levels.
- Existing unit tests may assume a single selected matcher per pair.

## Current Workspace Notes

- Active implementation worktree:
  - `/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/.worktrees/tile-illumination-adaptive-routing-20260602`
  - branch `feature/tile-illumination-adaptive-routing-20260602`.
- Main checkout remains a separate dirty branch and should not be used for this implementation.
- `print.prt` and `.gitignore` must remain out of commits/publish flows unless explicitly requested.
