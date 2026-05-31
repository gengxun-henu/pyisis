#!/bin/bash
# Compilation script for PyISIS IEEE JSTARS paper
# Usage: ./compile_paper.sh

set -e  # Exit on error

echo "=== PyISIS Paper LaTeX Compilation ==="
echo ""

# Clean previous compilation artifacts
echo "Cleaning previous compilation artifacts..."
rm -f paper_pyisis_jstars_final.aux \
      paper_pyisis_jstars_final.bbl \
      paper_pyisis_jstars_final.blg \
      paper_pyisis_jstars_final.log \
      paper_pyisis_jstars_final.out \
      paper_pyisis_jstars_final.pdf \
      paper_pyisis_jstars_final.toc \
      paper_pyisis_jstars_final.lof \
      paper_pyisis_jstars_final.lot

# First LaTeX pass - generates .aux file with citation references
echo "First LaTeX pass (generating .aux file)..."
pdflatex -interaction=nonstopmode paper_pyisis_jstars_final.tex > /dev/null

# BibTeX pass - processes bibliography
echo "BibTeX pass (processing bibliography)..."
bibtex paper_pyisis_jstars_final

# Second LaTeX pass - incorporates bibliography
echo "Second LaTeX pass (incorporating bibliography)..."
pdflatex -interaction=nonstopmode paper_pyisis_jstars_final.tex > /dev/null

# Third LaTeX pass - resolves all cross-references
echo "Third LaTeX pass (resolving cross-references)..."
pdflatex -interaction=nonstopmode paper_pyisis_jstars_final.tex > /dev/null

# Check final output
if [ -f paper_pyisis_jstars_final.pdf ]; then
    SIZE=$(ls -lh paper_pyisis_jstars_final.pdf | awk '{print $5}')
    PAGES=$(pdfinfo paper_pyisis_jstars_final.pdf 2>/dev/null | grep Pages | awk '{print $2}' || echo "unknown")
    echo ""
    echo "=== Compilation Successful ==="
    echo "Output: paper_pyisis_jstars_final.pdf"
    echo "Size: $SIZE"
    echo "Pages: $PAGES"
    echo ""
    echo "To view the PDF:"
    echo "  evince paper_pyisis_jstars_final.pdf &"
    echo "  or"
    echo "  xdg-open paper_pyisis_jstars_final.pdf"
else
    echo ""
    echo "=== Compilation Failed ==="
    echo "Check paper_pyisis_jstars_final.log for details"
    exit 1
fi
