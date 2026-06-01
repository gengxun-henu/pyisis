# Reproducible Experiment Logs Template

**Paper:** PyISIS: A Python-Bridged Planetary Photogrammetry Framework with Adaptive Deep Learning Image Matching for Automated Control Network Construction

**Purpose:** This document provides a template for logging all experimental parameters and processing steps to enable full reproducibility of the results reported in the paper.

---

## 1. Environment Configuration

### 1.1 System Specifications

```
Date: 2026-05-31
Operating System: [Linux distribution and version]
Kernel: [uname -r]
CPU: [model, cores, threads]
RAM: [total GB]
GPU: [model, VRAM GB, CUDA version]
Python: [version, e.g., 3.12.0]
Conda environment: [environment name]
```

### 1.2 Software Versions

```
ISIS: 9.0.0
PyISIS: 1.2.0
NumPy: [version]
OpenCV: [version]
PyTorch: [version]
CUDA: [version]
Kornia: [version]
scikit-image: [version]
matplotlib: [version]
```

### 1.3 Installation Commands

```bash
# ISIS installation
conda install -c usgs-astrogeology isis=9.0.0

# PyISIS build
cd /path/to/isis_pybind_standalone
mkdir build && cd build
cmake .. -DISIS_ROOT=/path/to/isis
make -j8

# Python dependencies
pip install -r requirements.txt
```

---

## 2. Dataset Specification

### 2.1 Test Image Pairs

For each of the 6 test pairs, log:

```
Pair ID: [unique identifier]
Pair Type: [same-orbit | cross-track]

Image 1:
  - Filename: [original EDR filename]
  - ISIS Cube: [path to calibrated cube]
  - Serial Number: [ISIS serial number]
  - Acquisition Date: [YYYY-MM-DD]
  - Center Coordinates: [latitude, longitude]
  - Solar Elevation: [degrees]
  - Solar Azimuth: [degrees]
  - Resolution: [m/pixel]

Image 2:
  - Filename: [original EDR filename]
  - ISIS Cube: [path to calibrated cube]
  - Serial Number: [ISIS serial number]
  - Acquisition Date: [YYYY-MM-DD]
  - Center Coordinates: [latitude, longitude]
  - Solar Elevation: [degrees]
  - Solar Azimuth: [degrees]
  - Resolution: [m/pixel]

Pair Metadata:
  - Elevation Difference: [degrees]
  - Azimuth Difference: [degrees]
  - Lighting Difference Score: [0-1]
  - Overlap Percentage: [%]
```

### 2.2 DEM Reference

```
DEM Source: [e.g., LOLA DEM]
DEM Resolution: [m/pixel]
DEM Filename: [path]
Projection: [e.g., SimpleCylindrical]
Coordinate System: [planetocentric | planetographic]
```

---

## 3. Processing Pipeline Configuration

### 3.1 Image Calibration

```bash
# For each image
lronac2isis from=[EDR] to=[ISIS cube]
spiceinit from=[ISIS cube]
lronaccal from=[ISIS cube] to=[calibrated cube]
lronacecho from=[calibrated cube] to=[echo-corrected cube]
```

### 3.2 DOM Generation

```
Projection: SimpleCylindrical
Resolution: [m/pixel]
DEM Reference: [path]
Output DOM: [path for each image]
```

### 3.3 Matching Pipeline Parameters

```json
{
  "tile_size": 2048,
  "tile_step": 2048,
  "min_valid_ratio": 0.05,
  "workers": 4,
  "sift_max_features": 1000,
  "lowres_level": 3,
  "lowres_offset_threshold": 2000,
  "quality_profile": "balanced",
  "random_seed": 42,
  "gpu_device": 0
}
```

### 3.4 Adaptive Routing Parameters

```json
{
  "texture_weights": {
    "sift_density": 0.45,
    "gradient": 0.30,
    "glcm_contrast": 0.25
  },
  "texture_thresholds": {
    "sift_density": 0.002,
    "gradient": 64.0,
    "glcm_contrast": 60.0
  },
  "lighting_weights": {
    "elevation": 0.4,
    "azimuth": 0.6
  },
  "routing_thresholds": {
    "sift_low": 0.35,
    "sift_high": 0.65,
    "lighting_low": 0.20,
    "lighting_high": 0.55
  },
  "glcm_params": {
    "levels": 16,
    "distance": 1,
    "angle": 0
  },
  "aggregation": {
    "tile_percentile": 90,
    "pair_method": "max"
  }
}
```

