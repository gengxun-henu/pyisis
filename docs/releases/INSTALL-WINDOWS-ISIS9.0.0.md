# Install PyISIS v1.3.0rc2 on Windows x64

## Requirements

- 64-bit Windows
- CPython 3.12
- the extracted Windows wheelhouse archive for USGS ISIS 9.0.0

## Install

Open PowerShell in the extracted archive directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse usgs-pyisis==1.3.0rc2
```

## Verify

```powershell
python -c "import pyisis, isis_pybind as ip; print(ip.__version__); print(pyisis.data_status().message)"
```

The expected binding version is `1.3.0rc2`.

## Real mission data

The installed minimal ISISDATA tree is only for import and smoke checks. Set
`ISISDATA` to a complete external data tree before real camera, SPICE,
calibration, or mission processing:

```powershell
$env:ISISDATA = "D:\isisdata"
```

To make the value permanent, configure it through your normal Windows
environment-management process rather than editing the installed wheel.
