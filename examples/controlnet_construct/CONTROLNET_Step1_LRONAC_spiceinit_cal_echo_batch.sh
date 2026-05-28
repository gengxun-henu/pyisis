#!/usr/bin/env bash
# Generate per-step LRO NAC preprocessing tasks for external parallel execution.
# This script only prints tasks and does not execute them.
#
# Author: Geng Xun
# Created: 2026-05-11
# Updated: 2026-05-11  Geng Xun added top-of-file metadata so example shell entrypoints follow the repository's example-file header convention.
# Updated: 2026-05-28  Geng Xun added a dedicated spiced-cube isis2std stage before cam2map while preserving the DOM export stage.

set -euo pipefail

MAP="lunar_transversemercator.map"
INPUT_DIR="."
INPUT_GLOB="*.IMG*"
OUTPUT_FILE=""
STEP="all"
TASK_FORMAT="command"
INCLUDE_SPICEINIT="0"
SPICEINIT_EXTRA=""
USE_REDUCE="0"
RESUME_FROM=""
declare -a SKIP_STEPS=()
STEP_ORDER=(init-lists lronac2isis reduce lronaccal lronacecho spiceinit isis2std-spiced cam2map isis2std append-lists cleanup)

usage() {
  cat <<'EOF'
Usage:
  CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh [options]

Generate task lines for LRO NAC Step1 preprocessing.
The output is intended to be consumed by an external parallel runner.

Options:
  --step NAME              Step to emit. Default: all
                           Supported: all, init-lists, lronac2isis, reduce,
                                      lronaccal, lronacecho, spiceinit,
                                      isis2std-spiced, cam2map, isis2std,
                                      append-lists, cleanup
  --task-format FORMAT     Output format. Default: command
                           Supported: command, tsv
                           - command: each line is a runnable shell command
                           - tsv: each line is "<step>\t<command>"
  --map PATH               Map file for cam2map. Default: lunar_transversemercator.map
  --input-dir PATH         Directory containing IMG files. Default: current directory
  --input-glob PATTERN     Input IMG pattern. Default: *.IMG*
  --output-file PATH       Write emitted tasks directly to this file instead of stdout
  --skip-step NAME[,NAME]  Skip already-processed steps; can be repeated or
                           passed as a comma-separated list
  --resume-from NAME       Auto-skip all earlier stages and resume command
                           emission from the named step
  --use-reduce             Insert reduce after lronac2isis and switch all
                           downstream tasks to REDUCED_* products
  --include-spiceinit      Emit spiceinit tasks (off by default)
  --spiceinit-extra ARGS   Extra args appended to spiceinit command (string)
  -h, --help               Show this help message

Examples:
  # 仅输出 cam2map 阶段任务（每行一条命令）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step cam2map

  # 输出全流程任务，包含步骤标签（TSV）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step all --task-format tsv

  # 仅导出当前 working cube 的 TIFF（原始或 REDUCED 版本）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step isis2std-spiced --use-reduce --output-file step1_spiced_tif_batch.txt

  # 从 spiceinit 恢复时，也会包含 spiced-cube TIFF 导出
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step all --use-reduce --include-spiceinit --resume-from spiceinit --output-file step1_resume_from_spiceinit.txt
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
    if [[ -n "$OUTPUT_FILE" ]]; then
      printf '%s\t%s\n' "$step_name" "$command_line" >> "$OUTPUT_FILE"
    else
      printf '%s\t%s\n' "$step_name" "$command_line"
    fi
  else
    if [[ -n "$OUTPUT_FILE" ]]; then
      printf '%s\n' "$command_line" >> "$OUTPUT_FILE"
    else
      printf '%s\n' "$command_line"
    fi
  fi
}

quote_arg() {
  local value="$1"
  printf '%q' "$value"
}

basename_without_img_suffix() {
  local filename="$1"
  local basename_value
  basename_value=$(basename "$filename")
  if [[ "$basename_value" == *".IMG"* ]]; then
    printf '%s' "${basename_value%%.IMG*}"
  elif [[ "$basename_value" == *.* ]]; then
    printf '%s' "${basename_value%.*}"
  else
    printf '%s' "$basename_value"
  fi
}

