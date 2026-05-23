# Raw Image Space ControlNet Pipeline Design

## Goal

Add an independent wrapper for building ControlNets from direct raw/original
image space matching, while leaving the existing DOM matching pipeline unchanged.

The first version should reuse the already implemented single-pair
`controlnet_stereopair.py from-ori-match` command. The work is orchestration,
reporting, and documentation, not a rewrite of matching or ControlNet creation.

## Current Context

The current end-to-end example pipeline is DOM-first:

1. `image_overlap.py` reads `original_images.lis` and writes
   `images_overlap.lis`.
2. `examples/image_match/image_match.py` matches aligned DOM cubes and writes
   DOM-space `.key` files.
3. `controlnet_stereopair.py from-dom-batch` merges, filters, converts DOM
   coordinates back to original-image coordinates, and writes pairwise
   ControlNets.
4. `controlnet_merge.py` prepares the final `cnetmerge` command.

The repository already has a single-pair raw image path:

```bash
python examples/controlnet_construct/controlnet_stereopair.py from-ori-match \
  LEFT_ORIGINAL.cub \
  RIGHT_ORIGINAL.cub \
  examples/controlnet_construct/controlnet_config.example.json \
  work/ori_pair_nets/LEFT__RIGHT.net
```

That command directly matches the original cubes, writes original-image `.key`
files, and calls the existing `build_controlnet_for_stereo_pair` function. The
missing piece is a low-risk batch wrapper that runs this command for every pair
in `images_overlap.lis` and then uses the existing merge helper.

## Scope

In scope for the first implementation:

- Add `examples/controlnet_construct/run_ori_match_pipeline_example.sh`.
- Reuse `image_overlap.py` for pair discovery.
- Reuse `controlnet_stereopair.py from-ori-match` for every overlap pair.
- Reuse `controlnet_merge.py` for merge script and pair-list generation.
- Preserve the existing DOM wrapper behavior and defaults.
- Keep output paths and reports predictable under a caller-provided work
  directory.
- Support a compact dry-run mode for command-generation tests.

Out of scope for the first implementation:

- Deep matchers, deep-match export/import, and external learning environments.
- Adaptive routing.
- DOM preparation, DOM low-resolution offset estimation, and DOM-space RANSAC
  visualizations.
- Changing `image_match.py` matching internals.
- Changing `from-dom`, `from-dom-batch`, or `run_pipeline_example.sh` behavior.

## Entry Point

Add:

```text
examples/controlnet_construct/run_ori_match_pipeline_example.sh
```

The wrapper should follow the existing shell style used by
`run_pipeline_example.sh`: fail fast, print compact stage summaries, resolve
paths relative to the repository, and keep detailed artifacts in files rather
than noisy stdout.

Example invocation:

```bash
bash examples/controlnet_construct/run_ori_match_pipeline_example.sh \
  --work-dir work_ori \
  --original-list work/original_images.lis \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --matcher-method flann \
  --num-worker-parallel-cpu 8
```

## Pipeline

### Stage 1: Pair Discovery

Run:

```bash
python examples/controlnet_construct/image_overlap.py \
  "$ORIGINAL_LIST" \
  "$IMAGES_OVERLAP_LIST" \
  --report-json "$REPORTS_DIR/image_overlap_summary.json"
```

The first version should use the same overlap semantics as the DOM pipeline.
If users need fewer pairs, they should provide a smaller `original_images.lis`
or precomputed overlap list in a later extension. The wrapper should not
implement sampling policy.

### Stage 2: Raw Image Pair Matching and Pairwise ControlNets

For each `left,right` entry in `images_overlap.lis`:

1. Build the canonical pair tag with the same stem convention as existing
   pairwise outputs: `LEFT_STEM__RIGHT_STEM`.
2. Auto-assign a pair ID using `--pair-id-prefix` and `--pair-id-start`.
3. Call `controlnet_stereopair.py from-ori-match`.
4. Persist original-image key files and per-pair summaries.

Suggested output layout:

```text
<work-dir>/
  images_overlap.lis
  ori_keys/
    LEFT__RIGHT_A.key
    LEFT__RIGHT_B.key
  ori_pair_nets/
    LEFT__RIGHT.net
  reports/
    image_overlap_summary.json
    LEFT__RIGHT.summary.json
    ori_match_batch_summary.json
  merge/
    ori_matching_merged.net
    merge_all_controlnets.lis
    merge_all_controlnets.sh
    controlnet_merge_summary.json
```

Each `from-ori-match` command should receive:

