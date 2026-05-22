#!/usr/bin/env bash

# Three-stage deep-match pipeline wrapper.
#
# Automates the manual conda handoff cycle:
#   1. asp360_new   → export deep-match manifests
#   2. deep-learning → run matching on every manifest
#   3. asp360_new   → import results and (optionally) continue ControlNet
#
# Author: Geng Xun
# Created: 2026-05-16

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)

log() {
  printf '[deep-match-pipeline] %s\n' "$*"
}

warn() {
  printf '[deep-match-pipeline] warning: %s\n' "$*" >&2
}

die() {
  printf '[deep-match-pipeline] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: run_deep_match_pipeline.sh [OPTIONS]

Automates the three-stage deep-match handoff (export → match → import) so you
don't need to manually switch conda environments between stages.

Modes:
  --mode MODE               "full" runs export → deep-learning → import → ControlNet.
                            "deep-match-only" runs export → deep-learning → import, then stops.
                            Default: full

Conda environments:
  --asp360-env NAME         Conda env for ISIS/PYISIS stages. Default: asp360_new
  --deep-learning-env NAME  Conda env for deep matcher execution. Default: deep-learning

Pipeline arguments (forwarded to run_pipeline_example.sh):
  --work-dir PATH           Root working directory. Default: work
  --config PATH             Path to JSON config file.
  --matcher-method NAME     Matcher backend (e.g. lightglue, loftr, superglue).
  --deep-match-config-path PATH
                            Path to deep matcher preset JSON config.
  --skip-final-merge        Skip the final cnetmerge step in full mode.

Deep-match arguments:
  --deep-match-temp-root-dir PATH  Workspace root for exported manifests.
                            Default: <work-dir>/deep_match_workspaces
  --deep-match-manifest-summary PATH
                            Summary JSON path. Default: <work-dir>/reports/deep_match_manifests.json

Deep-learning execution:
  --device DEVICE           Device for deep matcher: auto, cpu, cuda. Default: auto
  --fail-fast               Stop deep-learning stage on first manifest failure.
  --skip-existing           Skip manifests whose results already exist.
  --continue-on-deep-failure
                            Instead of failing the whole pipeline when a manifest
                            fails, continue to import and warn about missing results.

Recovery:
  --resume-from STAGE       Skip completed stages and resume from "export", "deep-learning", or "import".
                            Useful when a stage was interrupted.

Misc:
  --dry-run                 Print commands instead of executing them.
  -h, --help                Show this help message.

Examples:

  # Full pipeline with default env names:
  bash examples/controlnet_construct/run_deep_match_pipeline.sh \
    --work-dir work --matcher-method lightglue

  # Deep-match only (no ControlNet steps):
  bash examples/controlnet_construct/run_deep_match_pipeline.sh \
    --mode deep-match-only --work-dir work --matcher-method loftr

  # Resume from import stage after deep-learning completed:
  bash examples/controlnet_construct/run_deep_match_pipeline.sh \
    --work-dir work --matcher-method lightglue --resume-from import

  # Continue even if some manifests fail (import what succeeded):
  bash examples/controlnet_construct/run_deep_match_pipeline.sh \
    --work-dir work --matcher-method lightglue --continue-on-deep-failure
EOF
}

# ── Defaults ──────────────────────────────────────────────────────────────

MODE="full"
ASP360_ENV="asp360_new"
DEEP_LEARNING_ENV="deep-learning"
WORK_DIR="work"
CONFIG_PATH=""
MATCHER_METHOD=""
DEEP_MATCH_CONFIG_PATH=""
SKIP_FINAL_MERGE=false
DEEP_MATCH_TEMP_ROOT_DIR=""
DEEP_MATCH_MANIFEST_SUMMARY=""
DEVICE="auto"
FAIL_FAST=true
SKIP_EXISTING=false
CONTINUE_ON_DEEP_FAILURE=false
RESUME_FROM=""
DRY_RUN=false

