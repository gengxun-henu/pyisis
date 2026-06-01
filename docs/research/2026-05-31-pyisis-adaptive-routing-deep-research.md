# Deep Research Brief: PyISIS Adaptive Routing for Image Matching and ControlNet Construction

Created: 2026-05-31

## Stage

Academic Research Suite workflow: `deep-research`, Phase 1-3 compact brief.

This document is a research and experiment scoping artifact for the existing PyISIS / ControlNet codebase. It is not an implementation patch and does not claim new experimental results.

## Research Question Brief

### Primary Research Question

How can PyISIS use ISIS camera/SPICE geometry, image texture diagnostics, and adaptive matcher routing to improve automated planetary ControlNet construction across SIFT, LightGlue, and LoFTR methods without weakening reproducibility or existing wrapper semantics?

### FINER Assessment

| Criterion | Score | Justification |
| --- | ---: | --- |
| Feasible | 5/5 | The repo already contains PyISIS bindings, DOM matching, raw-image matching, adaptive routing helpers, deep-match presets, manifest export/import, and matcher-comparison runners. |
| Interesting | 5/5 | The problem is operationally real: no single matcher dominates planetary image pairs with different texture, overlap, illumination, and compute constraints. |
| Novel | 4/5 | SIFT, LightGlue, LoFTR, and AutoCNet exist, but a PyISIS-centered router using planetary sensor metadata and ControlNet-quality gates is a specific contribution. |
| Ethical | 5/5 | The work is non-human-subjects image-processing research; main risks are reproducibility, overstated claims, and unclear dependency provenance. |
| Relevant | 5/5 | The output directly affects LRO NAC and broader planetary mapping workflows, especially automated tie-point generation before ISIS bundle adjustment. |
| Average | 4.8/5 | Strong candidate for a methods paper plus reproducible engineering artifact. |

### Scope Boundaries

In scope:

- PyISIS as a Python bridge to ISIS camera, SPICE, ControlNet, and cube access.
- Automated pair matching for DOM-space and original-image-space ControlNet construction.
- Classical SIFT BF/FLANN baseline, official LightGlue sparse deep matching, and external official LoFTR detector-free matching.
- Adaptive routing signals: texture sparseness, lighting difference, route confidence, fallback cascade, and post-match quality gates.
- End-to-end evaluation on real pipeline outputs: per-pair key files, pairwise ControlNets, merged ControlNets, runtime, failure modes, and jigsaw-readiness.

Out of scope for the first paper/experiment slice:

- Training new deep networks.
- Replacing ISIS bundle adjustment or ControlNet file semantics.
- Broad deletion of legacy matcher presets before callers and tests are inventoried.
- Claiming LoFTR official-runtime confidence without validating the real `deep-learning` environment and checkpoint/import paths.

### Sub-questions

1. Which pair-level diagnostics best predict whether SIFT/FLANN, LightGlue, or LoFTR should run first for planetary stereo pairs?
2. Does adaptive routing improve ControlNet construction success, quality, or runtime compared with fixed matcher strategies?
3. How should PyISIS expose ISIS geometry and ControlNet operations so deep-learning matchers remain reproducible and environment-isolated?

## Methodology Blueprint

### Paradigm

Pragmatist, mixed-method engineering research. The main claim should be judged by reproducible pipeline outcomes, not by matcher novelty alone.

### Data Strategy

- Use real LRO NAC stereo-pair lists already supported by the pipeline, including pipe-test-style runs.
- Preserve the current wrapper semantics: one work directory per method or adaptive profile; report JSON/CSV/MD outputs; keep generated pair-level sidecars.
- Use production `ISISDATA` for real data experiments; mock `ISISDATA` is only valid for import/unit smoke checks.

### Experimental Conditions

Recommended minimum fixed-method baselines:

- `classic_sift_flann`
- `classic_sift_bf`
- `lightglue_official_superpoint`
- `lightglue_official_disk`
- `lightglue_official_aliked`
- `lightglue_official_doghardnet`
- `lightglue_official_sift`
- `loftr_external_outdoor`

