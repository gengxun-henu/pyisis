# Anticipated Reviewer Questions and Responses

**Paper:** PyISIS: A Python-Bridged Planetary Photogrammetry Framework with Adaptive Deep Learning Image Matching for Automated Control Network Construction

**Journal:** IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing (JSTARS)

**Prepared:** 2026-05-31

---

## Category 1: Novelty and Contributions

### Q1.1: "The authors claim novelty in SPICE-aware adaptive routing, but how is this fundamentally different from learned scene classifiers used in SLAM systems like CHAMELEON-SLAM?"

**Response:**
Our SPICE-aware routing differs from learned classifiers in three fundamental respects:

1. **No training data requirement**: CHAMELEON-SLAM and similar systems require labeled training datasets (e.g., scene classifications with matching success labels). Such labeled planetary matching datasets do not currently exist at scale. Our approach uses physics-based measurements (solar elevation and azimuth from SPICE kernels) that require no training data.

2. **Geometric precision vs. learned approximation**: SPICE-derived solar geometry provides physically precise measurements (sub-degree accuracy for well-calibrated missions), whereas learned classifiers produce probabilistic approximations that may not capture the full illumination parameter space, especially for extreme conditions not well-represented in training data.

3. **Domain specificity**: Terrestrial SLAM classifiers are trained on Earth scenes with atmospheric scattering that softens shadows. Airless bodies like the Moon exhibit fundamentally different illumination characteristics (hard-edged shadows, permanent shadow regions) that terrestrial classifiers cannot capture without planetary-specific training.

We have clarified this distinction in Section II-C (Table I) and Section I-B of the revised manuscript.

---

### Q1.2: "Why not simply use AutoCNet, which is already a USGS-supported Python library for planetary control networks?"

**Response:**
AutoCNet is an excellent tool that addresses automation needs, but it has architectural limitations that PyISIS overcomes:

1. **Subprocess overhead**: AutoCNet operates through subprocess calls to ISIS applications, introducing serialization overhead for every operation. PyISIS provides direct pybind11 API access, eliminating this overhead and enabling tight integration with Python scientific computing libraries.

2. **No deep learning integration**: AutoCNet employs classical feature matching methods (SIFT, area-based matching via ISIS autoseed). It does not integrate deep learning matchers (SuperGlue, LightGlue, LoFTR) that have demonstrated superior robustness under challenging conditions.

3. **No adaptive routing**: AutoCNet uses a single matching strategy throughout processing. Our adaptive routing system automatically selects the optimal method based on image characteristics, with cascade fallback for robustness.

4. **No illumination-aware method selection**: AutoCNet does not leverage SPICE-derived solar geometry for matching strategy selection. Our system exploits mission metadata that is already embedded in planetary image labels.

We acknowledge that a quantitative head-to-head comparison is planned for future work (Section VIII-F), as AutoCNet's different algorithmic choices (area-based matching) require careful experimental design for fair comparison.

---

## Category 2: Methodology and Technical Soundness

### Q2.1: "The texture sparseness metric uses SIFT keypoint density (weight 0.45) while the routing system decides whether to invoke SIFT. Isn't this circular?"

**Response:**
We acknowledge this circular dependency and discuss it explicitly in Section V-F. We mitigate it through:

1. **Low-cost preview pass**: The SIFT density computation uses only 500 features with a relaxed contrast threshold (0.04), requiring <5% of the full matching computation.

2. **Independent signals**: Gradient magnitude and GLCM contrast together carry 55% of the weight and are method-agnostic texture descriptors.

3. **Empirical validation**: Our sensitivity analysis (Section V-J) shows that the cascade fallback mechanism compensates for any routing errors caused by this circularity.

We have added a discussion of future work to replace the SIFT density component with fully method-agnostic descriptors (LBP entropy, frequency-domain energy) to eliminate this dependency entirely (Section VIII-E, Limitation 5).

---

### Q2.2: "How were the routing thresholds (0.35, 0.65, 0.20, 0.55) determined? Are they robust across different instruments?"

**Response:**
The thresholds were determined through grid search optimization on the six LRO NAC test pairs (Section V-I):

1. **Optimization process**: For each candidate threshold combination, we ran the full adaptive routing pipeline and computed the mean composite quality score Q across successfully matched pairs, with penalties for configurations that failed to match any pair.

2. **Sensitivity analysis**: We perturbed each threshold by ±0.10 and observed routing decision changes (Section V-J, Table V). The cascade fallback mechanism compensated for all routing changes, demonstrating robustness to threshold perturbations.

