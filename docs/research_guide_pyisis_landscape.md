# PyISIS Research Guide: Literature Landscape & Positioning

*Generated: 2026-05-31 | Sources analyzed: 80+ | Confidence: High*

---

## Executive Summary

This guide maps the research landscape surrounding PyISIS's three core contributions—(1) Python bindings for USGS ISIS, (2) adaptive routing between classic and deep learning matchers, and (3) automated control network construction for planetary photogrammetry. It identifies **35+ high-priority papers** to strengthen your IEEE JSTARS submission, organized by section, with gap analysis and novelty positioning.

**Key finding:** Your paper occupies a unique niche at the intersection of three communities (planetary photogrammetry, deep learning matching, and research software engineering) that have minimal overlap in the literature. No prior work combines all three: comprehensive ISIS Python bindings + multi-method DL matching + SPICE-aware adaptive routing. This is a strong novelty claim that the current draft understates.

---

## 1. USGS ISIS Ecosystem & Python Bindings (Section II-A)

### Current references: [3], [9], [10], [11], [12]

### What's well-covered in your draft:
- ISIS overview [3], AutoCNet [9], ASP [10], SpiceQL [11], PyISIS discussion [12]

### Recommended additions:

| # | Paper / Resource | Why add it | URL |
|---|---|---|---|
| 1 | **PLIO v1.6.3** (USGS, 2026) — Planetary I/O library | Shows the existing Python ecosystem's file-I/O-only approach vs. your API-level binding | https://github.com/DOI-USGS/plio |
| 2 | **Official in-tree `python_bindings/`** in ISIS repo | USGS has started their own pybind11 effort — you should acknowledge it and differentiate | https://code.usgs.gov/astrogeology/isis/-/tree/dev/isis/python_bindings |
| 3 | **Pysis** (legacy) and **Kalasiris** (rbeyer) | Both are CLI wrappers, not API bindings — important for distinguishing your approach | https://github.com/rbeyer/kalasiris |
| 4 | **Edmundson et al. (2012)** "JIGSAW: The ISIS3 Bundle Adjustment" — ISPRS Annals | You cite this as [8] but should expand: this is the definitive jigsaw reference | https://isprs-annals.copernicus.org/articles/I-4/203/2012/ |
| 5 | **CSM interoperability** (2019-2020) — Earth and Space Science | Community Sensor Model enables cross-tool compatibility; relevant to PyISIS's CSMCamera binding | https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019EA001014 |
| 6 | **PlanetFlow** (2025) — Open-source cross-platform pipeline | Recent automated planetary processing pipeline; good for context | Search "PlanetFlow planetary processing 2025" |

### Novelty positioning for Section II-A:
- **Pysis & Kalasiris** = subprocess wrappers (no direct C++ API access, high I/O overhead)
- **AutoCNet** = Python orchestration over ISIS CLI calls (file-based coupling)
- **PLIO** = file I/O only (no camera models, no SPICE, no bundle adjustment)
- **Official in-tree bindings** = parallel effort, validates community need for Python access
- **PyISIS (yours)** = first comprehensive pybind11 binding covering camera models + SPICE + control networks + bundle adjustment

---

## 2. Deep Learning Feature Matching SOTA (Section II-B)

### Current references: [4], [5], [6], [7], [13], [14], [15], [16], [17], [18]

### Recommended additions:

| # | Paper | Key contribution | URL |
|---|---|---|---|
| 7 | **EfficientLoFTR** (Wang et al., CVPR 2024) | 2.5× faster than LoFTR, RepVGG backbone, <41ms/pair — directly relevant to your "GPU memory" limitation | https://arxiv.org/abs/2403.04765 |
| 8 | **RoMa / RoMa v2** (Edstedt et al., CVPR 2024 & 2025) | Dense matching with DINOv2 features; explicitly tested on aerial/orbital imagery; v2 adds uncertainty quantification | https://arxiv.org/abs/2305.15404; https://arxiv.org/html/2511.15706v1 |
| 9 | **DKM** (Edstedt et al., 2022-2023) | >95% inlier ratio on WorldView-3 satellite data; best DSM spatial coverage in satellite benchmarks | Search "DKM dense keypoint matching" |
| 10 | **Satellite benchmark study** (arXiv 2409.02825, Sept 2024) | Tests SIFT, SuperGlue, LightGlue, LoFTR, DKM on 496 WorldView-3 pairs with LiDAR ground truth — **the most directly comparable evaluation** | https://arxiv.org/html/2409.02825v1 |
| 11 | **"To Glue or Not to Glue?"** (ISPRS Annals, 2025) | SIFT+FLANN competitive on HPatches but DL dominates on MegaDepth; hybrid pipelines excel on repetitive facades | https://isprs-annals.copernicus.org/articles/X-1-W2-2025/35/2025/ |
| 12 | **MambaGlue** (Feb 2025) | Replaces Transformer attention with Mamba SSM; emerging architecture for matching | https://arxiv.org/html/2502.00462v1 |
| 13 | **XFeat** (2024) | 5-16× faster than alternatives, CPU-compatible — relevant to resource-constrained planetary processing | Search "XFeat lightweight feature extraction 2024" |
| 14 | **ALIKED** (Zhao et al., 2023) | Deformable transformation for sub-pixel keypoints; your pipeline already supports it via LightGlue official backend | Search "ALIKED lighter keypoint descriptor" |

