# Findings: LRO Polar Adaptive Routing Benchmark

## Requirements

- Use `planning-with-files` with a new isolated plan for this experiment.
- Use the dataset under `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd`.
- Preprocess original `*.echo.cal.cub` files with ISIS `reduce` using `sscale=10` and `lscale=10`.
- Generate 10 m/pixel DOMs from the reduced cubes using `lunar_polarstereographic.map`.
- Run experiments on the reduced DOMs.
- Analyze adaptive routing matching performance.
- Compare adaptive routing against fixed methods:
  - SIFT+FLANN
  - SIFT+LightGlue
  - SuperPoint+LightGlue
  - LoFTR
- Use Nature-style figure workflow for final plots, preferably Python/matplotlib as in the previous benchmark.

## Research Findings

- Source directory is readable.
- The source directory contains a `work/` subdirectory with `*.echo.cal.cub` files and supporting list/map files.
- Initial file discovery found 22 `backup_echo_cal_cubes/*.echo.cal.cub` files and 22 corresponding `work/*.echo.cal.cub` files.
- `work/original_images.lis` lists 22 original image cubes by basename.
- `work/doms.lis` lists 22 expected DOM cubes named `dom_<image_id>.cub`.
- `work/` currently contains 22 `dom_*.cub` files, but Phase 2 must verify whether they were generated from the requested `reduce sscale=10 lscale=10` and 10 m/pixel map settings or need regeneration.
- Existing files found under `work/`:
  - `original_images.lis`
  - `doms.lis`
  - `caminfo_all.lis`
  - `lunar_polarstereographic.map`
- `lunar_polarstereographic.map` is a south polar stereographic map for the Moon covering -90 to -60 latitude and 0--360 longitude, but the inspected file does not include explicit `PixelResolution` or `Scale`.
- Existing repo entry points likely relevant to this experiment:
  - `examples/controlnet_construct/run_image_match_batch_example.sh`
  - `examples/controlnet_construct/run_pipeline_example.sh`
  - `examples/controlnet_construct/experiments/run_matcher_comparison.py`
  - `examples/controlnet_construct/experiments/matcher_comparison.py`
  - `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`
- Existing matcher presets likely relevant:
  - `examples/controlnet_construct/presets/classic_sift_flann.json`
  - `examples/controlnet_construct/presets/lightglue_official_sift.json`
  - `examples/controlnet_construct/presets/lightglue_official_superpoint.json`
  - `examples/controlnet_construct/presets/loftr_default.json` or `loftr_external_outdoor.json`
- `selected_pair_original_gsd_paths.csv` exists and contains 16 selected image pairs. The pair names encode latitude band, texture class, and lighting/consistency class, for example:
  - `south-85-to-89.9_sparse-consistent`
  - `south-85-to-89.9_sparse-inconsistent`
  - `south-85-to-89.9_rich-consistent`
  - `south-85-to-89.9_rich-inconsistent`
  - `south-80-to-82_sparse-consistent`
  - `south-80-to-82_sparse-inconsistent`
  - `south-80-to-82_rich-consistent`
  - `south-80-to-82_rich-inconsistent`
- Each selected-pair CSV row includes absolute paths for `echo_cal_cube` and `dom_cube`, and the inspected rows have `all_exist=True`.
- `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py` already defines the exact method set requested:
  - `sift_flann`: Classic SIFT+FLANN via `classic_sift_flann.json`
  - `adaptive`: adaptive routing starting from `matcher_method=flann`, with deep presets for LightGlue and LoFTR
  - `loftr`: LoFTR via `loftr_default.json`
  - `superpoint_lightglue`: SuperPoint+LightGlue via `lightglue_official_superpoint.json`
  - `sift_lightglue`: SIFT+LightGlue via `lightglue_official_sift.json`
- The same script supports `--dry-run`, `--max-pairs`, `--methods`, `--skip-existing`, `--continue-on-error`, tiling parameters, and low-resolution offset estimation.
- The experiment should avoid overwriting original external-media inputs. Reduced cubes and new DOMs should be written to a dedicated experiment output directory.
- Added preprocessing script `examples/controlnet_construct/experiments/prepare_lro_polar_reduced_doms.py`.
- Full dry-run output directory:
  - `work/lro_polar_adaptive_routing_preprocess`
  - Contains 22-line `reduced_original_images.lis`, 22-line `reduced_doms.lis`, 33-line `reduced_selected_pair_paths.csv` including header, 44 ISIS commands in `preprocess_commands.sh`, and `preprocess_manifest.json`.
- Smoke execution output directory:
  - `work/lro_polar_adaptive_routing_preprocess_smoke_exec`
  - `reduce` produced `reduced_cubes/REDUCED_M1106754872LE.echo.cal.cub`.
  - `cam2map` produced `doms_10m/dom_REDUCED_M1106754872LE.cub`.
  - `cam2map` reported `PixelResolution = 10.0 <meters/pixel>` in the output Mapping group.
