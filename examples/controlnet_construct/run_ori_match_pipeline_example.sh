#!/usr/bin/env bash
# End-to-end raw/original image matching ControlNet pipeline example runner.
#
# Author: Geng Xun
# Created: 2026-05-23
# Updated: 2026-05-23  Geng Xun added the raw image ControlNet batch wrapper.
# Updated: 2026-05-23  Geng Xun enabled deep matcher and adaptive-routing forwarding for raw image matching.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)

DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work_ori"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM="1.0"
DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="drop"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"
HOST_PYTHON_EXECUTABLE="${HOST_PYTHON_EXECUTABLE:-python}"

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

run_command() {
  log "$1"
  shift
  append_command "$@"
  "$@"
}

resolve_path() {
  local path=$1
  if command -v realpath >/dev/null 2>&1; then
    realpath -m -- "$path"
  else
    python - "$path" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
  fi
}

extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  "$HOST_PYTHON_EXECUTABLE" - "$config_path" "$field_name" "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path

config_path, field_name, repo_root = sys.argv[1:]
sys.path.insert(0, str(Path(repo_root) / "examples"))

from image_match.image_match import format_image_match_default_for_shell, load_image_match_defaults_from_config

defaults = load_image_match_defaults_from_config(config_path)
if field_name == "deep_matcher_config_path" and field_name not in defaults:
    field_name = "deep_match_config_path"
if field_name not in defaults:
    raise SystemExit(0)
print(format_image_match_default_for_shell(defaults[field_name]))
PY
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

extract_adaptive_routing_deep_preset_args() {
  local config_path=$1
  "$HOST_PYTHON_EXECUTABLE" - "$config_path" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).expanduser().resolve(strict=False)
repo_root = Path(sys.argv[2]).expanduser().resolve(strict=False)
payload = json.loads(config_path.read_text(encoding="utf-8"))
section = payload.get("ImageMatch", {})
presets = section.get("adaptive_routing_deep_presets", {}) if isinstance(section, dict) else {}
if not isinstance(presets, dict):
    raise SystemExit(0)

def resolve_path(value: object) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    config_relative = config_path.parent / path
    if config_relative.is_file():
        return config_relative.resolve(strict=False)
    repo_relative = repo_root / path
    if repo_relative.is_file():
        return repo_relative.resolve(strict=False)
    return repo_relative.resolve(strict=False)

for key, value in presets.items():
    if value in (None, ""):
        continue
    print(f"{str(key).strip().lower()}={resolve_path(value)}")
PY
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

build_match_args() {
  local left=$1
  local right=$2
  local pair_id=$3
  local pair_tag=$4
  local pair_net=$5
  local left_key=$6
  local right_key=$7
  local pair_report=$8

  match_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-ori-match
    "$left" "$right" "$CONFIG_PATH" "$pair_net"
    --pair-id "$pair_id"
    --left-output-key "$left_key"
    --right-output-key "$right_key"
    --report-path "$pair_report"
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
  [[ -z "$DEEP_MATCH_CONFIG_PATH" ]] || match_args+=(--deep-match-config-path "$DEEP_MATCH_CONFIG_PATH")
  [[ "$ADAPTIVE_ROUTING" == "1" ]] && match_args+=(--adaptive-routing) || match_args+=(--no-adaptive-routing)
  match_args+=(--adaptive-routing-profile "$ADAPTIVE_ROUTING_PROFILE")
  match_args+=(--pre-ransac-max-ground-distance-km "$PRE_RANSAC_MAX_GROUND_DISTANCE_KM")
  match_args+=(--pre-ransac-ground-lookup-failure-policy "$PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY")
  [[ "$USE_PARALLEL_CPU" == "1" ]] && match_args+=(--use-parallel-cpu) || match_args+=(--no-parallel-cpu)
  [[ "$USE_GPU" == "1" ]] && match_args+=(--use-gpu)
  [[ "$GPU_DYNAMIC_BATCH" == "1" ]] && match_args+=(--gpu-dynamic-batch) || match_args+=(--no-gpu-dynamic-batch)
  local preset_arg
  for preset_arg in "${ADAPTIVE_ROUTING_DEEP_PRESET_ARGS[@]}"; do
    match_args+=(--adaptive-routing-deep-preset "$preset_arg")
  done
}

