# Deep-Match Manifest Parallel Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative tile-level parallel execution and safe task-level rerun cleanup to the deep-learning manifest runner without changing existing classic SIFT parallel behavior.

**Architecture:** Keep `run_deep_match_manifest.py` as the execution owner for exported NumPy tile manifests. Preserve the current serial path for `--num-workers 1`; add a process-pool path for `--num-workers > 1` where each worker initializes and reuses one `DeepMatcherAdapter`. Forward the new manifest-runner knobs only from the official LightGlue experiment script.

**Tech Stack:** Python 3.12/3.10, `argparse`, `concurrent.futures.ProcessPoolExecutor`, `multiprocessing`, NumPy, existing `unittest` suite, Bash experiment wrappers.

---

## File Structure

- Modify `examples/learning_methods/run_deep_match_manifest.py`
  - Add CLI parsing for `--num-workers`, `--torch-num-threads`, and `--force-rerun`.
  - Factor current per-task execution into reusable helpers.
  - Add safe current-task cleanup.
  - Add process-pool execution with worker-local adapter cache.
  - Preserve stable summary ordering.

- Modify `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`
  - Add parser validation tests.
  - Add serial and parallel fake-adapter tests.
  - Add safe rerun cleanup tests.
  - Add parallel failure summary tests.

- Modify `examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh`
  - Add `--deep-match-num-workers`, `--deep-match-torch-num-threads`, and `--force-rerun-deep-match`.
  - Forward those arguments to `run_deep_match_manifest.py` in split mode.

- Do not modify `examples/image_match/tile_matching.py` or classic SIFT parallel code in this plan.

---

### Task 1: Add CLI Argument Tests

**Files:**
- Modify: `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`
- Modify later: `examples/learning_methods/run_deep_match_manifest.py`

- [ ] **Step 1: Extend parser test with accepted options**

In `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`, update `test_build_argument_parser_accepts_manifest_runner_options` to assert the new parsed values:

```python
def test_build_argument_parser_accepts_manifest_runner_options(self):
    parser = build_argument_parser()

    parsed = parser.parse_args(
        [
            "tasks.json",
            "--device",
            "cpu",
            "--summary-output",
            "summary.json",
            "--fail-fast",
            "--skip-existing",
            "--num-workers",
            "3",
            "--torch-num-threads",
            "2",
        ]
    )

    self.assertEqual(parsed.manifest, "tasks.json")
    self.assertEqual(parsed.device, "cpu")
    self.assertEqual(parsed.summary_output, "summary.json")
    self.assertTrue(parsed.fail_fast)
    self.assertTrue(parsed.skip_existing)
    self.assertEqual(parsed.num_workers, 3)
    self.assertEqual(parsed.torch_num_threads, 2)
```

- [ ] **Step 2: Add parser rejection tests**

Add these tests near the parser test:

```python
def test_build_argument_parser_rejects_invalid_worker_counts(self):
    parser = build_argument_parser()

    with self.assertRaises(SystemExit):
        parser.parse_args(["tasks.json", "--num-workers", "0"])

    with self.assertRaises(SystemExit):
        parser.parse_args(["tasks.json", "--torch-num-threads", "0"])


def test_build_argument_parser_rejects_skip_existing_with_force_rerun(self):
    parser = build_argument_parser()

    with self.assertRaises(SystemExit):
        parser.parse_args(["tasks.json", "--skip-existing", "--force-rerun"])
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_build_argument_parser_accepts_manifest_runner_options tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_build_argument_parser_rejects_invalid_worker_counts tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_build_argument_parser_rejects_skip_existing_with_force_rerun -v
```

Expected: failure because the parser has no `num_workers`, `torch_num_threads`, or `force_rerun` fields yet.

- [ ] **Step 4: Add parser helpers and arguments**

In `examples/learning_methods/run_deep_match_manifest.py`, add constants and parser helpers near `SUPPORTED_DEVICES`:

```python
MAX_MANIFEST_WORKERS = 64


def _parse_positive_int(value: str, *, field_name: str, max_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{field_name} must be an integer.") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"{field_name} must be >= 1.")
    if max_value is not None and parsed > max_value:
        raise argparse.ArgumentTypeError(f"{field_name} must be <= {max_value}.")
    return parsed


def _parse_num_workers(value: str) -> int:
    return _parse_positive_int(value, field_name="num_workers", max_value=MAX_MANIFEST_WORKERS)


def _parse_torch_num_threads(value: str) -> int:
    return _parse_positive_int(value, field_name="torch_num_threads")
```

Update `build_argument_parser()`:

