#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD=""

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
  6. optionally run merge_control_measure.py as a post-processing step

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --config PATH                   ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --use_parallel_cpu              Forward explicit CPU tile parallelism enable flag to image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in image_match.py and force serial tile matching
  --pair-id-prefix PREFIX         Batch pair-id prefix. Default: S
  --pair-id-start N               Batch pair-id starting index. Default: 1
  --valid-pixel-percent-threshold VALUE
                                 Forwarded to image_match.py. If omitted, this script
                                 falls back to config JSON field ImageMatch.valid_pixel_percent_threshold
                                 when present; otherwise image_match.py keeps its own default (0.0).
  --merged-net PATH               Final merged ControlNet output path. Default: <work-dir>/merge/dom_matching_merged.net
  --merge-script PATH             Generated merge shell path. Default: <work-dir>/merge/merge_all_controlnets.sh
  --merge-log PATH                cnetmerge log path. Default: <work-dir>/merge/cnetmerge.log
  --pair-list PATH                Optional explicit cnetmerge input list path. Default: auto-named by controlnet_merge.py
  --timing-json PATH              Structured JSON timing output. Default: <work-dir>/reports/pipeline_timing.json
  --network-id VALUE              NETWORKID passed to controlnet_merge.py. Default: read from config JSON
  --description TEXT              Description passed to controlnet_merge.py. Default: Merged DOM matching ControlNet
  --cnetmerge PATH                cnetmerge executable path written into the generated merge shell. Default: $CNETMERGE_EXECUTABLE or cnetmerge
  --skip-final-merge              Generate merge shell but do not execute it
  --post-merge-control-measure    After final cnetmerge, run merge_control_measure.py on the merged network
  --post-merge-output PATH        Output path for the post-processed merged ControlNet. Default: auto-named by merge_control_measure.py
  --post-merge-decimals N         Rounded hash decimals for merge_control_measure.py. Default: 1
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

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

