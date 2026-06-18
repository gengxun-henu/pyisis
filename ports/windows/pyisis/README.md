# pyisis Windows Build and Test

These scripts configure, build, and test pyisis against a Windows-native
`ISIS_PREFIX`.

Set `ISIS_PREFIX` before running the scripts:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
```

The scripts set `PYTHONPATH`, `ISIS_PREFIX`, `ISISROOT`, `ISISDATA`, and
`PATH` so Python can find the built `pyisis` and `isis_pybind` packages, ISIS
can initialize its runtime prefix, and Windows can find ISIS/Qt runtime DLLs.

Application code should prefer the high-level facade:

```python
import pyisis

with pyisis.open_cube("image.cub") as cube:
    print(pyisis.cube_dimensions(cube))
    print(pyisis.ground_at_center(cube))
```

Use `import isis_pybind as ip` when direct low-level access to the bound ISIS
C++ API is required.

The `pyisis` facade and the lower-level `isis_pybind` package both register
runtime DLL directories from `ISISROOT`, `ISIS_PREFIX`, and `CONDA_PREFIX` with
`os.add_dll_directory`. The lower-level package also assigns `ISISROOT` from
`ISIS_PREFIX` during import when `ISISROOT` is missing.

Current local validation:

```powershell
.\ports\windows\pyisis\test_pyisis_smoke.ps1
.\ports\windows\pyisis\test_pyisis_basic.ps1
```