### Key insight from satellite benchmark (paper #10):
- **SIFT + LightGlue** achieved best DSM accuracy when matches exist
- **DKM** dominated on spatial coverage and inlier ratio (>95%)
- **SIFT alone** had lowest success rate under seasonal transitions
- **Least Squares Matching** refinement improved geometric fidelity across ALL pipelines
- This directly validates your cascade approach (SIFT → LightGlue → LoFTR)

### Novelty positioning for Section II-B:
Your pipeline covers the 3 most important matcher families (sparse GNN: SuperGlue/LightGlue, detector-free: LoFTR, classical: SIFT). The satellite benchmark paper (#10) validates that no single method dominates — exactly the premise your adaptive routing exploits.

---

## 3. Adaptive Routing & Hybrid Matching (Section II-C)

### Current references: [19], [20], [21], [22], [23]

### Recommended additions:

| # | Paper | Key contribution | URL |
|---|---|---|---|
| 15 | **AMES** (Information Fusion, Dec 2024) | Adaptive Matching with Enhanced Sketches — tuning-free filtering for multi-modal matching | https://www.sciencedirect.com/science/article/abs/pii/S1566253524003774 |
| 16 | **MARSNet** (ISPRS, 2025) | Mamba-driven adaptive framework with DINOv2 foundation models | https://www.sciencedirect.com/science/article/abs/pii/S0924271625005052 |
| 17 | **PySIFT** (arXiv, May 2026) | GPU-resident deterministic SIFT with zero-copy handoff to DL pipelines — bridges classic/modern | https://arxiv.org/html/2605.17869v1 |
| 18 | **Algorithm Selection for IQA** (arXiv 2019) | AutoFolio for per-instance algorithm selection — concept directly generalizes to matcher selection | https://arxiv.org/abs/1908.06911 |
| 19 | **Robust Feature Matching of Multi-Illumination Lunar Orbiter Images** (Remote Sensing MDPI, 2025) | Crater neighborhood structure for illumination-invariant lunar matching — **same domain as yours** | https://www.mdpi.com/2072-4292/17/13/2302 |
| 20 | **Comparative Evaluation of Traditional and DL Features** (arXiv, Sept 2025) | Direct SIFT/ASIFT/AKAZE vs. SuperGlue comparison for lunar image registration | https://arxiv.org/pdf/2509.04775 |
| 21 | **Effective Feature Matching of HRPOIs** (Planetary and Space Science, March 2025) | Optimized image partitioning + rapid local correspondence — similar tile-based approach to yours | https://www.sciencedirect.com/science/article/abs/pii/S0032063325000583 |
| 22 | **GLCM + LBP fusion** (MDPI Applied Sciences, 2021) | Multi-directional GLCM with LBP for enhanced texture analysis — validates your GLCM approach | https://www.mdpi.com/2076-3417/11/5/2332 |

### Novelty positioning for Section II-C:
Your adaptive routing is unique in three ways:
1. **Domain-specific signals**: SPICE-derived solar geometry (elevation + azimuth) — no prior work uses ephemeris data for matcher routing
2. **Planetary-specific metrics**: Texture sparseness combining SIFT density + gradient + GLCM for planetary surfaces
3. **Cascade fallback**: Progressive escalation SIFT → LightGlue → LoFTR with quality-gated acceptance

Prior adaptive methods (#15, #16) are generic computer vision — none use mission metadata. The lunar illumination paper (#19) uses crater structure, not illumination geometry, for matching robustness.

---

## 4. Planetary Control Network Construction (Section VI)

### Current references: [1], [2], [8]

### Recommended additions:

| # | Paper | Key contribution | URL |
|---|---|---|---|
| 23 | **Wang et al. (2025)** "Control Network Construction for LRO NAC Images" — IEEE JSTARS | **Directly comparable work**: LRO NAC control networks using DEM-shaded tie point refinement — **published Oct 2025** | https://ieeexplore.ieee.org/iel8/4609443/10766875/11185283.pdf |
| 24 | **Chen et al. (2024)** "Large-Scale Block Bundle Adjustment of LROC NAC" — IEEE JSTARS | Lunar south pole BBA with topographic constraints; <1m relative positioning error | https://ieeexplore.ieee.org/iel7/4609443/10330207/10371383.pdf |
| 25 | **Methods for Construction and Editing of Efficient Control Networks** (Remote Sensing MDPI, 2024) | Addresses redundant/invalid point pruning — relevant to your tile validity prefilter | https://www.mdpi.com/2072-4292/16/23/4600 |
| 26 | **LGCN2025** (LPSC 2025) | New lunar global control network from LROC — shows community need for automated tools | https://www.hou.usra.edu/meetings/lpsc2025/pdf/1380.pdf |
| 27 | **THEMIS Control Network of Mars** (Earth and Space Science, Jan 2026) | Mars control network using photogrammetric BA as gold standard | https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2025EA004755 |
| 28 | **Photogrammetric Processing of ShadowCam and LROC** (Remote Sensing MDPI, 2026) | Full pipeline: pre-processing → control network → BA → mosaicking for LROC NAC | https://www.mdpi.com/2072-4292/18/3/525 |
| 29 | **LROC NAC Meter-scale Topography of Moon's South Pole** (PSJ, Nov 2025) | 1m/pixel DTMs from 6 NAC stereo pairs with meticulous tie point selection | https://iopscience.iop.org/article/10.3847/PSJ/ae10a4 |
| 30 | **Bundle adjustment for multi-source Mars orbiter imagery** (Photogrammetric Record, 2024) | Generalized control constraints + bias compensation for multi-source Mars data | https://www.researchgate.net/publication/392966088 |

### Critical new paper (#23):
Wang et al. 2025 is **the most directly comparable work** — also published in IEEE JSTARS, also on LRO NAC control network construction. They use shaded LOLA DEM as intermediate reference for tie point refinement. Your paper should cite this and differentiate:
- Their approach: DEM-shaded matching for tie point refinement
- Your approach: adaptive routing + cascade fallback for automated initial matching
- Complementary: their method could serve as a refinement step after your adaptive matching

---

## 5. Planetary Image Matching Challenges (Section VII context)

### Recommended additions:

| # | Paper | Key contribution | URL |
|---|---|---|---|
| 31 | **Comparison and Evaluation of Feature Matching for Planetary RS** (Photogrammetric Record, Oct 2024) | **13 detectors × 12 descriptors** on Moon and Mars — the most comprehensive planetary matching benchmark | https://onlinelibrary.wiley.com/doi/10.1111/phor.12520 |
| 32 | **MARs: Multi-view Attention Regularizations** (ECCV 2024) | DL matching on HiRISE Mars + synthetic lunar data; 85%+ improvement with rotation-equivariant features | https://arxiv.org/abs/2410.05182 |
| 33 | **Illumination Invariant Feature Matching for Planetary RS** (Planetary and Space Science, 2018) | Early illumination-invariant matching work for planetary images | https://www.sciencedirect.com/science/article/abs/pii/S0032063317303173 |
| 34 | **Feature Matching under Extreme Lighting** (various) | HDR approaches, DarkFeat (AAAI 2023), spatial-frequency domain methods | Search "DarkFeat low-light feature detection AAAI 2023" |
| 35 | **DL-based Feature Extraction for Yutu-2 PCAM** (ISPRS, 2023) | Two-branch attention network for Chang'E-4 lunar rover — planetary DL matching precedent | https://www.sciencedirect.com/science/article/abs/pii/S0924271623002964 |
| 36 | **Illumination Invariant Matching for Lunar TRN** (AIAA SciTech, 2025) | Georgia Tech: learning illumination-invariant features for lunar south pole navigation | https://arc.aiaa.org/doi/10.2514/6.2025-2073 |

---

## 6. Bundle Adjustment & Network Optimization (Context for Section VIII)

### Recommended additions:

| # | Paper | Key contribution | URL |
|---|---|---|---|
| 37 | **Hu & Wu (2018)** — Planetary and Space Science | Block adjustment + coupled epipolar rectification of LROC NAC — foundational method | https://www.sciencedirect.com/science/article/abs/pii/S0032063317304014 |
| 38 | **Global CTX Mosaic of Mars** (AGU Advances, 2024) | 5.7 terapixel mosaic from 86,571 CTX images — demonstrates scale of control network challenge | https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2024EA003555 |
| 39 | **Intelligent vision-guided trajectory reconstruction** (Nature Computational Science, Dec 2025) | BA + 3D reconstruction for lander descent with LRO NAC reference | https://www.nature.com/articles/s43247-05-03074-7 |
| 40 | **Reconstruction of Lunar Terrain: Photogrammetry vs NeRF vs Gaussian Splatting** (2025) | Comparison of classical and neural reconstruction — context for future directions | https://www.sciencedirect.com/science/article/abs/pii/S2213133725000265 |

---

## 7. Gap Analysis: What Your Paper Has vs. What It Needs

### Strengths of current draft:
- ✅ Well-structured IEEE format with clear contribution claims
- ✅ Rigorous mathematical formulation of routing metrics
- ✅ Honest acknowledgment of limitations (scale, thresholds, domain gap)
- ✅ Sensitivity analysis (Section V-I) — reviewers will appreciate this
- ✅ 121,856 control points is a strong quantitative result

### Gaps to address:

| Gap | Severity | How to address |
|---|---|---|
| **Missing Wang et al. 2025** (paper #23) | 🔴 Critical | Same journal, same instrument, same task. Must cite and differentiate. |
| **Missing satellite benchmark** (paper #10) | 🔴 Critical | 496 WorldView-3 pairs with LiDAR ground truth — validates your "no single method dominates" premise |
| **Missing EfficientLoFTR** (paper #7) | 🟡 Moderate | Directly addresses your GPU memory limitation; mention as future integration |
| **Missing comprehensive planetary benchmark** (paper #31) | 🟡 Moderate | 13 detectors × 12 descriptors — cite for context on method diversity |
| **No ground truth validation** | 🔴 Critical (acknowledged) | You acknowledge this in Section VIII-D. Prioritize manual tie point comparison. |
| **Only 6 test pairs** | 🟡 Moderate (acknowledged) | Sensitivity analysis partially compensates; promise multi-body extension |
| **No AutoCNet head-to-head** | 🟡 Moderate (acknowledged) | Plan controlled comparison; acknowledge difference in matching approaches |
| **Missing official ISIS Python bindings** context | 🟢 Low | Add brief mention of USGS in-tree effort to show community momentum |

---

## 8. Suggested Paper Enhancements

### A. Strengthen the novelty claim
Current draft says "no prior work has developed an adaptive routing system specifically designed for planetary photogrammetry that leverages mission-specific metadata." This is correct and strong. Strengthen by:
1. Explicitly listing what makes your routing unique vs. CHAMELEON-SLAM, Light-SLAM, and adaptive matching networks
2. Adding: "To our knowledge, PyISIS is the first framework to use SPICE-derived solar geometry for illumination-aware matching strategy selection"

### B. Add a "Related Work" comparison table
Create a table comparing existing tools:

| Tool | ISIS Integration | DL Matching | Adaptive Routing | Python Native |
|---|---|---|---|---|
| ISIS CLI [3] | Native C++ | No | No | No |
| AutoCNet [9] | Subprocess | No | No | Yes (orchestration) |
| ASP [10] | External | No | No | CLI only |
| PLIO | File I/O only | No | No | Yes |
| PyISIS (ours) | pybind11 API | SuperGlue, LightGlue, LoFTR | SPICE-aware cascade | Yes |

### C. Reference the "no single method dominates" finding more explicitly
The satellite benchmark study (#10) and the planetary matching benchmark (#31) both confirm that no single matcher works best across all conditions. This is the core premise of your adaptive routing — cite both papers prominently in the Introduction and Related Work.

### D. Discuss the "algorithm selection" framing
Your adaptive routing is essentially an instance of the Algorithm Selection Problem (Rice, 1976; AutoFolio, #18). Framing it this way connects to a broader CS literature and makes the "learned routing" future work more concrete.

### E. Consider adding RoMa/DKM to the pipeline
RoMa v2 (#8) explicitly supports aerial/orbital imagery and provides uncertainty quantification. Adding it as a 4th matcher option (even as future work) would strengthen the paper's coverage of dense matching methods.

---

## 9. Prioritized Reading List

### Must-read before revision (top 5):
1. **Wang et al. 2025** — Control Network Construction for LRO NAC (IEEE JSTARS) — your most direct competitor
2. **Satellite benchmark** (arXiv 2409.02825) — 496 WorldView-3 pairs, validates your cascade design
3. **Comparison and Evaluation** (Photogrammetric Record 2024) — 13 detectors × 12 descriptors on planetary data
4. **EfficientLoFTR** (CVPR 2024) — addresses your GPU memory limitation
5. **Robust Feature Matching of Multi-Illumination Lunar Orbiter** (MDPI 2025) — same domain, crater-based approach

### Should-read for positioning (next 5):
6. "To Glue or Not to Glue?" (ISPRS 2025) — SIFT vs DL benchmark
7. CHAMELEON-SLAM (#19 in your draft) — closest adaptive routing precedent
8. Large-Scale BBA of LROC NAC (#24) — bundle adjustment context
9. LGCN2025 (#26) — community need for automated control networks
10. RoMa v2 (#8 above) — dense matching with uncertainty for orbital imagery

---

## 10. Source Index

All URLs referenced in this guide, organized by topic:

### ISIS & Python Bindings
- ISIS GitHub: https://github.com/DOI-USGS/ISIS3
- ISIS Documentation: https://isis.astrogeology.usgs.gov/
- USGS Astro Docs: https://astrogeology.usgs.gov/docs/
- Official python_bindings: https://code.usgs.gov/astrogeology/isis/-/tree/dev/isis/python_bindings
- PLIO: https://github.com/DOI-USGS/plio
- AutoCNet: https://github.com/DOI-USGS/Autocnet
- Kalasiris: https://github.com/rbeyer/kalasiris
- PyISIS announcement: https://github.com/DOI-USGS/ISIS3/discussions/6017

### Deep Learning Matching
- EfficientLoFTR: https://arxiv.org/abs/2403.04765
- RoMa: https://arxiv.org/abs/2305.15404
- RoMa v2: https://arxiv.org/html/2511.15706v1
- MambaGlue: https://arxiv.org/html/2502.00462v1
- Satellite benchmark: https://arxiv.org/html/2409.02825v1
- "To Glue or Not to Glue?": https://isprs-annals.copernicus.org/articles/X-1-W2-2025/35/2025/
- PySIFT: https://arxiv.org/html/2605.17869v1

### Planetary Photogrammetry
- Wang et al. 2025 (JSTARS): https://ieeexplore.ieee.org/iel8/4609443/10766875/11185283.pdf
- Chen et al. 2024 (BBA): https://ieeexplore.ieee.org/iel7/4609443/10330207/10371383.pdf
- LGCN2025: https://www.hou.usra.edu/meetings/lpsc2025/pdf/1380.pdf
- THEMIS Control Network: https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2025EA004755
- ShadowCam/LROC: https://www.mdpi.com/2072-4292/18/3/525
- JIGSAW: https://isprs-annals.copernicus.org/articles/I-4/203/2012/

### Planetary Feature Matching
- 13 detectors × 12 descriptors: https://onlinelibrary.wiley.com/doi/10.1111/phor.12520
- MARs (ECCV 2024): https://arxiv.org/abs/2410.05182
- Crater neighborhood: https://www.mdpi.com/2072-4292/17/13/2302
- HRPOI partitioning: https://www.sciencedirect.com/science/article/abs/pii/S0032063325000583
- Yutu-2 DL features: https://www.sciencedirect.com/science/article/abs/pii/S0924271623002964
- Lunar TRN: https://arc.aiaa.org/doi/10.2514/6.2025-2073
- Traditional vs DL lunar: https://arxiv.org/pdf/2509.04775

### Adaptive & Hybrid Methods
- AMES: https://www.sciencedirect.com/science/article/abs/pii/S1566253524003774
- MARSNet: https://www.sciencedirect.com/science/article/abs/pii/S0924271625005052
- Algorithm Selection IQA: https://arxiv.org/abs/1908.06911
- GLCM+LBP fusion: https://www.mdpi.com/2076-3417/11/5/2332

### Reconstruction & DEM
- Global CTX Mosaic: https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2024EA003555
- NeRF/Gaussian lunar: https://www.sciencedirect.com/science/article/abs/pii/S2213133725000265
- Nature Comp Sci trajectory: https://www.nature.com/articles/s43247-025-03074-7

---

## Methodology

Research conducted 2026-05-31 via 5 parallel research agents covering: (1) local codebase analysis, (2) USGS ISIS ecosystem, (3) DL feature matching SOTA, (4) adaptive routing methods, (5) planetary control networks. Queried 40+ search variations across web, academic, and code repositories. Analyzed 80+ sources. Cross-referenced against existing paper draft references [1]-[27].
