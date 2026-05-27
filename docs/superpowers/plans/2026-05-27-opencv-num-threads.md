# OpenCV Thread Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit `--opencv-num-threads` image-match control so users can cap OpenCV's internal pthread parallelism while preserving current default behavior when the option/config value is omitted.

**Architecture:** Keep OpenCV thread policy owned by `examples/image_match/image_match.py`, pass the resolved value through tile-task payloads in `examples/image_match/tile_matching.py`, and apply it both in the main process and in process-pool workers. Bash wrappers and JSON config only forward a positive integer when explicitly configured. GPU SIFT fallback uses the same process-level OpenCV setting; do not add a separate GPU-specific knob.

**Tech Stack:** Python 3.12, OpenCV/cv2 4.13, `unittest`, Bash wrappers, JSON config, existing `asp360_new` conda environment.

---

## File Structure

- Modify `examples/image_match/image_match.py`: add parser/config/API parameter, validation helpers, OpenCV thread application helper, summary/metadata diagnostics, and forwarding into tile task construction.
- Modify `examples/image_match/tile_matching.py`: add `TileMatchTask.opencv_num_threads`, payload round-trip support, and worker-side application before processing a shard.
- Modify `examples/controlnet_construct/run_pipeline_example.sh`: parse/log/config-resolve/forward `--opencv-num-threads` to image matching.
- Modify `examples/controlnet_construct/run_image_match_batch_example.sh`: parse/log/config-resolve/forward `--opencv-num-threads` for batch image matching.
- Modify `examples/controlnet_construct/controlnet_config.example.json`: add a conservative example `ImageMatch.opencv_num_threads` value.
- Modify `examples/controlnet_construct/usage.md`: document the new option, its relationship with `--num-worker-parallel-cpu`, and recommended SIFT+FLANN settings.
- Modify `tests/unitTest/controlnet_construct_matching_unit_test.py`: parser/config/helper/metadata regression coverage.
- Modify `tests/unitTest/image_match_deep_manifest_unit_test.py`: tile-task payload round-trip regression coverage.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`: wrapper forwarding/config fallback regression coverage.

## Cross-Cutting Constraints

- Public CLI spelling must be kebab-case: `--opencv-num-threads`.
- Internal Python names stay snake_case: `opencv_num_threads`.
- Omitted/`None` means **do not call** `cv2.setNumThreads`; this preserves OpenCV defaults.
- Positive integer means call `cv2.setNumThreads(N)` once in the main process before matching and once per process-pool worker before processing its batch.
- Reject `0`, negative values, and non-integers at CLI/config/API boundaries.
- Do not implement `auto` mode in this change.
- Do not reopen cubes per tile while adding this feature; preserve current batched worker cube reuse.
- When editing runnable example Python/Bash files, preserve existing `Created:` metadata and append one concise `Updated: 2026-05-27  Geng Xun ...` line only for files meaningfully changed.
- Avoid committing unrelated workspace noise such as `.claude/`, `print.prt`, `resume`, or unrelated local artifacts.

## Task 1: Add CLI And Config Validation For `opencv_num_threads`

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/image_match/image_match.py`

- [ ] **Step 1: Add parser/config/default tests first**

In `ControlNetConstructMatchingUnitTest`, add focused tests near the existing parser/config default tests:

```python
    def test_build_argument_parser_accepts_opencv_num_threads(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        explicit_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--opencv-num-threads",
                "1",
            ]
        )

        self.assertIsNone(default_args.opencv_num_threads)
        self.assertEqual(explicit_args.opencv_num_threads, 1)

    def test_build_argument_parser_rejects_invalid_opencv_num_threads(self):
        parser = build_argument_parser()

        for value in ("0", "-1", "1.5", "auto"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "left.cub",
                        "right.cub",
                        "left.key",
                        "right.key",
                        "--opencv-num-threads",
                        value,
                    ]
                )

    def test_print_image_match_config_default_reads_opencv_num_threads(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"opencvNumThreads": 2}}),
                encoding="utf-8",
            )

            self.assertEqual(image_match.print_image_match_config_default(config_path, "opencv_num_threads"), "2")

    def test_image_match_config_rejects_invalid_opencv_num_threads(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"opencv_num_threads": 0}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "opencv_num_threads must be >= 1"):
                image_match.load_image_match_defaults_from_config(config_path)
```

