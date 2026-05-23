#!/usr/bin/env bash

# End-to-end raw/original image matching ControlNet pipeline example runner.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)

DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work_ori"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"

log() {
  printf '[ori-match-pipeline] %s\n' "$*"
}

die() {
  printf '[ori-match-pipeline] error: %s\n' "$*" >&2
  exit 1
}

quote_cmd() {
  local quoted=()
  local arg
  for arg in "$@"; do
    quoted+=("$(printf '%q' "$arg")")
  done
  printf '%s\n' "${quoted[*]}"
}

append_command() {
  quote_cmd "$@" >> "$COMMAND_SCRIPT"
}

pair_tag_from_paths() {
  local left=$1
  local right=$2
  local left_stem
  local right_stem
  left_stem=$(basename "${left%.*}")
  right_stem=$(basename "${right%.*}")
  printf '%s__%s\n' "$left_stem" "$right_stem"
}

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_ori_match_pipeline_example.sh [options]

Run raw/original image matching ControlNet construction:
  1. image_overlap.py
  2. controlnet_stereopair.py from-ori-match for every overlap pair
  3. controlnet_merge.py and optionally the generated merge script

Options:
  --work-dir PATH                Work directory. Default: work_ori
  --original-list PATH           original_images.lis path. Default: <work-dir>/original_images.lis
  --images-overlap-list PATH     images_overlap.lis path. Default: <work-dir>/images_overlap.lis
  --config PATH                  ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
  --matcher-method NAME          Matcher method forwarded to from-ori-match. Default: flann
  --band N                       Band forwarded to from-ori-match. Default: 1
  --ratio-test FLOAT             Ratio test threshold. Default: 0.75
  --max-features N               Optional SIFT max_features.
  --pair-id-prefix VALUE         Pair id prefix. Default: S
  --pair-id-start N              Pair id start. Default: 1
  --num-worker-parallel-cpu N    CPU worker count. Default: 8
  --use-parallel-cpu             Enable parallel CPU matching. Default.
  --no-parallel-cpu              Disable parallel CPU matching.
  --use-gpu                      Enable GPU route when supported.
  --gpu-batch-size N             GPU batch size. Default: 4
  --gpu-dynamic-batch            Enable dynamic GPU batch sizing. Default.
  --no-gpu-dynamic-batch         Disable dynamic GPU batch sizing.
  --gpu-min-batch-size N         Minimum dynamic GPU batch size. Default: 2
  --gpu-max-batch-size N         Maximum dynamic GPU batch size. Default: 16
  --skip-final-merge             Generate but do not execute merge shell.
  --dry-run                      Write command.sh and summary without executing commands.
  --log-level VALUE              from-ori-match log level. Default: INFO
  -h, --help                     Show this help.
EOF
}

