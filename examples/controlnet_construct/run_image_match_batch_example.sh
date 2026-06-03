#!/usr/bin/env bash

# Batch image-match example runner for images_overlap.lis stereo pairs.
#
# Author: Geng Xun
# Created: 2026-05-11
# Updated: 2026-05-11  Geng Xun added top-of-file metadata so example shell entrypoints follow the repository's example-file header convention.
# Updated: 2026-05-16  Geng Xun added deep-match export/import forwarding and manifest summary output for cross-conda handoff workflows.
# Updated: 2026-05-19  Geng Xun added deep matcher config path CLI/config forwarding for batch matching.
# Updated: 2026-05-19  Geng Xun aligned batch wrapper config precedence, adaptive routing flags, and resolved deep matcher config path logging with the main pipeline wrapper.
# Updated: 2026-05-27  Geng Xun added explicit OpenCV thread-limit forwarding for batch DOM matching.

set -euo pipefail

CALLER_CWD=$(pwd)
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD="0.05"
DEFAULT_INVALID_PIXEL_RADIUS="1"

log() {
  printf '[image-match-batch] %s\n' "$*"
}

warn() {
  printf '[image-match-batch] warning: %s\n' "$*" >&2
}

die() {
  printf '[image-match-batch] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_image_match_batch_example.sh [options] [-- image_match_extra_args...]

Batch-run examples/image_match/image_match.py for all pairs listed in images_overlap.lis.

Defaults assume a work directory layout like:
  work/original_images.lis
  work/doms_scaled.lis (or work/doms.lis)
  work/images_overlap.lis
  work/dom_keys/
  work/match_metadata/
  work/match_viz/            # pre-RANSAC drawMatches PNGs from examples/image_match/image_match.py
  work/deep_match_manifests.json

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --pair-list PATH                Overlap pair list path. Default: <work-dir>/images_overlap.lis
  --config PATH                   Optional config JSON. Its ImageMatch section is forwarded to examples/image_match/image_match.py
                                  as default matching parameters, and this wrapper also reads selected fields for overrides.
  --output-key-dir PATH           Output .key directory. Default: <work-dir>/dom_keys
  --metadata-dir PATH             Metadata JSON output directory. Default: <work-dir>/match_metadata
  --match-viz-dir PATH            Pre-RANSAC match visualization PNG directory.
                                  Default: <work-dir>/match_viz
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --use-parallel-cpu              Forward explicit CPU tile parallelism enable flag to examples/image_match/image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in examples/image_match/image_match.py and force serial tile matching
  --num-worker-parallel-cpu N     Maximum worker-process count forwarded to examples/image_match/image_match.py when CPU parallelism is enabled.
                                  Default: 8. If omitted, this script falls back to config JSON field
                                  ImageMatch.num_worker_parallel_cpu when present. Valid range: 1~4096.
  --opencv-num-threads N          Optional OpenCV internal CPU thread limit for SIFT/FLANN work.
                                  If omitted, this script falls back to config JSON field
                                  ImageMatch.opencv_num_threads when present. Use 1 with multiple CPU
                                  workers to avoid OpenCV/process-pool oversubscription.
  --valid-pixel-percent-threshold VALUE
                                 Minimum valid-pixel ratio forwarded to examples/image_match/image_match.py.
                                 Default: 0.05 unless omitted and resolved from --config.
  --min-valid-pixels N           Minimum valid pixels per tile before matching. Default: image_match.py default.
  --valid-intensity-lower-percent VALUE
                                 Lower intensity percentile masked before matching. Default: image_match.py default.
  --valid-intensity-upper-percent VALUE
                                 Upper intensity percentile masked before matching. Default: image_match.py default.
  --invalid-pixel-radius N        Suppress feature detection near invalid pixels or image borders.
                                  Default: 1 unless omitted and resolved from --config.
  --dom-source-metadata-csv PATH   CSV mapping DOM cubes to source/original camera cubes for physical tile illumination.
  --matcher-method NAME           Matcher backend forwarded to examples/image_match/image_match.py.
                                  Supported values: bf, flann, superglue, lightglue, loftr.
                                  Default: bf unless omitted and resolved from --config.
  --match-preset-path PATH        Forwarded to examples/image_match/image_match.py to select a match preset.
                                  Relative CLI paths resolve first from the current working directory, then
                                  from the repository root. If omitted, this script falls back to config JSON field
                                  ImageMatch.match_preset_path when present. Cannot be combined with
                                  --matcher-method or --deep-match-config-path.
  --deep-match-config-path PATH   Path to deep matcher preset JSON config.
                                  If omitted, this script falls back to config JSON field
                                  ImageMatch.deep_matcher_config_path when present. Relative config values
                                  are resolved first against the config file directory, then against the repo root.
  --adaptive-routing              Enable image_match.py adaptive routing. If omitted, this script falls back to
                                  config JSON field ImageMatch.enable_adaptive_routing when present; otherwise disabled.
  --no-adaptive-routing           Disable image_match.py adaptive routing even if config enables it.
  --adaptive-routing-profile NAME Forwarded to image_match.py as the named adaptive-routing quality profile.
                                  Supported values: balanced, strict, relaxed, fast. If omitted, this script falls back
                                  to config JSON field ImageMatch.adaptive_routing_profile when present; otherwise balanced.
  --deep-match-mode MODE          Deep-match execution mode forwarded to image_match.py: direct, export, or import.
                                  Default: direct. Use export in asp360_new to write manifest workspaces;
                                  use import after deep-learning results have been written.
  --deep-match-temp-root-dir PATH Root directory for exported deep-match workspaces.
                                  Default: <work-dir>/deep_match_workspaces when --deep-match-mode export.
  --deep-match-manifest-dir PATH  Directory containing per-pair manifest workspaces for import mode.
                                  Each pair expects <PATH>/<pair_tag>/tasks.json.
  --deep-match-manifest-summary PATH
                                  JSON summary of per-pair manifest paths. Default: <work-dir>/deep_match_manifests.json
  --enable-low-resolution-offset-estimation
                                  Enable low-resolution DOM matching to estimate projected offset before
                                  the full-resolution overlap crop is prepared.
  --low-resolution-level N        Low-resolution pyramid level for projected-offset estimation.
                                  Default: 3 unless omitted and resolved from --config.
  --low-resolution-max-mean-reprojection-error-pixels VALUE
                                  Maximum trimmed-mean low-resolution homography reprojection error allowed
                                  before coarse projected offset falls back to zero. Default: 3.0 unless omitted
                                  and resolved from --config.
  --low-resolution-min-retained-match-count N
                                  Minimum retained low-resolution RANSAC match count required before
                                  projected-offset statistics are trusted. Default: 5 unless omitted and
                                  resolved from --config.
  --low-resolution-max-mean-projected-offset-meters VALUE
                                  Maximum allowed magnitude of the mean low-resolution projected offset.
                                  Unit: meters. Default: examples/image_match/image_match.py default unless omitted and resolved
                                  from --config.
  --skip-existing                 Skip pairs whose left/right key files already exist
  -h, --help                      Show this help message

Default behavior:
  - Terminal output stays compact: this wrapper mainly prints batch progress and pair-level progress lines.
    Detailed per-pair diagnostics continue to live in <metadata-dir>/ as JSON sidecars.
  - If you need the full match result payload in a separate JSON file, forward
    examples/image_match/image_match.py's own option after --, for example: -- --result-output <path>
  - CPU tile parallelism is enabled unless --no-parallel-cpu is provided.
  - examples/image_match/image_match.py writes pre-RANSAC match visualization PNGs by default.
  - To disable those PNGs, forward: -- --no-write-match-visualization

Anything after -- is forwarded directly to examples/image_match/image_match.py.

Examples:
  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --valid-pixel-percent-threshold 0.05

  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --config examples/controlnet_construct/controlnet_config.example.json \
    -- \
    --ratio-test 0.8 \
    --max-image-dimension 1024 \
    --sub-block-size-x 1024 \
    --sub-block-size-y 1024

  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --num-worker-parallel-cpu 4 \
    --no-parallel-cpu \
    -- \
    --no-write-match-visualization

  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --matcher-method lightglue \
    --deep-match-mode export
EOF
}

