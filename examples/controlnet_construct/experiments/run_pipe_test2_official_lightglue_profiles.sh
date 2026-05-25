#!/usr/bin/env bash
# Reproduce the pipe_test2 official LightGlue extractor comparison.
#
# Matching is performed on DOM images from doms.lis. original_images.lis is
# still passed so the pipeline can convert DOM tie points back to original-image
# coordinates and build pairwise ControlNets.
#
# Default mapping:
#   superpoint_lightglue -> lightglue_official_superpoint.json
#   disk_lightglue       -> lightglue_official_disk.json
#   sift_lightglue       -> lightglue_official_sift.json
#
# Default workflow:
#   1. asp360_new exports deep-match tile manifests.
#   2. deep-learning runs each manifest with official LightGlue dependencies.
#   3. asp360_new imports manifest results and continues ControlNet construction.

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../../.." && pwd)

data_dir="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
output_root="/tmp/pipe_test2_official_lightglue_compare"
python_executable="${PYTHON_EXECUTABLE:-python}"
conda_sh="${PYISIS_CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
deep_learning_env="${DEEP_LEARNING_CONDA_ENV:-deep-learning}"
deep_match_mode="split"
deep_match_device="auto"
deep_match_num_workers=1
max_deep_match_num_workers=64
deep_match_torch_num_threads=""
force_rerun_deep_match=0
validate_only=0
run_final_merge=0
only_labels="superpoint_lightglue,disk_lightglue,sift_lightglue"

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh [options]

Run the pipe_test2 ControlNet pipeline comparison with official LightGlue fixed
and only the official extractor preset changed.

The matching step uses DOM images from doms.lis. original_images.lis is used by
later ControlNet steps to convert DOM tie points back to original-image
coordinates.

Options:
  --data-dir PATH       Input directory containing original_images.lis and doms.lis.
                        Default: /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2
  --output-root PATH    Output root for config, logs, and per-method work dirs.
                        Default: /tmp/pipe_test2_official_lightglue_compare
  --python PATH         Python executable forwarded to run_pipeline_example.sh.
                        Default: $PYTHON_EXECUTABLE or python
  --deep-match-mode MODE
                        Deep matcher workflow. Default: split.
                        split: export in asp360_new, run manifests in deep-learning,
                               then import in asp360_new.
                        direct/export/import: forwarded to run_pipeline_example.sh.
  --deep-learning-env NAME
                        Conda env used for split-mode manifest execution.
                        Default: $DEEP_LEARNING_CONDA_ENV or deep-learning.
  --conda-sh PATH       Conda shell hook. Default: $PYISIS_CONDA_SH or
                        $HOME/miniconda3/etc/profile.d/conda.sh.
  --device MODE         Device for run_deep_match_manifest.py in split mode.
                        Supported values: auto, cpu, cuda. Default: auto.
                        Explicit cuda currently requires --deep-match-num-workers 1.
  --deep-match-num-workers N
                        Number of parallel manifest workers in split mode.
                        Range: 1-64. Default: 1.
  --deep-match-torch-num-threads N
                        Torch thread count forwarded to manifest workers in split mode.
                        Default: unset.
  --force-rerun-deep-match
                        Recompute deep-match manifest tasks instead of skipping existing results.
  --only LIST           Comma-separated labels to run.
                        Default: superpoint_lightglue,disk_lightglue,sift_lightglue
                        Supported labels: superpoint_lightglue, disk_lightglue, sift_lightglue
  --validate-only       Validate resolved parameters for each selected label and exit.
  --run-final-merge     Execute final cnetmerge instead of using --skip-final-merge.
  -h, --help            Show this help.

Runtime setup example:
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate asp360_new
  export PYTHONPATH="$PWD/build/python"
  export ISISDATA="$PWD/tests/data/isisdata/mockup"

Examples:
  bash examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh --validate-only

  bash examples/controlnet_construct/experiments/run_pipe_test2_official_lightglue_profiles.sh \
    --only superpoint_lightglue,sift_lightglue
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_positive_integer() {
  local option_name=$1
  local value=$2
  case "$value" in
    ''|*[!0-9]*) die "$option_name must be a positive integer" ;;
  esac
  (( 10#$value > 0 )) || die "$option_name must be a positive integer"
}

require_option_value() {
  local option_name=$1
  local value=${2-}
  if [[ -z "$value" || "$value" == --* ]]; then
    die "missing value for $option_name"
  fi
}

check_manifest_summary_status() {
  local summary_path=$1
  python - "$summary_path" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
try:
    with summary_path.open("r", encoding="utf-8") as stream:
        summary = json.load(stream)
except Exception as exc:
    print(f"ERROR: unable to read manifest summary {summary_path}: {exc}", file=sys.stderr)
    sys.exit(1)

status = summary.get("status")
failed = summary.get("failed_task_count")
incomplete = summary.get("incomplete_task_count")
skipped = summary.get("skipped_existing_task_count")
print(
    "Manifest summary status: "
    f"status={status} failed={failed} incomplete={incomplete} skipped_existing={skipped}"
)
if status != "completed":
    print(f"ERROR: manifest summary is not completed: {summary_path}", file=sys.stderr)
    sys.exit(1)
PY
}

preset_for_label() {
  case "$1" in
    superpoint_lightglue) printf '%s\n' "$repo_root/examples/controlnet_construct/presets/lightglue_official_superpoint.json" ;;
    disk_lightglue) printf '%s\n' "$repo_root/examples/controlnet_construct/presets/lightglue_official_disk.json" ;;
    sift_lightglue) printf '%s\n' "$repo_root/examples/controlnet_construct/presets/lightglue_official_sift.json" ;;
    *) die "unsupported label '$1'. Use superpoint_lightglue, disk_lightglue, or sift_lightglue." ;;
  esac
}

