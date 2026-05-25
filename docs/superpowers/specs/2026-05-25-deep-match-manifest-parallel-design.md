# Deep-Match Manifest Parallel Execution Design

Date: 2026-05-25
Status: Draft for user review

## Context

ControlNet deep matching currently has two execution shapes:

- Classic SIFT/FLANN and SIFT/BF tile matching runs through `examples/image_match/image_match.py` and already has CPU process-pool tile parallelism via `--use-parallel-cpu` and `--num-worker-parallel-cpu`.
- Deep-learning split mode exports tile manifests in the `asp360_new` environment, then runs those manifests with `examples/learning_methods/run_deep_match_manifest.py` in the `deep-learning` environment, then imports the results back into the ControlNet pipeline.

The slow path observed in `pipe_test2` is the deep-learning manifest execution step, especially `disk+lightglue` on CPU. The reference note in `doc_development_process/20260525-parallel-plan.md` recommends a conservative first version: add manifest-internal tile parallelism to `run_deep_match_manifest.py`, default it to serial behavior, and limit PyTorch CPU threads per worker to avoid CPU oversubscription.

## Goals

- Add tile-level parallel execution for deep-learning manifest tasks.
- Keep `--num-workers 1` as the default and preserve current serial behavior.
- Reuse one `DeepMatcherAdapter` per worker process to avoid reloading models for every tile.
- Control per-worker PyTorch CPU thread usage when manifest parallelism is enabled.
- Keep output summaries deterministic and compatible with existing import logic.
- Add an explicit safe rerun mode that only cleans current task result/log files.
- Leave the existing classic SIFT tile parallelism untouched.

## Non-Goals

- Do not build a shared executor abstraction for classic SIFT and deep-learning paths in v1.
- Do not parallelize at pair, manifest, profile, or pipeline level in v1.
- Do not change `examples/image_match/tile_matching.py` classic SIFT parallel behavior.
- Do not introduce default deletion of historical results or workspaces.
- Do not make CUDA multi-process execution the default recommendation.

## Proposed Scope

### Manifest Runner

`examples/learning_methods/run_deep_match_manifest.py` gets these options:

- `--num-workers N`
  - Default: `1`.
  - `1` uses the existing serial path.
  - `N > 1` enables process-pool task execution inside one manifest.
  - Validate `N >= 1`; use a conservative documented upper bound such as `64`.

