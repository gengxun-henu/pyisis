# Task Plan: LRO Polar Adaptive Routing Benchmark

## Goal

Build a reproducible experiment on reduced LRO NAC polar imagery to compare adaptive routing against SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, and LoFTR, then generate Nature-style figures from the benchmark results.

## Current Phase

Phase 11

## Phases

### Phase 1: Dataset and Pipeline Discovery

- [x] Create isolated planning directory for this experiment
- [x] Confirm source data directory is readable
- [x] Count source `*.echo.cal.cub` files and inspect existing lists/map files
- [x] Locate existing reduce/cam2map/DOM generation and adaptive matching scripts in the repo
- [x] Identify matcher preset names for SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, and LoFTR
- [x] Document findings in `findings.md`
- **Status:** complete

### Phase 2: Preprocessing Design

- [x] Define output workspace under `work/` for this experiment
- [x] Generate or validate reduced cubes using ISIS `reduce` with `sscale=10` and `lscale=10`
- [x] Generate 10 m/pixel DOMs from reduced cubes using `lunar_polarstereographic.map`
- [x] Create reduced original and DOM list files for downstream matching
- [x] Record exact ISIS commands and environment variables
- **Status:** complete

### Phase 3: Matcher Benchmark Design

- [x] Define image-pair selection strategy from reduced DOM footprints/overlap lists
- [x] Configure adaptive routing run
- [x] Configure single-method baselines: SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, LoFTR
- [x] Define common metrics: matched pairs, valid tiles, matched tiles, candidate matches, inliers, inlier ratio, coverage, residuals, runtime, fallback path, failures
- [x] Define output schema for CSV/JSON summaries suitable for figure generation
- **Status:** complete

### Phase 4: Implementation

- [x] Add or extend experiment scripts/configs without disturbing existing benchmark outputs
- [x] Add dry-run/preflight checks for data paths, ISIS tools, GPU-dependent matchers, and output directories
- [x] Add report aggregation for adaptive vs fixed-method comparison
- [x] Add focused tests or smoke checks for config generation and result parsing
- **Status:** complete

### Phase 5: Full Experiment Execution

- [x] Run reduction stage or skip already verified outputs
- [x] Run DOM generation stage or skip already verified outputs
- [x] Run adaptive routing benchmark
- [x] Run fixed-method benchmarks
- [x] Record wall/core timings, failures, and generated artifacts after each stage
- **Status:** complete

### Phase 6: Nature-Style Figures and Paper Outputs

- [x] Use Python/matplotlib through the `nature-figure` workflow
- [x] Generate one-theme-per-figure outputs for method success, match quality, runtime, and routing behavior
- [x] Export SVG, PDF, TIFF 600 dpi, and PNG previews
- [x] Run visual QA for label overlap, units, readable legends, and data traceability
- [x] Summarize figure conclusions for manuscript text
- **Status:** complete

### Phase 7: Verification and Handoff

- [x] Run unit/smoke tests relevant to touched code
- [x] Verify generated reports and figures exist
- [x] Update `progress.md`, `findings.md`, and this plan with final status
- [x] Confirm `.gitignore` is unmodified and `print.prt` remains only an unstaged ISIS side effect
- **Status:** complete

### Phase 8: Deep-Learning Conda Handoff Supplement

- [x] Confirm `deep-learning` conda environment dependencies for LightGlue/SuperPoint/LoFTR
- [x] Extend selected-pair benchmark runner to pass through `deep-match-mode export/import`
- [x] Export one-pair deep-match manifests from `asp360_new`
- [x] Execute exported manifests in `deep-learning`
- [x] Import deep-match results back in `asp360_new`
- [ ] Run full deep-method supplement if smoke succeeds with corrected LoFTR mask handling
- [x] Regenerate summaries and figures including one-pair deep-learning results
- [x] Update findings/progress with LoFTR invalid-mask root cause and default runtime settings
- [ ] Update findings/progress with final deep-method status
- **Status:** in_progress

### Phase 9: External Reduced-10m Workspace Migration

- [x] Move generated 10 m reduced cubes, DOMs, smoke outputs, benchmark outputs, and deep benchmark outputs to the external data tree
- [x] Update reduced list/CSV/JSON/text files so paths point to the external `reduced-10m` workspace
- [x] Handle external filesystem symlink limitation in deep-match manifest aliases
- [x] Continue one-pair deep-learning matching from the migrated external workspace
- [x] Regenerate summaries and figures from the migrated workspace
- [ ] Continue full selected-pair deep-learning matching from the migrated external workspace
- **Status:** in_progress

### Phase 10: LoFTR Invalid-Mask Debug and Runtime Defaults

- [x] Pause LoFTR full batch execution
- [x] Run one-tile diagnostics for mask polarity, point coordinate ranges, mask dimensions, and filter rejection counts
- [x] Confirm LoFTR failures were caused by uint8 valid-mask polarity being passed into a bool invalid-mask frontend
- [x] Fix LoFTR mask normalization before frontend preparation
- [x] Add unit regression coverage
- [x] Set deep-learning manifest runtime defaults to `num_workers=1` and `torch_num_threads=8`
- [x] Complete first-pair LoFTR smoke with corrected mask handling and 8 torch threads
- [x] Import corrected first-pair LoFTR results and regenerate reports
- [ ] Resume remaining LoFTR manifests after creating real import alias directories on the external filesystem
- **Status:** in_progress

### Phase 11: Intensity-Percentile Valid Mask Supplement

