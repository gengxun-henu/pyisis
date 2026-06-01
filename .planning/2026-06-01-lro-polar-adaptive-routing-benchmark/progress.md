# Progress Log: LRO Polar Adaptive Routing Benchmark

## Session: 2026-06-01

### Phase 1: Dataset and Pipeline Discovery

- **Status:** complete
- **Started:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Created isolated plan with `planning-with-files`.
  - Confirmed the requested source data directory is readable.
  - Found initial data layout under `original_gsd`, including `work/`, `backup_echo_cal_cubes/`, `selected_original_products.txt`, `original_images.lis`, `doms.lis`, `caminfo_all.lis`, and `lunar_polarstereographic.map`.
  - Replaced template planning files with task-specific `task_plan.md`, `findings.md`, and `progress.md`.
  - Counted 22 source `work/*.echo.cal.cub` files and 22 existing `work/dom_*.cub` files.
  - Inspected `original_images.lis`, `doms.lis`, and `lunar_polarstereographic.map`.
  - Found `selected_pair_original_gsd_paths.csv` with 16 curated image pairs spanning sparse/rich and consistent/inconsistent categories.
  - Located an existing large-DOM matcher comparison runner that already supports the requested methods.
- Files created/modified:
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/task_plan.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/findings.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/progress.md`

## Test Results

| Test | Input | Expected | Actual | Status |
|---|---|---|---|---|
| Source directory discovery | `find .../original_gsd` | Locate cubes/list/map files | Found 22 backup cubes, 22 work cubes, and required list/map files | pass |
| Pair manifest discovery | `selected_pair_original_gsd_paths.csv` | Locate selected pairs for method comparison | Found 16 curated pairs with absolute echo-cal and DOM paths | pass |
| Existing runner discovery | repo search for matcher comparison | Locate reusable adaptive/fixed-method runner | Found `match_original_gsd_lro_dom_pairs_large.py` with requested method set | pass |
| Preprocess dry-run smoke | `prepare_lro_polar_reduced_doms.py --max-cubes 2 --allow-partial-pairs` | Generate reduce/cam2map commands and reduced list files without executing ISIS | Generated commands, two reduced original entries, two DOM entries, and one complete pair manifest | pass |
| Preprocess execution smoke | `prepare_lro_polar_reduced_doms.py --max-cubes 1 --allow-partial-pairs --execute --skip-existing` | Run reduce/cam2map on one real LRO cube and create a 10 m DOM | `reduce` and `cam2map` succeeded after using real conda `ISISDATA`; output Mapping reported `PixelResolution = 10.0 <meters/pixel>` | pass |
| Full preprocessing dry-run | `prepare_lro_polar_reduced_doms.py --output-root work/lro_polar_adaptive_routing_preprocess` | Generate full 22-cube command/list/manifest artifacts without executing ISIS | Created 22 original entries, 22 DOM entries, 32 selected-pair rows plus header, and 44 ISIS commands | pass |
| Full preprocessing execution | `prepare_lro_polar_reduced_doms.py --output-root work/lro_polar_adaptive_routing_preprocess --execute --skip-existing` | Create all reduced cubes and 10 m DOMs for selected-pair benchmark | Created 22 REDUCED cubes, 22 10 m DOMs, and 32 selected pair-side records all marked `all_exist=True` | pass |
| Matcher dry-run | `match_original_gsd_lro_dom_pairs_large.py --methods all --max-pairs 1 --dry-run` | Confirm all five method commands and directories | Generated commands for SIFT+FLANN, adaptive, LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue | pass |
| All-method smoke | `match_original_gsd_lro_dom_pairs_large.py --methods all --max-pairs 1 --continue-on-error` | Validate one pair across all methods | SIFT+FLANN and no-preview adaptive completed; LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue failed due current deep-matcher environment | partial |
| Adaptive low-resolution preview smoke | `match_original_gsd_lro_dom_pairs_large.py --methods adaptive --max-pairs 1 --enable-low-resolution-offset-estimation` | Verify adaptive route prepass can use low-resolution preview DOMs | Preview DOM generation succeeded, but route selected LightGlue and failed because `lightglue` is unavailable | partial |
| Full available-method matching | `match_original_gsd_lro_dom_pairs_large.py --methods sift_flann,adaptive --skip-existing` | Complete all resumable CPU-available benchmark runs | SIFT+FLANN and adaptive each produced 16 metadata files and return code 0 | pass |
| Report aggregation | `summarize_lro_polar_adaptive_routing_benchmark.py --make-figures` | Produce CSV/JSON summaries and Python/matplotlib figures | Generated pair/method/category summaries, environment report, manifest, and SVG/PDF/PNG/TIFF figures | pass |
| Python syntax check | `python -m py_compile ...prepare_lro_polar_reduced_doms.py` | Script compiles | No output | pass |
| Python syntax check | `python -m py_compile ...summarize_lro_polar_adaptive_routing_benchmark.py` | Script compiles | No output | pass |
| Smoke import | `python tests/smoke_import.py` in `asp360_new` with mock `ISISDATA` | PyISIS import smoke passes | `smoke import ok` | pass |
| Figure file validation | `file reports/figures/*` | SVG/PDF/PNG/TIFF outputs exist and TIFF is 600 dpi export size | Three figure themes exported in all requested formats | pass |
| Whitespace check | `git diff --check` on touched files | No whitespace errors | No output | pass |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|---|---|---:|---|
| 2026-06-01 Asia/Shanghai | `cam2map` failed when `ISISDATA` was overridden to repo mockup; LRO DEM shape model could not be opened | 1 | Re-ran with conda environment's real `ISISDATA=/home/gengxun/miniconda3/envs/asp360_new/data`; smoke succeeded |
| 2026-06-01 Asia/Shanghai | ISIS smoke execution updated generated `print.prt` | 1 | Left `print.prt` unstaged and otherwise untouched; must be excluded from any commit/publish scope |

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Phase 3: Matcher Benchmark Design |
| Where am I going? | Preprocessing design, matcher benchmark design, implementation, execution, figures, verification |
| What's the goal? | Compare adaptive routing against fixed SIFT/LightGlue/LoFTR methods on reduced LRO polar DOM data and generate Nature-style figures |
| What have I learned? | Source directory is readable, contains 22 work cubes/DOMs, 16 curated pairs, and an existing method-comparison runner |
| What have I done? | Completed Phase 1 and Phase 2, added the preprocessing script, generated full dry-run artifacts, and verified a one-cube reduce/cam2map smoke |

### Phase 2: Preprocessing Design

- **Status:** complete
- **Started:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Added `examples/controlnet_construct/experiments/prepare_lro_polar_reduced_doms.py`.
  - Script reads `original_gsd/work/original_images.lis`, resolves `*.echo.cal.cub`, writes reduced cubes and DOMs under an independent repo `work/` output directory.
  - Script generates ISIS `reduce from=<source> to=<REDUCED> sscale=10 lscale=10`.
  - Script generates ISIS `cam2map from=<REDUCED> map=<lunar_polarstereographic.map> to=<dom> interp=bilinear warpalgorithm=forwardpatch patchsize=21 pixres=mpp resolution=10`.
  - Script writes `reduced_original_images.lis`, `reduced_doms.lis`, `reduced_selected_pair_paths.csv`, `preprocess_commands.sh`, and `preprocess_manifest.json`.
  - Ran dry-run with two cubes and a full dry-run for all 22 cubes.
  - Ran one-cube execution smoke; first attempt failed due to mock `ISISDATA`, second attempt succeeded with the conda environment's real `ISISDATA`.
  - Checked git status and observed generated `print.prt` was updated by ISIS as a side effect; it was not staged, restored, deleted, or otherwise edited.
- Files created/modified:
  - `examples/controlnet_construct/experiments/prepare_lro_polar_reduced_doms.py`
  - `work/lro_polar_adaptive_routing_preprocess/`
  - `work/lro_polar_adaptive_routing_preprocess_smoke/`
  - `work/lro_polar_adaptive_routing_preprocess_smoke_exec/`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/task_plan.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/findings.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/progress.md`

### Phase 5: Full Experiment Execution

- **Status:** complete
- **Started:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Ran full preprocessing execution with conda environment `asp360_new` and the conda-provided ISIS data tree.
  - Verified 22 reduced cubes and 22 10 m/pixel DOMs exist in `work/lro_polar_adaptive_routing_preprocess`.
  - Verified `reduced_selected_pair_paths.csv` contains 32 pair-side rows plus header and all rows have `all_exist=True`.
  - Ran all-method one-pair smoke; SIFT+FLANN and no-preview adaptive completed, deep methods exposed environment failures.
  - Ran full available-method benchmark for SIFT+FLANN and adaptive over all 16 selected pairs.
  - Generated reports and figures from the completed metadata.
- Files created/modified:
  - `work/lro_polar_adaptive_routing_preprocess/reduced_cubes/`
  - `work/lro_polar_adaptive_routing_preprocess/doms_10m/`
  - `work/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/task_plan.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/findings.md`
  - `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/progress.md`

### Phase 6: Nature-Style Figures and Paper Outputs

- **Status:** complete
- Actions taken:
  - Used the Python backend of the `nature-figure` workflow.
  - Generated method-success, match-yield, and adaptive-routing outcome figures.
  - Exported SVG, PDF, PNG preview, and 600 dpi TIFF for each theme.
  - Performed visual QA and shortened the adaptive outcome label for readability.

### Phase 7: Verification and Handoff

- **Status:** complete
- Actions taken:
  - Ran `python -m py_compile` on both experiment scripts.
  - Ran `python tests/smoke_import.py` in `asp360_new`.
  - Ran `git diff --check` for the touched scripts and plan files.
  - Checked generated figure formats with `file`.
  - Confirmed `.gitignore` is not modified in current scoped status output.
  - Confirmed `print.prt` remains modified as an ISIS side effect and was not restored, deleted, or staged.

### Phase 8: Deep-Learning Conda Handoff Supplement

- **Status:** in_progress
- **Started:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - User clarified that deep learning matching should run in conda environment `deep-learning`.
  - Re-read the active plan, findings, and progress.
  - Confirmed `deep-learning` exists in `conda env list`.
  - Located the existing three-stage handoff support: batch export/import plus `examples/learning_methods/run_deep_match_manifest.py`.

### Phase 9: External Reduced-10m Workspace Migration

- **Status:** in_progress
- **Started:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Moved generated reduced 10 m preprocessing outputs, smoke outputs, benchmark outputs, deep supplement outputs, and low-resolution adaptive outputs from repo `work/` to `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`.
  - Encountered an external filesystem limitation: symlinks are not allowed, so the initial `mv` of the deep benchmark alias link failed.
  - Recovered by copying the deep benchmark content without symlink aliases and removing the repo-side source directory.
  - Updated 129 migrated text/CSV/JSON/list files so old repo `work/lro_polar_adaptive_routing...` absolute paths now point to the external `reduced-10m` workspace.
  - Verified the migrated `reduced_selected_pair_paths.csv`, `reduced_original_images.lis`, and `reduced_doms.lis` now point to external reduced cube and DOM paths.
  - Verified no repo `work/lro_polar_adaptive_routing*` directories remain.
- Next actions:
  - Continue deep-learning handoff using the migrated external workspace.
  - Use real manifest alias directories or regenerate manifests instead of symlinks for import on the external filesystem.

### Phase 8/9: Deep-Learning Handoff After Migration

- **Status:** in_progress
- Actions taken:
  - Ran migrated SuperPoint+LightGlue one-pair manifest in `deep-learning` on CPU: 15/15 tile tasks succeeded.
  - Imported SuperPoint+LightGlue in `asp360_new`: first selected pair status `imported`, 846 points.
  - Ran migrated SIFT+LightGlue one-pair export, executed it in `deep-learning` on CPU, and imported it in `asp360_new`: first selected pair status `imported`, 6533 points.
  - Ran migrated LoFTR one-pair export and executed it in `deep-learning` on CPU: 15/15 tile tasks completed, but all effective matches were removed by the invalid mask.
  - Imported LoFTR in `asp360_new`: first selected pair status `imported_no_points`, 0 points.
  - Regenerated migrated benchmark reports and Nature-style figures under the external `reduced-10m` benchmark root.
- Observed results:
  - `superpoint_lightglue`: 1/16 pairs currently imported, 846 total points.
  - `sift_lightglue`: 1/16 pairs currently imported, 6533 total points.
  - `loftr`: 1/16 pairs currently attempted/imported, 0 valid points after mask filtering.
- Next actions:
  - Export remaining deep-match manifests for all missing selected pairs.
  - Execute manifests in `deep-learning`, skipping already completed first-pair results.
  - Import all completed manifests back in `asp360_new` and regenerate final reports/figures.

### Phase 10: LoFTR Invalid-Mask Debug

- **Status:** in_progress
- **Started:** 2026-06-01 Asia/Shanghai
- Trigger:
  - User paused LoFTR full run because raw LoFTR matches exist, but `invalid_mask_removed_count == raw_match_count`, leading to `imported_no_points`.
- Actions taken:
  - Stopped the running LoFTR full batch process.
  - Preserved completed SIFT+LightGlue and SuperPoint+LightGlue deep baseline outputs.
  - Began root-cause investigation before attempting code changes.
- Initial evidence:
  - LoFTR `.npz` result files already contain zero `left_points/right_points`, so filtering happens during `deep-learning` manifest execution before import.
  - Example task metadata: `raw_match_count=45`, `invalid_mask_removed_count=45`, `match_count=0`.
  - Manifest task masks are saved as uint8 OpenCV-style valid masks with values 0 and 255.
  - Candidate root cause: LoFTR frontend may treat the uint8 valid mask as an invalid mask and invert it, causing LoFTR inference to use invalid pixels and post-filter to remove all raw matches.
- Next actions:
  - Run a single-tile diagnostic comparing current mask handling, no mask, and corrected invalid-mask polarity.
  - Add debug output for raw point ranges, tile window, mask size, inside/outside counts, and left/right mask rejection counts.

### Phase 10 Update: LoFTR Mask Polarity Fix

- **Status:** in_progress
- **Updated:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Confirmed no full LoFTR batch should continue while the invalid-mask issue is unresolved.
  - Ran a single-tile diagnostic in `deep-learning` comparing original uint8 masks, no masks, and corrected bool invalid masks.
  - Confirmed the exported masks are OpenCV-style valid masks (`0=invalid`, `255=valid`), while the LoFTR frontend path expects bool invalid masks.
  - Fixed the adapter LoFTR branch so masks are normalized through `_as_invalid_mask()` before entering `LoFTRFrontend.prepare()`.
  - Added regression coverage proving uint8 valid masks are converted to bool invalid masks for LoFTR while bool invalid masks keep their existing semantics.
  - Updated `examples/learning_methods/run_deep_match_manifest.py` so deep-learning manifest execution defaults to `num_workers=1` and `torch_num_threads=8`.
  - Stopped the earlier one-pair smoke that was started with `--torch-num-threads 1`.
  - Re-ran focused unit tests: `tests.unitTest.image_match_deep_adapter_unit_test` and `tests.unitTest.learning_methods_deep_manifest_runner_unit_test`; 51 tests passed.
  - Restarted the first LoFTR pair smoke with `--num-workers 1 --torch-num-threads 8 --force-rerun`.
- Evidence:
  - Before fix on task 0: original uint8 masks yielded `raw_match_count=45`, and all 45 were rejected by the exported masks.
  - No-mask diagnostic yielded 936 raw matches and 862 post-filter valid matches.
  - Corrected bool invalid-mask diagnostic yielded 832 raw matches and 829 post-filter valid matches.
  - After the code fix, passing the original uint8 masks directly yielded 832 raw matches and 829 post-filter valid matches.
- Next actions:
  - Wait for the first-pair LoFTR smoke summary at `loftr/deep_match_results_smoke_after_mask_fix.json`.
  - If the summary has nonzero imported points, import the first pair back in `asp360_new`, then decide whether to resume full LoFTR with the new defaults.

### Phase 10 Update: Corrected LoFTR Smoke and Import

- **Status:** complete for first-pair smoke/import
- **Updated:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - Completed first-pair LoFTR smoke in `deep-learning` with `--num-workers 1 --torch-num-threads 8 --force-rerun`.
  - Smoke summary: 15/15 tile tasks succeeded, `actual_device=cpu`, `torch_num_threads=8`, no failed or incomplete tasks.
  - Created a real manifest alias directory on the external filesystem because symlink aliases are not supported there:
    - `loftr/deep_match_workspaces/REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal/tasks.json`
  - Imported the corrected first LoFTR pair back in `asp360_new`.
  - Regenerated benchmark reports and Nature-style figures from the migrated benchmark root.
- Results:
  - LoFTR first pair import status: `imported`.
  - Imported LoFTR point count for first pair: 7294.
  - LoFTR smoke tile summary: 7294 retained matches from 7305 raw matches, 11 removed by invalid-mask filtering.
  - Updated method summary: `loftr` now reports 1/16 successful pairs and 7294 total points; remaining LoFTR pairs are still exported/not rerun.
  - SIFT+LightGlue and SuperPoint+LightGlue remain preserved as deep baselines with one imported pair each.
- Artifacts:
  - Smoke summary: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/loftr/deep_match_results_smoke_after_mask_fix.json`
  - Import summary: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/loftr/deep_match_manifests_import_after_mask_fix.json`
  - Updated reports: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/reports`
- Next actions:
  - Resume remaining LoFTR manifests only after ensuring each import-expected alias directory exists as a real directory.
  - Use default deep-learning execution settings: `num_workers=1`, `torch_num_threads=8`.

### Phase 11: Intensity-Percentile Valid Mask Supplement

- **Status:** in_progress
- **Started:** 2026-06-01 Asia/Shanghai
- Trigger:
  - User observed many LoFTR match points visually falling in shadow regions and asked whether the previous 1% gray-tail exclusion was actually used as an invalid-pixel mask.
- Actions taken:
  - Confirmed the existing percentile controls are gray-stretch parameters, not invalid-pixel masking.
  - Added default-off valid-intensity percentile mask controls to the shared image-match preprocessing path and CLI.
  - Added focused unit tests for the new mask summary behavior and CLI arguments.
  - Verified focused tests and `py_compile` for the edited modules.
  - Exported a first-pair LoFTR manifest with `--valid-intensity-lower-percent 1.0 --valid-intensity-upper-percent 99.0`.
  - Ran the exported manifest in `deep-learning` with `--num-workers 1 --torch-num-threads 8 --force-rerun`.
  - Created the real import alias directory required by the external filesystem.
  - Imported the intensity-masked LoFTR results back in `asp360_new`.
  - Generated a reduced-cropped match-line visualization for the intensity-masked run.
- Results:
  - Intensity-masked LoFTR manifest status: `completed`, 15/15 tile tasks succeeded on CPU.
  - Runtime settings: `num_workers=1`, `torch_num_threads=8`.
  - Raw LoFTR matches: 6540.
  - Retained/imported LoFTR matches: 6475.
  - Invalid-mask removals after model inference: 65.
  - Corrected baseline LoFTR retained/imported matches for the same pair: 7294.
  - 1%/99% intensity masking reduced imported matches by 819 points and retained 88.77% of the corrected baseline.
- Artifacts:
  - Export/import root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_intensity_1_99`
  - Deep summary: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_intensity_1_99/loftr/deep_match_results_intensity_1_99.json`
  - Import summary: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_intensity_1_99/loftr/deep_match_manifests_import.json`
  - Match-line figure: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_intensity_1_99/loftr/match_viz/REDUCED_M110860982RE__REDUCED_M110881352RE_loftr_intensity_1_99_reduced_cropped.png`
- Next actions:
  - Visually compare the baseline and 1%/99% match-line figures.
  - Decide whether the full deep-learning benchmark should use the new intensity-percentile mask by default or keep it as a supplementary robustness setting.

### Phase 11 Verification

- **Status:** complete for first-pair supplement
- **Updated:** 2026-06-01 Asia/Shanghai
- Checks:
  - Viewed the intensity-masked match-line PNG; the image is non-empty and renders at 2678 x 554 pixels.
  - `python -m py_compile examples/image_match/preprocess.py examples/controlnet_construct/preprocess.py examples/image_match/tile_matching.py examples/image_match/image_match.py examples/image_match/deep_adapter.py examples/learning_methods/run_deep_match_manifest.py` passed.
  - `git diff --check` passed for the edited code, tests, and planning files.
  - Focused unit test command ran 54 tests and passed.
  - `python tests/smoke_import.py` passed with `smoke import ok`.

### Phase 11 Update: Conservative Default Mask

- **Status:** complete
- **Updated:** 2026-06-01 Asia/Shanghai
- Actions taken:
  - User approved changing the default away from strict `1.0/99.0` after discussing LRO NAC sensitivity.
  - Added parser tests first and confirmed they failed because defaults were still `None` and no disable flag existed.
  - Set the default valid-intensity percentile mask to `0.1/99.9`.
  - Added `--disable-valid-intensity-percentile-mask` so experiments can explicitly turn the default mask off.
  - Kept `--valid-intensity-lower-percent` and `--valid-intensity-upper-percent` as explicit overrides, including strict `1.0/99.0` ablation runs.
- Verification:
  - Focused parser tests passed after implementation.
  - Broader focused test command ran 55 tests and passed.
  - `py_compile` passed for edited image-match modules.
  - `git diff --check` passed for the edited files.
  - `python tests/smoke_import.py` passed with `smoke import ok`.
