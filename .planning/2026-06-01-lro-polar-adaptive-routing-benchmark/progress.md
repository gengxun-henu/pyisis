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
### Phase 12: Deep-Learning Rerun in Separate Directory

- **Status:** in_progress
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User requested rerunning the previous deep-learning matching test and placing outputs in a different directory.
- Planned output root:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_rerun_20260602`
- Execution policy:
  - Use migrated reduced-10m selected-pair CSV from `lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`.
  - Use `asp360_new` for manifest export/import.
  - Use `deep-learning` for manifest execution.
  - Keep deep runtime defaults at `num_workers=1` and `torch_num_threads=8`.
  - Start with a first-pair smoke export/run for `loftr`, `superpoint_lightglue`, and `sift_lightglue` before expanding to all selected pairs.
- Workspace hygiene:
  - Current repo has unrelated local changes in `print.prt`, `.planning/.active_plan`, `work/`, and a separate test assertion fix; do not stage or overwrite them during the experiment rerun.
- Export update:
  - Exported first selected pair for `loftr`, `superpoint_lightglue`, and `sift_lightglue` into the rerun root.
  - Each method produced one metadata row and one `deep_match_manifests.json` entry.
  - Each exported workspace contains 15 deep-learning tile tasks; 45 tiles were skipped before full-resolution deep inference.
  - Export metadata confirms the default valid-intensity percentile mask is active at `0.1/99.9`.
- Error encountered:
  - First deep-learning execution attempt read the manifest summary as if it had an `entries` list. The actual schema uses `pairs` and stores the task manifest path in each pair metadata JSON under `deep_match_export.manifest_path`.
  - The command did not use `set -e`, so an empty manifest variable was passed to `run_deep_match_manifest.py`, causing `IsADirectoryError` on the repo root.
  - Resolution: inspect the manifest summary/metadata schema and rerun with `set -euo pipefail`, extracting `deep_match_export.manifest_path` from the metadata JSON.
  - Second attempt used `set -u` before conda activation and hit conda's `deactivate-gxx_linux-64.sh` unbound `CONDA_BACKUP_CXX` variable. Resolution: avoid nounset around conda activation and use `set -eo pipefail` for the actual manifest loop.
- Deep-learning run update:
  - Ran all three exported first-pair manifests in the `deep-learning` conda environment.
  - Runtime: `--device cpu --num-workers 1 --torch-num-threads 8 --force-rerun`.
  - LoFTR: `status=completed`, 15/15 tasks succeeded, 7246 raw matches, 7228 retained matches, 18 removed by invalid-mask filtering.
  - SuperPoint+LightGlue: `status=completed`, 15/15 tasks succeeded, 728 retained matches.
  - SIFT+LightGlue: `status=completed`, 15/15 tasks succeeded, 6347 retained matches.
  - Summary files:
    - `loftr/deep_match_results_rerun_smoke.json`
    - `superpoint_lightglue/deep_match_results_rerun_smoke.json`
    - `sift_lightglue/deep_match_results_rerun_smoke.json`
- Import/update:
  - Created real `deep_match_workspaces/<pair_tag>/tasks.json` alias directories for all three methods because the external filesystem does not support the symlink alias expected by import.
  - Imported the completed deep-learning results back in `asp360_new`.
  - LoFTR import: `status=imported`, `point_count=7228`, `imported_task_count=15`, `failed_task_count=0`, `missing_result_count=0`, `skipped_empty_task_count=0`.
  - SuperPoint+LightGlue import: `status=imported`, `point_count=728`, `imported_task_count=15`, `failed_task_count=0`, `missing_result_count=0`, `skipped_empty_task_count=0`.
  - SIFT+LightGlue import: `status=imported`, `point_count=6347`, `imported_task_count=14`, `failed_task_count=0`, `missing_result_count=0`, `skipped_empty_task_count=1`.
  - Regenerated method summaries and root method summary in the rerun output root.
  - Match visualization PNGs were generated under each method's `match_viz/` directory.
- Verification:
  - Confirmed the following files exist for each method: `deep_match_results_rerun_smoke.json`, `deep_match_manifests.json`, `<method>_large_dom_match_summary.json`, and `<method>_large_dom_match_summary.csv`.
  - Confirmed root summary files exist: `large_dom_match_methods_summary.json` and `large_dom_match_methods_summary.csv`.
  - Confirmed the new output root did not overwrite the previous deep-learning benchmark directory.

### Phase 12 Full Selected-Pair Rerun

- **Status:** in_progress
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User accepted the first-pair smoke and requested the full selected-pair rerun, with match-line visualizations for all outputs.
- Scope:
  - Full selected-pair CSV has 32 side rows, corresponding to 16 DOM pairs.
  - Methods: `loftr`, `superpoint_lightglue`, `sift_lightglue`.
  - Use the default conservative valid-intensity percentile mask `0.1/99.9`.
  - Keep runtime settings at `num_workers=1`, `torch_num_threads=8`.
- Planned output root:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602`
- Visualization policy:
  - Do not pass `--no-write-match-visualization`; import should write per-pair match-line PNGs into each method's `match_viz/` directory.
