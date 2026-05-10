#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/svg_to_pdf.sh <input.svg> [--output output.pdf]

Description:
  Convert an SVG file to PDF. By default, the output path uses the same
  directory and base name as the input file, with a .pdf extension.

Examples:
  scripts/svg_to_pdf.sh paper_use/image_ground_conversion_flow.svg
  scripts/svg_to_pdf.sh paper_use/image_ground_conversion_flow.svg --output paper_use/figure1.pdf

Options:
  --output PATH   Write PDF to PATH instead of the default same-name .pdf path.
  --help          Show this help message.

Converter priority:
  1. inkscape      Best general-purpose SVG/PDF converter.
  2. rsvg-convert  Lightweight converter, available in many conda environments.
  3. cairosvg      Python-based fallback when installed.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

input_path=""
output_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help)
      usage
      exit 0
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "error: --output requires a path" >&2
        exit 2
      fi
      output_path="$2"
      shift 2
      ;;
    --*)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$input_path" ]]; then
        echo "error: only one input file is supported" >&2
        usage >&2
        exit 2
      fi
      input_path="$1"
      shift
      ;;
  esac
done

if [[ -z "$input_path" ]]; then
  echo "error: missing input SVG file" >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$input_path" ]]; then
  echo "error: input file does not exist: $input_path" >&2
  exit 1
fi

case "$input_path" in
  *.svg|*.SVG)
    ;;
  *)
    echo "error: input file should end with .svg: $input_path" >&2
    exit 2
    ;;
esac

if [[ -z "$output_path" ]]; then
  output_path="${input_path%.*}.pdf"
fi

case "$output_path" in
  *.pdf|*.PDF)
    ;;
  *)
    echo "error: output file should end with .pdf: $output_path" >&2
    exit 2
    ;;
esac

output_dir="$(dirname "$output_path")"
mkdir -p "$output_dir"

if command -v inkscape >/dev/null 2>&1; then
  inkscape "$input_path" --export-type=pdf --export-filename="$output_path"
elif command -v rsvg-convert >/dev/null 2>&1; then
  rsvg-convert -f pdf -o "$output_path" "$input_path"
elif command -v cairosvg >/dev/null 2>&1; then
  cairosvg "$input_path" -o "$output_path"
else
  cat >&2 <<'ERROR'
error: no SVG-to-PDF converter found.
Install one of:
  - inkscape
  - librsvg/rsvg-convert
  - cairosvg
ERROR
  exit 1
fi

echo "wrote: $output_path"
