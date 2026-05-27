# Adaptive Fast Pipeline Performance Design

Date: 2026-05-27
Status: Draft for user review

## Context

The ControlNet construction pipeline now supports several matching paths:

- Classic SIFT with BF or FLANN matching in `examples/image_match/image_match.py`.
- Deep matcher export/import split mode through `examples/learning_methods/run_deep_match_manifest.py`.
- Adaptive routing in `examples/image_match/adaptive_routing.py`, driven by texture sparseness and sensor-model lighting difference.

Recent real-data runs on `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2` show that deep matching is not the right default for this dataset on CPU. `SIFT+LightGlue` on one 512 x 512 tile spends about 20-22 seconds, mostly in LightGlue matching. OpenCV `SIFT+FLANN` on the same tile is below one second. A full adaptive `SIFT+FLANN` run with existing texture and lighting routing completed the pairwise pipeline in 54.36 seconds, then final `cnetmerge` completed in another 21.28 seconds.

The adaptive run selected `flann` for all six pairs because the pair texture was rich and the lighting difference was small. It produced a merged ControlNet at:

`/tmp/pipe_test2_adaptive_route_realdata_20260527/balanced/merge/dom_matching_merged.net`

The pairwise ControlNet stage retained 37,455 final control points before final merge execution.

## Goals

- Make the fast classic matcher path the recommended production default for LRO-style DOM matching.
- Use the existing texture and lighting adaptive router as the decision layer.
- Escalate to deep matchers only when diagnostics or quality gates show the classic matcher is not enough.
- Preserve existing deep matcher functionality for difficult imagery and explicit quality-first runs.
- Keep the first release slice small: documentation, reproducible commands, and validation evidence before broad refactoring.
- Capture enough performance evidence to decide whether this can become a versioned release.

## Non-Goals

- Do not rewrite the ControlNet pipeline executor in this slice.
- Do not change default matcher behavior globally without a separate implementation plan.
- Do not tune GPU LightGlue or LoFTR in this release candidate.
- Do not remove existing deep matcher presets, split-mode manifests, or profile scripts.
- Do not stage or modify local `.gitignore` or generated `print.prt` files.

## Recommended Pipeline

The recommended production path is an adaptive fast pipeline:

1. Run overlap discovery as usual.
2. Generate or reuse low-resolution DOMs for offset estimation.
3. Enable adaptive routing with the `balanced` profile.
4. Request `flann` as the baseline matcher.
5. Let the router compute texture sparseness and sensor-model lighting difference.
6. Stay on `flann` when the pair has rich texture and low lighting difference.
7. Escalate only when the router or post-match quality gate indicates the pair is difficult.
8. Build pairwise ControlNets and merge as before.

The reference command shape is:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"

bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir /tmp/pipe_test2_adaptive_route_realdata_20260527/balanced \
  --original-list /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/original_images.lis \
  --dom-list /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/doms.lis \
  --config /tmp/pipe_test2_deep_parallel_controlnet_20260526/pipe_test2_official_lightglue_config.json \
  --parameter-profile balanced \
  --matcher-method flann \
  --adaptive-routing \
  --adaptive-routing-profile balanced
