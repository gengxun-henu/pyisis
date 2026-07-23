#!/usr/bin/env bash
#
# Build the optional CUDA-enabled OpenCV dependency outside the repository.

set -euo pipefail

readonly OPENCV_VERSION="4.14.0"
readonly OPENCV_COMMIT="0654a42e19215ef25b1d367d822f3c630447e7c7"
readonly OPENCV_CONTRIB_COMMIT="a8e9acd62cabd30419dba83007f2ac0d07de5e2c"

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "Activate the deep-learning conda environment before running this script." >&2
  exit 2
fi

readonly CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
readonly DEPENDENCY_ROOT="${PYISIS_OPENCV_CUDA_ROOT:-${CACHE_BASE}/pyisis/opencv-cuda/${OPENCV_VERSION}}"
readonly SOURCE_ROOT="${DEPENDENCY_ROOT}/src"
readonly BUILD_ROOT="${DEPENDENCY_ROOT}/build"
readonly INSTALL_ROOT="${DEPENDENCY_ROOT}/install"
readonly CUDA_ARCH="${PYISIS_OPENCV_CUDA_ARCH:-12.0}"
readonly BUILD_JOBS="${PYISIS_OPENCV_CUDA_JOBS:-$(nproc)}"

clone_pinned_source() {
  local repository="$1"
  local destination="$2"
  local expected_commit="$3"

  if [[ ! -d "${destination}/.git" ]]; then
    git clone \
      --depth 1 \
      --branch "${OPENCV_VERSION}" \
      "${repository}" \
      "${destination}"
  fi

  local actual_commit
  actual_commit="$(git -C "${destination}" rev-parse HEAD)"
  if [[ "${actual_commit}" != "${expected_commit}" ]]; then
    echo "${destination} is at ${actual_commit}; expected ${expected_commit}." >&2
    echo "Choose an empty PYISIS_OPENCV_CUDA_ROOT or remove that cache manually." >&2
    exit 2
  fi
}

mkdir -p "${SOURCE_ROOT}"
clone_pinned_source \
  "https://github.com/opencv/opencv.git" \
  "${SOURCE_ROOT}/opencv" \
  "${OPENCV_COMMIT}"
clone_pinned_source \
  "https://github.com/opencv/opencv_contrib.git" \
  "${SOURCE_ROOT}/opencv_contrib" \
  "${OPENCV_CONTRIB_COMMIT}"

readonly PYTHON_EXECUTABLE="${CONDA_PREFIX}/bin/python"
readonly PYTHON_INCLUDE_DIR="$(
  "${PYTHON_EXECUTABLE}" -c 'import sysconfig; print(sysconfig.get_path("include"))'
)"

cmake \
  -S "${SOURCE_ROOT}/opencv" \
  -B "${BUILD_ROOT}" \
  -G Ninja \
  -D CMAKE_BUILD_TYPE=Release \
  -D CMAKE_INSTALL_PREFIX="${INSTALL_ROOT}" \
  -D OPENCV_EXTRA_MODULES_PATH="${SOURCE_ROOT}/opencv_contrib/modules" \
  -D PYTHON3_EXECUTABLE="${PYTHON_EXECUTABLE}" \
  -D PYTHON3_INCLUDE_DIR="${PYTHON_INCLUDE_DIR}" \
  -D PYTHON3_PACKAGES_PATH="${INSTALL_ROOT}/python" \
  -D WITH_CUDA=ON \
  -D CUDA_ARCH_BIN="${CUDA_ARCH}" \
  -D OPENCV_ENABLE_NONFREE=ON \
  -D BUILD_opencv_python3=ON \
  -D BUILD_opencv_python2=OFF \
  -D BUILD_TESTS=OFF \
  -D BUILD_PERF_TESTS=OFF \
  -D BUILD_EXAMPLES=OFF \
  -D BUILD_opencv_world=OFF

cmake --build "${BUILD_ROOT}" -j"${BUILD_JOBS}"
cmake --install "${BUILD_ROOT}"

echo "OpenCV CUDA ${OPENCV_VERSION} installed under ${INSTALL_ROOT}"
echo "Use: export PYTHONPATH=${INSTALL_ROOT}/python:\${PYTHONPATH:-}"