- [ ] **Step 2: Run the new tests and verify failure**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_rejects_invalid_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_image_match_config_rejects_invalid_opencv_num_threads -v
```

Expected: FAIL because parser/config support does not exist yet.

- [ ] **Step 3: Implement validation helpers in `image_match.py`**

Near `_validate_num_worker_parallel_cpu`, add:

```python
def _validate_opencv_num_threads(value: int | None) -> int | None:
    if value is None:
        return None
    resolved_value = int(value)
    if resolved_value < 1:
        raise ValueError("opencv_num_threads must be >= 1.")
    return resolved_value


def _parse_opencv_num_threads(value: str) -> int:
    try:
        return _validate_opencv_num_threads(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
```

If `int(value)` raises for `"auto"`/`"1.5"`, convert that failure to `argparse.ArgumentTypeError("opencv_num_threads must be an integer >= 1.")` so CLI failures are clean.

- [ ] **Step 4: Add config field spec**

In `load_image_match_defaults_from_config(...)`, add a field spec alongside execution controls:

```python
        _field_spec(
            "opencv_num_threads",
            ("opencv_num_threads", "opencvNumThreads", "OpenCVNumThreads"),
            lambda value: _validate_opencv_num_threads(int(value)),
        ),
```

Use the local field-spec helper name/pattern exactly as the file currently uses it.

- [ ] **Step 5: Add parser argument**

In `build_argument_parser()`, add:

```python
    parser.add_argument(
        "--opencv-num-threads",
        type=_parse_opencv_num_threads,
        default=config_defaults.get("opencv_num_threads"),
        help=(
            "Optional OpenCV internal thread limit for CPU SIFT/FLANN work. "
            "Omit to keep OpenCV's default thread policy; use 1 with multiple CPU workers to avoid oversubscription."
        ),
    )
```

Place it near `--num-worker-parallel-cpu` so users see both CPU controls together.

- [ ] **Step 6: Run focused parser/config tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_rejects_invalid_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_opencv_num_threads tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_image_match_config_rejects_invalid_opencv_num_threads -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: parse OpenCV thread limit for image matching"
```

## Task 2: Propagate `opencv_num_threads` Through Tile Task Payloads

**Files:**
- Modify: `tests/unitTest/image_match_deep_manifest_unit_test.py`
- Modify: `examples/image_match/tile_matching.py`
- Modify: `examples/image_match/image_match.py`

- [ ] **Step 1: Extend tile payload round-trip test**

In `_make_tile_task(...)`, add an optional parameter and pass it into `TileMatchTask`:

```python
    opencv_num_threads: int | None = 2,
```

```python
        opencv_num_threads=opencv_num_threads,
```

In `test_tile_match_task_payload_round_trip_preserves_gpu_and_window_metadata`, add:

```python
        self.assertEqual(payload["opencv_num_threads"], 2)
        self.assertEqual(restored.opencv_num_threads, 2)
```

Add backward-compatible payload test:

```python
    def test_tile_match_task_payload_defaults_missing_opencv_num_threads_to_none(self):
        task = _make_tile_task(opencv_num_threads=None)
        payload = tile_match_task_to_payload(task)
        payload.pop("opencv_num_threads")

        restored = tile_match_task_from_payload(payload)

        self.assertIsNone(restored.opencv_num_threads)
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python -m unittest tests.unitTest.image_match_deep_manifest_unit_test.ImageMatchDeepManifestUnitTest.test_tile_match_task_payload_round_trip_preserves_gpu_and_window_metadata tests.unitTest.image_match_deep_manifest_unit_test.ImageMatchDeepManifestUnitTest.test_tile_match_task_payload_defaults_missing_opencv_num_threads_to_none -v
```

Expected: FAIL because `TileMatchTask` and payload helpers do not yet support the field.

- [ ] **Step 3: Update `TileMatchTask` dataclass**

In `examples/image_match/tile_matching.py`, add:

```python
    opencv_num_threads: int | None = None
```

Place it near execution-related fields such as `use_gpu`/`gpu_batch_size`.

- [ ] **Step 4: Update payload serialization/deserialization**

In `tile_match_task_to_payload(...)`, add:

```python
        "opencv_num_threads": task.opencv_num_threads,
```

In `tile_match_task_from_payload(...)`, add:

```python
        opencv_num_threads=payload.get("opencv_num_threads"),
```

If the existing deserializer casts ints for other fields, cast only when not `None`:

```python
        opencv_num_threads=(None if payload.get("opencv_num_threads") is None else int(payload["opencv_num_threads"])),
```

- [ ] **Step 5: Forward from `_build_tile_match_tasks(...)`**

In `image_match.py` and/or `tile_matching.py` depending on the actual helper location, add an `opencv_num_threads: int | None = None` parameter to `_build_tile_match_tasks(...)` and set each task's field.

At the call site inside `match_dom_pair(...)`, pass the validated value:

```python
opencv_num_threads=resolved_opencv_num_threads,
```

- [ ] **Step 6: Run focused payload tests**

```bash
python -m unittest tests.unitTest.image_match_deep_manifest_unit_test.ImageMatchDeepManifestUnitTest.test_tile_match_task_payload_round_trip_preserves_gpu_and_window_metadata tests.unitTest.image_match_deep_manifest_unit_test.ImageMatchDeepManifestUnitTest.test_tile_match_task_payload_defaults_missing_opencv_num_threads_to_none -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add examples/image_match/tile_matching.py examples/image_match/image_match.py tests/unitTest/image_match_deep_manifest_unit_test.py
git commit -m "feat: carry OpenCV thread limit in tile tasks"
```

## Task 3: Apply OpenCV Thread Setting In Main Process And Report Diagnostics

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/image_match/image_match.py`

- [ ] **Step 1: Add direct helper tests with monkeypatched cv2**

Add tests near other helper tests:

```python
    def test_apply_opencv_thread_config_skips_when_unset(self):
        calls = []
        original_set = image_match.cv2.setNumThreads
        original_get = image_match.cv2.getNumThreads
        original_optimized = image_match.cv2.useOptimized
        image_match.cv2.setNumThreads = lambda value: calls.append(value)
        image_match.cv2.getNumThreads = lambda: 8
        image_match.cv2.useOptimized = lambda: True
        try:
            summary = image_match._apply_opencv_thread_config(None)
        finally:
            image_match.cv2.setNumThreads = original_set
            image_match.cv2.getNumThreads = original_get
            image_match.cv2.useOptimized = original_optimized

        self.assertEqual(calls, [])
        self.assertFalse(summary["opencv_num_threads_configured"])
        self.assertIsNone(summary["opencv_num_threads_requested"])
        self.assertEqual(summary["opencv_num_threads_effective"], 8)
        self.assertTrue(summary["opencv_use_optimized"])

    def test_apply_opencv_thread_config_sets_positive_value(self):
        calls = []
        original_set = image_match.cv2.setNumThreads
        original_get = image_match.cv2.getNumThreads
        original_optimized = image_match.cv2.useOptimized
        image_match.cv2.setNumThreads = lambda value: calls.append(value)
        image_match.cv2.getNumThreads = lambda: calls[-1]
        image_match.cv2.useOptimized = lambda: True
        try:
            summary = image_match._apply_opencv_thread_config(2)
        finally:
            image_match.cv2.setNumThreads = original_set
            image_match.cv2.getNumThreads = original_get
            image_match.cv2.useOptimized = original_optimized

        self.assertEqual(calls, [2])
        self.assertTrue(summary["opencv_num_threads_configured"])
        self.assertEqual(summary["opencv_num_threads_requested"], 2)
        self.assertEqual(summary["opencv_num_threads_effective"], 2)
```

- [ ] **Step 2: Run helper tests and verify failure**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_apply_opencv_thread_config_skips_when_unset tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_apply_opencv_thread_config_sets_positive_value -v
```

Expected: FAIL because helper does not exist.

- [ ] **Step 3: Implement `_apply_opencv_thread_config(...)`**

In `image_match.py`, add near validation/helpers:

```python
def _apply_opencv_thread_config(opencv_num_threads: int | None) -> dict[str, object]:
    requested = _validate_opencv_num_threads(opencv_num_threads)
    configured = requested is not None
    if configured:
        cv2.setNumThreads(requested)
    return {
        "opencv_num_threads_configured": configured,
        "opencv_num_threads_requested": requested,
        "opencv_num_threads_effective": int(cv2.getNumThreads()),
        "opencv_use_optimized": bool(cv2.useOptimized()),
    }
```

- [ ] **Step 4: Wire API parameters and summary**

In `match_dom_pair(...)` signature, add:

```python
    opencv_num_threads: int | None = None,
```

After existing validation of CPU worker limits, add:

```python
        resolved_opencv_num_threads = _validate_opencv_num_threads(opencv_num_threads)
        opencv_thread_summary = _apply_opencv_thread_config(resolved_opencv_num_threads)
```

Add the returned keys into the main `summary` dictionary:

```python
            **opencv_thread_summary,
```

In `match_dom_pair_to_key_files(...)`, add the same keyword argument and forward it to `match_dom_pair(...)`.

In `main(...)`, forward:

```python
        opencv_num_threads=args.opencv_num_threads,
```

- [ ] **Step 5: Add metadata-sidecar assertion**

If a lightweight existing metadata-output test can be extended without expensive cube work, assert the written metadata contains:

```python
        self.assertEqual(metadata["opencv_num_threads_requested"], 1)
        self.assertEqual(metadata["opencv_num_threads_configured"], True)
```

If all suitable metadata tests are integration-heavy, add this assertion in a later focused integration pass instead of expanding expensive tests here.

- [ ] **Step 6: Run focused helper and parser tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_apply_opencv_thread_config_skips_when_unset tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_apply_opencv_thread_config_sets_positive_value tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_build_argument_parser_accepts_opencv_num_threads -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: apply OpenCV thread limit in image matching"
```

## Task 4: Apply OpenCV Thread Setting In Process-Pool Workers

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/image_match/tile_matching.py`

- [ ] **Step 1: Add worker-side regression test**

Add a focused test that directly calls `_match_tile_task_batch_worker(...)` without spawning a process. Mock cube opening and tile matching to keep it fast:

```python
    def test_parallel_tile_batch_worker_applies_opencv_thread_config_once(self):
        task = tile_matching.TileMatchTask(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            band=1,
            paired_window=tile_matching.PairedTileWindow(
                local_window=tile_matching.TileWindow(0, 0, 16, 16),
                left_window=tile_matching.TileWindow(0, 0, 16, 16),
                right_window=tile_matching.TileWindow(0, 0, 16, 16),
            ),
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=1,
            valid_pixel_percent_threshold=0.0,
            invalid_pixel_radius=0,
            ratio_test=0.75,
            matcher_method="flann",
            max_features=64,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            image_space="dom",
            use_gpu=False,
            gpu_batch_size=1,
            opencv_num_threads=1,
        )
        payload = tile_matching.tile_match_task_to_payload(task)
        calls = []

        class FakeCube:
            def open(self, path, mode):
                self.path = path
            def close(self):
                pass

        original_ip = tile_matching.ip
        original_set = tile_matching.cv2.setNumThreads
        original_match = tile_matching._match_tile_task_with_open_cubes
        tile_matching.ip = SimpleNamespace(Cube=FakeCube)
        tile_matching.cv2.setNumThreads = lambda value: calls.append(value)
        tile_matching._match_tile_task_with_open_cubes = lambda *args, **kwargs: []
        try:
            result = tile_matching._match_tile_task_batch_worker([payload])
        finally:
            tile_matching.ip = original_ip
            tile_matching.cv2.setNumThreads = original_set
            tile_matching._match_tile_task_with_open_cubes = original_match

        self.assertEqual(calls, [1])
        self.assertEqual(result, [[]])
```

Adjust names if the actual worker helper or matching helper has a slightly different name.

- [ ] **Step 2: Run worker test and verify failure**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_parallel_tile_batch_worker_applies_opencv_thread_config_once -v
```

Expected: FAIL because worker does not set OpenCV threads.

- [ ] **Step 3: Implement worker-side application**

In `examples/image_match/tile_matching.py`, ensure `cv2` is imported if not already imported. In `_match_tile_task_batch_worker(...)`, after payloads are converted back to tasks and before opening cubes / processing the shard:

```python
    opencv_num_threads = tasks[0].opencv_num_threads if tasks else None
    if opencv_num_threads is not None:
        cv2.setNumThreads(int(opencv_num_threads))
```

Keep this outside the per-task loop so the call happens once per worker shard.

- [ ] **Step 4: Validate all payloads in a worker shard agree**

If tasks can be mixed, add a guard:

```python
    if any(task.opencv_num_threads != opencv_num_threads for task in tasks):
        raise ValueError("All tile tasks in one worker batch must use the same opencv_num_threads value.")
```

This should never trigger with current construction, but it prevents confusing diagnostics if future callers mix payloads.

- [ ] **Step 5: Run worker and payload tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_parallel_tile_batch_worker_applies_opencv_thread_config_once tests.unitTest.image_match_deep_manifest_unit_test.ImageMatchDeepManifestUnitTest.test_tile_match_task_payload_round_trip_preserves_gpu_and_window_metadata -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add examples/image_match/tile_matching.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: apply OpenCV thread limit in tile workers"
```

## Task 5: Synchronize Bash Wrappers And Example Config

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Modify: `examples/controlnet_construct/controlnet_config.example.json`

- [ ] **Step 1: Add wrapper tests first**

In `ControlNetConstructPipelineUnitTest`, add tests matching existing subprocess-wrapper style. Cover these behaviors:

```python
    def test_run_pipeline_example_help_mentions_opencv_num_threads(self):
        result = subprocess.run(
            ["bash", str(RUN_PIPELINE_EXAMPLE_PATH), "--help"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--opencv-num-threads", result.stdout)
        self.assertIn("OpenCV", result.stdout)
```

Add a validate-only/config fallback test if the existing test utilities already build minimal configs. The assertion should inspect stdout/stderr or generated command text for:

```text
--opencv-num-threads 1
```

For `run_image_match_batch_example.sh`, add a corresponding `--help` test and, if existing tests mock command execution, a forwarding test.

- [ ] **Step 2: Run wrapper tests and verify failure**

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_help_mentions_opencv_num_threads -v
```

Expected: FAIL because wrapper help does not mention the option yet.

- [ ] **Step 3: Update `run_pipeline_example.sh`**

Add a variable near other image-match execution controls:

```bash
opencv_num_threads=""
```

In `usage()`, document:

```bash
  --opencv-num-threads N
      Optional OpenCV internal CPU thread limit for SIFT/FLANN. Omit to keep OpenCV defaults.
      Recommended with multi-process classic SIFT: --num-worker-parallel-cpu 2..4 --opencv-num-threads 1.
```

In argument parsing, add:

```bash
    --opencv-num-threads)
      opencv_num_threads="$2"
      shift 2
      ;;