- Full preprocessing execution completed under `work/lro_polar_adaptive_routing_preprocess`.
- User requested moving generated DOMs and all related experiment files to `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`.
- Migrated experiment directories now live under the external `reduced-10m` workspace:
  - `lro_polar_adaptive_routing_preprocess`
  - `lro_polar_adaptive_routing_preprocess_smoke`
  - `lro_polar_adaptive_routing_preprocess_smoke_exec`
  - `lro_polar_adaptive_routing_match_benchmark`
  - `lro_polar_adaptive_routing_match_benchmark_deep`
  - `lro_polar_adaptive_routing_match_benchmark_lowres`
- Updated 129 text/CSV/JSON/list files in the migrated workspace so absolute paths no longer point to the repo `work/lro_polar_adaptive_routing...` locations.
- The external filesystem does not allow creating symbolic links, so deep-match manifest aliases must be represented by real directories or regenerated manifests rather than symlinks.
- Full preprocessing outputs:
  - 22 `reduced_cubes/REDUCED_*.cub` files.
  - 22 `doms_10m/dom_REDUCED_*.cub` files.
  - `reduced_original_images.lis` with 22 entries.
  - `reduced_doms.lis` with 22 entries.
  - `reduced_selected_pair_paths.csv` with 32 pair-side rows plus header.
  - All 32 selected pair-side rows are marked `all_exist=True` after execution.
- Full available-method benchmark completed under `work/lro_polar_adaptive_routing_match_benchmark`.
- SIFT+FLANN result:
  - 16 expected pairs.
  - 15 successful matched pairs.
  - 1 `matched_no_points` pair.
  - Total matched DOM points: 3945.
  - Mean successful-point count: 263.0.
  - Median successful-point count: 17.0.
- Adaptive result without low-resolution preview routing:
  - 16 expected pairs.
  - 15 successful matched pairs.
  - 1 `matched_no_points` pair.
  - Total matched DOM points: 9328.
  - Mean successful-point count: 621.8666666666667.
  - Median successful-point count: 50.0.
  - Mean inlier ratio among successful pairs: 1.0.
  - Mean coverage among successful pairs: 0.46735449735449736.
  - All 16 adaptive metadata records reported `adaptive_status=skipped_missing_previews` and selected final matcher `flann`; the run therefore tests the adaptive quality-gated cascade path, not a full preview-based route selection.
- Deep baseline environment findings:
  - `lightglue` package is unavailable in `asp360_new`.
  - `torch` is available but CUDA is not available.
  - `kornia` and `kornia.feature` are available.
  - SuperPoint+LightGlue and SIFT+LightGlue fail because `lightglue` is missing.
  - LoFTR smoke failed with `BrokenProcessPool` under the current CPU worker setup.
  - Adaptive routing with low-resolution preview DOMs generated preview DOMs but selected a LightGlue route and failed because `lightglue` is missing.
- User clarified that deep learning matching must be executed in the `deep-learning` conda environment, not directly in `asp360_new`.
- `conda env list` confirmed `/home/gengxun/miniconda3/envs/deep-learning` exists.
- Existing repo support for the conda handoff:
  - `examples/controlnet_construct/run_image_match_batch_example.sh` supports `--deep-match-mode export` and `--deep-match-mode import`.
  - `examples/learning_methods/run_deep_match_manifest.py` executes exported `tasks.json` manifests in the deep-learning environment.
  - `examples/controlnet_construct/run_deep_match_pipeline.sh` documents the intended three-stage pattern: `asp360_new` export, `deep-learning` execution, `asp360_new` import.