3. **Generalization limitation**: We acknowledge that these thresholds were optimized for LRO NAC and may not generalize to other instruments without re-optimization (Section VIII-E, Limitation 2). Ongoing work extends the evaluation to MRO HiRISE/CTX and Kaguya TC with 30+ pairs per instrument to establish instrument-specific parameter profiles.

---

### Q2.3: "The evaluation covers only 6 image pairs from a single instrument. Is this sufficient to validate the framework?"

**Response:**
We acknowledge this limitation explicitly (Section VIII-E, Limitation 1). The six-pair evaluation demonstrates end-to-end functionality and the cascade fallback mechanism's effectiveness, but limits generalization claims. We address this through:

1. **Diverse test conditions**: The six pairs span different terrain types (cratered highlands, smooth mare) and illumination conditions (same-orbit and cross-track geometries), covering the routing decision space (Section VII-E).

2. **Sensitivity analysis**: Section V-J demonstrates robustness to threshold perturbations within the test dataset.

3. **Ongoing multi-instrument validation**: We are extending the evaluation to MRO HiRISE/CTX (Mars) and Kaguya TC (Moon) with 30+ pairs per instrument (Section VIII-F, Future Work 1).

4. **Architecture extensibility**: The framework's instrument-agnostic design (50+ mission camera models) enables straightforward extension to other datasets without architectural changes.

---

### Q2.4: "Where is the ground truth validation? How do we know the generated control points are geometrically accurate?"

**Response:**
We acknowledge this critical limitation (Section VIII-D) and are conducting ground truth validation:

1. **Current metrics**: We report internal quality metrics (inlier count, ratio, coverage, reprojection residual) that measure self-consistency but not absolute geometric accuracy.

2. **Ongoing validation**: We are conducting:
   - Manual tie point measurement on a subset of test pairs by trained analysts
   - Bundle adjustment convergence analysis using ISIS jigsaw
   - Comparison of DTM quality from adaptively-matched vs. manually-measured networks

3. **Planned publication**: This ground truth evaluation will be reported in a future publication once complete.

We agree that rigorous ground truth validation is essential and have made this a priority in our future work (Section VIII-F, Future Work 2).

---

## Category 3: Experimental Design and Results

### Q3.1: "Why not compare against recent dense matching methods like RoMa or DKM that achieve >95% inlier ratios on satellite imagery?"

**Response:**
We focused on sparse/semi-dense methods (SIFT, LightGlue, LoFTR) for practical reasons:

1. **Computational cost**: Dense methods like RoMa and DKM require significantly more GPU memory (>12 GB for 2048×2048 tiles) and computation time (>30s per tile), making them impractical for our 6-pair campaign with thousands of tiles.

2. **Control network requirements**: Planetary control networks typically use sparse tie points (hundreds to thousands per image pair) rather than pixel-dense correspondences. Sparse methods align better with this requirement.

3. **Cascade design**: Our cascade (SIFT → LightGlue → LoFTR) covers the spectrum from fast/classical to robust/learned, with LoFTR providing semi-dense correspondences as a middle ground.

We acknowledge dense matching as future work (Section VIII-F) and note that EfficientLoFTR [15] offers a promising balance between accuracy and efficiency.

---

### Q3.2: "The paper reports 121,856 control points, but what percentage of tiles actually produced matches? Is 29% success rate acceptable?"

**Response:**
The 29% tile success rate (611 matched tiles out of 2,128 total tiles) reflects the challenging nature of planetary imagery:

1. **Tile validity prefilter**: 19% of tiles were rejected upfront due to insufficient valid pixel coverage (<5%), primarily border regions and data gaps.

2. **Homogeneous terrain**: 55% of valid tiles produced insufficient matches due to genuinely featureless terrain (smooth mare plains, dust-covered regions) where even LoFTR struggles.

3. **Quality gating**: We use strict quality thresholds (Balanced profile: min 24 inliers, 0.35 ratio, 0.20 coverage) to ensure only reliable matches enter the control network.

4. **Absolute numbers**: 121,856 high-quality control points from 6 pairs is a substantial result, sufficient for bundle adjustment and DTM generation.

We argue that quality > quantity for control network construction, and the adaptive routing system maximizes success across diverse conditions rather than forcing matches on inherently unmatchable terrain.

---

### Q3.3: "The computational cost analysis shows adaptive routing is 2.5× more expensive than single-method baselines. Is this overhead justified?"

**Response:**
The computational overhead is justified by improved robustness (Section VIII-C):