- [x] Confirm existing lower/upper percent parameters are gray-stretch controls, not invalid-pixel masking
- [x] Add explicit valid-intensity percentile mask parameters with default-off behavior
- [x] Add unit coverage for the new intensity mask controls
- [x] Export first-pair LoFTR manifest using `--valid-intensity-lower-percent 1.0 --valid-intensity-upper-percent 99.0`
- [x] Run exported first-pair LoFTR manifest in `deep-learning` with `num_workers=1` and `torch_num_threads=8`
- [x] Import intensity-masked LoFTR results back in `asp360_new`
- [x] Generate a match-line visualization for the intensity-masked first pair
- [x] Compare baseline corrected LoFTR against the 1%/99% intensity-masked run
- [x] Set the default valid-intensity percentile mask to conservative `0.1/99.9` for LRO NAC matching
- [ ] Decide whether to apply the intensity-percentile mask to the remaining full deep-learning runs
- **Status:** in_progress

## Key Questions

1. Are the 22 `work/*.echo.cal.cub` files already SPICE-initialized and suitable for `reduce`/`cam2map`, or should the backup cubes be used as the source of truth?
2. Does `lunar_polarstereographic.map` already specify 10 m/pixel resolution, or must `cam2map` override map scale/resolution explicitly?
3. Which existing pipeline entry point should drive the comparison: a current controlnet construction script, a new thin benchmark wrapper, or both?
4. What is the expected pair-selection policy: all overlapping pairs, a curated subset, or pairs selected to span texture/lighting regimes?
5. Do all LightGlue/SuperPoint/LoFTR dependencies and model weights exist in the `asp360_new` environment and local cache?

## Decisions Made

| Decision | Rationale |
|---|---|
| Use isolated plan `.planning/2026-06-01-lro-polar-adaptive-routing-benchmark/` | This is a new experiment and should not overwrite the previous DOM/ORI benchmark plan. |
| Keep preprocessing outputs separate from the source data | The input directory is on external media; a dedicated experiment workspace prevents accidental overwrite of original cubes. |
| Treat adaptive routing vs fixed-method comparison as the central scientific claim | The requested experiment is not only matching execution, but evidence that adaptive routing improves robustness across texture/lighting regimes. |
| Use Nature-style figures only after benchmark reports are stable | Figure generation should use final CSV/JSON summaries rather than ad hoc logs. |
| Migrate final reduced-10m experiment artifacts to the external source data tree | User requested the generated DOMs and all related experiment files under `original_gsd/work/reduced-10m` for the remaining deep-learning experiments. |
| Add a default-off intensity-percentile invalid mask instead of changing gray stretch semantics | The previous `lower_percent`/`upper_percent` controls only display/matcher stretch. A separate valid-intensity mask preserves backward compatibility and makes shadow/highlight exclusion explicit. |
| Use `0.1/99.9` rather than `1.0/99.0` as the default valid-intensity mask | LRO NAC polar scenes can contain real low-light texture; `1.0/99.0` removed 11.2% of first-pair LoFTR matches, so it is better treated as a stricter ablation setting. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| First smoke used mock `ISISDATA` and `cam2map` could not open the LRO DEM shape model | 1 | Re-ran with the conda environment's real `ISISDATA=/home/gengxun/miniconda3/envs/asp360_new/data`; `cam2map` succeeded. |
| ISIS smoke execution updated generated `print.prt` | 1 | Left `print.prt` unstaged and otherwise untouched; do not include it in any commit or publish scope. |
| LightGlue methods failed in smoke because optional Python package `lightglue` is missing from `asp360_new` | 1 | Recorded the dependency failure in `reports/environment_report.json`; did not install new packages into the conda environment. |
| LoFTR smoke failed with `BrokenProcessPool` in the current CPU worker environment | 1 | Recorded as an environment/runtime failure; avoided repeating full LoFTR runs that would only reproduce the same failure. |
| Adaptive routing with low-resolution previews selected a LightGlue route and failed because `lightglue` is unavailable | 1 | Completed the no-preview adaptive cascade benchmark, and recorded the low-resolution preview route failure as an environment constraint. |
| LoFTR raw matches were all removed by invalid-mask filtering | 1 | Diagnosed a mask polarity mismatch: exported task masks are uint8 OpenCV valid masks, while the LoFTR frontend expects bool invalid masks. Fixed adapter-side normalization and added regression coverage. |

## Notes

- Required source directory: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd`
- Required preprocessing: `reduce sscale=10 lscale=10`, then 10 m/pixel DOM generation with `lunar_polarstereographic.map`.
- Preprocessing script: `examples/controlnet_construct/experiments/prepare_lro_polar_reduced_doms.py`.
- Full dry-run output: `work/lro_polar_adaptive_routing_preprocess`.
- Smoke execution output: `work/lro_polar_adaptive_routing_preprocess_smoke_exec`.
- Full preprocessing execution output: `work/lro_polar_adaptive_routing_preprocess` with 22 REDUCED cubes, 22 10 m/pixel DOMs, and 32 selected pair-side rows all marked `all_exist=True`.
- Migrated workspace root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`.
- Methods to compare: adaptive routing, SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, LoFTR.
- Final benchmark output root after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark`.
- Final reports after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/reports`.
- Final figures after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark/reports/figures`.
- Deep-learning supplement output root after migration: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_match_benchmark_deep`.
- Repo rule: do not modify, delete, stage, or restore `.gitignore` or `print.prt` unless explicitly requested.
- Deep-learning manifest runtime defaults: `num_workers=1`, `torch_num_threads=8`.