- Reports generated:
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/pair_summary.csv`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/pair_summary.json`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/method_summary.csv`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/method_summary.json`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/category_summary.csv`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/category_summary.json`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/environment_report.json`
  - `work/lro_polar_adaptive_routing_match_benchmark/reports/report_manifest.json`
- Figures generated in SVG, PDF, PNG, and 600 dpi TIFF:
  - `method_success`
  - `match_yield_distribution`
  - `adaptive_routing_outcomes`
- Correct runtime environment for real LRO preprocessing:
  - `source "$HOME/miniconda3/etc/profile.d/conda.sh"`
  - `conda activate asp360_new`
  - use the conda-provided `ISISDATA=/home/gengxun/miniconda3/envs/asp360_new/data`
  - do not override `ISISDATA` with the repo mockup for real LRO data.

## Technical Decisions

| Decision | Rationale |
|---|---|
| Start from `work/*.echo.cal.cub` unless discovery shows they are stale or incomplete | The user specifically named `original_gsd`; its `work/` directory already contains list files and the polar stereographic map. |
| Keep `backup_echo_cal_cubes/` as fallback source | It mirrors the 22 `*.echo.cal.cub` files and can recover source data if `work/` files were modified. |
| Use JSON/CSV reports as the only figure input | Keeps Nature-style figures reproducible and avoids manually extracting values from logs. |
| Separate preprocessing, matching, aggregation, and plotting phases | Each stage can be resumed without rerunning expensive completed work. |
| Explicitly verify or set 10 m/pixel DOM resolution | The provided map lacks an inspected `PixelResolution`, so `cam2map` must not silently inherit an unintended resolution. |
| Reuse `match_original_gsd_lro_dom_pairs_large.py` where possible | It already implements the requested method comparison and selected-pair orchestration, reducing risk versus a new runner. |
| Output all preprocessing artifacts under repo `work/` initially | Avoided writing into the external source tree during development and smoke testing. |
| Move final reduced-10m artifacts to external media | User requested the generated DOMs and all related experiment files in `original_gsd/work/reduced-10m` before continuing deep-learning matching. |

## Issues Encountered

| Issue | Resolution |
|---|---|
| `cam2map` failed with mock `ISISDATA` because the referenced LRO DEM shape model was missing/invalid in the mock tree | Re-ran without overriding the conda environment's real `ISISDATA`; `cam2map` succeeded and produced a 10 m/pixel DOM. |
| ISIS smoke execution updated generated `print.prt` | Leave it unstaged and out of any commit/publish scope; do not delete or restore without explicit user request. |
| LightGlue is missing in the selected conda environment | Record the failure and do not treat LightGlue baseline rows as algorithmic zero-match results. |
| LoFTR failed with a worker-process crash in smoke | Record as runtime failure under the current CPU worker environment; avoid repeating expensive full LoFTR runs until the environment is fixed. |
| External workspace rejected symlink creation during `mv` of the deep benchmark alias directory | Copied the deep benchmark without symlink aliases and will use real directories or regenerated manifests for import. |

## Deep-Learning Supplement Plan

- Use `asp360_new` only for CUBE/ISIS preparation and importing final key files.
- Use `deep-learning` for `examples/learning_methods/run_deep_match_manifest.py`.
- First extend the selected-pair runner to expose deep-match handoff arguments already supported by the lower-level batch wrapper.
- Then run smoke on one selected pair before any full 16-pair rerun.
- Migrated one-pair deep-learning handoff results:
  - SuperPoint+LightGlue: 15/15 tile tasks succeeded in `deep-learning` on CPU; import status `imported`; first selected pair produced 846 points.
  - SIFT+LightGlue: 15/15 tile tasks succeeded in `deep-learning` on CPU; import status `imported`; first selected pair produced 6533 points.
  - LoFTR: 15/15 tile tasks completed in `deep-learning` on CPU, but all raw matches were removed by invalid-mask filtering; import status `imported_no_points`; first selected pair produced 0 valid points.
- Current regenerated method summary after one-pair deep supplement:
  - SIFT+FLANN: 15/16 successful pairs, 3945 total points.
  - Adaptive: 15/16 successful pairs, 9328 total points.
  - SuperPoint+LightGlue: 1/16 imported pairs so far, 846 total points.
  - SIFT+LightGlue: 1/16 imported pairs so far, 6533 total points.
  - LoFTR: 0/16 successful pairs by nonzero-point criterion so far; first pair was attempted/imported with 0 valid points.
- LoFTR invalid-mask root cause and fix:
  - Exported deep-match task masks are OpenCV-style valid masks with `0=invalid` and `255=valid`.
  - The manifest runner's post-filter already interprets uint8 masks correctly, but the LoFTR frontend path expects bool invalid masks and inverts them to create model valid masks.
  - Passing the uint8 valid masks directly into LoFTR inverted the valid area, so raw LoFTR matches were generated mostly/entirely in invalid pixels and then removed by the post-filter.
  - Single-tile evidence on the first LoFTR pair:
    - Original uint8 masks before fix: 45 raw matches, 45 removed by exported invalid-mask filtering.
    - No LoFTR masks: 936 raw matches, 862 retained by post-filtering.
    - Corrected bool invalid masks: 832 raw matches, 829 retained by post-filtering.
    - After adapter fix with original uint8 masks: 832 raw matches, 829 retained by post-filtering.
  - Fix location: `examples/image_match/deep_adapter.py`, LoFTR branch normalizes `left_mask/right_mask` through `_as_invalid_mask()` before `LoFTRFrontend.prepare()`.
  - Regression coverage: `tests/unitTest/image_match_deep_adapter_unit_test.py` now covers uint8 valid-mask conversion for LoFTR.
  - Deep-learning manifest defaults are now `num_workers=1` and `torch_num_threads=8`.
  - Corrected first-pair LoFTR smoke with the new runtime settings succeeded: 15/15 tile tasks completed on CPU with `torch_num_threads=8`, retaining 7294 matches after invalid-mask filtering.
  - Corrected first-pair LoFTR import succeeded in `asp360_new` with status `imported` and `point_count=7294`.
  - External filesystem symlink limitation also affects import alias paths; import expected `REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal/tasks.json`, so a real alias directory containing `tasks.json` was created for the first pair.
  - Updated report status after corrected first-pair import:
    - LoFTR: 1/16 successful pairs, 7294 total points; remaining LoFTR pairs are still exported/not rerun.
    - SuperPoint+LightGlue: 1/16 successful pairs, 846 total points.
    - SIFT+LightGlue: 1/16 successful pairs, 6533 total points.
- Shadow/extreme-gray masking follow-up:
  - The existing `lower_percent=0.5` and `upper_percent=99.5` parameters only control grayscale stretch for matcher input; they did not mark low/high intensity pixels as invalid.
  - Added explicit default-off valid-intensity masking controls:
    - `--valid-intensity-lower-percent`
    - `--valid-intensity-upper-percent`
  - The 1%/99% test masks pixels outside the central 98% intensity range after the existing invalid-pixel mask is applied.
  - First-pair LoFTR comparison:
    - Corrected baseline LoFTR: 7305 raw matches, 7294 retained/imported matches, 11 invalid-mask removals.
    - 1%/99% intensity-masked LoFTR: 6540 raw matches, 6475 retained/imported matches, 65 invalid-mask removals.
    - The intensity mask reduced retained/imported LoFTR matches by 819 points, retaining 88.77% of the corrected baseline count.
  - Match-line visualization for the 1%/99% run:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_intensity_1_99/loftr/match_viz/REDUCED_M110860982RE__REDUCED_M110881352RE_loftr_intensity_1_99_reduced_cropped.png`
  - Default policy update:
    - The default valid-intensity percentile mask is now conservative `0.1/99.9`.
    - The stricter `1.0/99.0` setting remains available through CLI/config for shadow/highlight ablation experiments.
    - CLI can disable the default mask with `--disable-valid-intensity-percentile-mask`.
- Separate rerun in `deep-learning` after the default `0.1/99.9` mask update:
  - Output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_rerun_20260602`.
  - Scope: first selected DOM pair only, using the migrated reduced-10m selected-pair CSV.
  - Execution split: `asp360_new` exported/imported manifests and key files; `deep-learning` executed LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue manifests.
  - Runtime settings: CPU, `num_workers=1`, `torch_num_threads=8`, `force_rerun=True`.
  - LoFTR: 15/15 tile tasks completed, 7246 raw matches, 7228 retained/imported matches, 18 invalid-mask removals, import status `imported`.
  - SuperPoint+LightGlue: 15/15 tile tasks completed, 728 retained/imported matches, import status `imported`.
  - SIFT+LightGlue: 15/15 tile tasks completed, 6347 retained/imported matches, one empty tile skipped during import, import status `imported`.
  - All method summary JSON/CSV files and root method summary JSON/CSV files were regenerated in the rerun root.
- Full selected-pair rerun after first-pair smoke acceptance:
  - Output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602`.
  - Scope: 16 selected DOM pairs; each method exported 16 metadata entries, 15 pairs with deep-learning tasks, and 1 zero-task pair.
  - Execution split: manifest export/import in `asp360_new`, deep inference in `deep-learning`.
  - Runtime settings: CPU, `num_workers=1`, `torch_num_threads=8`, `force_rerun=True`.
  - LoFTR: 14 imported pairs, 1 imported-no-points zero-task pair, 1 `import_failed_no_usable_results` pair after a deep-learning SIGKILL on a single long tile; total imported/visualized points from successful rows: 30595.
  - SuperPoint+LightGlue: 14 imported pairs, 2 imported-no-points pairs, no failed metadata; total imported/visualized points: 3109.
  - SIFT+LightGlue: 11 imported pairs, 5 imported-no-points pairs, no failed metadata; total imported/visualized points: 13541.
  - Match-line visualization PNGs were generated for all 16 selected pairs for each method:
    - LoFTR: `loftr/match_viz/*.png` = 16
    - SuperPoint+LightGlue: `superpoint_lightglue/match_viz/*.png` = 16
    - SIFT+LightGlue: `sift_lightglue/match_viz/*.png` = 16
  - Summary outputs exist:
    - Root: `large_dom_match_methods_summary.json`, `large_dom_match_methods_summary.csv`
    - Per method: `<method>_large_dom_match_summary.json`, `<method>_large_dom_match_summary.csv`
  - Note: per-method CSV `point_count` cells are currently blank after import, but the same rows contain `match_visualization.point_count`, and each metadata JSON contains `image_match.point_count`. Use those fields for quantitative summaries until the CSV writer is corrected.
- LoFTR pair 15 retry after the original full-run SIGKILL:
  - The original one-task retry failed again without writing a result or retry summary.
  - Re-exporting the same pair with `max_image_dimension=1024` and `sub_block_size_x/y=1024` split the `2623 x 652` shared extent into 3 LoFTR tasks.
  - The smaller-tile retry completed in `deep-learning`: 3/3 tasks succeeded, 395 raw matches, 383 retained/imported matches, 12 invalid-mask removals.
  - Import in `asp360_new` succeeded with `status=imported`, `point_count=383`, and `imported_task_count=3`.
  - Retry output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602`.
  - Match-line PNG: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602/loftr/match_viz/dom_REDUCED_M1200848465RE__dom_REDUCED_M173567595LE__20260602T081305.png`.
  - Interpretation: the previous failure was caused by LoFTR CPU memory/attention pressure on an overly long tile; using the new 1024 tiling default resolves this pair.
- RANSAC-filtered match-line visualization follow-up:
  - Added script: `examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py`.
  - The script regenerates match-line PNGs from existing imported deep-match `.key` files and applies homography RANSAC before drawing. It does not rerun deep inference and does not overwrite original `match_viz/` outputs.
  - Full selected-pair root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602`.
  - RANSAC-filtered PNGs are under each method's `match_viz_ransac/` directory.
  - Full-run summary files:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.json`
  - Full-run before/after counts:
    - LoFTR: 30,595 raw matches -> 11,145 RANSAC-retained matches; retained fraction 36.43%.
    - SuperPoint+LightGlue: 3,109 raw matches -> 765 RANSAC-retained matches; retained fraction 24.61%.
    - SIFT+LightGlue: 13,541 raw matches -> 12,478 RANSAC-retained matches; retained fraction 92.15%.
    - Combined: 47,245 raw matches -> 24,388 retained; retained fraction 51.62%.
  - Interpretation:
    - SIFT+LightGlue has the highest geometric consistency on this selected-pair set after import.
    - LoFTR and SuperPoint+LightGlue produce many raw correspondences in difficult lighting/texture cases, but a large fraction are inconsistent with a single homography. Their raw match counts should not be interpreted as control-network quality without geometric filtering.
- Five-method RANSAC visualization and Nature-style figure input follow-up:
  - Full selected-pair root:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602`
  - SIFT+FLANN and adaptive routing were rerun for all 16 selected pairs using 1024 x 1024 tiles, one OpenCV thread, and four Python process workers.
  - The adaptive run completed, but all 16 adaptive metadata records still report `adaptive_routing.status=skipped_missing_previews` and select final matcher `flann`; this is therefore a quality-gated adaptive wrapper/fallback baseline, not a full low-resolution-preview route-selection result.
  - RANSAC-filtered PNG counts:
    - LoFTR: 16
    - SuperPoint+LightGlue: 16
    - SIFT+LightGlue: 16
    - SIFT+FLANN: 16
    - Adaptive: 16
  - Five-method before/after RANSAC counts:
    - LoFTR: 30,595 raw -> 11,145 retained; retained fraction 36.43%; 14/16 pairs retained at least one match.
    - SuperPoint+LightGlue: 3,109 raw -> 765 retained; retained fraction 24.61%; 14/16 pairs retained at least one match.
    - SIFT+LightGlue: 13,541 raw -> 12,478 retained; retained fraction 92.15%; 11/16 pairs retained at least one match.
    - SIFT+FLANN: 3,606 raw -> 2,754 retained; retained fraction 76.37%; 16/16 pairs retained at least one match.
    - Adaptive: 9,011 raw -> 7,077 retained; retained fraction 78.54%; 16/16 pairs retained at least one match.
    - Combined: 59,862 raw -> 34,219 retained; retained fraction 57.16%.
  - Runtime fields in the Nature-style source data intentionally use method-specific provenance:
    - Deep methods: summed per-task `started_at_utc`/`finished_at_utc` as deep inference core seconds.
    - SIFT+FLANN/adaptive: `command.json` to method-summary mtime as a wall-time proxy because the classic matcher runner does not yet emit per-tile core timings.
  - Runtime summary:
    - LoFTR: 2,011.998 s (33.53 min), source `deep_task_started_finished_sum`.
    - SuperPoint+LightGlue: 556.809 s (9.28 min), source `deep_task_started_finished_sum`.
    - SIFT+LightGlue: 541.780 s (9.03 min), source `deep_task_started_finished_sum`.
    - SIFT+FLANN: 93.710 s (1.56 min), source `command_to_method_summary_mtime_proxy`.
    - Adaptive: 103.370 s (1.72 min), source `command_to_method_summary_mtime_proxy`.
  - Nature-style source data and figure outputs:
    - `nature_figure_inputs/five_method_pair_summary.csv`
    - `nature_figure_inputs/five_method_method_summary.csv`
    - `nature_figure_inputs/five_method_match_comparison_source_data.json`
    - `nature_figure_inputs/five_method_match_comparison.svg`
    - `nature_figure_inputs/five_method_match_comparison.pdf`
    - `nature_figure_inputs/five_method_match_comparison.tiff`
    - `nature_figure_inputs/five_method_match_comparison.png`
  - LoFTR pair-15 retry RANSAC visualization:
    - Raw 383 -> retained 9; retained fraction 2.35%.
    - PNG: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602/loftr/match_viz_ransac/dom_REDUCED_M1200848465RE__dom_REDUCED_M173567595LE__20260602T081305__ransac.png`.
- True deep-learning adaptive routing rerun:
  - Output root:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602`
  - Low-resolution DOMs:
    - 22 precomputed low-resolution DOMs were reused under `adaptive/low_resolution_doms/level3`.
    - The routing metadata includes low-resolution preview source paths and, where available, solar elevation/azimuth differences derived from the corresponding reduced original image metadata.
  - Adaptive export behavior:
    - `deep_match_mode=export` previously failed when adaptive routing selected FLANN because export mode only supports deep matchers.
    - The implemented fix keeps the routed traditional matcher as the initial decision, then exports the first deep fallback from the adaptive cascade for execution in the `deep-learning` conda environment.
    - This preserves routing evidence while satisfying the user's environment split: ISIS/metadata/import in `asp360_new`, deep inference in `deep-learning`.
  - Full execution:
    - 16/16 selected pairs exported.
    - 95 LightGlue/SuperPoint tile tasks exported.
    - 16/16 manifests completed in `deep-learning`.
    - 95/95 tasks succeeded, 0 task failures.
    - Runtime settings: CPU, `num_workers=1`, `torch_num_threads=8`.
    - Deep task runtime for true adaptive: 605.001 s; wrapper elapsed time: 642.578 s.
  - RANSAC-filtered success metric:
    - Pair success is counted only when `ransac_retained_count > 0`.
    - True adaptive raw/imported matches: 3,573.
    - True adaptive RANSAC-retained matches: 830.
    - True adaptive retained fraction: 23.23%.
    - True adaptive pair success after RANSAC: 15/16.
  - Updated five-method comparison with true adaptive:
    - LoFTR: 30,595 raw -> 11,145 retained; 14/16 successful after RANSAC; runtime 2,011.998 s.
    - SuperPoint+LightGlue: 3,109 raw -> 765 retained; 14/16 successful after RANSAC; runtime 556.809 s.
    - SIFT+LightGlue: 13,541 raw -> 12,478 retained; 11/16 successful after RANSAC; runtime 541.780 s.
    - SIFT+FLANN: 3,606 raw -> 2,754 retained; 16/16 successful after RANSAC; runtime 93.710 s mtime proxy.
    - True adaptive deep-learning: 3,573 raw -> 830 retained; 15/16 successful after RANSAC; runtime 605.001 s.
  - Interpretation:
    - The true adaptive rerun now genuinely exercises the deep-learning handoff, but in this selected-pair set it mostly routes to SuperPoint+LightGlue and therefore behaves closer to the SuperPoint+LightGlue baseline than to the previous FLANN-fallback adaptive result.
    - The previous adaptive row in Phase 13 should be described as a fast FLANN-backed adaptive fallback baseline, not the final deep-learning adaptive result.
    - For manuscript claims, use the true-adaptive `nature_figure_inputs_true_adaptive/` outputs when discussing deep-learning routing, and use pair success after RANSAC rather than raw match count.
  - Updated Nature-style source data and figure outputs:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_pair_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_method_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_source_data.json`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.svg`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.pdf`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.tiff`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.png`

## Resources

- Active plan: `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/`
- Source data: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd`
- Source cubes: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/*.echo.cal.cub`
- Backup cubes: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/backup_echo_cal_cubes/*.echo.cal.cub`
- Projection map: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/lunar_polarstereographic.map`
- Preprocessing script: `examples/controlnet_construct/experiments/prepare_lro_polar_reduced_doms.py`
- Full dry-run manifest: `work/lro_polar_adaptive_routing_preprocess/preprocess_manifest.json`
- Full dry-run commands: `work/lro_polar_adaptive_routing_preprocess/preprocess_commands.sh`
- Full executed reduced-pair manifest after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`
- Smoke output manifest: `work/lro_polar_adaptive_routing_preprocess_smoke_exec/preprocess_manifest.json`
- Benchmark reports after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/reports`
- Figure outputs after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/reports/figures`

## Visual/Browser Findings

- No image/PDF/browser visual inspection has been performed yet.

## Phase 15 Prior-Only Adaptive Routing Findings

- The previous Phase 14 adaptive export behavior is now superseded for the main experiment claim. It preserved a FLANN/BF prior route in metadata but exported the first deep fallback for execution in `deep-learning`; the user clarified that this is not the intended adaptive-routing definition.
- The revised adaptive rule is prior-only:
  - Rich texture and small lighting difference -> SIFT+FLANN.
  - Moderate texture or moderate lighting difference -> SIFT+LightGlue as the main deep-learning matcher.
  - Weak-to-moderate texture with non-extreme lighting -> SuperPoint+LightGlue.
  - Weak texture plus large lighting difference, or extreme single-condition cases -> LoFTR.
- Post-match quality evaluation remains useful for reporting success/failure, but it no longer triggers a recursive matcher change. A failed selected matcher records `quality_insufficient_no_fallback`.
- `deep_match_mode=export` now rejects an adaptive route that selects a traditional matcher, instead of silently exporting LightGlue/LoFTR fallback tasks. Real mixed adaptive experiments should either:
  - run prior-selected FLANN/BF routes directly in `asp360_new`, or
  - export only pairs whose prior route selected a deep matcher.
- The adaptive experiment runner now maps the main `lightglue` route to `lightglue_official_sift.json` and reserves `superpoint_lightglue` for the SuperPoint+LightGlue branch.

## Phase 15 Final Prior-Only Adaptive Rerun

- Phase 14 true-adaptive outputs are now treated as old fallback-export strategy results, not the final prior-only adaptive conclusion.
- Real 16 selected-pair prior-only route partition:
  - SIFT+FLANN: 3 pairs
  - SIFT+LightGlue: 13 pairs
  - SuperPoint+LightGlue: 0 pairs
  - LoFTR: 0 pairs
- Deep-learning execution:
  - Ran in `deep-learning` conda environment with `--num-workers 1` and `--torch-num-threads 8`.
  - CUDA was unavailable, so SIFT+LightGlue ran on CPU.
  - 13/13 manifests completed with 0 process-level failures.
- Import detail:
  - Exported workspaces used DOM/hash names, while import looked for `REDUCED_*.echo.cal` pair-tag directories.
  - Pair-tag alias `tasks.json` directories were created without rerunning deep inference.
- Final adaptive outputs:
  - 16 `_A.key`/`_B.key` pairs.
  - Matcher split: 13 SIFT+LightGlue, 3 SIFT+FLANN.
  - Status split: 8 imported, 5 imported_no_points, 3 matched.
  - Clean summary:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/adaptive/adaptive_prior_only_clean_pair_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/adaptive/adaptive_prior_only_clean_pair_summary.json`
- Final adaptive RANSAC summary:
  - pair_count: 16
  - raw_match_count: 13,930
  - ransac_retained_count: 12,767
  - ransac_dropped_count: 1,163
  - retained fraction: 0.9165
- Final five-method comparison uses Phase 14 fixed-method baselines plus Phase 15 prior-only adaptive only.
  - LoFTR: 11,145 retained, 33.53 min.
  - SuperPoint+LightGlue: 765 retained, 9.28 min.
  - SIFT+LightGlue: 12,478 retained, 9.03 min.
  - SIFT+FLANN: 2,754 retained, 1.56 min.
  - Adaptive prior-only: 12,767 retained, 6.84 min.
- Adaptive runtime provenance is hybrid:
  - deep task started/finished sum: 371.67 s
  - classic command-to-summary mtime proxy: 38.51 s
  - total: 410.18 s
- Final source data and figure outputs:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_pair_summary.csv`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_method_summary.csv`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison_source_data.json`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.svg`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.pdf`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.tiff`

## Phase 16 Valid-Block Texture Evidence Cleanup

- Adaptive routing texture diagnostics now prefer the actual matched image paths:
  - DOM-space matching uses the matched DOM paths.
  - ORI-space matching uses the original/REDUCED cube paths.
  - Low-resolution DOM previews remain available only as fallback diagnostics when actual source paths are unavailable.
- The route summary `preview_sources` payload now reports the selected texture diagnostic source and whether it was a fallback:
  - `source_type="matched_dom"` for actual DOM texture evidence.
  - `source_type="raw_original_cube"` for ORI-space texture evidence.
  - `source_type="low_resolution_dom"` only when falling back to previews.
  - `fallback_used` records whether the source was fallback rather than the actual matched image.
- Tile-level texture sparseness already excluded invalid blocks via `min_valid_pixel_ratio`; this behavior is now preserved by selecting the actual matched image instead of bypassing through preview-source selection.
- Missing pair texture evidence now remains missing in route diagnostics:
  - `PairRoutingDecision.mean_real_texture_score` is `None` when `pair_texture_sparseness` is unavailable.
  - This removes the misleading legacy neutral `0.5` value when no valid texture tiles could be computed.
- A stale controlnet matching regression still expected old adaptive cascade fallback. It was updated to current Phase 15 prior-only semantics:
  - one prior-selected matcher is run;
  - no LoFTR fallback is requested after a failed quality gate;
  - the stop reason is `quality_insufficient_no_fallback`.
- Verification:
  - `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_texture_sparseness_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v` passed: 262 tests, 1 skipped.
  - `python tests/smoke_import.py` passed.
  - `git diff --check` passed for touched files.
- Follow-up texture aggregation detail:
  - `ImageSparsenessSummary` now includes effective aggregation counts that exclude invalid texture blocks from the pixel denominator:
    - `skipped_invalid_tile_count`
    - `aggregation_tile_count`
    - `aggregation_pixel_count`
    - `aggregation_valid_pixel_count`
    - `aggregation_valid_pixel_ratio`
  - `tile_total_count` remains the scanned-window count for diagnostics, while aggregation fields are the clean evidence denominator for texture analysis.
  - Focused verification passed: `python -m unittest tests.unitTest.image_match_texture_sparseness_unit_test tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_tile_diagnostics_unit_test -v`.

## Phase 17 Feature-Count Routing and Reporting Cleanup

- Adaptive routing now has an explicit hard route for very low texture-probe keypoint evidence:
  - if either side has fewer than `min_texture_probe_keypoints=12`, route directly to LoFTR;
  - if either side has keypoint density lower than `min_texture_probe_keypoint_density=1.0e-5`, route directly to LoFTR.
- This hard rule is evaluated before texture-sparseness/lighting bins, so a pair that otherwise looks rich by aggregate texture can still go LoFTR when actual keypoint evidence is too sparse.
- The previous SIFT+FLANN vs SIFT+LightGlue feature-count mismatch was caused by different feature budgets:
  - `classic_sift_flann.json`: OpenCV SIFT `max_features=1000`;
  - `lightglue_official_sift.json`: official SIFT frontend was `max_features=4096`.
- `lightglue_official_sift.json` is now aligned to `max_features=1000`, so SIFT+FLANN and SIFT+LightGlue use the same intended SIFT feature budget for this experiment.
- Even with the same feature budget, matched-count outputs should not be expected to match:
  - extracted SIFT features are the detector output;
  - FLANN ratio-test correspondences and LightGlue learned correspondences are different matcher outputs;
  - RANSAC-retained counts are the final geometric-success evidence.
- Match summaries now report extracted features separately:
  - `left_feature_count_total`
  - `right_feature_count_total`
  - `feature_count_total`
  - `tile_match_count_total`
- Five-method source-data generation now propagates those fields into:
  - pair-level CSV/JSON rows;
  - method-level totals and median extracted feature counts.
- Verification:
  - `python -m py_compile examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py examples/image_match/image_match.py examples/image_match/adaptive_routing.py` passed.
  - `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v` passed: 249 tests, 1 skipped.
  - `python tests/smoke_import.py` passed.
  - `git diff --check` passed for touched files.

## Phase 18 Latest-Parameter Five-Method Final Rerun

- Output root:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602`
- Deep-learning execution policy:
  - conda env: `deep-learning`
  - device: CPU
  - `num_workers=1`
  - `torch_num_threads=8`
- Fixed deep-method completion:
  - LoFTR: 16/16 manifests, 96/96 tile tasks succeeded, 0 failed.
  - SuperPoint+LightGlue: 16/16 manifests, 96/96 tile tasks succeeded, 0 failed.
  - SIFT+LightGlue: 16/16 manifests, 96/96 tile tasks succeeded, 0 failed.
- Adaptive prior-only route distribution with the latest texture/keypoint rules:
  - SIFT+FLANN/direct: 14 pairs.
  - SIFT+LightGlue/deep import: 2 pairs.
  - SuperPoint+LightGlue: 0 pairs.
  - LoFTR: 0 pairs.
- Final RANSAC-filtered counts:
  - LoFTR: raw 31,565; retained 11,172; retained fraction 0.3539; runtime 30.70 min.
  - SuperPoint+LightGlue: raw 3,439; retained 770; retained fraction 0.2239; runtime 8.37 min.
  - SIFT+LightGlue: raw 5,348; retained 3,906; retained fraction 0.7304; runtime 1.58 min.
  - SIFT+FLANN: raw 3,611; retained 2,757; retained fraction 0.7635; runtime 1.48 min.
  - Adaptive: raw 5,511; retained 4,220; retained fraction 0.7657; runtime 4.99 min.
- Feature-count reporting:
  - SIFT+FLANN now records extracted SIFT features for all 16 pairs; total extracted features: 168,395; median per pair: 6,295.
  - Adaptive records extracted SIFT features for 14 direct SIFT+FLANN branches; total extracted features: 347,797; median per recorded pair: 14,461. The 2 deep-import branches do not currently record detector feature totals in imported manifest metadata.
- Final figure/source outputs:
  - `nature_figure_inputs_latest_params/five_method_pair_summary.csv`
  - `nature_figure_inputs_latest_params/five_method_method_summary.csv`
  - `nature_figure_inputs_latest_params/five_method_match_comparison_source_data.json`
  - `nature_figure_inputs_latest_params/five_method_match_comparison.svg`
  - `nature_figure_inputs_latest_params/five_method_match_comparison.pdf`
  - `nature_figure_inputs_latest_params/five_method_match_comparison.tiff`
  - `nature_figure_inputs_latest_params/five_method_match_comparison.png`
- Implementation findings:
  - Adaptive route probing must not load full 10k-scale DOM bands. A bounded preview reader now keeps actual matched-image evidence while avoiding OOM/SIGKILL.
  - RANSAC rerendering cannot assume an old `match_visualization` block exists because low-memory reruns can disable initial visualization. It now falls back to direct pair metadata or deep-import manifest DOM paths.
  - Batch and plotting summaries must read nested `image_match` fields. Direct metadata sidecars now persist feature-count totals so source data can distinguish extracted features from matched correspondences.
