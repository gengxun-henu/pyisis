# AGENTS.md

## Cursor Cloud specific instructions

### Environment overview

This is a C++/Python binding project (PyISIS) that wraps USGS ISIS 9.0.0 for planetary image processing.
The core deliverable is `isis_pybind._isis_core`, a pybind11 extension module.

All dependencies are managed via **conda** (not pip/npm). The conda environment is named `asp360_new`.

### Key paths after setup

- Conda: `$HOME/miniconda3/etc/profile.d/conda.sh`
- Environment: `asp360_new`
- Built module: `build/python/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so`
- Mock ISISDATA: `tests/data/isisdata/mockup`

### Build commands

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"

# Configure (only needed once or after CMakeLists.txt changes)
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"

# Build
cmake --build build -j$(nproc)
```

### Running tests

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"

# Smoke test (fast, ~1s)
python tests/smoke_import.py

# Individual test modules (recommended for iteration)
python -m unittest tests.unitTest.<module_name> -v

# Full suite (slow, ~5+ minutes across 84 test files)
python -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
```

### Gotchas

- The **system compiler** (`/usr/bin/c++`) cannot link against the conda environment's libstdc++. Always use the conda compiler (`x86_64-conda-linux-gnu-c++`) explicitly via `-DCMAKE_CXX_COMPILER`.
- The `build_test_smoke.sh` script hardcodes `/home/gengxun/miniconda3` as the conda path. Use the environment variables `PYISIS_CONDA_SH=$HOME/miniconda3/etc/profile.d/conda.sh` to override.
- The full unit test suite (84 files) takes several minutes. For quick validation, run `tests/smoke_import.py` or selected test modules.
- The forward intersection example at `examples/forward_intersection/forward_intersection.py` is the best "hello world" to verify the full stack works. Run with: `python examples/forward_intersection/forward_intersection.py tests/data/mosrange/EN0108828322M_iof.cub tests/data/mosrange/EN0108828327M_iof.cub 64.0 512.0`
- `ISISDATA` must be set before running tests. The mock data at `tests/data/isisdata/mockup` is sufficient for most tests.
- After rebuilding, no server restart is needed — the `.so` is loaded fresh each time Python imports `isis_pybind`.
