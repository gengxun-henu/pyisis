#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD="0.05"

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
  work/match_viz/

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --pair-list PATH                Overlap pair list path. Default: <work-dir>/images_overlap.lis
  --config PATH                   Optional config JSON used to read ImageMatch.valid_pixel_percent_threshold
  --output-key-dir PATH           Output .key directory. Default: <work-dir>/dom_keys
  --metadata-dir PATH             Metadata JSON output directory. Default: <work-dir>/match_metadata
  --match-viz-dir PATH            Match visualization PNG directory. Default: <work-dir>/match_viz
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --use_parallel_cpu              Forward explicit CPU tile parallelism enable flag to image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in image_match.py and force serial tile matching
  --valid-pixel-percent-threshold VALUE
                                 Minimum valid-pixel ratio forwarded to image_match.py.
                                 Default: 0.05 unless omitted and resolved from --config.
  --skip-existing                 Skip pairs whose left/right key files already exist
  -h, --help                      Show this help message

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

extract_valid_pixel_percent_threshold_from_config() {
  local config_path=$1
  "$PYTHON_EXECUTABLE" - "$config_path" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))

candidate_containers = [
    payload,
    payload.get('ImageMatch') or {},
    payload.get('image_match') or {},
    payload.get('imageMatch') or {},
]
candidate_keys = (
    'valid_pixel_percent_threshold',
    'validPixelPercentThreshold',
    'ValidPixelPercentThreshold',
)

for container in candidate_containers:
    if not isinstance(container, dict):
        continue
    for key in candidate_keys:
        value = container.get(key)
        if value in (None, ''):
            continue
        print(value)
        raise SystemExit(0)

raise SystemExit(0)
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
  local explicit_threshold=""
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
      --use_parallel_cpu|--use-parallel-cpu)
        use_parallel_cpu="1"
        shift
        ;;
      --no-parallel-cpu|--no_parallel_cpu)
        use_parallel_cpu="0"
        shift
        ;;
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        explicit_threshold=$2
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
    config_threshold=$(extract_valid_pixel_percent_threshold_from_config "$CONFIG_PATH")
    if [[ -n "$config_threshold" ]]; then
      VALID_PIXEL_PERCENT_THRESHOLD="$config_threshold"
    fi
  fi
  if [[ -n "$explicit_threshold" ]]; then
    VALID_PIXEL_PERCENT_THRESHOLD="$explicit_threshold"
  fi

  log "Repository root: $REPO_ROOT"
  log "Work directory: $WORK_DIR"
  log "Original list: $ORIGINAL_LIST"
  log "DOM list: $DOM_LIST"
  log "Pair list: $PAIR_LIST"
  log "Output key dir: $OUTPUT_KEY_DIR"
  log "Metadata dir: $METADATA_DIR"
  log "Match viz dir: $MATCH_VIZ_DIR"
  log "Valid pixel percent threshold: $VALID_PIXEL_PERCENT_THRESHOLD"
  if [[ "$use_parallel_cpu" == "1" ]]; then
    log "CPU parallel tile matching: enabled"
  else
    log "CPU parallel tile matching: disabled"
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
    )
    if [[ "$use_parallel_cpu" == "1" ]]; then
      match_args+=(--use_parallel_cpu)
    else
      match_args+=(--no-parallel-cpu)
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
