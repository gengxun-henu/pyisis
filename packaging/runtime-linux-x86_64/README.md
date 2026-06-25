# usgs-pyisis-runtime-linux-x86_64

This package contains the Linux x86_64 ISIS runtime files needed by
usgs-pyisis wheels. It is generated from a verified ISIS 9.0.0 Linux prefix and
intentionally excludes SDK headers, static libraries, CMake metadata, and local
build files.

The package exposes the same import module as the Windows runtime package:

```python
import pyisis_runtime

print(pyisis_runtime.prefix())
print(pyisis_runtime.dll_directories())
```

The main `usgs-pyisis` package depends on this package only on Linux x86_64 via
PEP 508 environment markers.
