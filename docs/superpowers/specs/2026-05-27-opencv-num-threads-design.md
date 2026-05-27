# OpenCV thread control for image matching

## Purpose

Add an explicit image-match parameter for controlling OpenCV's internal CPU thread count. The goal is to prevent accidental oversubscription when the pipeline combines outer tile-level process parallelism with OpenCV's own internal pthread parallelism, while preserving current behavior unless the user opts in.

The active `asp360_new` OpenCV environment reports `cv2.getNumThreads() == 8`, `cv2.useOptimized() == True`, and `Parallel framework: pthreads`. With the current default CPU tile process limit of 8, traditional SIFT+FLANN can therefore create many more runnable CPU threads than users expect. This design gives users one stable knob for the OpenCV layer without changing the existing `--num-worker-parallel-cpu` process-level knob.

## User-facing behavior

Introduce one new optional setting:

- CLI flag: `--opencv-num-threads N`
- Config key: `ImageMatch.opencv_num_threads`
- Python API argument: `opencv_num_threads: int | None = None`

Semantics:

- `None` / omitted means do not call `cv2.setNumThreads`; keep the OpenCV default behavior.
- A positive integer `N` means call `cv2.setNumThreads(N)` before image matching work runs.
- Invalid values such as `0`, negative integers, or non-integers fail validation before matching.

Recommended traditional SIFT+FLANN starting point for large DOM matching:

- `num_worker_parallel_cpu = 2..4`
- `opencv_num_threads = 1`

This keeps the distinction clear:

- `num_worker_parallel_cpu` controls outer process-level tile parallelism.
- `opencv_num_threads` controls OpenCV's internal CPU worker threads inside each process.

## CPU/GPU synchronization rules

The first implementation should use a simple global OpenCV thread setting, not a hidden auto mode.

When `opencv_num_threads` is provided:

1. The main `image_match.py` process applies it before full-resolution matching and other OpenCV-heavy stages run.
2. Each process-pool tile worker applies the same setting before processing its tile shard.
3. GPU SIFT direct paths do not require special thread logic, but any CPU fallback path still observes the same OpenCV process setting.
4. Deep matcher paths are not given separate OpenCV-thread behavior in this change. If they call OpenCV in the same process, they inherit the configured process-level OpenCV setting.

GPU-specific notes:

- `--use-gpu` does not automatically change `opencv_num_threads`.
- GPU SIFT with `matcher_method=flann` currently falls back to CPU because GPU FLANN is unsupported in the current helper. That fallback should use the configured OpenCV thread count.
- CUDA unavailable or CUDA SIFT failure also falls back to CPU; those fallbacks should use the configured OpenCV thread count.

No automatic policy such as `auto` is included in this first change. An auto policy can be added later after benchmarking, but the initial behavior should remain explicit and easy to reason about.

## Architecture

### Shared helper

Add a small helper near the image-match runtime/config utilities, for example:

- validate a user value as `int | None`
- apply `cv2.setNumThreads(value)` when value is not `None`
- return diagnostics containing requested and effective OpenCV state

The helper should avoid scattering raw `cv2.setNumThreads(...)` calls across the codebase. The process worker can call the same helper with the payload value.

Suggested diagnostics shape:

```json
{
  "requested_num_threads": 1,
  "effective_num_threads": 1,
  "use_optimized": true
}
```

If omitted, metadata should still record enough to explain runtime behavior, for example requested `null` plus the observed effective OpenCV thread count.

### Image-match orchestration

Update `examples/image_match/image_match.py` so the new parameter flows through:

1. `load_image_match_defaults_from_config(...)`
2. argument parser
3. `match_dom_pair_to_key_files(...)`
4. `match_dom_pair(...)`
5. metadata output

The setting should be applied early enough that low-resolution offset estimation, adaptive routing probes, full-resolution tile matching, RANSAC/visualization-adjacent OpenCV work, and GPU fallback CPU paths see the same OpenCV process configuration.

### Tile task payloads

Update `examples/image_match/tile_matching.py` so `TileMatchTask` carries `opencv_num_threads`. It must be included in:

- `_build_tile_match_tasks(...)`
- `_tile_task_to_payload(...)`
- `_tile_task_from_payload(...)`
- process-pool batch worker setup

Each process-pool worker should apply the value once after payload deserialization and before opening/processing cube-backed tile data. This keeps worker behavior consistent with the main process and avoids relying on fork/spawn inheritance differences.

### GPU SIFT helper

`examples/image_match/gpu_sift.py` should not grow a separate thread-control policy. CPU fallback functions should rely on the current process's OpenCV setting. If a helper is needed for local tests, it should delegate to the shared image-match helper rather than introducing a second configuration surface.

## Pipeline and config integration

Update the user-facing wrappers so users can set the new knob from the same places as other execution controls:

- `examples/controlnet_construct/run_pipeline_example.sh`
- `examples/controlnet_construct/run_image_match_batch_example.sh`
- `examples/controlnet_construct/controlnet_config.example.json`
- `examples/controlnet_construct/usage.md`

Wrapper behavior:

- Add `--opencv-num-threads N` to usage/help.
- If omitted, read `ImageMatch.opencv_num_threads` from config when present.
- Forward the resolved value to `examples/image_match/image_match.py` only when a value is explicitly resolved.
- Log the value near CPU/GPU execution settings.

The example config may include:

```json
"opencv_num_threads": 1
```

Because the code default is opt-in, the example config can choose to recommend `1` for large traditional SIFT+FLANN workflows while preserving code-level default compatibility for direct users.

## Error handling

Validation should be consistent across CLI and config:

- `opencv_num_threads` must be a positive integer when provided.
- `null` in JSON means omitted.
- A CLI value overrides the config value.
- Worker-process apply failures should not be silently ignored. If OpenCV rejects the value or `cv2.setNumThreads` fails, the run should fail with the original exception context.

## Testing

Focused tests should cover:

1. CLI parsing accepts `--opencv-num-threads 1` and rejects `0` / negative values.
2. Config loading accepts `ImageMatch.opencv_num_threads` and treats `null` as omitted.
3. `match_dom_pair(...)` metadata includes requested/effective OpenCV thread diagnostics.
4. `TileMatchTask` payload serialization/deserialization preserves `opencv_num_threads`.
5. Process-pool batch workers apply the setting before tile processing.
6. Default behavior does not call `cv2.setNumThreads` or otherwise force a new OpenCV thread count.
7. GPU SIFT CPU fallback paths remain functional when `opencv_num_threads=1` is configured.

Validation should use the smallest focused Python tests first, then a smoke import/run if implementation touches CLI or worker payload plumbing.

## Non-goals

- Do not add an `auto` thread policy in the first implementation.
- Do not change the default process-pool worker count.
- Do not change SIFT, FLANN, ratio-test, or GPU batch defaults.
- Do not introduce a separate GPU-specific OpenCV thread knob.
- Do not refactor unrelated matching or visualization code.

## Open questions resolved by this design

- The setting is global per process, not scoped only to one matcher call.
- CPU and GPU fallback paths use the same process-level OpenCV thread count.
- Omitted values preserve existing behavior.
- The process-pool worker applies the setting explicitly rather than relying on platform-specific multiprocessing inheritance.
