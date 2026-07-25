# Install PyISIS v1.3.0rc2 on Linux x86_64

## Requirements

- x86_64 Linux compatible with `manylinux_2_35`
- CPython 3.12
- the extracted Linux wheelhouse archive for USGS ISIS 9.0.0

The release is clean-install tested on Ubuntu 22.04 and Ubuntu 24.04.

## Install

Run these commands in the extracted archive directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse usgs-pyisis==1.3.0rc2
```

## Verify

```bash
python -c "import pyisis, isis_pybind as ip; print(ip.__version__); print(pyisis.data_status().message)"
```

The expected binding version is `1.3.0rc2`.

## Real mission data

The installed minimal ISISDATA tree is only for import and smoke checks. Point
`ISISDATA` to a complete external data tree before real camera, SPICE,
calibration, or mission processing:

```bash
export ISISDATA=/path/to/isisdata
```

Persist the value in your environment configuration if required.
