# Findings: LRO Polar Adaptive-Tile Routing Benchmark

## Source Plans

This plan consolidates two previous plans:

- `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/`
- `.planning/2026-06-02-tile-illumination-adaptive-routing/`

The first plan provides the reduced-10m benchmark data, fixed-method baselines, prior pair-level adaptive baseline, and Nature-style figure/reporting scripts. The second plan provides the tile-level physical illumination architecture, representative-point policy, route metadata, grouped deep manifests, and mixed classic/deep import strategy.

## Data and Previous Outputs

- Reduced-10m data root:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`
- Selected pair CSV:
  `lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`
- Previous latest-parameter five-method output:
  `lro_polar_adaptive_routing_latest_params_20260602`
- Previous Phase 18 summary:
  - LoFTR: raw 31,565; retained 11,172; retained fraction 0.3539; runtime 30.70 min.
  - SuperPoint+LightGlue: raw 3,439; retained 770; retained fraction 0.2239; runtime 8.37 min.
  - SIFT+LightGlue: raw 5,348; retained 3,906; retained fraction 0.7304; runtime 1.58 min.
  - SIFT+FLANN: raw 3,611; retained 2,757; retained fraction 0.7635; runtime 1.48 min.
  - Adaptive pair-level/prior-only: raw 5,511; retained 4,220; retained fraction 0.7657; runtime 4.99 min.

The previous adaptive row should be treated as `Adaptive-pair` for ablation, not as the new main adaptive result.

## Main Scientific Framing

Main claim should focus on:

> Tile-level physical illumination adaptive routing improves robust control-point matching under heterogeneous lunar polar illumination.

Do not frame the main adaptive method as pair-level method selection. For long-strip NAC images, a stereo pair can contain tiles with different texture and illumination conditions. A single pair-center or pair-level decision can hide this heterogeneity.

## Method Set

Main methods:

- SIFT+FLANN
- SIFT+LightGlue
- SuperPoint+LightGlue
- LoFTR
- Adaptive-tile

Supplementary/ablation:

- Adaptive-pair

## Tile Validity and Shadow Handling

The valid-pixel threshold is a minimum valid-pixel ratio. `0.02` means skip a tile only when fewer than 2% of pixels remain valid.

This is intentionally less strict than `0.10` because LRO NAC south-pole shadow scenes can have large dark/invalid regions after the 0.1/99.9 percentile mask. A strict threshold could skip tiles containing small but matchable textured regions.

Recommended default for this plan:

- `--valid-pixel-percent-threshold 0.02`
- `--min-valid-pixels 256`
- `--valid-intensity-lower-percent 0.1`
- `--valid-intensity-upper-percent 99.9`

## Representative Point Policy

Tile illumination representative-point selection must distinguish:

- `pixel_available`: finite DOM pixel and not true no-data/special pixel.
- `radiometric_valid_for_matching`: passes feature-matching masks such as percentile filtering.
- `source_projectable`: DOM point can be projected to the source/original camera cube and can produce finite solar geometry.

Representative-point selection must use `pixel_available + source_projectable`. It must not use `radiometric_valid_for_matching` as a hard exclusion, because shadowed terrain can be physically meaningful for illumination sampling even when excluded from matching.

Policy:

1. Try tile center.
2. If center fails, find the nearest bounded pixel that is pixel-available and source-projectable.
3. If no projectable point exists, skip illumination routing for that tile and record the failure reason.
4. Use solar azimuth, incidence angle, and solar elevation (`90.0 - incidence_angle`) from the source/original cube camera geometry.

## Execution Strategy

Fixed baselines use one method for all selected pairs.

Adaptive-tile uses mixed per-tile routes:

- Build per-tile route metadata first.
- Partition tiles by selected route and execution environment.
- Run SIFT+FLANN route tiles in `asp360_new`.
- Export deep route tiles as grouped manifests by matcher method.
- Run deep grouped manifests in `deep-learning`.
- Import deep results back in `asp360_new`.
- Merge classic and deep route outputs into one pair-level `.key` output.

Avoid tile-by-tile deep matcher switching. The benchmark should batch deep work by method/group to avoid repeated model initialization overhead.

## Reporting Requirements

Required outputs:

- Raw match count
- RANSAC retained count
- RANSAC dropped count
- Retained fraction
- RANSAC-successful pair count
- Runtime
- Tile route distribution
- Representative point status distribution
- Illumination difference diagnostics
- RANSAC-filtered match-line PNGs
- Nature-style source CSV/JSON
- SVG/PDF/TIFF/PNG figure outputs

## Representative Four-Pair Case Set

The 16-pair run is useful as the reproducible candidate pool and aggregate support, but it is too broad for the main narrative. For manuscript case-study figures, use four representative pairs:

| Role | Latitude interval | Texture | Pair tag | Adaptive-pair retained | Adaptive-tile retained | Delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Near-pole sparse | 85-to-89.9S | sparse, inconsistent lighting | `REDUCED_M1109027420LE.echo.cal__REDUCED_M140550700LE.echo.cal` | 0 | 11 | +11 |
| Near-pole rich | 85-to-89.9S | rich, inconsistent lighting | `REDUCED_M1203964116RE.echo.cal__REDUCED_M140577849LE.echo.cal` | 0 | 8 | +8 |
| Near-80S sparse | 80-to-82S | sparse, inconsistent lighting | `REDUCED_M1232286275LE.echo.cal__REDUCED_M173554018RE.echo.cal` | 1 | 5 | +4 |
| Near-80S rich | 80-to-82S | rich, consistent lighting | `REDUCED_M1137240043RE.echo.cal__REDUCED_M1137247155LE.echo.cal` | 6 | 13 | +7 |

Use the two sparse/inconsistent rows to make the low-texture claim: Adaptive-tile crosses or restores the RANSAC-success threshold where Adaptive-pair fails or remains below threshold. Use the two rich rows as controls showing that the method is not only a low-texture rescue case.

Source CSV:
`.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_case_selection.csv`

## Risks

- If route metadata is missing, adaptive export can fall back to pair-level behavior; this must be detected before the full run.
- Per-pair grouped manifests may still have more startup overhead than global method-level manifests.
- DOM source metadata must point to the actual source/original cube used to generate the DOM; do not hard-code a REDUCED path pattern for future generality.
- `print.prt` can be modified by ISIS commands and must not be staged accidentally.
- Some previous outputs were generated before the final tile-level main-method framing, so filenames may say `adaptive` while scientifically representing `Adaptive-pair`.

## Useful Existing Code

- `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`
- `examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py`
- `examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py`
- `examples/controlnet_construct/experiments/summarize_lro_polar_adaptive_routing_benchmark.py`
- `examples/image_match/image_match.py`
- `examples/image_match/adaptive_routing.py`
- `examples/image_match/tile_illumination.py`
- `examples/image_match/tile_illumination_geometry.py`
- `examples/learning_methods/run_deep_match_manifest.py`

## Phase 2 Implementation Audit

- `examples/image_match/image_match.py` contains tile-level physical illumination metadata construction, per-tile route metadata, route grouping by execution environment, classic-route execution in `asp360_new`, grouped deep manifest export for deep routes, and mixed classic/deep import merge.
- `tests/unitTest/image_match_adaptive_routing_unit_test.py` covers physical tile illumination sampling, route partitioning, grouped deep export, classic route execution, and persisted classic route results.
- `tests/unitTest/image_match_deep_manifest_unit_test.py` covers grouped deep manifest metadata preservation and mixed-route import merging.
- Missing glue found during audit: the outer experiment orchestrator and batch wrapper did not expose/forward `--min-valid-pixels`, `--valid-intensity-lower-percent`, `--valid-intensity-upper-percent`, or `--dom-source-metadata-csv`.
- Fix applied: `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py` now forwards the tile validity, valid-intensity, and DOM source metadata arguments to the batch runner.
- Fix applied: `examples/controlnet_construct/run_image_match_batch_example.sh` now parses/logs these arguments and forwards them to `examples/image_match/image_match.py`.
- Test coverage added: `test_run_image_match_batch_example_forwards_tile_validity_and_source_metadata`.
- Focused validation passed: `python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_deep_manifest_unit_test tests.unitTest.image_match_tile_illumination_unit_test -v` ran 225 tests, OK, with 1 expected skip.

## Phase 3 Smoke Results

- One-pair Adaptive-tile export smoke output root:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_smoke_20260603`
- The first attempt failed because `ISISDATA` pointed at `tests/data/isisdata/mockup`; real LRO source-camera projection needs the full conda ISISDATA tree. Rerun with `ISISDATA=$CONDA_PREFIX/data` succeeded.
- Smoke pair:
  `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal`
