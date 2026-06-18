# pyisis Windows Build and Test

These scripts configure, build, and test pyisis against a Windows-native
`ISIS_PREFIX`.

Set `ISIS_PREFIX` before running the scripts:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
```

The scripts set `PYTHONPATH`, `ISIS_PREFIX`, `ISISROOT`, `ISISDATA`, and
`PATH` so Python can find the built pyisis package, ISIS can initialize its
runtime prefix, and Windows can find ISIS/Qt runtime DLLs.

The `isis_pybind` package also performs Windows import-time setup: if
`ISISROOT` is missing but `ISIS_PREFIX` is set, it assigns `ISISROOT` from
`ISIS_PREFIX`, then registers runtime DLL directories from `ISISROOT`,
`ISIS_PREFIX`, and `CONDA_PREFIX` with `os.add_dll_directory`.

Current local validation:

```powershell
.\ports\windows\pyisis\test_pyisis_smoke.ps1
.\ports\windows\pyisis\test_pyisis_basic.ps1
```