```python
    existing_mode = parser.add_mutually_exclusive_group()
    existing_mode.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip tasks whose result NPZ file already exists.",
    )
    existing_mode.add_argument(
        "--force-rerun",
        action="store_true",
        help="Delete each selected task's result/log file before running it.",
    )
    parser.add_argument(
        "--num-workers",
        type=_parse_num_workers,
        default=1,
        help=f"Manifest task worker process count. Default: 1. Must be within [1, {MAX_MANIFEST_WORKERS}].",
    )
    parser.add_argument(
        "--torch-num-threads",
        type=_parse_torch_num_threads,
        default=None,
        help="Optional PyTorch CPU thread count per worker. In parallel mode, defaults to 1.",
    )
```

Remove the old standalone `parser.add_argument("--skip-existing", ...)` block so the mutual exclusion group owns it.

Update `main()` to pass the new values:

```python
    summary = run_manifest(
        args.manifest,
        device=args.device,
        fail_fast=args.fail_fast,
        skip_existing=args.skip_existing,
        force_rerun=args.force_rerun,
        num_workers=args.num_workers,
        torch_num_threads=args.torch_num_threads,
    )
```

- [ ] **Step 5: Run parser tests**

Run the same command from Step 3.

Expected: all three parser tests pass.

- [ ] **Step 6: Commit parser work**

```bash
git add examples/learning_methods/run_deep_match_manifest.py tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py
git commit -m "test: cover deep manifest parallel CLI options"
```

---

### Task 2: Factor Serial Task Execution and Safe Rerun Cleanup

**Files:**
- Modify: `examples/learning_methods/run_deep_match_manifest.py`
- Modify: `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`

- [ ] **Step 1: Add serial summary fields test**

Add a test that calls `run_manifest()` with default serial settings and checks new diagnostics:

```python
def test_run_manifest_reports_serial_execution_fields(self):
    with temporary_directory() as temp_dir:
        manifest = build_deep_match_pair_manifest(
            tasks=[_make_tile_task()],
            left_dom_path="left_dom.cub",
            right_dom_path="right_dom.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
            temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
            requested_device="cpu",
            created_at_utc="2026-05-16T00:00:00Z",
        )
        record = manifest.tasks[0]
        write_deep_match_task_arrays(
            record,
            left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
            right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
            left_mask=np.zeros((8, 8), dtype=bool),
            right_mask=np.zeros((8, 8), dtype=bool),
        )
        manifest_path = write_deep_match_pair_manifest(manifest)

        summary = run_manifest(
            manifest_path,
            device="cpu",
            adapter_factory=FakeDeepMatcherAdapter,
        )

        self.assertEqual(summary["num_workers"], 1)
        self.assertFalse(summary["parallel_execution_used"])
        self.assertEqual(summary["worker_count"], 1)
        self.assertIsNone(summary["torch_num_threads"])
        self.assertFalse(summary["force_rerun"])
        self.assertEqual(summary["succeeded_task_count"], 1)
```

- [ ] **Step 2: Add safe rerun cleanup test**

Add:

```python
def test_run_manifest_force_rerun_deletes_only_task_result_and_log(self):
    with temporary_directory() as temp_dir:
        manifest = build_deep_match_pair_manifest(
            tasks=[_make_tile_task()],
            left_dom_path="left_dom.cub",
            right_dom_path="right_dom.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
            temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
            requested_device="cpu",
            created_at_utc="2026-05-16T00:00:00Z",
        )
        record = manifest.tasks[0]
        write_deep_match_task_arrays(
            record,
            left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
            right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
            left_mask=np.zeros((8, 8), dtype=bool),
            right_mask=np.zeros((8, 8), dtype=bool),
        )
        manifest_path = write_deep_match_pair_manifest(manifest)
        result_path = Path(record.result_path)
        log_path = Path(record.log_path)
        image_path = Path(record.left_image_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text("stale result", encoding="utf-8")
        log_path.write_text("stale log", encoding="utf-8")

        summary = run_manifest(
            manifest_path,
            device="cpu",
            force_rerun=True,
            adapter_factory=FakeDeepMatcherAdapter,
        )

        self.assertEqual(summary["succeeded_task_count"], 1)
        self.assertTrue(result_path.exists())
        self.assertTrue(log_path.exists())
        self.assertTrue(image_path.exists())
        self.assertNotEqual(result_path.read_bytes(), b"stale result")
        self.assertNotEqual(log_path.read_text(encoding="utf-8"), "stale log")
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_run_manifest_reports_serial_execution_fields tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_run_manifest_force_rerun_deletes_only_task_result_and_log -v
```

Expected: failure because `run_manifest()` does not accept `force_rerun`, `num_workers`, or summary diagnostics yet.