WORK_DIR=""
ORIGINAL_LIST=""
IMAGES_OVERLAP_LIST=""
CONFIG_PATH=""
MATCHER_METHOD="flann"
BAND="1"
RATIO_TEST="0.75"
MAX_FEATURES=""
PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
PAIR_ID_START="$DEFAULT_PAIR_ID_START"
NUM_WORKER_PARALLEL_CPU="8"
USE_PARALLEL_CPU="1"
USE_GPU="0"
GPU_BATCH_SIZE="4"
GPU_DYNAMIC_BATCH="1"
GPU_MIN_BATCH_SIZE="2"
GPU_MAX_BATCH_SIZE="16"
SKIP_FINAL_MERGE="0"
DRY_RUN="0"
LOG_LEVEL="INFO"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) [[ $# -ge 2 ]] || die "missing value for --work-dir"; WORK_DIR=$2; shift 2 ;;
    --original-list) [[ $# -ge 2 ]] || die "missing value for --original-list"; ORIGINAL_LIST=$2; shift 2 ;;
    --images-overlap-list) [[ $# -ge 2 ]] || die "missing value for --images-overlap-list"; IMAGES_OVERLAP_LIST=$2; shift 2 ;;
    --config) [[ $# -ge 2 ]] || die "missing value for --config"; CONFIG_PATH=$2; shift 2 ;;
    --matcher-method) [[ $# -ge 2 ]] || die "missing value for --matcher-method"; MATCHER_METHOD=$2; shift 2 ;;
    --band) [[ $# -ge 2 ]] || die "missing value for --band"; BAND=$2; shift 2 ;;
    --ratio-test) [[ $# -ge 2 ]] || die "missing value for --ratio-test"; RATIO_TEST=$2; shift 2 ;;
    --max-features) [[ $# -ge 2 ]] || die "missing value for --max-features"; MAX_FEATURES=$2; shift 2 ;;
    --pair-id-prefix) [[ $# -ge 2 ]] || die "missing value for --pair-id-prefix"; PAIR_ID_PREFIX=$2; shift 2 ;;
    --pair-id-start) [[ $# -ge 2 ]] || die "missing value for --pair-id-start"; PAIR_ID_START=$2; shift 2 ;;
    --num-worker-parallel-cpu) [[ $# -ge 2 ]] || die "missing value for --num-worker-parallel-cpu"; NUM_WORKER_PARALLEL_CPU=$2; shift 2 ;;
    --use-parallel-cpu) USE_PARALLEL_CPU="1"; shift ;;
    --no-parallel-cpu) USE_PARALLEL_CPU="0"; shift ;;
    --use-gpu) USE_GPU="1"; shift ;;
    --gpu-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-batch-size"; GPU_BATCH_SIZE=$2; shift 2 ;;
    --gpu-dynamic-batch) GPU_DYNAMIC_BATCH="1"; shift ;;
    --no-gpu-dynamic-batch) GPU_DYNAMIC_BATCH="0"; shift ;;
    --gpu-min-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-min-batch-size"; GPU_MIN_BATCH_SIZE=$2; shift 2 ;;
    --gpu-max-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-max-batch-size"; GPU_MAX_BATCH_SIZE=$2; shift 2 ;;
    --skip-final-merge) SKIP_FINAL_MERGE="1"; shift ;;
    --dry-run) DRY_RUN="1"; shift ;;
    --log-level) [[ $# -ge 2 ]] || die "missing value for --log-level"; LOG_LEVEL=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --deep-match-config-path|--deep-match-mode|--adaptive-routing|--no-adaptive-routing)
      die "$1 is not supported by the raw image space wrapper first version"
      ;;
    *) die "unknown option: $1" ;;
  esac
done

case "$PAIR_ID_START" in
  ''|*[!0-9]*) die "--pair-id-start must be a positive integer" ;;
esac
if [[ "$PAIR_ID_START" -lt 1 ]]; then
  die "--pair-id-start must be at least 1"
fi

WORK_DIR="${WORK_DIR:-$REPO_ROOT/$DEFAULT_WORK_DIR_RELATIVE}"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/$DEFAULT_CONFIG_RELATIVE}"
ORIGINAL_LIST="${ORIGINAL_LIST:-$WORK_DIR/original_images.lis}"
IMAGES_OVERLAP_LIST="${IMAGES_OVERLAP_LIST:-$WORK_DIR/images_overlap.lis}"

WORK_DIR=$(cd -- "$(dirname -- "$WORK_DIR")" && pwd)/$(basename -- "$WORK_DIR")
CONFIG_PATH=$(cd -- "$(dirname -- "$CONFIG_PATH")" && pwd)/$(basename -- "$CONFIG_PATH")
ORIGINAL_LIST=$(cd -- "$(dirname -- "$ORIGINAL_LIST")" && pwd)/$(basename -- "$ORIGINAL_LIST")
IMAGES_OVERLAP_LIST=$(cd -- "$(dirname -- "$IMAGES_OVERLAP_LIST")" && pwd)/$(basename -- "$IMAGES_OVERLAP_LIST")

ORI_KEYS_DIR="$WORK_DIR/ori_keys"
PAIR_NETS_DIR="$WORK_DIR/ori_pair_nets"
REPORTS_DIR="$WORK_DIR/reports"
MERGE_DIR="$WORK_DIR/merge"
COMMAND_SCRIPT="$WORK_DIR/command.sh"
OVERLAP_REPORT_PATH="$REPORTS_DIR/image_overlap_summary.json"
MERGE_OUTPUT_NET="$MERGE_DIR/ori_matching_merged.net"
MERGE_SCRIPT_PATH="$MERGE_DIR/merge_all_controlnets.sh"
MERGE_PAIR_LIST_PATH="$MERGE_DIR/merge_all_controlnets.lis"
MERGE_REPORT_PATH="$MERGE_DIR/controlnet_merge_summary.json"

mkdir -p "$WORK_DIR" "$ORI_KEYS_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"
: > "$COMMAND_SCRIPT"
chmod 755 "$COMMAND_SCRIPT"

[[ -f "$ORIGINAL_LIST" ]] || die "original image list not found: $ORIGINAL_LIST"
[[ -f "$CONFIG_PATH" ]] || die "controlnet config not found: $CONFIG_PATH"

append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
  "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"

pair_index=0
if [[ -f "$IMAGES_OVERLAP_LIST" ]]; then
  while IFS=, read -r left right; do
    [[ -n "$left" ]] || continue
    [[ -n "$right" ]] || die "invalid overlap pair line missing right-hand entry"
    pair_index=$((pair_index + 1))
    pair_id="${PAIR_ID_PREFIX}$((PAIR_ID_START + pair_index - 1))"
    pair_tag=$(pair_tag_from_paths "$left" "$right")
    match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-ori-match
      "$left" "$right" "$CONFIG_PATH" "$PAIR_NETS_DIR/${pair_tag}.net"
      --pair-id "$pair_id"
      --left-output-key "$ORI_KEYS_DIR/${pair_tag}_A.key"
      --right-output-key "$ORI_KEYS_DIR/${pair_tag}_B.key"
      --report-path "$REPORTS_DIR/${pair_tag}.summary.json"
      --matcher-method "$MATCHER_METHOD"
      --band "$BAND"
      --ratio-test "$RATIO_TEST"
      --num-worker-parallel-cpu "$NUM_WORKER_PARALLEL_CPU"
      --gpu-batch-size "$GPU_BATCH_SIZE"
      --gpu-min-batch-size "$GPU_MIN_BATCH_SIZE"
      --gpu-max-batch-size "$GPU_MAX_BATCH_SIZE"
      --log-level "$LOG_LEVEL"
    )
    [[ -z "$MAX_FEATURES" ]] || match_args+=(--max-features "$MAX_FEATURES")
    [[ "$USE_PARALLEL_CPU" == "1" ]] && match_args+=(--use-parallel-cpu) || match_args+=(--no-parallel-cpu)
    [[ "$USE_GPU" == "1" ]] && match_args+=(--use-gpu)
    [[ "$GPU_DYNAMIC_BATCH" == "1" ]] && match_args+=(--gpu-dynamic-batch) || match_args+=(--no-gpu-dynamic-batch)
    append_command "${match_args[@]}"
  done < "$IMAGES_OVERLAP_LIST"
fi

append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_merge.py" \
  "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH" \
  --network-id "raw_image_matching" \
  --description "Merged raw image matching ControlNet" \
  --pair-list "$MERGE_PAIR_LIST_PATH" \
  --report-json "$MERGE_REPORT_PATH"

if [[ "$SKIP_FINAL_MERGE" != "1" ]]; then
  append_command bash "$MERGE_SCRIPT_PATH"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "dry run complete: $COMMAND_SCRIPT"
  exit 0
fi

die "execution mode is not implemented yet"
