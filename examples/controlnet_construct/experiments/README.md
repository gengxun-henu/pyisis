# ControlNet Matcher Comparison Experiments

This directory contains a wrapper-driven experiment runner for comparing
ControlNet construction matcher methods. It does not modify the core pipeline;
it prepares per-method workspaces, invokes the existing ControlNet wrapper
scripts, and collects comparable reports.

## Inputs

The example config uses the stereo pairs that are already represented by these
repo-relative lists:

- `work/original_images.lis`
- `work/doms_scaled.lis`

The runner does not select or downsample pairs on its own. To reduce runtime,
manually edit or prepare `work/original_images.lis` and `work/doms_scaled.lis`
before starting the comparison. Each method run receives copies of those lists
as `work/original_images.lis` and `work/doms_scaled.lis` inside its method
workspace so the existing wrapper defaults continue to apply.

## Default Methods

`matcher_comparison.example.json` currently compares these method labels:

- `sift_flann`
- `sift_lightglue`
- `disk_lightglue`
- `aliked_lightglue`
- `doghardnet_lightglue`
- `superpoint_lightglue`
- `loftr`

Use `--only` with comma-separated labels for a subset run, for example
`--only sift_flann,loftr`.

## Runtime Setup

Run these commands from the repository root before invoking the matcher
comparison runner:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
```

The mock `ISISDATA` path is appropriate for tests, smoke checks, and examples.
For real data runs, set real ISISDATA to the production ISIS data location
instead of the mock tree.

Deep matcher methods such as LightGlue, SuperGlue, and LoFTR use the
`deep-learning` conda environment named in the experiment config. That
environment must already exist, and `conda` must be available on `PATH`, because
the wrapper launches the deep-learning stage through conda.

## Dry Run

Use dry-run mode to validate the config, create the run manifest, and write each
method's `command.sh` without executing the pipeline:

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root work/matcher_comparison \
  --dry-run
```

Dry-run mode allows missing input lists. When the configured lists are absent,
the manifest records warnings and the command scripts are still written.

## Dry-Run Output

Dry-run output contains only the files needed to inspect the planned run:

```text
work/matcher_comparison/<run_id>/
  experiment_config.json        # config snapshot
  experiment_manifest.json
  methods/
    <method_label>/
      command.sh
```

The manifest includes warnings for missing input lists. Dry-run mode does not write
per-method `stdout.log`, `stderr.log`, or `metrics.json`, and it does not write
real-run summary reports: `reports/summary.json`, `summary.csv`, `summary.md`,
or `failures.json`.

## Real Run

For a resumable run that continues after method failures:

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root work/matcher_comparison \
  --resume \
  --keep-going
```

The example config also enables resume and keep-going by default. CLI flags are
useful when making the desired behavior explicit in a run log.

## Real-Run Output

Runs are created below the selected output root using the config `run_id`:

```text
work/matcher_comparison/<run_id>/
  experiment_config.json
  experiment_manifest.json
  methods/
    <method_label>/
      command.sh
      stdout.log
      stderr.log
      metrics.json
      work/
        original_images.lis
        doms_scaled.lis
  reports/
    summary.json
    summary.csv
    summary.md
    failures.json
```

Each per-method directory is independent. `command.sh` is the exact command the
runner prepared for that method, `stdout.log` and `stderr.log` capture pipeline
output, and `metrics.json` stores the collected method metrics. The `reports/`
directory contains cross-method summaries, including `reports/summary.json`,
`summary.csv`, `summary.md`, and `failures.json`.

## ISIS C++ vs PyISIS Benchmark

`isis_cpp_pyisis_benchmark.py` compares direct ISIS C++ calls against PyISIS for
camera coordinate conversion and ControlNet traversal. It is a benchmark
harness, not a ControlNet construction pipeline.

Build the C++ benchmark first. If the build directory has not been configured
yet, configure it with the conda compiler:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$HOME/miniconda3/bin/x86_64-conda-linux-gnu-c++"
cmake --build build --target isis_cpp_benchmark -j"$(nproc)"
```

Dry-run mode validates the config and writes the planned command files without
running PyISIS or the C++ benchmark:

```bash
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

Fixture smoke mode runs the repo fixture with mock `ISISDATA`:

```bash
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark
```

Benchmark runs keep going after task failures by default; pass `--fail-fast`
when the first PyISIS or C++ task failure should abort the run. Real runs
validate selected CUBE and ControlNet input paths before task execution, while
dry-run mode still permits missing inputs so command scripts can be reviewed.
The JSON summaries include run provenance such as the config snapshot path,
PyISIS import path, C++ benchmark path, ISIS environment, git commit, and
per-result command arguments for C++ tasks.

For real LRO NAC performance runs, set production `ISISDATA` and point the
config at production CUBE and ControlNet files. Remove `max_points` from a
camera task when you want full-grid sampling at the configured step.