- [ ] **Step 4: Add task execution helpers**

In `examples/learning_methods/run_deep_match_manifest.py`, add imports:

```python
import os
```

Add these helpers above `run_manifest()`:

```python
def _effective_torch_num_threads(*, num_workers: int, torch_num_threads: int | None) -> int | None:
    if torch_num_threads is not None:
        return int(torch_num_threads)
    if num_workers > 1:
        return 1
    return None


def _apply_torch_thread_limit(torch_num_threads: int | None) -> None:
    if torch_num_threads is None:
        return
    os.environ["OMP_NUM_THREADS"] = str(torch_num_threads)
    os.environ["MKL_NUM_THREADS"] = str(torch_num_threads)
    try:
        import torch
    except Exception:
        return
    torch.set_num_threads(int(torch_num_threads))


def _safe_unlink(path: str | Path) -> None:
    resolved = Path(path).expanduser().resolve()
    if resolved.exists():
        resolved.unlink()


def _clean_task_outputs(record: DeepMatchTaskRecord) -> None:
    _safe_unlink(record.result_path)
    _safe_unlink(record.log_path)
```

Add a helper for result writing and log payload construction:

```python
def _run_one_task(
    *,
    record: DeepMatchTaskRecord,
    matcher_method: str,
    device: str,
    actual_device: str,
    adapter: Any,
    force_rerun: bool = False,
    torch_num_threads: int | None = None,
) -> dict[str, Any]:
    result_path = Path(record.result_path).expanduser().resolve()
    started_at = _utc_now_iso()
    if force_rerun:
        _clean_task_outputs(record)
    try:
        arrays = read_deep_match_task_arrays(record)
        match_result = adapter.match_pair(
            matcher_method=matcher_method,
            left_image=arrays["left_image"],
            right_image=arrays["right_image"],
            left_mask=arrays["left_mask"],
            right_mask=arrays["right_mask"],
        )
        left_points, right_points, scores = _deep_match_result_to_arrays(match_result)
        raw_match_count = int(min(left_points.shape[0], right_points.shape[0], scores.shape[0]))
        left_points, right_points, scores, invalid_removed_count = _filter_points_by_invalid_masks(
            left_points,
            right_points,
            scores,
            left_mask=arrays["left_mask"],
            right_mask=arrays["right_mask"],
        )
        status = "matched" if len(scores) > 0 else "matched_no_points"
        finished_at = _utc_now_iso()
        write_deep_match_task_result(
            record,
            left_points=left_points,
            right_points=right_points,
            scores=scores,
            status=status,
            metadata={
                "task_index": record.task_index,
                "matcher_method": matcher_method,
                "requested_device": device,
                "actual_device": actual_device,
                "raw_match_count": raw_match_count,
                "invalid_mask_removed_count": invalid_removed_count,
                "worker_pid": os.getpid(),
                "torch_num_threads": torch_num_threads,
                "started_at_utc": started_at,
                "finished_at_utc": finished_at,
            },
        )
        task_summary = {
            "task_index": record.task_index,
            "status": status,
            "match_count": int(len(scores)),
            "raw_match_count": raw_match_count,
            "invalid_mask_removed_count": invalid_removed_count,
            "result_path": str(result_path),
            "log_path": record.log_path,
            "worker_pid": os.getpid(),
            "torch_num_threads": torch_num_threads,
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
        }
        _write_task_log(record, task_summary)
        return task_summary
    except Exception as exc:
        finished_at = _utc_now_iso()
        error_summary = {
            "task_index": record.task_index,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "result_path": str(result_path),
            "log_path": record.log_path,
            "worker_pid": os.getpid(),
            "torch_num_threads": torch_num_threads,
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
        }
        write_deep_match_task_result(
            record,
            left_points=np.empty((0, 2), dtype=np.float32),
            right_points=np.empty((0, 2), dtype=np.float32),
            scores=np.empty((0,), dtype=np.float32),
            status="failed",
            metadata=error_summary,
        )
        _write_task_log(record, error_summary)
        return error_summary
```

- [ ] **Step 5: Update `run_manifest()` signature and serial path**

Change the signature:

```python
def run_manifest(
    manifest_path: str | Path,
    *,
    device: str = "auto",
    fail_fast: bool = False,
    skip_existing: bool = False,
    force_rerun: bool = False,
    num_workers: int = 1,
    torch_num_threads: int | None = None,
    adapter_factory: Callable[..., Any] = DeepMatcherAdapter,
) -> dict[str, Any]:
```

At the start of `run_manifest()` add:

