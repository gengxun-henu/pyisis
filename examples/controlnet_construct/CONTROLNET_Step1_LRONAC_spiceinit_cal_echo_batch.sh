#!/usr/bin/env bash
# Generate per-step LRO NAC preprocessing tasks for external parallel execution.
# This script ONLY prints tasks and does not execute them.

set -euo pipefail

MAP="lunar_transversemercator.map"
INPUT_GLOB="*.IMG*"
STEP="all"
TASK_FORMAT="command"
INCLUDE_SPICEINIT="0"
SPICEINIT_EXTRA=""

usage() {
  cat <<'EOF'
Usage:
  CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh [options]

Generate task lines for LRO NAC Step1 preprocessing.
The output is intended to be consumed by an external parallel runner.

Options:
  --step NAME              Step to emit. Default: all
                           Supported: all, init-lists, lronac2isis, lronaccal,
                                      lronacecho, spiceinit, cam2map, isis2std,
                                      append-lists, cleanup
  --task-format FORMAT     Output format. Default: command
                           Supported: command, tsv
                           - command: each line is a runnable shell command
                           - tsv: each line is "<step>\t<command>"
  --map PATH               Map file for cam2map. Default: lunar_transversemercator.map
  --input-glob PATTERN     Input IMG pattern. Default: *.IMG*
  --include-spiceinit      Emit spiceinit tasks (off by default)
  --spiceinit-extra ARGS   Extra args appended to spiceinit command (string)
  -h, --help               Show this help message

Examples:
  # 仅输出 cam2map 阶段任务（每行一条命令）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step cam2map

  # 输出全流程任务，包含步骤标签（TSV）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step all --task-format tsv
EOF
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

emit_task() {
  local step_name="$1"
  local command_line="$2"
  if [[ "$TASK_FORMAT" == "tsv" ]]; then
    printf '%s\t%s\n' "$step_name" "$command_line"
  else
    printf '%s\n' "$command_line"
  fi
}

quote_arg() {
  local value="$1"
  printf '%q' "$value"
}

basename_without_img_suffix() {
  local filename="$1"
  if [[ "$filename" == *".IMG"* ]]; then
    printf '%s' "${filename%%.IMG*}"
  elif [[ "$filename" == *.* ]]; then
    printf '%s' "${filename%.*}"
  else
    printf '%s' "$filename"
  fi
}

step_selected() {
  local name="$1"
  [[ "$STEP" == "all" || "$STEP" == "$name" ]]
}

validate_step() {
  case "$STEP" in
    all|init-lists|lronac2isis|lronaccal|lronacecho|spiceinit|cam2map|isis2std|append-lists|cleanup)
      ;;
    *)
      die "unsupported --step: $STEP"
      ;;
  esac
}

validate_task_format() {
  case "$TASK_FORMAT" in
    command|tsv)
      ;;
    *)
      die "unsupported --task-format: $TASK_FORMAT"
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --step)
      [[ $# -ge 2 ]] || die "missing value for --step"
      STEP="$2"
      shift 2
      ;;
    --task-format)
      [[ $# -ge 2 ]] || die "missing value for --task-format"
      TASK_FORMAT="$2"
      shift 2
      ;;
    --map)
      [[ $# -ge 2 ]] || die "missing value for --map"
      MAP="$2"
      shift 2
      ;;
    --input-glob)
      [[ $# -ge 2 ]] || die "missing value for --input-glob"
      INPUT_GLOB="$2"
      shift 2
      ;;
    --include-spiceinit)
      INCLUDE_SPICEINIT="1"
      shift
      ;;
    --spiceinit-extra)
      [[ $# -ge 2 ]] || die "missing value for --spiceinit-extra"
      SPICEINIT_EXTRA="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

validate_step
validate_task_format

mapfile -t input_files < <(find . -maxdepth 1 -type f -name "$INPUT_GLOB" -printf '%P\n' | LC_ALL=C sort)
[[ ${#input_files[@]} -gt 0 ]] || die "no input files matched pattern: $INPUT_GLOB"

if step_selected "init-lists"; then
  emit_task "init-lists" "rm -f caminfo_all.lis image_all.lis image_all_reduced.lis original_images.lis doms.lis"
fi

for filename in "${input_files[@]}"; do
  base_name=$(basename_without_img_suffix "$filename")

  filename_q=$(quote_arg "$filename")
  base_cub_q=$(quote_arg "${base_name}.cub")
  base_cal_q=$(quote_arg "${base_name}.cal.cub")
  base_echo_cal_q=$(quote_arg "${base_name}.echo.cal.cub")
  dom_cub_q=$(quote_arg "dom_${base_name}.cub")
  dom_tif_q=$(quote_arg "dom_8bpp${base_name}.tif")
  map_q=$(quote_arg "$MAP")
  caminfo_q=$(quote_arg "caminfo_${base_name}.txt")

  if step_selected "lronac2isis"; then
    emit_task "lronac2isis" "lronac2isis from=${filename_q} to=${base_cub_q}"
  fi

  if step_selected "lronaccal"; then
    emit_task "lronaccal" "lronaccal from=${base_cub_q} to=${base_cal_q}"
  fi

  if step_selected "lronacecho"; then
    emit_task "lronacecho" "lronacecho from=${base_cal_q} to=${base_echo_cal_q}"
  fi

  if step_selected "spiceinit" && [[ "$INCLUDE_SPICEINIT" == "1" ]]; then
    if [[ -n "$SPICEINIT_EXTRA" ]]; then
      emit_task "spiceinit" "spiceinit from=${base_echo_cal_q} ${SPICEINIT_EXTRA}"
    else
      emit_task "spiceinit" "spiceinit from=${base_echo_cal_q}"
    fi
  fi

  if step_selected "cam2map"; then
    emit_task "cam2map" "cam2map from=${base_echo_cal_q} map=${map_q} to=${dom_cub_q} interp=bilinear warpalgorithm=forwardpatch patchsize=21 pixres=mpp resolution=1"
  fi

  if step_selected "isis2std"; then
    emit_task "isis2std" "isis2std from=${dom_cub_q} to=${dom_tif_q} format=tiff minpercent=0.1 maxpercent=99.9"
  fi

  if step_selected "append-lists"; then
    emit_task "append-lists" "printf '%s\\n' ${caminfo_q} >> caminfo_all.lis"
    emit_task "append-lists" "printf '%s\\n' ${base_echo_cal_q} >> original_images.lis"
    emit_task "append-lists" "printf '%s\\n' ${dom_cub_q} >> doms.lis"
  fi

  if step_selected "cleanup"; then
    emit_task "cleanup" "rm -f ${base_cal_q} ${base_cub_q}"
  fi
done