```

After config resolution, use the existing helper style:

```bash
if [[ -z "$opencv_num_threads" ]]; then
  opencv_num_threads="$(extract_image_match_config_value "$config_input" "opencv_num_threads")"
fi
```

When building the image-match command, forward only if non-empty:

```bash
if [[ -n "$opencv_num_threads" ]]; then
  image_match_args+=(--opencv-num-threads "$opencv_num_threads")
fi
```

Include a log line near other execution settings:

```bash
echo "OpenCV threads: ${opencv_num_threads:-opencv default}"
```

- [ ] **Step 4: Update `run_image_match_batch_example.sh`**

Mirror the same variable, usage text, parser branch, config fallback, log line, and conditional forwarding.

- [ ] **Step 5: Update example config**

In `examples/controlnet_construct/controlnet_config.example.json`, inside `ImageMatch`, add:

```json
"opencv_num_threads": 1
```

Prefer the existing key style if the surrounding block consistently uses camelCase. If both styles exist, use snake_case because the new design names config as `ImageMatch.opencv_num_threads`.

- [ ] **Step 6: Run wrapper-focused tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS, or if the full module is slow/noisy, run only the new wrapper tests plus nearby existing wrapper tests and record the scope in the final report.

- [ ] **Step 7: Commit Task 5**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_image_match_batch_example.sh examples/controlnet_construct/controlnet_config.example.json tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: forward OpenCV thread limit from wrappers"
```