```python
    if num_workers < 1:
        raise ValueError("num_workers must be >= 1.")
    if torch_num_threads is not None and torch_num_threads < 1:
        raise ValueError("torch_num_threads must be >= 1 when provided.")
    if skip_existing and force_rerun:
        raise ValueError("skip_existing and force_rerun cannot both be enabled.")
    effective_torch_num_threads = _effective_torch_num_threads(
        num_workers=num_workers,
        torch_num_threads=torch_num_threads,
    )
```

In the serial path, keep one adapter and replace inline task execution with:

```python
    _apply_torch_thread_limit(effective_torch_num_threads if torch_num_threads is not None else None)
    adapter = adapter_factory(prefer_gpu=prefer_gpu, runtime_config=runtime_config)
    actual_device = str(getattr(adapter, "_device", "cuda" if prefer_gpu else "cpu"))
```

Then inside the task loop:

```python
        if skip_existing and result_path.exists():
            skipped_existing_count += 1
            task_summaries.append(
                {
                    "task_index": record.task_index,
                    "status": "skipped_existing",
                    "result_path": str(result_path),
                }
            )
            continue

        task_summary = _run_one_task(
            record=record,
            matcher_method=manifest.matcher_method,
            device=device,
            actual_device=actual_device,
            adapter=adapter,
            force_rerun=force_rerun,
            torch_num_threads=effective_torch_num_threads,
        )
        task_summaries.append(task_summary)
        if task_summary["status"] == "failed":
            failed_count += 1
            if fail_fast:
                break
        else:
            succeeded_count += 1
```

Add diagnostics to the returned summary:

```python
        "num_workers": int(num_workers),
        "parallel_execution_used": False,
        "worker_count": 1,
        "torch_num_threads": effective_torch_num_threads,
        "force_rerun": bool(force_rerun),
```

- [ ] **Step 6: Run serial and cleanup tests**

Run the command from Step 3.

Expected: both tests pass.

- [ ] **Step 7: Run existing manifest runner module tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
```

Expected: all tests in the module pass.

- [ ] **Step 8: Commit serial refactor and cleanup**

```bash
git add examples/learning_methods/run_deep_match_manifest.py tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py
git commit -m "feat: add safe deep manifest rerun cleanup"
```

---

### Task 3: Add Parallel Manifest Execution

**Files:**
- Modify: `examples/learning_methods/run_deep_match_manifest.py`
- Modify: `tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py`

- [ ] **Step 1: Add fake adapter variant that proves separate tasks ran**

Add this class below `FakeDeepMatcherAdapter`:

```python
class IndexedFakeDeepMatcherAdapter(FakeDeepMatcherAdapter):
    def match_pair(self, *, matcher_method: str, left_image, right_image, left_mask=None, right_mask=None):
        task_value = float(np.asarray(left_image).reshape(-1)[0])
        return SimpleNamespace(
            left_keypoints=(np.array([task_value, 1.0]), np.array([task_value, 2.0])),
            right_keypoints=(np.array([task_value + 1.0, 1.0]), np.array([task_value + 1.0, 2.0])),
            matches=(
                SimpleNamespace(queryIdx=0, trainIdx=0, distance=0.1),
                SimpleNamespace(queryIdx=1, trainIdx=1, distance=0.2),
            ),
        )
```

- [ ] **Step 2: Add parallel deterministic order test**

Add:

```python
def test_run_manifest_parallel_preserves_summary_order(self):
    with temporary_directory() as temp_dir:
        tasks = [_make_tile_task(), replace(_make_tile_task(), paired_window=_make_tile_task().paired_window)]
        manifest = build_deep_match_pair_manifest(
            tasks=tasks,
            left_dom_path="left_dom.cub",
            right_dom_path="right_dom.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
            temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
            requested_device="cpu",
            created_at_utc="2026-05-16T00:00:00Z",
        )
        for offset, record in enumerate(manifest.tasks):
            write_deep_match_task_arrays(
                record,
                left_image=np.full((8, 8), offset + 1, dtype=np.uint8),
                right_image=np.full((8, 8), offset + 2, dtype=np.uint8),
                left_mask=np.zeros((8, 8), dtype=bool),
                right_mask=np.zeros((8, 8), dtype=bool),
            )
        manifest_path = write_deep_match_pair_manifest(manifest)

        summary = run_manifest(
            manifest_path,
            device="cpu",
            num_workers=2,
            adapter_factory=IndexedFakeDeepMatcherAdapter,
        )

        self.assertTrue(summary["parallel_execution_used"])
        self.assertEqual(summary["num_workers"], 2)
        self.assertEqual(summary["worker_count"], 2)
        self.assertEqual(summary["torch_num_threads"], 1)
        self.assertEqual([task["task_index"] for task in summary["tasks"]], [0, 1])
        self.assertEqual(summary["succeeded_task_count"], 2)
        self.assertEqual(summary["failed_task_count"], 0)
