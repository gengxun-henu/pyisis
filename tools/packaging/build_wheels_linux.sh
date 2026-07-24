#!/usr/bin/env bash
set -euo pipefail

isis_prefix="${ISIS_PREFIX:-}"
output_dir="${OUTPUT_DIR:-"$PWD/wheelhouse"}"
python_executable="${PYTHON_EXECUTABLE:-python}"
dependency_prefix="${PYISIS_DEP_PREFIX:-${CONDA_PREFIX:-}}"
platform_tag="${PYISIS_LINUX_PLATFORM_TAG:-linux_x86_64}"
max_runtime_bytes="${PYISIS_MAX_LINUX_RUNTIME_BYTES:-650000000}"
max_runtime_wheel_bytes="${PYISIS_MAX_LINUX_RUNTIME_WHEEL_BYTES:-350000000}"
binding_project_dir="${PYISIS_BINDING_PROJECT_DIR:-.}"
distribution_name="${PYISIS_DISTRIBUTION_NAME:-usgs-pyisis}"
runtime_distribution="${PYISIS_RUNTIME_DISTRIBUTION:-usgs-pyisis-runtime-linux-x86_64}"
package_version="${PYISIS_PACKAGE_VERSION:-1.3.0rc1}"
vendor_toolchain_runtime="${PYISIS_VENDOR_TOOLCHAIN_RUNTIME:-OFF}"

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
    --binding-project-dir)
      binding_project_dir="$2"
      shift 2
      ;;
    --distribution-name)
      distribution_name="$2"
      shift 2
      ;;
    --runtime-distribution)
      runtime_distribution="$2"
      shift 2
      ;;
    --package-version)
      package_version="$2"
      shift 2
      ;;
    --vendor-toolchain-runtime)
      vendor_toolchain_runtime="ON"
      shift
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

runtime_normalized="${runtime_distribution//-/_}"
distribution_normalized="${distribution_name//-/_}"
runtime_stage_dir="$PWD/build/packaging/$runtime_distribution"
"$python_executable" tools/packaging/stage_runtime_linux.py \
  --isis-prefix "$ISIS_PREFIX" \
  --dependency-prefix "$PYISIS_DEP_PREFIX" \
  --dependency-copy-mode closure \
  --max-runtime-bytes "$max_runtime_bytes" \
  --distribution-name "$runtime_distribution" \
  --package-version "$package_version" \
  --stage-dir "$runtime_stage_dir"

"$python_executable" -m build "$runtime_stage_dir" --wheel --no-isolation --outdir "$output_dir"

runtime_wheel="$("$python_executable" -c 'from pathlib import Path; import sys; wheels=sorted(Path(sys.argv[1]).glob(f"{sys.argv[2]}-*-py3-none-*.whl")); print(wheels[-1] if wheels else "")' "$output_dir" "$runtime_normalized")"
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
"$python_executable" -m build "$binding_project_dir" --wheel --no-isolation --skip-dependency-check --outdir "$output_dir"

extension_wheel="$("$python_executable" -c 'from pathlib import Path; import sys; wheels=sorted(Path(sys.argv[1]).glob(f"{sys.argv[2]}-*-linux_x86_64.whl")); print(wheels[-1] if wheels else "")' "$output_dir" "$distribution_normalized")"
if [ -z "$extension_wheel" ]; then
  echo "Linux extension wheel was not produced." >&2
  exit 1
fi

combined_dir="$PWD/build/packaging/linux-combined-wheel"
combined_wheel="$combined_dir/$(basename "$extension_wheel")"
"$python_executable" tools/packaging/build_linux_audit_bundle.py \
  --extension-wheel "$extension_wheel" \
  --runtime-wheel "$runtime_wheel" \
  --runtime-dependency "$runtime_distribution" \
  --output "$combined_wheel"

runtime_lib="$runtime_stage_dir/src/pyisis_runtime/vendor/isis/lib"
if [ "$vendor_toolchain_runtime" = "ON" ]; then
  "$python_executable" tools/packaging/vendor_linux_toolchain_runtime.py \
    --wheel "$combined_wheel"
fi
if [ "$platform_tag" = "linux_x86_64" ]; then
  "$python_executable" -c 'from pathlib import Path; import sys; Path(sys.argv[1]).unlink()' \
    "$extension_wheel"
  "$python_executable" -c 'from pathlib import Path; import sys; Path(sys.argv[1]).replace(Path(sys.argv[2]))' \
    "$combined_wheel" \
    "$output_dir/$(basename "$combined_wheel")"
else
  if [ "$vendor_toolchain_runtime" = "ON" ]; then
    retagged_wheel="$(
      cd "$combined_dir"
      "$python_executable" -m wheel tags \
        --platform-tag "$platform_tag" \
        --remove \
        "$(basename "$combined_wheel")"
    )"
    mv "$combined_dir/$retagged_wheel" "$output_dir/$retagged_wheel"
  else
    repair_library_path="$runtime_lib:$PYISIS_DEP_PREFIX/lib"
    LD_LIBRARY_PATH="$repair_library_path" auditwheel repair \
      --plat "$platform_tag" \
      --wheel-dir "$output_dir" \
      "$combined_wheel"
  fi
  "$python_executable" -c 'from pathlib import Path; import sys; Path(sys.argv[1]).unlink()' \
    "$extension_wheel"
fi

"$python_executable" -c 'from pathlib import Path; import sys; Path(sys.argv[1]).unlink()' \
  "$runtime_wheel"
"$python_executable" -c 'from pathlib import Path; import shutil, sys; shutil.rmtree(Path(sys.argv[1]))' \
  "$combined_dir"

find "$output_dir" -maxdepth 1 -name "*.whl" -print | sort