## Task 6: Update User Documentation

**Files:**
- Modify: `examples/controlnet_construct/usage.md`

- [ ] **Step 1: Add docs for the new option**

In the image-matching/execution section, add content equivalent to:

```markdown
### OpenCV internal thread control

`--opencv-num-threads N` limits OpenCV's internal CPU thread pool in each process. If omitted, the pipeline does not call `cv2.setNumThreads`, so OpenCV keeps its environment/default policy.

For classic SIFT+FLANN, total CPU pressure is roughly:

`num_worker_parallel_cpu × opencv_num_threads`

Recommended starting points:

- CPU-only classic SIFT+FLANN on a workstation: `--num-worker-parallel-cpu 2` to `4` with `--opencv-num-threads 1`.
- Single-process debugging: `--no-parallel-cpu --opencv-num-threads 1`.
- GPU SIFT with possible CPU fallback: keep the same `--opencv-num-threads` setting so fallback SIFT/FLANN paths remain bounded.
```

Mention the config key:

```json
{
  "ImageMatch": {
    "opencv_num_threads": 1
  }
}
```

- [ ] **Step 2: Verify docs mention all synchronized surfaces**

Search:

```bash
grep -R "opencv-num-threads\|opencv_num_threads" examples/controlnet_construct/usage.md examples/controlnet_construct/controlnet_config.example.json examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_image_match_batch_example.sh examples/image_match/image_match.py
```