- Export result:
  - status: `exported_grouped_for_mixed_route`
  - DOM source metadata: ready, 44 lookup entries
  - tile illumination status: sampled
  - candidate tiles: 60
  - tiles after validity prefilter: 32
  - route distribution by tile: `sift_flann=14`, `superpoint_lightglue=2`, `loftr=11`, `sift_lightglue=5`
  - classic SIFT+FLANN route: 14 tasks, 10 matched tasks, 3479 matches
  - deep export: 3 groups, 18 routed deep tasks, 6 exported tasks, 12 skipped by validity
  - exported deep tasks: SuperPoint+LightGlue 2, SIFT+LightGlue 4, LoFTR 0
- Deep-learning smoke execution:
  - SIFT+LightGlue grouped manifest: 4/4 tasks completed, 519 total matches
  - SuperPoint+LightGlue grouped manifest: 2/2 tasks completed, 27 total matches
- Mixed-route import:
  - status: `merged_mixed_route_results`
  - final point count: 4025
  - classic point count: 3479
  - deep point count: 546
  - imported grouped deep tasks: 6
  - failed/missing/empty imported deep tasks: 0
- RANSAC-filtered smoke visualization:
  - output PNG: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_smoke_20260603/adaptive/import_ransac_viz/dom_REDUCED_M110860982RE__dom_REDUCED_M110881352RE__20260603T204259.png`
  - RANSAC input matches: 4025
  - retained: 3507
  - dropped: 518
  - mode: loose, threshold 3.0 px

## Phase 4 Fixed-Method Baseline Results

### SIFT+FLANN

- Output root:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/sift_flann`
- Summary JSON:
  `sift_flann_large_dom_match_summary.json`