- `--torch-num-threads N`
  - Optional explicit per-worker PyTorch CPU thread count.
  - In parallel mode, default effective value is `1`.
  - In serial mode, do not force a PyTorch thread setting unless explicitly provided.
  - Worker processes call `torch.set_num_threads(N)` when torch is importable.
  - Worker-local environment may set `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to the same value before model work begins.

- `--force-rerun`
  - Explicitly reruns selected manifest tasks.
  - Mutually exclusive with `--skip-existing`; argument parsing should reject using both.
  - For each task, delete only that task's `result_path` and `log_path` before execution.
  - Do not delete `images/`, `tasks.json`, `manifest_run_summary.json`, profile work dirs, ControlNet keys, or import outputs.
  - If deleting the current task result/log fails, mark that task failed with error metadata rather than proceeding with uncertain state.

### Experiment Script

`examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh` forwards deep manifest worker settings in split mode:

- `--deep-match-num-workers N`
  - Default: `1`.
  - Passed to `run_deep_match_manifest.py --num-workers N`.

- `--deep-match-torch-num-threads N`
  - Optional.
  - Passed to `run_deep_match_manifest.py --torch-num-threads N`.

- `--force-rerun-deep-match`
  - Passed to `run_deep_match_manifest.py --force-rerun`.
  - Should not imply re-export or re-import cleanup.

The SIFT/FLANN profile script does not need deep-learning worker parameters because classic SIFT already uses `ImageMatch.num_worker_parallel_cpu` and `--num-worker-parallel-cpu`.

## Execution Model

### Serial Mode

When `--num-workers 1`:

1. Read `tasks.json`.
2. Rehydrate runtime config.
3. Validate matcher/device configuration.
4. Run dependency preflight once.
5. Create one `DeepMatcherAdapter`.
6. Execute tasks in manifest order.
7. Write per-task NPZ/log files and final summary.

This path should stay close to the current implementation so existing tests remain meaningful.

### Parallel Mode

When `--num-workers > 1`:

1. The main process reads the manifest and resolves runtime config.
2. The main process validates matcher/device config and runs dependency preflight once before creating workers.
3. The main process builds task work items in manifest order.
4. `--skip-existing` removes already completed tasks from the submitted work list.
5. `--force-rerun` removes only the current task result/log before submitting that task.
6. A `ProcessPoolExecutor` runs task work items.
7. Each worker initializes worker-local state on first task:
   - effective device preference,
   - runtime config,
   - torch thread limits,
   - one cached `DeepMatcherAdapter`.
8. Each worker processes one task at a time:
   - read task arrays,
   - call `adapter.match_pair`,
   - convert match result arrays,
   - apply invalid-mask filtering,
   - write the task NPZ,
   - write that task log JSON,
   - return task summary to the main process.
9. The main process collects summaries and orders them by manifest task order, not completion order.
10. The main process writes the final summary.

## Failure Semantics

- Default behavior remains best-effort: continue after task failures and report `completed_with_failures` if at least one task succeeds and at least one fails.
- Failed tasks write empty result NPZ files with `status="failed"` and error metadata, matching current import expectations.
- `--fail-fast` in parallel mode means:
  - after the first failed future is observed, do not submit more work,
  - cancel futures that have not started when possible,
  - allow already running tasks to finish,
  - include completed, failed, cancelled, and skipped tasks in the summary.
- Worker exceptions must be converted into JSON-safe summaries in the main process if the worker could not write its own task log.

## Summary and Logging

The final manifest summary keeps all existing top-level and per-task fields and adds execution diagnostics:

- `num_workers`
- `parallel_execution_used`
- `worker_count`
- `torch_num_threads`
- `force_rerun`

Task summaries keep existing fields:

- `task_index`
- `status`
- `match_count`
- `raw_match_count`
- `invalid_mask_removed_count`
- `result_path`
- `log_path`

Task logs may add:

- `worker_pid`
- `torch_num_threads`
- `started_at_utc`
- `finished_at_utc`

Each task writes only its own log file. The final manifest summary is written only by the main process.

## Resource Control

Parallel deep matching can be slower than serial execution if PyTorch threads are not limited. The expected safe starting points are:

- CPU DISK/LightGlue: `--num-workers 2 --torch-num-threads 1`
- CPU SuperPoint/LightGlue: `--num-workers 2` or `4`, with `--torch-num-threads 1`
- CPU official SIFT/LightGlue: start with `2`, then test `4`

CUDA execution remains supported through `--device cuda`, but v1 should document it as cautious:

- use low worker counts,
- expect higher memory pressure,
- prefer `--num-workers 1` first,
- do not assume multi-process CUDA improves throughput.

## Compatibility With Classic SIFT

Classic SIFT matching already has process-pool tile parallelism in `examples/image_match/tile_matching.py`. It is controlled through:

- `--use-parallel-cpu`
- `--no-parallel-cpu`
- `--num-worker-parallel-cpu`

The new deep-learning manifest parameters are intentionally separate:

- `--num-workers`
- `--torch-num-threads`
- `--force-rerun`

This keeps existing classic SIFT behavior stable and avoids conflating two different execution layers:

- classic SIFT parallelism runs inside `image_match.py` while reading cube windows directly,
- deep-learning parallelism runs after export, inside `run_deep_match_manifest.py`, using already exported NumPy tile arrays.

## Testing Plan

### Unit Tests

Add focused tests in `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`:

- parser accepts `--num-workers`, `--torch-num-threads`, and `--force-rerun`.
- parser rejects `--skip-existing` together with `--force-rerun`.
- `num_workers=1` preserves existing serial behavior.
- `num_workers=2` runs multiple fake tasks and produces deterministic task summary order.
- parallel mode writes expected NPZ and log files for each fake task.
- parallel failure handling writes failed result metadata and returns `completed_with_failures`.
- `--force-rerun` deletes only the current task's result/log path and leaves images and manifest files untouched.
- effective parallel summary fields are present and stable.

### Script Validation

For `run_pipe_test2_official_lightglue_profiles.sh`:

- `bash -n examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh`
- `--validate-only` still works without running deep manifest execution.
- command construction includes `--num-workers`, optional `--torch-num-threads`, and optional `--force-rerun` when the matching script options are set.

### Real Data Validation

Use `pipe_test2` after unit coverage passes:

1. Run `superpoint_lightglue` with `--deep-match-num-workers 2`.
2. Run `disk_lightglue` with `--deep-match-num-workers 2`.
3. Compare against serial summaries:
   - same manifest count,
   - same task count,
   - zero unexpected failures,
   - compatible match counts for deterministic model/runtime conditions.
4. If CPU remains stable, test worker count `4`.

## Rollout Plan

1. Write and review this design spec.
2. Implement manifest-runner parallel execution and safe rerun cleanup.
3. Add unit tests with fake adapters.
4. Add script argument forwarding in the official LightGlue profile experiment script.
5. Validate with focused unit tests and shell validation.
6. Run `pipe_test2` on a narrow subset before broader DISK/SIFT comparisons.
7. Defer any unified executor or pipeline-level parallelism until v1 behavior is proven.

## Open Decisions Resolved

- v1 uses the conservative manifest-runner approach.
- v1 includes safe task-level stale result cleanup through `--force-rerun`.
- v1 defaults to serial execution.
- v1 limits PyTorch worker threads to `1` when manifest parallelism is enabled and no explicit thread count is provided.
- v1 does not modify classic SIFT parallel internals.