require_existing_file() {
  local path=$1
  [[ -f "$path" ]] || die "expected from-ori-match output not found: $path"
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
  --matcher-method NAME          Matcher method forwarded to from-ori-match. Default: bf
  --deep-match-config-path PATH  Deep matcher preset forwarded to from-ori-match.
  --deep-match-mode MODE         Deep matcher mode. Only direct is supported here.
  --adaptive-routing             Enable adaptive matcher routing in from-ori-match.
  --no-adaptive-routing          Disable adaptive matcher routing in from-ori-match. Default.
  --adaptive-routing-profile NAME
                                  Adaptive-routing quality profile. Default: balanced
  --adaptive-routing-deep-preset KEY=PATH
                                  Adaptive deep preset mapping. Repeat as needed.
  --pre-ransac-max-ground-distance-km VALUE
                                  Maximum paired ground distance retained before RANSAC. Use 0 to disable.
                                  Default: 1.0 unless omitted and resolved from ImageMatch config.
  --pre-ransac-ground-lookup-failure-policy VALUE
                                  Ground lookup failure policy for pre-RANSAC filtering: drop or keep.
                                  Default: drop unless omitted and resolved from ImageMatch config.
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
MATCHER_METHOD="bf"
DEEP_MATCH_CONFIG_PATH=""
ADAPTIVE_ROUTING="0"
ADAPTIVE_ROUTING_PROFILE="balanced"
PRE_RANSAC_MAX_GROUND_DISTANCE_KM="$DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM"
PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="$DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY"
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
DEEP_MATCH_MODE="direct"
ADAPTIVE_ROUTING_DEEP_PRESET_ARGS=()
explicit_adaptive_routing=""
explicit_adaptive_routing_profile=""
explicit_deep_match_config_path=""
explicit_pre_ransac_max_ground_distance_km=""
explicit_pre_ransac_ground_lookup_failure_policy=""
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
    --deep-match-config-path) [[ $# -ge 2 ]] || die "missing value for --deep-match-config-path"; DEEP_MATCH_CONFIG_PATH=$2; explicit_deep_match_config_path="1"; shift 2 ;;
    --adaptive-routing) ADAPTIVE_ROUTING="1"; explicit_adaptive_routing="1"; shift ;;
    --no-adaptive-routing) ADAPTIVE_ROUTING="0"; explicit_adaptive_routing="1"; shift ;;
    --adaptive-routing-profile) [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-profile"; ADAPTIVE_ROUTING_PROFILE=$2; explicit_adaptive_routing_profile="1"; shift 2 ;;
    --pre-ransac-max-ground-distance-km) [[ $# -ge 2 ]] || die "missing value for --pre-ransac-max-ground-distance-km"; PRE_RANSAC_MAX_GROUND_DISTANCE_KM=$2; explicit_pre_ransac_max_ground_distance_km="1"; shift 2 ;;
    --pre-ransac-ground-lookup-failure-policy)
      [[ $# -ge 2 ]] || die "missing value for --pre-ransac-ground-lookup-failure-policy"
      case "$2" in drop|keep) ;; *) die "--pre-ransac-ground-lookup-failure-policy must be drop or keep" ;; esac
      PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY=$2
      explicit_pre_ransac_ground_lookup_failure_policy="1"
      shift 2
      ;;
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
    --deep-match-mode) [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"; DEEP_MATCH_MODE=$2; shift 2 ;;
    --deep-match-mode=*) DEEP_MATCH_MODE=${1#*=}; shift ;;
    --adaptive-routing-deep-preset) [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-deep-preset"; ADAPTIVE_ROUTING_DEEP_PRESET_ARGS+=("$2"); shift 2 ;;
    --skip-final-merge) SKIP_FINAL_MERGE="1"; shift ;;
    --dry-run) DRY_RUN="1"; shift ;;
    --log-level) [[ $# -ge 2 ]] || die "missing value for --log-level"; LOG_LEVEL=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

case "$PAIR_ID_START" in
  ''|*[!0-9]*) die "--pair-id-start must be a positive integer" ;;
esac
if [[ "$PAIR_ID_START" -lt 1 ]]; then
  die "--pair-id-start must be at least 1"
fi

WORK_DIR=$(resolve_path "${WORK_DIR:-$REPO_ROOT/$DEFAULT_WORK_DIR_RELATIVE}")
mkdir -p "$WORK_DIR"

CONFIG_PATH=$(resolve_path "${CONFIG_PATH:-$REPO_ROOT/$DEFAULT_CONFIG_RELATIVE}")
ORIGINAL_LIST=$(resolve_path "${ORIGINAL_LIST:-$WORK_DIR/original_images.lis}")
IMAGES_OVERLAP_LIST=$(resolve_path "${IMAGES_OVERLAP_LIST:-$WORK_DIR/images_overlap.lis}")
[[ -f "$CONFIG_PATH" ]] || die "controlnet config not found: $CONFIG_PATH"

case "$DEEP_MATCH_MODE" in
  direct) ;;
  *) die "--deep-match-mode currently supports only direct in the raw image space wrapper" ;;
