param(
    [string]$Wheelhouse = "$PWD\wheelhouse",
    [string]$PythonExecutable = "python",
    [ValidateSet("testpypi")]
    [string]$Repository = "testpypi",
    [string]$ExpectedVersion = "1.3.0rc2",
    [string]$DistributionName = "usgs-pyisis",
    [string]$RuntimeDistribution = "usgs-pyisis-runtime-win64",
    [string]$PythonTag = "cp312-cp312",
    [string]$IsisDataVersion = "",
    [switch]$CheckOnly,
    [switch]$Upload
)

$ErrorActionPreference = "Stop"

if ($CheckOnly -and $Upload) {
    throw "Use either -CheckOnly or -Upload, not both."
}

if ($Upload -and -not $PSBoundParameters.ContainsKey("Wheelhouse")) {
    throw "Uploading requires an explicit -Wheelhouse path to avoid publishing stale local wheels."
}

if (-not (Test-Path -LiteralPath $Wheelhouse)) {
    throw "Wheelhouse not found: $Wheelhouse"
}

$Wheels = Get-ChildItem -LiteralPath $Wheelhouse -Filter "*.whl" | Sort-Object Name
if (-not $Wheels) {
    throw "No wheel files found in: $Wheelhouse"
}

$BindingWheelPrefix = $DistributionName.Replace("-", "_")
$RuntimeWheelPrefix = $RuntimeDistribution.Replace("-", "_")
if (-not $IsisDataVersion) {
    $IsisDataVersion = $ExpectedVersion
}
$ExpectedWheelNames = @(
    "$BindingWheelPrefix-$ExpectedVersion-$PythonTag-win_amd64.whl",
    "$RuntimeWheelPrefix-$ExpectedVersion-py3-none-win_amd64.whl",
    "usgs_pyisis_isisdata_minimal-$IsisDataVersion-py3-none-any.whl"
)
$ActualWheelNames = @($Wheels | ForEach-Object { $_.Name })
$MissingWheelNames = @($ExpectedWheelNames | Where-Object { $_ -notin $ActualWheelNames })
$UnexpectedWheelNames = @($ActualWheelNames | Where-Object { $_ -notin $ExpectedWheelNames })
if ($MissingWheelNames -or $UnexpectedWheelNames) {
    throw (
        "Wheelhouse does not match expected $DistributionName $ExpectedVersion wheel set. " +
        "Missing: $($MissingWheelNames -join ', '); " +
        "Unexpected: $($UnexpectedWheelNames -join ', ')"
    )
}
$WheelPaths = @($Wheels | ForEach-Object { $_.FullName })

& $PythonExecutable -m pip install -U twine
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m twine check @WheelPaths
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Upload) {
    Write-Host "Upload switch was not set; completed twine check only."
    $Wheels | ForEach-Object { Write-Host $_.FullName }
    exit 0
}

if ($Repository -eq "testpypi" -and $env:TESTPYPI_API_TOKEN -and -not $env:TWINE_PASSWORD) {
    $env:TWINE_USERNAME = "__token__"
    $env:TWINE_PASSWORD = $env:TESTPYPI_API_TOKEN
}

& $PythonExecutable -m twine upload --repository $Repository @WheelPaths
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