- Summary CSV:
  `sift_flann_large_dom_match_summary.csv`
- Execution environment: `asp360_new`, with real `ISISDATA=$CONDA_PREFIX/data`
- Parameters: 1024x1024 tiles, 128 overlap, `valid-pixel-percent-threshold=0.02`, `min-valid-pixels=256`, valid-intensity percentiles 0.1/99.9, tile validity prefilter enabled, DOM source metadata CSV forwarded.
- Result:
  - selected pairs: 16
  - metadata files: 16
  - matched pairs: 16
  - failed metadata: 0
  - raw matches: 3761
  - RANSAC-retained matches: 2846
  - RANSAC-dropped matches: 915
  - retained fraction: 0.7567
  - RANSAC-successful pairs using retained >= 4: 14
- Highest raw-count pairs:
  - `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal`: raw 1498, retained 1305
  - `REDUCED_M110840613RE.echo.cal__REDUCED_M110860982RE.echo.cal`: raw 1484, retained 1288
  - `REDUCED_M173710225LE.echo.cal__REDUCED_M173717012LE.echo.cal`: raw 312, retained 182

### Fixed Deep Exports

- Export execution environment: `asp360_new`, with real `ISISDATA=$CONDA_PREFIX/data`.
- Methods exported:
  - LoFTR
  - SuperPoint+LightGlue
  - SIFT+LightGlue
- Shared export parameters: 1024x1024 tiles, 128 overlap, `valid-pixel-percent-threshold=0.02`, `min-valid-pixels=256`, valid-intensity percentiles 0.1/99.9, tile validity prefilter enabled, DOM source metadata CSV forwarded.
- Output roots:
  - `lro_polar_adaptive_tile_routing_20260603/loftr`
  - `lro_polar_adaptive_tile_routing_20260603/superpoint_lightglue`
  - `lro_polar_adaptive_tile_routing_20260603/sift_lightglue`
