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
