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

## Windows wheelhouse

Build the ISIS 9 Windows wheelhouse from the verified local ISIS prefix:

```powershell
$env:CONDA_PREFIX = "D:\pyisis-win-env"
$env:PATH = "D:\pyisis-win-env;D:\pyisis-win-env\Scripts;D:\pyisis-win-env\Library\bin;D:\pyisis-win-env\Library\usr\bin;D:\pyisis-win-env\Library\mingw-w64\bin;D:\pyisis-win-env\bin;C:\Users\gx\miniconda3\Scripts;$env:PATH"
.\ports\windows\activate_msvc.ps1
& "D:\pyisis-win-env\python.exe" -c "import build, pybind11, scikit_build_core, wheel"
.\tools\packaging\build_wheels.ps1 `
  -IsisPrefix "$PWD\build\windows\isis-prefix" `
  -OutputDir "$PWD\build\windows\wheelhouse-isis9" `
  -PythonExecutable "D:\pyisis-win-env\python.exe" `
  -DependencyPrefix "D:\pyisis-win-env" `
  -BindingProjectDir "$PWD" `
  -PackageVersion "1.3.0rc2"
```

The wheelhouse contains these three wheels:

- `usgs_pyisis-1.3.0rc2-cp312-cp312-win_amd64.whl`
- `usgs_pyisis_runtime_win64-1.3.0rc2-py3-none-win_amd64.whl`
- `usgs_pyisis_isisdata_minimal-1.3.0rc2-py3-none-any.whl`

Verify a clean offline installation with:

```powershell
& "D:\pyisis-win-env\python.exe" tools\packaging\test_wheel_install.py `
  --wheelhouse "$PWD\build\windows\wheelhouse-isis9" `
  --venv "$PWD\build\windows\pyisis-wheel-install-venv-20260816" `
  --package "usgs-pyisis==1.3.0rc2" `
  --expected-isis-version "9.0.0" `
  --test-list tools\packaging\basic_tests.txt `
  --report "$PWD\build\windows\reports\pyisis-wheel-install-isis9.json"
```

The clean-install and final wheelhouse reports are:

- `build\windows\reports\pyisis-wheel-install-isis9.json`
- `build\windows\reports\pyisis-wheelhouse-isis9-validation.json`

The PyISIS wheelhouse does not contain standalone ISIS APP executables or APP XML. Native applications such as reduce, jigsaw, and qnet are distributed separately.