Expected: each changed user-facing surface contains the new option/key.

- [ ] **Step 3: Commit Task 6**

```bash
git add examples/controlnet_construct/usage.md
git commit -m "docs: document OpenCV thread control"
```

## Task 7: Run Focused Validation And Smoke Checks

**Files:**
- Validate changed files only; no planned code edits unless tests expose failures.

- [ ] **Step 1: Run focused image-match tests**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test tests.unitTest.image_match_deep_manifest_unit_test -v
```

Expected: PASS.

- [ ] **Step 2: Run wrapper tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS. If this module is too slow for the session budget, run only the new wrapper tests plus nearby existing wrapper tests and explicitly report the reduced scope.

- [ ] **Step 3: Run smoke import**

```bash
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 4: Inspect git diff and commit any final fixes**

```bash
git status --short
git diff -- examples/image_match/image_match.py examples/image_match/tile_matching.py examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_image_match_batch_example.sh examples/controlnet_construct/controlnet_config.example.json examples/controlnet_construct/usage.md tests/unitTest/controlnet_construct_matching_unit_test.py tests/unitTest/image_match_deep_manifest_unit_test.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
```

If validation required additional fixes, commit them:

```bash
git add examples/image_match/image_match.py examples/image_match/tile_matching.py examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_image_match_batch_example.sh examples/controlnet_construct/controlnet_config.example.json examples/controlnet_construct/usage.md tests/unitTest/controlnet_construct_matching_unit_test.py tests/unitTest/image_match_deep_manifest_unit_test.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: validate OpenCV thread control"
```

