#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD=""
DEFAULT_INVALID_PIXEL_RADIUS="1"

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


# -----------------------------------------------------------------------------
# One-click parameter presets for run_pipeline_example.sh (copy & paste)
#
# Conservative (stability first):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --valid-pixel-percent-threshold 0.08 \
#   --invalid-pixel-radius 2 \
#   --matcher-method flann \
#   --enable-low-resolution-offset-estimation \
#   --low-resolution-level 3 \
#   --low-resolution-max-mean-reprojection-error-pixels 2.5 \
#   --low-resolution-min-retained-match-count 8 \
#   --low-resolution-max-mean-projected-offset-meters 1200 \
#   --num-worker-parallel-cpu 8
#
# Balanced (recommended default):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --valid-pixel-percent-threshold 0.05 \
#   --invalid-pixel-radius 1 \
#   --matcher-method flann \
#   --enable-low-resolution-offset-estimation \
#   --low-resolution-level 3 \
#   --low-resolution-max-mean-reprojection-error-pixels 3.0 \
#   --low-resolution-min-retained-match-count 5 \
#   --low-resolution-max-mean-projected-offset-meters 2000 \
#   --num-worker-parallel-cpu 8
#
# Aggressive (recall first):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --valid-pixel-percent-threshold 0.02 \
#   --invalid-pixel-radius 1 \
#   --matcher-method bf \
#   --enable-low-resolution-offset-estimation \
#   --low-resolution-level 4 \
#   --low-resolution-max-mean-reprojection-error-pixels 4.0 \
#   --low-resolution-min-retained-match-count 4 \
#   --low-resolution-max-mean-projected-offset-meters 3500 \
#   --num-worker-parallel-cpu 12
# -----------------------------------------------------------------------------


usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_pipeline_example.sh [options]

Run the DOM matching ControlNet example pipeline end to end:
  1. image_overlap.py
  2. image_match.py (for every pair in images_overlap.lis)
  3. controlnet_stereopair.py from-dom-batch
  4. controlnet_merge.py + execute the generated merge_all_controlnets.sh by default
  5. optionally run merge_control_measure.py as a post-processing step

Default behavior:
  - CPU tile parallelism is enabled unless --no-parallel-cpu is provided.
  - image_match.py writes pre-RANSAC match visualizations to <work-dir>/match_viz.
  - from-dom-batch writes post-RANSAC match visualizations to <work-dir>/match_viz_post_ransac.

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --config PATH                   ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
                                  Its ImageMatch section is forwarded to image_match.py as default matching parameters.
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --use-parallel-cpu              Forward explicit CPU tile parallelism enable flag to image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in image_match.py and force serial tile matching
  --num-worker-parallel-cpu N     Maximum worker-process count forwarded to image_match.py when CPU parallelism is enabled.
                                  Default: 8. If omitted, this script falls back to config JSON field
                                  ImageMatch.num_worker_parallel_cpu when present. Valid range: 1~4096.
  --pair-id-prefix PREFIX         Batch pair-id prefix. Default: S
  --pair-id-start N               Batch pair-id starting index. Default: 1
  --valid-pixel-percent-threshold VALUE
                                 Forwarded to image_match.py. If omitted, this script
                                 falls back to config JSON field ImageMatch.valid_pixel_percent_threshold
                                 when present; otherwise image_match.py keeps its own default (0.0).
  --invalid-pixel-radius N        Forwarded to image_match.py to suppress feature detection near
                                 invalid pixels and image borders. If omitted, this script falls
                                 back to config JSON field ImageMatch.invalid_pixel_radius when present;
                                 otherwise image_match.py keeps its own default.
--matcher-method NAME           Forwarded to image_match.py to select SIFT descriptor matcher backend.
                                 Supported values: bf, flann. If omitted, this script falls back to
                                 config JSON field ImageMatch.matcher_method when present; otherwise
                                 image_match.py keeps its own default.
  --enable-low-resolution-offset-estimation
                                 Forwarded to image_match.py to enable low-resolution DOM coarse
                                 registration before full-resolution overlap preparation.
  --low-resolution-level N        Forwarded to image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_level when present;
                                 otherwise image_match.py keeps its own default.
  --low-resolution-max-mean-reprojection-error-pixels VALUE
                                 Forwarded to image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_max_mean_reprojection_error_pixels
                                 when present; otherwise image_match.py keeps its own default.
  --low-resolution-min-retained-match-count N
                                 Forwarded to image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_min_retained_match_count
                                 when present; otherwise image_match.py keeps its own default.
  --low-resolution-max-mean-projected-offset-meters VALUE
                                 Forwarded to image_match.py. Unit: meters. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_max_mean_projected_offset_meters
                                 when present; otherwise image_match.py keeps its own default.
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

