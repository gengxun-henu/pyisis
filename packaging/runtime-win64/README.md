# usgs-pyisis-runtime-win64

This package contains the minimal Windows x64 native runtime required by the
PyISIS binding wheel. It is generated from a verified ISIS prefix and includes
only the DLLs, plugins, configuration, and runtime resources needed to import
and use `isis_pybind`.

It intentionally excludes ISIS APP executables and APP XML. Native command-line
and GUI applications are built, tested, and released through the separate ISIS
Native Windows product line. It also excludes SDK headers, import libraries,
CMake metadata, and local build files.

The package exposes:

```python
import pyisis_runtime

print(pyisis_runtime.prefix())
print(pyisis_runtime.dll_directories())
```

## Dependency closure

The generated Windows runtime wheel includes the recursive closure of normal PE
imports and PE export-forwarder targets. Forwarder DLLs such as `libblas.dll`,
`libcblas.dll`, and `liblapack.dll` therefore also bring in their implementation
DLL, such as `openblas.dll`.