- Export result:
  - LoFTR: 16/16 manifests, 107 exported tile tasks, 90 skipped invalid/filtered tile tasks, failed metadata 0
  - SuperPoint+LightGlue: 16/16 manifests, 107 exported tile tasks, 90 skipped invalid/filtered tile tasks, failed metadata 0
  - SIFT+LightGlue: 16/16 manifests, 107 exported tile tasks, 90 skipped invalid/filtered tile tasks, failed metadata 0

### Fixed Deep Inference

- Deep execution environment: `deep-learning`, CPU, `torch_num_threads=8`, `num_workers=1`.
- Manifest runner summary:
  - SIFT+LightGlue: 16 manifests, 107/107 tasks succeeded, failed 0, raw/importable matches 5621; task statuses `matched=99`, `matched_no_points=8`.
  - SuperPoint+LightGlue: 16 manifests, 107/107 tasks succeeded, failed 0, raw/importable matches 3545; task statuses `matched=98`, `matched_no_points=9`.
  - LoFTR: 16 manifests, 107/107 tasks succeeded, failed 0, raw matches 32766, importable matches 32610 after invalid-mask filtering; task statuses `matched=107`.
- Combined runner summary file:
  `lro_polar_adaptive_tile_routing_20260603/fixed_deep_manifest_run_summaries.json`

### Fixed Deep Import and RANSAC Results

- Import execution environment: `asp360_new`, with real `ISISDATA=$CONDA_PREFIX/data`.
- Batch import issue found: `run_image_match_batch_example.sh --deep-match-mode import` expects each manifest at `<deep_match_workspaces>/<original_pair_tag>/tasks.json`, while export creates DOM-id-plus-hash workspaces. External disk symlink creation was not permitted, so each pair was imported directly with the cached `manifest_path` from export metadata.
- Import summary files:
  - `sift_lightglue/deep_match_import_manifests.json`
  - `superpoint_lightglue/deep_match_import_manifests.json`
  - `loftr/deep_match_import_manifests.json`
- Imported pair-level results:
  - SIFT+LightGlue: 16/16 imported pairs, 99 imported non-empty tasks, missing 0, failed 0, raw matches 5621, RANSAC-retained 4048, dropped 1573, retained fraction 0.7202, RANSAC-successful pairs 12.
  - SuperPoint+LightGlue: 16/16 imported pairs, 98 imported non-empty tasks, missing 0, failed 0, raw matches 3545, RANSAC-retained 830, dropped 2715, retained fraction 0.2341, RANSAC-successful pairs 15.
  - LoFTR: 16/16 imported pairs, 107 imported non-empty tasks, missing 0, failed 0, raw matches 32610, RANSAC-retained 11767, dropped 20843, retained fraction 0.3608, RANSAC-successful pairs 16.
- Highest raw-count fixed deep pairs:
  - SIFT+LightGlue: `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal` raw 2141, retained 1948; `REDUCED_M110840613RE.echo.cal__REDUCED_M110860982RE.echo.cal` raw 1845, retained 1704; `REDUCED_M173710225LE.echo.cal__REDUCED_M173717012LE.echo.cal` raw 579, retained 297.
  - SuperPoint+LightGlue: `REDUCED_M110840613RE.echo.cal__REDUCED_M110860982RE.echo.cal` raw 843, retained 222; `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal` raw 745, retained 288; `REDUCED_M173710225LE.echo.cal__REDUCED_M173717012LE.echo.cal` raw 564, retained 176.
  - LoFTR: `REDUCED_M110840613RE.echo.cal__REDUCED_M110860982RE.echo.cal` raw 8999, retained 6468; `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal` raw 7634, retained 4982; `REDUCED_M173710225LE.echo.cal__REDUCED_M173717012LE.echo.cal` raw 4302, retained 127.

## Phase 5 Adaptive-Tile Full Run

- Output root:
  `lro_polar_adaptive_tile_routing_20260603/adaptive`
- Export/classic execution environment: `asp360_new`, with real `ISISDATA=$CONDA_PREFIX/data`.
- Deep execution environment: `deep-learning`, CPU, `torch_num_threads=8`, `num_workers=1`.
- Import/merge execution environment: `asp360_new`, with real `ISISDATA=$CONDA_PREFIX/data`.
- Adaptive export/classic route result:
  - selected pairs: 16
  - metadata files: 16
  - failed metadata: 0
  - total candidate tiles: 369
  - tiles after validity prefilter: 197
  - classic route tasks: 110
  - classic route matches persisted for mixed import: 9082
  - deep route candidate tasks: 87
  - exported deep tasks: 13
  - skipped deep tasks: 74
  - non-empty grouped deep manifests: 7