esac

if [[ -z "$explicit_adaptive_routing" ]]; then
  config_enable_adaptive_routing=$(extract_image_match_config_value "$CONFIG_PATH" "enable_adaptive_routing")
  [[ -z "$config_enable_adaptive_routing" ]] || ADAPTIVE_ROUTING="$config_enable_adaptive_routing"
fi
if [[ -z "$explicit_adaptive_routing_profile" ]]; then
  config_adaptive_routing_profile=$(extract_image_match_config_value "$CONFIG_PATH" "adaptive_routing_profile")
  [[ -z "$config_adaptive_routing_profile" ]] || ADAPTIVE_ROUTING_PROFILE="$config_adaptive_routing_profile"
fi
if [[ -z "$explicit_deep_match_config_path" ]]; then
  config_deep_matcher_config_path=$(extract_image_match_config_value "$CONFIG_PATH" "deep_matcher_config_path")
  if [[ -n "$config_deep_matcher_config_path" ]]; then
    DEEP_MATCH_CONFIG_PATH=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
  fi
elif [[ -n "$DEEP_MATCH_CONFIG_PATH" ]]; then
  DEEP_MATCH_CONFIG_PATH=$(resolve_path "$DEEP_MATCH_CONFIG_PATH")
fi
if [[ -z "$explicit_pre_ransac_max_ground_distance_km" ]]; then
  config_pre_ransac_max_ground_distance_km=$(extract_image_match_config_value "$CONFIG_PATH" "pre_ransac_max_ground_distance_km")
  [[ -z "$config_pre_ransac_max_ground_distance_km" ]] || PRE_RANSAC_MAX_GROUND_DISTANCE_KM="$config_pre_ransac_max_ground_distance_km"
fi
if [[ -z "$explicit_pre_ransac_ground_lookup_failure_policy" ]]; then
  config_pre_ransac_ground_lookup_failure_policy=$(extract_image_match_config_value "$CONFIG_PATH" "pre_ransac_ground_lookup_failure_policy")
  [[ -z "$config_pre_ransac_ground_lookup_failure_policy" ]] || PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="$config_pre_ransac_ground_lookup_failure_policy"
fi
if [[ "${#ADAPTIVE_ROUTING_DEEP_PRESET_ARGS[@]}" -eq 0 ]]; then
  while IFS= read -r preset_arg; do
    [[ -z "$preset_arg" ]] || ADAPTIVE_ROUTING_DEEP_PRESET_ARGS+=("$preset_arg")
  done < <(extract_adaptive_routing_deep_preset_args "$CONFIG_PATH")
fi

ORI_KEYS_DIR="$WORK_DIR/ori_keys"
PAIR_NETS_DIR="$WORK_DIR/ori_pair_nets"
REPORTS_DIR="$WORK_DIR/reports"
MERGE_DIR="$WORK_DIR/merge"
COMMAND_SCRIPT="$WORK_DIR/command.sh"
BATCH_REPORT_PATH="$REPORTS_DIR/ori_match_batch_summary.json"
PAIRS_JSON="$REPORTS_DIR/.ori_match_pairs.jsonl"
OVERLAP_REPORT_PATH="$REPORTS_DIR/image_overlap_summary.json"
MERGE_OUTPUT_NET="$MERGE_DIR/ori_matching_merged.net"
MERGE_SCRIPT_PATH="$MERGE_DIR/merge_all_controlnets.sh"
MERGE_PAIR_LIST_PATH="$MERGE_DIR/merge_all_controlnets.lis"
MERGE_REPORT_PATH="$MERGE_DIR/controlnet_merge_summary.json"

mkdir -p "$ORI_KEYS_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n'
} > "$COMMAND_SCRIPT"
chmod 755 "$COMMAND_SCRIPT"

[[ -f "$ORIGINAL_LIST" ]] || die "original image list not found: $ORIGINAL_LIST"
if [[ "$DRY_RUN" != "1" ]]; then
  : > "$PAIRS_JSON"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"
else
  run_command "stage 1: discovering overlap pairs" "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"
  [[ -s "$IMAGES_OVERLAP_LIST" ]] || die "images overlap list is empty: $IMAGES_OVERLAP_LIST"
fi