```

- [ ] **Step 3: Add parallel failure test**

Add:

```python
class FailingOnSecondFakeAdapter(FakeDeepMatcherAdapter):
    def match_pair(self, *, matcher_method: str, left_image, right_image, left_mask=None, right_mask=None):
        if int(np.asarray(left_image).reshape(-1)[0]) == 2:
            raise RuntimeError("intentional task failure")
        return super().match_pair(
            matcher_method=matcher_method,
            left_image=left_image,
            right_image=right_image,
            left_mask=left_mask,
            right_mask=right_mask,
        )


def test_run_manifest_parallel_records_task_failures(self):
    with temporary_directory() as temp_dir:
        manifest = build_deep_match_pair_manifest(
            tasks=[_make_tile_task(), _make_tile_task()],
            left_dom_path="left_dom.cub",
            right_dom_path="right_dom.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
            temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
            requested_device="cpu",
            created_at_utc="2026-05-16T00:00:00Z",
        )
        for offset, record in enumerate(manifest.tasks):
            write_deep_match_task_arrays(
                record,
                left_image=np.full((8, 8), offset + 1, dtype=np.uint8),
                right_image=np.full((8, 8), offset + 1, dtype=np.uint8),
                left_mask=np.zeros((8, 8), dtype=bool),
                right_mask=np.zeros((8, 8), dtype=bool),
            )
        manifest_path = write_deep_match_pair_manifest(manifest)

        summary = run_manifest(
            manifest_path,
            device="cpu",
            num_workers=2,
            adapter_factory=FailingOnSecondFakeAdapter,
        )

        self.assertEqual(summary["status"], "completed_with_failures")
        self.assertEqual(summary["succeeded_task_count"], 1)
        self.assertEqual(summary["failed_task_count"], 1)
        self.assertEqual(summary["tasks"][1]["status"], "failed")
        self.assertIn("intentional task failure", summary["tasks"][1]["error"])
```

- [ ] **Step 4: Run tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_run_manifest_parallel_preserves_summary_order tests.unitTest.learning_methods_deep_manifest_runner_unit_test.LearningMethodsDeepManifestRunnerUnitTest.test_run_manifest_parallel_records_task_failures -v
```

Expected: failure because parallel execution is not implemented yet.

- [ ] **Step 5: Add process-pool imports and worker state**

In `examples/learning_methods/run_deep_match_manifest.py`, add imports:

```python
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import multiprocessing as mp
```

Add worker globals above `run_manifest()`:

```python
_WORKER_ADAPTER: Any | None = None
_WORKER_ACTUAL_DEVICE: str | None = None
_WORKER_MATCHER_METHOD: str | None = None
_WORKER_DEVICE: str | None = None
_WORKER_TORCH_NUM_THREADS: int | None = None
```

- [ ] **Step 6: Add worker initializer and worker task function**

Add:

```python
def _manifest_process_pool_context() -> mp.context.BaseContext:
    preferred_context = "fork" if os.name == "posix" else "spawn"
    return mp.get_context(preferred_context)


def _initialize_worker(
    *,
    matcher_method: str,
    device: str,
    prefer_gpu: bool,
    runtime_config: Any | None,
    torch_num_threads: int | None,
    adapter_factory: Callable[..., Any],
) -> None:
    global _WORKER_ADAPTER
    global _WORKER_ACTUAL_DEVICE
    global _WORKER_MATCHER_METHOD
    global _WORKER_DEVICE
    global _WORKER_TORCH_NUM_THREADS

    _apply_torch_thread_limit(torch_num_threads)
    _WORKER_ADAPTER = adapter_factory(prefer_gpu=prefer_gpu, runtime_config=runtime_config)
    _WORKER_ACTUAL_DEVICE = str(getattr(_WORKER_ADAPTER, "_device", "cuda" if prefer_gpu else "cpu"))
    _WORKER_MATCHER_METHOD = matcher_method
    _WORKER_DEVICE = device
    _WORKER_TORCH_NUM_THREADS = torch_num_threads


def _run_one_task_worker(record: DeepMatchTaskRecord) -> dict[str, Any]:
    if _WORKER_ADAPTER is None or _WORKER_MATCHER_METHOD is None or _WORKER_DEVICE is None:
        raise RuntimeError("deep manifest worker was not initialized")
    return _run_one_task(
        record=record,
        matcher_method=_WORKER_MATCHER_METHOD,
        device=_WORKER_DEVICE,
        actual_device=str(_WORKER_ACTUAL_DEVICE or "cpu"),
        adapter=_WORKER_ADAPTER,
        force_rerun=False,
        torch_num_threads=_WORKER_TORCH_NUM_THREADS,
    )
```