### 3.5 Quality Gate Profile (Balanced)

```json
{
  "min_inliers": 24,
  "min_ratio": 0.35,
  "min_coverage": 0.20,
  "max_mean_residual": 2.5,
  "max_p95_residual": 4.0
}
```

### 3.6 Cascade Fallback Chain

```
SIFT/BF → LightGlue → LoFTR
LightGlue → LoFTR
LoFTR → (no fallback)
```

---

## 4. Per-Pair Processing Logs

For each pair, log the following:

### 4.1 Texture and Lighting Analysis

```
Pair ID: [ID]
Processing Time: [YYYY-MM-DD HH:MM:SS]

Texture Analysis:
  - SIFT Density (Image 1): [value]
  - SIFT Density (Image 2): [value]
  - Gradient Magnitude (Image 1): [value]
  - Gradient Magnitude (Image 2): [value]
  - GLCM Contrast (Image 1): [value]
  - GLCM Contrast (Image 2): [value]
  - Pair Texture Sparseness: [value]

Lighting Analysis:
  - Solar Elevation (Image 1): [degrees]
  - Solar Elevation (Image 2): [degrees]
  - Solar Azimuth (Image 1): [degrees]
  - Solar Azimuth (Image 2): [degrees]
  - Elevation Difference: [degrees]
  - Azimuth Difference: [degrees]
  - Pair Lighting Difference: [value]
```

### 4.2 Routing Decision

```
Pair ID: [ID]
Routed Method: [SIFT/BF | LightGlue | LoFTR]
Route Confidence: [value]
Routing Rationale: [explanation]
```

### 4.3 Tile-Level Results

For each tile:

```
Tile ID: [pair_id]_[tile_row]_[tile_col]
Valid Pixel Ratio: [value]
Tile Included: [true | false]

If included:
  - Initial Method: [SIFT/BF | LightGlue | LoFTR]
  - Keypoints Detected: [count]
  - Matches Found: [count]
  - Inliers After RANSAC: [count]
  - Inlier Ratio: [value]
  - Coverage: [value]
  - Mean Residual: [pixels]
  - P95 Residual: [pixels]
  - Quality Score Q: [value]
  - Quality Gate: [pass | fail]
  - Cascade Triggered: [none | LightGlue | LoFTR]
  - Final Method: [method that produced accepted match]
  - Processing Time: [seconds]
```

### 4.4 Pair-Level Aggregation

```
Pair ID: [ID]
Total Tiles: [count]
Valid Tiles: [count]
Matched Tiles: [count]
Tile Success Rate: [%]

Total Keypoints: [count]
Total Matches: [count]
Total Inliers: [count]
Control Points Generated: [count]

Average Inlier Ratio: [value]
Average Coverage: [value]
Average Mean Residual: [pixels]
Average Quality Score: [value]

Processing Time: [seconds]
  - I/O: [seconds]
  - Matching: [seconds]
  - RANSAC: [seconds]
  - ControlNet Assembly: [seconds]
```

---

## 5. Control Network Construction Logs

### 5.1 Coordinate Transformation

For each matched point:

```
Point ID: [unique identifier]
DOM Coordinates: [x_dom, y_dom]
Geographic Coordinates: [latitude, longitude]
DEM Elevation: [meters]
Ground Coordinates: [X, Y, Z body-fixed]

Image 1 Projection:
  - Line: [pixels]
  - Sample: [pixels]
  - Residual: [pixels]

Image 2 Projection:
  - Line: [pixels]
  - Sample: [pixels]
  - Residual: [pixels]
```

### 5.2 Control Network Assembly

```
ControlNet ID: [network name]
Target: Moon
Network Type: [ImageToGround | ImageToImage]
Total Points: [count]
Total Measures: [count]

Point Statistics:
  - Free Points: [count]
  - Constrained Points: [count]
  - Fixed Points: [count]

Measure Statistics:
  - Average Measures per Point: [value]
  - Points with 2 Measures: [count]
  - Points with 3+ Measures: [count]
```

### 5.3 Network Merging

```
Input Networks: [list of pairwise network files]
Duplicate Threshold: [pixels]
Merged Network: [output filename]
Final Point Count: [count]
Final Measure Count: [count]
File Size: [MB]
```

---

## 6. Sensitivity Analysis Logs

### 6.1 Threshold Perturbation

For each threshold perturbation:

```
Threshold: [S_low | S_high | D_low | D_high]
Original Value: [value]
Perturbed Range: [min, max]
Step Size: 0.01

For each perturbed value:
  - Pairs Affected: [list of pair IDs that changed routing]
  - Routing Changes: [details]
  - Cascade Compensated: [yes | no]
  - Final Matching Outcome: [identical | different]
```