```

For quick validation where final merge is not needed, add `--skip-final-merge`, then run the generated merge script separately if the pairwise results look good.

## Routing Policy

The initial policy should use existing behavior rather than new thresholds:

- `flann` remains the fast path for rich texture and small lighting difference.
- Deep matcher escalation is reserved for sparse texture, larger lighting difference, or a failed post-match quality gate.
- The `balanced` profile is the default release candidate because it avoids over-escalation on `pipe_test2`.
- `strict` can be used for quality-sensitive experiments, but it is not the first production recommendation.
- `fast` can be used for throughput sweeps, but it should not be the first release default until compared against `balanced`.

The route summary must remain visible in each image-match result JSON:

- selected initial matcher,
- selected final matcher,
- route reason,
- pair texture sparseness,
- lighting difference score,
- quality gate profile and thresholds.

## Evidence From `pipe_test2`

The adaptive run used real LRO data and completed successfully with six image pairs.

Stage timing:

- `image_overlap`: 1 second.
- `image_match_batch`: 37 seconds.
- `pairwise_controlnets`: 16 seconds.
- merge script generation: 0 seconds.
- final `cnetmerge` run separately: 21.28 seconds.

Pair routing summary:

| Pair | Points | Initial -> Final | Texture Sparseness | Lighting Difference |
|---|---:|---|---:|---:|
| M104311715LE - M104311715RE | 222 | flann -> flann | 0.149 | 0.0011 |
| M104311715LE - M104318871LE | 18,889 | flann -> flann | 0.149 | 0.0057 |
| M104311715LE - M104318871RE | 570 | flann -> flann | 0.149 | 0.0067 |
| M104311715RE - M104318871LE | 253 | flann -> flann | 0.137 | 0.0046 |
| M104311715RE - M104318871RE | 22,691 | flann -> flann | 0.132 | 0.0056 |
| M104318871LE - M104318871RE | 190 | flann -> flann | 0.137 | 0.0010 |

The routing explanation for all six pairs was effectively the same: rich texture and small lighting difference, so SIFT descriptor matching was selected first and retained as the final matcher.

## Release Candidate Scope

The next release candidate should include:

- A documented recommended adaptive fast command.
- A short performance comparison table:
  - classic `SIFT+FLANN` without adaptive routing,
  - `SIFT+FLANN` with adaptive routing,
  - `SIFT+LightGlue` as a quality-reference deep matcher.
- A report of route decisions and final control point counts on `pipe_test2`.
- Clear guidance that deep matchers are not the default speed path on CPU.
- A known limitation note for sandboxed multiprocessing: local `multiprocessing.Manager()` sockets may require running outside restricted sandboxes.

The release candidate should not claim general performance across all LRO datasets until at least one harder, sparse-texture or high-lighting-difference case is tested.

## Implementation Strategy

No immediate behavior change is required to prove the release candidate. The first implementation plan should focus on packaging the workflow:

1. Add or update an experiment script for the adaptive fast pipeline.
2. Add a concise README section or release note with the real-data command and expected outputs.
3. Add a small summary extractor that reports route decisions, timings, and final control point counts from an output directory.
4. Run focused unit tests around adaptive routing and pipeline forwarding.
5. Re-run the real `pipe_test2` adaptive command and the comparison commands.

Only after this evidence is stable should the project consider changing any default profile or default matcher choices.

## Testing

Focused tests:

- `tests.unitTest.image_match_adaptive_routing_unit_test`
- `tests.unitTest.controlnet_construct_pipeline_unit_test`
- `tests.unitTest.controlnet_construct_matching_unit_test`

Real-data checks:

- `pipe_test2` adaptive `SIFT+FLANN` run with `balanced`.
- final `cnetmerge` execution from the generated merge script.
- summary extraction from:
  - `reports/pipeline_timing.json`,
  - `match_results/*.json`,
  - `reports/controlnet_batch_summary.json`,
  - `merge/dom_matching_merged.net`.

Success criteria:

- Pipeline exits successfully.
- Every pair result contains adaptive routing diagnostics.
- Route decisions are explainable from texture and lighting scores.
- The merged ControlNet is generated.
- Runtime remains in the minute-level range on `pipe_test2`.
- Final control point count is recorded and compared to the non-adaptive baseline.

## Open Follow-Ups

- Add a harder real-data case that forces at least one escalation to a deep matcher.
- Re-test with CUDA when a working 4090 runtime is available.
- Decide whether `balanced` or `fast` should become the recommended production profile.
- Consider pair-level parallelism after the adaptive fast path is documented.
- Consider reducing visualization overhead for high-throughput production runs.
