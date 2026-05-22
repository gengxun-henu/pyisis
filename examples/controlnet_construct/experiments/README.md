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

## Output Layout

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