Recommended adaptive conditions:

- adaptive routing with `fast`, `balanced`, and `strict` quality profiles
- ablation A: texture-only routing
- ablation B: lighting-only routing
- ablation C: route selection without cascade fallback
- ablation D: fixed first route with cascade fallback

### Outcome Measures

Pipeline-level:

- completed pairs, failed pairs, skipped pairs
- generated match count, RANSAC inlier count, inlier ratio
- spatial coverage of accepted matches
- pairwise ControlNet point/measure counts
- merged ControlNet point/measure counts
- downstream jigsaw acceptability where a real jigsaw run is available

Quality-gate metrics:

- residual mean and P95
- route decision, route confidence, fallback attempts
- accepted final matcher
- rejection reasons

Compute metrics:

- wall time per pair and per method
- CPU/GPU environment used
- memory pressure or OOM failures
- manifest export/import overhead for deep methods

### Validity Criteria

| Risk | Control |
| --- | --- |
| Dataset cherry-picking | Predefine pair lists and include easy, moderate, sparse-texture, and high-lighting-difference cases. |
| Wrapper drift | Run through existing wrappers, not isolated matcher microbenchmarks only. |
| Dependency confounding | Record conda env, preset file, git commit, checkpoint path, and device in every report. |
| Overclaiming deep methods | Separate Kornia-compatible LoFTR from external official LoFTR in text, presets, and results. |
| Routing threshold overfit | Report profile thresholds, run ablations, and avoid tuning on the final evaluation set. |

## Evidence Matrix

### Planetary ControlNet Context

- ISIS control networks represent common ground points and image-space measures, and ISIS supports binary protobuf and PVL control-network formats. This anchors PyISIS outputs to ISIS semantics rather than a custom graph format.
- ISIS `autoseed`, `pointreg`, and `jigsaw` are the established control-network path; `jigsaw` performs bundle adjustment after images and a control network have been prepared.
- AutoCNet is the closest prior Python system: it supports sparse multi-image correspondence identification for planetary data and subsequent bundle adjustment, but PyISIS can argue a different contribution through direct ISIS C++ binding coverage and deep-learning integration.

### Matching Method Literature

- SIFT remains the required classical baseline because it is scale and rotation robust and still performs well on texture-rich, similar-lighting pairs.
- SuperGlue showed that learned graph matching can jointly match sparse local features and reject non-matchable points.
- LightGlue is the best sparse deep matcher default for this pipeline because its adaptive inference is explicitly designed to spend less computation on easier pairs while preserving strong matching quality.
- LoFTR is the correct hard-case fallback because it is detector-free and can produce matches in low-texture areas where keypoint detectors struggle.

### Repo-Specific Evidence

- The current DOM path already has adaptive routing helpers, route confidence, quality profiles, sidecar writing, and cascade planning in `examples/image_match/adaptive_routing.py`.
- `examples/controlnet_construct/deep_match_config.py` is the authoritative deep preset validation and rehydration layer.
- `examples/learning_methods/run_deep_match_manifest.py` is the environment-isolated deep matcher executor and should remain the bridge between `asp360_new` and `deep-learning`.
- Raw original-image routing should reuse the same routing contract but compute diagnostics from original cubes rather than DOM previews.

## Recommended Research Claim Shape

Strong claim:

PyISIS enables a reproducible Python-native planetary photogrammetry workflow that keeps ISIS ControlNet semantics while allowing adaptive, evidence-driven selection among classical and deep image matchers.

Defensible adaptive-routing claim:

Adaptive routing should be framed as a robust orchestration layer. It selects cheaper classical matching when diagnostics predict success, escalates to LightGlue for moderate difficulty, and reserves LoFTR for sparse-texture or large-lighting-difference cases.

Avoid until verified:

- "LoFTR always outperforms SIFT/LightGlue."
- "Adaptive routing is globally optimal."
- "External official LoFTR is fully production-ready" unless the real `deep-learning` environment, external repository, and checkpoints are validated on the target machine.