- left and right original cube paths from `images_overlap.lis`
- controlnet config path
- pairwise output `.net` path
- `--pair-id`
- `--left-output-key`
- `--right-output-key`
- `--report-path`
- selected matcher and execution parameters

### Stage 3: Merge Preparation and Optional Merge Execution

Run `controlnet_merge.py` with the overlap list, pairwise net directory, final
output path, and merge script path. The wrapper should default to executing the
generated merge shell, matching the normal example pipeline behavior, and expose
`--skip-final-merge` for users who only want the script.

## CLI Surface

The first version should support:

- `--work-dir PATH`
- `--original-list PATH`
- `--images-overlap-list PATH`
- `--config PATH`
- `--matcher-method NAME`
- `--band N`
- `--ratio-test FLOAT`
- `--max-features N`
- `--pair-id-prefix VALUE`
- `--pair-id-start N`
- `--num-worker-parallel-cpu N`
- `--use-parallel-cpu` / `--no-parallel-cpu`
- `--use-gpu`
- `--gpu-batch-size N`
- `--gpu-dynamic-batch` / `--no-gpu-dynamic-batch`
- `--gpu-min-batch-size N`
- `--gpu-max-batch-size N`
- `--skip-final-merge`
- `--dry-run`
- `--log-level VALUE`

Defaults should be conservative:

- `--work-dir work_ori`
- `--original-list <work-dir>/original_images.lis`
- `--images-overlap-list <work-dir>/images_overlap.lis`
- `--config examples/controlnet_construct/controlnet_config.example.json`
- `--matcher-method flann`
- `--pair-id-prefix S`
- `--pair-id-start 1`
- `--num-worker-parallel-cpu 8`

## Dry Run

`--dry-run` should write the commands that would be executed without running
ISIS or matching work. It should create a reproducible command script such as:

```text
<work-dir>/command.sh
```

The command script is the primary regression surface for the first
implementation. It lets tests verify routing, pair naming, pair IDs, and option
forwarding without requiring real planetary image data.

## Reporting

The wrapper should write `reports/ori_match_batch_summary.json` with:

- `mode: "from-ori-match-batch-wrapper"`
- input paths
- pair count
- pair ID prefix/start
- matcher method
- pairwise net output directory
- report directory
- merge output path
- per-pair records containing pair CSV, pair ID, net path, key paths, report
  path, and command status

The wrapper should keep stdout compact:

- stage labels
- pair tag currently running
- per-pair summary path
- final batch summary path
- merge summary path

Detailed command output should stay in logs or per-pair JSON where practical.

## Error Handling

- Missing `original_images.lis` should fail before any output-heavy stage.
- Empty `images_overlap.lis` should warn and stop before pairwise ControlNet
  generation.
- A failed pair should fail the wrapper by default.
- A future `--keep-going` option may be useful, but it is not needed for the
  first version.
- Deep matcher flags must be rejected or omitted in the first version. The
  wrapper should not silently interpret deep preset options.

## Testing

Add focused tests that do not require real data-heavy matching:

1. Command-generation test for `run_ori_match_pipeline_example.sh --dry-run`.
   It should verify:
   - `image_overlap.py` command is present.
   - `from-ori-match` commands use canonical pair tags.
   - pair IDs increment from `--pair-id-start`.
   - key, net, and report paths are under the selected work directory.
   - `controlnet_merge.py` command is present.

2. Argument validation test:
   - missing required files fail clearly.
   - invalid `--pair-id-start` fails clearly.
   - unsupported deep-only flags are not accepted.

3. Existing smoke:
   - `python tests/smoke_import.py`

If the implementation touches Python helpers, run the relevant
`tests.unitTest.controlnet_construct_*` module. If the change remains shell
wrapper only, a wrapper-specific test plus smoke import is enough.

## Risks

- Raw image matching may be less stable than DOM matching for pairs with large
  viewpoint or illumination differences. The first version should expose
  matcher parameters and write artifacts that make bad pairs inspectable.
- A shell-only wrapper has some duplicated orchestration logic. That is
  acceptable here because the goal is isolation and low blast radius. If this
  path becomes the primary workflow, a later implementation can extract shared
  wrapper helpers.
- Pair naming must stay consistent with `controlnet_merge.py` expectations.
  Tests should lock down the `LEFT__RIGHT` convention.

## Acceptance Criteria

- A user can run a separate raw image pipeline wrapper without changing the DOM
  pipeline.
- The wrapper can produce one pairwise ControlNet per overlap pair using
  `from-ori-match`.
- The wrapper can generate and optionally execute the final merge script.
- Dry-run output is deterministic enough for regression tests.
- Existing DOM pipeline tests and smoke import still pass.
