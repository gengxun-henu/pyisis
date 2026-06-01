# PyISIS Paper Figures

This directory contains Mermaid diagram files for all figures in the PyISIS IEEE JSTARS paper.

## Figure Files

### Figure 1: PyISIS Architecture Diagram
- **File:** `figure1_architecture.mmd`
- **Description:** Layered architecture showing C++ ISIS → pybind11 → Python bindings → Applications with 7 modules
- **Render command:**
  ```bash
  mmdc -i figure1_architecture.mmd -o figure1_architecture.pdf
  mmdc -i figure1_architecture.mmd -o figure1_architecture.png
  ```

### Figure 2: Adaptive Routing Flowchart
- **File:** `figure2_adaptive_routing.mmd`
- **Description:** Decision flowchart showing texture/lighting analysis → routing decision → cascade fallback
- **Render command:**
  ```bash
  mmdc -i figure2_adaptive_routing.mmd -o figure2_adaptive_routing.pdf
  mmdc -i figure2_adaptive_routing.mmd -o figure2_adaptive_routing.png
  ```

### Figure 3: Qualitative Matching Examples
- **File:** `figure3_matching_examples.mmd`
- **Description:** Schematic showing SIFT vs LightGlue vs LoFTR performance on different terrain types
- **Note:** This is a schematic representation. For publication, replace with actual matching visualizations from experimental results showing keypoints as colored circles, matches as connecting lines, inliers in green, outliers in red.
- **Render command:**
  ```bash
  mmdc -i figure3_matching_examples.mmd -o figure3_matching_examples.pdf
  mmdc -i figure3_matching_examples.mmd -o figure3_matching_examples.png
  ```

### Figure 4: Routing Decision Space Visualization
- **File:** `figure4_routing_space.mmd`
- **Description:** 2D scatter plot with texture sparseness vs lighting difference, color-coded by routing decision
- **Note:** This is a schematic. For publication, create actual scatter plot with matplotlib showing the 6 test pairs as labeled points with decision boundaries.
- **Render command:**
  ```bash
  mmdc -i figure4_routing_space.mmd -o figure4_routing_space.pdf
  mmdc -i figure4_routing_space.mmd -o figure4_routing_space.png
  ```

### Figure 5: Control Network Construction Pipeline
- **File:** `figure5_controlnet_pipeline.mmd`
- **Description:** Linear pipeline showing 7 steps from raw imagery to ControlNet
- **Render command:**
  ```bash
  mmdc -i figure5_controlnet_pipeline.mmd -o figure5_controlnet_pipeline.pdf
  mmdc -i figure5_controlnet_pipeline.mmd -o figure5_controlnet_pipeline.png
  ```

## Rendering Requirements

### Mermaid CLI (mmdc)

Install mermaid-cli globally:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Or use npx without installation:

```bash
npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.pdf
```

### Alternative Rendering Options

1. **Mermaid Live Editor:**
   - Visit: https://mermaid.live
   - Copy the content of each `.mmd` file
   - Export as PNG, SVG, or PDF

2. **VS Code Extension:**
   - Install "Markdown Preview Mermaid Support" extension
   - Embed mermaid code in markdown and preview

3. **Python with matplotlib:**
   - For Figures 3 and 4, consider creating actual data visualizations using matplotlib
   - Use the schematic as a guide for layout and content

## Color Scheme

All figures use IEEE-compliant, colorblind-safe colors:

- **Applications (Red):** `#d62728`
- **Python Package (Green):** `#2ca02c`
- **Modules (Purple):** `#9467bd`
- **pybind11 (Orange):** `#ff7f0e`
- **C++ ISIS (Blue):** `#1f77b4`
- **Ecosystem (Brown):** `#8c564b`

## IEEE Compliance

- **Format:** PDF for vector graphics (preferred), PNG at 300 DPI minimum
- **Font:** Serif font family, size 8-12 pt
- **Line width:** 1.5-2 pt for borders, 1 pt for internal lines
- **Color:** Figures should be legible in both color and grayscale
- **Size:** Single column width (3.5 inches) or double column width (7 inches)

## Updating Figures

To modify a figure:

1. Edit the `.mmd` file in a text editor
2. Re-render using `mmdc`
3. Verify the output in PDF/PNG format
4. Update the paper manuscript with the new figure reference

## Notes for Publication

### Figure 3 (Qualitative Matching Examples)

Replace the schematic with actual experimental visualizations:

