#!/usr/bin/env bash
set -euo pipefail

isis_prefix="${ISIS_PREFIX:-}"
output_dir="${OUTPUT_DIR:-"$PWD/wheelhouse"}"
python_executable="${PYTHON_EXECUTABLE:-python}"
dependency_prefix="${PYISIS_DEP_PREFIX:-${CONDA_PREFIX:-}}"
platform_tag="${PYISIS_LINUX_PLATFORM_TAG:-linux_x86_64}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --isis-prefix)
      isis_prefix="$2"
      shift 2
      ;;
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    --python-executable)
      python_executable="$2"
      shift 2
      ;;
    --dependency-prefix)
      dependency_prefix="$2"
      shift 2
      ;;
    --platform-tag)
      platform_tag="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$isis_prefix" ]; then
  echo "ISIS prefix is required; pass --isis-prefix or set ISIS_PREFIX." >&2
  exit 2
fi

if [ ! -d "$isis_prefix" ]; then
  echo "ISIS prefix not found: $isis_prefix" >&2
  exit 2
fi

if [ -z "$dependency_prefix" ]; then
  dependency_prefix="$isis_prefix"
fi

if [ ! -d "$dependency_prefix" ]; then
  echo "Dependency prefix not found: $dependency_prefix" >&2
  exit 2
fi

mkdir -p "$output_dir"

"$python_executable" -c "import build, pybind11, scikit_build_core, wheel"

export ISIS_PREFIX
ISIS_PREFIX="$(cd "$isis_prefix" && pwd)"
export ISISROOT="$ISIS_PREFIX"
export PYISIS_DEP_PREFIX
PYISIS_DEP_PREFIX="$(cd "$dependency_prefix" && pwd)"

runtime_stage_dir="$PWD/build/packaging/usgs-pyisis-runtime-linux-x86_64"
"$python_executable" tools/packaging/stage_runtime_linux.py \
  --isis-prefix "$ISIS_PREFIX" \
  --dependency-prefix "$PYISIS_DEP_PREFIX" \
  --dependency-copy-mode closure \
  --stage-dir "$runtime_stage_dir"

"$python_executable" -m build "$runtime_stage_dir" --wheel --no-isolation --outdir "$output_dir"

runtime_any_wheel="$(
  find "$output_dir" -maxdepth 1 -name "usgs_pyisis_runtime_linux_x86_64-*-py3-none-any.whl" -print -quit
)"
if [ -n "$runtime_any_wheel" ]; then
  "$python_executable" -m wheel tags \
    --platform-tag "$platform_tag" \
    --remove \
    "$runtime_any_wheel"
fi

"$python_executable" -m build packaging/isisdata-minimal --wheel --no-isolation --outdir "$output_dir"
"$python_executable" -m build . --wheel --no-isolation --skip-dependency-check --outdir "$output_dir"

find "$output_dir" -maxdepth 1 -name "*.whl" -print | sort
