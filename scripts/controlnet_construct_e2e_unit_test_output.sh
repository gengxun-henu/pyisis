#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-/home/gengxun/miniconda3/envs/asp360_new/bin/python}"
OUTPUT_ROOT="${ISIS_PYBIND_E2E_OUTPUT_ROOT:-${REPO_ROOT}/build/test_artifacts/controlnet_e2e}"
GENERATE_MATCH_LINE_PLOTS=1

usage() {
	cat <<'EOF'
Usage: scripts/controlnet_construct_e2e_unit_test_output.sh [--generate-match-line-plots] [--no-generate-match-line-plots]

Runs the two external-data DOM matching E2E tests while preserving outputs under
build/test_artifacts/controlnet_e2e by default.

Options:
  --generate-match-line-plots     Also save per-pair stereo-match line-plot PNG artifacts.
  --no-generate-match-line-plots  Explicitly disable line-plot PNG artifact generation (default).
  -h, --help                      Show this help message.

Environment overrides:
  PYTHON_EXECUTABLE               Python interpreter to use.
  ISIS_PYBIND_E2E_OUTPUT_ROOT     Root directory where preserved E2E outputs are written.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--generate-match-line-plots)
			GENERATE_MATCH_LINE_PLOTS=1
			;;
		--no-generate-match-line-plots)
			GENERATE_MATCH_LINE_PLOTS=0
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "Unknown argument: $1" >&2
			usage >&2
			exit 2
			;;
	esac
	shift
done

export ISIS_PYBIND_E2E_OUTPUT_ROOT="${OUTPUT_ROOT}"
export ISIS_PYBIND_E2E_GENERATE_MATCH_LINE_PLOTS="${GENERATE_MATCH_LINE_PLOTS}"

echo "Using Python: ${PYTHON_EXECUTABLE}"
echo "Preserved E2E output root: ${ISIS_PYBIND_E2E_OUTPUT_ROOT}"
echo "Generate stereo-pair match line plots: ${ISIS_PYBIND_E2E_GENERATE_MATCH_LINE_PLOTS}"

"${PYTHON_EXECUTABLE}" -m unittest tests.unitTest.controlnet_construct_e2e_unit_test.ControlNetConstructE2eUnitTest.test_lro_dom_matching_pipeline_end_to_end_for_all_overlap_pairs -v
"${PYTHON_EXECUTABLE}" -m unittest tests.unitTest.controlnet_construct_e2e_unit_test.ControlNetConstructE2eUnitTest.test_lro_dom_matching_cli_batch_pipeline_for_all_overlap_pairs -v