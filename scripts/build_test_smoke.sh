#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)

ENV_NAME=${PYISIS_ENV_NAME:-asp360_new}
CONDA_SH=${PYISIS_CONDA_SH:-/home/gengxun/miniconda3/etc/profile.d/conda.sh}
BUILD_DIR=${PYISIS_BUILD_DIR:-build}
BUILD_TYPE=${PYISIS_BUILD_TYPE:-Release}
BUILD_JOBS=${PYISIS_BUILD_JOBS:-$(nproc)}
BUILD_DIR_PATH="${REPO_ROOT}/${BUILD_DIR}"

log() {
  printf '[build-test-smoke] %s\n' "$*"
}

warn() {
  printf '[build-test-smoke] warning: %s\n' "$*" >&2
}

die() {
  printf '[build-test-smoke] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/build_test_smoke.sh full
  scripts/build_test_smoke.sh build-only
  scripts/build_test_smoke.sh test-only
  scripts/build_test_smoke.sh verbose-test
  scripts/build_test_smoke.sh clean-full
  scripts/build_test_smoke.sh unit-module <python.unittest.module>

Commands:
  full         Configure, build, run ctest, then run tests/smoke_import.py.
  build-only   Configure and build only.
  test-only    Run ctest and tests/smoke_import.py against the current build.
  verbose-test Run unittest discover -v, then run tests/smoke_import.py.
  clean-full   Remove the build directory, then run the full pipeline.
  unit-module  Run one unittest module, for example:
               scripts/build_test_smoke.sh unit-module tests.unitTest.controlnet_construct_e2e_unit_test

Environment overrides:
  PYISIS_ENV_NAME     Conda environment name. Default: asp360_new
  PYISIS_CONDA_SH     Path to conda.sh. Default: /home/gengxun/miniconda3/etc/profile.d/conda.sh
  PYISIS_BUILD_DIR    Build directory relative to repo root. Default: build
  PYISIS_BUILD_TYPE   CMake build type. Default: Release
  PYISIS_BUILD_JOBS   Parallel build job count. Default: nproc

Notes:
  - This script intentionally does not export LD_LIBRARY_PATH by default.
  - test-only / verbose-test / unit-module expect an existing configured build tree.
EOF
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

activate_env() {
  [[ -f "$CONDA_SH" ]] || die "conda activation script not found: $CONDA_SH"

  require_command cmake
  require_command ctest

  # shellcheck disable=SC1090
  source "$CONDA_SH"
  require_command conda
  conda activate "$ENV_NAME"

  [[ -n "${CONDA_PREFIX:-}" ]] || die "conda environment '$ENV_NAME' did not activate correctly"

  export ISIS_PREFIX="${ISIS_PREFIX:-$CONDA_PREFIX}"
  export ISISROOT="${ISISROOT:-$CONDA_PREFIX}"
  export ISISDATA="${ISISDATA:-$REPO_ROOT/tests/data/isisdata/mockup}"
  export CMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH:-$CONDA_PREFIX}"

  PYTHON_BIN="${PYTHON_BIN:-$CONDA_PREFIX/bin/python}"
  [[ -x "$PYTHON_BIN" ]] || die "python executable not found: $PYTHON_BIN"

  cd "$REPO_ROOT"

  log "repo root: $REPO_ROOT"
  log "conda env: $ENV_NAME"
  log "python: $PYTHON_BIN"
  log "build dir: $BUILD_DIR"
}

require_existing_build_dir() {
  [[ -d "$BUILD_DIR_PATH" ]] || die "missing build directory: $BUILD_DIR_PATH; run 'scripts/build_test_smoke.sh full' or 'build-only' first"
}

run_configure() {
  log "configuring CMake"
  cmake -S . -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DPython3_EXECUTABLE="$PYTHON_BIN" \
    -DISIS_PREFIX="$CONDA_PREFIX" \
    -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
}

run_build() {
  log "building with ${BUILD_JOBS} job(s)"
  cmake --build "$BUILD_DIR" -j"$BUILD_JOBS"
}

run_ctest_suite() {
  require_existing_build_dir
  log "running ctest python-unit-tests"
  ctest --test-dir "$BUILD_DIR" -R python-unit-tests --output-on-failure
}

run_verbose_unittest_suite() {
  require_existing_build_dir
  log "running verbose unittest discover"
  PYTHONUNBUFFERED=1 "$PYTHON_BIN" -X faulthandler -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
}

run_single_unittest_module() {
  local module_name=${1:-}

  [[ -n "$module_name" ]] || die "unit-module requires a Python unittest module path"
  require_existing_build_dir

  log "running unittest module: $module_name"
  PYTHONUNBUFFERED=1 "$PYTHON_BIN" -X faulthandler -m unittest "$module_name" -v
}

run_smoke() {
  log "running smoke import"
  "$PYTHON_BIN" tests/smoke_import.py
}

clean_build_dir() {
  if [[ -d "$BUILD_DIR_PATH" ]]; then
    warn "removing build directory: $BUILD_DIR_PATH"
    rm -rf "$BUILD_DIR_PATH"
  else
    warn "build directory does not exist, skipping clean: $BUILD_DIR_PATH"
  fi
}

main() {
  local command=${1:-}

  case "$command" in
    -h|--help|help|'')
      usage
      exit 0
      ;;
  esac

  activate_env

  case "$command" in
    full)
      run_configure
      run_build
      run_ctest_suite
      run_smoke
      ;;
    build-only)
      run_configure
      run_build
      ;;
    test-only)
      run_ctest_suite
      run_smoke
      ;;
    verbose-test)
      run_verbose_unittest_suite
      run_smoke
      ;;
    clean-full)
      clean_build_dir
      run_configure
      run_build
      run_ctest_suite
      run_smoke
      ;;
    unit-module)
      run_single_unittest_module "${2:-}"
      ;;
    *)
      usage
      die "unknown command: $command"
      ;;
  esac

  log "done: $command"
}

main "$@"