add_skip_steps() {
  local raw_value="$1"
  local raw_step=""
  local normalized_step=""
  local IFS=','
  read -r -a raw_skip_parts <<< "$raw_value"
  for raw_step in "${raw_skip_parts[@]}"; do
    normalized_step="${raw_step//[[:space:]]/}"
    normalized_step="${normalized_step,,}"
    [[ -n "$normalized_step" ]] || continue
    SKIP_STEPS+=("$normalized_step")
  done
}

is_step_skipped() {
  local candidate_name="${1,,}"
  local skipped_name=""
  for skipped_name in "${SKIP_STEPS[@]}"; do
    if [[ "$skipped_name" == "$candidate_name" ]]; then
      return 0
    fi
  done
  return 1
}

apply_resume_from_skip_steps() {
  local ordered_step=""
  [[ -n "$RESUME_FROM" ]] || return 0
  for ordered_step in "${STEP_ORDER[@]}"; do
    if [[ "$ordered_step" == "$RESUME_FROM" ]]; then
      return 0
    fi
    SKIP_STEPS+=("$ordered_step")
  done
  die "unsupported --resume-from: $RESUME_FROM"
}

step_selected() {
  local name="$1"
  if is_step_skipped "$name"; then
    return 1
  fi
  if [[ "$name" == "reduce" ]]; then
    [[ "$STEP" == "reduce" || ( "$STEP" == "all" && "$USE_REDUCE" == "1" ) ]]
    return
  fi
  [[ "$STEP" == "all" || "$STEP" == "$name" ]]
}

validate_step() {
  case "$STEP" in
    all|init-lists|lronac2isis|reduce|lronaccal|lronacecho|spiceinit|isis2std-spiced|cam2map|isis2std|append-lists|cleanup)
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

validate_input_dir() {
  [[ -d "$INPUT_DIR" ]] || die "input directory does not exist: $INPUT_DIR"
}

validate_resume_from() {
  local ordered_step=""
  [[ -n "$RESUME_FROM" ]] || return 0
  for ordered_step in "${STEP_ORDER[@]}"; do
    if [[ "$ordered_step" == "$RESUME_FROM" ]]; then
      return 0
    fi
  done
  die "unsupported --resume-from: $RESUME_FROM"
}

validate_skip_steps() {
  local skip_name=""
  for skip_name in "${SKIP_STEPS[@]}"; do
    case "$skip_name" in
      init-lists|lronac2isis|reduce|lronaccal|lronacecho|spiceinit|isis2std-spiced|cam2map|isis2std|append-lists|cleanup)
        ;;
      *)
        die "unsupported --skip-step: $skip_name"
        ;;
    esac
  done
}