- Export update:
  - Full export completed for `loftr`, `superpoint_lightglue`, and `sift_lightglue`.
  - Each method exported 16 pair metadata files with no export command failures.
  - Each method has 15 pairs with deep-learning tasks and 1 pair with `exported_task_count=0` because no tile met validity requirements.
  - Task counts: LoFTR 90 tile tasks, SuperPoint+LightGlue 90 tile tasks, SIFT+LightGlue 90 tile tasks.
  - Export root size after manifest/tile generation is about 2.5G.
- Deep-learning execution update:
  - Started full manifest execution in `deep-learning` using CPU, `num_workers=1`, `torch_num_threads=8`, and `force_rerun=True`.
  - LoFTR pair 1/16 completed: 15/15 tasks, raw matches 7246, retained matches 7228, invalid-mask removals 18.
  - LoFTR pair 2/16 completed: 13/13 tasks, raw matches 8849, retained matches 8832, invalid-mask removals 17.
  - LoFTR pair 3/16 completed: 2/2 tasks, raw matches 51, retained matches 50, invalid-mask removals 1.
  - LoFTR pair 4/16 completed: 4/4 tasks, raw matches 126, retained matches 126, invalid-mask removals 0.
  - LoFTR pair 5/16 completed: 12/12 tasks, raw matches 2875, retained matches 2855, invalid-mask removals 20.
  - LoFTR pair 6/16 completed: 12/12 tasks, raw matches 4188, retained matches 4165, invalid-mask removals 23.
  - LoFTR pair 7/16 completed: 1/1 task, raw matches 211, retained matches 211, invalid-mask removals 0.
  - LoFTR pair 8/16 completed: 1/1 task, raw matches 198, retained matches 194, invalid-mask removals 4.
  - LoFTR pair 9/16 completed: 11/11 tasks, raw matches 2173, retained matches 2158, invalid-mask removals 15.
  - LoFTR pair 10/16 completed: 6/6 tasks, raw matches 978, retained matches 969, invalid-mask removals 9.
  - LoFTR pair 11/16 completed: 1/1 task, raw matches 102, retained matches 100, invalid-mask removals 2.
  - LoFTR pair 12/16 completed: 1/1 task, raw matches 167, retained matches 165, invalid-mask removals 2.
  - LoFTR pair 13/16 completed: 1/1 task, raw matches 724, retained matches 706, invalid-mask removals 18.
  - LoFTR pair 14/16 completed: 9/9 tasks, raw matches 2851, retained matches 2836, invalid-mask removals 15.
  - LoFTR pair 15/16 failed during deep-learning execution with `SIGKILL` while running one `2623 x 652` tile.
  - Diagnostic note: the exported `.npy` arrays for the failed tile are only about 1.63 MiB each and load correctly, so this is more consistent with LoFTR inference peak memory on a long tile than corrupted input. Current swap was full after the failure.
  - Resolution direction: resume with keep-going semantics so the failed LoFTR pair does not stop SuperPoint+LightGlue and SIFT+LightGlue full runs; record LoFTR pair 15 as failed unless a lower-memory rerun is explicitly added.
  - Keep-going resume skipped completed LoFTR pairs 1-14, recorded LoFTR pair 15 as failed, and skipped LoFTR pair 16 because it had no exported tasks.
  - SuperPoint+LightGlue pair 1/16 completed: 15/15 tasks, raw matches 730, retained matches 730, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 2/16 completed: 13/13 tasks, raw matches 828, retained matches 828, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 3/16 completed: 2/2 tasks, raw matches 9, retained matches 9, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 4/16 completed: 4/4 tasks, raw matches 40, retained matches 40, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 5/16 completed: 12/12 tasks, raw matches 276, retained matches 276, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 6/16 completed: 12/12 tasks, raw matches 527, retained matches 527, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 7/16 completed: 1/1 task, raw matches 17, retained matches 17, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 8/16 completed: 1/1 task, raw matches 27, retained matches 27, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 9/16 completed: 11/11 tasks, raw matches 232, retained matches 232, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 10/16 completed: 6/6 tasks, raw matches 129, retained matches 129, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 11/16 completed: 1/1 task, raw matches 0, retained matches 0, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 12/16 completed: 1/1 task, raw matches 1, retained matches 1, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 13/16 completed: 1/1 task, raw matches 41, retained matches 41, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 14/16 completed: 9/9 tasks, raw matches 251, retained matches 251, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 15/16 completed: 1/1 task, raw matches 1, retained matches 1, invalid-mask removals 0.
  - SuperPoint+LightGlue pair 16/16 skipped because it had no exported tasks.
  - SIFT+LightGlue full execution started. Pair 1/16 completed: 15/15 tasks, raw matches 6348, retained matches 6348, invalid-mask removals 0.
  - SIFT+LightGlue pair 2/16 completed: 13/13 tasks, raw matches 5771, retained matches 5771, invalid-mask removals 0.
  - SIFT+LightGlue pair 3/16 completed: 2/2 tasks, raw matches 0, retained matches 0, invalid-mask removals 0.
  - SIFT+LightGlue pair 4/16 completed: 4/4 tasks, raw matches 0, retained matches 0, invalid-mask removals 0.
  - SIFT+LightGlue pair 5/16 completed: 12/12 tasks, raw matches 46, retained matches 46, invalid-mask removals 0.
  - SIFT+LightGlue pair 6/16 completed: 12/12 tasks, raw matches 1271, retained matches 1271, invalid-mask removals 0.
  - SIFT+LightGlue pair 7/16 completed: 1/1 task, raw matches 0, retained matches 0, invalid-mask removals 0.
  - SIFT+LightGlue pair 8/16 completed: 1/1 task, raw matches 0, retained matches 0, invalid-mask removals 0.
  - SIFT+LightGlue pair 9/16 completed: 11/11 tasks, raw matches 38, retained matches 38, invalid-mask removals 0.
  - SIFT+LightGlue pair 10/16 completed: 6/6 tasks, raw matches 17, retained matches 17, invalid-mask removals 0.
  - SIFT+LightGlue pair 11/16 completed: 1/1 task, raw matches 2, retained matches 2, invalid-mask removals 0.
  - SIFT+LightGlue pair 12/16 completed: 1/1 task, raw matches 8, retained matches 8, invalid-mask removals 0.
  - SIFT+LightGlue pair 13/16 completed: 1/1 task, raw matches 8, retained matches 8, invalid-mask removals 0.
  - SIFT+LightGlue pair 14/16 completed: 9/9 tasks, raw matches 24, retained matches 24, invalid-mask removals 0.
  - SIFT+LightGlue pair 15/16 completed: 1/1 task, raw matches 8, retained matches 8, invalid-mask removals 0.
  - SIFT+LightGlue pair 16/16 skipped because it had no exported tasks.
  - Keep-going resume finished with `errors=0`; the known LoFTR SIGKILL pair is recorded separately as a failed summary, not a resume-script error.
  - Created real `deep_match_workspaces/<pair_tag>/tasks.json` alias directories for all 16 pairs for LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue because the external filesystem does not support symlinks.
  - Imported all three full selected-pair method outputs back in `asp360_new`.
  - Import return codes: LoFTR 0, SuperPoint+LightGlue 0, SIFT+LightGlue 0.
  - Summary outputs exist at the root: `large_dom_match_methods_summary.json` and `large_dom_match_methods_summary.csv`.
  - Per-method summaries exist: `<method>_large_dom_match_summary.json` and `<method>_large_dom_match_summary.csv`.
  - Final imported statuses:
    - LoFTR: 14 `imported`, 1 `imported_no_points`, 1 `import_failed_no_usable_results`; total imported/visualized points 30595.
    - SuperPoint+LightGlue: 14 `imported`, 2 `imported_no_points`; total imported/visualized points 3109.
    - SIFT+LightGlue: 11 `imported`, 5 `imported_no_points`; total imported/visualized points 13541.
  - Match-line visualization PNGs:
    - LoFTR: 16 top-level PNGs under `loftr/match_viz/`.
    - SuperPoint+LightGlue: 16 top-level PNGs under `superpoint_lightglue/match_viz/`.
    - SIFT+LightGlue: 16 top-level PNGs under `sift_lightglue/match_viz/`.
  - Noted a summary schema issue: CSV `point_count` is blank after import, but metadata JSON `image_match.point_count` and CSV `match_visualization.point_count` contain the real counts.
