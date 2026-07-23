# Optional OpenCV CUDA development dependency

The OpenCV CUDA build is an optional development dependency for GPU image
matching experiments. It is not part of the `isis_pybind` runtime, wheel, or
source release.

Do not commit OpenCV headers, libraries, build trees, or install prefixes to
this repository. These files are platform-specific and can be larger than the
binding source itself. In particular, a build made against one GLIBC or CUDA
toolchain is not portable to another Linux host.

## Reproducible build

Activate the `deep-learning` conda environment described in `AGENTS.md`, then
run:

```bash
tools/dev/build_opencv_cuda.sh
```

The helper checks out the OpenCV and `opencv_contrib` 4.14.0 release commits and
builds them under:

```text
${XDG_CACHE_HOME:-$HOME/.cache}/pyisis/opencv-cuda/4.14.0
```

The repository remains unchanged. Override the cache location or CUDA
architecture when necessary:

```bash
PYISIS_OPENCV_CUDA_ROOT=/path/to/cache/opencv-cuda/4.14.0 \
PYISIS_OPENCV_CUDA_ARCH=8.6 \
tools/dev/build_opencv_cuda.sh
```

After a successful build, prepend its Python directory:

```bash
export PYTHONPATH="${PYISIS_OPENCV_CUDA_ROOT:-$HOME/.cache/pyisis/opencv-cuda/4.14.0}/install/python:${PYTHONPATH:-}"
```

The legacy repository-local `.deps/opencv-cuda/` directory can remain on an
existing workstation as a local cache, but Git no longer tracks it. New builds
should use the external cache path above.

`.tmp_install/` is likewise a generated CMake install-staging directory. It is
already covered by the repository ignore rules and must not be committed.
