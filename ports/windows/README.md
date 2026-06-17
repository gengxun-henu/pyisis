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
- Conda or Mamba
- Ninja and CMake from the active conda environment

Create the initial environment with:

```powershell
conda env create -f ports\windows\env\pyisis-isis-win64.yml
conda activate pyisis-isis-win64
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
.\ports\windows\isis\fetch_isis_900.ps1
.\ports\windows\isis\apply_patches.ps1
.\ports\windows\isis\configure_isis.ps1
.\ports\windows\isis\build_isis.ps1
.\ports\windows\isis\install_isis.ps1
.\ports\windows\isis\verify_isis_prefix.ps1
```

`fetch_isis_900.ps1` defaults to downloading the `9.0.0` `tar.gz` source
archive and initializing a local git worktree for patch application. Use
`-ArchiveFormat zip` when a zip archive is preferred. Use `-Method git` only
when a direct shallow clone is preferred and the network is stable enough for
GitHub clone traffic.

## Stage 2: pyisis

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
.\ports\windows\pyisis\configure_pyisis.ps1
.\ports\windows\pyisis\build_pyisis.ps1
.\ports\windows\pyisis\test_pyisis_smoke.ps1
.\ports\windows\pyisis\test_pyisis_basic.ps1
```

The first milestone does not promise full ISIS CLI support, production
`ISISDATA`, GitHub Actions, or conda packaging.
