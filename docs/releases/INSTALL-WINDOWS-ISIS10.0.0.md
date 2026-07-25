# Install PyISIS v1.4.0rc2 for ISIS 10 on Windows x64

## Requirements

- 64-bit Windows
- CPython 3.13
- the extracted Windows wheelhouse archive for USGS ISIS 10.0.0

## Install

Open PowerShell in the extracted archive directory:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse usgs-pyisis-isis10==1.4.0rc2
```

Do not install `usgs-pyisis` (the ISIS 9 line) in this environment.

## Verify

```powershell
python -c "import pyisis, isis_pybind as ip; print(ip.__version__, ip.__isis_version__); print(pyisis.data_status().message)"
```

The expected output starts with `1.4.0rc2 10.0.0`.

## Real mission data

The installed minimal ISISDATA tree is only for import and smoke checks. Set
`ISISDATA` to a complete external data tree before real camera, SPICE,
calibration, or mission processing:

```powershell
$env:ISISDATA = "D:\isisdata"
```
