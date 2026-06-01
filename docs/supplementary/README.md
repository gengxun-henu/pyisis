# Supplementary Materials

This directory contains supplementary materials for the PyISIS IEEE JSTARS paper.

## Contents

### 1. references.bib
- **Description:** BibTeX file with all 29 references cited in the paper
- **Usage:** Include in LaTeX compilation
- **Format:** Standard BibTeX
- **Total entries:** 29

```bibtex
@article{archinal2018iau,
  author = {Archinal, B. A. and others},
  title = {Report of the IAU Working Group on Cartographic Coordinates...},
  journal = {Celestial Mechanics and Dynamical Astronomy},
  year = {2018}
}
```

### 2. reviewer_response.md
- **Description:** Anticipated reviewer questions and prepared responses
- **Sections:**
  - Category 1: Novelty and Contributions (2 questions)
  - Category 2: Methodology and Technical Soundness (4 questions)
  - Category 3: Experimental Design and Results (3 questions)
  - Category 4: Related Work and Positioning (2 questions)
  - Category 5: Reproducibility and Open Science (2 questions)
- **Total questions:** 13
- **Usage:** Reference during revision process; update with actual reviewer comments

### 3. reproducible_experiment_logs.md
- **Description:** Template for logging all experimental parameters to enable full reproducibility
- **Sections:**
  1. Environment Configuration
  2. Dataset Specification
  3. Processing Pipeline Configuration
  4. Per-Pair Processing Logs
  5. Control Network Construction Logs
  6. Sensitivity Analysis Logs
  7. Computational Performance Logs
  8. Random Seeds and Determinism
  9. Data Availability Statement
  10. Validation and Verification
  11. Reproducibility Checklist
- **Usage:** Fill in during actual experiments; archive alongside code and data

### 4. matching_preset_specifications.json
- **Description:** Complete parameter specifications for all 17 matching presets
- **Format:** JSON
- **Total presets:** 17
- **Categories:**
  - Classic SIFT (2 presets)
  - LightGlue Legacy (5 presets)
  - LightGlue Official (6 presets)
  - LoFTR (3 presets)
  - SuperGlue (2 presets)
- **Includes:**
  - Quality profiles (strict, balanced, relaxed, fast)
  - Feature extractor parameters
  - Matcher-specific parameters
  - Device configuration
  - Dependencies

## Using These Materials

### For LaTeX Compilation

1. Copy `references.bib` to your LaTeX project directory
2. Add to your `.tex` file:
   ```latex
   \bibliographystyle{IEEEtran}
   \bibliography{references}
   ```
3. Compile with:
   ```bash
   pdflatex paper.tex
   bibtex paper
   pdflatex paper.tex
   pdflatex paper.tex
   ```

### For Revisions

1. Review `reviewer_response.md` when actual reviewer comments arrive
2. Update responses based on specific feedback
3. Use as a checklist to ensure all major concerns are addressed

### For Reproducibility

1. Copy `reproducible_experiment_logs.md` to your experiment directory
2. Fill in all sections during actual experiments
3. Archive the completed log alongside:
   - Code repository (with commit hash)
   - Data repository (with DOI)
   - Processing logs
   - Random seeds

### For Implementation Reference

1. Consult `matching_preset_specifications.json` for exact parameter values
2. Use as validation reference when implementing presets
3. Compare against actual implementation in `examples/controlnet_construct/deep_match_config.py`

## File Formats

- **.bib:** BibTeX bibliography (plain text)
- **.md:** Markdown (plain text)
- **.json:** JSON configuration (plain text)

All files are UTF-8 encoded with LF line endings.

## Version Control

These files should be tracked in version control:

```bash
git add docs/supplementary/
git commit -m "Add supplementary materials for JSTARS submission"
```

## DOI Assignment

When depositing to Zenodo or similar archive:

1. Include all files in this directory
2. Add DOI reference to paper manuscript
3. Update README with archive URL

Example:
```
Supplementary materials available at: https://doi.org/10.5281/zenodo.XXXXXXX
```

## Contact

For questions about supplementary materials, contact:

**Geng Xun**  
Henan University, Kaifeng, China  
Email: [correspondence email]

## License

These supplementary materials are licensed under the same terms as the PyISIS framework (MIT License).

---

**Generated:** 2026-05-31  
**Paper version:** Final submission draft  
**Total files:** 4  
**Total size:** ~50 KB