The worker receives only tasks already selected by the main process. `force_rerun` cleanup is done in the main process before submit so cleanup errors can become deterministic task summaries.

- [ ] **Step 7: Add parallel task selection and cleanup helper**

Add:

```python
def _skipped_existing_summary(record: DeepMatchTaskRecord) -> dict[str, Any]:
    result_path = Path(record.result_path).expanduser().resolve()
    return {
        "task_index": record.task_index,
        "status": "skipped_existing",
        "result_path": str(result_path),
    }


def _cleanup_failed_summary(record: DeepMatchTaskRecord, exc: Exception, *, torch_num_threads: int | None) -> dict[str, Any]:
    now = _utc_now_iso()
    result_path = Path(record.result_path).expanduser().resolve()
    summary = {
        "task_index": record.task_index,
        "status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "result_path": str(result_path),
        "log_path": record.log_path,
        "worker_pid": os.getpid(),
        "torch_num_threads": torch_num_threads,
        "started_at_utc": now,
        "finished_at_utc": now,
    }
    write_deep_match_task_result(
        record,
        left_points=np.empty((0, 2), dtype=np.float32),
        right_points=np.empty((0, 2), dtype=np.float32),
        scores=np.empty((0,), dtype=np.float32),
        status="failed",
        metadata=summary,
    )
    _write_task_log(record, summary)
    return summary


def _prepare_records_for_execution(
    records: list[DeepMatchTaskRecord],
    *,
    skip_existing: bool,
    force_rerun: bool,
    torch_num_threads: int | None,
) -> tuple[list[DeepMatchTaskRecord], list[dict[str, Any]]]:
    selected_records: list[DeepMatchTaskRecord] = []
    precomputed_summaries: list[dict[str, Any]] = []
    for record in records:
        result_path = Path(record.result_path).expanduser().resolve()
        if skip_existing and result_path.exists():
            precomputed_summaries.append(_skipped_existing_summary(record))
            continue
        if force_rerun:
            try:
                _clean_task_outputs(record)
            except Exception as exc:
                precomputed_summaries.append(
                    _cleanup_failed_summary(record, exc, torch_num_threads=torch_num_threads)
                )
                continue
        selected_records.append(record)
    return selected_records, precomputed_summaries
```

- [ ] **Step 8: Add parallel execution helper**

Add:

```python
def _run_parallel_tasks(
    records: list[DeepMatchTaskRecord],
    *,
    matcher_method: str,
    device: str,
    prefer_gpu: bool,
    runtime_config: Any | None,
    num_workers: int,
    torch_num_threads: int | None,
    fail_fast: bool,
    adapter_factory: Callable[..., Any],
) -> list[dict[str, Any]]:
    if not records:
        return []
    worker_count = min(num_workers, len(records))
    summaries: list[dict[str, Any]] = []
    initializer = functools.partial(
        _initialize_worker,
        matcher_method=matcher_method,
        device=device,
        prefer_gpu=prefer_gpu,
        runtime_config=runtime_config,
        torch_num_threads=torch_num_threads,
        adapter_factory=adapter_factory,
    )
    with ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=_manifest_process_pool_context(),
        initializer=initializer,
    ) as executor:
        futures = {executor.submit(_run_one_task_worker, record): record for record in records}
        pending_futures = set(futures)
        stop_after_failure = False
        while pending_futures:
            done_futures, pending_futures = wait(
                pending_futures,
                timeout=0.1,
                return_when=FIRST_COMPLETED,
            )
            for future in done_futures:
                record = futures[future]
                try:
                    task_summary = future.result()
                except Exception as exc:
                    task_summary = _cleanup_failed_summary(record, exc, torch_num_threads=torch_num_threads)
                summaries.append(task_summary)
                if fail_fast and task_summary.get("status") == "failed":
                    stop_after_failure = True
            if stop_after_failure:
                for future in pending_futures:
                    future.cancel()
                break
    return summaries
```

Add `import functools` if it is not already present in the file.

- [ ] **Step 9: Route `run_manifest()` to parallel mode**

After manifest config validation and before old serial loop body, build selected records:

```python
    selected_records, precomputed_summaries = _prepare_records_for_execution(
        list(manifest.tasks),
        skip_existing=skip_existing,
        force_rerun=force_rerun,
        torch_num_threads=effective_torch_num_threads,
    )
```

If `num_workers > 1`, use:

