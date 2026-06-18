# pyisis conda recipe

This directory contains the first conda-build recipe for `pyisis`. It builds
the local repository with CMake and installs both Python packages:

- `pyisis`, the high-level Python facade.
- `isis_pybind`, including the compiled `_isis_core` extension.

## Local Windows build

The current Windows port keeps the ISIS runtime in a separate prefix from the
conda dependency environment. Set both paths before invoking `conda build`:

```powershell
$env:ISIS_PREFIX = (Resolve-Path build\windows\isis-prefix).Path
$env:PYISIS_DEP_PREFIX = 'E:\code\pyisis-win-env'
$env:ISISDATA = (Resolve-Path build\windows\testdata\isisdata-overlay).Path
conda build recipe --no-anaconda-upload
```

`ISIS_PREFIX` must contain the ISIS headers, libraries, `isis.dll`, and
`Camera.plugin`. `PYISIS_DEP_PREFIX` should point at the conda environment that
contains Python, Qt, CSPICE, Bullet, Eigen, pybind11, CMake, and Ninja.
conda-build provides `SP_DIR`; the build scripts pass it into CMake so the
Python files are installed into the package prefix instead of the build-time
Python environment.

## Linux build

For the existing Linux conda environment, `ISIS_PREFIX` and
`PYISIS_DEP_PREFIX` can usually point at the same environment:

```bash
export ISIS_PREFIX="$CONDA_PREFIX"
export PYISIS_DEP_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
conda build recipe --no-anaconda-upload
```

## Runtime note

This recipe is intentionally a local/private-channel bootstrap recipe. It does
not bundle the full ISIS runtime into the `pyisis` package yet. For a fully
self-contained channel, publish ISIS itself as a conda package first, then add
that package as a normal host/run dependency here.