- Adaptive grouped deep execution:
  - manifests: 7/7 completed
  - tasks: 13/13 succeeded
  - failed tasks: 0
  - combined deep matches imported later: 666
  - summary file: `adaptive/adaptive_deep_manifest_run_summaries.json`
- Adaptive mixed import:
  - summary file: `adaptive/adaptive_mixed_import_summary.json`
  - final merged pairs: 16/16
  - status: `merged_mixed_route_results` for all 16 pairs
  - classic point count: 9082
  - deep point count: 666
  - raw merged matches: 9748
  - RANSAC-retained matches: 7736
  - RANSAC-dropped matches: 2012
  - retained fraction: 0.7936
  - RANSAC-successful pairs using retained >= 4: 14
  - imported deep tasks: 12
  - failed deep import tasks: 0
  - missing deep result tasks: 0
- Highest raw-count Adaptive-tile pairs:
  - `REDUCED_M110840613RE.echo.cal__REDUCED_M110860982RE.echo.cal`: raw 4041, retained 3610
  - `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal`: raw 4025, retained 3507
  - `REDUCED_M173710225LE.echo.cal__REDUCED_M173717012LE.echo.cal`: raw 808, retained 541

## Five-Method Final Matching Summary

| Method | Raw matches | RANSAC retained | Dropped | Retained fraction | Successful pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT+FLANN | 3761 | 2846 | 915 | 0.7567 | 14 |
| SIFT+LightGlue | 5621 | 4048 | 1573 | 0.7202 | 12 |
| SuperPoint+LightGlue | 3545 | 830 | 2715 | 0.2341 | 15 |
| LoFTR | 32610 | 11767 | 20843 | 0.3608 | 16 |
| Adaptive-tile | 9748 | 7736 | 2012 | 0.7936 | 14 |

## Phase 6 Adaptive-Tile Route and Illumination Diagnostics

- Diagnostic source files generated under:
  `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase6_diagnostics/`
- Files:
  - `adaptive_tile_phase6_diagnostics_summary.json`
  - `adaptive_tile_route_distribution_by_pair.csv`
  - `adaptive_tile_route_illumination_by_tile.csv`
- Input summary:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/adaptive/adaptive_large_dom_match_summary.json`
- Aggregated Adaptive-tile routed tiles:
  - pairs: 16
  - routed tiles after validity prefilter: 197
  - projectable illumination tiles: 133
  - skipped illumination tiles: 64
- Route distribution across routed tiles:
  - SIFT+FLANN: 110
  - LoFTR: 72
  - SIFT+LightGlue: 12
  - SuperPoint+LightGlue: 3
- Route distribution across projectable illumination tiles:
  - SIFT+FLANN: 110
  - SIFT+LightGlue: 12
  - SuperPoint+LightGlue: 3
  - LoFTR: 8
- Illumination representative-point statuses:
  - `center_projectable`: 72
  - `nearest_projectable_pixel`: 234
  - `no_projectable_pixel`: 88
- Illumination tile statuses:
  - `ok`: 133
  - `left_failed`: 31
  - `right_failed`: 9
  - `both_failed`: 24
- Illumination difference score over projectable tiles:
  - count: 133
  - min: 0.0000878785
  - mean: 0.0257080
  - median: 0.000874726
  - p90: 0.169672
  - max: 0.210463
- Interpretation note: LoFTR dominates non-projectable or sparse-texture tiles in the routed-tile distribution, but only 8 LoFTR tiles had full illumination representative points. This supports reporting LoFTR route count separately from physically projectable illumination diagnostics.

## Phase 7 Five-Method Figure Source Data

- RANSAC visualization/source summary regenerated for all five methods:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/ransac_match_visualization_summary.csv`
- Summary row counts:
  - `ransac_match_visualization_summary.csv`: 80 pair-method rows plus header
  - `five_method_pair_summary.csv`: 80 pair-method rows plus header
  - `five_method_method_summary.csv`: 5 method rows plus header
