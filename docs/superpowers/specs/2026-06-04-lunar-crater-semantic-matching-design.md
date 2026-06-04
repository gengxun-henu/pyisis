# Lunar Crater Semantic Matching Design

## Goal

Design a minimum viable matching pipeline for lunar south-pole NAC DOM imagery that improves crater correspondence under heavy shadow and terrain distortion by combining:

- DEM-derived geometric constraints for coarse localization.
- Crater-centered semantic matching instead of raw pixel-only matching.
- Local crater topology as the primary matching signal.
- Terrain consistency as a constraint and re-scoring signal.

The first version targets partially overlapping image regions where crater ellipse detections, NAC DOM imagery, and DEM-derived products are already available.

## Decision Summary

The design fixes the matching strategy to:

```text
DEM coarse constraint -> crater graph candidate generation -> terrain re-scoring -> global consistency selection
```

Signal priority is:

```text
topology > shape > terrain
```

Where:

- **Topology** is the main matching backbone.
- **Shape** is a node-level prior.
- **Terrain** is used for disambiguation, rejection, and confidence adjustment.

Line-drawn crater ellipse images may still be used as a baseline, but they are not the primary architecture because they suppress too much asymmetric crater detail and amplify structural repetition.

## Non-Goals

- Do not train a new multimodal LoFTR, SuperPoint, or LightGlue model in the first version.
- Do not solve online crater detection in the first version.
- Do not require global lunar-scale retrieval or search.
- Do not require perfect graph isomorphism or one-to-one complete crater correspondence.
- Do not treat ellipse raster images plus SuperPoint/LightGlue as the production architecture.

## Rationale

The south-polar NAC matching problem is dominated by three failure sources:

1. large shadowed regions that remove or invert local appearance;
2. repeated crater structure that makes single-object matching ambiguous;
3. terrain-driven geometric distortion that broad appearance matchers do not model explicitly.

Pure local-feature matching on crater line drawings is attractive as a fast experiment, but it is not a strong semantic representation. Converting crater detections into binary or grayscale ellipse maps removes:

- rim sharpness variation;
- shadow occupancy cues;
- local asymmetry;
- neighborhood structure encoded by relative crater arrangement.

The design instead treats each crater as a structured object embedded in a locally constrained geometric neighborhood.

## Inputs and Preconditions

The pipeline assumes the following inputs exist for each overlapping region:

- `NAC DOM` image tiles or subregions.
- `DEM` and at least one DEM-derived rendering such as hillshade or shadow render.
- crater ellipse detections with center, major axis, minor axis, orientation, and detection confidence.

Optional but preferred inputs:

- local crater-centered image patches from NAC DOM;
- local DEM statistics around each crater;
- shadow coverage or shadow ratio per crater neighborhood.

Data quality may vary by region. The design therefore requires every downstream score to be confidence-aware and tolerant of missing or weak evidence.

## Data Flow

### Stage A: DEM Geometric Constraint Layer

Use NAC DOM and DEM-derived renderings to establish coarse local geometric consistency before crater semantic matching.

Preferred outputs of this stage:

- a local search window for each crater or crater neighborhood;
- an approximate scale range;
- an approximate orientation prior if the coarse alignment supports it;
- a per-region coarse alignment confidence.

This stage narrows the candidate space. It is not required to produce final crater correspondences.

```text
NAC DOM + DEM render/hillshade/shadow -> coarse local alignment -> candidate window constraints
```

### Stage B: Crater Semantic Matching Layer

Within the Stage A search window, match crater objects instead of raw pixel points.

Each crater becomes a graph node with attached semantic and geometric attributes. Nearby craters form attributed edges. Matching is performed over local crater constellations rather than isolated ellipses.

```text
crater nodes + local topology + terrain attributes -> local candidate scores -> graph consistency refinement
```

### Stage C: Global Consistency Selection

After local scoring, perform a global consistency pass that selects a compatible subset of crater correspondences while allowing:

- missing detections;
- partial overlap;
- asymmetric neighborhood availability.

This final stage should output both accepted matches and rejection evidence so downstream control-network or bundle-adjustment steps can inspect why a correspondence was retained or removed.

## Module Shape

The first implementation should be split into five focused modules.

### 1. DEM Constraint Module

Responsibilities:

- ingest NAC DOM and DEM-derived products;
- estimate coarse local alignment or local geometric compatibility;
- emit candidate search windows and local prior metadata.

Outputs:

- `search_window`
- `scale_prior`
- `orientation_prior`
- `coarse_alignment_confidence`

### 2. Crater Object Encoding Module

Responsibilities:

- normalize crater detections into node objects;
- attach node-level semantic features and confidence.

Recommended node attributes:

- crater center;
- major/minor axis lengths;
- orientation;
- ellipse-fit or detector confidence;
- rim sharpness or contour residual if available;
- shadow ratio in a local support region;
- local patch embedding from NAC DOM if available;
- local DEM summary such as height, slope, or relief statistics.

### 3. Local Topology Graph Module

Responsibilities:

- build a local crater neighborhood graph around each crater or cluster;
- encode neighbor relationships for matching.

Recommended edge attributes:

- center distance;
- relative bearing;
- scale ratio;
- overlap or nested relation;
- local height difference;
- neighborhood consistency statistics.

The first version should prefer local K-nearest-neighbor graphs or radius-limited graphs instead of trying to build a fragile global graph over the full region.

### 4. Matching Score Module

Responsibilities:

- generate node-level candidate scores;
- refine them with graph consistency;
- apply terrain-based re-scoring and rejection.

Recommended score form:

```text
total_score = node_prior_score + topology_score + terrain_rescore
```

With fixed role semantics:

