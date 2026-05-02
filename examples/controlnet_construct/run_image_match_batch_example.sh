#!/usr/bin/env bash

set -euo pipefail

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

Batch-run image_match.py for all pairs listed in images_overlap.lis.

Defaults assume a work directory layout like:
  work/original_images.lis
  work/doms_scaled.lis (or work/doms.lis)
  work/images_overlap.lis
  work/dom_keys/
  work/match_metadata/
  work/match_viz/            # pre-RANSAC drawMatches PNGs from image_match.py

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --pair-list PATH                Overlap pair list path. Default: <work-dir>/images_overlap.lis
  --config PATH                   Optional config JSON. Its ImageMatch section is forwarded to image_match.py
                                  as default matching parameters, and this wrapper also reads selected fields for overrides.
  --output-key-dir PATH           Output .key directory. Default: <work-dir>/dom_keys
  --metadata-dir PATH             Metadata JSON output directory. Default: <work-dir>/match_metadata
  --match-viz-dir PATH            Pre-RANSAC match visualization PNG directory.
                                  Default: <work-dir>/match_viz
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --use-parallel-cpu              Forward explicit CPU tile parallelism enable flag to image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in image_match.py and force serial tile matching
  --num-worker-parallel-cpu N     Maximum worker-process count forwarded to image_match.py when CPU parallelism is enabled.
                                  Default: 8. If omitted, this script falls back to config JSON field
                                  ImageMatch.num_worker_parallel_cpu when present. Valid range: 1~4096.
  --valid-pixel-percent-threshold VALUE
                                 Minimum valid-pixel ratio forwarded to image_match.py.
                                 Default: 0.05 unless omitted and resolved from --config.
  --invalid-pixel-radius N        Suppress feature detection near invalid pixels or image borders.
                                  Default: 1 unless omitted and resolved from --config.
  --matcher-method NAME           Descriptor matcher backend forwarded to image_match.py.
                                  Supported values: bf, flann. Default: bf unless omitted and resolved from --config.
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
                                  Unit: meters. Default: image_match.py default unless omitted and resolved
                                  from --config.
  --skip-existing                 Skip pairs whose left/right key files already exist
  -h, --help                      Show this help message

Default behavior:
  - CPU tile parallelism is enabled unless --no-parallel-cpu is provided.
  - image_match.py writes pre-RANSAC match visualization PNGs by default.
  - To disable those PNGs, forward: -- --no-write-match-visualization

Anything after -- is forwarded directly to image_match.py.

Examples:
  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --valid-pixel-percent-threshold 0.05

  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --config examples/controlnet_construct/controlnet_config.example.json \
    -- \
    --ratio-test 0.8 \
    --sub-block-size-x 1536 \
    --sub-block-size-y 1536

  bash examples/controlnet_construct/run_image_match_batch_example.sh \
    --work-dir work \
    --num-worker-parallel-cpu 4 \
    --no-parallel-cpu \
    -- \
    --no-write-match-visualization
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
  local container_order=${3:-top-level-first}
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py" \
    --config "$config_path" \
    --print-config-default "$field_name" \
    --print-config-default-container-order "$container_order"
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
  local explicit_threshold=""
  local invalid_pixel_radius="$DEFAULT_INVALID_PIXEL_RADIUS"
  local explicit_invalid_pixel_radius=""
  local matcher_method="bf"
  local explicit_matcher_method=""
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
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        explicit_threshold=$2
        shift 2
        ;;
      --invalid-pixel-radius)
        [[ $# -ge 2 ]] || die "missing value for --invalid-pixel-radius"
        invalid_pixel_radius=$2
        explicit_invalid_pixel_radius=$2
        shift 2
        ;;
      --matcher-method)
        [[ $# -ge 2 ]] || die "missing value for --matcher-method"
        matcher_method=$2
        explicit_matcher_method=$2
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

  require_file "$ORIGINAL_LIST"
  require_file "$DOM_LIST"
  require_file "$PAIR_LIST"
  if [[ -n "$CONFIG_PATH" ]]; then
    require_file "$CONFIG_PATH"
  fi

  mkdir -p "$OUTPUT_KEY_DIR" "$METADATA_DIR" "$MATCH_VIZ_DIR"

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
    if [[ -z "$explicit_invalid_pixel_radius" ]]; then
      local config_invalid_pixel_radius
      config_invalid_pixel_radius=$(extract_image_match_config_value "$config_input" "invalid_pixel_radius")
      if [[ -n "$config_invalid_pixel_radius" ]]; then
        invalid_pixel_radius="$config_invalid_pixel_radius"
      fi
    fi
    if [[ -z "$explicit_matcher_method" ]]; then
      local config_matcher_method
      config_matcher_method=$(extract_image_match_config_value "$config_input" "matcher_method")
      if [[ -n "$config_matcher_method" ]]; then
        matcher_method="$config_matcher_method"
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
  log "Invalid pixel radius: $invalid_pixel_radius"
  log "Matcher method: $matcher_method"
  if [[ "$use_parallel_cpu" == "1" ]]; then
    log "CPU parallel tile matching: enabled"
    log "CPU parallel worker limit: $num_worker_parallel_cpu"
  else
    log "CPU parallel tile matching: disabled"
    log "CPU parallel worker limit (forwarded default): $num_worker_parallel_cpu"
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
    log "Forwarding extra image_match.py args: ${forwarded_args[*]}"
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
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py"
      "${dom_by_original[$left]}"
      "${dom_by_original[$right]}"
      "$left_key"
      "$right_key"
      --metadata-output "$METADATA_DIR/${pair_tag}.json"
      --match-visualization-output-dir "$MATCH_VIZ_DIR"
      --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"
      --invalid-pixel-radius "$invalid_pixel_radius"
      --matcher-method "$matcher_method"
    )
    if [[ -n "$CONFIG_PATH" ]]; then
      match_args=(
        "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py"
        --config "$CONFIG_PATH"
        "${dom_by_original[$left]}"
        "${dom_by_original[$right]}"
        "$left_key"
        "$right_key"
        --metadata-output "$METADATA_DIR/${pair_tag}.json"
        --match-visualization-output-dir "$MATCH_VIZ_DIR"
        --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"
        --invalid-pixel-radius "$invalid_pixel_radius"
        --matcher-method "$matcher_method"
      )
    fi
    if [[ "$use_parallel_cpu" == "1" ]]; then
      match_args+=(--use-parallel-cpu)
    else
      match_args+=(--no-parallel-cpu)
    fi
    match_args+=(--num-worker-parallel-cpu "$num_worker_parallel_cpu")
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
    if [[ ${#forwarded_args[@]} -gt 0 ]]; then
      match_args+=("${forwarded_args[@]}")
    fi
    "${match_args[@]}"

    pair_count=$((pair_count + 1))
  done < "$PAIR_LIST"

  if [[ "$pair_count" -eq 0 ]]; then
    warn "no pairs were processed; check images_overlap.lis or use --skip-existing carefully"
  else
    log "Completed DOM matching for ${pair_count} pair(s)"
  fi
}

main "$@"
