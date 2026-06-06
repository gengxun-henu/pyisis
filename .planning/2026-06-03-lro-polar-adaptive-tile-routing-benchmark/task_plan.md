# Task Plan: LRO Polar Adaptive-Tile Routing Benchmark

## Goal

Run a reduced-10m LRO NAC south-pole benchmark whose main manuscript comparison uses five methods: SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, LoFTR, and Adaptive-tile. The adaptive method must use tile-level physical illumination routing rather than one pair-level route decision.

## Current Phase

All phases are complete. The remaining repository state is a dirty worktree containing planning artifacts, targeted wrapper/test code changes, and the local ISIS `print.prt` runtime artifact.

## Data Scope

- Data root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`
- Pair CSV: `lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`
- Original/source cubes: `REDUCED_*.echo.cal.cub` for this reduced-10m benchmark
- DOMs: 10 m/pixel reduced DOMs listed by the pair CSV
- The 16 selected pairs should be treated as the candidate/evidence pool. For manuscript case-study figures and narrative examples, use a four-pair representative subset rather than showing all 16 pairs.

## Representative Four-Pair Reporting Scope

Use four representative groups across latitude and texture:

| Role | Latitude interval | Texture | Pair folder | Main evidence |
| --- | --- | --- | --- | --- |
| Near-pole sparse | 85-to-89.9S | sparse, inconsistent lighting | `04_south-85-to-89.9_sparse-inconsistent_rank02_M1109027420LE__M140550700LE` | Adaptive-tile retained 11 RANSAC matches versus Adaptive-pair 0. |
| Near-pole rich | 85-to-89.9S | rich, inconsistent lighting | `07_south-85-to-89.9_rich-inconsistent_rank01_M1203964116RE__M140577849LE` | Adaptive-tile retained 8 RANSAC matches versus Adaptive-pair 0. |
| Near-80S sparse | 80-to-82S | sparse, inconsistent lighting | `12_south-80-to-82_sparse-inconsistent_rank02_M1232286275LE__M173554018RE` | Adaptive-tile retained 5 RANSAC matches versus Adaptive-pair 1. |
| Near-80S rich | 80-to-82S | rich, consistent lighting | `14_south-80-to-82_rich-consistent_rank02_M1137240043RE__M1137247155LE` | Adaptive-tile retained 13 RANSAC matches versus Adaptive-pair 6. |

Source table:
`.planning/2026-06-03-lro-polar-adaptive-tile-routing-benchmark/phase7_supplementary/representative_4pair_case_selection.csv`

This keeps the main example set compact while preserving two low-texture cases that directly show why Adaptive-tile is useful.

## Main Method Set

1. SIFT+FLANN
2. SIFT+LightGlue
3. SuperPoint+LightGlue
4. LoFTR
5. Adaptive-tile

Adaptive-pair is retained only as a supplementary or ablation baseline and must not be used as the main adaptive result.

## Core Parameters

- Tile size: `1024 x 1024`
- Tile overlap: `128`
- `valid-pixel-percent-threshold = 0.02`
- `min-valid-pixels = 256`
- `valid-intensity-lower-percent = 0.1`
- `valid-intensity-upper-percent = 99.9`
- Success metric: RANSAC-retained matches and RANSAC-successful pair count, not raw imported match count

## Execution Environments

- `asp360_new`: SIFT+FLANN, PyISIS/ISIS geometry, tile illumination metadata, manifest export/import, RANSAC summaries, plotting
- `deep-learning`: SIFT+LightGlue, SuperPoint+LightGlue, LoFTR inference
- Deep runtime defaults: `torch_num_threads=8`, `num_workers=1`
- Avoid repeated conda switching. Finish all `asp360_new` export/classic work, then run grouped deep manifests in `deep-learning`, then return to `asp360_new` for import/reporting.

## Adaptive-Tile Definition

Adaptive-tile must route per tile:

- Each tile selects a matcher independently.
- Representative point chain: DOM tile sample/line -> ground -> source/original cube camera projection -> solar azimuth/incidence/elevation.
- Use tile center first if it is pixel-available and source-camera-projectable.
- If center projection fails, search a bounded nearest pixel-available and source-projectable point inside the tile.
- If no source-projectable representative exists, record a skip/diagnostic reason.
- Keep `radiometric_valid_for_matching` separate from physical illumination representative-point selection. Radiometric percentile masks are used for matching, texture, and keypoint evidence, not as the only illumination exclusion rule.
- Preserve prior-only semantics: do not cascade to another matcher after a failed match.

## Adaptive-Tile Execution Strategy

- Build per-tile route metadata before matching.
- Partition tiles by selected route and execution environment.
- Run SIFT+FLANN route tiles in `asp360_new`.
- Export deep route tiles as grouped manifests by matcher method.
- Do not alternate deep matchers tile-by-tile.
- Run grouped deep manifests in `deep-learning`.
- Import grouped deep results and merge them with classic tile results into one pair-level `.key` output per stereo pair.
- Preserve route provenance for later pair summaries and figure source data.

## Phases

### Phase 1: Plan Initialization and Context Consolidation

- [x] Create this isolated planning directory
- [x] Read previous polar benchmark plan
- [x] Read tile-level physical illumination plan
- [x] Consolidate data paths, method set, parameter constraints, and execution rules
- [x] Record inherited findings and risks
- **Status:** complete

### Phase 2: Current Implementation Audit

- [x] Confirm current checkout contains tile-level physical illumination routing code
- [x] Confirm `match_original_gsd_lro_dom_pairs_large.py` forwards the required tile, validity, intensity, and deep handoff parameters
- [x] Confirm batch runner forwards DOM source metadata CSV for tile illumination
- [x] Confirm grouped deep manifests preserve selected route and tile metadata
- [x] Confirm import mode can merge classic route keys plus multiple grouped deep manifests
- [x] Identify any missing glue code needed for full Adaptive-tile benchmark execution
- **Status:** complete

### Phase 3: Focused Tests and Smoke

- [x] Run focused unit tests for tile illumination, adaptive routing, deep manifests, and controlnet pipeline handoff
- [x] Run one-pair Adaptive-tile export smoke on reduced-10m data
- [x] Verify route metadata contains tile illumination summary and route distribution
- [x] Run one grouped deep manifest in `deep-learning`
- [x] Import and merge one-pair mixed-route result in `asp360_new`
- [x] Generate one RANSAC-filtered match-line PNG for the smoke pair
- **Status:** complete

### Phase 4: Fixed-Method Baselines

- [x] Run SIFT+FLANN baseline in `asp360_new`
- [x] Export SIFT+LightGlue manifests in `asp360_new`
- [x] Export SuperPoint+LightGlue manifests in `asp360_new`
- [x] Export LoFTR manifests in `asp360_new`
- [x] Run all fixed deep manifests in `deep-learning`
- [x] Import fixed deep results in `asp360_new`
- **Status:** complete

### Phase 5: Adaptive-Tile Full Run

- [x] Run Adaptive-tile route metadata generation and SIFT+FLANN route tiles in `asp360_new`
- [x] Export grouped deep manifests for Adaptive-tile deep route tiles
- [x] Run Adaptive-tile grouped deep manifests in `deep-learning`
- [x] Import and merge Adaptive-tile mixed route results in `asp360_new`
- [x] Confirm every selected pair has final pair-level key outputs or an explicit failure reason
- **Status:** complete

### Phase 6: RANSAC Summaries and Visualizations

- [x] Regenerate RANSAC-filtered match-line visualizations for all five main methods
- [x] Record raw, retained, dropped, and retained fraction counts
- [x] Count successful stereo pairs using RANSAC-retained matches
- [x] Summarize Adaptive-tile route distribution by tile and by pair
- [x] Produce representative point and illumination diagnostic summaries
- **Status:** complete

### Phase 7: Figures and Source Data

- [x] Generate Nature-style source CSV/JSON for the five main methods
- [x] Generate main figure outputs: SVG, PDF, TIFF, PNG
- [x] Generate supplementary Adaptive-pair vs Adaptive-tile ablation source data
- [x] Optionally generate case-study tile comparison figures for rich/small-lighting-gap and weak/large-lighting-gap tiles
- [x] Verify figure labels, units, route legends, and data provenance
- **Status:** complete

### Phase 8: Verification and Handoff

- [x] Run focused tests and smoke import
- [x] Verify output directories and report files exist
- [x] Update `findings.md`, `progress.md`, and this plan with final results
- [x] Confirm `.gitignore` and `print.prt` are not staged or intentionally modified
- [x] Provide final paths and manuscript-ready summary
- **Status:** complete

### Phase 9: Representative Four-Pair Manuscript Rerun

- [x] Select four representative pairs by latitude and texture: near-pole sparse, near-pole rich, near-80S sparse, and near-80S rich
- [x] Run SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, LoFTR, and Adaptive-tile on the four-pair subset
- [x] Run all deep manifests and Adaptive-tile grouped manifests
- [x] Import deep and mixed-route results and extract RANSAC retained counts
- [x] Write representative source CSVs and interpretation summary under `phase7_supplementary/`
- **Status:** complete

## Key Decisions

| Decision | Rationale |
| --- | --- |
| Main adaptive method is `Adaptive-tile` | This is the scientific contribution; pair-level adaptive is weaker for long-strip polar NAC images. |
| Keep `Adaptive-pair` supplementary only | It is useful as an ablation but should not dilute the main five-method claim. |
| Use `valid-pixel-percent-threshold=0.02` | A strict 0.10 threshold can discard shadow tiles where a small textured region remains useful. |
| Keep radiometric and physical validity separate | Shadowed pixels can be useful for physical illumination sampling even if excluded from feature matching. |
| Group deep work by matcher method | Avoids tile-by-tile model switching and repeated deep-learning initialization overhead. |
| Use RANSAC-retained matches for success | Raw deep matches can include unusable correspondences; control-net value depends on geometric consistency. |

## Open Questions

1. Should Adaptive-tile route thresholds be tuned before the full run, or should the current tile-level router be treated as the first reproducible benchmark?
2. Should deep grouped manifests be generated per pair or aggregated across all pairs by matcher method for lower startup overhead?
3. Should the supplementary Adaptive-pair run reuse the previous Phase 18 outputs or be rerun with the same `0.02/256` validity settings?

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| Missing outer-wrapper forwarding for `min-valid-pixels`, valid-intensity percentiles, and DOM source metadata CSV | Phase 2 audit | Added forwarding in `match_original_gsd_lro_dom_pairs_large.py` and `run_image_match_batch_example.sh`; covered by focused pipeline wrapper unit test. |
| One-pair Adaptive-tile export failed with mock `ISISDATA` because real LRO source cubes need the full DEM/camera data tree | Phase 3 smoke attempt 1 | Reran the same smoke with `ISISDATA=$CONDA_PREFIX/data`; export completed successfully. |
| Fixed deep batch import looked for `<deep_match_workspaces>/<original_pair_tag>/tasks.json`, but export workspaces are named with DOM pair ids plus hashes | Phase 4 import attempt 1 | Directly imported each pair using the `manifest_path` cached from export metadata and wrote per-method `deep_match_import_manifests.json` summaries. |
| Phase 7 plotting script reported deep-method runtime as `not_available` | Phase 7 source-data generation | Main source data and figures were generated successfully; runtime provenance needs a follow-up merge from combined deep manifest summaries because fixed deep imports were run from cached manifest paths rather than the plotting script's expected per-method `deep_match_workspaces/*/deep_match_run_summary.json` layout. |
