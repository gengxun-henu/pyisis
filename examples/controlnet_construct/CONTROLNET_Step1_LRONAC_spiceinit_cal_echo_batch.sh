#!/usr/bin/env bash
# Generate per-step LRO NAC preprocessing tasks or an orchestrator shell script.
# The default modes only print tasks; orchestrator mode writes a runnable script.
#
# Author: Geng Xun
# Created: 2026-05-11
# Updated: 2026-05-11  Geng Xun added top-of-file metadata so example shell entrypoints follow the repository's example-file header convention.
# Updated: 2026-05-28  Geng Xun added a dedicated spiced-cube isis2std stage before cam2map while preserving the DOM export stage.
# Updated: 2026-05-28  Geng Xun added orchestrator output with per-stage barriers, moved reduce after lronacecho, and added batched cleanup.
# Updated: 2026-05-29  Geng Xun added configurable cam2map map resolution for reduced polar DOM generation.
# Updated: 2026-06-03  Geng Xun restored echo/cal downstream routing after reduce so Step1 TIFF/list outputs match spiced camera products.

set -euo pipefail

MAP="lunar_transversemercator.map"
CAM2MAP_RESOLUTION="1"
INPUT_DIR="."
INPUT_GLOB="*.IMG*"
OUTPUT_FILE=""
STEP="all"
TASK_FORMAT="command"
INCLUDE_SPICEINIT="0"
SPICEINIT_EXTRA=""
USE_REDUCE="0"
RESUME_FROM=""
PARALLEL_JOBS="4"
CLEANUP_BATCH_SIZE="80"
declare -a SKIP_STEPS=()
STEP_ORDER=(init-lists lronac2isis lronaccal lronacecho reduce spiceinit isis2std-spiced cam2map isis2std append-lists cleanup)