- Final status:
  - Full selected-pair rerun is complete with one recorded LoFTR CPU/SIGKILL pair failure.
  - All requested match-line visualizations were generated.

### Phase 12 Follow-up: LoFTR Pair 15 Retry

- **Status:** complete
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User requested rerunning the previously failed LoFTR SIGKILL pair.
- Pair:
  - `REDUCED_M1200848465RE.echo.cal__REDUCED_M173567595LE.echo.cal`
- Actions taken:
  - First reran the original one-task manifest in `deep-learning` with CPU, `num_workers=1`, `torch_num_threads=8`, and `force_rerun=True`.
  - The original manifest retry exited abnormally without writing a retry summary, result `.npz`, or task log, consistent with the previous SIGKILL behavior.
  - Re-exported only this pair to a separate retry directory using `--max-image-dimension 1024 --sub-block-size-x 1024 --sub-block-size-y 1024`.
  - The smaller-tile export split the old `2623 x 652` single tile into 3 deep-learning tasks.
  - Ran the 3-task LoFTR retry manifest in `deep-learning` with CPU, `num_workers=1`, `torch_num_threads=8`, and `force_rerun=True`.
  - Imported the successful retry result in `asp360_new` and generated a match-line visualization.
- Results:
  - Deep summary: `status=completed`, `task_count=3`, `succeeded_task_count=3`, `failed_task_count=0`.
  - Raw matches: 395.
  - Retained/imported matches: 383.
  - Invalid-mask removals: 12.
  - Import status: `imported`, `point_count=383`, `imported_task_count=3`.
  - Match-line PNG:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602/loftr/match_viz/dom_REDUCED_M1200848465RE__dom_REDUCED_M173567595LE__20260602T081305.png`
- Output root:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602`
- Note:
  - This retry was kept in a separate output directory and did not overwrite the original 16-pair full summary.

### Phase 12 Follow-up: RANSAC-Filtered Match-Line Visualizations

- **Status:** complete
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User requested that generated deep-learning match-line plots be redrawn after RANSAC outlier filtering and that before/after connection counts be recorded.
- Implementation:
  - Added reusable script: `examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py`.
  - The script reads preserved `dom_keys/*_A.key` and `dom_keys/*_B.key` files, applies existing homography RANSAC filtering, redraws the connection PNGs, and writes CSV/JSON summaries.
  - Original `match_viz/` PNGs were not overwritten.