# ── Argument parsing ─────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ $# -ge 2 ]] || die "missing value for --mode"
      MODE=$2; shift 2 ;;
    --asp360-env)
      [[ $# -ge 2 ]] || die "missing value for --asp360-env"
      ASP360_ENV=$2; shift 2 ;;
    --deep-learning-env)
      [[ $# -ge 2 ]] || die "missing value for --deep-learning-env"
      DEEP_LEARNING_ENV=$2; shift 2 ;;
    --work-dir)
      [[ $# -ge 2 ]] || die "missing value for --work-dir"
      WORK_DIR=$2; shift 2 ;;
    --config)
      [[ $# -ge 2 ]] || die "missing value for --config"
      CONFIG_PATH=$2; shift 2 ;;
    --matcher-method)
      [[ $# -ge 2 ]] || die "missing value for --matcher-method"
      MATCHER_METHOD=$2; shift 2 ;;
    --deep-match-config-path)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-config-path"
      DEEP_MATCH_CONFIG_PATH=$2; shift 2 ;;
    --skip-final-merge)
      SKIP_FINAL_MERGE=true; shift ;;
    --deep-match-temp-root-dir)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-temp-root-dir"
      DEEP_MATCH_TEMP_ROOT_DIR=$2; shift 2 ;;
    --deep-match-manifest-summary)
      [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-summary"
      DEEP_MATCH_MANIFEST_SUMMARY=$2; shift 2 ;;
    --device)
      [[ $# -ge 2 ]] || die "missing value for --device"
      DEVICE=$2; shift 2 ;;
    --fail-fast)
      FAIL_FAST=true; shift ;;
    --no-fail-fast)
      FAIL_FAST=false; shift ;;
    --skip-existing)
      SKIP_EXISTING=true; shift ;;
    --continue-on-deep-failure)
      CONTINUE_ON_DEEP_FAILURE=true; shift ;;
    --resume-from)
      [[ $# -ge 2 ]] || die "missing value for --resume-from"
      RESUME_FROM=$2; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "unknown argument: $1" ;;
  esac
done

# ── Validation ────────────────────────────────────────────────────────────

if [[ "$MODE" != "full" && "$MODE" != "deep-match-only" ]]; then
  die "--mode must be 'full' or 'deep-match-only', got '$MODE'"
fi

if [[ -n "$RESUME_FROM" && "$RESUME_FROM" != "export" && "$RESUME_FROM" != "deep-learning" && "$RESUME_FROM" != "import" ]]; then
  die "--resume-from must be 'export', 'deep-learning', or 'import', got '$RESUME_FROM'"
fi

if [[ -z "$MATCHER_METHOD" ]]; then
  die "--matcher-method is required (e.g. lightglue, loftr, superglue)"
fi

# Compute derived defaults
WORK_DIR_ABS=$(cd "$REPO_ROOT" && realpath -m "$WORK_DIR")
DEEP_MATCH_TEMP_ROOT_DIR="${DEEP_MATCH_TEMP_ROOT_DIR:-${WORK_DIR_ABS}/deep_match_workspaces}"
DEEP_MATCH_MANIFEST_SUMMARY="${DEEP_MATCH_MANIFEST_SUMMARY:-${WORK_DIR_ABS}/reports/deep_match_manifests.json}"

# ── Helper: run a command inside a conda env ──────────────────────────────

run_in_conda_env() {
  local env_name=$1; shift
  if [[ "$DRY_RUN" == "true" ]]; then
    log "[dry-run] conda run -n $env_name --no-capture-output $*"
    return 0
  fi
  conda run -n "$env_name" --no-capture-output "$@"
}

# ── Stage 1: Export ───────────────────────────────────────────────────────

stage_export() {
  log "=== Stage 1: Export deep-match manifests (env: $ASP360_ENV) ==="

  local pipeline_args=(
    "$REPO_ROOT/examples/controlnet_construct/run_pipeline_example.sh"
    --work-dir "$WORK_DIR"
    --matcher-method "$MATCHER_METHOD"
    --deep-match-mode export
    --deep-match-temp-root-dir "$DEEP_MATCH_TEMP_ROOT_DIR"
    --deep-match-manifest-summary "$DEEP_MATCH_MANIFEST_SUMMARY"
  )

  if [[ -n "$CONFIG_PATH" ]]; then
    pipeline_args+=(--config "$CONFIG_PATH")
  fi

  if [[ -n "$DEEP_MATCH_CONFIG_PATH" ]]; then
    pipeline_args+=(--deep-match-config-path "$DEEP_MATCH_CONFIG_PATH")
  fi

  if [[ "$SKIP_FINAL_MERGE" == "true" && "$MODE" == "full" ]]; then
    pipeline_args+=(--skip-final-merge)
  fi

  run_in_conda_env "$ASP360_ENV" bash "${pipeline_args[@]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Export complete (dry-run: not verifying output)"
    return 0
  fi

  if [[ ! -f "$DEEP_MATCH_MANIFEST_SUMMARY" ]]; then
    die "Export completed but manifest summary not found: $DEEP_MATCH_MANIFEST_SUMMARY"
  fi

  local pair_count
  pair_count=$(python3 -c "import json; print(len(json.load(open('$DEEP_MATCH_MANIFEST_SUMMARY')).get('pairs', [])))")
  log "Export complete: $pair_count pair(s) in manifest summary"
}

# ── Stage 2: Deep-learning batch execution ────────────────────────────────

stage_deep_learning() {
  log "=== Stage 2: Run deep matching (env: $DEEP_LEARNING_ENV) ==="

  if [[ "$DRY_RUN" == "true" ]]; then
    log "  manifest_paths: (from $DEEP_MATCH_MANIFEST_SUMMARY)"
    log "  device: $DEVICE, fail-fast: $FAIL_FAST, skip-existing: $SKIP_EXISTING"
    log "Deep-learning stage complete (dry-run)"
    return 0
  fi

  if [[ ! -f "$DEEP_MATCH_MANIFEST_SUMMARY" ]]; then
    die "Manifest summary not found: $DEEP_MATCH_MANIFEST_SUMMARY. Run export stage first."
  fi

  # Extract manifest paths from the summary JSON
  local manifest_paths
  manifest_paths=$(python3 -c "
import json, sys
data = json.load(open('$DEEP_MATCH_MANIFEST_SUMMARY'))
pairs = data.get('pairs', [])
manifests = [p.get('manifest_path', '') for p in pairs if p.get('manifest_path')]
if not manifests:
    print('ERROR: no manifest_path entries found in summary', file=sys.stderr)
    sys.exit(1)
for m in manifests:
    print(m)
")

  if [[ -z "$manifest_paths" ]]; then
    die "No manifest paths found in $DEEP_MATCH_MANIFEST_SUMMARY"
  fi

  local total_manifests failed_manifests succeeded_manifests
  total_manifests=0
  failed_manifests=0
  succeeded_manifests=0

  local manifest_results_dir
  manifest_results_dir="${WORK_DIR_ABS}/deep_match_results"
  mkdir -p "$manifest_results_dir"

  while IFS= read -r manifest_path; do
    [[ -n "$manifest_path" ]] || continue
    total_manifests=$((total_manifests + 1))

    local pair_id
    pair_id=$(basename "$(dirname "$manifest_path")")
    local result_json="${manifest_results_dir}/${pair_id}_result.json"

    log "--- Pair ${total_manifests}: ${pair_id} ---"
    log "  manifest: ${manifest_path}"

    if run_in_conda_env "$DEEP_LEARNING_ENV" python3 \
      "$REPO_ROOT/examples/learning_methods/run_deep_match_manifest.py" \
      "$manifest_path" \
      --device "$DEVICE" \
      $([[ "$FAIL_FAST" == "true" ]] && echo "--fail-fast") \
      $([[ "$SKIP_EXISTING" == "true" ]] && echo "--skip-existing") \
      --summary-output "$result_json"
    then
      local status
      status=$(python3 -c "import json; d=json.load(open('$result_json')); print(d.get('status','unknown'))")
      log "  result: $status"
      if [[ "$status" == "completed" ]]; then
        succeeded_manifests=$((succeeded_manifests + 1))
      else
        failed_manifests=$((failed_manifests + 1))
      fi
    else
      failed_manifests=$((failed_manifests + 1))
      warn "  manifest execution failed: ${pair_id}"
    fi

    if [[ "$FAIL_FAST" == "true" && "$failed_manifests" -gt 0 && "$CONTINUE_ON_DEEP_FAILURE" != "true" ]]; then
      die "Deep-learning stage failed on pair '${pair_id}' (fail-fast enabled)"
    fi
  done <<< "$manifest_paths"

  log "Deep-learning stage complete: $succeeded_manifests succeeded, $failed_manifests failed out of $total_manifests pair(s)"

  if [[ "$failed_manifests" -gt 0 && "$CONTINUE_ON_DEEP_FAILURE" != "true" ]]; then
    die "Deep-learning stage had $failed_manifests failed pair(s). Use --continue-on-deep-failure to proceed anyway."
  fi

  if [[ "$failed_manifests" -gt 0 && "$CONTINUE_ON_DEEP_FAILURE" == "true" ]]; then
    warn "Continuing with $failed_manifests failed pair(s) -- import stage will only process available results"
  fi
}

# ── Stage 3: Import ───────────────────────────────────────────────────────

stage_import() {
  log "=== Stage 3: Import deep-match results (env: $ASP360_ENV) ==="

  if [[ "$DRY_RUN" == "true" ]]; then
    log "  import from: $DEEP_MATCH_TEMP_ROOT_DIR"
  else
    # Verify that results exist before importing
    local missing_results=0
    while IFS= read -r manifest_path; do
      [[ -n "$manifest_path" ]] || continue
      local results_dir
      results_dir=$(dirname "$(dirname "$manifest_path")")/results
      if [[ ! -d "$results_dir" ]] || [[ -z "$(ls -A "$results_dir" 2>/dev/null)" ]]; then
        missing_results=$((missing_results + 1))
        warn "  no results found for pair: $(basename "$(dirname "$manifest_path")")"
      fi
    done < <(python3 -c "
import json
data = json.load(open('$DEEP_MATCH_MANIFEST_SUMMARY'))
for p in data.get('pairs', []):
    mp = p.get('manifest_path', '')
    if mp:
        print(mp)
")

    if [[ "$missing_results" -gt 0 && "$CONTINUE_ON_DEEP_FAILURE" != "true" ]]; then
      die "$missing_results pair(s) have no results. Run deep-learning stage first."
    fi
  fi

  local pipeline_args=(
    "$REPO_ROOT/examples/controlnet_construct/run_pipeline_example.sh"
    --work-dir "$WORK_DIR"
    --matcher-method "$MATCHER_METHOD"
    --deep-match-mode import
    --deep-match-manifest-dir "$DEEP_MATCH_TEMP_ROOT_DIR"
    --deep-match-manifest-summary "$DEEP_MATCH_MANIFEST_SUMMARY"
  )

  if [[ -n "$CONFIG_PATH" ]]; then
    pipeline_args+=(--config "$CONFIG_PATH")
  fi

  if [[ -n "$DEEP_MATCH_CONFIG_PATH" ]]; then
    pipeline_args+=(--deep-match-config-path "$DEEP_MATCH_CONFIG_PATH")
  fi

  if [[ "$SKIP_FINAL_MERGE" == "true" ]]; then
    pipeline_args+=(--skip-final-merge)
  fi

  run_in_conda_env "$ASP360_ENV" bash "${pipeline_args[@]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Import stage complete (dry-run)"
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────

main() {
  log "Starting deep-match pipeline (mode: $MODE)"
  log "  work-dir: $WORK_DIR"
  log "  matcher-method: $MATCHER_METHOD"
  log "  asp360 env: $ASP360_ENV"
  log "  deep-learning env: $DEEP_LEARNING_ENV"
  log "  device: $DEVICE"
  log "  manifest summary: $DEEP_MATCH_MANIFEST_SUMMARY"
  if [[ "$DRY_RUN" == "true" ]]; then
    log "*** DRY RUN MODE - commands will be printed but not executed ***"
  fi

  # Verify conda is available
  if ! command -v conda &>/dev/null; then
    die "conda not found in PATH. This script requires conda to switch environments."
  fi

  local run_export=false
  local run_deep_learning=false
  local run_import=false
  case "$RESUME_FROM" in
    ""|"export")
      run_export=true
      run_deep_learning=true
      run_import=true
      ;;
    "deep-learning")
      run_deep_learning=true
      run_import=true
      ;;
    "import")
      run_import=true
      ;;
  esac

  if [[ "$run_export" == "true" ]]; then
    stage_export
  fi

  if [[ "$run_deep_learning" == "true" ]]; then
    stage_deep_learning
  fi

  if [[ "$run_import" == "true" ]]; then
    stage_import
  fi

  if [[ "$MODE" == "deep-match-only" ]]; then
    log "Deep-match pipeline complete (deep-match-only mode)"
    return 0
  fi

  log "Full pipeline complete"
}

main "$@"
