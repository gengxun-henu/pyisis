#!/usr/bin/env bash
#
# Sparse stereo DEM extraction pipeline wrapper.
#
# Author: Geng Xun
# Created: 2026-05-10
# Last Modified: 2026-05-10
# Updated: 2026-05-10  Geng Xun added a one-command DEM pipeline wrapper for original-image and DOM matching routes.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_CONFIG_RELATIVE="examples/dem_extract/dem_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work/dem_extract"

log() {
  printf '[dem-pipeline] %s\n' "$*"
}

warn() {
  printf '[dem-pipeline] warning: %s\n' "$*" >&2
}

die() {
  printf '[dem-pipeline] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  examples/dem_extract/run_pipeline_example.sh [options]

Run the sparse stereo DEM example pipeline end to end. Two matching routes are
supported:

  ori  original-image matching -> original-image .key -> DEM
  dom  DOM matching -> DOM .key -> merge/RANSAC/dom2ori -> original-image .key -> DEM

Options:
  --mode ori|dom                 Matching route. Default: ori
  --work-dir PATH                Root working directory. Default: work/dem_extract
  --config PATH                  DEM pipeline config JSON. Default: examples/dem_extract/dem_config.example.json
  --python PATH                  Python interpreter. Default: $PYTHON_EXECUTABLE or python
  --left-cube PATH               Left original ISIS cube. Required for both modes
  --right-cube PATH              Right original ISIS cube. Required for both modes
  --left-dom PATH                Left DOM/projected cube. Required for --mode dom
  --right-dom PATH               Right DOM/projected cube. Required for --mode dom
  --map-template-cube PATH       Projected cube whose Mapping group and dimensions define the DEM grid. Required
  --output-dem-cube PATH         Output DEM cube. Default: <work-dir>/dem/stereo_dem.cub
  --point-cloud-output PATH      Output point cloud JSONL/CSV. Default: <work-dir>/point_cloud/stereo_points.jsonl
  --summary-output PATH          DEM extraction summary JSON. Default: <work-dir>/reports/dem_summary.json
  --quality-prefix PATH          Prefix for quality sidecars. Default: <work-dir>/quality/stereo_dem
  --pipeline-summary-output PATH Pipeline summary JSON. Default: <work-dir>/reports/pipeline_summary.json
  -h, --help                     Show this help message

Environment overrides:
  PYTHON_EXECUTABLE              Python interpreter used by this script

Examples:
  bash examples/dem_extract/run_pipeline_example.sh \
    --mode ori \
    --left-cube left.cub \
    --right-cube right.cub \
    --map-template-cube left_dom.cub

  bash examples/dem_extract/run_pipeline_example.sh \
    --mode dom \
    --left-dom left_dom.cub \
    --right-dom right_dom.cub \
    --left-cube left.cub \
    --right-cube right.cub \
    --map-template-cube left_dom.cub
EOF
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_value() {
  local name=$1
  local value=$2
  [[ -n "$value" ]] || die "missing required option: $name"
}

summarize_pipeline_report() {
  local report_path=$1
  [[ -s "$report_path" ]] || {
    log "pipeline summary json: $report_path"
    return 0
  }
  "$PYTHON_EXECUTABLE" - "$report_path" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(f"pipeline summary json={path}")
    raise SystemExit(0)

parts = [
    f"mode={payload.get('mode')}",
    f"output_dem_cube={payload.get('output_dem_cube')}",
    f"point_cloud_output={payload.get('point_cloud_output')}",
]
dem = payload.get("dem")
if isinstance(dem, dict):
    for key, label in (
        ("success_count", "triangulated"),
        ("filled_cell_count", "filled_cells"),
        ("rasterized_point_count", "rasterized"),
    ):
        value = dem.get(key)
        if value is not None:
            parts.append(f"{label}={value}")
parts.append(f"summary_json={path}")
print(" ".join(str(part) for part in parts if part and not str(part).endswith("=None")))
PY
}

main() {
  local mode="ori"
  local work_dir_input="$DEFAULT_WORK_DIR_RELATIVE"
  local config_input="$DEFAULT_CONFIG_RELATIVE"
  local left_cube=""
  local right_cube=""
  local left_dom=""
  local right_dom=""
  local map_template_cube=""
  local output_dem_cube=""
  local point_cloud_output=""
  local summary_output=""
  local quality_prefix=""
  local pipeline_summary_output=""

  PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        [[ $# -ge 2 ]] || die "missing value for --mode"
        mode=$2
        shift 2
        ;;
      --work-dir)
        [[ $# -ge 2 ]] || die "missing value for --work-dir"
        work_dir_input=$2
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
      --left-cube)
        [[ $# -ge 2 ]] || die "missing value for --left-cube"
        left_cube=$2
        shift 2
        ;;
      --right-cube)
        [[ $# -ge 2 ]] || die "missing value for --right-cube"
        right_cube=$2
        shift 2
        ;;
      --left-dom)
        [[ $# -ge 2 ]] || die "missing value for --left-dom"
        left_dom=$2
        shift 2
        ;;
      --right-dom)
        [[ $# -ge 2 ]] || die "missing value for --right-dom"
        right_dom=$2
        shift 2
        ;;
      --map-template-cube)
        [[ $# -ge 2 ]] || die "missing value for --map-template-cube"
        map_template_cube=$2
        shift 2
        ;;
      --output-dem-cube)
        [[ $# -ge 2 ]] || die "missing value for --output-dem-cube"
        output_dem_cube=$2
        shift 2
        ;;
      --point-cloud-output)
        [[ $# -ge 2 ]] || die "missing value for --point-cloud-output"
        point_cloud_output=$2
        shift 2
        ;;
      --summary-output)
        [[ $# -ge 2 ]] || die "missing value for --summary-output"
        summary_output=$2
        shift 2
        ;;
      --quality-prefix)
        [[ $# -ge 2 ]] || die "missing value for --quality-prefix"
        quality_prefix=$2
        shift 2
        ;;
      --pipeline-summary-output)
        [[ $# -ge 2 ]] || die "missing value for --pipeline-summary-output"
        pipeline_summary_output=$2
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

  case "$mode" in
    ori|dom) ;;
    *) die "--mode must be one of: ori, dom" ;;
  esac

  require_command "$PYTHON_EXECUTABLE"
  require_value "--left-cube" "$left_cube"
  require_value "--right-cube" "$right_cube"
  require_value "--map-template-cube" "$map_template_cube"
  if [[ "$mode" == "dom" ]]; then
    require_value "--left-dom" "$left_dom"
    require_value "--right-dom" "$right_dom"
  elif [[ -n "$left_dom" || -n "$right_dom" ]]; then
    warn "--left-dom/--right-dom were provided but --mode ori ignores DOM inputs"
  fi

  cd "$REPO_ROOT"

  local pipeline_summary_default="$work_dir_input/reports/pipeline_summary.json"
  local pipeline_summary_path="${pipeline_summary_output:-$pipeline_summary_default}"
  local command_name="from-ori-match-dem"
  local pipeline_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/dem_extract/dem_pipeline.py"
    --work-dir "$work_dir_input"
    --config "$config_input"
    --pipeline-summary-output "$pipeline_summary_path"
  )

  if [[ -n "$output_dem_cube" ]]; then
    pipeline_args+=(--output-dem-cube "$output_dem_cube")
  fi
  if [[ -n "$point_cloud_output" ]]; then
    pipeline_args+=(--point-cloud-output "$point_cloud_output")
  fi
  if [[ -n "$summary_output" ]]; then
    pipeline_args+=(--summary-output "$summary_output")
  fi
  if [[ -n "$quality_prefix" ]]; then
    pipeline_args+=(--quality-prefix "$quality_prefix")
  fi

  if [[ "$mode" == "dom" ]]; then
    command_name="from-dom-match"
    pipeline_args+=(
      "$command_name"
      --left-dom "$left_dom"
      --right-dom "$right_dom"
      --left-cube "$left_cube"
      --right-cube "$right_cube"
      --map-template-cube "$map_template_cube"
    )
  else
    pipeline_args+=(
      "$command_name"
      --left-cube "$left_cube"
      --right-cube "$right_cube"
      --map-template-cube "$map_template_cube"
    )
  fi

  log "Repository root: $REPO_ROOT"
  log "Mode: $mode"
  log "Work directory: $work_dir_input"
  log "Config: $config_input"
  log "Python executable: $PYTHON_EXECUTABLE"
  log "Pipeline summary: $pipeline_summary_path"
  log "START $command_name"
  "${pipeline_args[@]}" >/dev/null
  log "END $command_name status=success"
  log "$(summarize_pipeline_report "$pipeline_summary_path")"
  log "Key outputs:"
  log "  work dir: $work_dir_input"
  log "  keys: $work_dir_input/keys_ori"
  if [[ "$mode" == "dom" ]]; then
    log "  DOM keys: $work_dir_input/keys_dom"
    log "  match viz: $work_dir_input/match_viz"
  fi
  log "  DEM: ${output_dem_cube:-$work_dir_input/dem/stereo_dem.cub}"
  log "  reports: $work_dir_input/reports"
  log "  point cloud: ${point_cloud_output:-$work_dir_input/point_cloud/stereo_points.jsonl}"
}

main "$@"
