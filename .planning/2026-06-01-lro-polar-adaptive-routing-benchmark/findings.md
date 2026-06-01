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