## Task 8: Self-Review Before Hand-Off

- [ ] **Step 1: Confirm design-spec coverage**

Check implementation against `docs/superpowers/specs/2026-05-27-opencv-num-threads-design.md`:

- `--opencv-num-threads N` exists in image-match CLI.
- `ImageMatch.opencv_num_threads` config works.
- API accepts `opencv_num_threads: int | None = None`.
- `None` does not call `cv2.setNumThreads`.
- Positive int calls `cv2.setNumThreads` in main process.
- Worker process applies the same setting once per batch.
- GPU fallback path uses the process-level setting without a separate knob.
- Metadata/summary exposes requested/effective OpenCV thread state.
- No `auto` behavior was added.

- [ ] **Step 2: Check metadata headers and CLI naming**

Verify changed runnable example files have concise `Updated: 2026-05-27  Geng Xun ...` entries and that public flags use kebab-case only:

```bash
grep -R "--opencv_num_threads" examples scripts tests || true
grep -R "--opencv-num-threads" examples/controlnet_construct examples/image_match tests/unitTest | head -50
```

Expected: no public underscore flag; new public flag appears only as `--opencv-num-threads`.

- [ ] **Step 3: Check for unfinished markers and accidental artifacts**

```bash
python - <<'PY'
from pathlib import Path

needles = ("T" + "BD", "TO" + "DO", "PLACE" + "HOLDER", "??" + "?", "FIX" + "ME")
paths = [
    Path("docs/superpowers/plans/2026-05-27-opencv-num-threads.md"),
    *Path("examples/image_match").rglob("*"),
    *Path("examples/controlnet_construct").rglob("*"),
    Path("tests/unitTest/controlnet_construct_matching_unit_test.py"),
    Path("tests/unitTest/image_match_deep_manifest_unit_test.py"),
    Path("tests/unitTest/controlnet_construct_pipeline_unit_test.py"),
]
for path in paths:
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for needle in needles:
        if needle in text:
            print(f"{path}: contains {needle}")
git status --short
PY
```

Expected: no unfinished markers; status contains only intended tracked changes or is clean after commits.

- [ ] **Step 4: Final report**

Report:

- Files changed.
- Exact tests run and pass/fail output summary.
- Recommended user settings for classic SIFT+FLANN: start with `--num-worker-parallel-cpu 2` to `4` and `--opencv-num-threads 1`.
- Any validation not run and why.
