# isis_pybind_standalone

Standalone `pybind11` bindings for selected ISIS C++ APIs.

## License

The binding glue code, Python package entrypoint, and other project-specific
source files under `isis_pybind_standalone/` are released under the
`MIT` License. See [`LICENSE`](./LICENSE).

This standalone license applies to the authored binding layer in this
subproject. It does **not** change the license of upstream ISIS source code,
linked ISIS shared libraries, or other third-party dependencies used at build
or runtime. Those components remain under their respective licenses, including
the top-level ISIS `CC0-1.0` / public-domain dedication described in
[`../LICENSE.md`](../LICENSE.md).

For newly added binding sources, use the concise file header style:

```cpp
// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
```

This project is intentionally **not** added to the main ISIS CMake build. It treats an existing ISIS installation (for example the `asp360_new` conda environment) as an external SDK/runtime and only builds the Python extension module.

## What it uses from external ISIS

- headers: `${ISIS_PREFIX}/include/isis`
- core library: `${ISIS_PREFIX}/lib/libisis.so`
- plugin file: `${ISIS_PREFIX}/lib/Camera.plugin`
- optional camera libraries: `${ISIS_PREFIX}/lib/libIdealCamera.so`, `${ISIS_PREFIX}/lib/libVimsCamera.so`

## Build in a separate environment

You can compile this project in a different conda environment from the one that contains ISIS, as long as:

1. the compiler / C++ runtime ABI is compatible,
2. `pybind11` and Python development files are available in the build environment,
3. `ISIS_PREFIX` points at the external ISIS environment.

Example:

```bash
conda activate <pybind-build-env>
cmake -S isis_pybind_standalone -B isis_pybind_standalone/build \
  -DISIS_PREFIX=/home/gengxun/miniconda3/envs/asp360_new
cmake --build isis_pybind_standalone/build -j8
```

The built package appears under:

- `isis_pybind_standalone/build/python/isis_pybind/`

The build-tree package now also carries:

- `isis_pybind_standalone/build/python/isis_pybind/LICENSE`

## Additional project docs

- `pyisis-发布前检查清单.md` — release-oriented checklist for ABI, install, runtime dependency, and packaging validation.
- `pyisis-开发测试指标原则.md` — longer-form engineering guidance for testing layers, release strategy, and compatibility expectations.
- `testing.md` — focused testing guidance for smoke tests, unit tests, install validation, environment-aware skips, and coverage planning.
- `packaging.md` — packaging and release guidance for conda strategy, ABI/runtime validation, and user-facing distribution choices.

## How Python finds the module

The build step only creates the package under the build tree. It does **not** automatically place `isis_pybind` into Python's normal import path.

That is why running this from `tests/` failed:

```bash
python smoke_import.py
```

Python only searched the current environment's standard `site-packages`, and `isis_pybind` was still sitting in:

- `isis_pybind_standalone/build/python/isis_pybind/`

### Option 1: temporary use from the build directory

Add the build package root to `PYTHONPATH`:

```bash
PYTHONPATH=isis_pybind_standalone/build/python python
```

Or run the smoke test directly; it now prepends `../build/python` automatically when available:

```bash
cd isis_pybind_standalone/tests
python smoke_import.py
```

## Python unitTest layout

To mirror the C++ `unitTest.cpp` style under `isis/src/base/objs`, the Python-side tests now live under:

- `isis_pybind_standalone/tests/unitTest/`

Each file is named after the bound ISIS class, for example:

- `angle_unit_test.py`
- `distance_unit_test.py`
- `latitude_unit_test.py`
- `longitude_unit_test.py`

These tests are written with Python's built-in `unittest` module so they can run without adding another test dependency.

Run them directly with:

```bash
cd isis_pybind_standalone
python -m unittest discover -s tests/unitTest -p '*_unit_test.py'
```

If you configured the project with CMake, the same suite is also registered with CTest:

```bash
cd isis_pybind_standalone/build
ctest --output-on-failure -R python-unit-tests
```

### Option 2: install into the active Python environment

This project already defines an install rule that copies the package into the active Python environment's `site-packages`.

The install step also places the standalone MIT `LICENSE` file inside the
installed `isis_pybind` package directory so redistributed install artifacts
carry the license text with them.

```bash
cmake --install isis_pybind_standalone/build
```

After that, a normal import works:

```bash
python -c "import isis_pybind; print(isis_pybind.__file__)"
```

To verify the installed package also carries the license file, you can run:

```bash
python -c "import pathlib, isis_pybind; print(pathlib.Path(isis_pybind.__file__).with_name('LICENSE'))"
```

If you are using a dedicated pybind build environment, install while that environment is active so the module lands in the correct interpreter's library path.

## Notes

- This standalone project currently mirrors the in-repo first-pass bindings: `Sensor`, `Camera`, `CameraFactory`, `Cube`, and a small hierarchy layer.
- It does **not** modify the main ISIS build.
- If you add more mission-specific camera class bindings later, add their corresponding shared libraries to `ISIS_CAMERA_LIBS` or extend the CMake logic.