usage() {
  cat <<'EOF'
Usage:
  CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh [options]

Generate LRO NAC Step1 preprocessing tasks.
Use --task-format orchestrator when emitting multiple dependent stages; it writes
a runnable shell script with per-stage GNU Parallel barriers.

Options:
  --step NAME              Step to emit. Default: all
                           Supported: all, init-lists, lronac2isis, reduce,
                                      lronaccal, lronacecho, spiceinit,
                                      isis2std-spiced, cam2map, isis2std,
                                      append-lists, cleanup
  --task-format FORMAT     Output format. Default: command
                           Supported: command, tsv, orchestrator
                           - command: each line is a runnable shell command
                           - tsv: each line is "<step>\t<command>"
                           - orchestrator: runnable shell script; each stage
                             completes before the next stage starts
  --map PATH               Map file for cam2map. Default: lunar_transversemercator.map
  --cam2map-resolution N   cam2map output map resolution in meters/pixel. Default: 1
  --input-dir PATH         Directory containing IMG files. Default: current directory
  --input-glob PATTERN     Input IMG pattern. Default: *.IMG*
  --output-file PATH       Write emitted tasks directly to this file instead of stdout
  --skip-step NAME[,NAME]  Skip already-processed steps; can be repeated or
                           passed as a comma-separated list
  --resume-from NAME       Auto-skip all earlier stages and resume command
                           emission from the named step
  --use-reduce             Insert reduce after lronacecho and switch all
                           downstream tasks to REDUCED_* echo/cal products
  --parallel-jobs N        GNU Parallel jobs used by orchestrator output. Default: 4
  --cleanup-batch-size N   Orchestrator batch size before intermediate cleanup.
                           Default: 80. Use 0 to disable batching.
  --include-spiceinit      Emit spiceinit tasks (off by default)
  --spiceinit-extra ARGS   Extra args appended to spiceinit command (string)
  -h, --help               Show this help message

Examples:
  # 仅输出 cam2map 阶段任务（每行一条命令）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step cam2map

  # 输出全流程任务，包含步骤标签（TSV）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --step all --task-format tsv

  # 输出带阶段屏障的可执行 orchestration shell 脚本（推荐用于多步骤）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step all --use-reduce --task-format orchestrator --parallel-jobs 8 --output-file step1_orchestrator.sh
  bash step1_orchestrator.sh

  # 仅导出当前 working cube 的 TIFF（原始或 REDUCED 版本）
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step isis2std-spiced --use-reduce --output-file step1_spiced_tif_batch.txt

  # 从 spiceinit 恢复时，也会包含 spiced-cube TIFF 导出
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step all --use-reduce --include-spiceinit --resume-from spiceinit --task-format orchestrator --parallel-jobs 8 --output-file step1_resume_from_spiceinit.sh
  bash step1_resume_from_spiceinit.sh

  # gnu parallel processing based on a single-stage generated task list
  ./CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh --input-dir /data/lro/img --step lronac2isis --output-file lronac2isis_batch.txt
  cat lronac2isis_batch.txt | parallel --jobs 4
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

write_output_line() {
  local line="$1"
  if [[ -n "$OUTPUT_FILE" ]]; then
    printf '%s\n' "$line" >> "$OUTPUT_FILE"
  else
    printf '%s\n' "$line"
  fi
}

emit_orchestrator_header() {
  write_output_line "#!/usr/bin/env bash"
  write_output_line "set -euo pipefail"
  write_output_line ""
  write_output_line "PARALLEL_JOBS=\"\${PARALLEL_JOBS:-${PARALLEL_JOBS}}\""
  write_output_line ""
  write_output_line "run_parallel_stage() {"
  write_output_line "  local stage_name=\"\$1\""
  write_output_line "  echo \"[START] \${stage_name}\""
  write_output_line "  parallel --jobs \"\$PARALLEL_JOBS\" --halt soon,fail=1"
  write_output_line "  echo \"[END] \${stage_name}\""
  write_output_line "}"
  write_output_line ""
  write_output_line "run_serial_stage() {"
  write_output_line "  local stage_name=\"\$1\""
  write_output_line "  local command_line=\"\""
  write_output_line "  echo \"[START] \${stage_name}\""
  write_output_line "  while IFS= read -r command_line; do"
  write_output_line "    [[ -n \"\$command_line\" ]] || continue"
  write_output_line "    echo \"+ \${command_line}\""
  write_output_line "    bash -c \"\$command_line\""
  write_output_line "  done"
  write_output_line "  echo \"[END] \${stage_name}\""
  write_output_line "}"
  write_output_line ""
}

emit_orchestrator_stage() {
  local runner_name="$1"
  local stage_label="$2"
  shift 2
  local commands=("$@")
  local command_line=""

  [[ ${#commands[@]} -gt 0 ]] || return 0
  write_output_line "${runner_name} $(quote_arg "$stage_label") <<'EOF'"
  for command_line in "${commands[@]}"; do
    write_output_line "$command_line"
  done
  write_output_line "EOF"
  write_output_line ""
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

build_stage_commands_for_file() {
  local stage_name="$1"
  local filename="$2"
  local base_name=""
  local reduced_base_name=""
  local filename_q=""
  local base_cub_q=""
  local base_cal_q=""
  local base_echo_cal_q=""
  local reduced_echo_cal_q=""
  local working_base_name=""
  local working_echo_cal_q=""
  local working_tif_q=""
  local dom_cub_q=""
  local dom_tif_q=""
  local map_q=""
  local cam2map_resolution_q=""
  local caminfo_q=""
  local cleanup_targets=""

  base_name=$(basename_without_img_suffix "$filename")
  reduced_base_name="REDUCED_${base_name}"

  filename_q=$(quote_arg "$filename")
  base_cub_q=$(quote_arg "${base_name}.cub")
  base_cal_q=$(quote_arg "${base_name}.cal.cub")
  base_echo_cal_q=$(quote_arg "${base_name}.echo.cal.cub")
  reduced_echo_cal_q=$(quote_arg "${reduced_base_name}.echo.cal.cub")
  if [[ "$USE_REDUCE" == "1" ]]; then
    working_base_name="$reduced_base_name"
    working_echo_cal_q="$reduced_echo_cal_q"
  else
    working_base_name="$base_name"
    working_echo_cal_q="$base_echo_cal_q"
  fi
  working_tif_q=$(quote_arg "${working_base_name}.tif")
  dom_cub_q=$(quote_arg "dom_${working_base_name}.cub")
  dom_tif_q=$(quote_arg "dom_8bpp${working_base_name}.tif")
  map_q=$(quote_arg "$MAP")
  cam2map_resolution_q=$(quote_arg "$CAM2MAP_RESOLUTION")
  caminfo_q=$(quote_arg "caminfo_${working_base_name}.txt")

  case "$stage_name" in
    lronac2isis)
      printf '%s\n' "lronac2isis from=${filename_q} to=${base_cub_q}"
      ;;
    lronaccal)
      printf '%s\n' "lronaccal from=${base_cub_q} to=${base_cal_q}"
      ;;
    lronacecho)
      printf '%s\n' "lronacecho from=${base_cal_q} to=${base_echo_cal_q}"
      ;;
    reduce)
      printf '%s\n' "reduce from=${base_echo_cal_q} to=${reduced_echo_cal_q} sscale=10 lscale=10"
      ;;
    spiceinit)
      if [[ "$INCLUDE_SPICEINIT" == "1" ]]; then
        if [[ -n "$SPICEINIT_EXTRA" ]]; then
          printf '%s\n' "spiceinit from=${working_echo_cal_q} ${SPICEINIT_EXTRA}"
        else
          printf '%s\n' "spiceinit from=${working_echo_cal_q}"
        fi
      fi
      ;;
    isis2std-spiced)
      printf '%s\n' "isis2std from=${working_echo_cal_q} to=${working_tif_q} format=tiff minpercent=0.1 maxpercent=99.9"
      ;;
    cam2map)
      printf '%s\n' "cam2map from=${working_echo_cal_q} map=${map_q} to=${dom_cub_q} interp=bilinear warpalgorithm=forwardpatch patchsize=21 pixres=mpp resolution=${cam2map_resolution_q}"
      ;;
    isis2std)
      printf '%s\n' "isis2std from=${dom_cub_q} to=${dom_tif_q} format=tiff minpercent=0.1 maxpercent=99.9"
      ;;
    append-lists)
      printf '%s\n' "printf '%s\\n' ${caminfo_q} >> caminfo_all.lis"
      printf '%s\n' "printf '%s\\n' ${working_echo_cal_q} >> original_images.lis"
      if [[ "$USE_REDUCE" == "1" ]]; then
        printf '%s\n' "printf '%s\\n' ${working_echo_cal_q} >> image_all_reduced.lis"
      fi
      printf '%s\n' "printf '%s\\n' ${dom_cub_q} >> doms.lis"
      ;;
    cleanup)
      cleanup_targets="${base_cal_q} ${base_cub_q}"
      if [[ "$USE_REDUCE" == "1" ]]; then
        cleanup_targets+=" ${base_echo_cal_q}"
      fi
      printf '%s\n' "rm -f ${cleanup_targets}"
      ;;
  esac
}

