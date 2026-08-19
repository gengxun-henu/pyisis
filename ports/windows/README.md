# Windows Native Port

This directory contains the local Windows-native port workflow for pyisis and
the packaging workflow for the standalone ISIS native-application archive.

The SDK/runtime development workflow is intentionally local and prefix-driven:

1. Build and verify a Windows-native ISIS 9.0.0 SDK/runtime prefix.
2. Build and test pyisis against that prefix.

The default generated directories are under `build/windows/` so they are covered
by the repository's existing build artifact ignore rule:

- `build/windows/external/isis-9.0.0-src`
- `build/windows/isis-build`
- `build/windows/isis-prefix`
- `build/windows/pyisis-build`

The scripts accept explicit path parameters when a developer wants another
layout.

## Prerequisites

- Windows 10 or newer
- Visual Studio Build Tools with the MSVC C++ toolchain
- Conda, Mamba, or Micromamba
- Ninja and CMake from the active conda environment

Create the initial environment with a short prefix. Some conda-forge packages
used by ISIS, especially Qt and Bullet, contain deep include paths that can
exceed Windows path limits when extracted under this repository's worktree.

```powershell
$mambaRoot = "E:\code\pyisis-win-mamba-root"
$envPrefix = "E:\code\pyisis-win-env"
micromamba --root-prefix $mambaRoot create -y -p $envPrefix -f ports\windows\env\pyisis-isis-win64.yml
$env:CONDA_PREFIX = $envPrefix
$env:PATH = "$envPrefix;$envPrefix\Scripts;$envPrefix\Library\bin;$envPrefix\Library\usr\bin;$envPrefix\Library\mingw-w64\bin;$envPrefix\bin;$env:PATH"
```

Check that the shell is ready before configuring anything:

```powershell
.\ports\windows\check_prereqs.ps1
```

If `cl.exe` is missing, run these scripts from an x64 Native Tools prompt or
call Visual Studio's `vcvars64.bat` before continuing. The prerequisite checker
prints the detected `vcvars64.bat` path when Visual Studio Build Tools are
installed but not active in the current shell.

You can also load the detected MSVC environment into the current PowerShell
session with:

```powershell
.\ports\windows\activate_msvc.ps1
```

## Stage 1: ISIS Prefix

```powershell
.\ports\windows\isis\fetch_isis.ps1
.\ports\windows\isis\apply_patches.ps1
.\ports\windows\isis\configure_isis.ps1
.\ports\windows\isis\build_isis.ps1
.\ports\windows\isis\install_isis.ps1
.\ports\windows\isis\verify_isis_prefix.ps1
.\ports\windows\isis\test_isis_apps_smoke.ps1
```

`fetch_isis.ps1` defaults to a sparse Git checkout of the `9.0.0` tag
because this keeps the source patchable and avoids GitHub archive resume issues
seen on Windows. Use `-Method archive` when direct archive downloads are more
reliable on a given network.

`test_isis_apps_smoke.ps1` exercises a small representative command set against
the installed prefix: `stats`, `getkey`, `catlab`, `campt`, `reduce`,
`cam2map`, `isis2std`, `cubeit`, and `fx`. It writes command logs and generated
outputs under `build/windows/isis-command-smoke` by default. Pass
`-RunLroPipeline -LroRawImage <path>` to additionally smoke-test the LRO chain
`lronac2isis`, `spiceinit`, `lronaccal`, and `lronacecho` when a raw NAC image
is available.

### Launching installed ISIS applications

Directly launched CLI or GUI applications must inherit both the installed ISIS
prefix and the complete conda runtime search path. Do not add only
`Library\bin`: `isis.dll` loads `cspice.dll` from `%CONDA_PREFIX%\bin`.