initialize_timing_json() {
  "$PYTHON_EXECUTABLE" - "$TIMING_JSON_PATH" "$REPO_ROOT" "$WORK_DIR" "$PYTHON_EXECUTABLE" "$(timestamp_utc)" <<'PY'
import json
import sys
from pathlib import Path

timing_path = Path(sys.argv[1])
payload = {
    "pipeline": {
        "repo_root": sys.argv[2],
        "work_dir": sys.argv[3],
        "python_executable": sys.argv[4],
        "started_at": sys.argv[5],
        "status": "running",
    },
    "steps": [],
    "pair_matches": [],
}
timing_path.parent.mkdir(parents=True, exist_ok=True)
timing_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

append_timing_json_entry() {
  "$PYTHON_EXECUTABLE" - "$TIMING_JSON_PATH" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" <<'PY'
import json
import sys
from pathlib import Path

timing_path = Path(sys.argv[1])
section = sys.argv[2]
name = sys.argv[3]
status = sys.argv[4]
start_epoch = int(sys.argv[5])
end_epoch = int(sys.argv[6])
start_iso = sys.argv[7]
end_iso = sys.argv[8]
exit_code = int(sys.argv[9])

if timing_path.exists():
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
else:
    payload = {"pipeline": {"status": "running"}, "steps": [], "pair_matches": []}

payload.setdefault(section, []).append(
    {
        "name": name,
        "status": status,
        "started_at": start_iso,
        "finished_at": end_iso,
        "duration_seconds": max(0, end_epoch - start_epoch),
        "start_epoch": start_epoch,
        "end_epoch": end_epoch,
        "exit_code": exit_code,
    }
)
timing_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

finalize_timing_json() {
  "$PYTHON_EXECUTABLE" - "$TIMING_JSON_PATH" "$1" "$(timestamp_utc)" <<'PY'
import json
import sys
from pathlib import Path

timing_path = Path(sys.argv[1])
status = sys.argv[2]
finished_at = sys.argv[3]

if not timing_path.exists():
    raise SystemExit(0)

payload = json.loads(timing_path.read_text(encoding="utf-8"))
payload.setdefault("pipeline", {})["status"] = status
payload["pipeline"]["finished_at"] = finished_at
timing_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

run_timed_command() {
  local section=$1
  local name=$2
  shift 2

  local start_epoch
  local end_epoch
  local start_iso
  local end_iso
  local status
  local exit_code
  local duration

  start_epoch=$(date +%s)
  start_iso=$(timestamp_utc)
  log "START ${name}"

  if "$@"; then
    status="success"
    exit_code=0
  else
    exit_code=$?
    status="failed"
  fi

  end_epoch=$(date +%s)
  end_iso=$(timestamp_utc)
  duration=$((end_epoch - start_epoch))
  log "END ${name} status=${status} duration=${duration}s"
  append_timing_json_entry "$section" "$name" "$status" "$start_epoch" "$end_epoch" "$start_iso" "$end_iso" "$exit_code"
  return "$exit_code"
}

run_required_timed_step() {
  local section=$1
  local name=$2
  shift 2

  run_timed_command "$section" "$name" "$@"
  local exit_code=$?
  if [[ "$exit_code" -ne 0 ]]; then
    finalize_timing_json "failed"
    return "$exit_code"
  fi
  return 0
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
    local match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py"
      "${dom_by_original[$left]}"
      "${dom_by_original[$right]}"
      "$DOM_KEYS_DIR/${pair_tag}_A.key"
      "$DOM_KEYS_DIR/${pair_tag}_B.key"
      --metadata-output "$MATCH_METADATA_DIR/${pair_tag}.json"
      --match-visualization-output-dir "$PRE_RANSAC_MATCH_VIZ_DIR"
    )

    if [[ -n "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
      match_args+=(--valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD")
    fi
    if [[ "$USE_PARALLEL_CPU" == "1" ]]; then
      match_args+=(--use_parallel_cpu)
    else
      match_args+=(--no-parallel-cpu)
    fi

    run_timed_command "pair_matches" "image_match:${pair_tag}" "${match_args[@]}"
    local match_status=$?
    if [[ "$match_status" -ne 0 ]]; then
      return "$match_status"
    fi

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
    --pair-id-start "$PAIR_ID_START" \
    --write-match-visualization \
    --match-visualization-output-dir "$POST_RANSAC_MATCH_VIZ_DIR"
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

run_step_5_post_merge_control_measure() {
  [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]] || return 0

  if [[ "$SKIP_FINAL_MERGE" == "1" ]]; then
    die "--post-merge-control-measure cannot be used together with --skip-final-merge"
  fi

  log "Step 5/5: post-processing merged ControlNet -> ${POST_MERGE_OUTPUT_PATH:-auto-named by merge_control_measure.py}"

  local post_merge_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/merge_control_measure.py"
    "$ORIGINAL_LIST"
    "$MERGED_NET_PATH"
  )

  if [[ -n "$POST_MERGE_OUTPUT_PATH" ]]; then
    post_merge_args+=("$POST_MERGE_OUTPUT_PATH")
  fi

  post_merge_args+=(--decimals "$POST_MERGE_DECIMALS")

  "${post_merge_args[@]}"
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
  local timing_json_input=""
  local post_merge_output_input=""

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"
  CNETMERGE_PATH="${CNETMERGE_EXECUTABLE:-cnetmerge}"
  PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
  PAIR_ID_START="$DEFAULT_PAIR_ID_START"
  VALID_PIXEL_PERCENT_THRESHOLD="$DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD"
  USE_PARALLEL_CPU="1"
  NETWORK_ID=""
  MERGE_DESCRIPTION="Merged DOM matching ControlNet"
  SKIP_FINAL_MERGE="0"
  POST_MERGE_CONTROL_MEASURE="0"
  POST_MERGE_DECIMALS="1"

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
      --use_parallel_cpu|--use-parallel-cpu)
        USE_PARALLEL_CPU="1"
        shift
        ;;
      --no-parallel-cpu|--no_parallel_cpu)
        USE_PARALLEL_CPU="0"
        shift
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
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        VALID_PIXEL_PERCENT_THRESHOLD=$2
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
      --timing-json)
        [[ $# -ge 2 ]] || die "missing value for --timing-json"
        timing_json_input=$2
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
      --post-merge-control-measure)
        POST_MERGE_CONTROL_MEASURE="1"
        shift
        ;;
      --post-merge-output)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-output"
        post_merge_output_input=$2
        shift 2
        ;;
      --post-merge-decimals)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-decimals"
        POST_MERGE_DECIMALS=$2
        shift 2
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
  PRE_RANSAC_MATCH_VIZ_DIR="$WORK_DIR/match_viz"
  POST_RANSAC_MATCH_VIZ_DIR="$WORK_DIR/match_viz_post_ransac"
  PAIR_NETS_DIR="$WORK_DIR/pair_nets"
  REPORTS_DIR="$WORK_DIR/reports"
  MERGE_DIR="$WORK_DIR/merge"
  MERGED_NET_PATH="${merged_net_input:-$MERGE_DIR/dom_matching_merged.net}"
  MERGE_SCRIPT_PATH="${merge_script_input:-$MERGE_DIR/merge_all_controlnets.sh}"
  MERGE_LOG_PATH="${merge_log_input:-$MERGE_DIR/cnetmerge.log}"
  PAIR_LIST_PATH="$pair_list_input"
  TIMING_JSON_PATH="${timing_json_input:-$REPORTS_DIR/pipeline_timing.json}"
  POST_MERGE_OUTPUT_PATH="$post_merge_output_input"

  require_file "$ORIGINAL_LIST"
  require_file "$DOM_LIST"
  require_file "$CONFIG_PATH"

  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" && "$SKIP_FINAL_MERGE" == "1" ]]; then
    die "--post-merge-control-measure cannot be used together with --skip-final-merge"
  fi

  mkdir -p "$DOM_KEYS_DIR" "$MATCH_METADATA_DIR" "$PRE_RANSAC_MATCH_VIZ_DIR" "$POST_RANSAC_MATCH_VIZ_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"

  if [[ -z "$NETWORK_ID" ]]; then
    NETWORK_ID=$(extract_network_id_from_config "$CONFIG_PATH")
  fi
  if [[ -z "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
    VALID_PIXEL_PERCENT_THRESHOLD=$(extract_valid_pixel_percent_threshold_from_config "$CONFIG_PATH")
  fi

  initialize_timing_json

  log "Repository root: $REPO_ROOT"
  log "Work directory: $WORK_DIR"
  log "Python executable: $PYTHON_EXECUTABLE"
  log "Original list: $ORIGINAL_LIST"
  log "DOM list: $DOM_LIST"
  log "Config: $CONFIG_PATH"
  log "Network ID: $NETWORK_ID"
  if [[ "$USE_PARALLEL_CPU" == "1" ]]; then
    log "CPU parallel tile matching: enabled"
  else
    log "CPU parallel tile matching: disabled"
  fi
  if [[ -n "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
    log "Valid pixel percent threshold: $VALID_PIXEL_PERCENT_THRESHOLD"
  else
    log "Valid pixel percent threshold: image_match.py default"
  fi
  log "cnetmerge executable: $CNETMERGE_PATH"
  log "Timing JSON: $TIMING_JSON_PATH"
  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]]; then
    log "Post-merge ControlNet deduplication: enabled"
    log "Post-merge decimals: $POST_MERGE_DECIMALS"
    if [[ -n "$POST_MERGE_OUTPUT_PATH" ]]; then
      log "Post-merge output: $POST_MERGE_OUTPUT_PATH"
    else
      log "Post-merge output: auto-named by merge_control_measure.py"
    fi
  else
    log "Post-merge ControlNet deduplication: disabled"
  fi

  run_required_timed_step "steps" "image_overlap" run_step_1_image_overlap
  run_required_timed_step "steps" "image_match_batch" run_step_2_image_match_batch
  run_required_timed_step "steps" "pairwise_controlnets" run_step_3_pairwise_controlnets
  run_required_timed_step "steps" "merge" run_step_4_merge
  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]]; then
    run_required_timed_step "steps" "merge_control_measure" run_step_5_post_merge_control_measure
  fi

  finalize_timing_json "success"

  log "Pipeline completed"
  log "Key outputs:"
  log "  overlap list: $IMAGES_OVERLAP_LIST"
  log "  DOM keys: $DOM_KEYS_DIR"
  log "  pre-RANSAC match viz: $PRE_RANSAC_MATCH_VIZ_DIR"
  log "  post-RANSAC match viz: $POST_RANSAC_MATCH_VIZ_DIR"
  log "  pairwise nets: $PAIR_NETS_DIR"
  log "  reports: $REPORTS_DIR"
  log "  merge script: $MERGE_SCRIPT_PATH"
  log "  merged net: $MERGED_NET_PATH"
  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]]; then
    if [[ -n "$POST_MERGE_OUTPUT_PATH" ]]; then
      log "  post-merged net: $POST_MERGE_OUTPUT_PATH"
    else
      log "  post-merged net: auto-named beside $MERGED_NET_PATH"
    fi
  fi
  log "  timing json: $TIMING_JSON_PATH"
}

main "$@"