```python
# Example matplotlib code for Figure 3
import matplotlib.pyplot as plt
import cv2
import numpy as np

# Load image pair
img1 = cv2.imread('pair1_img1.png', cv2.IMREAD_GRAYSCALE)
img2 = cv2.imread('pair1_img2.png', cv2.IMREAD_GRAYSCALE)

# Run SIFT matching
sift = cv2.SIFT_create()
kp1, des1 = sift.detectAndCompute(img1, None)
kp2, des2 = sift.detectAndCompute(img2, None)

# Match with BF
bf = cv2.BFMatcher()
matches = bf.knnMatch(des1, des2, k=2)

# Apply ratio test
good = []
for m, n in matches:
    if m.distance < 0.75 * n.distance:
        good.append(m)

# Draw matches
result = cv2.drawMatches(img1, kp1, img2, kp2, good, None,
                         flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

# Save figure
plt.figure(figsize=(12, 4))
plt.imshow(result)
plt.axis('off')
plt.title('SIFT/BF Matching Results')
plt.savefig('figure3_sift_results.png', dpi=300, bbox_inches='tight')
```

### Figure 4 (Routing Decision Space)

Create actual scatter plot with matplotlib:

```python
import matplotlib.pyplot as plt
import numpy as np

# Data from experiments
pairs = [
    {'id': 1, 'S': 0.28, 'D': 0.12, 'route': 'SIFT', 'type': 'Same-orbit'},
    {'id': 2, 'S': 0.32, 'D': 0.18, 'route': 'SIFT', 'type': 'Same-orbit'},
    {'id': 3, 'S': 0.48, 'D': 0.32, 'route': 'LightGlue', 'type': 'Cross-track'},
    {'id': 4, 'S': 0.52, 'D': 0.41, 'route': 'LightGlue', 'type': 'Cross-track'},
    {'id': 5, 'S': 0.71, 'D': 0.38, 'route': 'LoFTR', 'type': 'Cross-track'},
    {'id': 6, 'S': 0.45, 'D': 0.62, 'route': 'LoFTR', 'type': 'Cross-track'},
]

# Plot
fig, ax = plt.subplots(figsize=(8, 6))

# Decision boundaries
ax.axvline(x=0.35, color='gray', linestyle='--', alpha=0.5)
ax.axvline(x=0.65, color='gray', linestyle='--', alpha=0.5)
ax.axhline(y=0.20, color='gray', linestyle='--', alpha=0.5)
ax.axhline(y=0.55, color='gray', linestyle='--', alpha=0.5)

# Color-code regions
ax.fill_between([0, 0.35], [0, 0], [0.20, 0.20], alpha=0.1, color='#1f77b4', label='SIFT Region')
ax.fill_between([0.35, 0.65], [0, 0], [0.55, 0.55], alpha=0.1, color='#ff7f0e', label='LightGlue Region')
ax.fill_between([0.65, 1.0], [0, 0], [1.0, 1.0], alpha=0.1, color='#d62728', label='LoFTR Region')

# Plot points
colors = {'SIFT': '#1f77b4', 'LightGlue': '#ff7f0e', 'LoFTR': '#d62728'}
markers = {'Same-orbit': 'o', 'Cross-track': 's'}

for pair in pairs:
    ax.scatter(pair['S'], pair['D'], 
               c=colors[pair['route']], 
               marker=markers[pair['type']],
               s=100, edgecolors='black', linewidths=1.5)
    ax.annotate(f"Pair {pair['id']}", 
                (pair['S'], pair['D']), 
                textcoords="offset points", 
                xytext=(5, 5))

ax.set_xlabel('Texture Sparseness (S)', fontsize=12)
ax.set_ylabel('Lighting Difference (D)', fontsize=12)
ax.set_title('Routing Decision Space', fontsize=14)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
plt.savefig('figure4_routing_space.png', dpi=300, bbox_inches='tight')
plt.savefig('figure4_routing_space.pdf', format='pdf', bbox_inches='tight')
```

## File Organization

```
docs/
├── figures/
│   ├── README.md                          # This file
│   ├── figure1_architecture.mmd
│   ├── figure2_adaptive_routing.mmd
│   ├── figure3_matching_examples.mmd
│   ├── figure4_routing_space.mmd
│   └── figure5_controlnet_pipeline.mmd
├── supplementary/
│   ├── README.md
│   ├── references.bib
│   ├── reviewer_response.md
│   ├── reproducible_experiment_logs.md
│   └── matching_preset_specifications.json
├── paper_pyisis_jstars_final.md           # Main paper
└── paper_pyisis_adaptive_matching_jstars.md  # Working draft
```

## Contact

For questions about figure generation or modifications, contact the paper authors.