### 6.2 Single-Method Baselines

For each baseline method (SIFT/BF only, LightGlue only, LoFTR only):

```
Method: [name]
Pairs Completed: [count] / 6
Total Points: [count]
Average Inlier Ratio: [value]
Average Coverage: [value]
Average Quality Score: [value]

Per-Pair Results:
  Pair 1: [completed | failed], [points], [inlier ratio], [coverage]
  Pair 2: [completed | failed], [points], [inlier ratio], [coverage]
  ...
  Pair 6: [completed | failed], [points], [inlier ratio], [coverage]
```

---

## 7. Computational Performance Logs

### 7.1 Per-Stage Timing

```
Total Processing Time: [seconds]

Stage Breakdown:
  - I/O (with TileCache): [seconds] ([%])
  - SIFT Detection + Description: [seconds] ([%])
  - FLANN/BF Matching: [seconds] ([%])
  - LightGlue Matching: [seconds] ([%])
  - LoFTR Matching: [seconds] ([%])
  - RANSAC Filtering: [seconds] ([%])
  - ControlNet Assembly: [seconds] ([%])

TileCache Statistics:
  - Total Reads: [count]
  - Cache Hits: [count] ([%])
  - Cache Misses: [count] ([%])
  - Total I/O Volume: [GB]
  - I/O Reduction: [%]
```

### 7.2 GPU Utilization

```
GPU Device: [model]
VRAM Capacity: [GB]
Peak VRAM Usage: [GB]
Average VRAM Usage: [GB]
GPU Utilization: [%]
```

---

## 8. Random Seeds and Determinism

```
Global Random Seed: 42
NumPy Random Seed: 42
PyTorch Random Seed: 42
CUDA Deterministic: true
OpenCV Random Seed: 42

Note: SIFT keypoint detection is deterministic given the same image and parameters.
LightGlue and LoFTR use deterministic attention mechanisms with fixed seeds.
RANSAC uses fixed random seed for reproducible inlier selection.
```

---

## 9. Data Availability Statement

### 9.1 Input Data

```
LRO NAC EDR Images:
  Source: PDS Geosciences Node
  URL: https://pds-geosciences.wustl.edu/missions/lro/lroc.htm
  Access Date: [YYYY-MM-DD]

LOLA DEM:
  Source: PDS Geosciences Node
  URL: [specific URL]
  Resolution: [m/pixel]
```

### 9.2 Processed Data

```
Calibrated ISIS Cubes: [repository URL or DOI]
DOM Images: [repository URL or DOI]
Control Networks: [repository URL or DOI]
Processing Logs: [repository URL or DOI]
```

### 9.3 Code Availability

```
PyISIS Framework: [GitHub repository URL]
Matching Pipeline: [GitHub repository URL]
Example Scripts: [GitHub repository URL]
Docker Images: [Docker Hub or repository URL]
```

---

## 10. Validation and Verification

### 10.1 Internal Consistency Checks

```
✓ All matched points have valid DOM coordinates
✓ All coordinate transformations are reversible (within tolerance)
✓ All control points have ≥2 measures
✓ All inlier ratios are within [0, 1]
✓ All quality scores are within [0, 1]
✓ No duplicate control points (within threshold)
```

### 10.2 Comparison with Manual Measurement

[To be added after ground truth validation]

```
Manual Tie Points: [count]
Automatic Tie Points: [count]
Overlap: [count] ([%])
Mean Positional Difference: [pixels]
Std Positional Difference: [pixels]
```

### 10.3 Bundle Adjustment Validation

[To be added after jigsaw run]

```
Bundle Adjustment Convergence: [yes | no]
Iterations: [count]
Final RMS Residual: [pixels]
Sigma Values: [statistics]
Points Flagged as Outliers: [count]
```

---

## 11. Reproducibility Checklist

- [ ] All software versions documented
- [ ] All input data accessible via public URLs
- [ ] All processing parameters logged
- [ ] All random seeds fixed
- [ ] All intermediate results saved
- [ ] All processing scripts version-controlled
- [ ] Docker/container environment provided
- [ ] README with step-by-step reproduction instructions
- [ ] Expected outputs documented with checksums
- [ ] Contact information for reproducibility issues

---

**Note:** This template should be filled in during actual experiments. The completed log should be archived alongside the code and data to enable full reproducibility of the reported results.
