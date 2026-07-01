# OpenCV CUDA SIFT BF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CUDA-enabled OpenCV Python module for the `deep-learning` conda environment so the existing `SIFT+BF` CPU/GPU code path can use CUDA BF matching with minimal repository changes. OpenCV 4.x does not provide `cv2.cuda.SIFT_create`; GPU SIFT extraction is routed through LightGlue's pycolmap CUDA SIFT backend when `pycolmap` is available.

**Architecture:** Keep `asp360_new` unchanged. Build OpenCV and opencv_contrib from source into an isolated prefix under `.deps/opencv-cuda/install`, then activate it by prepending the generated Python package path to `PYTHONPATH` when running GPU SIFT experiments.

**Tech Stack:** conda `deep-learning`, CUDA nvcc, CMake, Ninja, OpenCV 4.x, opencv_contrib, Python 3.10, optional LightGlue + pycolmap CUDA SIFT.

---

### Task 1: Prepare Build Toolchain

**Files:**
- No repository source edits.

- [ ] **Step 1: Install missing build tools into `deep-learning`**

Run:
```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
conda install -y -c nvidia -c conda-forge cuda-nvcc cuda-cudart-dev cuda-libraries-dev ninja pkg-config
```

Expected: `nvcc --version` and `ninja --version` both print versions.

- [ ] **Step 2: Verify GPU and Python ABI**

Run:
```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
python - <<'PY'
import sys, sysconfig, torch
print(sys.executable)
print(sys.version.split()[0])
print(sysconfig.get_paths()["include"])
print(sysconfig.get_paths()["purelib"])
print(torch.cuda.get_device_name(0))
print(torch.cuda.get_device_capability(0))
PY
```

Expected: Python 3.10 path from `deep-learning`, RTX 5090 device, capability `(12, 0)`.

### Task 2: Download OpenCV Sources

**Files:**
- Create: `.deps/opencv-cuda/src/opencv`
- Create: `.deps/opencv-cuda/src/opencv_contrib`

- [ ] **Step 1: Clone OpenCV and contrib**

Run:
```bash
mkdir -p .deps/opencv-cuda/src
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv.git .deps/opencv-cuda/src/opencv
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv_contrib.git .deps/opencv-cuda/src/opencv_contrib
```

Expected: both source directories exist and `git -C <dir> rev-parse --short HEAD` prints revisions.

### Task 3: Configure and Build OpenCV CUDA

**Files:**
- Create: `.deps/opencv-cuda/build`
- Create: `.deps/opencv-cuda/install`

- [ ] **Step 1: Configure CMake**

Run:
```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
cmake -S .deps/opencv-cuda/src/opencv -B .deps/opencv-cuda/build -G Ninja \
  -D CMAKE_BUILD_TYPE=Release \
  -D CMAKE_INSTALL_PREFIX=$PWD/.deps/opencv-cuda/install \
  -D OPENCV_EXTRA_MODULES_PATH=$PWD/.deps/opencv-cuda/src/opencv_contrib/modules \
  -D PYTHON3_EXECUTABLE=$CONDA_PREFIX/bin/python \
  -D PYTHON3_INCLUDE_DIR=$CONDA_PREFIX/include/python3.10 \
  -D PYTHON3_PACKAGES_PATH=$PWD/.deps/opencv-cuda/install/python \
  -D WITH_CUDA=ON \
  -D CUDA_ARCH_BIN=12.0 \
  -D OPENCV_ENABLE_NONFREE=ON \
  -D BUILD_opencv_python3=ON \
  -D BUILD_opencv_python2=OFF \
  -D BUILD_TESTS=OFF \
  -D BUILD_PERF_TESTS=OFF \
  -D BUILD_EXAMPLES=OFF \
  -D BUILD_opencv_world=OFF
```

Expected: CMake summary includes CUDA enabled and Python 3 bindings.

- [ ] **Step 2: Build and install**

Run:
```bash
cmake --build .deps/opencv-cuda/build -j$(nproc)
cmake --install .deps/opencv-cuda/build
```

Expected: `cv2*.so` exists under `.deps/opencv-cuda/install/python`.

### Task 4: Verify CUDA SIFT BF

**Files:**
- No repository source edits.

- [ ] **Step 1: Import isolated OpenCV build**

Run:
```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
PYTHONPATH=$PWD/.deps/opencv-cuda/install/python:$PYTHONPATH python - <<'PY'
import cv2
print(cv2.__version__)
print(cv2.__file__)
print(cv2.cuda.getCudaEnabledDeviceCount())
print(hasattr(cv2.cuda, "SIFT_create"))
print(hasattr(cv2.cuda, "DescriptorMatcher_createBFMatcher"))
PY
```

Expected: CUDA device count is at least `1`, CUDA BFMatcher is `True`, CPU SIFT is `True`, and OpenCV CUDA SIFT is `False` because OpenCV 4.x does not expose it.

- [ ] **Step 2: Run one GPU SIFT BF smoke test**

Run:
```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
PYTHONPATH=$PWD/.deps/opencv-cuda/install/python:$PWD:$PYTHONPATH python - <<'PY'
import numpy as np
from examples.image_match import gpu_sift
left = (np.random.rand(512, 512) * 255).astype("uint8")
right = left.copy()
mask = np.full_like(left, 255)
result = gpu_sift.match_sift_pair(
    left, right,
    left_mask=mask,
    right_mask=mask,
    ratio_test=0.8,
    matcher_method="bf",
    sift_kwargs={"nfeatures": 500},
    use_gpu=True,
)
print(result.used_gpu, result.used_cpu_fallback, len(result.matches), result.failure_reason)
PY
```

Expected: `used_gpu` is `True` and `used_cpu_fallback` is `False` only when LightGlue's `pycolmap_cuda` SIFT backend is installed and reports CUDA support. Without `pycolmap`, the GPU BFMatcher is available but the SIFT+BF route correctly falls back to CPU extraction/matching.
