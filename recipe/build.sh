#!/usr/bin/env bash
set -euo pipefail

: "${SRC_DIR:=$(pwd)}"
: "${PREFIX:?PREFIX is required by conda-build}"
: "${PYTHON:?PYTHON is required by conda-build}"
: "${ISIS_PREFIX:=${PREFIX}}"
: "${PYISIS_DEP_PREFIX:=${PREFIX}}"
: "${CPU_COUNT:=2}"

python_version="$("${PYTHON}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
: "${SP_DIR:=${PREFIX}/lib/python${python_version}/site-packages}"

require_path() {
  local description="$1"
  local path="$2"
  if [[ ! -e "${path}" ]]; then
    echo "Missing ${description}: ${path}" >&2
    exit 1
  fi
}

append_existing_dir() {
  local -n output_array="$1"
  shift
  local candidate
  for candidate in "$@"; do
    if [[ -d "${candidate}" ]]; then
      output_array+=("${candidate}")
    fi
  done
}

join_by_semicolon() {
  local IFS=";"
  echo "$*"
}

isis_include_dir="${ISIS_PREFIX}/include/isis"
isis_library_dir="${ISIS_PREFIX}/lib"
isis_runtime_dir="${ISIS_PREFIX}/lib"
isis_core_library="${isis_library_dir}/libisis.so"
isis_plugin_file="${isis_library_dir}/Camera.plugin"

require_path "ISIS include directory" "${isis_include_dir}"
require_path "ISIS library directory" "${isis_library_dir}"
require_path "ISIS core shared library" "${isis_core_library}"
require_path "ISIS Camera.plugin" "${isis_plugin_file}"

dep_include_dirs=()
dep_library_dirs=()
append_existing_dir dep_include_dirs \
  "${PYISIS_DEP_PREFIX}/include" \
  "${PYISIS_DEP_PREFIX}/Library/include" \
  "${ISIS_PREFIX}/include" \
  "${ISIS_PREFIX}/Library/include"
append_existing_dir dep_library_dirs \
  "${PYISIS_DEP_PREFIX}/lib" \
  "${PYISIS_DEP_PREFIX}/Library/lib" \
  "${ISIS_PREFIX}/lib" \
  "${ISIS_PREFIX}/Library/lib"

if [[ ${#dep_include_dirs[@]} -eq 0 ]]; then
  echo "No dependency include directories were found." >&2
  exit 1
fi
if [[ ${#dep_library_dirs[@]} -eq 0 ]]; then
  echo "No dependency library directories were found." >&2
  exit 1
fi

build_dir="${PYISIS_BUILD_DIR:-${SRC_DIR}/build-conda}"
cmake -S "${SRC_DIR}" -B "${build_dir}" -G Ninja ${CMAKE_ARGS:-} \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="${PYTHON}" \
  -DPYISIS_INSTALL_SITELIB="${SP_DIR}" \
  -DPYISIS_INSTALL_SITEARCH="${SP_DIR}" \
  -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
  -DCMAKE_PREFIX_PATH="${PYISIS_DEP_PREFIX};${ISIS_PREFIX}" \
  -DISIS_PREFIX="${ISIS_PREFIX}" \
  -DISIS_INCLUDE_DIR="${isis_include_dir}" \
  -DISIS_DEP_INCLUDE_DIR="${dep_include_dirs[0]}" \
  -DISIS_DEP_INCLUDE_DIRS="$(join_by_semicolon "${dep_include_dirs[@]}")" \
  -DISIS_LIBRARY_DIR="${isis_library_dir}" \
  -DISIS_DEP_LIBRARY_DIRS="$(join_by_semicolon "${dep_library_dirs[@]}")" \
  -DISIS_RUNTIME_DIR="${isis_runtime_dir}" \
  -DISIS_CORE_LIBRARY="${isis_core_library}" \
  -DISIS_PLUGIN_FILE="${isis_plugin_file}" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON

cmake --build "${build_dir}" --parallel "${CPU_COUNT}"
cmake --install "${build_dir}"
