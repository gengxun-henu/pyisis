#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"

log() {
  printf '[controlnet-pipeline] %s\n' "$*"
}

warn() {
  printf '[controlnet-pipeline] warning: %s\n' "$*" >&2
}

die() {
  printf '[controlnet-pipeline] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_pipeline_example.sh [options]

Run the DOM matching ControlNet example pipeline end to end:
  1. image_overlap.py
  2. image_match.py (for every pair in images_overlap.lis)
  3. controlnet_stereopair.py from-dom-batch
  4. controlnet_merge.py
  5. execute the generated merge_all_controlnets.sh by default

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --config PATH                   ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --pair-id-prefix PREFIX         Batch pair-id prefix. Default: S
  --pair-id-start N               Batch pair-id starting index. Default: 1
  --merged-net PATH               Final merged ControlNet output path. Default: <work-dir>/merge/dom_matching_merged.net
  --merge-script PATH             Generated merge shell path. Default: <work-dir>/merge/merge_all_controlnets.sh
  --merge-log PATH                cnetmerge log path. Default: <work-dir>/merge/cnetmerge.log
  --pair-list PATH                Optional explicit cnetmerge input list path. Default: auto-named by controlnet_merge.py
  --network-id VALUE              NETWORKID passed to controlnet_merge.py. Default: read from config JSON
  --description TEXT              Description passed to controlnet_merge.py. Default: Merged DOM matching ControlNet
  --cnetmerge PATH                cnetmerge executable path written into the generated merge shell. Default: $CNETMERGE_EXECUTABLE or cnetmerge
  --skip-final-merge              Generate merge shell but do not execute it
  -h, --help                      Show this help message

Environment overrides:
  PYTHON_EXECUTABLE               Python interpreter used by this script
  CNETMERGE_EXECUTABLE            cnetmerge executable path written into the generated merge shell
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

extract_network_id_from_config() {
  local config_path=$1
  "$PYTHON_EXECUTABLE" - "$config_path" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
value = config.get('NetworkId') or config.get('network_id')
if not value:
    raise SystemExit('missing NetworkId in config JSON')
print(value)
PY
}

run_step_1_image_overlap() {
  log "Step 1/4: computing overlap pairs -> ${IMAGES_OVERLAP_LIST}"
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" \
    "$IMAGES_OVERLAP_LIST"
}

run_step_2_image_match_batch() {
  log "Step 2/4: matching DOM pairs listed in ${IMAGES_OVERLAP_LIST}"

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
    left_stem=$(basename "${left%.*}")
    right_stem=$(basename "${right%.*}")
    pair_tag="${left_stem}__${right_stem}"

    log "  matching pair ${pair_tag}"
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py" \
      "${dom_by_original[$left]}" \
      "${dom_by_original[$right]}" \
      "$DOM_KEYS_DIR/${pair_tag}_A.key" \
      "$DOM_KEYS_DIR/${pair_tag}_B.key" \
      --metadata-output "$MATCH_METADATA_DIR/${pair_tag}.json" \
      --match-visualization-output-dir "$MATCH_VIZ_DIR"

    pair_count=$((pair_count + 1))
  done < "$IMAGES_OVERLAP_LIST"

  if [[ "$pair_count" -eq 0 ]]; then
    warn "images_overlap.lis did not contain any overlap pairs; downstream steps may fail or produce empty outputs"
  fi
}

run_step_3_pairwise_controlnets() {
  log "Step 3/4: building pairwise ControlNets -> ${PAIR_NETS_DIR}"
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-dom-batch \
    "$IMAGES_OVERLAP_LIST" \
    "$ORIGINAL_LIST" \
    "$DOM_LIST" \
    "$DOM_KEYS_DIR" \
    "$CONFIG_PATH" \
    "$PAIR_NETS_DIR" \
    --report-dir "$REPORTS_DIR" \
    --pair-id-prefix "$PAIR_ID_PREFIX" \
    --pair-id-start "$PAIR_ID_START"
}

run_step_4_merge() {
  log "Step 4/4: generating cnetmerge shell -> ${MERGE_SCRIPT_PATH}"

  local merge_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_merge.py"
    "$IMAGES_OVERLAP_LIST"
    "$PAIR_NETS_DIR"
    "$MERGED_NET_PATH"
    "$MERGE_SCRIPT_PATH"
    --network-id "$NETWORK_ID"
    --description "$MERGE_DESCRIPTION"
    --log "$MERGE_LOG_PATH"
    --cnetmerge "$CNETMERGE_PATH"
  )

  if [[ -n "$PAIR_LIST_PATH" ]]; then
    merge_args+=(--pair-list "$PAIR_LIST_PATH")
  fi

  "${merge_args[@]}"

  if [[ "$SKIP_FINAL_MERGE" == "1" ]]; then
    log "Skipping final cnetmerge execution by request (--skip-final-merge)"
    return 0
  fi

  require_command "$CNETMERGE_PATH"
  log "Executing generated merge shell"
  bash "$MERGE_SCRIPT_PATH"
}