```python
    if num_workers > 1:
        task_summaries = list(precomputed_summaries)
        task_summaries.extend(
            _run_parallel_tasks(
                selected_records,
                matcher_method=manifest.matcher_method,
                device=device,
                prefer_gpu=prefer_gpu,
                runtime_config=runtime_config,
                num_workers=num_workers,
                torch_num_threads=effective_torch_num_threads,
                fail_fast=fail_fast,
                adapter_factory=adapter_factory,
            )
        )
        task_summaries.sort(key=lambda item: int(item["task_index"]))
        succeeded_count = sum(1 for item in task_summaries if item.get("status") not in {"failed", "skipped_existing"})
        failed_count = sum(1 for item in task_summaries if item.get("status") == "failed")
        skipped_existing_count = sum(1 for item in task_summaries if item.get("status") == "skipped_existing")
        actual_device = "cuda" if prefer_gpu else "cpu"
        overall_status = "completed"
        if failed_count and succeeded_count:
            overall_status = "completed_with_failures"
        elif failed_count:
            overall_status = "failed"
        return {
            "status": overall_status,
            "manifest_path": str(Path(manifest_path).expanduser().resolve()),
            "pair_id": manifest.pair_id,
            "matcher_method": manifest.matcher_method,
            "requested_device": device,
            "actual_device": actual_device,
            "task_count": len(manifest.tasks),
            "succeeded_task_count": succeeded_count,
            "failed_task_count": failed_count,
            "skipped_existing_task_count": skipped_existing_count,
            "num_workers": int(num_workers),
            "parallel_execution_used": True,
            "worker_count": min(int(num_workers), len(selected_records)) if selected_records else 0,
            "torch_num_threads": effective_torch_num_threads,
            "force_rerun": bool(force_rerun),
            "started_at_utc": manifest.metadata.get("created_at_utc", manifest.created_at_utc),
            "finished_at_utc": _utc_now_iso(),
            "tasks": task_summaries,
        }
```

For serial mode, reuse `selected_records` instead of `manifest.tasks` and initialize `task_summaries = list(precomputed_summaries)` before the loop. Sort final task summaries before returning.

- [ ] **Step 10: Run parallel tests**

Run the command from Step 4.

Expected: both tests pass.

- [ ] **Step 11: Run full manifest runner tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
```

Expected: all tests in the module pass.

- [ ] **Step 12: Commit parallel runner**

```bash
git add examples/learning_methods/run_deep_match_manifest.py tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py
git commit -m "feat: parallelize deep match manifest tasks"
```

---

### Task 4: Forward Parameters From Official LightGlue Experiment Script

**Files:**
- Modify: `examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py` only if an existing test harness already inspects this script; otherwise validate with shell commands.

- [ ] **Step 1: Add shell validation command expectation**

Run before editing:

```bash
bash -n examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh
```

Expected: pass before edits.

- [ ] **Step 2: Add script variables**

Near existing `deep_match_device="auto"` add:

```bash
deep_match_num_workers=1
deep_match_torch_num_threads=""
force_rerun_deep_match=0
```

- [ ] **Step 3: Extend usage text**

Add these options under the existing `--device MODE` help:

```bash
  --deep-match-num-workers N
                        Worker process count for run_deep_match_manifest.py in split mode.
                        Default: 1.
  --deep-match-torch-num-threads N
                        PyTorch CPU thread count per deep-match worker. When omitted,
                        run_deep_match_manifest.py chooses its default.
  --force-rerun-deep-match
                        Rerun deep-match tasks by deleting only each task result/log
                        before manifest execution. Does not clean export/import outputs.