emit_stage_for_file() {
  local stage_name="$1"
  local filename="$2"
  local command_line=""
  while IFS= read -r command_line; do
    [[ -n "$command_line" ]] || continue
    emit_task "$stage_name" "$command_line"
  done < <(build_stage_commands_for_file "$stage_name" "$filename")
}

collect_batch_stage_commands() {
  local stage_name="$1"
  local batch_start="$2"
  local batch_end="$3"
  local index=""
  local command_line=""
  local collected=()

  for (( index=batch_start; index<batch_end; index++ )); do
    while IFS= read -r command_line; do
      [[ -n "$command_line" ]] || continue
      collected+=("$command_line")
    done < <(build_stage_commands_for_file "$stage_name" "${input_files[$index]}")
  done

  if [[ ${#collected[@]} -gt 0 ]]; then
    printf '%s\n' "${collected[@]}"
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
    command|tsv|orchestrator)
      ;;
    *)
      die "unsupported --task-format: $TASK_FORMAT"
      ;;
  esac
}

validate_positive_integer() {
  local option_name="$1"
  local value="$2"
  [[ "$value" =~ ^[0-9]+$ ]] || die "$option_name must be a non-negative integer: $value"
}

validate_parallel_options() {
  validate_positive_integer "--parallel-jobs" "$PARALLEL_JOBS"
  validate_positive_integer "--cleanup-batch-size" "$CLEANUP_BATCH_SIZE"
  [[ "$PARALLEL_JOBS" -gt 0 ]] || die "--parallel-jobs must be greater than 0"
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
    --cam2map-resolution)
      [[ $# -ge 2 ]] || die "missing value for --cam2map-resolution"
      CAM2MAP_RESOLUTION="$2"
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
    --parallel-jobs)
      [[ $# -ge 2 ]] || die "missing value for --parallel-jobs"
      PARALLEL_JOBS="$2"
      shift 2
      ;;
    --cleanup-batch-size)
      [[ $# -ge 2 ]] || die "missing value for --cleanup-batch-size"
      CLEANUP_BATCH_SIZE="$2"
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
validate_parallel_options
validate_input_dir
validate_resume_from
apply_resume_from_skip_steps
validate_skip_steps
initialize_output_file

mapfile -t input_files < <(find "$INPUT_DIR" -maxdepth 1 -type f -name "$INPUT_GLOB" -printf '%p\n' | LC_ALL=C sort)
[[ ${#input_files[@]} -gt 0 ]] || die "no input files matched pattern: $INPUT_GLOB under directory: $INPUT_DIR"

emit_stage_range() {
  local stage_name="$1"
  local batch_start="$2"
  local batch_end="$3"
  local index=""

  for (( index=batch_start; index<batch_end; index++ )); do
    emit_stage_for_file "$stage_name" "${input_files[$index]}"
  done
}

emit_flat_tasks() {
  local stage_name=""

  if step_selected "init-lists"; then
    emit_task "init-lists" "rm -f caminfo_all.lis image_all.lis image_all_reduced.lis original_images.lis doms.lis"
  fi

  for stage_name in "${STEP_ORDER[@]}"; do
    case "$stage_name" in
      init-lists)
        ;;
      cleanup)
        ;;
      *)
        if step_selected "$stage_name"; then
          emit_stage_range "$stage_name" 0 "${#input_files[@]}"
        fi
        ;;
    esac
  done

  if step_selected "cleanup"; then
    emit_stage_range "cleanup" 0 "${#input_files[@]}"
  fi
}

emit_orchestrator_tasks() {
  local total_files="${#input_files[@]}"
  local batch_size="$CLEANUP_BATCH_SIZE"
  local batch_start="0"
  local batch_end="0"
  local batch_label=""
  local stage_name=""
  local commands=()

  if [[ "$batch_size" -eq 0 ]]; then
    batch_size="$total_files"
  fi

  emit_orchestrator_header

  if step_selected "init-lists"; then
    emit_orchestrator_stage "run_serial_stage" "init-lists" \
      "rm -f caminfo_all.lis image_all.lis image_all_reduced.lis original_images.lis doms.lis"
  fi

  while [[ "$batch_start" -lt "$total_files" ]]; do
    batch_end=$(( batch_start + batch_size ))
    if [[ "$batch_end" -gt "$total_files" ]]; then
      batch_end="$total_files"
    fi
    batch_label="$(( batch_start + 1 ))-${batch_end}"

    for stage_name in "${STEP_ORDER[@]}"; do
      case "$stage_name" in
        init-lists|cleanup)
          ;;
        append-lists)
          if step_selected "$stage_name"; then
            mapfile -t commands < <(collect_batch_stage_commands "$stage_name" "$batch_start" "$batch_end")
            emit_orchestrator_stage "run_serial_stage" "${stage_name} batch ${batch_label}" "${commands[@]}"
          fi
          ;;
        *)
          if step_selected "$stage_name"; then
            mapfile -t commands < <(collect_batch_stage_commands "$stage_name" "$batch_start" "$batch_end")
            emit_orchestrator_stage "run_parallel_stage" "${stage_name} batch ${batch_label}" "${commands[@]}"
          fi
          ;;
      esac
    done

    if step_selected "cleanup"; then
      mapfile -t commands < <(collect_batch_stage_commands "cleanup" "$batch_start" "$batch_end")
      emit_orchestrator_stage "run_parallel_stage" "cleanup batch ${batch_label}" "${commands[@]}"
    fi

    batch_start="$batch_end"
  done

  if step_selected "cleanup" && [[ "$batch_size" -lt "$total_files" ]]; then
    mapfile -t commands < <(collect_batch_stage_commands "cleanup" 0 "$total_files")
    emit_orchestrator_stage "run_parallel_stage" "cleanup final sweep" "${commands[@]}"
  fi
}

if [[ "$TASK_FORMAT" == "orchestrator" ]]; then
  emit_orchestrator_tasks
else
  emit_flat_tasks
fi