main() {
  local work_dir_input="$DEFAULT_WORK_DIR_RELATIVE"
  local original_list_input=""
  local dom_list_input=""
  local config_input="$DEFAULT_CONFIG_RELATIVE"
  local merged_net_input=""
  local merge_script_input=""
  local merge_log_input=""
  local pair_list_input=""

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"
  CNETMERGE_PATH="${CNETMERGE_EXECUTABLE:-cnetmerge}"
  PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
  PAIR_ID_START="$DEFAULT_PAIR_ID_START"
  NETWORK_ID=""
  MERGE_DESCRIPTION="Merged DOM matching ControlNet"
  SKIP_FINAL_MERGE="0"

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
      --config)
        [[ $# -ge 2 ]] || die "missing value for --config"
        config_input=$2
        shift 2
        ;;
      --python)
        [[ $# -ge 2 ]] || die "missing value for --python"
        PYTHON_EXECUTABLE=$2
        shift 2
        ;;
      --pair-id-prefix)
        [[ $# -ge 2 ]] || die "missing value for --pair-id-prefix"
        PAIR_ID_PREFIX=$2
        shift 2
        ;;
      --pair-id-start)
        [[ $# -ge 2 ]] || die "missing value for --pair-id-start"
        PAIR_ID_START=$2
        shift 2
        ;;
      --merged-net)
        [[ $# -ge 2 ]] || die "missing value for --merged-net"
        merged_net_input=$2
        shift 2
        ;;
      --merge-script)
        [[ $# -ge 2 ]] || die "missing value for --merge-script"
        merge_script_input=$2
        shift 2
        ;;
      --merge-log)
        [[ $# -ge 2 ]] || die "missing value for --merge-log"
        merge_log_input=$2
        shift 2
        ;;
      --pair-list)
        [[ $# -ge 2 ]] || die "missing value for --pair-list"
        pair_list_input=$2
        shift 2
        ;;
      --network-id)
        [[ $# -ge 2 ]] || die "missing value for --network-id"
        NETWORK_ID=$2
        shift 2
        ;;
      --description)
        [[ $# -ge 2 ]] || die "missing value for --description"
        MERGE_DESCRIPTION=$2
        shift 2
        ;;
      --cnetmerge)
        [[ $# -ge 2 ]] || die "missing value for --cnetmerge"
        CNETMERGE_PATH=$2
        shift 2
        ;;
      --skip-final-merge)
        SKIP_FINAL_MERGE="1"
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

  require_command "$PYTHON_EXECUTABLE"

  cd "$REPO_ROOT"

  WORK_DIR="$work_dir_input"
  ORIGINAL_LIST="${original_list_input:-$WORK_DIR/original_images.lis}"
  if [[ -n "$dom_list_input" ]]; then
    DOM_LIST="$dom_list_input"
  else
    DOM_LIST=$(resolve_default_dom_list "$WORK_DIR/doms_scaled.lis" "$WORK_DIR/doms.lis")
  fi
  CONFIG_PATH="$config_input"
  IMAGES_OVERLAP_LIST="$WORK_DIR/images_overlap.lis"
  DOM_KEYS_DIR="$WORK_DIR/dom_keys"
  MATCH_METADATA_DIR="$WORK_DIR/match_metadata"
  MATCH_VIZ_DIR="$WORK_DIR/match_viz"
  PAIR_NETS_DIR="$WORK_DIR/pair_nets"
  REPORTS_DIR="$WORK_DIR/reports"
  MERGE_DIR="$WORK_DIR/merge"
  MERGED_NET_PATH="${merged_net_input:-$MERGE_DIR/dom_matching_merged.net}"
  MERGE_SCRIPT_PATH="${merge_script_input:-$MERGE_DIR/merge_all_controlnets.sh}"
  MERGE_LOG_PATH="${merge_log_input:-$MERGE_DIR/cnetmerge.log}"
  PAIR_LIST_PATH="$pair_list_input"

  require_file "$ORIGINAL_LIST"
  require_file "$DOM_LIST"
  require_file "$CONFIG_PATH"

  mkdir -p "$DOM_KEYS_DIR" "$MATCH_METADATA_DIR" "$MATCH_VIZ_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"

  if [[ -z "$NETWORK_ID" ]]; then
    NETWORK_ID=$(extract_network_id_from_config "$CONFIG_PATH")
  fi

  log "Repository root: $REPO_ROOT"
  log "Work directory: $WORK_DIR"
  log "Python executable: $PYTHON_EXECUTABLE"
  log "Original list: $ORIGINAL_LIST"
  log "DOM list: $DOM_LIST"
  log "Config: $CONFIG_PATH"
  log "Network ID: $NETWORK_ID"
  log "cnetmerge executable: $CNETMERGE_PATH"

  run_step_1_image_overlap
  run_step_2_image_match_batch
  run_step_3_pairwise_controlnets
  run_step_4_merge

  log "Pipeline completed"
  log "Key outputs:"
  log "  overlap list: $IMAGES_OVERLAP_LIST"
  log "  DOM keys: $DOM_KEYS_DIR"
  log "  pairwise nets: $PAIR_NETS_DIR"
  log "  reports: $REPORTS_DIR"
  log "  merge script: $MERGE_SCRIPT_PATH"
  log "  merged net: $MERGED_NET_PATH"
}

main "$@"