require_file() {
  local path=$1
  [[ -f "$path" ]] || die "required file not found: $path"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

resolve_default_dom_list() {
  local scaled_list=$1
  local raw_list=$2
  if [[ -f "$scaled_list" ]]; then
    printf '%s\n' "$scaled_list"
    return 0
  fi
  if [[ -f "$raw_list" ]]; then
    printf '%s\n' "$raw_list"
    return 0
  fi
  die "could not find a DOM list; checked: $scaled_list and $raw_list"
}

extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  local container_order=${3:-image-match-first}
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/image_match/image_match.py" \
    --config "$config_path" \
    --print-config-default "$field_name" \
    --print-config-default-container-order "$container_order"
}

resolve_config_relative_path() {
  local raw_path=$1
  local config_path=$2

  [[ -n "$raw_path" ]] || return 0
  if [[ "$raw_path" = /* ]]; then
    printf '%s\n' "$raw_path"
    return 0
  fi

  if [[ -n "$config_path" ]]; then
    local config_dir
    config_dir=$(cd -- "$(dirname -- "$config_path")" && pwd)
    local config_relative_candidate="$config_dir/$raw_path"
    if [[ -f "$config_relative_candidate" ]]; then
      printf '%s\n' "$(cd -- "$(dirname -- "$config_relative_candidate")" && pwd)/$(basename -- "$config_relative_candidate")"
      return 0
    fi
  fi

  local repo_relative_candidate="$REPO_ROOT/$raw_path"
  if [[ -f "$repo_relative_candidate" ]]; then
    printf '%s\n' "$(cd -- "$(dirname -- "$repo_relative_candidate")" && pwd)/$(basename -- "$repo_relative_candidate")"
    return 0
  fi

  printf '%s\n' "$REPO_ROOT/$raw_path"
}

resolve_cli_relative_path() {
  local raw_path=$1

  [[ -n "$raw_path" ]] || return 0
  if [[ "$raw_path" = /* ]]; then
    printf '%s\n' "$raw_path"
    return 0
  fi

  local caller_relative_candidate="$CALLER_CWD/$raw_path"
  if [[ -f "$caller_relative_candidate" ]]; then
    printf '%s\n' "$(cd -- "$(dirname -- "$caller_relative_candidate")" && pwd)/$(basename -- "$caller_relative_candidate")"
    return 0
  fi

  local repo_relative_candidate="$REPO_ROOT/$raw_path"
  if [[ -f "$repo_relative_candidate" ]]; then
    printf '%s\n' "$(cd -- "$(dirname -- "$repo_relative_candidate")" && pwd)/$(basename -- "$repo_relative_candidate")"
    return 0
  fi

  printf '%s\n' "$REPO_ROOT/$raw_path"
}

resolve_match_preset_shell_assignments() {
  local preset_path=$1
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/match_preset_config.py" \
    "$preset_path" \
    --shell-assignments
}

apply_match_preset_path() {
  local preset_path=$1
  local assignments
  local MATCHER_METHOD=""
  local DEEP_MATCHER_CONFIG_PATH=""
  assignments=$(resolve_match_preset_shell_assignments "$preset_path")
  eval "$assignments"
  matcher_method="$MATCHER_METHOD"
  deep_match_config_path="$DEEP_MATCHER_CONFIG_PATH"
}

initialize_deep_match_manifest_summary() {
  local summary_path=$1
  "$PYTHON_EXECUTABLE" - "$summary_path" "$deep_match_mode" "$DEEP_MATCH_TEMP_ROOT_DIR" "$DEEP_MATCH_MANIFEST_DIR" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
payload = {
    "deep_match_mode": sys.argv[2],
    "deep_match_temp_root_dir": sys.argv[3] or None,
    "deep_match_manifest_dir": sys.argv[4] or None,
    "pairs": [],
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

append_deep_match_manifest_summary() {
  local summary_path=$1
  local pair_tag=$2
  local metadata_path=$3
  "$PYTHON_EXECUTABLE" - "$summary_path" "$pair_tag" "$metadata_path" "$deep_match_mode" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
pair_tag = sys.argv[2]
metadata_path = Path(sys.argv[3])
mode = sys.argv[4]

payload = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {"pairs": []}
entry = {"pair_tag": pair_tag, "metadata_path": str(metadata_path), "deep_match_mode": mode}
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    section = metadata.get("deep_match_export") if mode == "export" else metadata.get("deep_match_import")
    entry["status"] = metadata.get("status")
    entry["point_count"] = metadata.get("point_count")
    if isinstance(section, dict):
        for key in ("manifest_path", "workspace_root", "results_dir", "logs_dir", "pair_id", "exported_task_count", "imported_task_count", "missing_result_count", "failed_task_count"):
            if key in section:
                entry[key] = section[key]
else:
    entry["status"] = "metadata_missing"

payload.setdefault("pairs", []).append(entry)
summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

main() {
  local work_dir_input="$DEFAULT_WORK_DIR_RELATIVE"
  local original_list_input=""
  local dom_list_input=""
  local pair_list_input=""
  local config_input=""
  local output_key_dir_input=""
  local metadata_dir_input=""
  local match_viz_dir_input=""
  local skip_existing="0"
  local use_parallel_cpu="1"
  local explicit_use_parallel_cpu=""
  local num_worker_parallel_cpu="8"
  local explicit_num_worker_parallel_cpu=""
  local opencv_num_threads=""
  local explicit_opencv_num_threads=""
  local explicit_threshold=""
  local min_valid_pixels=""
  local explicit_min_valid_pixels=""
  local valid_intensity_lower_percent=""
  local explicit_valid_intensity_lower_percent=""
  local valid_intensity_upper_percent=""
  local explicit_valid_intensity_upper_percent=""
  local invalid_pixel_radius="$DEFAULT_INVALID_PIXEL_RADIUS"
  local explicit_invalid_pixel_radius=""
  local dom_source_metadata_csv_input=""
  local matcher_method="bf"
  local explicit_matcher_method=""
  local explicit_match_preset_path=""
  local match_preset_path=""
  local deep_match_config_path=""
  local explicit_deep_match_config_path=""
  local adaptive_routing="0"
  local explicit_adaptive_routing=""
  local adaptive_routing_profile="balanced"
  local explicit_adaptive_routing_profile=""
  local deep_match_mode="direct"
  local deep_match_temp_root_dir_input=""
  local deep_match_manifest_dir_input=""
  local deep_match_manifest_summary_input=""
  local enable_low_resolution_offset_estimation="0"
  local explicit_enable_low_resolution_offset_estimation=""
  local low_resolution_level="3"
  local explicit_low_resolution_level=""
  local low_resolution_max_mean_reprojection_error_pixels="3.0"
  local explicit_low_resolution_max_mean_reprojection_error_pixels=""
  local low_resolution_min_retained_match_count="5"
  local explicit_low_resolution_min_retained_match_count=""
  local low_resolution_max_mean_projected_offset_meters="0.0"
  local explicit_low_resolution_max_mean_projected_offset_meters=""
  local config_threshold=""
  local forwarded_args=()

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --work-dir)
        [[ $# -ge 2 ]] || die "missing value for --work-dir"
        work_dir_input=$2
        shift 2
        ;;
      --original-list)
        [[ $# -ge 2 ]] || die "missing value for --original-list"
        original_list_input=$2
        shift 2
        ;;
      --dom-list)
        [[ $# -ge 2 ]] || die "missing value for --dom-list"
        dom_list_input=$2
        shift 2
        ;;
      --pair-list)
        [[ $# -ge 2 ]] || die "missing value for --pair-list"
        pair_list_input=$2
        shift 2
        ;;
      --config)
        [[ $# -ge 2 ]] || die "missing value for --config"
        config_input=$2
        shift 2
        ;;
      --output-key-dir)
        [[ $# -ge 2 ]] || die "missing value for --output-key-dir"
        output_key_dir_input=$2
        shift 2
        ;;
      --metadata-dir)
        [[ $# -ge 2 ]] || die "missing value for --metadata-dir"
        metadata_dir_input=$2
        shift 2
        ;;
      --match-viz-dir)
        [[ $# -ge 2 ]] || die "missing value for --match-viz-dir"
        match_viz_dir_input=$2
        shift 2
        ;;
      --python)
        [[ $# -ge 2 ]] || die "missing value for --python"
        PYTHON_EXECUTABLE=$2
        shift 2
        ;;
      --use-parallel-cpu)
        use_parallel_cpu="1"
        explicit_use_parallel_cpu="1"
        shift
        ;;
      --no-parallel-cpu)
        use_parallel_cpu="0"
        explicit_use_parallel_cpu="0"
        shift
        ;;
      --num-worker-parallel-cpu)
        [[ $# -ge 2 ]] || die "missing value for --num-worker-parallel-cpu"
        num_worker_parallel_cpu=$2
        explicit_num_worker_parallel_cpu=$2
        shift 2
        ;;
      --opencv-num-threads)
        [[ $# -ge 2 ]] || die "missing value for --opencv-num-threads"
        opencv_num_threads=$2
        explicit_opencv_num_threads=$2
        shift 2
        ;;
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        explicit_threshold=$2
        shift 2
        ;;
      --min-valid-pixels)
        [[ $# -ge 2 ]] || die "missing value for --min-valid-pixels"
        min_valid_pixels=$2
        explicit_min_valid_pixels=$2
        shift 2
        ;;
      --valid-intensity-lower-percent)
        [[ $# -ge 2 ]] || die "missing value for --valid-intensity-lower-percent"
        valid_intensity_lower_percent=$2
        explicit_valid_intensity_lower_percent=$2
        shift 2
        ;;
      --valid-intensity-upper-percent)
        [[ $# -ge 2 ]] || die "missing value for --valid-intensity-upper-percent"
        valid_intensity_upper_percent=$2
        explicit_valid_intensity_upper_percent=$2
        shift 2
        ;;
      --invalid-pixel-radius)
        [[ $# -ge 2 ]] || die "missing value for --invalid-pixel-radius"
        invalid_pixel_radius=$2
        explicit_invalid_pixel_radius=$2
        shift 2
        ;;
      --dom-source-metadata-csv)
        [[ $# -ge 2 ]] || die "missing value for --dom-source-metadata-csv"
        dom_source_metadata_csv_input=$2
        shift 2
        ;;
      --match-preset-path)
        [[ $# -ge 2 ]] || die "missing value for --match-preset-path"
        match_preset_path=$2
        explicit_match_preset_path=$2
        shift 2
        ;;
      --matcher-method)
        [[ $# -ge 2 ]] || die "missing value for --matcher-method"
        matcher_method=$2
        explicit_matcher_method=$2
        shift 2
        ;;
      --deep-match-config-path)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-config-path"
        deep_match_config_path=$2
        explicit_deep_match_config_path=$2
        shift 2
        ;;
      --adaptive-routing)
        adaptive_routing="1"
        explicit_adaptive_routing="1"
        shift
        ;;
      --no-adaptive-routing)
        adaptive_routing="0"
        explicit_adaptive_routing="0"
        shift
        ;;
      --adaptive-routing-profile)
        [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-profile"
        adaptive_routing_profile=$2
        explicit_adaptive_routing_profile=$2
        shift 2
        ;;
      --deep-match-mode)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"
        deep_match_mode=$2
        shift 2
        ;;
      --deep-match-temp-root-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-temp-root-dir"
        deep_match_temp_root_dir_input=$2
        shift 2
        ;;
      --deep-match-manifest-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-dir"
        deep_match_manifest_dir_input=$2
        shift 2
        ;;
      --deep-match-manifest-summary)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-summary"
        deep_match_manifest_summary_input=$2
        shift 2
        ;;
      --enable-low-resolution-offset-estimation)
        enable_low_resolution_offset_estimation="1"
        explicit_enable_low_resolution_offset_estimation="1"
        shift
        ;;
      --low-resolution-level)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-level"
        low_resolution_level=$2
        explicit_low_resolution_level=$2
        shift 2
        ;;
      --low-resolution-max-mean-reprojection-error-pixels)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-max-mean-reprojection-error-pixels"
        low_resolution_max_mean_reprojection_error_pixels=$2
        explicit_low_resolution_max_mean_reprojection_error_pixels=$2
        shift 2
        ;;
      --low-resolution-min-retained-match-count)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-min-retained-match-count"
        low_resolution_min_retained_match_count=$2
        explicit_low_resolution_min_retained_match_count=$2
        shift 2
        ;;
      --low-resolution-max-mean-projected-offset-meters)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-max-mean-projected-offset-meters"
        low_resolution_max_mean_projected_offset_meters=$2
        explicit_low_resolution_max_mean_projected_offset_meters=$2
        shift 2
        ;;
      --skip-existing)
        skip_existing="1"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      --)
        shift
        forwarded_args=("$@")
        break
        ;;
      *)
        usage >&2
        die "unknown argument: $1"
        ;;
    esac
  done

  if [[ -n "$explicit_match_preset_path" && -n "$explicit_matcher_method" ]]; then
    die "--match-preset-path cannot be combined with --matcher-method"
  fi
  if [[ -n "$explicit_match_preset_path" && -n "$explicit_deep_match_config_path" ]]; then
    die "--match-preset-path cannot be combined with --deep-match-config-path"
  fi

  require_command "$PYTHON_EXECUTABLE"

  cd "$REPO_ROOT"

  WORK_DIR="$work_dir_input"
  ORIGINAL_LIST="${original_list_input:-$WORK_DIR/original_images.lis}"
  if [[ -n "$dom_list_input" ]]; then
    DOM_LIST="$dom_list_input"
  else
    DOM_LIST=$(resolve_default_dom_list "$WORK_DIR/doms_scaled.lis" "$WORK_DIR/doms.lis")
  fi
  PAIR_LIST="${pair_list_input:-$WORK_DIR/images_overlap.lis}"
  OUTPUT_KEY_DIR="${output_key_dir_input:-$WORK_DIR/dom_keys}"
  METADATA_DIR="${metadata_dir_input:-$WORK_DIR/match_metadata}"
  MATCH_VIZ_DIR="${match_viz_dir_input:-$WORK_DIR/match_viz}"
  CONFIG_PATH="$config_input"
  VALID_PIXEL_PERCENT_THRESHOLD="$DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD"
  DEEP_MATCH_TEMP_ROOT_DIR="${deep_match_temp_root_dir_input:-$WORK_DIR/deep_match_workspaces}"
  DEEP_MATCH_MANIFEST_DIR="$deep_match_manifest_dir_input"
  DEEP_MATCH_MANIFEST_SUMMARY="${deep_match_manifest_summary_input:-$WORK_DIR/deep_match_manifests.json}"

  case "$deep_match_mode" in
    direct|export|import) ;;
    *) die "unsupported --deep-match-mode: $deep_match_mode" ;;
  esac
  if [[ "$deep_match_mode" == "import" && -z "$DEEP_MATCH_MANIFEST_DIR" ]]; then
    die "--deep-match-mode import requires --deep-match-manifest-dir"
  fi

  require_file "$ORIGINAL_LIST"
  require_file "$DOM_LIST"
  require_file "$PAIR_LIST"
  if [[ -n "$CONFIG_PATH" ]]; then
    require_file "$CONFIG_PATH"
  fi

  mkdir -p "$OUTPUT_KEY_DIR" "$METADATA_DIR" "$MATCH_VIZ_DIR"
  if [[ "$deep_match_mode" == "export" ]]; then
    mkdir -p "$DEEP_MATCH_TEMP_ROOT_DIR"
  fi
  if [[ "$deep_match_mode" != "direct" ]]; then
    initialize_deep_match_manifest_summary "$DEEP_MATCH_MANIFEST_SUMMARY"
  fi

  if [[ -n "$explicit_match_preset_path" ]]; then
    match_preset_path=$(resolve_cli_relative_path "$explicit_match_preset_path")
  elif [[ -n "$CONFIG_PATH" && -z "$explicit_matcher_method" && -z "$explicit_deep_match_config_path" ]]; then
    local config_match_preset_path
    config_match_preset_path=$(extract_image_match_config_value "$config_input" "match_preset_path")
    if [[ -n "$config_match_preset_path" && "$config_match_preset_path" != "null" ]]; then
      match_preset_path=$(resolve_config_relative_path "$config_match_preset_path" "$CONFIG_PATH")
    fi
  fi
  if [[ -n "$match_preset_path" ]]; then
    apply_match_preset_path "$match_preset_path"
  fi

  if [[ -n "$CONFIG_PATH" ]]; then
    config_threshold=$(extract_image_match_config_value "$config_input" "valid_pixel_percent_threshold")
    if [[ -n "$config_threshold" ]]; then
      VALID_PIXEL_PERCENT_THRESHOLD="$config_threshold"
    fi
    if [[ -z "$explicit_use_parallel_cpu" ]]; then
      local config_use_parallel_cpu
      config_use_parallel_cpu=$(extract_image_match_config_value "$config_input" "use_parallel_cpu" "image-match-first")
      if [[ -n "$config_use_parallel_cpu" ]]; then
        use_parallel_cpu="$config_use_parallel_cpu"
      fi
    fi
    if [[ -z "$explicit_num_worker_parallel_cpu" ]]; then
      local config_num_worker_parallel_cpu
      config_num_worker_parallel_cpu=$(extract_image_match_config_value "$config_input" "num_worker_parallel_cpu")
      if [[ -n "$config_num_worker_parallel_cpu" ]]; then
        num_worker_parallel_cpu="$config_num_worker_parallel_cpu"
      fi
    fi
    if [[ -z "$explicit_opencv_num_threads" ]]; then
      local config_opencv_num_threads
      config_opencv_num_threads=$(extract_image_match_config_value "$config_input" "opencv_num_threads")
      if [[ -n "$config_opencv_num_threads" ]]; then
        opencv_num_threads="$config_opencv_num_threads"
      fi
    fi
    if [[ -z "$explicit_invalid_pixel_radius" ]]; then
      local config_invalid_pixel_radius
      config_invalid_pixel_radius=$(extract_image_match_config_value "$config_input" "invalid_pixel_radius")
      if [[ -n "$config_invalid_pixel_radius" ]]; then
        invalid_pixel_radius="$config_invalid_pixel_radius"
      fi
    fi
    if [[ -z "$explicit_min_valid_pixels" ]]; then
      local config_min_valid_pixels
      config_min_valid_pixels=$(extract_image_match_config_value "$config_input" "min_valid_pixels")
      if [[ -n "$config_min_valid_pixels" ]]; then
        min_valid_pixels="$config_min_valid_pixels"
      fi
    fi
    if [[ -z "$explicit_valid_intensity_lower_percent" ]]; then
      local config_valid_intensity_lower_percent
      config_valid_intensity_lower_percent=$(extract_image_match_config_value "$config_input" "valid_intensity_lower_percent")
      if [[ -n "$config_valid_intensity_lower_percent" && "$config_valid_intensity_lower_percent" != "None" && "$config_valid_intensity_lower_percent" != "null" ]]; then
        valid_intensity_lower_percent="$config_valid_intensity_lower_percent"
      fi
    fi
    if [[ -z "$explicit_valid_intensity_upper_percent" ]]; then
      local config_valid_intensity_upper_percent
      config_valid_intensity_upper_percent=$(extract_image_match_config_value "$config_input" "valid_intensity_upper_percent")
      if [[ -n "$config_valid_intensity_upper_percent" && "$config_valid_intensity_upper_percent" != "None" && "$config_valid_intensity_upper_percent" != "null" ]]; then
        valid_intensity_upper_percent="$config_valid_intensity_upper_percent"
      fi
    fi
    if [[ -z "$match_preset_path" && -z "$explicit_matcher_method" ]]; then
      local config_matcher_method
      config_matcher_method=$(extract_image_match_config_value "$config_input" "matcher_method")
      if [[ -n "$config_matcher_method" ]]; then
        matcher_method="$config_matcher_method"
      fi
    fi
    if [[ -z "$match_preset_path" && -z "$deep_match_config_path" ]]; then
      local config_deep_matcher_config_path
      config_deep_matcher_config_path=$(extract_image_match_config_value "$config_input" "deep_matcher_config_path")
      if [[ -n "$config_deep_matcher_config_path" && "$config_deep_matcher_config_path" != "null" ]]; then
        deep_match_config_path=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
      fi
    fi
    if [[ -z "$explicit_adaptive_routing" ]]; then
      local config_enable_adaptive_routing
      config_enable_adaptive_routing=$(extract_image_match_config_value "$config_input" "enable_adaptive_routing")
      if [[ -n "$config_enable_adaptive_routing" ]]; then
        adaptive_routing="$config_enable_adaptive_routing"
      fi
    fi
    if [[ -z "$explicit_adaptive_routing_profile" ]]; then
      local config_adaptive_routing_profile
      config_adaptive_routing_profile=$(extract_image_match_config_value "$config_input" "adaptive_routing_profile")
      if [[ -n "$config_adaptive_routing_profile" ]]; then
        adaptive_routing_profile="$config_adaptive_routing_profile"
      fi
    fi
    if [[ -z "$explicit_enable_low_resolution_offset_estimation" ]]; then
      local config_enable_low_resolution_offset_estimation
      config_enable_low_resolution_offset_estimation=$(extract_image_match_config_value "$config_input" "enable_low_resolution_offset_estimation")
      if [[ -n "$config_enable_low_resolution_offset_estimation" ]]; then
        enable_low_resolution_offset_estimation="$config_enable_low_resolution_offset_estimation"
      fi
    fi
    if [[ -z "$explicit_low_resolution_level" ]]; then
      local config_low_resolution_level
      config_low_resolution_level=$(extract_image_match_config_value "$config_input" "low_resolution_level")
      if [[ -n "$config_low_resolution_level" ]]; then
        low_resolution_level="$config_low_resolution_level"
      fi
    fi
    if [[ -z "$explicit_low_resolution_max_mean_reprojection_error_pixels" ]]; then
      local config_low_resolution_max_mean_reprojection_error_pixels
      config_low_resolution_max_mean_reprojection_error_pixels=$(extract_image_match_config_value "$config_input" "low_resolution_max_mean_reprojection_error_pixels")
      if [[ -n "$config_low_resolution_max_mean_reprojection_error_pixels" ]]; then
        low_resolution_max_mean_reprojection_error_pixels="$config_low_resolution_max_mean_reprojection_error_pixels"
      fi
    fi
    if [[ -z "$explicit_low_resolution_min_retained_match_count" ]]; then
      local config_low_resolution_min_retained_match_count
      config_low_resolution_min_retained_match_count=$(extract_image_match_config_value "$config_input" "low_resolution_min_retained_match_count")
      if [[ -n "$config_low_resolution_min_retained_match_count" ]]; then
        low_resolution_min_retained_match_count="$config_low_resolution_min_retained_match_count"
      fi
    fi
    if [[ -z "$explicit_low_resolution_max_mean_projected_offset_meters" ]]; then
      local config_low_resolution_max_mean_projected_offset_meters
      config_low_resolution_max_mean_projected_offset_meters=$(extract_image_match_config_value "$config_input" "low_resolution_max_mean_projected_offset_meters")
      if [[ -n "$config_low_resolution_max_mean_projected_offset_meters" ]]; then
        low_resolution_max_mean_projected_offset_meters="$config_low_resolution_max_mean_projected_offset_meters"
      fi
    fi
  fi
  if [[ -n "$explicit_threshold" ]]; then
    VALID_PIXEL_PERCENT_THRESHOLD="$explicit_threshold"
  fi

  LOW_RESOLUTION_DOM_LIST="$WORK_DIR/doms_low_resolution_level${low_resolution_level}.lis"
  LOW_RESOLUTION_DOM_DIR="$WORK_DIR/low_resolution_doms/level${low_resolution_level}"
  LOW_RESOLUTION_DOM_REPORT="$METADATA_DIR/low_resolution_doms_level${low_resolution_level}.json"

  log "Repository root: $REPO_ROOT"
  log "Work directory: $WORK_DIR"
  log "Original list: $ORIGINAL_LIST"
  log "DOM list: $DOM_LIST"
  log "Pair list: $PAIR_LIST"
  log "Output key dir: $OUTPUT_KEY_DIR"
  log "Metadata dir: $METADATA_DIR"
  log "Match viz dir: $MATCH_VIZ_DIR"
  log "Valid pixel percent threshold: $VALID_PIXEL_PERCENT_THRESHOLD"
  if [[ -n "$min_valid_pixels" ]]; then
    log "Minimum valid pixels: $min_valid_pixels"
  fi
  if [[ -n "$valid_intensity_lower_percent" || -n "$valid_intensity_upper_percent" ]]; then
    log "Valid intensity percentile mask: ${valid_intensity_lower_percent:-unset}..${valid_intensity_upper_percent:-unset}"
  fi
  log "Invalid pixel radius: $invalid_pixel_radius"
  if [[ -n "$dom_source_metadata_csv_input" ]]; then
    log "DOM source metadata CSV: $dom_source_metadata_csv_input"
  fi
  if [[ -n "$match_preset_path" ]]; then
    log "Match preset path: $match_preset_path"
  fi
  log "Matcher method: $matcher_method"
  if [[ -n "$deep_match_config_path" ]]; then
    log "Deep-match config path: $deep_match_config_path"
  fi
  if [[ "$adaptive_routing" == "1" ]]; then
    log "Adaptive routing: enabled"
  else
    log "Adaptive routing: disabled"
  fi
  log "Adaptive routing profile: $adaptive_routing_profile"
  log "Deep-match mode: $deep_match_mode"
  if [[ "$deep_match_mode" == "export" ]]; then
    log "Deep-match temp root dir: $DEEP_MATCH_TEMP_ROOT_DIR"
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  elif [[ "$deep_match_mode" == "import" ]]; then
    log "Deep-match manifest dir: $DEEP_MATCH_MANIFEST_DIR"
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  fi
  if [[ "$use_parallel_cpu" == "1" ]]; then
    log "CPU parallel tile matching: enabled"
    log "CPU parallel worker limit: $num_worker_parallel_cpu"
  else
    log "CPU parallel tile matching: disabled"
    log "CPU parallel worker limit (forwarded default): $num_worker_parallel_cpu"
  fi
  if [[ -n "$opencv_num_threads" ]]; then
    log "OpenCV thread limit: $opencv_num_threads"
  else
    log "OpenCV thread limit: default"
  fi
  if [[ "$enable_low_resolution_offset_estimation" == "1" ]]; then
    log "Low-resolution offset estimation: enabled"
    log "Low-resolution level: $low_resolution_level"
    log "Low-resolution max mean reprojection error (pixels): $low_resolution_max_mean_reprojection_error_pixels"
    log "Low-resolution minimum retained matches: $low_resolution_min_retained_match_count"
    log "Low-resolution max mean projected offset (meters): $low_resolution_max_mean_projected_offset_meters"
    log "Low-resolution DOM list: $LOW_RESOLUTION_DOM_LIST"
    log "Low-resolution DOM cache dir: $LOW_RESOLUTION_DOM_DIR"
  else
    log "Low-resolution offset estimation: disabled"
  fi
  if [[ ${#forwarded_args[@]} -gt 0 ]]; then
    log "Forwarding extra examples/image_match/image_match.py args: ${forwarded_args[*]}"
  fi

  declare -A dom_by_original=()
  while IFS=$'\t' read -r original dom; do
    [[ -n "$original" ]] || continue
    [[ -n "$dom" ]] || die "DOM list alignment failed while reading paired original/DOM lists"
    dom_by_original["$original"]="$dom"
  done < <(paste "$ORIGINAL_LIST" "$DOM_LIST")

  declare -A low_resolution_dom_by_original=()
  if [[ "$enable_low_resolution_offset_estimation" == "1" ]]; then
    log "Preparing reusable low-resolution DOM list -> $LOW_RESOLUTION_DOM_LIST"
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/prepare_low_resolution_doms.py" \
      "$DOM_LIST" \
      "$LOW_RESOLUTION_DOM_LIST" \
      --level "$low_resolution_level" \
      --output-dir "$LOW_RESOLUTION_DOM_DIR" \
      --report-json "$LOW_RESOLUTION_DOM_REPORT"

    while IFS=$'\t' read -r original low_resolution_dom; do
      [[ -n "$original" ]] || continue
      [[ -n "$low_resolution_dom" ]] || die "low-resolution DOM list alignment failed while reading paired original/low-resolution DOM lists"
      low_resolution_dom_by_original["$original"]="$low_resolution_dom"
    done < <(paste "$ORIGINAL_LIST" "$LOW_RESOLUTION_DOM_LIST")
  fi

  local pair_count=0
  while IFS=, read -r left right; do
    [[ -n "$left" ]] || continue
    [[ -n "$right" ]] || die "invalid overlap pair line missing right-hand entry"

    if [[ -z "${dom_by_original[$left]+x}" ]]; then
      die "no DOM path found for left original image: $left"
    fi
    if [[ -z "${dom_by_original[$right]+x}" ]]; then
      die "no DOM path found for right original image: $right"
    fi

    local left_stem
    local right_stem
    local pair_tag
    local left_key
    local right_key
    local match_args=()
    left_stem=$(basename "${left%.*}")
    right_stem=$(basename "${right%.*}")
    pair_tag="${left_stem}__${right_stem}"
    left_key="$OUTPUT_KEY_DIR/${pair_tag}_A.key"
    right_key="$OUTPUT_KEY_DIR/${pair_tag}_B.key"

    if [[ "$skip_existing" == "1" && -f "$left_key" && -f "$right_key" ]]; then
      log "Skipping existing pair ${pair_tag}"
      continue
    fi

    log "Matching pair ${pair_tag}"
    match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/image_match/image_match.py"
      "${dom_by_original[$left]}"
      "${dom_by_original[$right]}"
      "$left_key"
      "$right_key"
      --metadata-output "$METADATA_DIR/${pair_tag}.json"
      --match-visualization-output-dir "$MATCH_VIZ_DIR"
      --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"
      --invalid-pixel-radius "$invalid_pixel_radius"
    )
    if [[ -n "$CONFIG_PATH" ]]; then
      match_args=(
        "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/image_match/image_match.py"
        --config "$CONFIG_PATH"
        "${dom_by_original[$left]}"
        "${dom_by_original[$right]}"
        "$left_key"
        "$right_key"
        --metadata-output "$METADATA_DIR/${pair_tag}.json"
        --match-visualization-output-dir "$MATCH_VIZ_DIR"
        --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"
        --invalid-pixel-radius "$invalid_pixel_radius"
      )
    fi
    if [[ -n "$min_valid_pixels" ]]; then
      match_args+=(--min-valid-pixels "$min_valid_pixels")
    fi
    if [[ -n "$valid_intensity_lower_percent" ]]; then
      match_args+=(--valid-intensity-lower-percent "$valid_intensity_lower_percent")
    fi
    if [[ -n "$valid_intensity_upper_percent" ]]; then
      match_args+=(--valid-intensity-upper-percent "$valid_intensity_upper_percent")
    fi
    if [[ -n "$dom_source_metadata_csv_input" ]]; then
      match_args+=(--dom-source-metadata-csv "$dom_source_metadata_csv_input")
    fi
    if [[ -n "$match_preset_path" ]]; then
      match_args+=(--match-preset-path "$match_preset_path")
    else
      match_args+=(--matcher-method "$matcher_method")
    fi
    if [[ "$use_parallel_cpu" == "1" ]]; then
      match_args+=(--use-parallel-cpu)
    else
      match_args+=(--no-parallel-cpu)
    fi
    if [[ "$adaptive_routing" == "1" ]]; then
      match_args+=(--adaptive-routing)
    else
      match_args+=(--no-adaptive-routing)
    fi
    match_args+=(--adaptive-routing-profile "$adaptive_routing_profile")
    if [[ -z "$match_preset_path" && -n "$deep_match_config_path" ]]; then
      match_args+=(--deep-match-config-path "$deep_match_config_path")
    fi
    match_args+=(--num-worker-parallel-cpu "$num_worker_parallel_cpu")
    if [[ -n "$opencv_num_threads" ]]; then
      match_args+=(--opencv-num-threads "$opencv_num_threads")
    fi
    if [[ "$enable_low_resolution_offset_estimation" == "1" ]]; then
      if [[ -z "${low_resolution_dom_by_original[$left]+x}" ]]; then
        die "no low-resolution DOM path found for left original image: $left"
      fi
      if [[ -z "${low_resolution_dom_by_original[$right]+x}" ]]; then
        die "no low-resolution DOM path found for right original image: $right"
      fi
      match_args+=(
        --enable-low-resolution-offset-estimation
        --low-resolution-level "$low_resolution_level"
        --low-resolution-max-mean-reprojection-error-pixels "$low_resolution_max_mean_reprojection_error_pixels"
        --low-resolution-min-retained-match-count "$low_resolution_min_retained_match_count"
        --low-resolution-max-mean-projected-offset-meters "$low_resolution_max_mean_projected_offset_meters"
        --left-low-resolution-dom "${low_resolution_dom_by_original[$left]}"
        --right-low-resolution-dom "${low_resolution_dom_by_original[$right]}"
      )
    fi
    if [[ "$deep_match_mode" != "direct" ]]; then
      match_args+=(--deep-match-mode "$deep_match_mode")
      if [[ "$deep_match_mode" == "export" ]]; then
        match_args+=(--deep-match-temp-root-dir "$DEEP_MATCH_TEMP_ROOT_DIR")
      elif [[ "$deep_match_mode" == "import" ]]; then
        match_args+=(--deep-match-manifest "$DEEP_MATCH_MANIFEST_DIR/${pair_tag}/tasks.json")
      fi
    fi
    if [[ ${#forwarded_args[@]} -gt 0 ]]; then
      match_args+=("${forwarded_args[@]}")
    fi
    "${match_args[@]}"
    if [[ "$deep_match_mode" != "direct" ]]; then
      append_deep_match_manifest_summary "$DEEP_MATCH_MANIFEST_SUMMARY" "$pair_tag" "$METADATA_DIR/${pair_tag}.json"
    fi

    pair_count=$((pair_count + 1))
  done < "$PAIR_LIST"

  if [[ "$pair_count" -eq 0 ]]; then
    warn "no pairs were processed; check images_overlap.lis or use --skip-existing carefully"
  else
    log "Completed DOM matching for ${pair_count} pair(s)"
  fi
  if [[ "$deep_match_mode" != "direct" ]]; then
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  fi
}

main "$@"
