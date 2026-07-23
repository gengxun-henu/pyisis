# Install PyISIS v1.4.0rc1 for ISIS 10 on Linux x86_64

## Requirements

- x86_64 Linux compatible with `manylinux_2_35`
- CPython 3.13
- the extracted Linux wheelhouse archive for USGS ISIS 10.0.0

The release is clean-install tested on Ubuntu 22.04 and Ubuntu 24.04.

## Install

Run these commands in the extracted archive directory:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse \
  usgs-pyisis-isis10==1.4.0rc1
```

Do not install `usgs-pyisis` (the ISIS 9 line) in this environment.

## Verify

```bash
python -c "import pyisis, isis_pybind as ip; print(ip.__version__, ip.__isis_version__); print(pyisis.data_status().message)"
```

The expected output starts with `1.4.0rc1 10.0.0`.

## Real mission data

The installed minimal ISISDATA tree is only for import and smoke checks. Point
`ISISDATA` to a complete external data tree before real camera, SPICE,
calibration, or mission processing:

```bash
export ISISDATA=/path/to/isisdata
```
