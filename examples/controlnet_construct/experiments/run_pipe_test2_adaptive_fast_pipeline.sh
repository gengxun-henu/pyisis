#!/usr/bin/env bash
# Reproduce the pipe_test2 adaptive fast ControlNet pipeline.
#
# This wrapper uses classic OpenCV SIFT/FLANN as the requested matcher and
# enables existing texture/sensor-model-lighting adaptive routing. Deep matchers
# remain escalation/reference paths; this script packages the fast CPU path.

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../../.." && pwd)

data_dir="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
output_root="/tmp/pipe_test2_adaptive_fast_pipeline"
python_executable="${PYTHON_EXECUTABLE:-python}"
profile="balanced"
adaptive_profile="balanced"
run_final_merge=0
validate_only=0

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh [options]

Run the pipe_test2 adaptive fast ControlNet pipeline:
  - requested matcher: flann
  - adaptive routing: enabled
  - adaptive profile: balanced by default
  - final cnetmerge: skipped unless --run-final-merge is provided

Options:
  --data-dir PATH       Directory with original_images.lis and doms.lis.
  --output-root PATH    Output root. Default: /tmp/pipe_test2_adaptive_fast_pipeline
  --python PATH         Python executable forwarded to run_pipeline_example.sh.
  --parameter-profile NAME
                        ControlNet parameter profile. Default: balanced.
  --adaptive-routing-profile NAME
                        Adaptive routing profile. Default: balanced.
  --validate-only       Validate resolved parameters and exit.
  --run-final-merge     Execute final cnetmerge.
  -h, --help            Show this help.

Runtime setup:
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate asp360_new
  export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
  export ISISDATA="$PWD/tests/data/isisdata/mockup"
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_option_value() {
  local option_name=$1
  local value=${2-}
  if [[ -z "$value" || "$value" == --* ]]; then
    die "missing value for $option_name"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)
      require_option_value "$1" "${2-}"
      data_dir=$2
      shift 2
      ;;
    --output-root)
      require_option_value "$1" "${2-}"
      output_root=$2
      shift 2
      ;;
    --python)
      require_option_value "$1" "${2-}"
      python_executable=$2
      shift 2
      ;;
    --parameter-profile)
      require_option_value "$1" "${2-}"
      profile=$2
      shift 2
      ;;
    --adaptive-routing-profile)
      require_option_value "$1" "${2-}"
      adaptive_profile=$2
      shift 2
      ;;
    --validate-only)
      validate_only=1
      shift
      ;;
    --run-final-merge)
      run_final_merge=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "unknown argument: $1"
      ;;
  esac
done

original_list="$data_dir/original_images.lis"
dom_list="$data_dir/doms.lis"
work_dir="$output_root/$profile"
logs_dir="$output_root/logs"
summary_json="$work_dir/reports/adaptive_fast_summary.json"
summary_md="$work_dir/reports/adaptive_fast_summary.md"

[[ -f "$original_list" ]] || die "missing original list: $original_list"
[[ -f "$dom_list" ]] || die "missing DOM list: $dom_list"
mkdir -p "$logs_dir"

command=(
  bash "$repo_root/examples/controlnet_construct/run_pipeline_example.sh"
  --work-dir "$work_dir"
  --original-list "$original_list"
  --dom-list "$dom_list"
  --python "$python_executable"
  --parameter-profile "$profile"
  --matcher-method flann
  --adaptive-routing
  --adaptive-routing-profile "$adaptive_profile"
)

if [[ "$validate_only" == "1" ]]; then
  command+=(--validate-parameters-only)
elif [[ "$run_final_merge" != "1" ]]; then
  command+=(--skip-final-merge)
fi

printf '===== pipe_test2 adaptive fast pipeline =====\n'
printf 'Command:'
printf ' %q' "${command[@]}"
printf '\n'

if [[ "$validate_only" == "1" ]]; then
  "${command[@]}"
else
  set +e
  /usr/bin/time -p "${command[@]}" 2>&1 | tee "$logs_dir/adaptive_fast_pipeline.log"
  status=${PIPESTATUS[0]}
  set -e
  printf '===== adaptive fast pipeline done status=%s log=%s =====\n' "$status" "$logs_dir/adaptive_fast_pipeline.log"
  [[ "$status" -eq 0 ]] || exit "$status"

  "$python_executable" "$repo_root/examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py" \
    "$work_dir" \
    --json-output "$summary_json" \
    --markdown-output "$summary_md"

  printf 'Summary JSON: %s\n' "$summary_json"
  printf 'Summary Markdown: %s\n' "$summary_md"
fi
