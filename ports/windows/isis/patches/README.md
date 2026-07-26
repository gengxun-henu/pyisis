# ISIS Windows Patch Queue

Patch files in this directory are applied in lexical order by
`ports/windows/isis/apply_patches.ps1`.

Patch naming convention:

```text
0001-short-description.patch
0002-short-description.patch
```

Each patch should solve one explainable Windows porting issue, such as CMake
library naming, plugin discovery, path separators, or MSVC compile errors.
Keep patch context narrow so the queue can be rebased against ISIS 9.0.0 source
without mixing unrelated changes.

Current queue:

- `0001-detect-windows-os-version.patch`: teach the ISIS CMake utility how to
  report a Windows build host.
- `0002-windows-cmake-portability.patch`: make ISIS/SensorUtilities CMake work
  with MSVC, conda Windows `.lib` dependencies, optional unavailable libraries,
  CMake-native resource/plugin generation, and app MOC files that are already
  provided by `isis.dll`.
- `0003-windows-code-generation-commands.patch`: remove shell-only assumptions
  from UI, protobuf, and moc generation.
- `0004-windows-isis-core-msvc-portability.patch`: source-level MSVC fixes for
  POSIX APIs, variable-length arrays, Windows SDK macro collisions, optional
  unavailable components, DLL data access, and legacy mission app file IO.
- `0005-windows-lazy-geos-global-factory.patch`: avoid eager GEOS factory
  construction from the `PolygonTools.h` header during Windows DLL load.
- `0006-windows-pvl-binary-read.patch`: open PVL streams in binary mode so
  nested-object `tellg`/`seekg` positions remain stable on Windows.
- `0007-windows-blob-binary-read.patch`: open attached and detached blob streams
  in binary mode so table data offsets are byte-accurate on Windows.
- `0008-windows-cube-close-before-remove.patch`: close `Cube` QFile handles
  before removing cube files so `close(remove=True)` works on Windows.

The ISIS 10.0.0 queue is maintained separately under `patches/10.0.0/`.
Its `0003-Build-allowlisted-Windows-apps-as-executables.patch` adds independent
MSVC executable targets selected through `ISIS_WINDOWS_APP_ALLOWLIST`; it does
not restore all application implementations to the export-all runtime DLL.
The tracked manifest currently selects 89 APP targets through the complete W1
promotion plus the next 20-APP W2/W3 batch. The ISIS 10 `0004` patch restores
`BundleAdjust` only when `jigsaw` is allowlisted and keeps the `cnethist`
command-line path without restoring qisis plotting objects.
The ISIS 10 `0005` patch likewise keeps `hist` report generation available
while omitting its qisis-only interactive plotting path on MSVC.
