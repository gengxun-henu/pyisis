#!/usr/bin/env bash

# End-to-end DOM matching ControlNet pipeline example runner.
#
# Author: Geng Xun
# Created: 2026-05-11
# Updated: 2026-05-11  Geng Xun added top-of-file metadata so example shell entrypoints follow the repository's example-file header convention.
# Updated: 2026-05-16  Geng Xun added deep-match export/import handoff forwarding and export-mode pipeline stop behavior.
# Updated: 2026-05-16  Geng Xun added adaptive-routing flag/profile forwarding for the latest image-match routing profiles.
# Updated: 2026-05-19  Geng Xun aligned ImageMatch config precedence and resolved config-relative deep matcher preset paths before forwarding.
# Updated: 2026-05-20  Geng Xun documented preset-aware adaptive-routing config support for deep matcher preset selection.
# Updated: 2026-05-27  Geng Xun added explicit OpenCV thread-limit forwarding through the example pipeline.
# Updated: 2026-07-23  Geng Xun extracted JSON report summarization from the shell orchestrator.

set -euo pipefail

CALLER_CWD=$(pwd)
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD="0.05"
DEFAULT_INVALID_PIXEL_RADIUS="1"
DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM="1.0"
DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="drop"

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

summarize_image_overlap_report() {
  local report_path=$1
  [[ -s "$report_path" ]] || {
    log "  image-overlap summary json: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/pipeline_report_summary.py" \
    image-overlap "$report_path"
}

summarize_image_match_result() {
  local pair_tag=$1
  local report_path=$2
  [[ -s "$report_path" ]] || {
    log "    image-match result json: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/pipeline_report_summary.py" \
    image-match "$pair_tag" "$report_path"
}

summarize_controlnet_batch_report() {
  local report_path=$1
  [[ -s "$report_path" ]] || {
    log "  pairwise ControlNet batch report: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/pipeline_report_summary.py" \
    controlnet-batch "$report_path"
}

summarize_controlnet_merge_report() {
  local report_path=$1
  [[ -s "$report_path" ]] || {
    log "  merge summary json: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/pipeline_report_summary.py" \
    controlnet-merge "$report_path"
}

summarize_post_merge_report() {
  local report_path=$1
  [[ -s "$report_path" ]] || {
    log "  post-merge summary json: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/pipeline_report_summary.py" \
    post-merge "$report_path"
}


# -----------------------------------------------------------------------------
# One-click parameter profiles for run_pipeline_example.sh.
#
# Conservative (stability first):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --parameter-profile conservative
#
# Balanced (recommended default):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --parameter-profile balanced
#
# Aggressive (recall first):
# bash examples/controlnet_construct/run_pipeline_example.sh \
#   --work-dir work \
#   --parameter-profile aggressive
# -----------------------------------------------------------------------------


usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_pipeline_example.sh [options]

Run the DOM matching ControlNet example pipeline end to end:
  1. image_overlap.py
  2. examples/image_match/image_match.py (for every pair in images_overlap.lis)
  3. controlnet_stereopair.py from-dom-batch
  4. controlnet_merge.py + execute the generated merge_all_controlnets.sh by default
  5. optionally run merge_control_measure.py as a post-processing step

Default behavior:
  - Terminal output stays compact: per-step JSON summaries are written to files under <work-dir>/reports or <work-dir>/match_results instead of being printed inline.
  - CPU tile parallelism is enabled unless --no-parallel-cpu is provided.
  - examples/image_match/image_match.py writes pre-RANSAC match visualizations to <work-dir>/match_viz.
  - from-dom-batch writes post-RANSAC match visualizations to <work-dir>/match_viz_post_ransac.

Parameter groups:
  inputs: work/config/list paths and the Python executable
    common flags: --work-dir, --original-list, --dom-list, --config
  pipeline: high-level pipeline mode and deep-match manifest handoff
    common flags: --deep-match-mode, --skip-final-merge, --parameter-profile
  matching: matcher selection, presets, and deep matcher config
    common flags: --matcher-method, --match-preset-path, --deep-match-config-path
  tile: tile size, overlap, validity filtering, and invalid-pixel suppression
    common flags: --valid-pixel-percent-threshold, --invalid-pixel-radius
  low_resolution: coarse low-resolution offset estimation and gates
    common flags: --enable-low-resolution-offset-estimation, --low-resolution-level
  adaptive_routing: pair-level adaptive matcher routing controls
    common flags: --adaptive-routing, --adaptive-routing-profile
  execution: CPU/GPU execution controls
    common flags: --use-parallel-cpu, --no-parallel-cpu, --num-worker-parallel-cpu, --opencv-num-threads
  visualization: pre/post-RANSAC preview behavior and memory profile
    common flags: --visualization-mode, --memory-profile, --preview-cache-source
  controlnet: pair IDs, cnetmerge, final network paths, and merge behavior
    common flags: --merged-net, --merge-script, --network-id, --cnetmerge
  reporting: timing, validation, and report output controls
    common flags: --timing-json, --validate-parameters-only, --strict-parameter-validation

For the full catalog with allowed values, defaults, and config paths:
  bash examples/controlnet_construct/run_pipeline_example.sh --print-parameter-groups

Options:
  --work-dir PATH                 Root working directory. Default: work
  --original-list PATH            original_images.lis path. Default: <work-dir>/original_images.lis
  --dom-list PATH                 DOM list path. Default: <work-dir>/doms_scaled.lis if present, else <work-dir>/doms.lis
  --config PATH                   ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
                                  Its ImageMatch section is forwarded to examples/image_match/image_match.py as default matching parameters.
  --python PATH                   Python interpreter to use. Default: $PYTHON_EXECUTABLE or python
  --print-parameter-groups        Print the cataloged parameter groups for this wrapper and exit
  --validate-parameters-only      Validate resolved parameters and exit before running pipeline steps
  --strict-parameter-validation   Promote parameter validation warnings to errors
  --parameter-profile NAME        Apply an opt-in matching parameter profile before config, preset, and CLI values.
                                  Supported values: conservative, balanced, aggressive.
  --use-parallel-cpu              Forward explicit CPU tile parallelism enable flag to examples/image_match/image_match.py (default behavior)
  --no-parallel-cpu               Disable CPU tile parallelism in examples/image_match/image_match.py and force serial tile matching
  --num-worker-parallel-cpu N     Maximum worker-process count forwarded to examples/image_match/image_match.py when CPU parallelism is enabled.
                                  Default: 8. If omitted, this script falls back to config JSON field
                                  ImageMatch.num_worker_parallel_cpu when present. Valid range: 1~4096.
  --opencv-num-threads N          Optional OpenCV internal CPU thread limit for SIFT/FLANN work.
                                  If omitted, this script falls back to config JSON field
                                  ImageMatch.opencv_num_threads when present. Use 1 with multiple CPU
                                  workers to avoid OpenCV/process-pool oversubscription.
  --pair-id-prefix PREFIX         Batch pair-id prefix. Default: S
  --pair-id-start N               Batch pair-id starting index. Default: 1
  --valid-pixel-percent-threshold VALUE
                                 Forwarded to examples/image_match/image_match.py. If omitted, this script
                                 falls back to config JSON field ImageMatch.valid_pixel_percent_threshold
                                 when present; otherwise defaults to 0.05.
  --invalid-pixel-radius N        Forwarded to examples/image_match/image_match.py to suppress feature detection near
                                 invalid pixels and image borders. If omitted, this script falls
                                 back to config JSON field ImageMatch.invalid_pixel_radius when present;
                                 otherwise examples/image_match/image_match.py keeps its own default.
  --pre-ransac-max-ground-distance-km VALUE
                                  Forwarded to image_match.py and controlnet_stereopair.py from-dom-batch as the
                                  maximum paired ground distance before RANSAC. Use 0 to disable. If omitted,
                                  this script falls back to ImageMatch.pre_ransac_max_ground_distance_km when present;
                                  otherwise defaults to 1.0.
  --pre-ransac-ground-lookup-failure-policy VALUE
                                  Forwarded to image_match.py and controlnet_stereopair.py from-dom-batch as the
                                  ground lookup failure policy for the pre-RANSAC ground-distance filter: drop or keep.
                                  If omitted, this script falls back to ImageMatch.pre_ransac_ground_lookup_failure_policy
                                  when present; otherwise defaults to drop.
  --matcher-method NAME           Forwarded to examples/image_match/image_match.py to select matcher backend.
                                 Supported values: bf, flann, superglue, lightglue, loftr.
                                 If omitted, this script falls back to
                                 config JSON field ImageMatch.matcher_method when present; otherwise
                                 examples/image_match/image_match.py keeps its own default.
  --match-preset-path PATH        Forwarded to examples/image_match/image_match.py to select a match preset.
                                  If omitted, this script falls back to config JSON field
                                  ImageMatch.match_preset_path when present. Cannot be combined with
                                  --matcher-method or --deep-match-config-path.
  --deep-match-config-path PATH   Path to deep matcher preset JSON config.
                                  Required when --matcher-method is superglue, lightglue, or loftr.
                                  Default: (read from config JSON). Relative config values are resolved first
                                  against the config file directory, then against the repo root.
  --adaptive-routing              Enable image_match.py adaptive routing. If omitted, this script falls back to
                                  config JSON field ImageMatch.enable_adaptive_routing when present; otherwise disabled.
  --no-adaptive-routing           Disable image_match.py adaptive routing even if config enables it.
  --adaptive-routing-profile NAME Forwarded to image_match.py as the named adaptive-routing quality profile.
                                   Supported values: balanced, strict, relaxed, fast. If omitted, this script falls back
                                   to config JSON field ImageMatch.adaptive_routing_profile when present; otherwise balanced.
                                   Preset-aware adaptive routing can additionally read ImageMatch.adaptive_routing_deep_presets
                                   from the config JSON so routed LightGlue/LoFTR passes select concrete preset files.
  --dom-source-metadata-csv PATH  CSV mapping DOM cube paths to the source/original camera cubes used to generate them.
                                  Forwarded to image_match.py for tile-level physical illumination routing.
  --deep-match-mode MODE          Deep-match execution mode forwarded to image_match.py: direct, export, or import.
                                  Default: direct. Export mode stops after Step 2 and writes manifest workspaces;
                                  import mode consumes completed per-pair manifests before continuing ControlNet steps.
  --deep-match-temp-root-dir PATH Root directory for exported deep-match workspaces.
                                  Default: <work-dir>/deep_match_workspaces when --deep-match-mode export.
  --deep-match-manifest-dir PATH  Directory containing per-pair manifest workspaces for import mode.
                                  Each pair expects <PATH>/<pair_tag>/tasks.json.
  --deep-match-manifest-summary PATH
                                  JSON summary of per-pair manifest paths. Default: <work-dir>/reports/deep_match_manifests.json
  --enable-low-resolution-offset-estimation
                                 Forwarded to examples/image_match/image_match.py to enable low-resolution DOM coarse
                                 registration before full-resolution overlap preparation.
  --low-resolution-level N        Forwarded to examples/image_match/image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_level when present;
                                 otherwise examples/image_match/image_match.py keeps its own default.
  --low-resolution-max-mean-reprojection-error-pixels VALUE
                                 Forwarded to examples/image_match/image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_max_mean_reprojection_error_pixels
                                 when present; otherwise examples/image_match/image_match.py keeps its own default.
  --low-resolution-min-retained-match-count N
                                 Forwarded to examples/image_match/image_match.py. If omitted, this script falls back to
                                 config JSON field ImageMatch.low_resolution_min_retained_match_count
                                 when present; otherwise examples/image_match/image_match.py keeps its own default.
  --low-resolution-max-mean-projected-offset-meters VALUE
                                  Forwarded to examples/image_match/image_match.py. Unit: meters. If omitted, this script falls back to
                                  config JSON field ImageMatch.low_resolution_max_mean_projected_offset_meters
                                  when present; otherwise examples/image_match/image_match.py keeps its own default.
  --visualization-mode VALUE      Forwarded to controlnet_stereopair.py from-dom-batch for post-RANSAC previews.
                                  If omitted, this script falls back to config JSON field ImageMatch.visualization_mode
                                  when present; otherwise defaults to full.
  --memory-profile VALUE          Forwarded to controlnet_stereopair.py from-dom-batch. If omitted, this script falls
                                  back to config JSON field ImageMatch.memory_profile when present; otherwise defaults
                                  to balanced.
  --visualization-target-long-edge N
                                  Forwarded to controlnet_stereopair.py from-dom-batch when set. If omitted, this script
                                  falls back to config JSON field ImageMatch.visualization_target_long_edge when present.
  --preview-crop-margin-pixels N  Forwarded to controlnet_stereopair.py from-dom-batch. If omitted, this script falls
                                  back to config JSON field ImageMatch.preview_crop_margin_pixels when present; otherwise
                                  defaults to 128.
  --preview-cache-source VALUE    Forwarded to controlnet_stereopair.py from-dom-batch. If omitted, this script falls
                                  back to config JSON field ImageMatch.preview_cache_source when present; otherwise
                                  defaults to auto.
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
  PARAMETER_CATALOG_PYTHON_EXECUTABLE
                                  Python interpreter used for parameter catalog validation. Default: python
  CNETMERGE_EXECUTABLE            cnetmerge executable path written into the generated merge shell

Examples:
  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work

  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work \
    --skip-final-merge

  bash examples/controlnet_construct/run_pipeline_example.sh \
    --work-dir work \
    --parameter-profile balanced \
    --validate-parameters-only

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

load_run_pipeline_config_values() {
  local config_path=$1
  "$PYTHON_EXECUTABLE" - "$config_path" "$REPO_ROOT" <<'PY'
import json
import shlex
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
sys.path.insert(0, str(repo_root / "examples"))

from image_match.image_match import format_image_match_default_for_shell, load_image_match_defaults_from_config

config = json.loads(config_path.read_text(encoding="utf-8"))
network_id = config.get("NetworkId") or config.get("network_id") or ""
reporting = config.get("Reporting") or config.get("reporting") or {}
strict_parameter_validation = reporting.get("strict_parameter_validation")

print(f"config_network_id={shlex.quote(str(network_id))}")
if strict_parameter_validation is None or strict_parameter_validation == "":
    print("config_strict_parameter_validation=''")
elif isinstance(strict_parameter_validation, bool):
    print(f"config_strict_parameter_validation={'1' if strict_parameter_validation else '0'}")
else:
    print(f"config_strict_parameter_validation={shlex.quote(str(strict_parameter_validation))}")

defaults = load_image_match_defaults_from_config(config_path)
field_map = {
    "config_match_preset_path": "match_preset_path",
    "config_valid_pixel_percent_threshold": "valid_pixel_percent_threshold",
    "config_use_parallel_cpu": "use_parallel_cpu",
    "config_num_worker_parallel_cpu": "num_worker_parallel_cpu",
    "config_opencv_num_threads": "opencv_num_threads",
    "config_invalid_pixel_radius": "invalid_pixel_radius",
    "config_pre_ransac_max_ground_distance_km": "pre_ransac_max_ground_distance_km",
    "config_pre_ransac_ground_lookup_failure_policy": "pre_ransac_ground_lookup_failure_policy",
    "config_matcher_method": "matcher_method",
    "config_enable_adaptive_routing": "enable_adaptive_routing",
    "config_adaptive_routing_profile": "adaptive_routing_profile",
    "config_deep_matcher_config_path": "deep_match_config_path",
    "config_enable_low_resolution_offset_estimation": "enable_low_resolution_offset_estimation",
    "config_low_resolution_level": "low_resolution_level",
    "config_low_resolution_max_mean_reprojection_error_pixels": "low_resolution_max_mean_reprojection_error_pixels",
    "config_low_resolution_min_retained_match_count": "low_resolution_min_retained_match_count",
    "config_low_resolution_max_mean_projected_offset_meters": "low_resolution_max_mean_projected_offset_meters",
    "config_visualization_mode": "visualization_mode",
    "config_memory_profile": "memory_profile",
    "config_visualization_target_long_edge": "visualization_target_long_edge",
    "config_preview_crop_margin_pixels": "preview_crop_margin_pixels",
    "config_preview_cache_source": "preview_cache_source",
}
for shell_name, config_name in field_map.items():
    value = ""
    if config_name in defaults:
        value = format_image_match_default_for_shell(defaults[config_name])
    print(f"{shell_name}={shlex.quote(value)}")
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

resolve_parameter_profile_shell_assignments() {
  local profile_name=$1
  "$CATALOG_PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/parameter_profiles.py" \
    "$profile_name" \
    --shell-assignments
}

apply_match_preset_path() {
  local preset_path=$1
  local assignments
  assignments=$(resolve_match_preset_shell_assignments "$preset_path")
  eval "$assignments"
}

apply_profile_value_if_unset() {
  local target_name=$1
  local profile_value=$2
  shift 2
  local marker_name
  for marker_name in "$@"; do
    if [[ -n "${!marker_name:-}" ]]; then
      return 0
    fi
  done
  printf -v "$target_name" '%s' "$profile_value"
}

apply_parameter_profile_defaults() {
  [[ -n "$parameter_profile" ]] || return 0

  local profile_assignments
  profile_assignments=$(resolve_parameter_profile_shell_assignments "$parameter_profile") || return $?
  eval "$profile_assignments"

  apply_profile_value_if_unset VALID_PIXEL_PERCENT_THRESHOLD "$PROFILE_VALID_PIXEL_PERCENT_THRESHOLD" explicit_valid_pixel_percent_threshold config_valid_pixel_percent_threshold
  apply_profile_value_if_unset INVALID_PIXEL_RADIUS "$PROFILE_INVALID_PIXEL_RADIUS" explicit_invalid_pixel_radius config_invalid_pixel_radius
  apply_profile_value_if_unset MATCHER_METHOD "$PROFILE_MATCHER_METHOD" explicit_matcher_method config_matcher_method match_preset_path
  apply_profile_value_if_unset ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION "$PROFILE_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION" explicit_enable_low_resolution_offset_estimation config_enable_low_resolution_offset_estimation
  apply_profile_value_if_unset LOW_RESOLUTION_LEVEL "$PROFILE_LOW_RESOLUTION_LEVEL" explicit_low_resolution_level config_low_resolution_level
  apply_profile_value_if_unset LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS "$PROFILE_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS" explicit_low_resolution_max_mean_reprojection_error_pixels config_low_resolution_max_mean_reprojection_error_pixels
  apply_profile_value_if_unset LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT "$PROFILE_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT" explicit_low_resolution_min_retained_match_count config_low_resolution_min_retained_match_count
  apply_profile_value_if_unset LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS "$PROFILE_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS" explicit_low_resolution_max_mean_projected_offset_meters config_low_resolution_max_mean_projected_offset_meters
  apply_profile_value_if_unset NUM_WORKER_PARALLEL_CPU "$PROFILE_NUM_WORKER_PARALLEL_CPU" explicit_num_worker_parallel_cpu config_num_worker_parallel_cpu
}

print_parameter_groups() {
  "$CATALOG_PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/print_parameter_catalog.py" \
    --entrypoint run_pipeline_example \
    --format text
}

validate_controlnet_parameters() {
  "$CATALOG_PYTHON_EXECUTABLE" - <<'PY'
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(repo_root / "examples"))
from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME, parameters_for_entrypoint
from controlnet_construct.parameter_validation import validate_parameters

supported_names = {parameter.name for parameter in parameters_for_entrypoint("run_pipeline_example")}
spec_by_name = {name: PARAMETER_BY_NAME[name] for name in supported_names}


def env(name: str) -> str:
    return os.environ.get(name, "")


def is_present(value: object) -> bool:
    return value is not None and value != "" and value != "null"


def coerce_value(name: str, value: object) -> object:
    spec = spec_by_name[name]
    if not isinstance(value, str):
        return value
    if spec.value_type == "bool":
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return value
    if spec.value_type == "int":
        try:
            return int(value)
        except ValueError:
            return value
    if spec.value_type == "float":
        try:
            return float(value)
        except ValueError:
            return value
    return value


def add_value(target: dict[str, object], name: str, value: object) -> None:
    if name in supported_names and is_present(value):
        target[name] = coerce_value(name, value)


def print_messages(prefix: str, messages: tuple[object, ...]) -> None:
    for message in messages:
        print(f"{prefix}: {message.field}: {message.message}", file=sys.stderr)


cli_values: dict[str, object] = {}
profile_values: dict[str, object] = {}
config_values: dict[str, object] = {}
preset_values: dict[str, object] = {}

if env("print_parameter_groups") == "1":
    add_value(cli_values, "print_parameter_groups", True)
if env("validate_parameters_only") == "1":
    add_value(cli_values, "validate_parameters_only", True)
if env("explicit_strict_parameter_validation") == "1":
    add_value(cli_values, "strict_parameter_validation", True)
if is_present(env("parameter_profile")):
    add_value(cli_values, "parameter_profile", env("parameter_profile"))

cli_sources = {
    "num_worker_parallel_cpu": ("explicit_num_worker_parallel_cpu", "NUM_WORKER_PARALLEL_CPU"),
    "opencv_num_threads": ("explicit_opencv_num_threads", "OPENCV_NUM_THREADS"),
    "use_parallel_cpu": ("explicit_use_parallel_cpu", "USE_PARALLEL_CPU"),
    "pair_id_start": ("explicit_pair_id_start", "PAIR_ID_START"),
    "valid_pixel_percent_threshold": (
        "explicit_valid_pixel_percent_threshold",
        "VALID_PIXEL_PERCENT_THRESHOLD",
    ),
    "invalid_pixel_radius": ("explicit_invalid_pixel_radius", "INVALID_PIXEL_RADIUS"),
    "pre_ransac_max_ground_distance_km": (
        "explicit_pre_ransac_max_ground_distance_km",
        "PRE_RANSAC_MAX_GROUND_DISTANCE_KM",
    ),
    "pre_ransac_ground_lookup_failure_policy": (
        "explicit_pre_ransac_ground_lookup_failure_policy",
        "PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY",
    ),
    "match_preset_path": ("explicit_match_preset_path", "match_preset_path"),
    "matcher_method": ("explicit_matcher_method", "MATCHER_METHOD"),
    "deep_match_config_path": ("explicit_deep_matcher_config_path", "DEEP_MATCHER_CONFIG_PATH"),
    "deep_match_mode": ("explicit_deep_match_mode", "DEEP_MATCH_MODE"),
    "deep_match_temp_root_dir": ("explicit_deep_match_temp_root_dir", "DEEP_MATCH_TEMP_ROOT_DIR"),
    "deep_match_manifest_dir": ("explicit_deep_match_manifest_dir", "DEEP_MATCH_MANIFEST_DIR"),
    "deep_match_manifest_summary": ("explicit_deep_match_manifest_summary", "DEEP_MATCH_MANIFEST_SUMMARY"),
    "enable_adaptive_routing": ("explicit_adaptive_routing", "ADAPTIVE_ROUTING"),
    "adaptive_routing_profile": ("explicit_adaptive_routing_profile", "ADAPTIVE_ROUTING_PROFILE"),
    "enable_low_resolution_offset_estimation": (
        "explicit_enable_low_resolution_offset_estimation",
        "ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION",
    ),
    "low_resolution_level": ("explicit_low_resolution_level", "LOW_RESOLUTION_LEVEL"),
    "low_resolution_max_mean_reprojection_error_pixels": (
        "explicit_low_resolution_max_mean_reprojection_error_pixels",
        "LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS",
    ),
    "low_resolution_min_retained_match_count": (
        "explicit_low_resolution_min_retained_match_count",
        "LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT",
    ),
    "low_resolution_max_mean_projected_offset_meters": (
        "explicit_low_resolution_max_mean_projected_offset_meters",
        "LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS",
    ),
    "visualization_mode": ("explicit_visualization_mode", "VISUALIZATION_MODE"),
    "memory_profile": ("explicit_memory_profile", "MEMORY_PROFILE"),
    "visualization_target_long_edge": ("explicit_visualization_target_long_edge", "VISUALIZATION_TARGET_LONG_EDGE"),
    "preview_crop_margin_pixels": ("explicit_preview_crop_margin_pixels", "PREVIEW_CROP_MARGIN_PIXELS"),
    "preview_cache_source": ("explicit_preview_cache_source", "PREVIEW_CACHE_SOURCE"),
    "skip_final_merge": ("explicit_skip_final_merge", "SKIP_FINAL_MERGE"),
    "post_merge_control_measure": ("explicit_post_merge_control_measure", "POST_MERGE_CONTROL_MEASURE"),
    "post_merge_output": ("explicit_post_merge_output", "POST_MERGE_OUTPUT_PATH"),
    "post_merge_decimals": ("explicit_post_merge_decimals", "POST_MERGE_DECIMALS"),
}
for parameter_name, (marker_name, value_name) in cli_sources.items():
    if is_present(env(marker_name)):
        add_value(cli_values, parameter_name, env(value_name))

profile_sources = {
    "valid_pixel_percent_threshold": "PROFILE_VALID_PIXEL_PERCENT_THRESHOLD",
    "invalid_pixel_radius": "PROFILE_INVALID_PIXEL_RADIUS",
    "matcher_method": "PROFILE_MATCHER_METHOD",
    "enable_low_resolution_offset_estimation": "PROFILE_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION",
    "low_resolution_level": "PROFILE_LOW_RESOLUTION_LEVEL",
    "low_resolution_max_mean_reprojection_error_pixels": "PROFILE_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS",
    "low_resolution_min_retained_match_count": "PROFILE_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT",
    "low_resolution_max_mean_projected_offset_meters": "PROFILE_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS",
    "num_worker_parallel_cpu": "PROFILE_NUM_WORKER_PARALLEL_CPU",
}
for parameter_name, value_name in profile_sources.items():
    add_value(profile_values, parameter_name, env(value_name))

config_sources = {
    "match_preset_path": "config_match_preset_path",
    "valid_pixel_percent_threshold": "config_valid_pixel_percent_threshold",
    "invalid_pixel_radius": "config_invalid_pixel_radius",
    "pre_ransac_max_ground_distance_km": "config_pre_ransac_max_ground_distance_km",
    "pre_ransac_ground_lookup_failure_policy": "config_pre_ransac_ground_lookup_failure_policy",
    "num_worker_parallel_cpu": "config_num_worker_parallel_cpu",
    "opencv_num_threads": "config_opencv_num_threads",
    "use_parallel_cpu": "config_use_parallel_cpu",
    "matcher_method": "config_matcher_method",
    "deep_match_config_path": "config_deep_matcher_config_path",
    "enable_adaptive_routing": "config_enable_adaptive_routing",
    "adaptive_routing_profile": "config_adaptive_routing_profile",
    "enable_low_resolution_offset_estimation": "config_enable_low_resolution_offset_estimation",
    "low_resolution_level": "config_low_resolution_level",
    "low_resolution_max_mean_reprojection_error_pixels": "config_low_resolution_max_mean_reprojection_error_pixels",
    "low_resolution_min_retained_match_count": "config_low_resolution_min_retained_match_count",
    "low_resolution_max_mean_projected_offset_meters": "config_low_resolution_max_mean_projected_offset_meters",
    "visualization_mode": "config_visualization_mode",
    "memory_profile": "config_memory_profile",
    "visualization_target_long_edge": "config_visualization_target_long_edge",
    "preview_crop_margin_pixels": "config_preview_crop_margin_pixels",
    "preview_cache_source": "config_preview_cache_source",
    "strict_parameter_validation": "config_strict_parameter_validation",
}
for parameter_name, value_name in config_sources.items():
    add_value(config_values, parameter_name, env(value_name))

preset_sources = {
    "match_preset_path": "preset_match_preset_path",
    "matcher_method": "preset_matcher_method",
    "deep_match_config_path": "preset_deep_match_config_path",
}
for parameter_name, value_name in preset_sources.items():
    add_value(preset_values, parameter_name, env(value_name))

try:
    result = validate_parameters(
        "run_pipeline_example",
        cli_values=cli_values,
        profile_values=profile_values,
        config_values=config_values,
        preset_values=preset_values,
    )
except ValueError as exc:
    print(f"error: validate-json: {exc}", file=sys.stderr)
    raise SystemExit(2)

print_messages("warning", result.warnings)
if result.errors:
    print_messages("error", result.errors)
    raise SystemExit(2)

print(result.to_shell_assignments())
PY
}

print_parameter_validation_summary() {
  printf 'WORK_DIR=%q\n' "$WORK_DIR"
  printf 'ORIGINAL_LIST=%q\n' "$ORIGINAL_LIST"
  printf 'DOM_LIST=%q\n' "$DOM_LIST"
  printf 'CONFIG=%q\n' "$CONFIG_PATH"
  printf 'NETWORK_ID=%q\n' "$NETWORK_ID"
  printf 'PARAMETER_PROFILE=%q\n' "$parameter_profile"
  printf 'MATCHER_METHOD=%q\n' "$MATCHER_METHOD"
  printf 'NUM_WORKER_PARALLEL_CPU=%q\n' "$NUM_WORKER_PARALLEL_CPU"
  printf 'OPENCV_NUM_THREADS=%q\n' "$OPENCV_NUM_THREADS"
  printf 'VALID_PIXEL_PERCENT_THRESHOLD=%q\n' "$VALID_PIXEL_PERCENT_THRESHOLD"
  printf 'INVALID_PIXEL_RADIUS=%q\n' "$INVALID_PIXEL_RADIUS"
  printf 'PRE_RANSAC_MAX_GROUND_DISTANCE_KM=%q\n' "$PRE_RANSAC_MAX_GROUND_DISTANCE_KM"
  printf 'PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY=%q\n' "$PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY"
  printf 'ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION=%q\n' "$ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION"
  printf 'LOW_RESOLUTION_LEVEL=%q\n' "$LOW_RESOLUTION_LEVEL"
  printf 'LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS=%q\n' "$LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS"
  printf 'LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT=%q\n' "$LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT"
  printf 'LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS=%q\n' "$LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS"
  printf 'VISUALIZATION_MODE=%q\n' "$VISUALIZATION_MODE"
  printf 'PREVIEW_CROP_MARGIN_PIXELS=%q\n' "$PREVIEW_CROP_MARGIN_PIXELS"
  printf 'STRICT_PARAMETER_VALIDATION=%q\n' "$strict_parameter_validation"
}

run_step_1_image_overlap() {
  log "$(pipeline_step_label 1): computing overlap pairs -> ${IMAGES_OVERLAP_LIST}"
  bash -lc '"$@" >/dev/null' bash \
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" \
    "$IMAGES_OVERLAP_LIST" \
    --report-json "$IMAGE_OVERLAP_REPORT_JSON_PATH"
  log "  image overlap summary json: $IMAGE_OVERLAP_REPORT_JSON_PATH"
  log "  $(summarize_image_overlap_report "$IMAGE_OVERLAP_REPORT_JSON_PATH")"
}

initialize_deep_match_manifest_summary() {
  local summary_path=$1
  "$PYTHON_EXECUTABLE" - "$summary_path" "$DEEP_MATCH_MODE" "$DEEP_MATCH_TEMP_ROOT_DIR" "$DEEP_MATCH_MANIFEST_DIR" <<'PY'
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
  local result_path=$3
  "$PYTHON_EXECUTABLE" - "$summary_path" "$pair_tag" "$result_path" "$DEEP_MATCH_MODE" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
pair_tag = sys.argv[2]
result_path = Path(sys.argv[3])
mode = sys.argv[4]

payload = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {"pairs": []}
entry = {"pair_tag": pair_tag, "result_path": str(result_path), "deep_match_mode": mode}
if result_path.exists():
    result = json.loads(result_path.read_text(encoding="utf-8"))
    section = result.get("deep_match_export") if mode == "export" else result.get("deep_match_import")
    entry["status"] = result.get("status")
    entry["point_count"] = result.get("point_count")
    if isinstance(section, dict):
        for key in ("manifest_path", "workspace_root", "results_dir", "logs_dir", "pair_id", "exported_task_count", "imported_task_count", "missing_result_count", "failed_task_count"):
            if key in section:
                entry[key] = section[key]
else:
    entry["status"] = "result_missing"

payload.setdefault("pairs", []).append(entry)
summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

resolve_deep_match_manifest_for_pair() {
  local pair_tag=$1
  local left_dom=$2
  local right_dom=$3
  "$PYTHON_EXECUTABLE" - "$pair_tag" "$left_dom" "$right_dom" "$DEEP_MATCH_MANIFEST_SUMMARY" "$DEEP_MATCH_MANIFEST_DIR" <<'PY'
import json
import sys
from pathlib import Path

pair_tag = sys.argv[1]
left_dom = str(Path(sys.argv[2]).expanduser().resolve())
right_dom = str(Path(sys.argv[3]).expanduser().resolve())
summary_path = Path(sys.argv[4])
manifest_dir = Path(sys.argv[5]).expanduser().resolve()

if summary_path.exists():
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    for entry in payload.get("pairs", []):
        if entry.get("pair_tag") == pair_tag and entry.get("manifest_path"):
            print(entry["manifest_path"])
            raise SystemExit(0)

for manifest_path in sorted(manifest_dir.glob("*/tasks.json")):
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    manifest_left = str(Path(manifest.get("left_dom_path", "")).expanduser().resolve())
    manifest_right = str(Path(manifest.get("right_dom_path", "")).expanduser().resolve())
    if manifest_left == left_dom and manifest_right == right_dom:
        print(manifest_path)
        raise SystemExit(0)

print(str(manifest_dir / pair_tag / "tasks.json"))
PY
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
    local match_result_path="$MATCH_RESULTS_DIR/${pair_tag}.json"
    local match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/image_match/image_match.py"
      --config "$CONFIG_PATH"
      "${dom_by_original[$left]}"
      "${dom_by_original[$right]}"
      "$DOM_KEYS_DIR/${pair_tag}_A.key"
      "$DOM_KEYS_DIR/${pair_tag}_B.key"
      --omit-tile-details
      --metadata-output "$MATCH_METADATA_DIR/${pair_tag}.json"
      --result-output "$match_result_path"
      --match-visualization-output-dir "$PRE_RANSAC_MATCH_VIZ_DIR"
    )

    if [[ -n "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
      match_args+=(--valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD")
    fi
    match_args+=(--invalid-pixel-radius "$INVALID_PIXEL_RADIUS")
    match_args+=(--pre-ransac-max-ground-distance-km "$PRE_RANSAC_MAX_GROUND_DISTANCE_KM")
    match_args+=(--pre-ransac-ground-lookup-failure-policy "$PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY")
    if [[ -n "$match_preset_path" ]]; then
      match_args+=(--match-preset-path "$match_preset_path")
    fi
    if [[ -z "$match_preset_path" ]]; then
      match_args+=(--matcher-method "$MATCHER_METHOD")
    fi
    if [[ -z "$match_preset_path" && -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
      match_args+=(--deep-match-config-path "$DEEP_MATCHER_CONFIG_PATH")
    fi
    if [[ "$ADAPTIVE_ROUTING" == "1" ]]; then
      match_args+=(--adaptive-routing)
    else
      match_args+=(--no-adaptive-routing)
    fi
    match_args+=(--adaptive-routing-profile "$ADAPTIVE_ROUTING_PROFILE")
    if [[ -n "$DOM_SOURCE_METADATA_CSV" ]]; then
      match_args+=(--dom-source-metadata-csv "$DOM_SOURCE_METADATA_CSV")
    fi
    if [[ "$USE_PARALLEL_CPU" == "1" ]]; then
      match_args+=(--use-parallel-cpu)
    else
      match_args+=(--no-parallel-cpu)
    fi
    match_args+=(--num-worker-parallel-cpu "$NUM_WORKER_PARALLEL_CPU")
    if [[ -n "$OPENCV_NUM_THREADS" ]]; then
      match_args+=(--opencv-num-threads "$OPENCV_NUM_THREADS")
    fi
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
    if [[ "$DEEP_MATCH_MODE" != "direct" ]]; then
      match_args+=(--deep-match-mode "$DEEP_MATCH_MODE")
      if [[ "$DEEP_MATCH_MODE" == "export" ]]; then
        match_args+=(--deep-match-temp-root-dir "$DEEP_MATCH_TEMP_ROOT_DIR")
      elif [[ "$DEEP_MATCH_MODE" == "import" ]]; then
        local deep_match_manifest_path
        deep_match_manifest_path=$(resolve_deep_match_manifest_for_pair "$pair_tag" "${dom_by_original[$left]}" "${dom_by_original[$right]}")
        match_args+=(--deep-match-manifest "$deep_match_manifest_path")
      fi
    fi

    run_timed_command "pair_matches" "image_match:${pair_tag}" bash -lc '"$@" >/dev/null' bash "${match_args[@]}"
    local match_status=$?
    if [[ "$match_status" -ne 0 ]]; then
      return "$match_status"
    fi
    log "    image-match result json: $match_result_path"
    log "    $(summarize_image_match_result "$pair_tag" "$match_result_path")"
    if [[ "$DEEP_MATCH_MODE" != "direct" ]]; then
      append_deep_match_manifest_summary "$DEEP_MATCH_MANIFEST_SUMMARY" "$pair_tag" "$match_result_path"
    fi

    pair_count=$((pair_count + 1))
  done < "$IMAGES_OVERLAP_LIST"

  if [[ "$pair_count" -eq 0 ]]; then
    warn "images_overlap.lis did not contain any overlap pairs; downstream steps may fail or produce empty outputs"
  fi
}

run_step_3_pairwise_controlnets() {
  log "$(pipeline_step_label 3): building pairwise ControlNets -> ${PAIR_NETS_DIR}"
  local controlnet_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-dom-batch
    "$IMAGES_OVERLAP_LIST"
    "$ORIGINAL_LIST"
    "$DOM_LIST"
    "$DOM_KEYS_DIR"
    "$CONFIG_PATH"
    "$PAIR_NETS_DIR"
    --report-dir "$REPORTS_DIR"
    --pair-id-prefix "$PAIR_ID_PREFIX"
    --pair-id-start "$PAIR_ID_START"
    --write-match-visualization
    --match-visualization-output-dir "$POST_RANSAC_MATCH_VIZ_DIR"
    --visualization-mode "$VISUALIZATION_MODE"
    --memory-profile "$MEMORY_PROFILE"
    --preview-crop-margin-pixels "$PREVIEW_CROP_MARGIN_PIXELS"
    --preview-cache-source "$PREVIEW_CACHE_SOURCE"
    --pre-ransac-max-ground-distance-km "$PRE_RANSAC_MAX_GROUND_DISTANCE_KM"
    --pre-ransac-ground-lookup-failure-policy "$PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY"
    --pre-ransac-match-metadata-dir "$MATCH_METADATA_DIR"
  )
  if [[ -n "$VISUALIZATION_TARGET_LONG_EDGE" ]]; then
    controlnet_args+=(--visualization-target-long-edge "$VISUALIZATION_TARGET_LONG_EDGE")
  fi
  bash -lc '"$@" >/dev/null' bash "${controlnet_args[@]}"
  log "  pairwise ControlNet batch report: $CONTROLNET_BATCH_REPORT_PATH"
  log "  $(summarize_controlnet_batch_report "$CONTROLNET_BATCH_REPORT_PATH")"
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
    --report-json "$MERGE_REPORT_JSON_PATH"
    --cnetmerge "$CNETMERGE_PATH"
  )

  if [[ -n "$PAIR_LIST_PATH" ]]; then
    merge_args+=(--pair-list "$PAIR_LIST_PATH")
  fi

  bash -lc '"$@" >/dev/null' bash "${merge_args[@]}"
  log "  merge summary json: $MERGE_REPORT_JSON_PATH"
  log "  $(summarize_controlnet_merge_report "$MERGE_REPORT_JSON_PATH")"

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

  post_merge_args+=(--decimals "$POST_MERGE_DECIMALS" --report-json "$POST_MERGE_REPORT_JSON_PATH")

  bash -lc '"$@" >/dev/null' bash "${post_merge_args[@]}"
  log "  post-merge summary json: $POST_MERGE_REPORT_JSON_PATH"
  log "  $(summarize_post_merge_report "$POST_MERGE_REPORT_JSON_PATH")"
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
  local print_parameter_groups="0"
  local validate_parameters_only="0"
  local strict_parameter_validation="0"
  local explicit_strict_parameter_validation="0"
  local parameter_profile=""
  local explicit_valid_pixel_percent_threshold=""
  local explicit_num_worker_parallel_cpu=""
  local explicit_opencv_num_threads=""
  local explicit_use_parallel_cpu=""
  local explicit_pair_id_start=""
  local explicit_invalid_pixel_radius=""
  local explicit_pre_ransac_max_ground_distance_km=""
  local explicit_pre_ransac_ground_lookup_failure_policy=""
  local explicit_matcher_method=""
  local explicit_match_preset_path=""
  local explicit_deep_matcher_config_path=""
  local explicit_deep_match_mode=""
  local explicit_deep_match_temp_root_dir=""
  local explicit_deep_match_manifest_dir=""
  local explicit_deep_match_manifest_summary=""
  local match_preset_path=""
  local explicit_adaptive_routing=""
  local explicit_adaptive_routing_profile=""
  local explicit_dom_source_metadata_csv=""
  local explicit_enable_low_resolution_offset_estimation=""
  local explicit_low_resolution_level=""
  local explicit_low_resolution_max_mean_reprojection_error_pixels=""
  local explicit_low_resolution_min_retained_match_count=""
  local explicit_low_resolution_max_mean_projected_offset_meters=""
  local explicit_visualization_mode=""
  local explicit_memory_profile=""
  local explicit_visualization_target_long_edge=""
  local explicit_preview_crop_margin_pixels=""
  local explicit_preview_cache_source=""
  local explicit_skip_final_merge=""
  local explicit_post_merge_control_measure=""
  local explicit_post_merge_output=""
  local explicit_post_merge_decimals=""
  local deep_match_temp_root_dir_input=""
  local deep_match_manifest_dir_input=""
  local deep_match_manifest_summary_input=""
  local DOM_SOURCE_METADATA_CSV=""
  local config_match_preset_path=""
  local config_valid_pixel_percent_threshold=""
  local config_num_worker_parallel_cpu=""
  local config_opencv_num_threads=""
  local config_use_parallel_cpu=""
  local config_invalid_pixel_radius=""
  local config_pre_ransac_max_ground_distance_km=""
  local config_pre_ransac_ground_lookup_failure_policy=""
  local config_matcher_method=""
  local config_deep_matcher_config_path=""
  local config_enable_adaptive_routing=""
  local config_adaptive_routing_profile=""
  local config_enable_low_resolution_offset_estimation=""
  local config_low_resolution_level=""
  local config_low_resolution_max_mean_reprojection_error_pixels=""
  local config_low_resolution_min_retained_match_count=""
  local config_low_resolution_max_mean_projected_offset_meters=""
  local config_visualization_mode=""
  local config_memory_profile=""
  local config_visualization_target_long_edge=""
  local config_preview_crop_margin_pixels=""
  local config_preview_cache_source=""
  local config_strict_parameter_validation=""
  local config_network_id=""
  local preset_match_preset_path=""
  local preset_matcher_method=""
  local preset_deep_match_config_path=""
  local PROFILE_VALID_PIXEL_PERCENT_THRESHOLD=""
  local PROFILE_INVALID_PIXEL_RADIUS=""
  local PROFILE_MATCHER_METHOD=""
  local PROFILE_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION=""
  local PROFILE_LOW_RESOLUTION_LEVEL=""
  local PROFILE_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS=""
  local PROFILE_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT=""
  local PROFILE_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS=""
  local PROFILE_NUM_WORKER_PARALLEL_CPU=""

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"
  CATALOG_PYTHON_EXECUTABLE="${PARAMETER_CATALOG_PYTHON_EXECUTABLE:-python}"
  CNETMERGE_PATH="${CNETMERGE_EXECUTABLE:-cnetmerge}"
  PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
  PAIR_ID_START="$DEFAULT_PAIR_ID_START"
  VALID_PIXEL_PERCENT_THRESHOLD=""
  INVALID_PIXEL_RADIUS="$DEFAULT_INVALID_PIXEL_RADIUS"
  PRE_RANSAC_MAX_GROUND_DISTANCE_KM="$DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM"
  PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="$DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY"
  MATCHER_METHOD="bf"
  ADAPTIVE_ROUTING="0"
  ADAPTIVE_ROUTING_PROFILE="balanced"
  DEEP_MATCH_MODE="direct"
  DEEP_MATCHER_CONFIG_PATH=""
  ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION="0"
  LOW_RESOLUTION_LEVEL="3"
  LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS="3.0"
  LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT="5"
  LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS="0.0"
  VISUALIZATION_MODE="full"
  MEMORY_PROFILE="balanced"
  VISUALIZATION_TARGET_LONG_EDGE=""
  PREVIEW_CROP_MARGIN_PIXELS="128"
  PREVIEW_CACHE_SOURCE="auto"
  USE_PARALLEL_CPU="1"
  NUM_WORKER_PARALLEL_CPU="8"
  OPENCV_NUM_THREADS=""
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
      --print-parameter-groups)
        print_parameter_groups="1"
        shift
        ;;
      --validate-parameters-only)
        validate_parameters_only="1"
        shift
        ;;
      --strict-parameter-validation)
        strict_parameter_validation="1"
        explicit_strict_parameter_validation="1"
        shift
        ;;
      --parameter-profile)
        [[ $# -ge 2 ]] || die "missing value for --parameter-profile"
        parameter_profile=$2
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
      --opencv-num-threads)
        [[ $# -ge 2 ]] || die "missing value for --opencv-num-threads"
        OPENCV_NUM_THREADS=$2
        explicit_opencv_num_threads=$2
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
        explicit_pair_id_start=$2
        shift 2
        ;;
      --valid-pixel-percent-threshold)
        [[ $# -ge 2 ]] || die "missing value for --valid-pixel-percent-threshold"
        VALID_PIXEL_PERCENT_THRESHOLD=$2
        explicit_valid_pixel_percent_threshold=$2
        shift 2
        ;;
      --invalid-pixel-radius)
        [[ $# -ge 2 ]] || die "missing value for --invalid-pixel-radius"
        INVALID_PIXEL_RADIUS=$2
        explicit_invalid_pixel_radius=$2
        shift 2
        ;;
      --pre-ransac-max-ground-distance-km)
        [[ $# -ge 2 ]] || die "missing value for --pre-ransac-max-ground-distance-km"
        PRE_RANSAC_MAX_GROUND_DISTANCE_KM=$2
        explicit_pre_ransac_max_ground_distance_km=$2
        shift 2
        ;;
      --pre-ransac-ground-lookup-failure-policy)
        [[ $# -ge 2 ]] || die "missing value for --pre-ransac-ground-lookup-failure-policy"
        case "$2" in
          drop|keep) ;;
          *) die "--pre-ransac-ground-lookup-failure-policy must be drop or keep" ;;
        esac
        PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY=$2
        explicit_pre_ransac_ground_lookup_failure_policy=$2
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
        MATCHER_METHOD=$2
        explicit_matcher_method=$2
        shift 2
        ;;
      --adaptive-routing)
        ADAPTIVE_ROUTING="1"
        explicit_adaptive_routing="1"
        shift
        ;;
      --no-adaptive-routing)
        ADAPTIVE_ROUTING="0"
        explicit_adaptive_routing="0"
        shift
        ;;
      --adaptive-routing-profile)
        [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-profile"
        ADAPTIVE_ROUTING_PROFILE=$2
        explicit_adaptive_routing_profile=$2
        shift 2
        ;;
      --dom-source-metadata-csv)
        [[ $# -ge 2 ]] || die "missing value for --dom-source-metadata-csv"
        DOM_SOURCE_METADATA_CSV=$2
        explicit_dom_source_metadata_csv=$2
        shift 2
        ;;
      --deep-match-mode)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"
        DEEP_MATCH_MODE=$2
        explicit_deep_match_mode=$2
        shift 2
        ;;
      --deep-match-config-path)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-config-path"
        DEEP_MATCHER_CONFIG_PATH=$2
        explicit_deep_matcher_config_path=$2
        shift 2
        ;;
      --deep-match-temp-root-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-temp-root-dir"
        deep_match_temp_root_dir_input=$2
        explicit_deep_match_temp_root_dir=$2
        shift 2
        ;;
      --deep-match-manifest-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-dir"
        deep_match_manifest_dir_input=$2
        explicit_deep_match_manifest_dir=$2
        shift 2
        ;;
      --deep-match-manifest-summary)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-summary"
        deep_match_manifest_summary_input=$2
        explicit_deep_match_manifest_summary=$2
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
      --visualization-mode)
        [[ $# -ge 2 ]] || die "missing value for --visualization-mode"
        VISUALIZATION_MODE=$2
        explicit_visualization_mode=$2
        shift 2
        ;;
      --memory-profile)
        [[ $# -ge 2 ]] || die "missing value for --memory-profile"
        MEMORY_PROFILE=$2
        explicit_memory_profile=$2
        shift 2
        ;;
      --visualization-target-long-edge)
        [[ $# -ge 2 ]] || die "missing value for --visualization-target-long-edge"
        VISUALIZATION_TARGET_LONG_EDGE=$2
        explicit_visualization_target_long_edge=$2
        shift 2
        ;;
      --preview-crop-margin-pixels)
        [[ $# -ge 2 ]] || die "missing value for --preview-crop-margin-pixels"
        PREVIEW_CROP_MARGIN_PIXELS=$2
        explicit_preview_crop_margin_pixels=$2
        shift 2
        ;;
      --preview-cache-source)
        [[ $# -ge 2 ]] || die "missing value for --preview-cache-source"
        PREVIEW_CACHE_SOURCE=$2
        explicit_preview_cache_source=$2
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
        explicit_skip_final_merge="1"
        shift
        ;;
      --post-merge-control-measure)
        POST_MERGE_CONTROL_MEASURE="1"
        explicit_post_merge_control_measure="1"
        shift
        ;;
      --post-merge-output)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-output"
        post_merge_output_input=$2
        explicit_post_merge_output=$2
        shift 2
        ;;
      --post-merge-decimals)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-decimals"
        POST_MERGE_DECIMALS=$2
        explicit_post_merge_decimals=$2
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

  if [[ -n "$explicit_match_preset_path" && -n "$explicit_matcher_method" ]]; then
    die "--match-preset-path cannot be combined with --matcher-method"
  fi
  if [[ -n "$explicit_match_preset_path" && -n "$explicit_deep_matcher_config_path" ]]; then
    die "--match-preset-path cannot be combined with --deep-match-config-path"
  fi

  require_command "$PYTHON_EXECUTABLE"
  require_command "$CATALOG_PYTHON_EXECUTABLE"

  cd "$REPO_ROOT"

  if [[ "$print_parameter_groups" == "1" ]]; then
    print_parameter_groups
    exit 0
  fi

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
  MATCH_RESULTS_DIR="$WORK_DIR/match_results"
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
  IMAGE_OVERLAP_REPORT_JSON_PATH="$REPORTS_DIR/image_overlap_summary.json"
  CONTROLNET_BATCH_REPORT_PATH="$REPORTS_DIR/controlnet_batch_summary.json"
  MERGE_REPORT_JSON_PATH="$REPORTS_DIR/controlnet_merge_summary.json"
  POST_MERGE_REPORT_JSON_PATH="$REPORTS_DIR/merge_control_measure_summary.json"
  DEEP_MATCH_TEMP_ROOT_DIR="${deep_match_temp_root_dir_input:-$WORK_DIR/deep_match_workspaces}"
  DEEP_MATCH_MANIFEST_DIR="$deep_match_manifest_dir_input"
  DEEP_MATCH_MANIFEST_SUMMARY="${deep_match_manifest_summary_input:-$REPORTS_DIR/deep_match_manifests.json}"

  case "$DEEP_MATCH_MODE" in
    direct|export|import) ;;
    *) die "unsupported --deep-match-mode: $DEEP_MATCH_MODE" ;;
  esac
  if [[ "$DEEP_MATCH_MODE" == "import" && -z "$DEEP_MATCH_MANIFEST_DIR" ]]; then
    die "--deep-match-mode import requires --deep-match-manifest-dir"
  fi

  require_file "$ORIGINAL_LIST"
  require_file "$DOM_LIST"
  require_file "$CONFIG_PATH"
  local run_pipeline_config_assignments
  run_pipeline_config_assignments=$(load_run_pipeline_config_values "$CONFIG_PATH")
  eval "$run_pipeline_config_assignments"

  if [[ -n "$explicit_match_preset_path" ]]; then
    match_preset_path=$(resolve_cli_relative_path "$explicit_match_preset_path")
  elif [[ -z "$explicit_matcher_method" && -z "$explicit_deep_matcher_config_path" ]]; then
    if [[ -n "$config_match_preset_path" && "$config_match_preset_path" != "null" ]]; then
      match_preset_path=$(resolve_config_relative_path "$config_match_preset_path" "$CONFIG_PATH")
    fi
  fi
  if [[ -n "$match_preset_path" ]]; then
    local match_preset_assignments
    match_preset_assignments=$(resolve_match_preset_shell_assignments "$match_preset_path")
    eval "$match_preset_assignments"
    preset_match_preset_path="${MATCH_PRESET_PATH:-$match_preset_path}"
    preset_matcher_method="$MATCHER_METHOD"
    preset_deep_match_config_path="${DEEP_MATCHER_CONFIG_PATH:-}"
  fi

  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" && "$SKIP_FINAL_MERGE" == "1" ]]; then
    die "--post-merge-control-measure cannot be used together with --skip-final-merge"
  fi

  if [[ -z "$NETWORK_ID" ]]; then
    NETWORK_ID="$config_network_id"
    [[ -n "$NETWORK_ID" ]] || die "missing NetworkId in config JSON"
  fi
  if [[ "$strict_parameter_validation" != "1" ]]; then
    if [[ "$config_strict_parameter_validation" == "1" ]]; then
      strict_parameter_validation="1"
    fi
  fi
  if [[ -z "$explicit_valid_pixel_percent_threshold" ]]; then
    if [[ -n "$config_valid_pixel_percent_threshold" ]]; then
      VALID_PIXEL_PERCENT_THRESHOLD="$config_valid_pixel_percent_threshold"
    fi
  fi
  if [[ -z "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
    VALID_PIXEL_PERCENT_THRESHOLD="$DEFAULT_VALID_PIXEL_PERCENT_THRESHOLD"
  fi
  if [[ -z "$explicit_use_parallel_cpu" ]]; then
    if [[ -n "$config_use_parallel_cpu" ]]; then
      USE_PARALLEL_CPU="$config_use_parallel_cpu"
    fi
  fi
  if [[ -z "$explicit_num_worker_parallel_cpu" ]]; then
    if [[ -n "$config_num_worker_parallel_cpu" ]]; then
      NUM_WORKER_PARALLEL_CPU="$config_num_worker_parallel_cpu"
    fi
  fi
  if [[ -z "$explicit_opencv_num_threads" ]]; then
    if [[ -n "$config_opencv_num_threads" ]]; then
      OPENCV_NUM_THREADS="$config_opencv_num_threads"
    fi
  fi
  if [[ -z "$explicit_invalid_pixel_radius" ]]; then
    if [[ -n "$config_invalid_pixel_radius" ]]; then
      INVALID_PIXEL_RADIUS="$config_invalid_pixel_radius"
    fi
  fi
  if [[ -z "$explicit_pre_ransac_max_ground_distance_km" ]]; then
    if [[ -n "$config_pre_ransac_max_ground_distance_km" ]]; then
      PRE_RANSAC_MAX_GROUND_DISTANCE_KM="$config_pre_ransac_max_ground_distance_km"
    fi
  fi
  if [[ -z "$explicit_pre_ransac_ground_lookup_failure_policy" ]]; then
    if [[ -n "$config_pre_ransac_ground_lookup_failure_policy" ]]; then
      PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY="$config_pre_ransac_ground_lookup_failure_policy"
    fi
  fi
  if [[ -z "$match_preset_path" && -z "$explicit_matcher_method" ]]; then
    if [[ -n "$config_matcher_method" ]]; then
      MATCHER_METHOD="$config_matcher_method"
    fi
  fi
  if [[ -z "$explicit_adaptive_routing" ]]; then
    if [[ -n "$config_enable_adaptive_routing" ]]; then
      ADAPTIVE_ROUTING="$config_enable_adaptive_routing"
    fi
  fi
  if [[ -z "$explicit_adaptive_routing_profile" ]]; then
    if [[ -n "$config_adaptive_routing_profile" ]]; then
      ADAPTIVE_ROUTING_PROFILE="$config_adaptive_routing_profile"
    fi
  fi
  if [[ -z "$match_preset_path" && -z "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    if [[ -n "$config_deep_matcher_config_path" && "$config_deep_matcher_config_path" != "null" ]]; then
      config_deep_matcher_config_path=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
      DEEP_MATCHER_CONFIG_PATH="$config_deep_matcher_config_path"
    fi
  fi

  # Validate: deep matchers require a config file
  case "$MATCHER_METHOD" in
    superglue|lightglue|loftr)
      if [[ -z "$DEEP_MATCHER_CONFIG_PATH" ]]; then
        die "matcher_method '$MATCHER_METHOD' is a deep matcher. You must specify deep_matcher_config_path in the config JSON or use --deep-match-config-path."
      fi
      if [[ ! -f "$DEEP_MATCHER_CONFIG_PATH" ]]; then
        die "deep matcher config file not found: $DEEP_MATCHER_CONFIG_PATH"
      fi
      "$PYTHON_EXECUTABLE" - "$DEEP_MATCHER_CONFIG_PATH" "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[2]) / "examples" / "controlnet_construct"))
from deep_match_config import load_deep_match_config
try:
    load_deep_match_config(sys.argv[1])
except ValueError as e:
    print(f"ERROR: Invalid deep match config: {e}", file=sys.stderr)
    sys.exit(1)
PY
      if [[ $? -ne 0 ]]; then
        die "Deep match config validation failed for: $DEEP_MATCHER_CONFIG_PATH"
      fi
      ;;
  esac

  if [[ -z "$explicit_enable_low_resolution_offset_estimation" ]]; then
    if [[ -n "$config_enable_low_resolution_offset_estimation" ]]; then
      ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION="$config_enable_low_resolution_offset_estimation"
    fi
  fi
  if [[ -z "$explicit_low_resolution_level" ]]; then
    if [[ -n "$config_low_resolution_level" ]]; then
      LOW_RESOLUTION_LEVEL="$config_low_resolution_level"
    fi
  fi
  if [[ -z "$explicit_low_resolution_max_mean_reprojection_error_pixels" ]]; then
    if [[ -n "$config_low_resolution_max_mean_reprojection_error_pixels" ]]; then
      LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS="$config_low_resolution_max_mean_reprojection_error_pixels"
    fi
  fi
  if [[ -z "$explicit_low_resolution_min_retained_match_count" ]]; then
    if [[ -n "$config_low_resolution_min_retained_match_count" ]]; then
      LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT="$config_low_resolution_min_retained_match_count"
    fi
  fi
  if [[ -z "$explicit_low_resolution_max_mean_projected_offset_meters" ]]; then
    if [[ -n "$config_low_resolution_max_mean_projected_offset_meters" ]]; then
      LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS="$config_low_resolution_max_mean_projected_offset_meters"
    fi
  fi
  if [[ -z "$explicit_visualization_mode" ]]; then
    if [[ -n "$config_visualization_mode" ]]; then
      VISUALIZATION_MODE="$config_visualization_mode"
    fi
  fi
  if [[ -z "$explicit_memory_profile" ]]; then
    if [[ -n "$config_memory_profile" ]]; then
      MEMORY_PROFILE="$config_memory_profile"
    fi
  fi
  if [[ -z "$explicit_visualization_target_long_edge" ]]; then
    if [[ -n "$config_visualization_target_long_edge" ]]; then
      VISUALIZATION_TARGET_LONG_EDGE="$config_visualization_target_long_edge"
    fi
  fi
  if [[ -z "$explicit_preview_crop_margin_pixels" ]]; then
    if [[ -n "$config_preview_crop_margin_pixels" ]]; then
      PREVIEW_CROP_MARGIN_PIXELS="$config_preview_crop_margin_pixels"
    fi
  fi
  if [[ -z "$explicit_preview_cache_source" ]]; then
    if [[ -n "$config_preview_cache_source" ]]; then
      PREVIEW_CACHE_SOURCE="$config_preview_cache_source"
    fi
  fi

  if [[ -n "$parameter_profile" ]]; then
    apply_parameter_profile_defaults || die "unsupported --parameter-profile: $parameter_profile"
  fi

  export REPO_ROOT
  export print_parameter_groups validate_parameters_only strict_parameter_validation explicit_strict_parameter_validation parameter_profile
  export explicit_num_worker_parallel_cpu explicit_opencv_num_threads explicit_use_parallel_cpu explicit_pair_id_start explicit_valid_pixel_percent_threshold explicit_invalid_pixel_radius
  export explicit_pre_ransac_max_ground_distance_km explicit_pre_ransac_ground_lookup_failure_policy
  export explicit_match_preset_path explicit_matcher_method explicit_deep_matcher_config_path
  export explicit_deep_match_mode explicit_deep_match_temp_root_dir explicit_deep_match_manifest_dir explicit_deep_match_manifest_summary
  export explicit_adaptive_routing explicit_adaptive_routing_profile explicit_dom_source_metadata_csv explicit_enable_low_resolution_offset_estimation explicit_low_resolution_level
  export explicit_low_resolution_max_mean_reprojection_error_pixels explicit_low_resolution_min_retained_match_count explicit_low_resolution_max_mean_projected_offset_meters
  export explicit_visualization_mode explicit_memory_profile explicit_visualization_target_long_edge explicit_preview_crop_margin_pixels explicit_preview_cache_source
  export explicit_skip_final_merge explicit_post_merge_control_measure explicit_post_merge_output explicit_post_merge_decimals
  export match_preset_path MATCHER_METHOD DEEP_MATCHER_CONFIG_PATH ADAPTIVE_ROUTING ADAPTIVE_ROUTING_PROFILE DOM_SOURCE_METADATA_CSV USE_PARALLEL_CPU NUM_WORKER_PARALLEL_CPU OPENCV_NUM_THREADS
  export DEEP_MATCH_MODE DEEP_MATCH_TEMP_ROOT_DIR DEEP_MATCH_MANIFEST_DIR DEEP_MATCH_MANIFEST_SUMMARY
  export SKIP_FINAL_MERGE POST_MERGE_CONTROL_MEASURE POST_MERGE_OUTPUT_PATH POST_MERGE_DECIMALS
  export PAIR_ID_START VALID_PIXEL_PERCENT_THRESHOLD INVALID_PIXEL_RADIUS PRE_RANSAC_MAX_GROUND_DISTANCE_KM PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY
  export ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION LOW_RESOLUTION_LEVEL LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT
  export LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS VISUALIZATION_MODE MEMORY_PROFILE VISUALIZATION_TARGET_LONG_EDGE PREVIEW_CROP_MARGIN_PIXELS PREVIEW_CACHE_SOURCE
  export config_match_preset_path config_num_worker_parallel_cpu config_opencv_num_threads config_use_parallel_cpu config_matcher_method config_deep_matcher_config_path
  export config_pre_ransac_max_ground_distance_km config_pre_ransac_ground_lookup_failure_policy
  export config_enable_adaptive_routing config_adaptive_routing_profile config_enable_low_resolution_offset_estimation config_low_resolution_level
  export config_low_resolution_max_mean_reprojection_error_pixels config_low_resolution_min_retained_match_count config_low_resolution_max_mean_projected_offset_meters
  export config_visualization_mode config_memory_profile config_visualization_target_long_edge config_preview_crop_margin_pixels config_preview_cache_source
  export config_strict_parameter_validation
  export preset_match_preset_path preset_matcher_method preset_deep_match_config_path
  export PROFILE_VALID_PIXEL_PERCENT_THRESHOLD PROFILE_INVALID_PIXEL_RADIUS PROFILE_MATCHER_METHOD
  export PROFILE_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION PROFILE_LOW_RESOLUTION_LEVEL
  export PROFILE_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS PROFILE_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT
  export PROFILE_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS PROFILE_NUM_WORKER_PARALLEL_CPU

  validate_controlnet_parameters >/dev/null

  if [[ "$validate_parameters_only" == "1" ]]; then
    printf 'Parameter validation passed\n'
    print_parameter_validation_summary
    exit 0
  fi

  LOW_RESOLUTION_DOM_LIST="$WORK_DIR/doms_low_resolution_level${LOW_RESOLUTION_LEVEL}.lis"
  LOW_RESOLUTION_DOM_DIR="$WORK_DIR/low_resolution_doms/level${LOW_RESOLUTION_LEVEL}"
  LOW_RESOLUTION_DOM_REPORT="$REPORTS_DIR/low_resolution_doms_level${LOW_RESOLUTION_LEVEL}.json"

  mkdir -p "$DOM_KEYS_DIR" "$MATCH_METADATA_DIR" "$MATCH_RESULTS_DIR" "$PRE_RANSAC_MATCH_VIZ_DIR" "$POST_RANSAC_MATCH_VIZ_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"
  if [[ "$DEEP_MATCH_MODE" == "export" ]]; then
    mkdir -p "$DEEP_MATCH_TEMP_ROOT_DIR"
  fi
  if [[ "$DEEP_MATCH_MODE" == "export" ]]; then
    initialize_deep_match_manifest_summary "$DEEP_MATCH_MANIFEST_SUMMARY"
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
    log "CPU parallel worker limit: $NUM_WORKER_PARALLEL_CPU"
  else
    log "CPU parallel tile matching: disabled"
    log "CPU parallel worker limit (forwarded default): $NUM_WORKER_PARALLEL_CPU"
  fi
  if [[ -n "$OPENCV_NUM_THREADS" ]]; then
    log "OpenCV thread limit: $OPENCV_NUM_THREADS"
  else
    log "OpenCV thread limit: default"
  fi
  if [[ -n "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
    log "Valid pixel percent threshold: $VALID_PIXEL_PERCENT_THRESHOLD"
  else
    log "Valid pixel percent threshold: examples/image_match/image_match.py default"
  fi
  log "Invalid pixel radius: $INVALID_PIXEL_RADIUS"
  log "Pre-RANSAC max ground distance (km): $PRE_RANSAC_MAX_GROUND_DISTANCE_KM"
  log "Pre-RANSAC ground lookup failure policy: $PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY"
  if [[ -n "$match_preset_path" ]]; then
    log "Match preset path: $match_preset_path"
  fi
  log "Matcher method: $MATCHER_METHOD"
  if [[ -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    log "Deep match config: $DEEP_MATCHER_CONFIG_PATH"
  fi
  if [[ "$ADAPTIVE_ROUTING" == "1" ]]; then
    log "Adaptive routing: enabled"
  else
    log "Adaptive routing: disabled"
  fi
  log "Adaptive routing profile: $ADAPTIVE_ROUTING_PROFILE"
  if [[ -n "$DOM_SOURCE_METADATA_CSV" ]]; then
    log "DOM source metadata CSV: $DOM_SOURCE_METADATA_CSV"
  fi
  log "Deep-match mode: $DEEP_MATCH_MODE"
  if [[ "$DEEP_MATCH_MODE" == "export" ]]; then
    log "Deep-match temp root dir: $DEEP_MATCH_TEMP_ROOT_DIR"
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  elif [[ "$DEEP_MATCH_MODE" == "import" ]]; then
    log "Deep-match manifest dir: $DEEP_MATCH_MANIFEST_DIR"
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  fi
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
  log "Post-RANSAC visualization mode: $VISUALIZATION_MODE"
  log "Post-RANSAC memory profile: $MEMORY_PROFILE"
  if [[ -n "$VISUALIZATION_TARGET_LONG_EDGE" ]]; then
    log "Post-RANSAC visualization target long edge: $VISUALIZATION_TARGET_LONG_EDGE"
  else
    log "Post-RANSAC visualization target long edge: default"
  fi
  log "Post-RANSAC preview crop margin (pixels): $PREVIEW_CROP_MARGIN_PIXELS"
  log "Post-RANSAC preview cache source: $PREVIEW_CACHE_SOURCE"
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
  if [[ "$DEEP_MATCH_MODE" == "export" ]]; then
    finalize_timing_json "success"
    log "Pipeline stopped after image_match_batch because --deep-match-mode export does not create final .key files."
    log "Deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
    log "Run examples/learning_methods/run_deep_match_manifest.py in deep-learning for each manifest, then rerun this pipeline with --deep-match-mode import."
    return 0
  fi
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
  log "  image-match result json: $MATCH_RESULTS_DIR"
  if [[ "$DEEP_MATCH_MODE" != "direct" ]]; then
    log "  deep-match manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  fi
  log "  pre-RANSAC match viz: $PRE_RANSAC_MATCH_VIZ_DIR"
  log "  post-RANSAC match viz: $POST_RANSAC_MATCH_VIZ_DIR"
  log "  pairwise nets: $PAIR_NETS_DIR"
  log "  reports: $REPORTS_DIR"
  log "  image overlap summary json: $IMAGE_OVERLAP_REPORT_JSON_PATH"
  log "  merge summary json: $MERGE_REPORT_JSON_PATH"
  log "  merge script: $MERGE_SCRIPT_PATH"
  log "  merged net: $MERGED_NET_PATH"
  if [[ "$POST_MERGE_CONTROL_MEASURE" == "1" ]]; then
    if [[ -n "$POST_MERGE_OUTPUT_PATH" ]]; then
      log "  post-merged net: $POST_MERGE_OUTPUT_PATH"
    else
      log "  post-merged net: auto-named beside $MERGED_NET_PATH"
    fi
    log "  post-merge summary json: $POST_MERGE_REPORT_JSON_PATH"
  fi
  log "  timing json: $TIMING_JSON_PATH"
}

main "$@"