- Main full-run output:
  - Root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602`
  - RANSAC PNG count: 48.
  - Combined counts: raw matches 47,245; RANSAC retained 24,388; dropped 22,857; retained fraction 0.5162.
  - LoFTR: 16 pairs; raw 30,595; retained 11,145; dropped 19,450; retained fraction 0.3643.
  - SuperPoint+LightGlue: 16 pairs; raw 3,109; retained 765; dropped 2,344; retained fraction 0.2461.
  - SIFT+LightGlue: 16 pairs; raw 13,541; retained 12,478; dropped 1,063; retained fraction 0.9215.
  - Summary files:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.json`
- LoFTR pair-15 retry output:
  - Root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602`
  - RANSAC PNG count: 1.
  - Counts: raw 383; retained 9; dropped 374; retained fraction 0.0235.
  - RANSAC PNG:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/loftr_pair15_retry_1024_20260602/loftr/match_viz_ransac/dom_REDUCED_M1200848465RE__dom_REDUCED_M173567595LE__20260602T081305__ransac.png`
- Verification:
  - `python -m py_compile examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py` passed.
  - Generated RANSAC PNG count under the full deep output root: 49 including the separate retry directory.

### Phase 13: Five-Method RANSAC Visualization and Nature Figure Inputs

- **Status:** complete
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User requested SIFT+FLANN and adaptive routing matching, RANSAC-filtered match-line figures, before/after counts, and a five-method Nature-style figure input/plot package.
- Actions taken:
  - Ran `match_original_gsd_lro_dom_pairs_large.py` for `sift_flann,adaptive` in the full selected-pair output root with 1024 x 1024 matching tiles.
  - Regenerated RANSAC-filtered match-line visualizations for `loftr,superpoint_lightglue,sift_lightglue,sift_flann,adaptive`.
  - Added `examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py`.
  - The plotting script writes pair-level and method-level source data plus SVG/PDF/TIFF/PNG figure outputs using matplotlib with the headless `Agg` backend.
- Results:
  - RANSAC PNG counts: 16 per method, 80 total across the five methods.
  - Combined: 59,862 raw matches -> 34,219 RANSAC-retained matches; retained fraction 57.16%.
  - LoFTR: 30,595 raw -> 11,145 retained; 14/16 pairs retained; runtime 2,011.998 s from deep task timestamps.
  - SuperPoint+LightGlue: 3,109 raw -> 765 retained; 14/16 pairs retained; runtime 556.809 s from deep task timestamps.
  - SIFT+LightGlue: 13,541 raw -> 12,478 retained; 11/16 pairs retained; runtime 541.780 s from deep task timestamps.
  - SIFT+FLANN: 3,606 raw -> 2,754 retained; 16/16 pairs retained; runtime 93.710 s from command-to-summary mtime proxy.
  - Adaptive: 9,011 raw -> 7,077 retained; 16/16 pairs retained; runtime 103.370 s from command-to-summary mtime proxy.
  - Adaptive routing caveat: this run still lacks preview/original-image context for route selection, so it falls back to FLANN through the adaptive quality-gated wrapper.
- Output files:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.csv`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/ransac_match_visualization_summary.json`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_pair_summary.csv`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_method_summary.csv`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_match_comparison_source_data.json`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_match_comparison.svg`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_match_comparison.pdf`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_match_comparison.tiff`
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep_full_20260602/nature_figure_inputs/five_method_match_comparison.png`
- Verification:
  - `python -m py_compile examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py` passed.
  - All expected source data and figure files exist.
  - PNG preview was visually inspected after export; no blank rendering or obvious text overlap remained.

### Phase 14: True Deep-Learning Adaptive Routing Rerun

- **Status:** complete
- **Started:** 2026-06-02 Asia/Shanghai
- Trigger:
  - User clarified that adaptive routing should genuinely run deep-learning methods, use low-resolution DOMs if needed, use `REDUCED*` cubes for lighting information, and define pair success after RANSAC filtering.
- Code update:
  - Fixed `examples/image_match/image_match.py` so `deep_match_mode=export` no longer fails when adaptive routing initially selects a traditional matcher such as FLANN.
  - The fix preserves the original routed matcher in metadata, then exports the first deep cascade fallback for execution in `deep-learning`.
  - Added focused regression coverage in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`.
- Verification before full run:
  - Ran focused tests:
    - `test_match_dom_pair_export_uses_deep_fallback_when_adaptive_routes_to_flann`
    - `test_match_dom_pair_initial_routed_flann_export_uses_selected_deep_preset_matcher`
  - Result: 2 tests passed.
  - `python -m py_compile examples/image_match/image_match.py tests/unitTest/controlnet_construct_pipeline_unit_test.py` passed.
