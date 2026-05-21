# Learning methods deep-match workflow

`examples/learning_methods/` contains deep-learning-oriented image matching utilities that are intended to run outside the main ISIS/PYISIS environment when necessary. The current handoff workflow is designed for the common local setup where:

- ISIS/PYISIS and `examples/image_match` run in the `asp360_new` conda environment.
- LightGlue, LoFTR, SuperGlue, or related deep-learning stacks run in the `deep-learning` conda environment.

The workflow avoids importing heavy deep-learning dependencies inside `asp360_new`. Instead, it exchanges files through a manifest workspace.

## Directory roles

- `run_deep_match_manifest.py` — reads an exported `tasks.json`, runs a deep matcher, and writes standardized `.npz` result files.
- `test-lightglue.py`, `test-loftr.py` — minimal import-and-initialize smoke tests for checking whether LightGlue / LoFTR can be introduced into the current environment.
- `run-lightglue.py`, `run-loftr.py`, and related scripts — standalone two-image experiments and local matcher diagnostics.
- `sweep_lightglue_params.py`, `sweep_loftr_params.py` — parameter sweep utilities. Generated CSV output belongs in `sweep_results/` and is ignored by default.

## Three-stage handoff

### 1. Export matching tasks in `asp360_new`

Run `examples/image_match/image_match.py` with a deep matcher method and export mode. This stage reads ISIS cubes, prepares tile arrays and invalid masks, and writes a manifest workspace.

```bash
python examples/image_match/image_match.py \
  left_dom.cub \
  right_dom.cub \
  left_output.key \
  right_output.key \
  --matcher-method lightglue \
  --deep-match-mode export \
  --deep-match-temp-root-dir tmp_deep_match \
  --no-write-match-visualization
```

Expected workspace layout:

```text
tmp_deep_match/<pair-id>/
  tasks.json
  images/
    task_00000_left.npy
    task_00000_right.npy
    task_00000_left_mask.npy
    task_00000_right_mask.npy
  results/
  logs/
```

Export mode does not write final `.key` files. It records enough tile/window metadata for later import.

### 2. Run the manifest in `deep-learning`

Switch to the environment that contains the requested deep-learning matcher dependencies, then execute the manifest runner.

```bash
python examples/learning_methods/run_deep_match_manifest.py \
  tmp_deep_match/<pair-id>/tasks.json \
  --device auto \
  --summary-output tmp_deep_match/<pair-id>/run_summary.json
```

The runner writes one standardized result file per task:

```text
tmp_deep_match/<pair-id>/results/task_00000_matches.npz
```

Each `.npz` stores:

- `left_points`: float32 `N x 2` tile-local `(x, y)` coordinates.
- `right_points`: float32 `N x 2` tile-local `(x, y)` coordinates.
- `scores`: float32 confidence-like scores.
- `metadata_json`: JSON metadata including status and match counts.

### 3. Import results in `asp360_new`

Return to the ISIS/PYISIS environment and import the completed manifest. This converts tile-local deep-match coordinates into full-image ISIS-style `.key` files.

```bash
python examples/image_match/image_match.py \
  left_dom.cub \
  right_dom.cub \
  left_output.key \
  right_output.key \
  --deep-match-mode import \
  --deep-match-manifest tmp_deep_match/<pair-id>/tasks.json \
  --no-write-match-visualization
```

Coordinate conversion uses the manifest window metadata:

```text
sample = window.start_x + local_x + 1.0
line   = window.start_y + local_y + 1.0
```

This keeps deep-learning results tile-local while preserving the `.key` convention used by downstream controlnet construction.

## Status handling

The import stage skips tasks whose result files are missing or whose result metadata reports `failed`. Empty successful results are allowed and produce no points for that task. Import metadata records how many tasks were imported, skipped, failed, or missing.

## Validation checklist

For focused local validation in `asp360_new`, prefer:

```bash
python -m unittest \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.learning_methods_deep_manifest_runner_unit_test
```

For lightweight deep-matcher smoke checks, run the example scripts directly:

```bash
python examples/learning_methods/test-lightglue.py
python examples/learning_methods/test-loftr.py
```

For repository-level validation, use the standard project script when appropriate:

```bash
scripts/build_test_smoke.sh full
```

## Notes

- Keep generated sweep outputs out of commits unless they are intentionally curated benchmark artifacts.
- Use `--kebab-case` command-line options in user-facing docs and examples.
- Prefer small synthetic tests for manifest/schema behavior; reserve real deep matcher smoke tests for the `deep-learning` environment.