write_lightglue_config() {
  local config_path=$1
  mkdir -p "$(dirname "$config_path")"
  cat >"$config_path" <<'JSON'
{
  "NetworkId": "pipe_test2_official_lightglue_compare",
  "TargetName": "Moon",
  "UserName": "gengxun",
  "Description": "pipe_test2 official LightGlue extractor comparison.",
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
    "enable_low_resolution_offset_estimation": true,
    "low_resolution_level": 3,
    "low_resolution_max_mean_reprojection_error_pixels": 3.0,
    "low_resolution_min_retained_match_count": 5,
    "low_resolution_max_mean_projected_offset_meters": 2000.0,
    "visualization_mode": "auto",
    "memory_profile": "balanced",
    "visualization_target_long_edge": 1024,
    "low_resolution_matching_target_long_edge": 1024,
    "preview_crop_margin_pixels": 256,
    "preview_cache_source": "auto",
    "use_parallel_cpu": true,
    "num_worker_parallel_cpu": 4,
    "omit_tile_details": true,
    "write_match_visualization": true,
    "match_visualization_scale": 0.2
  }
}
JSON
}

run_deep_match_manifests() {
  local work_dir=$1
  local label=$2
  local manifest_log_path=$3
  local manifest_root="$work_dir/deep_match_workspaces"

  [[ -d "$manifest_root" ]] || die "missing deep-match manifest root for $label: $manifest_root"

  mapfile -t manifests < <(find "$manifest_root" -mindepth 2 -maxdepth 2 -name tasks.json -type f | sort)
  [[ "${#manifests[@]}" -gt 0 ]] || die "no deep-match manifests found for $label under $manifest_root"

  printf '===== %s: running %s manifest(s) in %s =====\n' "$label" "${#manifests[@]}" "$deep_learning_env" | tee -a "$manifest_log_path"
  for manifest_path in "${manifests[@]}"; do
    local summary_path
    summary_path="$(dirname "$manifest_path")/manifest_run_summary.json"
    printf 'Manifest: %s\n' "$manifest_path" | tee -a "$manifest_log_path"
    (
      set +u
      source "$conda_sh"
      conda activate "$deep_learning_env"
      set -u
      export PYTHONPATH="$repo_root/examples${PYTHONPATH:+:$PYTHONPATH}"
      manifest_command=(
        python "$repo_root/examples/learning_methods/run_deep_match_manifest.py"
        "$manifest_path"
        --device "$deep_match_device"
        --summary-output "$summary_path"
        --num-workers "$deep_match_num_workers"
      )
      if [[ -n "$deep_match_torch_num_threads" ]]; then
        manifest_command+=(--torch-num-threads "$deep_match_torch_num_threads")
      fi
      if [[ "$force_rerun_deep_match" == "1" ]]; then
        manifest_command+=(--force-rerun)
      else
        manifest_command+=(--skip-existing)
      fi
      printf 'Manifest command:'
      printf ' %q' "${manifest_command[@]}"
      printf '\n'
      "${manifest_command[@]}"
      check_manifest_summary_status "$summary_path"
    ) 2>&1 | tee -a "$manifest_log_path"
    local status=${PIPESTATUS[0]}
    [[ "$status" -eq 0 ]] || return "$status"
  done
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
    --deep-match-mode)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"
      deep_match_mode=$2
      shift 2
      ;;
    --deep-learning-env)
      [[ $# -ge 2 ]] || die "missing value for --deep-learning-env"
      deep_learning_env=$2
      shift 2
      ;;
    --conda-sh)
      [[ $# -ge 2 ]] || die "missing value for --conda-sh"
      conda_sh=$2
      shift 2
      ;;
    --device)
      [[ $# -ge 2 ]] || die "missing value for --device"
      deep_match_device=$2
      shift 2
      ;;
    --deep-match-num-workers)
      require_option_value "--deep-match-num-workers" "${2-}"
      deep_match_num_workers=$2
      shift 2
      ;;
    --deep-match-torch-num-threads)
      require_option_value "--deep-match-torch-num-threads" "${2-}"
      deep_match_torch_num_threads=$2
      shift 2
      ;;
    --force-rerun-deep-match)
      force_rerun_deep_match=1
      shift
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
config_path="$output_root/pipe_test2_official_lightglue_config.json"
logs_dir="$output_root/logs"

[[ -f "$original_list" ]] || die "missing original list: $original_list"
[[ -f "$dom_list" ]] || die "missing DOM list: $dom_list"
[[ -f "$conda_sh" ]] || die "missing conda shell hook: $conda_sh"
case "$deep_match_mode" in
  split|direct|export|import) ;;
  *) die "unsupported --deep-match-mode: $deep_match_mode" ;;