- Full true-adaptive run:
  - Output root:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602`
  - Export stage in `asp360_new`: completed 16/16 pairs, reused 22 low-resolution DOMs, exported 95 LightGlue/SuperPoint tile tasks.
  - Routing detail: all 16 pairs were exported to LightGlue/SuperPoint; 3 pairs were initially routed to FLANN and then exported through the deep fallback path.
  - Deep execution in `deep-learning`: 16/16 manifests completed, 95/95 tasks succeeded, 0 failed tasks, CPU execution, `num_workers=1`, `torch_num_threads=8`, total wrapper elapsed time 642.578 s.
  - Import stage in `asp360_new`: completed 16/16 pairs, created 16 real alias `tasks.json` directories because the external filesystem does not support symlinks.
- RANSAC-filtered adaptive result:
  - Raw imported matches: 3,573.
  - RANSAC-retained matches: 830.
  - Dropped matches: 2,743.
  - Retained fraction: 23.23%.
  - Pair success after RANSAC: 15/16.
  - RANSAC-filtered PNG count: 16 under `adaptive/match_viz_ransac/`.
- Updated five-method comparison with true adaptive:
  - LoFTR: 30,595 raw -> 11,145 retained; 14/16 successful after RANSAC.
  - SuperPoint+LightGlue: 3,109 raw -> 765 retained; 14/16 successful after RANSAC.
  - SIFT+LightGlue: 13,541 raw -> 12,478 retained; 11/16 successful after RANSAC.
  - SIFT+FLANN: 3,606 raw -> 2,754 retained; 16/16 successful after RANSAC.
  - True adaptive deep-learning: 3,573 raw -> 830 retained; 15/16 successful after RANSAC.
  - True adaptive deep task runtime: 605.001 s from deep task started/finished timestamps.
- Output files:
  - Adaptive execution summary:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/adaptive_deep_learning_execution_summary.json`
  - Adaptive RANSAC summary:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/ransac_match_visualization_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/ransac_match_visualization_summary.json`
  - Updated true-adaptive five-method source data and figure:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_pair_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_method_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_source_data.json`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.svg`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.pdf`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.tiff`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_adaptive_deep_20260602/nature_figure_inputs_true_adaptive/five_method_match_comparison_true_adaptive.png`
- Final verification:
  - `python tests/smoke_import.py` passed in `asp360_new` with mock `ISISDATA`.
  - `git diff --check` passed for the touched code and planning files.
  - Confirmed all true-adaptive source data and figure files exist.
  - Confirmed `adaptive/match_viz_ransac/*.png` count is 16.

### Phase 15: Prior-Only Adaptive Routing Rule Revision

- **Status:** in_progress
- **Started:** 2026-06-02 10:47:14 CST
- Trigger:
  - User clarified that adaptive routing should select a matcher from image texture and lighting diagnostics, and should not recursively switch from SIFT to LightGlue or LoFTR after the selected matcher fails.
- Code updates:
  - `examples/image_match/adaptive_routing.py`
    - `build_cascade_plan()` now returns only the prior-selected matcher.
    - `decide_post_match_action()` no longer requests a next matcher when quality is insufficient.
    - Pair routing now uses SIFT+FLANN for rich texture and small lighting difference.
    - SIFT+LightGlue is the default/main deep route for moderate texture or moderate lighting difference.
    - SuperPoint+LightGlue is selected for weak-to-moderate texture when lighting is not extreme.
    - LoFTR is selected for combined high texture sparseness and large lighting difference, or extreme single-condition cases.
  - `examples/image_match/image_match.py`
    - `_adaptive_cascade_steps_from_summary()` now returns a single adaptive step.
    - Removed export-mode deep fallback for FLANN/BF selected adaptive routes.
    - Adaptive direct-mode metadata now records `cascade_disabled=true` and `no_post_match_fallback=true`.
  - `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`
    - Adaptive preset map now uses `lightglue_official_sift.json` for the main `lightglue`/`sift_lightglue` route and keeps `lightglue_official_superpoint.json` under `superpoint_lightglue`.
- Test-first verification:
  - Modified tests first and confirmed RED failures in the old behavior:
    - `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.controlnet_construct_pipeline_unit_test -v`
    - Expected failures covered old cascade plans, old BF route, export fallback, and post-match fallback decision.
  - After implementation:
    - `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test -v` passed, 30 tests.
    - Focused pipeline tests passed:
      - `test_adaptive_cascade_steps_keep_only_prior_selected_matcher_without_presets`
      - `test_match_dom_pair_export_rejects_non_deep_adaptive_route_without_fallback`
      - `test_match_dom_pair_adaptive_quality_rejection_records_no_post_match_fallback`
      - `test_match_dom_pair_initial_routed_flann_export_uses_selected_deep_preset_matcher`
    - `python -m py_compile examples/image_match/adaptive_routing.py examples/image_match/image_match.py examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py tests/unitTest/image_match_adaptive_routing_unit_test.py tests/unitTest/controlnet_construct_pipeline_unit_test.py` passed.
    - `python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v` passed, 122 tests, 1 real-data skip.
    - `python tests/smoke_import.py` passed.
    - `git diff --check` passed.
- Remaining:
  - Real selected-pair adaptive benchmark has not yet been rerun with the Phase 15 prior-only behavior.
  - Existing Phase 14 true-adaptive figures still reflect the now-superseded fallback-export strategy and should not be used as final evidence for prior-only adaptive routing.

### Phase 15: Prior-Only Adaptive Real Selected-Pair Rerun