- Nature-style source data and main figure outputs:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/nature_figure_inputs/`
- Generated files:
  - `five_method_match_comparison_source_data.json`
  - `five_method_pair_summary.csv`
  - `five_method_method_summary.csv`
  - `five_method_match_comparison.svg`
  - `five_method_match_comparison.pdf`
  - `five_method_match_comparison.tiff`
  - `five_method_match_comparison.png`
- File sizes after generation:
  - SVG: 40,876 bytes
  - PDF: 40,252 bytes
  - TIFF: 57,039,650 bytes
  - PNG: 143,616 bytes
- Runtime provenance update: `plot_lro_polar_match_method_comparison.py` now accepts per-manifest deep runtime files named either `deep_match_run_summary.json` or `manifest_run_summary.json`. After redraw, Figure D has fixed deep method runtimes:
  - LoFTR: 35.6114 min, `runtime_source=deep_task_started_finished_sum`, 16 summaries, 107 tasks, 0 failed
  - SuperPoint+LightGlue: 12.1320 min, `runtime_source=deep_task_started_finished_sum`, 16 summaries, 107 tasks, 0 failed
  - SIFT+LightGlue: 2.4056 min, `runtime_source=deep_task_started_finished_sum`, 16 summaries, 107 tasks, 0 failed
  - SIFT+FLANN remains a command-to-summary mtime proxy: 2.0845 min
  - Adaptive uses deep task runtime plus command-to-summary mtime proxy: 16.5139 min
- Redrawn file sizes:
  - SVG: 41,419 bytes
  - PDF: 40,280 bytes
  - TIFF: 57,039,650 bytes
  - PNG: 146,725 bytes

### Supplementary Adaptive-Pair vs Adaptive-Tile Ablation

- Supplementary source data generated under:
  `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/`
- Files:
  - `adaptive_pair_vs_tile_ablation_by_pair.csv`
  - `adaptive_pair_vs_tile_ablation_summary.json`
  - `figure_source_data_provenance_check.json`
  - `tile_case_comparison_manifest.json`
- Adaptive-pair input:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/adaptive/ransac_match_visualization_summary.csv`
- Adaptive-tile input:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/adaptive/ransac_match_visualization_summary.csv`
- Ablation totals:
  - Adaptive-pair: raw 13,930; RANSAC retained 12,767; retained fraction 0.9165; successful pairs 9.
  - Adaptive-tile: raw 9,748; RANSAC retained 7,736; retained fraction 0.7936; successful pairs 14.
  - Tile minus pair: raw -4,182; retained -5,031; successful pairs +5.
  - Pair-wise retained comparison: Adaptive-tile higher on 8 pairs, Adaptive-pair higher on 5 pairs, equal on 3 pairs.
- Interpretation note: Adaptive-pair retained more total matches because it heavily concentrates on high-yield pairs, while Adaptive-tile improved retained>=4 pair coverage. Treat this as supplementary because the pair baseline comes from 2026-06-02 prior-only outputs rather than a same-output-root rerun.

### Figure and Case-Study Provenance

- Figure/source provenance report:
  `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/figure_source_data_provenance_check.json`
- SVG label checks found expected method labels and axis labels in `five_method_match_comparison.svg`.
- Existing case-study figure outputs were recorded rather than regenerated:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602/tile_case_comparison_latest_params`
- Case-study manifest:
  `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/tile_case_comparison_manifest.json`
- Recorded case-study file counts:
  - `rich_texture_small_lighting_gap`: 12 files
  - `sparse_texture_large_lighting_gap`: 7 files
- Runtime provenance recovered from manifest summaries:
  - Fixed SIFT+LightGlue: 16 manifests, 107 tasks, task-runtime sum 144.34 s.
  - Fixed SuperPoint+LightGlue: 16 manifests, 107 tasks, task-runtime sum 727.92 s.
  - Fixed LoFTR: 16 manifests, 107 tasks, task-runtime sum 2,136.68 s.
  - Adaptive deep routes: SIFT+LightGlue 5 manifests/10 tasks, SuperPoint+LightGlue 2 manifests/3 tasks.

## Phase 8 Verification and Handoff