```

- [ ] **Step 4: Parse new options**

Add cases to the `while [[ $# -gt 0 ]]` block:

```bash
    --deep-match-num-workers)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-num-workers"
      deep_match_num_workers=$2
      shift 2
      ;;
    --deep-match-torch-num-threads)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-torch-num-threads"
      deep_match_torch_num_threads=$2
      shift 2
      ;;
    --force-rerun-deep-match)
      force_rerun_deep_match=1
      shift
      ;;
```

- [ ] **Step 5: Validate simple numeric values**

After the `case "$deep_match_device"` validation block, add:

```bash
[[ "$deep_match_num_workers" =~ ^[1-9][0-9]*$ ]] || die "--deep-match-num-workers must be a positive integer"
if [[ -n "$deep_match_torch_num_threads" ]]; then
  [[ "$deep_match_torch_num_threads" =~ ^[1-9][0-9]*$ ]] || die "--deep-match-torch-num-threads must be a positive integer"
fi
```

- [ ] **Step 6: Forward arguments to manifest runner**

Inside `run_deep_match_manifests()`, replace the direct `python ... run_deep_match_manifest.py` command with an array:

```bash
      manifest_command=(
        python "$repo_root/examples/learning_methods/run_deep_match_manifest.py"
        "$manifest_path"
        --device "$deep_match_device"
        --summary-output "$summary_path"
        --num-workers "$deep_match_num_workers"
      )
      if [[ -n "$deep_match_torch_num_threads" ]]; then
        manifest_command+=(--torch-num-threads "$deep_match_torch_num_threads")
      fi
      if [[ "$force_rerun_deep_match" == "1" ]]; then
        manifest_command+=(--force-rerun)
      else
        manifest_command+=(--skip-existing)
      fi
      "${manifest_command[@]}"
```

Keep this inside the subshell after `conda activate` and `PYTHONPATH` setup.

- [ ] **Step 7: Add manifest command logging**

Before executing `manifest_command`, add:

```bash
      printf 'Manifest command:'
      printf ' %q' "${manifest_command[@]}"
      printf '\n'
```

- [ ] **Step 8: Run shell validation**

Run:

```bash
bash -n examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh
```

Expected: exit code 0.

- [ ] **Step 9: Run validate-only**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh --validate-only --deep-match-num-workers 2 --deep-match-torch-num-threads 1
```

Expected: parameter validation passes for `superpoint_lightglue`, `disk_lightglue`, and `sift_lightglue`. The script should not run manifest execution in validate-only mode.

- [ ] **Step 10: Commit script forwarding**

```bash
git add examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh
git commit -m "feat: forward deep manifest worker options"
```

---

### Task 5: Final Verification and Real-Data Smoke

**Files:**
- No source edits expected unless verification exposes a bug.

- [ ] **Step 1: Run focused unit tests**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.learning_methods_deep_manifest_runner_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 2: Run related deep adapter regression tests**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_deep_adapter_unit_test tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_deep_dependency_error_is_pickle_round_trippable -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Run shell validation and validate-only script check**

```bash
bash -n examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh --validate-only --deep-match-num-workers 2 --deep-match-torch-num-threads 1
```

Expected: shell syntax passes and all selected labels print `Parameter validation passed`.

- [ ] **Step 4: Run a narrow real-data split-mode smoke**

Use a fresh output root so `--skip-existing` cannot hide failures:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh \
  --only superpoint_lightglue \
  --deep-match-num-workers 2 \
  --deep-match-torch-num-threads 1 \
  --output-root /tmp/pipe_test2_official_lightglue_parallel_smoke
```

Expected:

- export step exits 0,
- manifest execution exits 0,
- import step exits 0,
- `/tmp/pipe_test2_official_lightglue_parallel_smoke/superpoint_lightglue/reports/controlnet_batch_summary.json` exists,
- manifest summaries report `failed_task_count: 0`.

- [ ] **Step 5: Inspect manifest summary diagnostics**

Run:

```bash
jq -s '{manifests:length,total_tasks:([.[].task_count]|add),failed:([.[].failed_task_count]|add),workers:([.[].num_workers]|unique),parallel:([.[].parallel_execution_used]|unique),torch_threads:([.[].torch_num_threads]|unique)}' /tmp/pipe_test2_official_lightglue_parallel_smoke/superpoint_lightglue/deep_match_workspaces/*/manifest_run_summary.json
```

Expected:

```json
{
  "manifests": 6,
  "total_tasks": 219,
  "failed": 0,
  "workers": [2],
  "parallel": [true],
  "torch_threads": [1]
}
```

- [ ] **Step 6: Run diff checks**

```bash
git diff --check
git status --short --branch
```

Expected:

- `git diff --check` exits 0.
- Status shows only intended source/test/script changes plus pre-existing unrelated `.gitignore` and `print.prt` if they are still present.

- [ ] **Step 7: Commit any verification fix**

If verification required a code or test fix:

```bash
git add examples/learning_methods/run_deep_match_manifest.py tests/unitTest/learning_methods_deep_manifest_runner_unit_test.py examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh
git commit -m "fix: stabilize deep manifest parallel execution"
```

If no fixes were needed, do not create an empty commit.

---

## Spec Coverage Review

- Manifest-level tile parallelism: Tasks 1-3.
- Default serial behavior: Tasks 1-2.
- One adapter per worker process: Task 3.
- PyTorch thread limiting: Tasks 1 and 3.
- Safe rerun cleanup: Task 2.
- Stable summary ordering and diagnostics: Tasks 2-3.
- Official LightGlue experiment forwarding: Task 4.
- Classic SIFT untouched: File Structure and no tasks against `tile_matching.py`.
- Validation and real-data smoke: Task 5.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-25-deep-match-manifest-parallel.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
