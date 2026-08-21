<div align="right">

[English](./README.md) | [简体中文](./README.zh-CN.md)

</div>

# PyISIS

Python bindings for selected, maintainable, non-GUI APIs from
[USGS ISIS](https://astrogeology.usgs.gov/docs/software/isis/). PyISIS supports
planetary image metadata, cubes, camera models, geometry, map projections,
control networks, and related photogrammetric workflows from Python.

The project has two Python layers:

- `pyisis`: the recommended high-level interface for most users.
- `isis_pybind`: direct access to the bound ISIS C++ APIs.

Binary releases are provided as downloadable wheelhouse archives. They are not
currently published to PyPI.

## Choose a release

Choose the ISIS line first, then download the archive for your operating
system. ISIS 9 and ISIS 10 use different Python ABIs and must be installed in
separate virtual environments.

| ISIS line | Release status | Python | Linux | Windows |
| --- | --- | --- | --- | --- |
| ISIS 9.0.0 | **Available:** [`v1.3.0rc3-isis9.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.3.0rc3-isis9.0.0) | CPython 3.12 | x86_64, `manylinux_2_35` | x64, `win_amd64` |
| ISIS 10.0.0 | **Available:** [`v1.4.0rc3-isis10.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.4.0rc3-isis10.0.0) | CPython 3.13 | x86_64, `manylinux_2_35` | x64, `win_amd64` |

Current platform validation targets:

- Linux: clean installs on Ubuntu 22.04 and Ubuntu 24.04.
- Windows: Windows Server 2022 / Windows x64.
- macOS, Linux ARM64, and Windows ARM64 are not currently release targets.

## Install ISIS 9.0.0

### 1. Download and extract a wheelhouse

Open the
[`v1.3.0rc3-isis9.0.0` release](https://github.com/gengxun-henu/pyisis/releases/tag/v1.3.0rc3-isis9.0.0)
and download exactly one platform archive:

- [Linux x86_64, CPython 3.12](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/pyisis-v1.3.0rc3-isis9.0.0-linux-x86_64-cp312-manylinux_2_35-wheelhouse.zip)
- [Windows x64, CPython 3.12](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/pyisis-v1.3.0rc3-isis9.0.0-windows-x64-cp312-wheelhouse.zip)
- [SHA256 checksums](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/SHA256SUMS.txt)

Extract the archive. The commands below assume the extracted directory contains
a `wheelhouse/` subdirectory.

### 2. Install on Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse \
  usgs-pyisis==1.3.0rc3
```

### 3. Install on Windows

Run in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse `
  usgs-pyisis==1.3.0rc3
```

If PowerShell activation is disabled by local policy, call the environment's
Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index `
  --find-links wheelhouse usgs-pyisis==1.3.0rc3
```

### 4. Verify the installation

```bash
python -c "import pyisis, isis_pybind as ip; print(ip.__version__, ip.__isis_version__); print(pyisis.data_status().message)"
```

The version line should report PyISIS `1.3.0rc3` and ISIS `9.0.0`.

Detailed instructions:

- [Linux / ISIS 9 installation](docs/releases/INSTALL-LINUX-ISIS9.0.0.md)
- [Windows / ISIS 9 installation](docs/releases/INSTALL-WINDOWS-ISIS9.0.0.md)
- [ISIS 9 release notes](docs/releases/v1.3.0rc3-isis9.0.0.md)

## Install ISIS 10.0.0

ISIS 10 support uses a separate distribution and Python ABI:

| Item | ISIS 10 release |
| --- | --- |
| Release tag | [`v1.4.0rc3-isis10.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.4.0rc3-isis10.0.0) |
| Top-level distribution | `usgs-pyisis-isis10` |
| Python | CPython 3.13 |
| Linux asset | [`pyisis-v1.4.0rc3-isis10.0.0-linux-x86_64-cp313-manylinux_2_35-wheelhouse.zip`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/pyisis-v1.4.0rc3-isis10.0.0-linux-x86_64-cp313-manylinux_2_35-wheelhouse.zip) |
| Windows asset | [`pyisis-v1.4.0rc3-isis10.0.0-windows-x64-cp313-wheelhouse.zip`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/pyisis-v1.4.0rc3-isis10.0.0-windows-x64-cp313-wheelhouse.zip) |

Download and extract the archive for your operating system. Installation from
the extracted wheelhouse uses the commands below. The release also provides
[`SHA256SUMS.txt`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/SHA256SUMS.txt).

Linux:

```bash
python3.13 -m venv .venv-isis10
source .venv-isis10/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse \
  usgs-pyisis-isis10==1.4.0rc3
```

Windows PowerShell:

```powershell
py -3.13 -m venv .venv-isis10
.\.venv-isis10\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse `
  usgs-pyisis-isis10==1.4.0rc3
```

The ISIS 10 package keeps the same import names:

```python
import pyisis
import isis_pybind
```

It includes a runtime-version guard so that an ISIS 10 binding is not silently
loaded with an ISIS 9 runtime. Do not install both release lines into the same
environment.

Planning and installation references:

- [ISIS 9/10 compatibility plan](docs/isis9-isis10-binding-compatibility-plan.md)
- [Linux / ISIS 10 installation](docs/releases/INSTALL-LINUX-ISIS10.0.0.md)
- [Windows / ISIS 10 installation](docs/releases/INSTALL-WINDOWS-ISIS10.0.0.md)
- [ISIS 10 release notes](docs/releases/v1.4.0rc3-isis10.0.0.md)

## ISISDATA

Each release wheelhouse includes only a small ISISDATA package for import and
smoke tests. Real camera, SPICE, radiometric calibration, and mission-specific
processing require a complete external ISISDATA installation.

Linux:

```bash
export ISISDATA=/path/to/isisdata
```

Windows PowerShell:

```powershell
$env:ISISDATA = "D:\isisdata"
```

The official ISIS installation and data guides remain the authority for
obtaining and maintaining a complete ISIS runtime/data environment:

- [Install ISIS](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/installing-isis-via-anaconda/)
- [ISIS data area](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/isis-data-area/)

## Basic use

Use the high-level facade for common work:

```python
import pyisis

with pyisis.open_cube("image.cub") as cube:
    print(pyisis.cube_dimensions(cube))
    print(pyisis.ground_at_center(cube))
```

Use the low-level package when direct access to a bound ISIS class is needed:

```python
import isis_pybind as ip

print("PyISIS:", ip.__version__)
print("Compiled for ISIS:", ip.__isis_version__)
```

Runnable examples are available under [`examples/`](examples/), including
camera geometry, forward intersection, map projections, control networks, and
image matching.

## What the binary releases contain

The release archive is an offline wheelhouse. Install the top-level
distribution as shown above; pip resolves the included local dependencies.

- Linux: the main binding wheel contains its audited shared-library runtime
  closure, plus a separate minimal ISISDATA wheel.
- Windows: the binding wheel, a separate ISIS runtime/dependency wheel, and a
  minimal ISISDATA wheel.

You do not need to select or install the dependency wheels individually.

Use the native ISIS `csv2table` application to attach CSV data as a typed ISIS
table:

```text
Linux:  csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
Windows portable archive: launch\isis-app.cmd csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
```

Python orchestration may use the standard library's `subprocess`, but PyISIS
publishes no `csv2table` helper or in-process binding.

## Scope and limitations

PyISIS is a curated Python interface, not a complete Python mirror of every
ISIS C++ class.

Included:

- Selected stable, non-GUI ISIS APIs.
- High-level Python helpers and direct low-level bindings.
- Linux and Windows binary wheelhouses for the release targets listed above.
- Tests and examples for supported binding workflows.

Not included:

- A complete ISISDATA archive.
- Every ISIS C++ class, Qt signal, slot, or GUI subsystem.
- The full native ISIS application suite on Windows.
- Native GUI applications such as `qview`, `qnet`, or `qmos`.

Linux users may install official ISIS separately when they need native command
line applications such as `cam2map`, `spiceinit`, or mission importers. Future
Windows-native ISIS APP work is a separate development track and is not part of
the current PyISIS wheel contract.

See [`docs/platform-support.md`](docs/platform-support.md) for the maintained
support boundary.

## Build from source

Source builds are intended for developers who already have a matching official
ISIS development environment. This repository uses conda for compilers and
dependencies; do not mix system compilers with conda ISIS libraries.

The active ISIS headers and libraries are the source of truth for signatures
and compile decisions. Start with the repository's
[`AGENTS.md`](AGENTS.md) build and validation commands, then use the installation
documents above for the target ISIS line and platform.

## Getting help

Open a [GitHub issue](https://github.com/gengxun-henu/pyisis/issues) and include:

- operating system and architecture;
- Python version;
- selected ISIS line and PyISIS version;
- the wheelhouse asset name or source commit;
- complete error output;
- whether a full `ISISDATA` tree is configured.

## License

Binding and Python code authored in this repository are distributed under the
[MIT License](LICENSE). USGS ISIS, bundled runtime dependencies, and external
data retain their respective licenses.
