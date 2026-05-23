# ControlNet Matcher Comparison Experiment Design

## Goal

Build a reproducible small-batch experiment for comparing end-to-end ControlNet construction across these matcher configurations:

| Label | Matcher method | Deep preset |
| --- | --- | --- |
| `sift_flann` | `flann` | none |
| `sift_lightglue` | `lightglue` | `examples/controlnet_construct/presets/lightglue_official_sift.json` |
| `disk_lightglue` | `lightglue` | `examples/controlnet_construct/presets/lightglue_official_disk.json` |
| `aliked_lightglue` | `lightglue` | `examples/controlnet_construct/presets/lightglue_official_aliked.json` |
| `doghardnet_lightglue` | `lightglue` | `examples/controlnet_construct/presets/lightglue_official_doghardnet.json` |
| `superpoint_lightglue` | `lightglue` | `examples/controlnet_construct/presets/lightglue_official_superpoint.json` |
| `loftr` | `loftr` | `examples/controlnet_construct/presets/loftr_default.json` |

The experiment compares both engineering performance and final ControlNet quality. It should use the same high-level pipeline users already run, so the result represents production workflow behavior rather than an isolated micro-benchmark.

## Scope

The first version is a wrapper-driven black-box experiment. It does not change core matching, RANSAC, or ControlNet construction logic. The experiment runner orchestrates existing shell/Python entry points, captures logs and metrics, and writes reports.

Sample selection stays outside the experiment runner. The user prepares the input lists and work context exactly as they would for the normal pipeline. If the configured pipeline finds three stereo pairs, each matcher runs three stereo pairs. If runtime is a concern, the user should prepare a smaller input list or work directory before starting the experiment. The experiment runner must not implement `first_n`, random sampling, or pair filtering in the first version.

## Execution Model

Add a new experiment package under:

```text
examples/controlnet_construct/experiments/
```

Primary entry point:

```text
examples/controlnet_construct/experiments/run_matcher_comparison.py
```

The runner reads a JSON config, expands method definitions, and creates one isolated work directory per method:

```text
work/matcher_comparison/<run_id>/
  experiment_config.json
  experiment_manifest.json
  reports/
    summary.csv
    summary.json
    summary.md
    failures.json
  methods/
    sift_flann/
      command.sh
      stdout.log
      stderr.log
      work/
      metrics.json
    superpoint_lightglue/
      command.sh
      stdout.log
      stderr.log
      work/
      metrics.json
```

`sift_flann` runs the normal pipeline directly in `asp360_new`, using `run_pipeline_example.sh --matcher-method flann`.

Deep methods run the existing export, deep-learning, and import handoff workflow via `run_deep_match_pipeline.sh`. This keeps ISIS/PyISIS work in `asp360_new` and model execution in a deep-learning conda environment. A future version may support direct deep matching, but export/import is the default first-version path.

Every method writes its exact command to `command.sh` before execution. This makes failed or suspicious runs easy to reproduce by hand.

## Experiment Config

Create a template:

```text
examples/controlnet_construct/experiments/matcher_comparison.example.json
```

Template shape:

```json
{
  "run_id": "lro_batch_20260522",
  "description": "Matcher comparison for ControlNet construction",
  "inputs": {
    "original_images_list": "original_images.lis",
    "doms_list": "doms_scaled.lis",
    "controlnet_config": "examples/controlnet_construct/controlnet_config.example.json"
  },
  "execution": {
    "asp360_env": "asp360_new",
    "deep_learning_env": "deep-learning",
    "device": "auto",
    "skip_final_merge": false,
    "keep_going": true,
    "resume": true
  },
  "methods": [
    { "label": "sift_flann", "matcher_method": "flann" },
    {
      "label": "sift_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_sift.json"
    },
    {
      "label": "disk_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_disk.json"
    },
    {
      "label": "aliked_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_aliked.json"
    },
    {
      "label": "doghardnet_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_doghardnet.json"
    },
    {
      "label": "superpoint_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json"
    },
    {
      "label": "loftr",
      "matcher_method": "loftr",
      "deep_match_config_path": "examples/controlnet_construct/presets/loftr_default.json"
    }
  ]
}
```

The `inputs` fields document the intended pipeline inputs and are copied into the experiment snapshot. The first version may rely on existing wrapper defaults for actual list paths if the wrappers do not currently expose explicit input-list flags. If wrapper changes are needed to honor these fields, keep them minimal and backwards-compatible.

## CLI Behavior

The runner should support:

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root work/matcher_comparison \
  --resume \
  --keep-going
```

Required options:

- positional config path
- `--output-root`
- `--resume`
- `--only METHOD[,METHOD]`
- `--dry-run`
- `--keep-going`
- `--fail-fast`

`--resume` skips methods whose `metrics.json` records `status: success`. Failed, partial, missing, or malformed metrics are rerun unless `--only` excludes them.

`--dry-run` writes the experiment manifest and method command scripts but does not execute wrappers.

## Metrics

The first version should collect stable black-box metrics. It should not depend on invasive instrumentation inside the matching core.

Performance metrics:

- `status`: `success`, `failed`, `skipped`, or `partial`
- `return_code`
- `total_wall_seconds`
- `export_wall_seconds`, `deep_match_wall_seconds`, and `import_or_pipeline_wall_seconds` where separable
- `peak_rss_mb` from `/usr/bin/time -v` when available
- requested `device`
- `pair_count`
- `failed_pair_count`

Quality metrics:

- pre-RANSAC match count, when available from image-match sidecars or key files
- post-RANSAC retained match count, when available from batch summaries or output key files
- pairwise ControlNet count
- final merged ControlNet generated: true/false
- control point count and control measure count, preferably via `isis_pybind` when possible
- per-pair success rate
- empty-match pair count
- RANSAC retained ratio
- key output paths and file sizes for traceability

Metrics collection must be defensive. Missing optional files should produce null fields and warnings rather than crashing the entire report pass.

## Reports

Write three report formats:

- `summary.json`: full structured data, one method object per matcher
- `summary.csv`: flat comparison table for spreadsheet use
- `summary.md`: human-readable report with a method ranking table, failures, and notes

Also write `failures.json` with method label, stage, return code, command, and log paths for every failed or partial method.

## Error Handling

The runner should treat each method as an independent job:

- With `--keep-going`, a method failure records failure metadata and continues to the next method.
- With `--fail-fast`, the first failure stops the experiment after writing current metrics.
- Missing deep-learning dependencies should be captured as method failures, not as runner crashes.
- Invalid config should fail before any method starts.

The runner must preserve logs even when a method fails.

## Tests

Do not require real deep models or large ISIS data in unit tests. Test orchestration with fake commands and fake outputs.

Recommended coverage:

- config parsing expands all seven method definitions
- command generation routes `sift_flann` to `run_pipeline_example.sh`
- command generation routes deep methods to `run_deep_match_pipeline.sh`
- `--only` restricts execution to requested methods
- `--resume` skips successful methods and reruns failed/missing methods
- `--dry-run` writes command scripts and manifest without executing
- report writer produces JSON, CSV, and Markdown from synthetic metrics
- failure handling records stdout/stderr paths and return codes

## Worktree

Implement this work on:

```text
.worktrees/experiment-matcher-comparison-20260522
```

Branch:

```text
feat/experiment-matcher-comparison-20260522
```

Before implementation, run the repo smoke import in the worktree:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

If the baseline smoke test fails, report it before implementation so new failures are not confused with pre-existing workspace state.
