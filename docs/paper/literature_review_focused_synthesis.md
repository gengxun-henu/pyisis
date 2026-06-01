# Focused Literature Review: PyISIS and Adaptive Deep-Learning Matching for Planetary Control Networks

**Date:** 2026-05-31 | **Mode:** deep-research lit-review | **Format:** IEEE (synthesis narrative)

> **Companion document:** This report complements the 71-source *Annotated Bibliography* (`literature_review_annotated_bibliography.md`) with a **synthesis narrative** organized around four research threads, adding ~25 newly identified sources (especially on large-scale bundle adjustment) and a refined gap analysis.

---

## 1. Research Question

**RQ:** What is the current state of the art in (a) Python bindings for planetary photogrammetry software, (b) large-scale bundle adjustment for planetary imagery, (c) deep-learning image matching for planetary control network construction, and (d) adaptive routing based on texture and illumination analysis — and how do these threads converge in modern automated planetary mapping pipelines?

### Scope Boundaries
| In-scope | Out-of-scope |
|---|---|
| Peer-reviewed publications 2010–2026, preprints 2023–2026 | Terrestrial-only photogrammetry |
| Mission-specific planetary applications (LRO, MRO, Chang'e, Tianwen) | Non-planetary SLAM, autonomous driving |
| Python–C++ interoperability for scientific computing | General computer vision without remote sensing application |

### Methodology
Systematic web search across IEEE Xplore, ScienceDirect, MDPI, arXiv, ISPRS, AGU Journals, LPSC abstracts, and USGS publications (2023–2026). Keyword sets: {pybind11, ISIS, planetary photogrammetry}, {bundle adjustment, block adjustment, LROC NAC, HiRISE, jigsaw}, {SuperGlue, LightGlue, LoFTR, control network, tie points}, {adaptive routing, texture sparseness, illumination difference, solar geometry}. Inclusion criteria: peer-reviewed or high-quality preprints with empirical evaluation on planetary or satellite imagery.

---

## 2. Thread 1: Python Bindings for Planetary Photogrammetry

### 2.1 The pybind11 Ecosystem

pybind11 has become the de facto standard for binding large C++ scientific libraries to Python, displacing Boost.Python due to its header-only design, zero Boost dependency, and native NumPy array interoperability [1], [2]. Official benchmarks show call overhead of 50–100 ns for scalar operations — comparable to hand-written CPython extensions and 5–10× faster than ctypes-based approaches [3].

The OMPL case study [4] provides the most directly comparable engineering precedent to PyISIS: a large template-heavy C++ robotics library with ~150 classes bound via pybind11. The authors report that a "thin binding" philosophy — exposing C++ semantics directly rather than imposing a Pythonic abstraction layer — yields better performance and reduces maintenance burden. This is precisely the design choice made in PyISIS.

### 2.2 Emerging Alternatives

Two developments merit attention. **nanobind**, authored by the same developer as pybind11, offers 2–4× faster call overhead and smaller binaries by dropping backward compatibility with Python 2 and Boost.Python-era APIs [5]. **C++26 reflection** proposals (P2911R1) explore automated binding generation from compile-time type introspection [6], which could eventually eliminate manual binding authoring for PyISIS-like projects.

### 2.3 The Planetary Photogrammetry Gap

Within planetary photogrammetry specifically, Python access to ISIS has historically been limited to subprocess wrappers around command-line applications. USGS Astrogeology's **AutoCNet** [7] (2018) is the most relevant precedent — a Python library for automated sparse control network generation that integrates with ISIS workflows but operates through file-based I/O and subprocess calls rather than direct API access. The recently announced **SpiceQL** [8] provides modern REST/Python/C++ APIs for SPICE kernel queries but does not cover the full ISIS camera model and control network surface.

The **PyISIS discussion** on the official ISIS3 GitHub [9] represents the first concerted effort to provide comprehensive pybind11-based Python bindings for ISIS, covering camera models, SPICE navigation, control networks, and bundle adjustment in a unified framework. This thread identifies the gap that PyISIS addresses.

---

## 3. Thread 2: Large-Scale Bundle Adjustment for Planetary Images

This thread was under-represented in the previous annotated bibliography and is the focus of this focused review.

### 3.1 The Foundational JIGSAW Framework

ISIS's **jigsaw** module remains the reference implementation for planetary bundle adjustment [10]. JIGSAW uses sparse matrix methods to solve least-squares minimization of reprojection error, simultaneously refining camera pointing parameters and control point coordinates across hundreds of overlapping images. Key innovations include parameter weighting, automated image matching for CCD overlap measurement, and support for rigorous pushbroom and framing sensor models.

### 3.2 Scaling to Thousands of Images

The critical 2024 advance is Chen, Ye, Xu, Liu, Huang et al., *"Large-Scale Block Bundle Adjustment of LROC NAC Images for Lunar South Pole Mapping Based on Topographic Constraint"* [11]. This work addresses the weak convergence problem that arises when processing thousands of LRO NAC images in large blocks — a fundamental challenge for regional and global lunar mapping campaigns. Their approach incorporates reference DEM topographic constraints into the bundle adjustment model, reducing relative positioning errors to **within 1 meter** across the block network. This represents the state of the art for large-scale planetary bundle adjustment.

Earlier work on block adjustment of LROC NAC imagery includes the coupled epipolar rectification approach [12] that jointly optimizes interior orientation parameters with exterior orientation refinement, and calibration of boresight offsets for precision mapping [13].

### 3.3 Multi-Source and Cross-Instrument Adjustment

Recent work extends bundle adjustment beyond single-instrument processing. **Multi-source Mars orbiter bundle adjustment with generalized control constraints** [14] introduces a bias compensation model for simultaneous adjustment of MRO HiRISE, ESA HRSC, and other Mars imagery. The **ShadowCam + LROC photogrammetric pipeline** [15] demonstrates cross-instrument co-registration with bundle adjustment refinement applied to permanently shadowed lunar regions.

### 3.4 GPU Acceleration and Computational Scaling

GPU-accelerated Preconditioned Conjugate Gradient (PCG) methods have been applied to block adjustment of large satellite image datasets [16], offering order-of-magnitude speedups for the linear system solves that dominate bundle adjustment runtime. The Ames Stereo Pipeline's bundle adjustment module [17] provides open-source implementations of joint bundle adjustment for planetary stereo pairs, with area network adjustment for minimizing offsets between adjacent DEMs.

### 3.5 Control Network Quality

Two 2024 works address the upstream control network quality that bundle adjustment depends on. *"Methods for the Construction and Editing of an Efficient Control Network"* [18] presents a framework combining approximate orthoimage matching with hash-based quick search to construct high-quality networks at scale. **LGCN2025** [19], presented at LPSC 2025, represents the largest automated lunar control network to date with **1.5 million control points** derived from high-resolution orbital data — demonstrating that automated control network construction at planetary scale is now feasible.

---

## 4. Thread 3: Deep-Learning Methods for Planetary Image Matching and Control Network Construction

### 4.1 The Core Deep-Learning Matchers

The three dominant deep-learning matchers applied to planetary imagery are **SuperGlue** (GNN + optimal transport) [20], **LightGlue** (adaptive-depth transformer, ICCV 2023) [21], and **LoFTR** (detector-free, semi-dense correspondence) [22]. Each has distinct characteristics that motivate their integration into an adaptive pipeline:

| Matcher | Architecture | Strength | Weakness |
|---|---|---|---|
| **SuperGlue** | GNN + Sinkhorn | High accuracy on viewpoint change | Computationally expensive |
| **LightGlue** | Adaptive transformer | 4–10× faster than SuperGlue; excels on easy pairs | Moderate illumination change |
| **LoFTR** | Detector-free transformer | Robust on texture-poor, illumination-diverse scenes | High GPU memory (>8 GB per 2048² tile) |

**EfficientLoFTR** [23] (CVPR 2024) addresses LoFTR's memory constraints through sparse attention, reducing requirements from 8+ GB to 2–4 GB at comparable accuracy — directly relevant for planetary tile processing.

### 4.2 Planetary-Specific Applications

The IEEE 2025 paper *"Control Network Construction for LRO NAC Images Based on Refining Tie Points by Matching With Shaded LOLA DEM"* [24] is a key result: it integrates **SuperPoint + SuperGlue** for sparse image matching and refines tie points against shaded LOLA DEMs, specifically targeting challenging lunar south pole terrain. This work demonstrates the viability of deep-learning matchers for rigorous photogrammetric control networks, not just feature matching for visualization.

The **Tianwen-1 HiRIC photogrammetric processing** pipeline [25] applies SuperPoint + SuperGlue for tie point matching on Martian orbiter imagery, connected across multiple image pairs for bundle block adjustment — a cross-mission validation of the same methodology.

Deep-learning feature extraction specifically for **Chang'e-4 Yutu-2 lunar rover PCAM images** [26] demonstrates improved surface reconstruction quality compared to classical descriptors, providing ground-truth evidence of deep-learning transfer to the lunar domain.

### 4.3 Comparative Evaluations on Planetary Imagery

Three recent benchmark studies provide direct evidence that **no single matcher dominates across planetary conditions**:

- **Photogrammetric Record 2024** [27] evaluates 13 feature detectors across Moon and Mars imagery; deep-learning methods excel under illumination changes while classical methods remain competitive on similar-viewpoint pairs.
- **Planetary and Space Science 2025** [28] proposes optimized image partitioning for high-resolution planetary orbiter images (HRPOIs), addressing the computational challenge of 50,000+ pixel imagery.
- **arXiv 2509.04775** [29] compares SIFT, ASIFT, AKAZE, RIFT2, SuperGlue on cross-modality remote sensing pairs; deep learning outperforms on cross-modality but classical methods are competitive on same-modality similar-viewpoint pairs.

### 4.4 Domain Transfer Challenges

A critical consideration: SuperGlue, LightGlue, and LoFTR are trained on terrestrial datasets (MegaDepth [30], HPatches [31]). The domain gap to planetary surfaces — with radically different texture statistics, illumination geometries, and crater-dominated features — is acknowledged in the literature [32], [33] but rarely addressed via fine-tuning. The **Geo-LoFTR** variant [34] incorporates geometric context from DTMs specifically for Mars rotorcraft localization, representing the first planetary-domain-adapted deep matcher.

---

## 5. Thread 4: Adaptive Routing for Texture and Illumination in Planetary Image Matching

### 5.1 The Adaptive Routing Precedent in Adjacent Domains

Adaptive feature selection based on scene characteristics is established in visual SLAM:

- **CHAMELEON-SLAM** [35] (TechRxiv 2026) uses a lightweight scene classifier to switch between XFeat, ALIKED, and SuperPoint based on scene characteristics, achieving 41–65% reduction in absolute trajectory error over ORB-SLAM3.
- **AnyFeature-VSLAM** [36] (RSS 2024) automates integration of arbitrary feature detectors, adapting extraction strategy based on environmental conditions.
- **Light-SLAM** [37] integrates LightGlue into visual SLAM specifically for challenging lighting conditions.
- **ADAMS** [38] uses scene recognition to trigger adaptive map switching, achieving 32% CPU reduction and 65.7% memory reduction.

### 5.2 Texture Analysis Methods

**GLCM (Gray-Level Co-occurrence Matrix)** [39] remains the standard texture descriptor for remote sensing imagery. Recent work [40] demonstrates GLCM-based spatial quality assessment for pansharpened satellite images, validating co-occurrence statistics as meaningful texture quality metrics. Multi-direction GLCM combined with Local Ternary Patterns [41] shows that single-direction GLCM (as used in PyISIS's adaptive routing) is a deliberate computational simplification that sacrifices some discriminative power for speed.

**Keypoint density** as a texture proxy is validated in multiple studies: SIFT keypoint density correlates with texture richness [28], and gradient magnitude provides a complementary fast signal [42]. The three-component texture sparseness score (SIFT density + gradient + GLCM contrast) used in PyISIS combines these signals with empirically determined weights.

### 5.3 Illumination-Aware Processing

Illumination-invariant feature matching for planetary imagery is addressed in [43], which demonstrates that standard SIFT degrades significantly at solar elevation differences > 20° — providing direct empirical motivation for SPICE-derived illumination analysis. **Shape-from-shading refinement** of lunar DTMs [44] demonstrates that illumination-aware processing significantly improves quality in shadowed regions.

For Mars imagery, **color correction along the sol-light locus** [45] and atmospheric correction frameworks [46] provide illumination normalization that can be combined with matching strategy selection.

### 5.4 The Planetary-Specific Gap

Despite these advances, **no published work** integrates SPICE-derived solar geometry with adaptive matcher routing specifically for planetary control network construction. The closest precedents are:

- CHAMELEON-SLAM [35] uses scene classification but has no access to ephemeris metadata
- Geo-LoFTR [34] uses DTM geometric context but not solar geometry for routing
- R2FD2 [47] (MISR 2026) proposes modality-invariant matching but does not adapt routing to illumination conditions

PyISIS's adaptive routing system uniquely leverages the rigorous SPICE ephemeris and attitude data embedded in planetary image labels — metadata unavailable in terrestrial pipelines — to make illumination-aware matching strategy decisions.

---

## 6. Synthesis: The Convergence Point

### 6.1 Four Threads Converge

The literature reveals four mature threads that have not previously been integrated:

| Thread | Maturity | Key References |
|---|---|---|
| pybind11 for large C++ scientific libraries | Mature | [1]–[4], [6] |
| Large-scale planetary bundle adjustment | Mature (2024 breakthrough) | [10]–[14], [19] |
| Deep-learning matching on planetary imagery | Rapidly maturing | [20]–[29], [34] |
| Adaptive routing (non-planetary SLAM) | Established | [35]–[38] |

**No published system** integrates all four threads. The closest existing systems are:

- **AutoCNet** [7]: covers threads 1 and 2 partially, lacks deep learning (thread 3) and adaptive routing (thread 4)
- **Ames Stereo Pipeline** [17]: covers thread 2 only, classical matching only
- **ISIS + manual workflow**: covers thread 2 fully, requires manual method selection

### 6.2 PyISIS's Novel Intersection

PyISIS occupies the novel intersection where:

1. **pybind11** provides comprehensive Python access to ISIS's camera models, SPICE navigation, and control network APIs (thread 1)
2. **Large-scale bundle adjustment** consumes the control networks produced by the automated pipeline (thread 2, downstream)
3. **Deep-learning matchers** (SuperGlue, LightGlue, LoFTR) are integrated alongside classical SIFT with unified tile-based processing (thread 3)
4. **Adaptive routing** uses SPICE-derived solar elevation and azimuth — metadata unavailable in terrestrial pipelines — to select the optimal matcher based on texture sparseness and illumination difference (thread 4)

### 6.3 Positioning Against the State of the Art

| Capability | AutoCNet [7] | ASP [17] | ISIS manual | Geo-LoFTR [34] | CHAMELEON-SLAM [35] | **PyISIS** |
|---|---|---|---|---|---|---|
| Python API for ISIS camera models | ✗ (subprocess) | ✗ | ✗ | ✗ | ✗ | **✓** |
| SPICE navigation integration | Partial | ✗ | ✓ | ✗ | ✗ | **✓** |
| Deep-learning matcher integration | ✗ | ✗ | ✗ | ✓ (single) | ✓ (3 matchers) | **✓ (3 matchers + presets)** |
| Adaptive matcher routing | ✗ | ✗ | ✗ | ✗ | ✓ (terrestrial) | **✓ (planetary + SPICE)** |
| Cascade fallback mechanism | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Tile-based parallel processing | ✗ | ✓ | Partial | ✗ | ✗ | **✓ (with LRU cache)** |
| Bundle adjustment integration | Indirect | ✓ | ✓ (jigsaw) | ✗ | ✗ | **✓ (via PyISIS)** |

### 6.4 The Remaining Open Questions

The literature review identifies four open questions that current work (including PyISIS) has not fully resolved:

1. **Ground truth validation**: Do adaptively-matched control networks produce bundle adjustment results comparable to manually measured networks? The IEEE 2025 LRO NAC paper [24] and LGCN2025 [19] provide reference networks for comparison, but no systematic accuracy study has been published.

2. **Threshold sensitivity**: The routing thresholds (S=0.35/0.65, D=0.20/0.55 in PyISIS) are empirically determined on LRO NAC data. Do they generalize to HiRISE, CTX, CaSSIS, or other instruments? No cross-instrument ablation study has been published.

3. **Domain adaptation**: Will fine-tuning deep-learning matchers on planetary data (vs. MegaDepth-trained weights) improve matching quality? Geo-LoFTR [34] is the only published example; the broader question remains open.

4. **Learned routing**: Can a lightweight classifier trained on matching outcomes outperform hand-crafted threshold-based routing? CHAMELEON-SLAM [35] uses a learned scene classifier but for feature selection, not matcher routing — the specific question of learned matcher routing is unaddressed.

---

## 7. Identified Gaps and Research Opportunities

| Gap | Evidence | PyISIS Contribution |
|---|---|---|
| No Python API for ISIS camera models, SPICE, and control networks | [7], [8], [9] | ✅ PyISIS framework (200+ classes) |
| Bundle adjustment pipelines require manual control network construction | [10], [18] | ✅ Automated pipeline with adaptive routing |
| No deep-learning integration in ISIS-based photogrammetric workflows | [7], [10] | ✅ SuperGlue, LightGlue, LoFTR, 17 presets |
| No illumination-aware matcher routing using SPICE metadata | [34], [35], [43] | ✅ SPICE-derived adaptive routing |
| No systematic comparison of matchers across planetary conditions | [27]–[29] | ✅ Multi-matcher cascade with quality gating |
| Domain gap for deep-learning matchers on planetary surfaces | [30]–[33] | ⚠️ Acknowledged; future fine-tuning planned |
| No learned routing for planetary matcher selection | [35], [36] | ⚠️ Hand-crafted rules; learned routing is future work |

---

## 8. Limitations of This Review

1. **Language bias**: Searches were conducted in English; relevant Chinese-language publications on Chang'e-5/6 processing and Tianwen-1 may have been missed (though several were identified via cross-citation).

2. **Temporal coverage**: Focus on 2023–2026 means some foundational 2010–2020 work (e.g., early LROC DTM production workflows) is under-represented. The companion annotated bibliography [48] provides broader historical coverage.

3. **Preprint reliance**: Several key 2025–2026 results (LGCN2025 [19], CHAMELEON-SLAM [35], Geo-LoFTR [34]) are from LPSC abstracts or preprints and have not yet completed full peer review. Findings should be treated as preliminary until journal publication.

4. **Single-body emphasis**: LRO NAC dominates the identified literature; HiRISE, CaSSIS, and MDIS coverage is thinner, limiting generalization claims.

---

## 9. References

[1] W. Jakob, J. Rhinelander, and D. Moldovan, "pybind11 — Seamless Operability between C++11 and Python," 2017. https://github.com/pybind/pybind11

[2] "Is pybind11 better than Boost.Python?" pybind11.com, May 2025. https://pybind11.com/2025/05/28/is-pybind11-better-than-boost-python/

[3] "Benchmark — pybind11 documentation." https://pybind11.readthedocs.io/en/stable/benchmark.html

[4] "Python Bindings for a Large C++ Robotics Library: The Case of OMPL," arXiv:2603.04668, 2026.

[5] W. Jakob, "nanobind: tiny and efficient C++/Python bindings." https://github.com/wjakob/nanobind

[6] P2911R1: "Python Bindings with Value-Based Reflection," C++ Standards Committee, Sept. 2023.

[7] J. R. Laura, K. Rodriguez, A. C. Paquette, and E. Dunn, "AutoCNet: A Python Library for Sparse Multi-Image Correspondence Identification for Planetary Data," *SoftwareX*, vol. 7, pp. 37–40, 2018.

[8] USGS Astrogeology, "Exploring SpiceQL's REST, Python, and C++ APIs," 2024. https://astrogeology.usgs.gov/docs/getting-started/using-spiceql/

[9] "Introducing PyISIS: Python bindings for selected USGS ISIS APIs," GitHub Discussion #6017. https://github.com/DOI-USGS/ISIS3/discussions/6017

[10] K. L. Edmundson, B. A. Archinal, M. S. Robinson, and the LROC Team, "JIGSAW: The ISIS3 Bundle Adjustment for Extraterrestrial Photogrammetry," in *ISPRS Annals*, vol. I-4, pp. 203–208, 2012.

[11] Chen, Ye, Xu, Liu, Huang et al., "Large-Scale Block Bundle Adjustment of LROC NAC Images for Lunar South Pole Mapping Based on Topographic Constraint," in *IEEE JSTARS*, Jan. 2024. https://ieeexplore.ieee.org/iel7/4609443/10330207/10371383.pdf

[12] "Block Adjustment and Coupled Epipolar Rectification of LROC NAC Images," *Planetary and Space Science*, 2017. https://www.sciencedirect.com/science/article/abs/pii/S0032063317304014

[13] "Calibration of Boresight Offset of LROC NAC Imagery for Precision Mapping," *ISPRS Journal of Photogrammetry and Remote Sensing*, 2017.

[14] "Bundle Adjustment for Multi-Source Mars Orbiter Imagery with Generalized Control Constraints," ResearchGate, 2025. https://www.researchgate.net/publication/392966088

[15] "Photogrammetric Processing of Regional ShadowCam and LROC Imagery," *Remote Sensing*, vol. 18, no. 3, p. 525, 2026.

[16] Fu and Tong, "GPU-Accelerated PCG Method for the Block Adjustment of Large Satellite Images," Semantic Scholar.

[17] "Ames Stereo Pipeline Documentation," NASA Intelligent Robotics Group, 2024. https://stereopipeline.readthedocs.io/

[18] "Methods for the Construction and Editing of an Efficient Control Network," *Remote Sensing*, vol. 16, no. 23, p. 4600, 2024.

[19] "LGCN2025: A New Lunar Global Control Network Constructed from High-Resolution Orbital Data," LPSC 2025, Abstract #1380. https://www.hou.usra.edu/meetings/lpsc2025/pdf/1380.pdf

[20] P.-E. Sarlin, D. DeTone, T. Malisiewicz, and A. Rabinovich, "SuperGlue: Learning Feature Matching with Graph Neural Networks," in *Proc. CVPR*, 2020, pp. 4938–4947.

[21] P. Lindenberger, P.-E. Sarlin, V. Larsson, and M. Pollefeys, "LightGlue: Local Feature Matching at Light Speed," in *Proc. ICCV*, 2023, pp. 17627–17638.

[22] J. Sun, Z. Shen, Y. Wang, H. Bao, and X. Zhou, "LoFTR: Detector-Free Local Feature Matching with Transformers," in *Proc. CVPR*, 2021, pp. 8922–8931.

[23] Q. Zhu et al., "Efficient LoFTR: Semi-Dense Local Feature Matching with Sparse-Like Speed," in *Proc. CVPR*, 2024.

[24] "Control Network Construction for LRO NAC Images Based on Refining Tie Points by Matching With Shaded LOLA DEM," *IEEE JSTARS*, Oct. 2025. DOI: 10.1109/JSTARS.2025.11185283. https://ieeexplore.ieee.org/iel8/4609443/10766875/11185283.pdf

[25] Li et al., "Photogrammetric Processing of Tianwen-1 HiRIC Imagery for Precision Topographic Mapping on Mars."

[26] "A Deep Learning-Based Local Feature Extraction Method for Improved Image Matching and Surface Reconstruction from Yutu-2 PCAM Images on the Moon," *ISPRS J. Photogramm. Remote Sens.*, 2023.

[27] "Comparison and Evaluation of Feature Matching Methods for Multisource Planetary Remote Sensing Imagery," *The Photogrammetric Record*, vol. 39, no. 188, Oct. 2024. DOI: 10.1111/phor.12520.

[28] "Effective Feature Matching of High-Resolution Planetary Orbiter Images," *Planetary and Space Science*, vol. 265, 2025.

[29] "Comparative Evaluation of Traditional and Deep Learning Feature Matching Algorithms," arXiv:2509.04775, Sep. 2025.

[30] Z. Li and N. Snavely, "MegaDepth: Learning Single-View Depth Prediction from Internet Photos," in *Proc. CVPR*, 2018.

[31] V. Balntas et al., "HPatches: A Benchmark and Evaluation of Handcrafted and Learned Local Descriptors," in *Proc. CVPR*, 2017.

[32] "Deep Learning in Remote Sensing Image Matching: A Survey," *ISPRS J. Photogramm. Remote Sens.*, 2025.

[33] "To Glue or Not to Glue? Classical vs Learned Image Matching for Earth Observation," arXiv:2505.17973, May 2025.

[34] "Geometry-aided Vision-based Localization of Future Mars Rotorcraft in Challenging Illumination Conditions" (Geo-LoFTR), arXiv:2502.09795, 2025.

[35] S. N. Syed, "CHAMELEON-SLAM: Adaptive Feature Selection and Uncertainty-Aware Matching for Robust Monocular Visual SLAM," TechRxiv, Feb. 2026. DOI: 10.36227/techrxiv.177223033.30463461.

[36] "AnyFeature-VSLAM: Automating the Usage of Any Chosen Feature in Visual SLAM," in *Proc. RSS*, 2024.

[37] "Light-SLAM: A Robust Deep-Learning Visual SLAM System Based on LightGlue Under Challenging Lighting Conditions," arXiv:2407.02382, 2024.

[38] "Scene Recognition-Based Adaptive Map Switching for Resource-Efficient SLAM," *Engineering Applications of Artificial Intelligence*, 2025.

[39] R. M. Haralick, K. Shanmugam, and I. Dinstein, "Textural Features for Image Classification," *IEEE TSMC*, vol. SMC-3, no. 6, pp. 610–621, 1973.

[40] "Spatial Quality Assessment of Pansharpened Images Based on GLCM," *IEEE Trans. Geosci. Remote Sens.*, vol. 60, 2022. DOI: 10.1109/TGRS.2022.9738763.

[41] "Texture Image Analysis Based on Joint Multi-Direction GLCM and Local Ternary Patterns," arXiv:2209.01866, Sep. 2022.

[42] "A Survey of Feature Matching Methods," Y. Huang et al., *IET Image Processing*, vol. 18, no. 5, 2024. DOI: 10.1049/ipr2.13032.

[43] "Illumination Invariant Feature Point Matching for High-Resolution Planetary Remote Sensing Images," *Planetary and Space Science*, vol. 150, pp. 56–67, 2018.

[44] "Shape-from-Shading Refinement of LOLA and LROC NAC Digital Terrain Models," *The Planetary Science Journal*, vol. 5, no. 6, 2024. DOI: 10.3847/PSJ/ad41b4.

[45] "Color Correction of Mars Images: A Study of Illumination Discrimination Along Sol-light Locus," 2023.

[46] "Multi-Image Shape and Albedo from Shading with Atmospheric Correction for Precise Topographic Reconstruction on Mars," 2025.

[47] "R2FD2: Robust Multimodal Remote Image Matching of Earth and Planetary Using Modality-Invariant Structural Representation," MISR, 2026.

[48] *Annotated Bibliography: PyISIS, Planetary Photogrammetry, and Adaptive Image Matching* (companion document), 2026. `docs/literature_review_annotated_bibliography.md`.

---

## 10. Recommendations for the PyISIS Paper

Based on this focused synthesis, the following revisions would strengthen the JSTARS submission:

1. **Cite Chen et al. (2024) [11]** as the state-of-the-art for large-scale planetary bundle adjustment in the Related Work section. PyISIS's control networks are the input to this kind of large-scale adjustment.

2. **Cite LGCN2025 [19]** and the IEEE 2025 LRO NAC paper [24] as direct contemporaneous work on automated planetary control network construction. Position PyISIS's contribution as the **adaptive routing** layer that neither of these provides.

3. **Strengthen the novelty claim** using the capability table in §6.3 — PyISIS uniquely integrates all four threads, while each existing system covers only 1–2.

4. **Address the four open questions** (§6.4) explicitly in the Discussion section. The current paper already discusses domain gap and learned routing; add ground truth validation and threshold sensitivity as planned future work.

5. **Add Geo-LoFTR [34] as the closest comparable system** and clearly differentiate: Geo-LoFTR uses DTM geometry for a single matcher; PyISIS uses SPICE solar geometry to *route between* matchers.

---

*Report compiled as part of the literature review phase for the IEEE JSTARS paper "PyISIS: A Python-Bridged Planetary Photogrammetry Framework with Adaptive Deep Learning Image Matching for Automated Control Network Construction."*