esac
case "$deep_match_device" in
  auto|cpu|cuda) ;;
  *) die "unsupported --device: $deep_match_device" ;;
esac
require_positive_integer "--deep-match-num-workers" "$deep_match_num_workers"
if (( 10#$deep_match_num_workers > max_deep_match_num_workers )); then
  die "--deep-match-num-workers must be between 1 and $max_deep_match_num_workers"
fi
if [[ "$deep_match_device" == "cuda" && "$deep_match_num_workers" != "1" ]]; then
  die "--device cuda is not supported with --deep-match-num-workers > 1"
fi
if [[ -n "$deep_match_torch_num_threads" ]]; then
  require_positive_integer "--deep-match-torch-num-threads" "$deep_match_torch_num_threads"
fi

mkdir -p "$logs_dir"
write_lightglue_config "$config_path"

IFS=',' read -r -a labels <<<"$only_labels"

for label in "${labels[@]}"; do
  label=${label//[[:space:]]/}
  [[ -n "$label" ]] || continue
  preset_path=$(preset_for_label "$label")
  [[ -f "$preset_path" ]] || die "missing preset for $label: $preset_path"
  work_dir="$output_root/$label"
  log_path="$logs_dir/$label.log"
  export_log_path="$logs_dir/$label.export.log"
  manifest_log_path="$logs_dir/$label.manifest.log"
  import_log_path="$logs_dir/$label.import.log"

  base_command=(
    bash "$repo_root/examples/controlnet_construct/run_pipeline_example.sh"
    --work-dir "$work_dir"
    --original-list "$original_list"
    --dom-list "$dom_list"
    --config "$config_path"
    --python "$python_executable"
    --matcher-method lightglue
    --deep-match-config-path "$preset_path"
  )

  printf '===== %s: official LightGlue preset %s =====\n' "$label" "$preset_path"

  if [[ "$validate_only" == "1" ]]; then
    command=("${base_command[@]}" --deep-match-mode direct --validate-parameters-only)
    printf 'Command:'
    printf ' %q' "${command[@]}"
    printf '\n'
    "${command[@]}"
  elif [[ "$deep_match_mode" == "split" ]]; then
    export_command=("${base_command[@]}" --deep-match-mode export)
    import_command=(
      "${base_command[@]}"
      --deep-match-mode import
      --deep-match-manifest-dir "$work_dir/deep_match_workspaces"
      --deep-match-manifest-summary "$work_dir/reports/deep_match_manifests.json"
    )
    if [[ "$run_final_merge" != "1" ]]; then
      import_command+=(--skip-final-merge)
    fi

    printf 'Export command:'
    printf ' %q' "${export_command[@]}"
    printf '\n'
    /usr/bin/time -p "${export_command[@]}" 2>&1 | tee "$export_log_path"
    status=${PIPESTATUS[0]}
    printf '===== %s export done status=%s log=%s =====\n' "$label" "$status" "$export_log_path"
    [[ "$status" -eq 0 ]] || exit "$status"

    : >"$manifest_log_path"
    run_deep_match_manifests "$work_dir" "$label" "$manifest_log_path"
    status=$?
    printf '===== %s manifest execution done status=%s log=%s =====\n' "$label" "$status" "$manifest_log_path"
    [[ "$status" -eq 0 ]] || exit "$status"

    printf 'Import command:'
    printf ' %q' "${import_command[@]}"
    printf '\n'
    /usr/bin/time -p "${import_command[@]}" 2>&1 | tee "$import_log_path"
    status=${PIPESTATUS[0]}
    printf '===== %s import done status=%s log=%s =====\n' "$label" "$status" "$import_log_path"
    [[ "$status" -eq 0 ]] || exit "$status"
  else
    command=("${base_command[@]}" --deep-match-mode "$deep_match_mode")
    if [[ "$run_final_merge" != "1" && "$deep_match_mode" != "export" ]]; then
      command+=(--skip-final-merge)
    fi
    printf 'Command:'
    printf ' %q' "${command[@]}"
    printf '\n'
    /usr/bin/time -p "${command[@]}" 2>&1 | tee "$log_path"
    status=${PIPESTATUS[0]}
    printf '===== %s done status=%s log=%s =====\n' "$label" "$status" "$log_path"
    [[ "$status" -eq 0 ]] || exit "$status"
  fi
done