pair_index=0
if [[ -f "$IMAGES_OVERLAP_LIST" ]]; then
  while IFS=, read -r left right; do
    [[ -n "$left" ]] || continue
    [[ -n "$right" ]] || die "invalid overlap pair line missing right-hand entry"
    pair_index=$((pair_index + 1))
    pair_id="${PAIR_ID_PREFIX}$((PAIR_ID_START + pair_index - 1))"
    pair_tag=$(pair_tag_from_paths "$left" "$right")
    pair_net="$PAIR_NETS_DIR/${pair_tag}.net"
    left_key="$ORI_KEYS_DIR/${pair_tag}_A.key"
    right_key="$ORI_KEYS_DIR/${pair_tag}_B.key"
    pair_report="$REPORTS_DIR/${pair_tag}.summary.json"
    build_match_args "$left" "$right" "$pair_id" "$pair_tag" "$pair_net" "$left_key" "$right_key" "$pair_report"
    if [[ "$DRY_RUN" == "1" ]]; then
      append_command "${match_args[@]}"
    else
      run_command "stage 2: matching pair $pair_tag" "${match_args[@]}"
      require_existing_file "$pair_net"
      require_existing_file "$left_key"
      require_existing_file "$right_key"
      require_existing_file "$pair_report"
      "$HOST_PYTHON_EXECUTABLE" - "$PAIRS_JSON" "$left,$right" "$pair_id" "$pair_net" "$left_key" "$right_key" "$pair_report" <<'PY'
import json
import sys
from pathlib import Path

jsonl, pair, pair_id, output_net, left_key, right_key, report_path = sys.argv[1:]
record = {
    "pair": pair,
    "pair_id": pair_id,
    "output_net": output_net,
    "left_key": left_key,
    "right_key": right_key,
    "report_path": report_path,
    "status": "success",
}
with Path(jsonl).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
PY
    fi
  done < "$IMAGES_OVERLAP_LIST"
else
  log "warning: overlap list not found; pair commands were not expanded: $IMAGES_OVERLAP_LIST" >&2
fi

merge_args=(
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_merge.py"
  "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH"
  --network-id "raw_image_matching"
  --description "Merged raw image matching ControlNet"
  --pair-list "$MERGE_PAIR_LIST_PATH"
  --report-json "$MERGE_REPORT_PATH"
  --strict
)

if [[ "$DRY_RUN" == "1" ]]; then
  append_command "${merge_args[@]}"
else
  run_command "stage 3: generating merge script" "${merge_args[@]}"
fi

if [[ "$SKIP_FINAL_MERGE" != "1" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    append_command bash "$MERGE_SCRIPT_PATH"
  else
    run_command "stage 4: executing merge script" bash "$MERGE_SCRIPT_PATH"
    require_existing_file "$MERGE_OUTPUT_NET"
  fi
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "dry run complete: $COMMAND_SCRIPT"
  exit 0
fi

"$HOST_PYTHON_EXECUTABLE" - "$BATCH_REPORT_PATH" "$PAIRS_JSON" "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH" "$PAIR_ID_PREFIX" "$PAIR_ID_START" "$MATCHER_METHOD" "$DEEP_MATCH_CONFIG_PATH" "$ADAPTIVE_ROUTING" "$ADAPTIVE_ROUTING_PROFILE" "$DEEP_MATCH_MODE" <<'PY'
import json
import sys
from pathlib import Path

(
    report_path,
    pairs_json,
    original_list,
    overlap_list,
    pair_nets_dir,
    reports_dir,
    merge_output_net,
    merge_script_path,
    pair_id_prefix,
    pair_id_start,
    matcher_method,
    deep_match_config_path,
    adaptive_routing,
    adaptive_routing_profile,
    deep_match_mode,
) = sys.argv[1:]
pairs = [
    json.loads(line)
    for line in Path(pairs_json).read_text(encoding="utf-8").splitlines()
    if line.strip()
]
payload = {
    "mode": "from-ori-match-batch-wrapper",
    "original_list": original_list,
    "images_overlap_list": overlap_list,
    "pair_count": len(pairs),
    "pair_id_prefix": pair_id_prefix,
    "pair_id_start": int(pair_id_start),
    "matcher_method": matcher_method,
    "deep_match_config_path": deep_match_config_path or None,
    "adaptive_routing": adaptive_routing == "1",
    "adaptive_routing_profile": adaptive_routing_profile,
    "deep_match_mode": deep_match_mode,
    "pair_net_directory": pair_nets_dir,
    "report_directory": reports_dir,
    "merge_output_net": merge_output_net,
    "merge_script_path": merge_script_path,
    "pairs": pairs,
}
Path(report_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

log "raw image pair matching complete: $BATCH_REPORT_PATH"