initialize_output_file() {
  if [[ -n "$OUTPUT_FILE" ]]; then
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    : > "$OUTPUT_FILE"
  fi
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
    --input-dir)
      [[ $# -ge 2 ]] || die "missing value for --input-dir"
      INPUT_DIR="$2"
      shift 2
      ;;
    --input-glob)
      [[ $# -ge 2 ]] || die "missing value for --input-glob"
      INPUT_GLOB="$2"
      shift 2
      ;;
    --output-file)
      [[ $# -ge 2 ]] || die "missing value for --output-file"
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --resume-from)
      [[ $# -ge 2 ]] || die "missing value for --resume-from"
      RESUME_FROM="${2,,}"
      shift 2
      ;;
    --skip-step)
      [[ $# -ge 2 ]] || die "missing value for --skip-step"
      add_skip_steps "$2"
      shift 2
      ;;
    --use-reduce)
      USE_REDUCE="1"
      shift
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
validate_input_dir
validate_resume_from
apply_resume_from_skip_steps
validate_skip_steps
initialize_output_file

mapfile -t input_files < <(find "$INPUT_DIR" -maxdepth 1 -type f -name "$INPUT_GLOB" -printf '%p\n' | LC_ALL=C sort)
[[ ${#input_files[@]} -gt 0 ]] || die "no input files matched pattern: $INPUT_GLOB under directory: $INPUT_DIR"

if step_selected "init-lists"; then
  emit_task "init-lists" "rm -f caminfo_all.lis image_all.lis image_all_reduced.lis original_images.lis doms.lis"
fi

for filename in "${input_files[@]}"; do
  base_name=$(basename_without_img_suffix "$filename")
  reduced_base_name="REDUCED_${base_name}"

  filename_q=$(quote_arg "$filename")
  base_cub_q=$(quote_arg "${base_name}.cub")
  reduced_cub_q=$(quote_arg "${reduced_base_name}.cub")
  if [[ "$USE_REDUCE" == "1" ]]; then
    working_base_name="$reduced_base_name"
    working_cub_q="$reduced_cub_q"
  else
    working_base_name="$base_name"
    working_cub_q="$base_cub_q"
  fi
  working_cal_q=$(quote_arg "${working_base_name}.cal.cub")
  working_echo_cal_q=$(quote_arg "${working_base_name}.echo.cal.cub")
  working_tif_q=$(quote_arg "${working_base_name}.tif")
  dom_cub_q=$(quote_arg "dom_${working_base_name}.cub")
  dom_tif_q=$(quote_arg "dom_8bpp${working_base_name}.tif")
  map_q=$(quote_arg "$MAP")
  caminfo_q=$(quote_arg "caminfo_${working_base_name}.txt")

  if step_selected "lronac2isis"; then
    emit_task "lronac2isis" "lronac2isis from=${filename_q} to=${base_cub_q}"
  fi

  if step_selected "reduce"; then
    emit_task "reduce" "reduce from=${base_cub_q} to=${reduced_cub_q} sscale=10 lscale=10"
  fi

  if step_selected "lronaccal"; then
    emit_task "lronaccal" "lronaccal from=${working_cub_q} to=${working_cal_q}"
  fi

  if step_selected "lronacecho"; then
    emit_task "lronacecho" "lronacecho from=${working_cal_q} to=${working_echo_cal_q}"
  fi

  if step_selected "spiceinit" && [[ "$INCLUDE_SPICEINIT" == "1" ]]; then
    if [[ -n "$SPICEINIT_EXTRA" ]]; then
      emit_task "spiceinit" "spiceinit from=${working_echo_cal_q} ${SPICEINIT_EXTRA}"
    else
      emit_task "spiceinit" "spiceinit from=${working_echo_cal_q}"
    fi
  fi

  if step_selected "isis2std-spiced"; then
    emit_task "isis2std-spiced" "isis2std from=${working_cub_q} to=${working_tif_q} format=tiff minpercent=0.1 maxpercent=99.9"
  fi

  if step_selected "cam2map"; then
    emit_task "cam2map" "cam2map from=${working_echo_cal_q} map=${map_q} to=${dom_cub_q} interp=bilinear warpalgorithm=forwardpatch patchsize=21 pixres=mpp resolution=1"
  fi

  if step_selected "isis2std"; then
    emit_task "isis2std" "isis2std from=${dom_cub_q} to=${dom_tif_q} format=tiff minpercent=0.1 maxpercent=99.9"
  fi

  if step_selected "append-lists"; then
    emit_task "append-lists" "printf '%s\\n' ${caminfo_q} >> caminfo_all.lis"
    emit_task "append-lists" "printf '%s\\n' ${working_echo_cal_q} >> original_images.lis"
    if [[ "$USE_REDUCE" == "1" ]]; then
      emit_task "append-lists" "printf '%s\\n' ${working_echo_cal_q} >> image_all_reduced.lis"
    fi
    emit_task "append-lists" "printf '%s\\n' ${dom_cub_q} >> doms.lis"
  fi

  if step_selected "cleanup"; then
    cleanup_targets="${working_cal_q} ${working_cub_q}"
    if [[ "$USE_REDUCE" == "1" ]]; then
      cleanup_targets+=" ${base_cub_q}"
    fi
    emit_task "cleanup" "rm -f ${cleanup_targets}"
  fi
done