## Implementation and Experiment Roadmap

### Slice 1: Paper-ready baseline inventory

1. Freeze the matcher/preset matrix from current code.
2. Record environment split: `asp360_new` for ISIS/PyISIS and ControlNet prep/import; `deep-learning` for real deep matcher execution.
3. Run wrapper-level dry runs for fixed methods and adaptive profiles.
4. Confirm report schemas contain route, fallback, quality, and ControlNet metrics.

### Slice 2: Adaptive DOM experiment

1. Run `classic_sift_flann` fixed baseline.
2. Run official LightGlue fixed baselines.
3. Run external LoFTR fixed baseline.
4. Run adaptive `fast`, `balanced`, and `strict`.
5. Summarize pair-level wins/losses by texture sparseness and lighting difference.

### Slice 3: Raw original-image extension

1. Keep default raw behavior as classic FLANN when adaptive routing is disabled.
2. Add opt-in raw adaptive diagnostics from original cubes.
3. Forward raw adaptive matcher decisions through `from-ori-match`.
4. Mirror DOM sidecar shape so reports compare DOM and raw runs directly.

### Slice 4: Paper revision

1. Replace draft-only numeric claims with generated experiment tables.
2. Separate evidence into fixed-method, adaptive, and ablation sections.
3. Add a reproducibility appendix with exact commands, env vars, preset JSON files, and output schema.

## Search Strategy

Databases and sources:

- Web of Science / IEEE / CVF Open Access / arXiv for feature matching papers.
- USGS Astrogeology documentation for ISIS, ControlNet, jigsaw, and AutoCNet.
- Official GitHub or package documentation for LightGlue, SuperGlue, Kornia/LoFTR, and repo-specific runtime behavior.

Keywords:

- `planetary photogrammetry control network ISIS jigsaw`
- `AutoCNet sparse multi-image correspondence planetary`
- `SIFT image matching Lowe 2004`
- `SuperGlue graph neural network feature matching`
- `LightGlue local feature matching adaptive inference`
- `LoFTR detector-free low texture local feature matching`
- `adaptive feature matching image registration remote sensing`

Inclusion criteria:

- Primary papers, official documentation, or authoritative project pages.
- Direct relevance to control networks, feature matching, deep local matching, or planetary photogrammetry.
- Methods that can be mapped to current repo runtime or planned extension.

Exclusion criteria:

- Generic image-matching blog posts unless used only for non-cited orientation.
- Claims about runtime support that are not reflected in current repo code.

## Sources to Cite in Paper Draft

- Lowe, D. G. (2004). Distinctive Image Features from Scale-Invariant Keypoints. International Journal of Computer Vision.
- Sarlin, P.-E., DeTone, D., Malisiewicz, T., & Rabinovich, A. (2020). SuperGlue: Learning Feature Matching with Graph Neural Networks. CVPR.
- Lindenberger, P., Sarlin, P.-E., & Pollefeys, M. (2023). LightGlue: Local Feature Matching at Light Speed.
- Sun, J., Shen, Z., Wang, Y., Bao, H., & Zhou, X. (2021). LoFTR: Detector-Free Local Feature Matching with Transformers. CVPR.
- Laura, J. R., Rodriguez, K., Paquette, A., & Dunn, E. (2018). AutoCNet: A Python library for sparse multi-image correspondence identification for planetary data. SoftwareX.
- USGS Astrogeology Software Docs: ISIS Control Networks, Image Registration, Bundle Adjustment in ISIS, `autoseed`, and `jigsaw`.

## Immediate Next Step

Run a small, wrapper-level experiment that compares `classic_sift_flann` against adaptive `balanced` on the same pair list, then inspect whether every pair report records:

- texture sparseness summary
- lighting difference summary
- initial route
- final route
- fallback attempts
- quality-gate result
- pairwise ControlNet point/measure counts

That is the smallest useful gate before widening to all deep methods.