- **Status:** in_progress
- **Started:** 2026-06-02 Asia/Shanghai
- Output root:
  - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602`
- Route preclassification:
  - Reused the migrated reduced selected-pair CSV:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv`
  - Generated/reused low-resolution level-3 DOMs under:
    - `adaptive_route_probe/low_resolution_doms/level3`
  - Wrote route partition files:
    - `adaptive_route_probe/adaptive_prior_only_route_partition.csv`
    - `adaptive_route_probe/adaptive_prior_only_route_partition.json`
    - `adaptive_route_probe/sift_flann_pair_paths.csv`
    - `adaptive_route_probe/sift_lightglue_pair_paths.csv`
  - Prior-only route counts:
    - SIFT+FLANN: 3 pairs
    - SIFT+LightGlue: 13 pairs
    - SuperPoint+LightGlue: 0 pairs
    - LoFTR: 0 pairs
- Execution plan:
  - Run the 3 SIFT+FLANN-routed pairs directly in `asp360_new`.
  - Export the 13 SIFT+LightGlue-routed pairs in `asp360_new`.
  - Run those manifests in `deep-learning` with `num_workers=1` and `torch_num_threads=8`.
  - Import the completed deep results back into the same adaptive output directory.
- Direct SIFT+FLANN adaptive subset:
  - Completed in `asp360_new` with prior-only routing and no fallback cascade.
  - Input subset:
    - `adaptive_route_probe/sift_flann_pair_paths.csv`
  - Output directory:
    - `adaptive/`
  - Produced 3 `_A.key` files under `adaptive/dom_keys`.
  - Top-level `match_metadata` contains 3 pair metadata JSON files plus command metadata; final aggregation should filter out non-pair command metadata.
- SIFT+LightGlue adaptive export subset:
  - Completed in `asp360_new` with prior-only routing and no fallback cascade.
  - Input subset:
    - `adaptive_route_probe/sift_lightglue_pair_paths.csv`
  - Output directory:
    - `adaptive/`
  - Wrote manifest summary:
    - `adaptive/deep_match_manifests.json`
  - Found 13 unique deep-learning task manifests under:
    - `adaptive/deep_match_workspaces/*/tasks.json`
  - Export metadata records `matcher_method_effective=lightglue` with the SIFT+LightGlue preset.
- SIFT+LightGlue deep-learning execution:
  - Completed in `deep-learning` conda environment.
  - Command policy:
    - `--device cpu`
    - `--num-workers 1`
    - `--torch-num-threads 8`
    - `--force-rerun`
  - Manifest result:
    - 13 completed
    - 0 failed
  - CUDA was unavailable, so LightGlue ran on CPU.
- First import attempt:
  - Failed before importing the first SIFT+LightGlue pair.
  - Error:
    - `FileNotFoundError` for `adaptive/deep_match_workspaces/REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal/tasks.json`
  - Cause:
    - Exported workspaces are named with DOM/hash identifiers, while the import wrapper looked for pair-tag directories derived from `REDUCED_*.echo.cal` image names.
  - Next action:
    - Create pair-tag alias directories containing the corresponding exported `tasks.json`; do not rerun deep-learning inference.
- Import retry:
  - Created 13 pair-tag alias manifest directories under `adaptive/deep_match_workspaces`.
  - Re-ran `deep-match-mode import` in `asp360_new`.
  - Import completed for all 13 SIFT+LightGlue-routed pairs.
  - Combined adaptive output now contains 16 `_A.key` files:
    - 3 direct SIFT+FLANN-routed pairs
    - 13 imported SIFT+LightGlue-routed pairs
  - Clean prior-only pair summary:
    - `adaptive/adaptive_prior_only_clean_pair_summary.csv`
    - `adaptive/adaptive_prior_only_clean_pair_summary.json`
  - Clean summary values:
    - 16 pair rows
    - matcher counts: 13 SIFT+LightGlue, 3 SIFT+FLANN
    - status counts: 8 imported, 5 imported_no_points, 3 matched
    - raw/imported point count total: 13,930
- RANSAC rerender:
  - Re-ran `rerender_ransac_match_visualizations.py --methods adaptive`.
  - Outputs:
    - `adaptive/ransac_match_visualization_summary.csv`
    - `adaptive/ransac_match_visualization_summary.json`
    - `adaptive/match_viz_ransac/`
    - root `ransac_match_visualization_summary.csv/json`
  - Adaptive RANSAC summary:
    - pair_count: 16
    - raw_match_count: 13,930
    - ransac_retained_count: 12,767
    - ransac_dropped_count: 1,163
    - retained fraction: 0.9165
