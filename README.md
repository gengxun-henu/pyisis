<div align="right">

[English](./README.md) | [简体中文](./README.zh-CN.md)

</div>

Welcome to the USGS ISIS Python Bindings (i.e., PyISIS)!
This project wraps the powerful USGS ISIS (v9.0.0) photogrammetric software, enabling seamless integration with Python for planetary image processing.

🛠️ Installation: You can easily install the USGS ISIS package using Conda or Mamba. For step-by-step instructions, please see the [Environment Setup Guide](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/installing-isis-via-anaconda/).

📚 Learning Resources: Processing planetary images with ISIS can be complex. We strongly suggest checking out the [Getting Started Guide](https://astrogeology.usgs.gov/docs/how-to-guides/image-processing/) to navigate the learning curve effectively.

# pyISIS / `isis_pybind_standalone`

This repository provides Python bindings for **USGS ISIS 9.0.0**, built with `pybind11`, and currently delivers the `isis_pybind` extension module primarily for Linux.

The scope of this repository is intentionally clear:

- use an **already installed ISIS environment** as the external SDK / runtime
- build the Python-importable extension module `isis_pybind._isis_core`
- expose Python access to APIs used in planetary remote sensing, photogrammetry, control networks, camera models, projections, and geometry processing

> The currently recommended distribution model is **GitHub Release + installation instructions + Linux build artifacts**.
> This is not the kind of project that can honestly be presented as a pure-Python “just `pip install` it” package; it depends on external ISIS, Qt, and related shared libraries.

## Supported scope

The current recommended and validated compatibility range is:

| Item | Current recommendation / validated range |
| --- | --- |
| Operating system | Linux x86_64 |
| Python | CPython 3.12 |
| ISIS | USGS ISIS 9.0.0 runtime / development environment |
| Distribution mode | GitHub Release, source build, installation into an active conda environment |
| Recommended as a direct PyPI first release | Not currently recommended |

## What this repository builds

After a successful build, the core Python package directory is:

- `build/python/isis_pybind/`

It typically contains:

- `build/python/isis_pybind/__init__.py`
- `build/python/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so`
- `build/python/isis_pybind/LICENSE`

The actual bound shared library is:

- `_isis_core.cpython-312-x86_64-linux-gnu.so`

However, **do not copy and use only the `.so` file by itself**. It should live inside the `isis_pybind/` package directory together with `__init__.py`.

## Install USGS ISIS first

This binding project does not install ISIS for you. You must first prepare a **working ISIS environment**, preferably managed with conda / mamba.

### Recommended approach

Prepare an environment that already contains the ISIS 9.0.0 runtime and development files, for example the locally used environment:

- `asp360_new`

This project assumes only that the environment provides:

- `${CONDA_PREFIX}/include/isis`
- `${CONDA_PREFIX}/lib/libisis.so`
- `${CONDA_PREFIX}/lib/Camera.plugin`

In other words, any ISIS environment that provides those pieces can be used to build this binding.

### Suggested ISIS installation path

1. Use the **official USGS ISIS / Astrogeology** installation approach, or a conda recipe already validated by your lab or team.
2. Activate that environment.
3. Confirm that the following key paths exist:
   - `include/isis`
   - `lib/libisis.so`
   - `lib/Camera.plugin`

If those three items are missing, this project cannot be configured and linked successfully.

### About `ISISDATA`

- Many real camera, time, and geometry workflows still require `ISISDATA` at runtime.
- The repository tests will try to fall back to `tests/data/isisdata/mockup/` as a minimal mock environment.
- But if you are processing your own real imagery and camera models, you should prefer a properly configured real `ISISDATA` setup.

## Installing this binding: recommended options

### Option A: build from source and install into the current Python environment

This is the **recommended** and most reliable installation method at the moment.

1. Activate the ISIS conda environment you have already prepared.
2. Use that environment as both:
   - the Python interpreter source
   - the ISIS headers / libraries source
3. Configure and build this repository.
4. Install it into the current environment's `site-packages` via `cmake --install`.

A standard workflow looks like this:

```bash
export ISIS_PREFIX="$CONDA_PREFIX"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX"
cmake --build build -j"$(nproc)"
cmake --install build
```

If you want to exclude ASP / VW camera libraries from the link step during configuration, enable the CMake option below:

```bash
cmake -S . -B build \
   -DCMAKE_BUILD_TYPE=Release \
   -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
   -DISIS_PREFIX="$ISIS_PREFIX" \
   -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
```

When `-DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON` is enabled, the build will exclude `libAsp*` and `libVw*` from the extra ISIS camera library link set while keeping the default behavior unchanged when the option is omitted or set to `OFF`.

After installation, `isis_pybind` will be copied into the current Python environment's `site-packages`.

### Option B: temporary use directly from the build tree

If you only want to develop, debug, or do a quick trial run, you can skip installation and use the package directly from the build tree:

```bash
export PYTHONPATH="$PWD/build/python${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind; print(isis_pybind.__file__)"
```

This is suitable for:

- local development
- quick smoke tests
- temporary validation of examples or unit tests

But it is not the recommended formal installation method for end users.

## Installing the shared library: what actually matters

In this project, the “generated binding shared library” is `isis_pybind/_isis_core*.so`.

### Recommended installation method

Prefer:

```bash
cmake --install build
```

Why:

- it installs `__init__.py` and `_isis_core*.so` together in the correct location
- it also includes `LICENSE`
- it avoids the easy-to-make situation where “the `.so` exists, but the Python package structure is incomplete”

### Manual installation method

If you download a **prebuilt binary artifact** from a GitHub Release, and that artifact already contains a complete package directory such as:

```text
isis_pybind/
  __init__.py
  _isis_core.cpython-312-x86_64-linux-gnu.so
  LICENSE
```

then you can copy the entire `isis_pybind/` directory into the target Python environment's `site-packages` directory.

> Copying only `_isis_core*.so` by itself is not recommended.

### Shared-library loading requirements

Even if the Python package itself is installed successfully, runtime loading still requires the target machine to resolve external dependencies such as:

- `libisis.so`
- Qt shared libraries
- required camera / projection / Bullet-related libraries

Therefore, **prebuilt binary artifacts are currently intended only for Linux users who already have a compatible ISIS environment**.

## How to verify the installation

At minimum, perform these three checks.

### 1. Verify that Python can import the package

```bash
python -c "import isis_pybind as ip; print(ip.__file__)"
```

### 2. Verify that the core extension is loaded

```bash
python -c "import isis_pybind as ip; print(hasattr(ip, 'Cube'), hasattr(ip, 'Camera'))"
```

### 3. Run the minimal smoke flow

```bash
python tests/smoke_import.py
```

If all three pass, that generally means:

- the `isis_pybind` package path is correct
- `_isis_core` can be loaded by Python
- the basic runtime dependencies are available

## Example: forward intersection

The repository already includes a ready-to-reference example:

- `examples/forward_intersection.py`
- usage guide: `examples/forward_intersection_usage.md`

This example demonstrates how to:

- open two ISIS cubes
- provide a left-image point
- automatically estimate / match the conjugate point in the right image
- call `Stereo.elevation(...)` to perform forward intersection

Example command using the repository's bundled test data:

```bash
python examples/forward_intersection.py \
  tests/data/mosrange/EN0108828322M_iof.cub \
  tests/data/mosrange/EN0108828327M_iof.cub \
  64.0 \
  512.0
```

If you want to run the example directly from the build tree, make sure Python can see the package under `build/python`, or install it first with `cmake --install build`.

## Unit tests: also useful as usage references

The tests in this repository are both regression checks and practical API usage references.

Key entry points include:

- `tests/smoke_import.py`: quick smoke validation
- `tests/unitTest/_unit_test_support.py`: shared test helpers and environment bootstrap logic
- `tests/unitTest/forward_intersection_example_test.py`: focused regression coverage for the forward-intersection example
- `tests/unitTest/`: detailed usage examples organized by class / module

### Run the full unit test suite

```bash
python -m unittest discover -s tests/unitTest -p "*_unit_test.py"
```

### Run the example-related test

```bash
python -m unittest tests.unitTest.forward_intersection_example_test
```

### Run via CTest

If you have already configured the project with CMake, you can also run:

```bash
ctest --output-on-failure -R python-unit-tests
```

## Release recommendations

A GitHub Release should ideally contain at least the following assets:

1. **Source package**
   - The repository source archive (`zip` / `tar.gz`) generated by GitHub is sufficient.
2. **Linux build artifact**
   - For example: `isis_pybind-linux-x86_64-cp312-isis9.0.0.tar.gz`
   - It should contain the full `isis_pybind/` package directory, not just a bare `.so` file.
3. **Installation instructions**
   - These can live in this README, on the Release page, or in a separate `INSTALL.md`.
4. **Version compatibility notes**
   - A version matrix for Linux / Python / ISIS.
5. **Checksum information**
   - `SHA256SUMS.txt`

### Recommended Release artifact naming

Include the following key information in the asset name:

- platform: `linux-x86_64`
- Python ABI: `cp312`
- ISIS version: `isis9.0.0`
- project version: for example `v1.0.0`

For example:

```text
isis_pybind-v1.0.0-linux-x86_64-cp312-isis9.0.0.tar.gz
SHA256SUMS.txt
```

## Checksum recommendations

When publishing binary artifacts, it is recommended to upload a checksum file as well:

```text
SHA256SUMS.txt
```

After downloading, users can run:

```bash
sha256sum -c SHA256SUMS.txt
```

This helps confirm that:

- the artifact is complete and not corrupted
- the download was not truncated
- the user received the exact build artifact you published

## Common issues

### 1. `import isis_pybind` fails, or `_isis_core` is missing

Check these first:

- whether the current Python is **CPython 3.12**
- whether `isis_pybind` is coming from the intended build or install environment
- whether an old `build/python` artifact is being picked up accidentally

### 2. `libisis.so` or another shared library cannot be found

This usually means:

- the target machine does not have a compatible ISIS environment installed
- or the current shell / Python runtime is not pointing to the correct conda environment

### 3. Examples or tests complain about `ISISDATA`

- For real workflows, configure a complete `ISISDATA`
- Repository tests will usually try `tests/data/isisdata/mockup/` automatically
- But not every real-world workflow can rely on mock data

### 4. Can this be supported as a normal `pip install` package?

At the moment, it is not recommended to describe this project as a normal pip-only package.

That is because it depends on:

- an external ISIS runtime
- Qt and other C++ shared libraries
- a specific Python ABI and system environment

So the more realistic distribution model right now is:

- GitHub Release
- source build
- or binary distribution for users who already have a compatible ISIS conda environment

## License

The binding-layer code and Python entry-point code authored in this repository are distributed under the:

- `MIT License`

See:

- `LICENSE`

Upstream ISIS source code, third-party dependencies, and external shared libraries remain under their respective licenses.
