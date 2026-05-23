# ISIS C++ vs PyISIS Benchmark Design

## Goal

Build a reproducible benchmark experiment for comparing PyISIS against direct
ISIS C++ calls on two performance-sensitive workflows:

- LRO NAC camera model image-to-ground and ground-to-image conversion.
- ControlNet loading and traversal for point and measure statistics.

The benchmark should report both efficiency and numerical agreement. It should
use the same conda-managed ISIS installation as the Python extension so the
comparison focuses on PyISIS binding overhead, Python loop overhead, and direct
C++ API behavior rather than different ISIS versions or command-line wrappers.

## Scope

The first version is an experiment harness, not a binding expansion. It should
not change camera model behavior, ControlNet behavior, or the ControlNet
construction pipeline. If a field is not available through both PyISIS and C++
in a stable way, exclude that field from the first version rather than expanding
the bindings as part of this work.

The experiment should run in a new isolated worktree and branch. The main
checkout is already being used for adjacent work, and this benchmark touches
CMake, C++ tooling, Python orchestration, and tests.

## Architecture

Add a performance experiment family that follows the existing
`examples/controlnet_construct/experiments/` style without mixing with matcher
comparison logic.

Python orchestration:

```text
examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py
examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json
```

C++ benchmark tool:

```text
tools/benchmarks/isis_cpp_benchmark.cpp
build/tools/benchmarks/isis_cpp_benchmark
```

The C++ tool is built by CMake and links directly to the same ISIS libraries
used by `isis_pybind._isis_core`. The Python runner invokes both the PyISIS
implementation and the C++ executable, compares their outputs, and writes
reports below:

```text
work/isis_cpp_pyisis_benchmark/<run_id>/
  experiment_config.json
  experiment_manifest.json
  pyisis/
  cpp/
  reports/
    summary.json
    summary.csv
    camera_top_errors.csv
    controlnet_summary.json
```

The runner owns experiment setup, command recording, subprocess execution,
reporting, and cross-implementation diffs. The C++ tool and PyISIS task code
own only the benchmark operations and their core timing.

## Config

Use a JSON config with three top-level task sections:

```json
{
  "run_id": "lro_nac_pyisis_cpp_20260523",
  "description": "Compare PyISIS and direct ISIS C++ on camera and ControlNet workflows.",
  "execution": {
    "cpp_benchmark_path": "build/tools/benchmarks/isis_cpp_benchmark",
    "repeat_count": 1,
    "keep_intermediate_json": true
  },
  "camera_tasks": [
    {
      "label": "lro_nac_example",
      "cube_path": "tests/data/lronacpho/M143947267L.cal.echo.crop.cub",
      "sample_step": 10,
      "line_step": 10,
      "max_points": 10000,
      "top_error_count": 50
    }
  ],
  "controlnet_tasks": [
    {
      "label": "three_image_network",
      "net_path": "tests/data/threeImageNetwork/controlnetwork.net"
    }
  ]
}
```

The default camera sampling mode is full image sampling at the configured
sample and line step. `max_points` is optional and caps the generated point set
for fast exploratory runs. When `max_points` is omitted, the task samples the
full grid. This keeps the real LRO NAC experiment faithful to the requested
10-pixel grid while allowing small smoke runs.

## Camera Benchmark

For each sampled image coordinate, both implementations run the same operation:

1. Call `set_image(sample, line)`.
2. Read universal latitude and longitude, and radius when a stable API is
   available in both implementations.
3. Call `set_universal_ground(...)` using the ground coordinate.
4. Read the returned sample and line.

Each side records:

- input point count
- successful point count
- failed `set_image` count
- failed `set_universal_ground` count
- core timing in seconds
- average successful point timing
- output values for successful points when intermediate JSON is enabled

The runner compares PyISIS and C++ only on points that succeed on both sides.
It computes max, mean, and RMS absolute errors for latitude, longitude, sample,
and line. It writes the top-N largest camera differences to
`reports/camera_top_errors.csv`, ordered by a combined absolute image-space and
ground-space error score.

## ControlNet Benchmark

For each ControlNet task, both implementations split timing into:

- `load_seconds`: constructing or reading the `ControlNet` from disk.
- `traverse_seconds`: iterating through all points and measures.

Traversal reads stable fields that both sides can access:

- point id
- point type where available
- measure cube serial number
- measure sample and line
- measure type where available
- ignored and edit-lock state where available

The reported statistics include:

- point count
- measure count
- valid point count when available
- valid measure count when available
- per-serial measure count when available without extra business logic
- load timing
- traversal timing
- total core timing

The first version does not implement merge-control-measure style hash grouping.
That workflow can be added later as a separate business-logic benchmark after
the base traversal overhead is known.

## Timing Rules

The reports must distinguish benchmark core time from orchestration wall time.

- `core_seconds`: time measured inside PyISIS task code or the C++ executable
  around the target ISIS operations.
- `wall_seconds`: time measured by the runner around the subprocess or function
  call.

Use `core_seconds` for API performance comparison. Keep `wall_seconds` in the
report for operational cost and debugging. Do not include Python subprocess
launch overhead in the C++ core time or PyISIS core time.

## Error Handling

Each task is independent. A failed camera task or ControlNet task should not
discard the rest of the experiment unless the user explicitly runs in fail-fast
mode.

Camera point-level failures are counted and sampled in the report. Task-level
failures preserve stdout, stderr, command arguments, return code, and a short
error summary. If PyISIS and C++ have different successful point sets, report
`missing_in_pyisis` and `missing_in_cpp`; calculate numerical error statistics
only on the intersection.

Invalid config should fail before any benchmark task starts. Missing input files
should be reported as config errors in real-run mode. Dry-run mode may write the
manifest and planned commands without requiring all inputs to exist.

## Reports

Write structured and tabular reports:

- `reports/summary.json`: complete task and implementation metrics.
- `reports/summary.csv`: flat task-level comparison for spreadsheet review.
- `reports/camera_top_errors.csv`: top-N camera coordinate disagreements.
- `reports/controlnet_summary.json`: ControlNet-specific counts and timings.

Every report should include enough provenance to reproduce the run: config
snapshot path, PyISIS import path, C++ executable path, command arguments,
`ISISDATA`, conda environment name when available, and git commit.

## CLI

The runner should support:

```bash
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark
```

Useful options:

- `--dry-run`: validate config and write the manifest and planned commands.
- `--only TASK_LABEL[,TASK_LABEL]`: run a subset of tasks.
- `--keep-going`: continue after task failures.
- `--fail-fast`: stop after the first task failure.
- `--cpp-benchmark-path PATH`: override the config's C++ executable path.

The exact command used for each C++ task should be written to a `command.sh`
file in that task's output directory.

## Tests

Automated tests should use small existing fixtures and fake subprocess output
where possible. Real production LRO NAC benchmark runs are manual validation,
not unit tests.

Recommended coverage:

- config parsing and path resolution
- camera sampling grid generation, including `max_points`
- top-N error ranking and max/mean/RMS calculations
- mismatched success-set handling
- ControlNet summary comparison
- dry-run manifest and command generation
- C++ output schema parsing

Focused verification commands:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

After implementation, a small smoke run should use repo fixtures. A real
performance run should use the user's production LRO NAC cubes and real
ControlNet files with production `ISISDATA`.

## Out Of Scope

- New PyISIS bindings.
- Changes to ISIS camera model or ControlNet semantics.
- ControlNet construction matcher comparison.
- Merge-control-measure hash grouping benchmark.
- Automatic selection or reduction of production input datasets outside the
  explicit camera sampling parameters.