```powershell
$env:CONDA_PREFIX = "D:\pyisis-win-env"
$env:ISISROOT = "$PWD\build\windows\isis-prefix"
$env:ISIS_PREFIX = $env:ISISROOT
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
$runtimePaths = @(
    "$env:ISISROOT\bin",
    "$env:ISISROOT\lib",
    "$env:CONDA_PREFIX\Library\bin",
    "$env:CONDA_PREFIX\Library\usr\bin",
    "$env:CONDA_PREFIX\Library\mingw-w64\bin",
    "$env:CONDA_PREFIX\Scripts",
    "$env:CONDA_PREFIX\bin",
    $env:CONDA_PREFIX
)
$env:PATH = (($runtimePaths | Where-Object { Test-Path $_ }) + @($env:PATH)) -join ";"

& "$env:ISISROOT\bin\reduce.exe" -gui
```

Use the same environment for other installed applications such as `jigsaw`.
For a loader error, use MSVC `dumpbin /DEPENDENTS` on the application and then
on `isis.dll` to identify the missing transitive DLL before modifying the build
or copying libraries.

## Stage 2: pyisis

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
$env:ISISROOT = $env:ISIS_PREFIX
.\ports\windows\pyisis\configure_pyisis.ps1
.\ports\windows\pyisis\build_pyisis.ps1
.\ports\windows\pyisis\test_pyisis_smoke.ps1
.\ports\windows\pyisis\test_pyisis_basic.ps1
```

The pyisis test scripts set `ISISROOT`, `ISISDATA`, `PYTHONPATH`, and the
runtime `PATH` for the current test process. The Python package also registers
Windows DLL search directories with `os.add_dll_directory` during import when
`ISISROOT`, `ISIS_PREFIX`, or `CONDA_PREFIX` are available.

The SDK/runtime prefix remains a developer input and is not the end-user
distribution. It does not promise every upstream ISIS application, production
`ISISDATA`, GitHub Actions, or conda packaging. The separately built native APP
archive below has its own fixed 151-APP contract.

## ISIS 9 Native APP Archive

The zero-install `usgs-isis-native-apps-9.0.0-win64.zip` product supports
Windows 11 x64. It contains exactly the 150 tracked ISIS 9 command-line APPs
from `isis/windows-app-manifest.json`, the `qnet` GUI, the private `isisui`
runtime helper, curated DLL and Qt plugin dependencies, package-relative
launchers, validation data, and repository-owned minimal ISISDATA. It is not a
PyISIS wheel, SDK, conda environment, complete upstream ISIS distribution, or
production mission-data bundle.

Build it from a verified ISIS 9 prefix in an MSVC x64 shell where `dumpbin` is
available. The dependency prefix can be repeated when more than one conda
runtime prefix is required:

```powershell
.\tools\packaging\build_windows_native_apps.ps1 `
  -PythonExecutable D:\pyisis-win-env\python.exe `
  -IsisPrefix build\windows\isis-prefix `
  -MinimalDataRoot packaging\isisdata-minimal\src\pyisis_isisdata_minimal\data `
  -OutputDir build\windows\native-apps-isis9 `
  -ReportDir build\windows\reports `
  -WorkDir build\windows\native-apps-isis9-work `
  -DependencyPrefix D:\pyisis-win-env
```

The successful build retains only these release outputs:

- `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64.zip`
- `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json`
- `build/windows/reports/isis-native-apps-9.0.0-win64-validation.json`

The dependency report records the recursive PE closure and must have no
unresolved non-system DLLs. The validation report binds the archive and runtime
evidence hashes and records the exact 151-APP inventory, Windows 11 x64 host,
150 CLI startup probes, three GUI probes, real operations, and zero failures or
skips. On success the guarded orchestrator removes only its verified
`build/windows/native-apps-isis9-work` directory; on failure it preserves the
work directory and logs for diagnosis. Do not delete the retained ZIP or JSON
reports when cleaning disposable build trees.

End users extract the archive to any writable path, including a path with
spaces, and launch only through the package-relative wrappers:

```powershell
Expand-Archive .\usgs-isis-native-apps-9.0.0-win64.zip -DestinationPath "C:\ISIS Apps"
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\isis-app.cmd" reduce -HELP
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\qnet.cmd"
$env:ISISDATA = "D:\isisdata"
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\isis-shell.cmd"
```

The bundled minimal ISISDATA is sufficient for packaged validation and basic
startup. Set `ISISDATA` before launching to use a separately managed, complete
external ISIS data tree; an explicitly invalid path is rejected rather than
silently falling back to bundled data.