1. **Completion rate**: Adaptive routing successfully completed all 6 pairs, whereas single-method baselines failed on 1-2 pairs each (Table IX). Manual intervention to rescue failed pairs is far more expensive than additional GPU compute.

2. **Selective overhead**: The 2.5× cost applies only to pairs requiring cascade escalation. Pairs where SIFT succeeded without fallback matched the single-method cost.

3. **Routing overhead**: The texture/lighting analysis adds only 8-12 seconds per pair (3% of total time), a small price for intelligent method selection.

4. **Automated processing**: For large-scale campaigns (hundreds of pairs), the adaptive system eliminates manual method selection and rescue efforts, providing net time savings despite per-pair overhead.

---

## Category 4: Related Work and Positioning

### Q4.1: "How does this compare to Wang et al. 2025 [28], which also addresses LRO NAC control network construction and was published in JSTARS?"

**Response:**
We have cited and positioned our work relative to Wang et al. [28] in Section II-A:

1. **Different focus**: Wang et al. address the matching refinement stage using DEM-shaded LOLA renders as intermediate references to improve tie point accuracy. Our work focuses on the initial matching stage with adaptive routing and cascade fallback.

2. **Complementary approaches**: The two methods are complementary. DEM-shaded refinement could serve as a post-processing step following our adaptive matching pipeline to further improve tie point quality.

3. **Different contributions**: Wang et al. contribute terrain-aware matching refinement; we contribute SPICE-aware adaptive routing with multi-method cascade fallback and comprehensive Python bindings.

We have clarified this positioning in the revised manuscript.

---

### Q4.2: "Why not use the official USGS Python bindings (isis/python_bindings) instead of creating PyISIS?"

**Response:**
We acknowledge the official in-tree Python binding effort (Section II-A):

1. **Timing**: PyISIS development began before the official effort was publicly visible.

2. **Breadth**: PyISIS currently covers 200+ classes across 7 modules, providing comprehensive functionality for photogrammetric workflows.

3. **Application focus**: PyISIS includes higher-level applications (adaptive routing, control network construction) beyond raw API bindings.

4. **Complementary efforts**: Both efforts validate community demand for Python-native ISIS access. We welcome collaboration and potential convergence of these efforts.

---

## Category 5: Reproducibility and Open Science

### Q5.1: "Is the code and data publicly available? How can other researchers reproduce these results?"

**Response:**
We are committed to reproducibility (Section VIII-G):

1. **Open-source code**: PyISIS is available at [repository URL to be added] under MIT license.

2. **Documentation**: Comprehensive documentation, example workflows, and API references are provided.

3. **Reproducible logs**: All experimental parameters, random seeds, and processing logs are archived (see supplementary material: reproducible_experiment_logs.md).

4. **DOI archive**: A permanent DOI-assigned archive (Zenodo) is in preparation for long-term preservation.

5. **Container support**: Docker/Singularity containers will be provided for reproducible deployment (Section VIII-F, Future Work 5).

---

### Q5.2: "The paper mentions 17 matching presets but doesn't detail all of them. Can you provide a complete specification?"

**Response:**
We provide the complete preset specification in Table II (Section IV-D) and supplementary material:

1. **Table II**: Lists all 17 presets organized by category (Classic SIFT, LightGlue Legacy/Official, LoFTR, SuperGlue).

2. **Supplementary material**: `matching_preset_specifications.json` provides complete parameter specifications for each preset (matcher architecture, feature extractor, model weights, device configuration, matching parameters).

3. **Validation**: Presets are validated at load time to ensure all dependencies are available.

---

## Summary of Key Revisions Made

In response to anticipated reviewer concerns, we have:

1. **Strengthened novelty claims**: Added explicit "first to leverage mission-specific ephemeris metadata" statement (Section I-B) and comparison table (Table I).

2. **Cited Wang et al. 2025**: Positioned as complementary work in Section II-A.

3. **Added design rationale**: Explained threshold and weight choices in Section V-I.

4. **Expanded limitations**: Added 2 new limitations (SPICE dependency, coordinate transformation error propagation) and expanded existing ones (Section VIII-E).

5. **Added broader impacts**: Discussed implications for Artemis, Mars Sample Return, and planetary science community (Section VIII-G).

6. **Provided supplementary materials**: BibTeX file, reproducible experiment logs, matching preset specifications.

---

**Note:** This document anticipates common reviewer questions based on the manuscript's content and the JSTARS review standards. Actual reviewer comments may differ, and responses should be tailored to specific feedback received.
