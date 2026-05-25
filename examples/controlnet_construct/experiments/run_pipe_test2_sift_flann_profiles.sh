#!/usr/bin/env bash
# Reproduce the pipe_test2 SIFT/FLANN parameter-profile comparison.
#
# Default mapping:
#   fast         -> run_pipeline_example.sh --parameter-profile aggressive --matcher-method flann
#   balanced     -> run_pipeline_example.sh --parameter-profile balanced   --matcher-method flann
#   high_quality -> run_pipeline_example.sh --parameter-profile conservative --matcher-method flann

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../../.." && pwd)

data_dir="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
output_root="/tmp/pipe_test2_profile_compare"
python_executable="${PYTHON_EXECUTABLE:-python}"
validate_only=0
run_final_merge=0
only_labels="fast,balanced,high_quality"

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/experiments/run_pipe_test2_sift_flann_profiles.sh [options]

Run the pipe_test2 ControlNet pipeline comparison with SIFT/FLANN fixed and
only the ControlNet parameter profile changed.

Options:
  --data-dir PATH       Input directory containing original_images.lis and doms.lis.
                        Default: /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2
  --output-root PATH    Output root for config, logs, and per-profile work dirs.
                        Default: /tmp/pipe_test2_profile_compare
  --python PATH         Python executable forwarded to run_pipeline_example.sh.
                        Default: $PYTHON_EXECUTABLE or python
  --only LIST           Comma-separated labels to run. Default: fast,balanced,high_quality
                        Supported labels: fast, balanced, high_quality
  --validate-only       Validate resolved parameters for each selected label and exit.
  --run-final-merge     Execute final cnetmerge instead of using --skip-final-merge.
  -h, --help            Show this help.

Runtime setup example:
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate asp360_new
  export PYTHONPATH="$PWD/build/python"
  export ISISDATA="$PWD/tests/data/isisdata/mockup"

Examples:
  bash examples/controlnet_construct/experiments/run_pipe_test2_sift_flann_profiles.sh --validate-only

  bash examples/controlnet_construct/experiments/run_pipe_test2_sift_flann_profiles.sh \
    --only fast,balanced
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

profile_for_label() {
  case "$1" in
    fast) printf '%s\n' "aggressive" ;;
    balanced) printf '%s\n' "balanced" ;;
    high_quality) printf '%s\n' "conservative" ;;
    *) die "unsupported label '$1'. Use fast, balanced, or high_quality." ;;
  esac
}

write_sift_flann_config() {
  local config_path=$1
  mkdir -p "$(dirname "$config_path")"
  cat >"$config_path" <<'JSON'
{
  "NetworkId": "pipe_test2_sift_flann_profile_compare",
  "TargetName": "Moon",
  "UserName": "gengxun",
  "Description": "pipe_test2 SIFT/FLANN parameter profile comparison.",
  "PointIdPrefix": "P",
  "PairId": "S1",
  "ImageMatch": {
    "band": 1,
    "max_image_dimension": 2000,
    "sub_block_size_x": 512,
    "sub_block_size_y": 512,
    "overlap_size_x": 64,
    "overlap_size_y": 64,
    "minimum_value": null,
    "maximum_value": null,
    "lower_percent": 0.5,
    "upper_percent": 99.5,
    "invalid_values": [],
    "special_pixel_abs_threshold": 1e300,
    "min_valid_pixels": 64,
    "enable_tile_validity_prefilter": true,
    "tile_validity_cell_width": 512,
    "tile_validity_cell_height": 512,
    "match_preset_path": null,
    "deep_matcher_config_path": null,
    "enable_adaptive_routing": false,
    "ratio_test": 0.75,
    "max_features": 1000,
    "sift_octave_layers": 3,
    "sift_contrast_threshold": 0.04,
    "sift_edge_threshold": 10.0,
    "sift_sigma": 1.6,
    "use_gpu": false,
    "crop_expand_pixels": 100,
    "min_overlap_size": 16,
    "visualization_mode": "auto",
    "memory_profile": "balanced",
    "visualization_target_long_edge": 1024,
    "low_resolution_matching_target_long_edge": 1024,
    "preview_crop_margin_pixels": 256,
    "preview_cache_source": "auto",
    "use_parallel_cpu": true,
    "omit_tile_details": true,
    "write_match_visualization": true,
    "match_visualization_scale": 0.2
  }
}
JSON
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)
      [[ $# -ge 2 ]] || die "missing value for --data-dir"
      data_dir=$2
      shift 2
      ;;
    --output-root)
      [[ $# -ge 2 ]] || die "missing value for --output-root"
      output_root=$2
      shift 2
      ;;
    --python)
      [[ $# -ge 2 ]] || die "missing value for --python"
      python_executable=$2
      shift 2
      ;;
    --only)
      [[ $# -ge 2 ]] || die "missing value for --only"
      only_labels=$2
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
config_path="$output_root/pipe_test2_sift_flann_profile_config.json"
logs_dir="$output_root/logs"

[[ -f "$original_list" ]] || die "missing original list: $original_list"
[[ -f "$dom_list" ]] || die "missing DOM list: $dom_list"

mkdir -p "$logs_dir"
write_sift_flann_config "$config_path"

IFS=',' read -r -a labels <<<"$only_labels"

for label in "${labels[@]}"; do
  label=${label//[[:space:]]/}
  [[ -n "$label" ]] || continue
  profile=$(profile_for_label "$label")
  work_dir="$output_root/$label"
  log_path="$logs_dir/$label.log"

  command=(
    bash "$repo_root/examples/controlnet_construct/run_pipeline_example.sh"
    --work-dir "$work_dir"
    --original-list "$original_list"
    --dom-list "$dom_list"
    --config "$config_path"
    --python "$python_executable"
    --parameter-profile "$profile"
    --matcher-method flann
  )

  if [[ "$validate_only" == "1" ]]; then
    command+=(--validate-parameters-only)
  elif [[ "$run_final_merge" != "1" ]]; then
    command+=(--skip-final-merge)
  fi

  printf '===== %s: %s -> %s =====\n' "$label" "$label" "$profile"
  printf 'Command:'
  printf ' %q' "${command[@]}"
  printf '\n'

  if [[ "$validate_only" == "1" ]]; then
    "${command[@]}"
  else
    /usr/bin/time -p "${command[@]}" 2>&1 | tee "$log_path"
    status=${PIPESTATUS[0]}
    printf '===== %s done status=%s log=%s =====\n' "$label" "$status" "$log_path"
    [[ "$status" -eq 0 ]] || exit "$status"
  fi
done