Examples:
  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work

  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work \
    --skip-final-merge

  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work \
    --num-worker-parallel-cpu 4 \
    --post-merge-control-measure \
    --post-merge-decimals 1

  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work \
    --post-merge-control-measure \
    --post-merge-output work/merge/dom_matching_merged_merged_measures.net
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

pipeline_total_step_count() {
  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]]; then
    printf '5\n'
  else
    printf '4\n'
  fi
}

pipeline_step_label() {
  local step_index=$1
  printf 'Step %s/%s' "$step_index" "$(pipeline_total_step_count)"
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

extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  local container_order=${3:-top-level-first}
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py" \
    --config "$config_path" \
    --print-config-default "$field_name" \
    --print-config-default-container-order "$container_order"
}

run_step_1_image_overlap() {
  log "$(pipeline_step_label 1): computing overlap pairs -> ${IMAGES_OVERLAP_LIST}"
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" \
    "$IMAGES_OVERLAP_LIST"
}

run_step_2_image_match_batch() {
  log "$(pipeline_step_label 2): matching DOM pairs listed in ${IMAGES_OVERLAP_LIST}"

  if [[ "$ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION" == "1" ]]; then
    log "  preparing reusable low-resolution DOM list -> ${LOW_RESOLUTION_DOM_LIST}"
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/prepare_low_resolution_doms.py" \
      "$DOM_LIST" \
      "$LOW_RESOLUTION_DOM_LIST" \
      --level "$LOW_RESOLUTION_LEVEL" \
      --output-dir "$LOW_RESOLUTION_DOM_DIR" \
      --report-json "$LOW_RESOLUTION_DOM_REPORT"
  fi

  declare -A dom_by_original=()
  while IFS=$'\t' read -r original dom; do
    [[ -n "$original" ]] || continue
    [[ -n "$dom" ]] || die "DOM list alignment failed while reading paired original/DOM lists"
    dom_by_original["$original"]="$dom"
  done < <(paste "$ORIGINAL_LIST" "$DOM_LIST")

  declare -A low_resolution_dom_by_original=()
  if [[ "$ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION" == "1" ]]; then
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
    left_stem=$(basename "${left%.*}")
    right_stem=$(basename "${right%.*}")
    pair_tag="${left_stem}__${right_stem}"

    log "  matching pair ${pair_tag}"
    local match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py"
      --config "$CONFIG_PATH"
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
    match_args+=(--invalid-pixel-radius "$INVALID_PIXEL_RADIUS")
    match_args+=(--matcher-method "$MATCHER_METHOD")
    if [[ "$USE_PARALLEL_CPU" == "1" ]]; then
      match_args+=(--use-parallel-cpu)
    else
      match_args+=(--no-parallel-cpu)
    fi
    match_args+=(--num-worker-parallel-cpu "$NUM_WORKER_PARALLEL_CPU")
    if [[ "$ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION" == "1" ]]; then
      if [[ -z "${low_resolution_dom_by_original[$left]+x}" ]]; then
        die "no low-resolution DOM path found for left original image: $left"
      fi
      if [[ -z "${low_resolution_dom_by_original[$right]+x}" ]]; then
        die "no low-resolution DOM path found for right original image: $right"
      fi
      match_args+=(
        --enable-low-resolution-offset-estimation
        --low-resolution-level "$LOW_RESOLUTION_LEVEL"
        --low-resolution-max-mean-reprojection-error-pixels "$LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS"
        --low-resolution-min-retained-match-count "$LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT"
        --low-resolution-max-mean-projected-offset-meters "$LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS"
        --left-low-resolution-dom "${low_resolution_dom_by_original[$left]}"
        --right-low-resolution-dom "${low_resolution_dom_by_original[$right]}"
      )
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
  log "$(pipeline_step_label 3): building pairwise ControlNets -> ${PAIR_NETS_DIR}"
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
  log "$(pipeline_step_label 4): generating cnetmerge shell -> ${MERGE_SCRIPT_PATH}"

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

  log "$(pipeline_step_label 5): post-processing merged ControlNet -> ${POST_MERGE_OUTPUT_PATH:-auto-named by merge_control_measure.py}"

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
  local explicit_num_worker_parallel_cpu=""
  local explicit_use_parallel_cpu=""
  local explicit_invalid_pixel_radius=""
  local explicit_matcher_method=""
  local explicit_enable_low_resolution_offset_estimation=""
  local explicit_low_resolution_level=""
  local explicit_low_resolution_max_mean_reprojection_error_pixels=""
  local explicit_low_resolution_min_retained_match_count=""
  local explicit_low_resolution_max_mean_projected_offset_meters=""

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"
  CNETMERGE_PATH="${CNETMERGE_EXECUTABLE:-cnetmerge}"
  PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
  PAIR_ID_START="$DEFAULT_PAIR_ID_START"
  VALID_PIXEL_PERCENT_THRESHOLD="$DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD"
  INVALID_PIXEL_RADIUS="$DEFAULT_INVALID_PIXEL_RADIUS"
  MATCHER_METHOD="bf"
  ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION="0"
  LOW_RESOLUTION_LEVEL="3"
  LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS="3.0"
  LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT="5"
  LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS="0.0"
  USE_PARALLEL_CPU="1"
  NUM_WORKER_PARALLEL_CPU="8"
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
      --use-parallel-cpu)
        USE_PARALLEL_CPU="1"
        explicit_use_parallel_cpu="1"
        shift
        ;;
      --no-parallel-cpu)
        USE_PARALLEL_CPU="0"
        explicit_use_parallel_cpu="0"
        shift
        ;;
      --num-worker-parallel-cpu)
        [[ $# -ge 2 ]] || die "missing value for --num-worker-parallel-cpu"
        NUM_WORKER_PARALLEL_CPU=$2
        explicit_num_worker_parallel_cpu=$2
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
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        VALID_PIXEL_PERCENT_THRESHOLD=$2
        shift 2
        ;;
      --invalid-pixel-radius)
        [[ $# -ge 2 ]] || die "missing value for --invalid-pixel-radius"
        INVALID_PIXEL_RADIUS=$2
        explicit_invalid_pixel_radius=$2
        shift 2
        ;;
      --matcher-method)
        [[ $# -ge 2 ]] || die "missing value for --matcher-method"
        MATCHER_METHOD=$2
        explicit_matcher_method=$2
        shift 2
        ;;
      --enable-low-resolution-offset-estimation)
        ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION="1"
        explicit_enable_low_resolution_offset_estimation="1"
        shift
        ;;
      --low-resolution-level)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-level"
        LOW_RESOLUTION_LEVEL=$2
        explicit_low_resolution_level=$2
        shift 2
        ;;
      --low-resolution-max-mean-reprojection-error-pixels)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-max-mean-reprojection-error-pixels"
        LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS=$2
        explicit_low_resolution_max_mean_reprojection_error_pixels=$2
        shift 2
        ;;
      --low-resolution-min-retained-match-count)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-min-retained-match-count"
        LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT=$2
        explicit_low_resolution_min_retained_match_count=$2
        shift 2
        ;;
      --low-resolution-max-mean-projected-offset-meters)
        [[ $# -ge 2 ]] || die "missing value for --low-resolution-max-mean-projected-offset-meters"
        LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS=$2
        explicit_low_resolution_max_mean_projected_offset_meters=$2
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
    VALID_PIXEL_PERCENT_THRESHOLD=$(extract_image_match_config_value "$CONFIG_PATH" "valid_pixel_percent_threshold")
  fi
  if [[ -z "$explicit_use_parallel_cpu" ]]; then
    local config_use_parallel_cpu
    config_use_parallel_cpu=$(extract_image_match_config_value "$CONFIG_PATH" "use_parallel_cpu" "image-match-first")
    if [[ -n "$config_use_parallel_cpu" ]]; then
      USE_PARALLEL_CPU="$config_use_parallel_cpu"
    fi
  fi
  if [[ -z "$explicit_num_worker_parallel_cpu" ]]; then
    local config_num_worker_parallel_cpu
    config_num_worker_parallel_cpu=$(extract_image_match_config_value "$CONFIG_PATH" "num_worker_parallel_cpu")
    if [[ -n "$config_num_worker_parallel_cpu" ]]; then
      NUM_WORKER_PARALLEL_CPU="$config_num_worker_parallel_cpu"
    fi
  fi
  if [[ -z "$explicit_invalid_pixel_radius" ]]; then
    local config_invalid_pixel_radius
    config_invalid_pixel_radius=$(extract_image_match_config_value "$CONFIG_PATH" "invalid_pixel_radius")
    if [[ -n "$config_invalid_pixel_radius" ]]; then
      INVALID_PIXEL_RADIUS="$config_invalid_pixel_radius"
    fi
  fi
  if [[ -z "$explicit_matcher_method" ]]; then
    local config_matcher_method
    config_matcher_method=$(extract_image_match_config_value "$CONFIG_PATH" "matcher_method")
    if [[ -n "$config_matcher_method" ]]; then
      MATCHER_METHOD="$config_matcher_method"
    fi
  fi
  if [[ -z "$explicit_enable_low_resolution_offset_estimation" ]]; then
    local config_enable_low_resolution_offset_estimation
    config_enable_low_resolution_offset_estimation=$(extract_image_match_config_value "$CONFIG_PATH" "enable_low_resolution_offset_estimation")
    if [[ -n "$config_enable_low_resolution_offset_estimation" ]]; then
      ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION="$config_enable_low_resolution_offset_estimation"
    fi
  fi
  if [[ -z "$explicit_low_resolution_level" ]]; then
    local config_low_resolution_level
    config_low_resolution_level=$(extract_image_match_config_value "$CONFIG_PATH" "low_resolution_level")
    if [[ -n "$config_low_resolution_level" ]]; then
      LOW_RESOLUTION_LEVEL="$config_low_resolution_level"
    fi
  fi
  if [[ -z "$explicit_low_resolution_max_mean_reprojection_error_pixels" ]]; then
    local config_low_resolution_max_mean_reprojection_error_pixels
    config_low_resolution_max_mean_reprojection_error_pixels=$(extract_image_match_config_value "$CONFIG_PATH" "low_resolution_max_mean_reprojection_error_pixels")
    if [[ -n "$config_low_resolution_max_mean_reprojection_error_pixels" ]]; then
      LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS="$config_low_resolution_max_mean_reprojection_error_pixels"
    fi
  fi
  if [[ -z "$explicit_low_resolution_min_retained_match_count" ]]; then
    local config_low_resolution_min_retained_match_count
    config_low_resolution_min_retained_match_count=$(extract_image_match_config_value "$CONFIG_PATH" "low_resolution_min_retained_match_count")
    if [[ -n "$config_low_resolution_min_retained_match_count" ]]; then
      LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT="$config_low_resolution_min_retained_match_count"
    fi
  fi
  if [[ -z "$explicit_low_resolution_max_mean_projected_offset_meters" ]]; then
    local config_low_resolution_max_mean_projected_offset_meters
    config_low_resolution_max_mean_projected_offset_meters=$(extract_image_match_config_value "$CONFIG_PATH" "low_resolution_max_mean_projected_offset_meters")
    if [[ -n "$config_low_resolution_max_mean_projected_offset_meters" ]]; then
      LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS="$config_low_resolution_max_mean_projected_offset_meters"
    fi
  fi

  LOW_RESOLUTION_DOM_LIST="$WORK_DIR/doms_low_resolution_level${LOW_RESOLUTION_LEVEL}.lis"
  LOW_RESOLUTION_DOM_DIR="$WORK_DIR/low_resolution_doms/level${LOW_RESOLUTION_LEVEL}"
  LOW_RESOLUTION_DOM_REPORT="$REPORTS_DIR/low_resolution_doms_level${LOW_RESOLUTION_LEVEL}.json"

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
    log "CPU parallel worker limit: $NUM_WORKER_PARALLEL_CPU"
  else
    log "CPU parallel tile matching: disabled"
    log "CPU parallel worker limit (forwarded default): $NUM_WORKER_PARALLEL_CPU"
  fi
  if [[ -n "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
    log "Valid pixel percent threshold: $VALID_PIXEL_PERCENT_THRESHOLD"
  else
    log "Valid pixel percent threshold: image_match.py default"
  fi
  log "Invalid pixel radius: $INVALID_PIXEL_RADIUS"
  log "Matcher method: $MATCHER_METHOD"
  if [[ "$ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION" == "1" ]]; then
    log "Low-resolution offset estimation: enabled"
    log "Low-resolution level: $LOW_RESOLUTION_LEVEL"
    log "Low-resolution max mean reprojection error (pixels): $LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS"
    log "Low-resolution minimum retained matches: $LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT"
    log "Low-resolution max mean projected offset (meters): $LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS"
    log "Low-resolution DOM list: $LOW_RESOLUTION_DOM_LIST"
    log "Low-resolution DOM cache dir: $LOW_RESOLUTION_DOM_DIR"
  else
    log "Low-resolution offset estimation: disabled"
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