- Five-method prior-only figure/source data:
  - Built lightweight combined root:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/five_method_prior_only`
  - Combined rows:
    - 16 LoFTR baseline rows from Phase 14 fixed-method run
    - 16 SuperPoint+LightGlue baseline rows from Phase 14 fixed-method run
    - 16 SIFT+LightGlue baseline rows from Phase 14 fixed-method run
    - 16 SIFT+FLANN baseline rows from Phase 14 fixed-method run
    - 16 Phase 15 prior-only adaptive rows
  - Reconstructed 13 adaptive `deep_match_run_summary.json` files from task logs so adaptive runtime includes CPU SIFT+LightGlue inference time.
  - Updated plotting runtime logic for adaptive:
    - deep task started/finished sum plus command-to-summary mtime proxy.
  - Final source data and figures:
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_pair_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_method_summary.csv`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison_source_data.json`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.svg`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.pdf`
    - `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_prior_only_20260602/nature_figure_inputs_prior_only/five_method_match_comparison.tiff`
  - Final five-method summary:
    - LoFTR: 11,145 retained, 33.53 min.
    - SuperPoint+LightGlue: 765 retained, 9.28 min.
    - SIFT+LightGlue: 12,478 retained, 9.03 min.
    - SIFT+FLANN: 2,754 retained, 1.56 min.
    - Adaptive prior-only: 12,767 retained, 6.84 min.
  - Verification:
    - Figure/source files exist.
    - `python -m py_compile examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py` passed in `asp360_new`.
- 2026-06-02 17:03 +0800: Started Phase 16 valid-block texture evidence cleanup. Read active plan and inspected `examples/image_match/adaptive_routing.py`, `examples/image_match/image_match.py`, `examples/image_match/texture_sparseness.py`, and related unit tests. Current finding: tile sparseness already skips low-valid-ratio blocks and returns `None` when no valid tile exists, but adaptive route source selection still prefers low-resolution preview DOMs and `route_matcher_for_pair_with_sparseness` maps missing sparseness to legacy `mean_real_texture_score=0.5`.
- 2026-06-02 17:15 +0800: Completed Phase 16 implementation. Added actual matched-image texture source selection in `examples/image_match/image_match.py`, using `matched_dom` for DOM-space and `raw_original_cube` for ORI-space, with low-resolution DOMs only as fallback. Updated `examples/image_match/adaptive_routing.py` so missing pair sparseness keeps `mean_real_texture_score=None` instead of neutral `0.5`.
- 2026-06-02 17:15 +0800: Added regression coverage in `tests/unitTest/image_match_adaptive_routing_unit_test.py` for DOM-space actual-source texture diagnostics and missing texture evidence. Updated stale `tests/unitTest/controlnet_construct_matching_unit_test.py` cascade expectation to current prior-only no-fallback semantics.
- 2026-06-02 17:16 +0800: Verification passed in `asp360_new`: `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_texture_sparseness_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v` ran 262 tests with 1 skipped; `python tests/smoke_import.py` passed; `git diff --check` passed for touched files.
- 2026-06-02 17:35 +0800: Added effective valid-block aggregation diagnostics for texture sparseness after user review. `ImageSparsenessSummary` now reports `skipped_invalid_tile_count`, `aggregation_tile_count`, `aggregation_pixel_count`, `aggregation_valid_pixel_count`, and `aggregation_valid_pixel_ratio`, where aggregation pixel totals only include blocks that pass the valid-pixel-ratio threshold. Verification passed: `python -m unittest tests.unitTest.image_match_texture_sparseness_unit_test tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_tile_diagnostics_unit_test -v` ran 46 tests OK; `git diff --check` passed for touched texture files.
- 2026-06-02 17:27 +0800: Completed Phase 17 feature-count routing/reporting cleanup. Added a hard adaptive-routing rule that sends low texture-probe keypoint count or density directly to LoFTR before the texture/lighting route bins. Forwarded left/right texture probes into the prior-only router from `image_match.py`.
- 2026-06-02 17:27 +0800: Aligned SIFT+LightGlue with SIFT+FLANN for this benchmark by changing `examples/controlnet_construct/presets/lightglue_official_sift.json` from `max_features=4096` to `max_features=1000`; confirmed `classic_sift_flann.json` is also `max_features=1000`.
- 2026-06-02 17:27 +0800: Separated extracted feature counts from matched correspondence counts in `match_dom_pair` summaries. New fields are `left_feature_count_total`, `right_feature_count_total`, `feature_count_total`, and `tile_match_count_total`; RANSAC summaries still provide raw/retained/dropped correspondence counts.
- 2026-06-02 17:27 +0800: Propagated extracted-feature source data into the five-method Nature figure inputs. Pair rows now include feature totals and tile match totals, and method rows include summed and median extracted feature counts.
- 2026-06-02 17:27 +0800: Verification passed in `asp360_new`: py_compile for the touched benchmark/plot/image-match modules passed; `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v` ran 249 tests with 1 skipped and passed; `python tests/smoke_import.py` passed; `git diff --check` passed for touched files.
- 2026-06-02 17:31 +0800: Started Phase 18 latest-parameter five-method full rerun. Scope: three deep methods (LoFTR, SuperPoint+LightGlue, SIFT+LightGlue), one classic SIFT+FLANN baseline, and one prior-only adaptive run using the latest texture/keypoint routing rules. Planned output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602`.
- 2026-06-02 17:34 +0800: Phase 18 SIFT+FLANN full selected-pair benchmark completed in `asp360_new`. Output: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602/sift_flann`. Runner summary: 16 pair metadata rows, 0 failed metadata rows, return code 0. Real metadata includes extracted feature-count fields and `max_features=1000`.
- 2026-06-02 17:38 +0800: Phase 18 deep-method export completed in `asp360_new` for LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue. Each method produced 16 pair metadata rows, 0 failed metadata rows, and return code 0. Confirmed SIFT+LightGlue export uses `lightglue_sift` with `max_features=1000`.
- 2026-06-02 18:09 +0800: Phase 18 LoFTR deep-learning execution completed in conda environment `deep-learning` with CPU, `num_workers=1`, `torch_num_threads=8`, and `force_rerun=True`. LoFTR completed 16/16 manifests; 96/96 tile tasks succeeded and 0 failed. The run advanced to SuperPoint+LightGlue execution.
- 2026-06-02 18:18 +0800: Phase 18 SuperPoint+LightGlue deep-learning execution completed in conda environment `deep-learning` with CPU, `num_workers=1`, `torch_num_threads=8`, and `force_rerun=True`. SuperPoint+LightGlue completed 16/16 manifests; 96/96 tile tasks succeeded and 0 failed. The run advanced to SIFT+LightGlue execution.
- 2026-06-02 18:20 +0800: Phase 18 all fixed deep-method execution completed in conda environment `deep-learning`. LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue each completed 16/16 manifests with 96/96 tile tasks succeeded and 0 failed. Overall summary: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602/run_all_deep_manifests_latest_summary.json`.
- 2026-06-02 18:21 +0800: First Phase 18 deep import attempt in `asp360_new` failed before importing because external-workspace manifests used DOM+hash workspace directories while import expected `REDUCED_*.echo.cal__REDUCED_*.echo.cal/tasks.json` alias directories. Created 48 real alias directories from existing `tasks.json` files: 16 each for LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue.
- 2026-06-02 18:24 +0800: Phase 18 deep import rerun completed in `asp360_new`. LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue each returned code 0 with 16 metadata rows and 0 failed metadata rows. Per-method summaries were regenerated under the latest-parameter output root.
- 2026-06-02 18:28 +0800: Phase 18 adaptive export hit SIGKILL 137 while route/exporting the first pair, even with `num_worker_parallel_cpu=1`. Root cause was the adaptive texture probe reading full 10k-scale DOM bands before routing. Added bounded actual-image preview reading for `_compute_texture_probe_from_cube_path()` so routing still uses the matched DOM source but does not load the full raster. Verification passed: `python -m py_compile examples/image_match/image_match.py`; `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_texture_sparseness_unit_test -v` ran 46 tests OK.
- 2026-06-02 18:55 +0800: Phase 18 adaptive latest-parameter partitioned execution completed in `asp360_new`. Because prior-only export mode correctly rejects SIFT+FLANN routes, reran only missing pairs through a partition loop: deep-selected pairs stayed exported, while 13 SIFT+FLANN-selected pairs were executed directly. Adaptive now has 16/16 pair metadata rows under the latest-parameter output root. Logs: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602/adaptive/adaptive_partition_logs/`.
- 2026-06-02 18:58 +0800: Phase 18 adaptive deep-learning execution completed in conda environment `deep-learning`: 2/2 adaptive manifests completed, 28/28 tile tasks succeeded, 0 failed. First import alias attempt used task tile filenames and produced an invalid `task_00000_left.echo.cal__task_00000_right.echo.cal` alias; next step is to regenerate aliases from workspace directory names.
- 2026-06-02 19:42 +0800: Phase 18 latest-parameter five-method rerun completed. Fixed-method deep execution used `deep-learning` with CPU, `num_workers=1`, and `torch_num_threads=8`; LoFTR, SuperPoint+LightGlue, and SIFT+LightGlue each completed 16/16 manifests and 96/96 tile tasks. Adaptive used prior-only routing with latest texture/keypoint rules: 14 direct SIFT+FLANN routes in `asp360_new` and 2 SIFT+LightGlue import routes from `deep-learning`.
- 2026-06-02 19:42 +0800: Fixed Phase 18 reporting issues discovered during final plotting: bounded adaptive texture preview prevented full-DOM OOM; RANSAC visualization now resolves DOM paths from direct metadata and deep import manifests; batch summaries and figure source data now read nested `image_match` fields; `image_match.py` metadata sidecars now preserve `left_feature_count_total`, `right_feature_count_total`, `feature_count_total`, and `tile_match_count_total`.
- 2026-06-02 19:42 +0800: Final RANSAC summary for latest-parameter root: LoFTR raw=31,565 retained=11,172; SuperPoint+LightGlue raw=3,439 retained=770; SIFT+LightGlue raw=5,348 retained=3,906; SIFT+FLANN raw=3,611 retained=2,757; Adaptive raw=5,511 retained=4,220. Adaptive retained fraction=0.7657 and SIFT+FLANN retained fraction=0.7635.
- 2026-06-02 19:42 +0800: Final feature-count reporting: SIFT+FLANN has 16/16 feature-count rows, total extracted features=168,395. Adaptive has 14/16 feature-count rows from direct SIFT+FLANN branches, total extracted features=347,797; the 2 deep import branches do not record detector feature totals in the imported manifest output.
- 2026-06-02 19:42 +0800: Final outputs are under `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_latest_params_20260602`. Figure/source outputs are under `nature_figure_inputs_latest_params/`: `five_method_pair_summary.csv`, `five_method_method_summary.csv`, `five_method_match_comparison_source_data.json`, `five_method_match_comparison.svg`, `.pdf`, `.tiff`, and `.png`.
- 2026-06-02 19:42 +0800: Verification passed in `asp360_new`: `python -m py_compile examples/image_match/image_match.py examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py`; `git diff --check` for touched benchmark/plot/image-match files; `python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_texture_sparseness_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v` ran 263 tests OK with 1 skipped; `python tests/smoke_import.py` passed.
