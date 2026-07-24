# Windows Native Port

This directory contains the local Windows-native port workflow for pyisis.

The first milestone is intentionally local and prefix-driven:

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

The first milestone does not promise full ISIS CLI support, production
`ISISDATA`, GitHub Actions, or conda packaging.
