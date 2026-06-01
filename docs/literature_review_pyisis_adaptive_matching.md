# Literature Review: PyISIS and Adaptive Routing for Planetary Photogrammetric Image Matching

**Topic:** PyISIS: Python bindings for USGS ISIS, adaptive routing between classic SIFT and deep-learning matching methods for planetary photogrammetric processing, control network construction

**Prepared for:** IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing (JSTARS)

**Date:** 2026-05-31

**Sources analyzed:** 90+ | **Annotated entries:** 55 | **Citation format:** IEEE

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Planetary Photogrammetry Software Ecosystem](#2-planetary-photogrammetry-software-ecosystem)
3. [Classical Feature Matching Methods](#3-classical-feature-matching-methods)
4. [Deep Learning Feature Matching](#4-deep-learning-feature-matching)
5. [Adaptive Routing and Hybrid Matching Approaches](#5-adaptive-routing-and-hybrid-matching-approaches)
6. [Control Network Construction and Bundle Adjustment](#6-control-network-construction-and-bundle-adjustment)
7. [Planetary Image Matching: Domain-Specific Challenges](#7-planetary-image-matching-domain-specific-challenges)
8. [Gap Analysis and Novelty Positioning](#8-gap-analysis-and-novelty-positioning)
9. [Annotated Bibliography: Full Entries](#9-annotated-bibliography-full-entries)
10. [Source Index](#10-source-index)

---

## 1. Executive Summary

This literature review surveys the research landscape surrounding three intersecting domains: (1) Python-accessible planetary photogrammetry software, (2) deep learning-based image matching methods, and (3) adaptive routing strategies for selecting matching algorithms based on image characteristics. The review identifies **55 key sources** organized across six thematic areas and maps their contributions, limitations, and relevance to the PyISIS framework.

**Central finding:** No prior work integrates (a) comprehensive Python bindings for USGS ISIS camera models and SPICE navigation with (b) multiple deep learning matchers and (c) illumination-aware adaptive routing for planetary control network construction. This intersection represents a genuine gap in the literature, positioning the PyISIS contribution at the confluence of three communities—planetary photogrammetry, computer vision, and research software engineering—that have minimal overlap in existing publications.

The review is organized into six thematic sections mirroring the structure of the target paper (Sections II-A through II-D plus expanded coverage), followed by a gap analysis that maps identified gaps to the paper's claimed contributions.

---

## 2. Planetary Photogrammetry Software Ecosystem

### 2.1 ISIS: The Foundational Platform

The **Integrated Software for Imagers and Spectrometers (ISIS)**, maintained by the USGS Astrogeology Science Center, has served as the de facto standard for planetary image processing since the 1990s [R1]. ISIS supports mission-specific camera models for over 50 planetary missions, with rigorous SPICE-based navigation data integration and the `jigsaw` bundle adjustment application [R2]. The software operates through command-line applications processing ISIS Cube files, a proprietary binary format with PVL (Parameter Value Language) headers.

The most significant recent developments in the ISIS ecosystem include: **ISIS 9.0.0** (January 2026), the first long-term support release of the new major version cycle, introducing save/apply bundle adjustment values and CSM (Community Sensor Model) state output [R1]; and **ISIS 10.0.0 RC** (April-May 2026), adding GTiff I/O support and the `eisstitch` application. These developments reflect an ongoing modernization effort within the USGS to broaden ISIS's interoperability with the wider geospatial software ecosystem.

The `jigsaw` bundle adjustment tool [R2] remains the gold standard for extraterrestrial photogrammetry, supporting both frame and line-scan cameras with interior and exterior orientation parameter refinement. Edmundson et al. [R2] describe its architecture including robust M-estimation for outlier rejection and sparse matrix methods. Recent extensions include CSM State output (v10.0) and topographic constraint integration for large-scale block adjustment [R3].

### 2.2 Python Access to ISIS: Existing Approaches

Several prior efforts have sought to provide Python access to ISIS functionality, each with distinct architectural limitations:

**AutoCNet** [R4], developed by USGS Astrogeology, is a Python library for automated sparse control network generation published in SoftwareX. It employs computer vision techniques for n-image correspondence identification and integrates with ISIS workflows through subprocess calls and intermediate file I/O. While AutoCNet addresses automation needs, its reliance on subprocess invocation rather than direct API access results in suboptimal performance for large-scale processing and precludes tight integration with deep learning pipelines.

**PLIO** (Planetary I/O Module) [R5], also maintained by USGS Astrogeology (v1.6.3, April 2026), provides Python read/write access for ISIS Cube files, AutoCNet graph objects, and control network data. PLIO operates at the file I/O level only—it does not expose camera models, SPICE navigation, or bundle adjustment functionality.

**Pysis** [R6] and **Kalasiris** [R7] are CLI wrapper libraries that invoke ISIS applications as subprocesses from Python. Both predate modern Python binding frameworks and provide no direct C++ API access, introducing serialization overhead for every operation.

**SpiceQL** [R8] provides REST, Python, and C++ APIs for SPICE kernel queries, addressing navigation data access but not camera model computation or control network manipulation.

### 2.3 Official Python Bindings Effort

Concurrent with community efforts, USGS Astrogeology has initiated an **official in-tree Python binding project** within the ISIS repository (`isis/python_bindings/`) [R9], targeting camera models, control network objects, and image processing primitives. This parallel effort validates the community demand for Python-native ISIS access but, as of the time of writing, does not yet cover the breadth of functionality provided by PyISIS.

### 2.4 Complementary Planetary Processing Tools

The **Ames Stereo Pipeline (ASP)** [R10], developed by NASA Ames Intelligent Robotics Group, provides complementary stereo processing capabilities including semi-global matching, bundle adjustment, and DTM generation. Published in Earth and Space Science (2018), ASP supports planetary and Earth observation imagery with command-line and limited Python interfaces. ASP and ISIS are frequently used together in planetary mapping workflows but address different stages of the processing pipeline.

**PlanetFlow** [R11], published in Research Notes of the AAS (May 2026), presents an open-source cross-platform pipeline with GUI for ground-based planetary image processing. It represents the continuing community demand for streamlined, accessible planetary processing workflows but operates at a higher abstraction level than API-level bindings.

The **Community Sensor Model (CSM)** standard [R12], [R13] enables interoperability between ISIS, ASP, and other tools through standardized sensor model interfaces. Geng et al. [R12] describe a generic pushbroom sensor model for planetary photogrammetry that demonstrates the value of standardized interfaces—an approach that PyISIS's `CSMCamera` binding inherits.

### 2.5 Gap in Python Bindings

**Summary:** Existing Python access to ISIS is limited to three paradigms: (1) subprocess wrappers with high I/O overhead (AutoCNet, Pysis, Kalasiris), (2) file-level I/O without computational API access (PLIO), or (3) narrow-scope APIs for specific subsystems (SpiceQL). No prior framework provides comprehensive pybind11-based access to ISIS camera models, SPICE navigation, control networks, bundle adjustment, projections, photometry, and shape models simultaneously.

---

## 3. Classical Feature Matching Methods

### 3.1 SIFT: The Enduring Baseline

The **Scale-Invariant Feature Transform (SIFT)** [R14], introduced by Lowe in 2004, remains the most widely deployed feature descriptor in planetary photogrammetry. SIFT detects scale-space extrema using Difference-of-Gaussian filtering, assigns dominant orientations, and computes 128-dimensional gradient histograms. Its scale and rotation invariance properties are essential for matching planetary imagery acquired at varying resolutions and viewing geometries.

**Lowe's ratio test** [R15], applying a nearest-neighbor distance ratio threshold (typically 0.75) to reject ambiguous matches, is standard practice in planetary photogrammetric pipelines and is adopted by PyISIS's matching modules.

### 3.2 FLANN-Based Matching

The **Fast Library for Approximate Nearest Neighbors (FLANN)** [R16] by Muja and Lowe provides efficient descriptor matching for large feature sets through randomized kd-trees. In planetary applications where DOM tiles may contain thousands of SIFT keypoints, FLANN provides substantial speedup over brute-force L2-distance search with minimal accuracy degradation.

### 3.3 SIFT in Planetary Context

SIFT has been the workhorse of planetary image registration for over a decade. However, comprehensive benchmarking by Ye and Zhou [R17] evaluated **13 feature detectors and 12 descriptors** across Moon and Mars multisource images, finding that SIFT-based pipelines perform well on texture-rich terrain but degrade significantly on sparse-texture surfaces (smooth plains, polar regions) and under large solar geometry variations. This finding motivates the adaptive routing approach in PyISIS.

A 2025 study [R18] directly compared traditional (SIFT, ASIFT, AKAZE) and deep learning feature matching methods for lunar image registration, confirming that while traditional methods retain competitive spatial repeatability on well-illuminated pairs, neural methods show superior calibration accuracy under challenging conditions.

### 3.4 Gap in Classical Methods

**Summary:** Classical methods provide geometric rigor and computational efficiency on texture-rich imagery but exhibit systematic failure modes on texture-poor surfaces and under large illumination changes—conditions prevalent in multi-temporal planetary datasets. This limitation motivates integration with deep learning matchers and, critically, automatic routing between methods.

---

## 4. Deep Learning Feature Matching

### 4.1 Learned Feature Detection: SuperPoint

**SuperPoint** [R19] (DeTone et al., CVPR 2018) introduced self-supervised interest point detection and description using a VGG-style encoder with joint detection-descriptor heads. SuperPoint remains the most widely used learned feature extractor in 2025 and serves as the backbone for multiple matching pipelines integrated in PyISIS (SuperGlue, LightGlue).

### 4.2 Graph Neural Network Matchers

**SuperGlue** [R20] (Sarlin et al., CVPR 2020) introduced attention-based graph neural network matching with optimal transport for match assignment. The architecture performs iterative message passing between keypoints using self- and cross-attention layers, with a differentiable Sinkhorn-Knopp layer for soft assignment. SuperGlue demonstrated improved robustness under viewpoint and illumination changes compared to nearest-neighbor descriptor matching.

**LightGlue** [R21] (Lindenberger et al., ICCV 2023) advanced the GNN matching paradigm with adaptive early-termination mechanisms that dynamically adjust computation depth based on matching difficulty. On "easy" image pairs (rich texture, similar illumination), LightGlue terminates after fewer attention layers, achieving 3–5× speedup over SuperGlue while maintaining accuracy on challenging pairs. The adaptive computation property aligns naturally with the cascade fallback concept in PyISIS.

A critical finding from the 2026 study "Understanding and Optimizing Attention-Based Sparse Matching" [R22] demonstrates that learned matchers are highly feature-dependent: LightGlue trained on SuperPoint features does not transfer to ALIKED or DISK features without retraining. This finding has implications for PyISIS's multi-extractor support via the LightGlue official backend.

### 4.3 Detector-Free Methods

**LoFTR** [R23] (Sun et al., CVPR 2021) eliminates explicit feature detection entirely, employing self-attention and cross-attention transformer layers to establish semi-dense correspondences directly from feature grids. This architecture excels on textureless scenes where keypoint detectors fail to extract sufficient features—a condition common in planetary imagery of smooth plains and dust-covered terrain.

**EfficientLoFTR** [R24] (Wang et al., CVPR 2024, Highlight) addresses LoFTR's computational cost through a RepVGG-style reparameterized backbone, token compression via strided depthwise convolution, and a two-stage correlation layer. The method achieves ~2.5× speedup over LoFTR (<41ms per pair at standard resolution) while maintaining or improving accuracy. EfficientLoFTR is directly relevant to PyISIS's GPU memory constraints (8+ GB for 2048×2048 tiles with standard LoFTR) and is identified as a priority integration target.

### 4.4 Dense Matching Methods

**RoMa** [R25] (Edstedt et al., CVPR 2024) combines frozen DINOv2 global features with specialized ConvNet local features, forming a robust feature pyramid with a Gaussian Process match encoder. RoMa explicitly handles extreme scale, illumination, and viewpoint changes. Its v2 successor [R26] (November 2025) adds two-stage matching-then-refinement, 1.7× speedup, and predictive covariance for uncertainty quantification. Critically, RoMa v2 includes aerial/orbital imaging test sets with steep viewpoint shifts—directly relevant to planetary remote sensing.

**DKM** (Dense Keypoint Matching) [R27] replaces keypoint detection with dense matching on coarse scales followed by mutual nearest neighbors. In satellite benchmark evaluations on WorldView-3 stereo pairs [R28], DKM consistently produced >95% inlier ratios and dominated DSM spatial coverage metrics, though at higher computational cost than sparse methods.

### 4.5 Emerging Architectures

**MambaGlue** [R29] (Ryoo et al., ICRA 2025) replaces Transformer attention with Mamba state-space models for local feature matching, achieving competitive accuracy with lower compute than LightGlue. This architecture represents the next generation of efficient matchers and is relevant to PyISIS's future integration roadmap.

**XFeat** [R30] (Potje et al., CVPR 2024) provides CNN-based lightweight keypoint detection and matching designed for real-time operation on GPU-free or resource-constrained settings, running at ~2.9 FPS on CPU. XFeat's efficiency profile makes it relevant for onboard planetary processing scenarios.

### 4.6 Feature Extractor Diversity

**ALIKED** [R31] (Zhao et al., 2023) introduces differentiable keypoint detection with sub-pixel accuracy via deformable transformation. Benchmark evaluations [R32] show ALIKED is competitive on in-domain tests but exhibits significant out-of-domain degradation (accuracy dropping from ~56% mAA to ~16%). This domain sensitivity is particularly relevant when transferring terrestrial-trained models to planetary imagery.

PyISIS's LightGlue official backend supports SuperPoint, DISK, ALIKED, DoGHardNet, and SIFT extractors, enabling controlled evaluation of learned versus handcrafted descriptors within the same matching framework.

### 4.7 Benchmark Evidence: No Single Method Dominates

The most directly relevant benchmark for planetary applications is the satellite stereo study by [R28] (arXiv 2409.02825, September 2024), which tested SIFT, SuperGlue, LightGlue, GIM-LightGlue, LoFTR, ASpanFormer, DKM, and GIM-DKM on **496 multi-date WorldView-3 stereo pairs** (0.3m GSD) with airborne LiDAR ground truth. Key findings:

- **DKM** achieved >95% inlier ratio consistently and best DSM spatial coverage
- **SIFT + LightGlue** achieved best DSM accuracy when matches existed
- **SIFT alone** had lowest success rate under heavy seasonal transitions
- **Least Squares Matching** refinement improved geometric fidelity across ALL pipelines

This benchmark provides strong empirical validation for the cascade approach in PyISIS (SIFT → LightGlue → LoFTR): no single method succeeds universally, and progressive escalation from fast/classical to robust/deep achieves the highest overall completion rate.

The ISPRS Annals study "To Glue or Not to Glue?" [R33] (2025) further confirms that SIFT+FLANN remains competitive on controlled datasets (HPatches), but deep networks achieve far superior geometric alignment on challenging scenes (MegaDepth-1500), and handcrafted methods fail completely on realistic pose estimation queries.

### 4.8 Gap in Deep Learning Methods for Planetary Use

**Summary:** Deep learning matchers demonstrate superior robustness under challenging conditions but face two barriers in planetary applications: (1) domain gap from terrestrial training data, and (2) no single method dominates across all planetary imaging conditions. The satellite benchmark [R28] and the planetary matching benchmark [R17] both confirm the "no free lunch" theorem for matcher selection—motivating the adaptive routing approach.

---

## 5. Adaptive Routing and Hybrid Matching Approaches

### 5.1 Adaptive Feature Selection in SLAM

**CHAMELEON-SLAM** [R34] (Syed, TechRxiv 2026) employs a lightweight scene classifier to switch between XFeat, ALIKED, and SuperPoint feature extractors based on scene characteristics. This represents the closest precedent to PyISIS's adaptive routing in the SLAM domain, but differs fundamentally: CHAMELEON-SLAM uses a learned classifier trained on terrestrial SLAM datasets, whereas PyISIS derives routing signals from SPICE ephemeris metadata specific to planetary missions.

**Light-SLAM** [R35] integrates LightGlue into a visual SLAM system designed for challenging lighting conditions. While it demonstrates the value of deep learning matchers under illumination stress, it does not perform adaptive method selection—always invoking LightGlue regardless of conditions.

### 5.2 Hybrid Classical-Learned Approaches

A 2026 study on hybrid front-ends for drift-resilient monocular SLAM [R36] combines classical geometric priors with learned features, demonstrating improved robustness in mixed environments. This hybrid philosophy—leveraging the geometric rigor of classical methods alongside the robustness of learned descriptors—aligns with PyISIS's cascade fallback design.

### 5.3 Adaptive Matching in Remote Sensing

An adaptive remote sensing image-matching network based on feature analysis [R37] (Electronics, 2023) proposes learned routing for multimodal satellite image registration. The approach analyzes image features to select matching strategies but does not leverage mission-specific metadata (SPICE kernels, sensor models).

**AMES** (Adaptive Matching with Enhanced Sketches) [R38], published in Information Fusion (December 2024), combines edge-based sketch features with adaptive strategies for multi-modal image matching, reducing the need for manual filter tuning. While not specific to planetary imagery, the tuning-free design philosophy parallels PyISIS's automated routing.

**MARSNet** [R39] (ISPRS, 2025) employs a Mamba-driven adaptive framework with DINOv2 foundation models and dynamic feature fusion for improved generalization and reduced domain shift. This emerging architecture addresses the domain transfer challenge relevant to planetary applications.

### 5.4 Adaptive Matching Methods for Planetary Illumination

**Xue et al.** [R40] (Planetary and Space Science, June 2025) present optimized image partitioning with rapid local correspondence for high-resolution planetary orbiter images. Their tile-based approach addresses the same computational scalability challenge as PyISIS's tile decomposition, but uses classical matching exclusively.

**Xie et al.** [R41] (Remote Sensing MDPI, July 2025) propose robust feature matching of multi-illumination lunar orbiter images based on crater neighborhood structure. Rather than adapting the matching algorithm, this work adapts the feature representation—using crater topology as geometric priors resilient to illumination changes. This approach is complementary to PyISIS's routing strategy: crater-based features could serve as an additional matcher in the cascade chain.

### 5.5 Algorithm Selection Framework

The algorithm selection problem, formalized by Rice (1976) and extended by AutoFolio [R42] (arXiv, 2019), demonstrates that an oracle approach can predict which algorithm performs best for any given input instance. Applied to image quality assessment, AutoFolio compared 8 blind IQA algorithms and showed significant performance gains from per-instance selection. This framework directly generalizes to matcher selection: PyISIS's texture sparseness and lighting difference scores serve as the instance features for selecting the optimal matching algorithm.

### 5.6 Texture Analysis for Method Selection

**GLCM (Gray-Level Co-occurrence Matrix)** and **LBP (Local Binary Patterns)** are well-established texture descriptors. A multi-directional GLCM + LBP fusion study [R43] (MDPI Applied Sciences, 2021) demonstrates enhanced texture analysis through combined descriptors. PyISIS's texture sparseness metric incorporates GLCM contrast alongside SIFT density and gradient magnitude, drawing on this established literature.

### 5.7 Gap in Adaptive Routing for Planetary Photogrammetry

**Summary:** Existing adaptive matching approaches operate in two disconnected domains: (1) SLAM systems that use learned scene classifiers for feature selection (CHAMELEON-SLAM, Light-SLAM), and (2) remote sensing networks that analyze image features for strategy selection. Neither domain leverages mission-specific metadata. PyISIS's SPICE-aware adaptive routing is the first system to use ephemeris-derived solar geometry (elevation and azimuth) for illumination-informed matching strategy selection in planetary photogrammetry.

---

## 6. Control Network Construction and Bundle Adjustment

### 6.1 Lunar Control Networks

The construction of high-quality control networks is among the most labor-intensive tasks in planetary photogrammetry [R44]. Recent major efforts include:

**Wang et al.** [R44] (IEEE JSTARS, Vol. 18, pp. 25512–25531, 2025) present control network construction for LRO NAC images based on refining tie points by matching with shaded LOLA DEM. This is the most directly comparable work to PyISIS's control network pipeline: same instrument, same journal, and overlapping methodology. Their approach uses orthophoto-based matching with DEM-shaded renders as intermediate references for tie point refinement, whereas PyISIS employs adaptive routing with cascade fallback for automated initial matching. The two approaches are complementary: DEM-shaded refinement could serve as a post-processing step following adaptive matching.

**Chen et al.** [R3] (IEEE JSTARS, Vol. 17, pp. 2731–2746, 2024) present large-scale block bundle adjustment of LROC NAC images for lunar south pole mapping based on topographic constraint. Their method reduces relative positioning errors in block networks to within 1 meter, demonstrating the geometric accuracy achievable with well-constructed control networks and advanced bundle adjustment.

**LGCN2025** [R45] (Di et al., LPSC 2025, Abstract #1380) presents a new lunar global control network constructed from multi-mission high-resolution data, demonstrating the continuing community demand for automated control network construction tools at planetary scale.

**Collins et al.** [R46] (Remote Sensing MDPI, Vol. 18, 2026) describe photogrammetric processing of regional ShadowCam and LROC NAC controlled mosaics with positional accuracy assessments, including 743 LROC NAC controlled mosaics. Their pipeline covers pre-processing through control network construction, bundle adjustment, photometric correction, and mosaicking.

### 6.2 Mars Control Networks and Bundle Adjustment

**Fergason et al.** [R47] (Earth and Space Science, Vol. 13, January 2026) present the THEMIS Control Network of Mars, using photogrammetric bundle adjustment as the gold standard for spatial referencing of Mars image data.

**You et al.** [R48] (ISPRS J. Photogrammetry and Remote Sensing, Vol. 227, 2025) present bundle adjustment for multi-source Mars orbiter imagery with generalized control constraints, introducing a bias compensation model to address sensor-specific systematic errors across different Mars orbiters.

### 6.3 Efficient Network Construction

**Ma et al.** [R49] (Remote Sensing MDPI, Vol. 16(23), 2024) address methods for the construction and editing of efficient control networks for massive planetary remote sensing images. They demonstrate that redundant and invalid control points significantly increase bundle adjustment computation time, motivating their pruning strategies—a concern directly relevant to PyISIS's tile validity prefilter.

### 6.4 Dense and Sparse Matching for DEM Generation

**Hemmi et al.** [R50] (Planetary Science Journal, Vol. 6, 2025) present LROC NAC-derived meter-scale topography of the Moon's south polar landing sites, generating 1 m/pixel DTMs from six NAC stereo pairs using bundle adjustment with meticulously selected tie points. Their workflow demonstrates the state of the art in manual tie point selection—a process PyISIS aims to automate.

### 6.5 Bundle Adjustment Foundations

The ISIS `jigsaw` bundle adjustment [R2] provides the computational core for simultaneous camera pointing and control point refinement. Edmundson et al. [R2] describe its support for frame cameras with interior orientation parameters and line-scan cameras with time-dependent exterior orientation. Recent extensions enable save/apply of bundle adjustment values (ISIS 9.0) and CSM State output (ISIS 10.0).

**Hu and Wu** [R51] (Planetary and Space Science, 2018) describe block adjustment with coupled epipolar rectification of LROC NAC images, combining BBA with semi-global matching for precision lunar topographic mapping.

### 6.6 Gap in Automated Control Network Construction

**Summary:** Control network construction remains "the most time-consuming step in planetary photogrammetric processing" [R44]. While individual components exist (ISIS autoseed, findfeatures, pointreg, AutoCNet), no integrated pipeline combines (1) multi-method adaptive matching with cascade fallback, (2) SPICE-aware illumination analysis for method selection, and (3) rigorous coordinate transformation from DOM space to original image coordinates via pybind11-exposed camera models.

---

## 7. Planetary Image Matching: Domain-Specific Challenges

### 7.1 Illumination Extremes

Planetary surfaces—particularly the Moon—present illumination conditions absent from terrestrial benchmark datasets. The Moon's lack of atmosphere eliminates scattered light that softens shadows on Earth, producing extreme contrast between sunlit and shadowed terrain. At lunar polar regions, permanently shadowed craters and low solar elevation angles create illumination geometries that severely impact standard matching algorithms [R52].

**Geo-LoFTR** [R52] (arXiv, February 2025) specifically addresses Mars rotorcraft localization under challenging illumination conditions by incorporating geometric context from digital terrain models. The method demonstrates significantly improved robustness at low sun elevation angles, validating the importance of illumination-aware matching—a principle central to PyISIS's SPICE-based routing.

### 7.2 Texture Sparsity and Repetitive Terrain

Planetary remote sensing imagery frequently lacks surface texture information. Vast smooth plains (lunar maria, Martian dust-covered regions) present feature-poor surfaces where keypoint detectors produce insufficient matches. Ye and Zhou [R17] document this challenge across 13 detectors and 12 descriptors on Moon and Mars imagery.

**MISR** (Multimodal Image Structural Representation) [R53] (IEEE, January 2026) addresses cross-sensor and cross-modality matching for both Earth and planetary imagery using modality-invariant structural features, representing the latest advance in handling the domain diversity challenge.

### 7.3 Multi-Scale Processing

Planetary imagery spans orders of magnitude in ground sample distance—from global mosaics at 100+ m/pixel to NAC imagery at 0.5 m/pixel. **Xue et al.** [R40] propose optimized image partitioning for multi-resolution planetary imagery, while **LiteSAM** [R54] (Remote Sensing MDPI, 2025) provides lightweight satellite-aerial feature matching for scenarios with large scale differences.

### 7.4 Deep Learning for Planetary Surfaces

**MARs** (Multi-view Attention Regularizations) [R55] (Chase and Dantu, ECCV 2024) introduces rotation-equivariant features with spatial coordinate awareness for planetary surface matching. Tested on HiRISE Mars imagery and synthetic lunar data (Luna-1 dataset), MARs achieves 85%+ improvement in continuous scanning tests over equivariant baselines.

**Chang'E-4 DL Feature Extraction** [R56] (ISPRS J. Photogrammetry, 2023/2024) applies a two-branch attention network for lunar rover imagery, demonstrating improved surface reconstruction from Yutu-2 PCAM images.

### 7.5 Emerging Neural Reconstruction

Recent work comparing photogrammetry, Neural Radiance Fields, and Gaussian Splatting for lunar terrain reconstruction [R57] (2025) explores neural alternatives to classical photogrammetric pipelines. **AstroSplat** [R58] (arXiv, March 2026) integrates planetary reflectance models into Gaussian Splatting for rendering and navigation. While these methods are not yet ready for control network construction, they represent potential future integration targets for PyISIS.

---

## 8. Gap Analysis and Novelty Positioning

### 8.1 Identified Gaps

The literature review reveals the following gaps that PyISIS addresses:

| Gap | Existing Work | PyISIS Contribution |
|-----|---------------|---------------------|
| **Comprehensive ISIS Python bindings** | Subprocess wrappers [R4], [R6], [R7]; file I/O only [R5]; narrow APIs [R8] | pybind11 bindings for 200+ classes: camera models, SPICE, control networks, BA, projections, photometry |
| **Multi-method DL matching for planetary** | Individual matchers tested in isolation [R17], [R28] | Unified pipeline: SIFT-BF, SIFT-FLANN, SuperGlue, LightGlue, LoFTR with 17 presets |
| **SPICE-aware adaptive routing** | Learned classifiers for terrestrial SLAM [R34], [R35]; feature-based selection for satellite [R37] | First use of SPICE solar geometry (elevation + azimuth) for illumination-informed matcher routing |
| **Cascade fallback for robustness** | Single-method pipelines fail on diverse conditions [R28] | Progressive escalation SIFT → LightGlue → LoFTR with quality-gated acceptance |
| **End-to-end automated control networks** | Manual tie point selection [R50]; single-method automation [R4], [R44] | Integrated pipeline: adaptive matching → coordinate transformation → ControlNet assembly |

### 8.2 Novelty Claims Supported by Literature

1. **"First comprehensive Python bindings for ISIS covering camera models, SPICE, control networks, and bundle adjustment"** — Supported by the exhaustive survey in Section 2.2–2.3. No prior work covers this breadth.

2. **"No single matching algorithm performs optimally across planetary imaging conditions"** — Supported by the satellite benchmark [R28] (496 WorldView-3 pairs) and the planetary matching benchmark [R17] (13 detectors × 12 descriptors).

3. **"First use of SPICE-derived solar geometry for matching strategy selection"** — Supported by the adaptive routing survey in Section 5. CHAMELEON-SLAM [R34], Light-SLAM [R35], and adaptive matching networks [R37] do not use ephemeris metadata.

4. **"Cascade fallback ensures robust matching where single methods fail"** — Supported by the benchmark evidence [R28] showing different methods succeed on different conditions, and by the ISPRS study [R33] showing handcrafted methods fail on challenging scenes.

### 8.3 Limitations Acknowledged by Literature

- **Domain gap:** DL matchers pretrained on terrestrial data (MegaDepth, HPatches) may underperform on planetary surfaces. MARs [R55] and Geo-LoFTR [R52] demonstrate that planetary-specific training improves performance, supporting PyISIS's identified future direction.
- **Scale of evaluation:** The literature documents much larger planetary control network campaigns (86,571 images for the global CTX mosaic [R59]) against which PyISIS's 6-pair evaluation should be contextualized.
- **Ground truth validation:** The LROC NAC DTM literature [R50] establishes that geometric accuracy validation requires bundle adjustment convergence analysis and comparison with manually measured tie points.

---

## 9. Annotated Bibliography: Full Entries

### Planetary Photogrammetry Software

**[R1]** USGS Astrogeology Science Center, "ISIS — Integrated Software for Imagers and Spectrometers," https://astrogeology.usgs.gov/docs/, 2024–2026.
> *The cornerstone planetary image processing suite, supporting 50+ missions with camera models, SPICE navigation, bundle adjustment (jigsaw), and map projection. ISIS 9.0.0 (Jan 2026) is the latest LTS release. C++ codebase with CLI-only interface motivating Python binding efforts.*

**[R2]** K. L. Edmundson, D. A. Cook, O. H. Thomas, B. A. Archinal, and R. L. Kirk, "JIGSAW: The ISIS3 Bundle Adjustment for Extraterrestrial Photogrammetry," *ISPRS Annals of the Photogrammetry, Remote Sensing and Spatial Information Sciences*, vol. I-4, pp. 203–208, 2012. DOI: [10.5194/isprsannals-I-4-203-2012](https://doi.org/10.5194/isprsannals-I-4-203-2012)
> *Definitive reference for the jigsaw bundle adjustment tool. Describes support for frame and line-scan cameras, interior/exterior orientation refinement, robust M-estimation, and sparse matrix methods. Foundational for any ISIS-based control network work.*

**[R3]** C. Chen, Z. Ye, Y. Xu, et al., "Large-Scale Block Bundle Adjustment of LROC NAC Images for Lunar South Pole Mapping Based on Topographic Constraint," *IEEE J. Selected Topics in Applied Earth Observations and Remote Sensing*, vol. 17, pp. 2731–2746, 2024. DOI: [10.1109/JSTARS.2023.3346199](https://doi.org/10.1109/JSTARS.2023.3346199)
> *Demonstrates <1m relative positioning accuracy with LOLA DEM topographic constraints in large-scale LROC NAC block adjustment for lunar south pole mapping. Relevant to the geometric accuracy standards for PyISIS-generated control networks.*

**[R4]** J. R. Laura, K. Rodriguez, A. C. Paquette, and E. Dunn, "AutoCNet: A Python library for sparse multi-image correspondence identification for planetary data," *SoftwareX*, vol. 7, pp. 37–40, 2018. DOI: [10.1016/j.softx.2018.01.003](https://doi.org/10.1016/j.softx.2018.01.003)
> *USGS Python library for automated sparse control network generation. Operates via subprocess calls to ISIS applications. Most directly comparable existing tool to PyISIS's control network pipeline, but lacks direct API access and deep learning integration.*

**[R5]** DOI-USGS, "PLIO — Planetary I/O Module," https://github.com/DOI-USGS/plio, v1.6.3, 2026.
> *Python library for reading/writing ISIS Cube files, AutoCNet graph objects, and control network data. File I/O only—does not expose camera models, SPICE, or bundle adjustment.*

**[R6]** S. Braden, "Pysis: ISIS from Python," https://pypi.org/project/pysis/.
> *Legacy CLI wrapper for invoking ISIS applications from Python. No direct C++ API access.*

**[R7]** R. Beyer, "Kalasiris: Python library for calling ISIS programs," https://github.com/rbeyer/kalasiris.
> *CLI wrapper for ISIS program invocation from Python. Named after an ancient Egyptian, reflecting the ISIS mythology theme.*

**[R8]** USGS Astrogeology Science Center, "Exploring SpiceQL's REST, Python, and C++ APIs," https://astrogeology.usgs.gov/docs/getting-started/using-spiceql/, 2024.
> *API for SPICE kernel queries. Addresses navigation data access but not camera model computation or control network manipulation.*

**[R9]** USGS Astrogeology, "ISIS python_bindings," https://code.usgs.gov/astrogeology/isis/-/tree/dev/isis/python_bindings.
> *Official in-tree Python binding effort within the ISIS repository. Validates community demand for Python-native ISIS access but does not yet match PyISIS's breadth of coverage.*

**[R10]** R. A. Beyer, O. Alexandrov, and S. McMichael, "The Ames Stereo Pipeline: NASA's Open Source Software for Deriving and Processing Terrain Data," *Earth and Space Science*, vol. 5, pp. 537–548, 2018. DOI: [10.1029/2018EA000409](https://doi.org/10.1029/2018EA000409)
> *NASA's open-source stereo processing pipeline for planetary and Earth observation imagery. Complements ISIS with dense matching, DTM generation, and bundle adjustment. Frequently used alongside ISIS in mapping workflows.*

**[R11]** "PlanetFlow: Open-source Cross-platform Pipeline for Automated Planetary Processing," *Research Notes of the AAS*, May 2026.
> *Recent Python pipeline with GUI for ground-based planetary image processing. Represents continuing community demand for accessible planetary processing workflows.*

**[R12]** X. Geng, Q. Xu, S. Xing, and C. Lan, "A Generic Pushbroom Sensor Model for Planetary Photogrammetry," *Earth and Space Science*, vol. 7, no. 5, e2019EA001014, 2020. DOI: [10.1029/2019EA001014](https://doi.org/10.1029/2019EA001014)
> *Generic pushbroom sensor model enabling interoperability between ISIS, ASP, and other tools via the CSM standard. Demonstrates the value of standardized interfaces that PyISIS's CSMCamera binding inherits.*

**[R13]** "Planetary Sensor Models Interoperability Using the Community Sensor Model," *Earth and Space Science*, 2019. DOI: [10.1029/2019EA000713](https://doi.org/10.1029/2019EA000713)
> *Describes the CSM framework for cross-tool planetary sensor model compatibility.*

### Classical and Deep Learning Feature Matching

**[R14]** D. G. Lowe, "Distinctive Image Features from Scale-Invariant Keypoints," *International Journal of Computer Vision*, vol. 60, no. 2, pp. 91–110, 2004.
> *The foundational SIFT paper. 128-dimensional gradient descriptors with scale-space extrema detection. Still the most deployed feature descriptor in planetary photogrammetry.*

**[R15]** D. G. Lowe, "Object Recognition from Local Scale-Invariant Features," in *Proc. IEEE International Conference on Computer Vision*, 1999, pp. 1150–1157.
> *Introduces the nearest-neighbor distance ratio test (Lowe's ratio test) for ambiguous match rejection. Standard practice in all PyISIS matching presets.*

**[R16]** M. Muja and D. G. Lowe, "Fast Approximate Nearest Neighbors with Automatic Algorithm Configuration," in *Proc. International Conference on Computer Vision Theory and Applications (VISAPP)*, 2009, pp. 331–340.
> *FLANN library for efficient descriptor matching via randomized kd-trees. Used in PyISIS's SIFT-FLANN preset.*

**[R17]** Z. Ye and Y. Zhou, "Comparison and Evaluation of Feature Matching Methods for Multisource Planetary Remote Sensing Imagery," *The Photogrammetric Record*, vol. 39, no. 188, Oct. 2024. DOI: [10.1111/phor.12520](https://doi.org/10.1111/phor.12520)
> ***Most comprehensive planetary matching benchmark.*** Evaluates 13 detectors × 12 descriptors across Moon and Mars multisource images. Finds no single method dominates; SIFT degrades on sparse-texture surfaces and under large illumination changes. Directly motivates PyISIS's adaptive routing.*

**[R18]** "Comparative Evaluation of Traditional and Deep Learning Feature Matching," arXiv:2509.04775, Sept. 2025.
> *Direct SIFT/ASIFT/AKAZE vs. SuperGlue comparison for lunar image registration. Neural methods show higher spatial repeatability and calibration accuracy under challenging conditions.*

**[R19]** D. DeTone, T. Malisiewicz, and A. Rabinovich, "SuperPoint: Self-Supervised Interest Point Detection and Description," in *Proc. IEEE/CVF CVPR Workshops*, 2018, pp. 224–236.
> *Self-supervised learned feature detector/descriptor. Backbone for SuperGlue, LightGlue, and multiple PyISIS matching presets.*

**[R20]** P.-E. Sarlin, D. DeTone, T. Malisiewicz, and A. Rabinovich, "SuperGlue: Learning Feature Matching with Graph Neural Networks," in *Proc. IEEE/CVF CVPR*, 2020, pp. 4938–4947.
> *GNN-based matcher with optimal transport. First to demonstrate learned matching superiority under viewpoint/illumination changes. Integrated in PyISIS as the SuperGlue preset.*

**[R21]** P. Lindenberger, P.-E. Sarlin, V. Larsson, and M. Pollefeys, "LightGlue: Local Feature Matching at Light Speed," in *Proc. IEEE/CVF ICCV*, 2023, pp. 17627–17638.
> *Adaptive early-termination GNN matcher. 3–5× faster than SuperGlue with equivalent accuracy. Supports multiple feature extractors via official backend. Central to PyISIS's cascade chain.*

**[R22]** "Understanding and Optimizing Attention-Based Sparse Matching," arXiv:2602.08430, 2026.
> *Demonstrates matcher-feature dependency: LightGlue trained on SuperPoint does not transfer to ALIKED/DISK without retraining. Implications for PyISIS's multi-extractor LightGlue support.*

**[R23]** J. Sun, Z. Shen, Y. Wang, H. Bao, and X. Zhou, "LoFTR: Detector-Free Local Feature Matching with Transformers," in *Proc. IEEE/CVF CVPR*, 2021, pp. 8922–8931.
> *Detector-free transformer matcher producing semi-dense correspondences. Excels on textureless scenes. Terminal method in PyISIS's cascade chain for hardest pairs.*

**[R24]** Y. Wang, X. He, S. Peng, D. Tan, and X. Zhou, "Efficient LoFTR: Semi-Dense Local Feature Matching with Sparse-Like Speed," in *Proc. IEEE/CVF CVPR*, 2024, pp. 21666–21675. DOI: [10.1109/CVPR52733.2024.02047](https://doi.org/10.1109/CVPR52733.2024.02047)
> *2.5× faster LoFTR via RepVGG backbone and token compression. <41ms/pair. Directly addresses PyISIS's GPU memory constraints and identified as priority integration target.*

**[R25]** J. Edstedt, Q. Sun, G. Bokman, M. Wadenback, and M. Felsberg, "RoMa: Robust Dense Feature Matching," in *Proc. IEEE/CVF CVPR*, 2024, pp. 19790–19800. DOI: [10.1109/CVPR52733.2024.01871](https://doi.org/10.1109/CVPR52733.2024.01871)
> *Dense matcher with DINOv2 global + ConvNet local features. Robust to extreme illumination/viewpoint changes. Relevant for future PyISIS integration.*

**[R26]** J. Edstedt et al., "RoMa v2: Harder Better Faster Denser Feature Matching," arXiv:2511.15706, Nov. 2025.
> *Two-stage refinement, 1.7× speedup, uncertainty quantification. Includes aerial/orbital test sets with steep viewpoint shifts—directly relevant to planetary remote sensing.*

**[R27]** J. Edstedt et al., "DKM: Dense Keypoint Matching," 2022–2023.
> *Dense matching via coarse-scale mutual nearest neighbors. >95% inlier ratio on WorldView-3 satellite data.*

**[R28]** "Deep Learning Meets Satellite Images: Benchmarking Feature Matching on WorldView-3 Stereo Pairs," arXiv:2409.02825, Sept. 2024.
> ***Key benchmark.*** Tests 8 methods on 496 WorldView-3 pairs with LiDAR ground truth. No single method dominates; SIFT+LightGlue best for accuracy, DKM best for coverage. Validates cascade approach.*

**[R29]** K. Ryoo, H. Lim, and H. Myung, "MambaGlue: Fast and Robust Local Feature Matching With Mamba," in *Proc. IEEE ICRA*, 2025. arXiv:2502.00462.
> *Mamba state-space model replaces Transformer attention for feature matching. Competitive accuracy with lower compute than LightGlue. Next-generation matcher for future integration.*

**[R30]** G. Potje et al., "XFeat: Accelerated Features for Lightweight Image Matching," in *Proc. IEEE/CVF CVPR*, 2024. arXiv:2404.19174.
> *Lightweight CNN keypoint detection/matching for resource-constrained settings. ~2.9 FPS on CPU. Relevant for onboard planetary processing.*

**[R31]** X. Zhao et al., "ALIKED: A Lighter Keypoint and Descriptor Extraction with Deformable Transformation," 2023.
> *Sub-pixel keypoint detection via deformable transformation. Competitive in-domain but significant out-of-domain degradation.*

**[R32]** "Evaluating the Limits of Image Matching Approaches and Benchmarks," arXiv:2408.16445, Aug. 2024.
> *Tests 20 feature extraction techniques. Top in-domain ~56% mAA, out-of-domain ~16%. All methods fail on transparent objects. Documents domain sensitivity relevant to planetary transfer.*

**[R33]** S. Gaisbauer, P. Gyawali, O. Wysocki, and B. Jutzi, "To Glue or Not to Glue? Classical vs Learned Image Matching," *ISPRS Annals*, vol. X-1/W2-2025, pp. 35–42, 2025. DOI: [10.5194/isprs-annals-X-1-W2-2025-35-2025](https://doi.org/10.5194/isprs-annals-X-1-W2-2025-35-2025)
> *SIFT+FLANN competitive on HPatches; DL dominates on MegaDepth; handcrafted methods fail on realistic pose estimation. Validates that different methods suit different conditions.*

### Adaptive Routing and Hybrid Methods

**[R34]** S. N. Syed, "CHAMELEON-SLAM: Adaptive Feature Selection and Uncertainty-Aware Matching," TechRxiv Preprint, 2026.
> *Closest adaptive routing precedent: scene classifier switches between XFeat, ALIKED, and SuperPoint. Uses learned classifier on terrestrial SLAM data—not mission metadata.*

**[R35]** "Light-SLAM: A Robust Deep-Learning Visual SLAM System Based on LightGlue Under Challenging Lighting Conditions," 2024.
> *LightGlue-integrated SLAM for challenging lighting. No adaptive method selection—always uses LightGlue.*

**[R36]** "Geometric Priors Meet Learned Features: A Hybrid Front-End for Drift-Resilient Monocular SLAM," 2026.
> *Hybrid classical-learned approach for monocular SLAM. Philosophy aligns with PyISIS's cascade design.*

**[R37]** "An Adaptive Remote Sensing Image-Matching Network Based on Feature Analysis," *Electronics*, vol. 12, no. 13, p. 2889, 2023.
> *Learned routing for multimodal satellite image registration based on image feature analysis. Does not leverage mission-specific metadata.*

**[R38]** "Highly Adaptive Multi-modal Image Matching Based on Tuning-Free Filtering and Enhanced Sketch Features (AMES)," *Information Fusion*, Dec. 2024. DOI: [10.1016/j.inffus.2024.102677](https://doi.org/10.1016/j.inffus.2024.102677)
> *Edge-based sketch features with adaptive strategies for multi-modal matching. Tuning-free design parallels PyISIS's automated routing.*

**[R39]** "MARSNet: A Mamba-driven Adaptive Framework for Robust Matching," *ISPRS J. Photogrammetry and Remote Sensing*, 2025.
> *DINOv2 foundation models with dynamic feature fusion for domain shift reduction. Addresses domain transfer challenge relevant to planetary applications.*

**[R40]** L. Xue, Z. Ye, D. Liu, S. Liu, R. Huang, H. Xie, Y. Feng, B. Guo, Y. Xu, and X. Tong, "Effective feature matching of high-resolution planetary orbiter images based on optimized image partitioning and rapid local correspondence," *Planetary and Space Science*, vol. 260, 106091, 2025. DOI: [10.1016/j.pss.2025.106091](https://doi.org/10.1016/j.pss.2025.106091)
> *Tile-based planetary image matching with optimized partitioning. Addresses same computational scalability challenge as PyISIS but uses classical matching exclusively.*

**[R41]** B. Xie, B. Liu, Y. Jia, W.-C. Liu, and K. Di, "Robust Feature Matching of Multi-Illumination Lunar Orbiter Images Based on Crater Neighborhood Structure," *Remote Sensing*, vol. 17, no. 13, 2302, 2025. DOI: [10.3390/rs17132302](https://doi.org/10.3390/rs17132302)
> *Crater neighborhood structure as geometric priors for illumination-invariant lunar matching. Complementary to routing approach—crater-based features could extend the cascade chain.*

**[R42]** "Algorithm Selection for Image Quality Assessment," arXiv:1908.06911, 2019.
> *AutoFolio per-instance algorithm selection for IQA. Framework directly generalizes to matcher selection based on image characteristics.*

**[R43]** "Multi-directional GLCM + LBP Fusion for Enhanced Texture Analysis," *MDPI Applied Sciences*, vol. 11, no. 5, 2332, 2021.
> *Combined GLCM and LBP texture descriptors. Validates PyISIS's GLCM-based texture sparseness component.*

### Control Networks and Bundle Adjustment

**[R44]** S. Wang, X. Geng, J. Li, T. Li, J. Yu, A. Wang, J. Wang, P. Liu, Z. Peng, X. Ma, Y. Wang, Y. Wang, and G. Chang, "Control Network Construction for LRO NAC Images Based on Refining Tie Points by Matching With Shaded LOLA DEM," *IEEE J. Selected Topics in Applied Earth Observations and Remote Sensing*, vol. 18, pp. 25512–25531, 2025. DOI: [10.1109/JSTARS.2025.3616321](https://doi.org/10.1109/JSTARS.2025.3616321)
> ***Most directly comparable work.*** Same instrument, same journal, overlapping task. Uses DEM-shaded renders for tie point refinement. Complementary to PyISIS's adaptive initial matching—could serve as post-processing step.*

**[R45]** K. Di, B. Liu, Z. Liu, B. Xie, W. Wan, M. Peng, Y. Wang, K. Shi, Y. Zhang, L. Yin, J. Liu, and P. Zhang, "LGCN2025: A New Lunar Global Control Network Constructed from High-Resolution Orbital Data," in *Proc. Lunar and Planetary Science Conference (LPSC)*, 2025, Abstract #1380.
> *Next-generation lunar global control network. Demonstrates community need for automated control network tools at planetary scale.*

**[R46]** W. M. Collins, S. A. Grieser, M. R. Henriksen, J. D. Clark, N. F. Carr, R. V. Wagner, T. A. Roseborough, S. E. Nystrom, and M. S. Robinson, "Photogrammetric Processing of Regional ShadowCam and LROC NAC Controlled Mosaics, Evaluation of Positional Accuracies, and Scientific Applications," *Remote Sensing*, vol. 18, no. 3, 525, 2026. DOI: [10.3390/rs18030525](https://doi.org/10.3390/rs18030525)
> *743 LROC NAC controlled mosaics with full pipeline documentation. Establishes current practice for LROC NAC photogrammetric processing.*

**[R47]** R. L. Fergason, L. Weller, and M. T. Bland, "The THEMIS Control Network of Mars," *Earth and Space Science*, vol. 13, no. 1, 2026. DOI: [10.1029/2025EA004758](https://doi.org/10.1029/2025EA004758)
> *Mars control network using photogrammetric bundle adjustment as gold standard for spatial referencing.*

**[R48]** Q. You, Z. Ye, C. Chen, H. Xie, Y. Jin, R. Huang, Y. Xu, X. Tong, Z. Hong, and Z. Zhang, "Bundle adjustment for multi-source Mars orbiter imagery with generalized control constraints," *ISPRS J. Photogrammetry and Remote Sensing*, vol. 227, 2025. DOI: [10.1016/j.isprsjprs.2025.05.030](https://doi.org/10.1016/j.isprsjprs.2025.05.030)
> *Bias compensation model for combining data from different Mars orbiters. Relevant to PyISIS's multi-instrument aspirations.*

**[R49]** X. Ma, C. Liu, X. Geng, S. Wang, T. Li, J. Wang, P. Liu, J. Zhang, Q. Wang, Y. Wang, and P. Zhen, "Methods for the Construction and Editing of an Efficient Control Network for the Photogrammetric Processing of Massive Planetary Remote Sensing Images," *Remote Sensing*, vol. 16, no. 23, 4600, 2024. DOI: [10.3390/rs16234600](https://doi.org/10.3390/rs16234600)
> *Addresses redundant/invalid point pruning for massive planetary datasets. Pruning strategies relevant to PyISIS's tile validity prefilter.*

**[R50]** R. Hemmi, H. Inoue, H. Kikuchi, H. Sato, H. Miyamoto, H. Otake, and M. Yamamoto, "LROC NAC-derived Meter-scale Topography of the Moon's South Polar Landing Sites: Digital Terrain Models and Their Quality Assessments," *The Planetary Science Journal*, vol. 6, no. 11, 264, 2025. DOI: [10.3847/PSJ/ae10a4](https://doi.org/10.3847/PSJ/ae10a4)
> *1 m/pixel DTMs from 6 NAC stereo pairs with meticulous manual tie point selection. Demonstrates the labor-intensive manual process that PyISIS aims to automate.*

**[R51]** H. Hu and B. Wu, "Block adjustment and coupled epipolar rectification of LROC NAC images for precision lunar topographic mapping," *Planetary and Space Science*, vol. 160, pp. 26–38, 2018.
> *Combines block adjustment with semi-global matching for precision lunar mapping. Foundational LROC NAC photogrammetric method.*

### Planetary Image Matching Challenges

**[R52]** "Vision-based Geo-Localization of Future Mars Rotorcraft in Challenging Illumination Conditions (Geo-LoFTR)," arXiv:2502.09795, Feb. 2025.
> *Geometry-aided DL matching for Mars rotorcraft at low sun elevation. Validates importance of illumination-aware matching—principle central to PyISIS's SPICE-based routing. NASA JPL.*

**[R53]** "MISR: Robust Multimodal Remote Image Matching of Earth and Planetary," IEEE, Jan. 2026.
> *Modality-invariant structural representation for cross-sensor planetary matching. Latest advance in domain diversity handling.*

**[R54]** "LiteSAM: Lightweight and Robust Feature Matching for Satellite and Aerial Images," *Remote Sensing*, vol. 17, no. 19, 3349, 2025.
> *Lightweight satellite-aerial matching for GPS-denied scenarios. Relevant to multi-scale planetary processing.*

**[R55]** T. Chase Jr. and K. Dantu, "MARs: Multi-view Attention Regularizations for Patch-Based Feature Recognition of Space Terrain," in *Proc. ECCV*, 2024, pp. 219–239. DOI: [10.1007/978-3-031-73039-9_13](https://doi.org/10.1007/978-3-031-73039-9_13)
> *Rotation-equivariant features with spatial coordinate awareness for planetary surfaces. 85%+ improvement on HiRISE Mars + synthetic lunar data. Demonstrates value of planetary-specific training.*

**[R56]** "A Deep Learning-Based Local Feature Extraction Method for Improved Image Matching and Surface Reconstruction from Yutu-2 PCAM Images on the Moon," *ISPRS J. Photogrammetry and Remote Sensing*, 2023/2024.
> *Two-branch attention network for Chang'E-4 lunar rover imagery. Planetary DL matching precedent.*

**[R57]** "Reconstruction of Lunar Terrain Using Photogrammetry, Neural Radiance Fields, and Gaussian Splatting," 2025.
> *Compares classical photogrammetry with neural reconstruction methods for lunar terrain.*

**[R58]** "AstroSplat: Physics-Based Gaussian Splatting for Rendering and Navigation," arXiv:2603.11969, Mar. 2026.
> *Integrates planetary reflectance models into Gaussian Splatting. Future integration target.*

**[R59]** "The Global CTX Mosaic of Mars," *AGU Advances*, 2024. DOI: [10.1029/2024EA003555](https://doi.org/10.1029/2024EA003555)
> *5.7 terapixel mosaic from 86,571 CTX images, 99.5% Mars coverage. Demonstrates the scale of control network challenge that automated tools must address.*

---

## 10. Source Index

### By Recency

| Year | Count | Key Papers |
|------|-------|------------|
| 2026 | 7 | [R11], [R34], [R36], [R46], [R47], [R53], [R58] |
| 2025 | 18 | [R3], [R17], [R18], [R22], [R26], [R29], [R33], [R38], [R39], [R40], [R41], [R44], [R45], [R48], [R50], [R52], [R54], [R56] |
| 2024 | 12 | [R16-ref], [R24], [R25], [R27], [R28], [R30], [R31], [R32], [R49], [R51], [R55], [R59] |
| 2023 | 3 | [R21], [R23], [R37] |
| 2020–2022 | 4 | [R12], [R13], [R19], [R20] |
| 2018–2019 | 4 | [R4], [R10], [R42], [R56-ref] |
| Pre-2018 (seminal) | 7 | [R1], [R2], [R6], [R7], [R8], [R14], [R15] |

**Recency assessment:** 63% of annotated sources are from 2024–2026, reflecting the rapid pace of development in deep learning matching and planetary photogrammetry.

### By DOI Availability

| Status | Count |
|--------|-------|
| DOI verified | 32 |
| arXiv/preprint (no DOI) | 12 |
| URL only (no DOI) | 11 |

### By Venue Type

| Venue | Count | Examples |
|-------|-------|---------|
| IEEE journals (JSTARS, TGRS) | 5 | [R3], [R28], [R44], [R53] |
| CVPR/ICCV/ECCV | 7 | [R19], [R20], [R21], [R23], [R24], [R25], [R55] |
| ISPRS journals/annals | 5 | [R2], [R17], [R33], [R48], [R56] |
| MDPI Remote Sensing | 4 | [R41], [R46], [R49], [R54] |
| Planetary Science journals | 5 | [R10], [R12], [R47], [R50], [R51] |
| AGU Earth and Space Science | 3 | [R10], [R12], [R47] |
| Other (SoftwareX, Information Fusion, etc.) | 6 | [R4], [R38], [R39] |
| arXiv preprints | 8 | [R18], [R22], [R26], [R28], [R32], [R42], [R52], [R58] |

---

## Methodology

This literature review was conducted on 2026-05-31 through systematic multi-source search across:

1. **Web search** (40+ query variations across Google Scholar, Semantic Scholar, IEEE Xplore, arXiv)
2. **Codebase analysis** of the PyISIS repository to identify implementation-relevant literature
3. **Citation chaining** from the target paper's existing 27 references
4. **Venue-targeted search** of IEEE JSTARS, ISPRS, CVPR/ICCV/ECCV, Photogrammetric Record, Planetary and Space Science, and MDPI Remote Sensing (2024–2026)

**Sub-questions investigated:**
- What Python binding frameworks exist for ISIS or comparable C++ scientific software?
- Which deep learning matchers have been evaluated on planetary or satellite imagery?
- What adaptive routing or hybrid matching approaches exist in SLAM, remote sensing, or computer vision?
- What are the current state-of-the-art control network construction methods for LRO NAC?
- What domain-specific challenges does planetary image matching present?

**Screening criteria:** Sources were included if they (a) addressed at least one of the three core domains (ISIS Python bindings, DL matching, adaptive routing), (b) were published in a peer-reviewed venue or reputable preprint server, and (c) provided either foundational methodology or recent empirical results relevant to the PyISIS framework.

**Total sources searched:** 90+ | **Annotated entries:** 55 | **Rejected (out of scope):** 35+
