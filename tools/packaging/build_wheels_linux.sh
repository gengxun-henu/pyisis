#!/usr/bin/env bash
set -euo pipefail

isis_prefix="${ISIS_PREFIX:-}"
output_dir="${OUTPUT_DIR:-"$PWD/wheelhouse"}"
python_executable="${PYTHON_EXECUTABLE:-python}"
dependency_prefix="${PYISIS_DEP_PREFIX:-${CONDA_PREFIX:-}}"
platform_tag="${PYISIS_LINUX_PLATFORM_TAG:-linux_x86_64}"
max_runtime_bytes="${PYISIS_MAX_LINUX_RUNTIME_BYTES:-650000000}"
max_runtime_wheel_bytes="${PYISIS_MAX_LINUX_RUNTIME_WHEEL_BYTES:-350000000}"

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
    --max-runtime-bytes)
      max_runtime_bytes="$2"
      shift 2
      ;;
    --max-runtime-wheel-bytes)
      max_runtime_wheel_bytes="$2"
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
  --max-runtime-bytes "$max_runtime_bytes" \
  --stage-dir "$runtime_stage_dir"

"$python_executable" -m build "$runtime_stage_dir" --wheel --no-isolation --outdir "$output_dir"

runtime_source_wheel="$("$python_executable" -c 'from pathlib import Path; import sys; wheels=sorted(Path(sys.argv[1]).glob("usgs_pyisis_runtime_linux_x86_64-*-py3-none-*.whl")); print(wheels[-1] if wheels else "")' "$output_dir")"
if [ -z "$runtime_source_wheel" ]; then
  echo "Linux runtime wheel was not produced." >&2
  exit 1
fi
if [[ "$runtime_source_wheel" != *-"$platform_tag".whl ]]; then
  "$python_executable" -m wheel tags \
    --platform-tag "$platform_tag" \
    --remove \
    "$runtime_source_wheel"
fi

runtime_wheel="$("$python_executable" -c 'from pathlib import Path; import sys; wheels=sorted(Path(sys.argv[1]).glob("usgs_pyisis_runtime_linux_x86_64-*.whl")); print(wheels[-1] if wheels else "")' "$output_dir")"
if [ -z "$runtime_wheel" ]; then
  echo "Linux runtime wheel was not produced." >&2
  exit 1
fi
runtime_wheel_bytes="$(stat -c %s "$runtime_wheel")"
if [ "$runtime_wheel_bytes" -gt "$max_runtime_wheel_bytes" ]; then
  echo "Linux runtime wheel exceeds its size budget: ${runtime_wheel_bytes} > ${max_runtime_wheel_bytes} bytes" >&2
  exit 1
fi

"$python_executable" -m build packaging/isisdata-minimal --wheel --no-isolation --outdir "$output_dir"
"$python_executable" -m build . --wheel --no-isolation --skip-dependency-check --outdir "$output_dir"

if [ "$platform_tag" != "linux_x86_64" ]; then
  extension_wheel="$("$python_executable" -c 'from pathlib import Path; import sys; wheels=sorted(Path(sys.argv[1]).glob("usgs_pyisis-*-linux_x86_64.whl")); print(wheels[-1] if wheels else "")' "$output_dir")"
  if [ -z "$extension_wheel" ]; then
    echo "Linux extension wheel was not produced." >&2
    exit 1
  fi
  "$python_executable" -m wheel tags \
    --platform-tag "$platform_tag" \
    --remove \
    "$extension_wheel"
fi

find "$output_dir" -maxdepth 1 -name "*.whl" -print | sort