- `node_prior_score`: shape and local crater evidence.
- `topology_score`: primary signal from constellation consistency.
- `terrain_rescore`: reject or downweight geometrically implausible matches.

The design intentionally avoids making terrain the dominant signal, because DEM-derived cues help reject ambiguity but do not replace crater identity.

### 5. Global Selection Module

Responsibilities:

- choose a globally compatible subset of matches from local candidates;
- allow partial matching;
- emit final correspondence confidence and rejection reasons.

The exact solver may be Hungarian assignment, graph matching, or another approximate consistency method, but the first version should choose the simplest solver that supports partial matching and explicit confidence outputs.

## Matching Strategy

### Candidate Generation

Candidate generation must be constrained by Stage A. No crater should search the entire target region in the first version.

For each source crater:

1. read its DEM-constrained search window;
2. retrieve target crater candidates within that window;
3. compute node prior scores;
4. keep only the top local candidates for graph refinement.

### Local Graph Refinement

For each provisional node match, compare its local crater neighborhood to the neighborhood of the candidate target crater.

Refinement should reward:

- preserved neighbor ordering;
- similar distance ratios;
- similar angle patterns;
- similar local crater density;
- compatible local terrain relations.

### Terrain Re-Scoring

Terrain cues should not invent matches, but they should suppress implausible ones.

Useful terrain checks include:

- DEM height compatibility;
- slope compatibility;
- local hillshade/shadow compatibility;
- coarse alignment support from Stage A.

### Global Selection

The final pass must preserve:

- one-to-one preference where evidence supports it;
- tolerance for missing craters;
- compatibility with downstream quality filtering.

The output should include confidence, not just a binary match flag.

## Recommended MVP

The MVP is intentionally narrow.

### In Scope

- use existing crater ellipse detections;
- use existing NAC DOM plus DEM-derived renderings;
- build DEM-constrained local crater matching for overlapping regions;
- compare the proposed crater-graph pipeline against a line-drawing baseline;
- produce interpretable score components and rejection metadata.

### Out of Scope

- end-to-end neural retraining;
- online crater detection;
- global place recognition;
- full-planet candidate search;
- highly complex learned graph neural network training.

## Baselines and Experiments

The first evaluation round should include exactly three comparison groups.

### A. Baseline: Ellipse Raster + SuperPoint/LightGlue

Purpose:

- quantify the best simple image-based baseline built from crater line drawings.

Expected outcome:

- useful as a speed/reference baseline;
- likely weaker under repeated crater patterns and symmetric ambiguity.

### B. Shape-Prior Baseline

Purpose:

- test whether single-crater ellipse parameters and local candidate windows are already enough.

Expected outcome:

- stronger than pure line drawing;
- still vulnerable in dense repeated crater fields.

### C. Main Method: DEM Constraint + Crater Graph + Terrain Re-Scoring

Purpose:

- test the full semantic design.

Expected outcome:

- best precision-recall tradeoff under shadow-heavy and topographically ambiguous regions.

## Evaluation Metrics

The design fixes the first-round evaluation metrics to four items:

1. crater match recall;
2. crater match precision or inlier ratio;
3. local graph consistency score;
4. robustness stratified by shadow coverage level.

If needed, a fifth supporting metric may be added later for runtime, but runtime is not a primary success criterion for the MVP.

## Failure Modes and Mitigations

### Repeated Dense Crater Fields

Problem:

- many local craters have similar ellipse parameters.

Mitigation:

- increase dependence on local topology;
- expand neighborhood context before accepting a match.

### Permanent Shadow or Extremely Low Texture

Problem:

- patch-level appearance becomes unreliable.

Mitigation:

- reduce patch embedding influence;
- rely more on topology and DEM-based constraints.

### Unstable Ellipse Fits

Problem:

- crater detector or ellipse fitter quality may vary sharply across regions.

Mitigation:

- carry detector confidence into node prior scores;
- treat low-confidence craters as weak evidence rather than hard anchors.

### Missing Detections or Partial Overlap

Problem:

- not all craters appear on both sides, and some may be missed.

Mitigation:

- require partial-match tolerance in the global selection stage;
- avoid designs that assume exact graph correspondence.

## Interfaces and Outputs

The first implementation should expose explicit intermediate outputs so experiments remain debuggable.

Recommended artifacts:

- per-crater candidate list after DEM constraint;
- per-candidate node prior score;
- per-candidate topology score;
- per-candidate terrain re-score;
- final selected matches;
- rejection reasons for non-selected high-score candidates.

These outputs are required because downstream lunar control-network workflows need to inspect why a crater correspondence was accepted or rejected.

## Implementation Order

The implementation order is fixed to reduce scope drift.

### Step 1

Create the evaluation set and baseline comparisons.

### Step 2

Implement DEM-constrained crater graph candidate generation and matching.

### Step 3

Add terrain re-scoring and failure-mode-specific weighting or gating.

No later-stage neural retraining or model redesign should start before the Step 1-3 pipeline is working and measurable.

## Open Choices Kept Explicit

The design intentionally leaves some low-level implementation choices open as long as they respect the architecture:

- exact coarse alignment method in the DEM constraint stage;
- exact patch embedding extractor;
- exact global selection solver.

These are implementation details. They must not change the architectural commitments:

- topology-first crater semantics;
- DEM-first candidate-space reduction;
- terrain as re-scoring and rejection, not the primary identity signal.

## Acceptance Criteria

The design is successful if the implementation plan built from it can produce an MVP that:

- outperforms the ellipse-raster baseline in shadow-heavy south-polar crater matching;
- yields interpretable match confidence and rejection evidence;
- remains robust under partial overlap and crater-detection quality variation;
- stays narrow enough to implement without retraining new deep models in the first pass.
