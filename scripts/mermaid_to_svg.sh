#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/mermaid_to_svg.sh <input.mmd|input.mermaid> [--output output.svg]

Description:
  Convert a Mermaid source file to SVG. By default, the output path uses the
  same directory and base name as the input file, with a .svg extension.

Examples:
  scripts/mermaid_to_svg.sh paper_use/image_ground_conversion_flow.mmd
  scripts/mermaid_to_svg.sh paper_use/image_ground_conversion_flow.mermaid
  scripts/mermaid_to_svg.sh paper_use/image_ground_conversion_flow.mmd --output paper_use/flow.svg

Options:
  --output PATH   Write SVG to PATH instead of the default same-name .svg path.
  --help          Show this help message.

Environment:
  MERMAID_CLI_VERSION   Mermaid CLI version used by npx when mmdc is not installed.
                        Default: 10.9.1, selected for Node 20 compatibility.
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
  echo "error: missing input Mermaid file" >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$input_path" ]]; then
  echo "error: input file does not exist: $input_path" >&2
  exit 1
fi

case "$input_path" in
  *.mmd|*.mermaid)
    ;;
  *)
    echo "error: input file should end with .mmd or .mermaid: $input_path" >&2
    exit 2
    ;;
esac

if [[ -z "$output_path" ]]; then
  output_path="${input_path%.*}.svg"
fi

output_dir="$(dirname "$output_path")"
mkdir -p "$output_dir"

if command -v mmdc >/dev/null 2>&1; then
  mmdc -i "$input_path" -o "$output_path"
else
  mermaid_cli_version="${MERMAID_CLI_VERSION:-10.9.1}"
  if ! command -v npx >/dev/null 2>&1; then
    echo "error: neither mmdc nor npx is available. Install Mermaid CLI or Node/npm." >&2
    exit 1
  fi
  npx -y "@mermaid-js/mermaid-cli@${mermaid_cli_version}" -i "$input_path" -o "$output_path"
fi

echo "wrote: $output_path"
