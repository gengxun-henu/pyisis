# usgs-pyisis-runtime-win64

This package contains the Windows x64 runtime files needed by usgs-pyisis wheels.
It is generated from a verified ISIS 9.0.0 Windows prefix and intentionally
excludes SDK headers, import libraries, CMake metadata, and local build files.

The package exposes:

```python
import pyisis_runtime

print(pyisis_runtime.prefix())
print(pyisis_runtime.dll_directories())
```