- Smoke import verification:
  - command: `python tests/smoke_import.py`
  - result: `smoke import ok`
  - environment: `asp360_new`, `ISISDATA=tests/data/isisdata/mockup`
- Focused unit verification:
  - command: `python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_deep_manifest_unit_test tests.unitTest.image_match_tile_illumination_unit_test -v`
  - result: `Ran 225 tests in 47.830s`, `OK (skipped=1)`
- Output existence verification:
  - Phase 6 diagnostics exist under `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase6_diagnostics/`
  - Phase 7 supplementary files exist under `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/`
  - Main five-method source data and figures exist under `lro_polar_adaptive_tile_routing_20260603/nature_figure_inputs/`
- Git/worktree verification:
  - `.gitignore` is not modified in `git status --short`.
  - `print.prt` is modified and should remain out of staging/commits as an ISIS runtime artifact.
  - Modified tracked files besides `print.prt`: `.planning/.active_plan`, `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`, `examples/controlnet_construct/run_image_match_batch_example.sh`, and `tests/unitTest/controlnet_construct_pipeline_unit_test.py`.
  - Untracked planning directory: `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/`.

## Current Notes

- A SIFT+FLANN reduced rerun output exists under:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_reduced_rerun_20260603/sift_flann`
- It has 16 match metadata JSON files and no active matching process was found when checked.
- This new plan should not automatically continue that older Phase 19 rerun; it should first audit whether the output should be reused or discarded.

## Representative Four-Pair Rerun

- Representative rerun output root:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_representative_4pair_20260604`
- Selection files:
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/representative_4pair_paths.csv`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_case_selection.csv`
- Result files:
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_test_results.csv`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_adaptive_route_summary.csv`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_test_summary.md`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_quantitative_summary.csv`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_quantitative_summary.json`
  - `.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_retained_line_plot.{png,pdf,svg}`
- Four cases: near-pole sparse/inconsistent, near-pole rich/inconsistent, near-80S sparse/inconsistent, and near-80S rich/consistent.
- Deep inference completed with 55/55 tasks succeeded and 0 failed.
- Four-case method totals:
  - SIFT+FLANN: raw 131; RANSAC retained 25; successful pairs 4.
  - SIFT+LightGlue: raw 344; RANSAC retained 35; successful pairs 3.
  - SuperPoint+LightGlue: raw 339; RANSAC retained 45; successful pairs 4.
  - LoFTR: raw 3429; RANSAC retained 61; successful pairs 4.
  - Adaptive-tile: raw 249; RANSAC retained 37; successful pairs 4.
- Adaptive-tile retained counts by representative case:
  - near-pole sparse/inconsistent: 11 retained from 25 raw matches.
  - near-pole rich/inconsistent: 8 retained from 26 raw matches.
  - near-80S sparse/inconsistent: 5 retained from 22 raw matches.
  - near-80S rich/consistent: 13 retained from 176 raw matches.
- Interpretation: this subset supports the method rationale better than a broad 16-pair timing-only table. Adaptive-tile produces fewer raw matches than fixed LoFTR but preserves successful pair coverage while avoiding indiscriminate deep matching. In sparse low-texture cases, it keeps enough geometrically consistent matches; in rich/consistent cases, it keeps the simpler classic route where that route is already appropriate.

## Figure C Coverage Threshold Update

- Updated `five_method_match_comparison` Panel C to count pair coverage only when a pair has at least 10 RANSAC-retained matches.
- Updated source data fields:
  - pair-level `coverage_min_retained_match_threshold=10`
  - pair-level `coverage_pair_passes_threshold`
  - method-level `ransac_min10_pair_count`
- Updated Panel C coverage counts:
  - LoFTR: 9/16
  - SuperPoint+LightGlue: 10/16
  - SIFT+LightGlue: 6/16
  - SIFT+FLANN: 4/16
  - Adaptive-tile: 5/16
- Redrawn figure/source files:
  `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_20260603/nature_figure_inputs/five_method_match_comparison.{svg,pdf,tiff,png}`
- Redrawn file sizes:
  - SVG: 41,434 bytes
  - PDF: 40,751 bytes
  - TIFF: 57,039,650 bytes
  - PNG: 153,151 bytes
