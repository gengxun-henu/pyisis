param(
    [string]$IsisPrefix = "$PWD\build\windows\isis-prefix",
    [string]$OutputDir = "$PWD\wheelhouse",
    [string]$PythonExecutable = "python",
    [string]$DependencyPrefix = $env:PYISIS_DEP_PREFIX,
    [string]$BindingProjectDir = ".",
    [string]$DistributionName = "usgs-pyisis",
    [string]$RuntimeDistribution = "usgs-pyisis-runtime-win64",
    [string]$PackageVersion = "1.3.0rc2"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $IsisPrefix)) {
    throw "ISIS prefix not found: $IsisPrefix"
}

if (-not $DependencyPrefix) {
    $DependencyPrefix = (& $PythonExecutable -c "import sys; print(sys.prefix)").Trim()
}
if (-not (Test-Path -LiteralPath $DependencyPrefix)) {
    throw "Dependency prefix not found: $DependencyPrefix"
}

$MsvcActivationScript = Join-Path $PWD "ports\windows\activate_msvc.ps1"
if (Test-Path -LiteralPath $MsvcActivationScript) {
    . $MsvcActivationScript
}

$BuildJobs = [Math]::Min(24, [Environment]::ProcessorCount)
$env:CMAKE_GENERATOR = "Ninja"
$env:CMAKE_BUILD_PARALLEL_LEVEL = "$BuildJobs"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

& $PythonExecutable -m pip install -U build scikit-build-core pybind11 "setuptools>=77" wheel
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:ISIS_PREFIX = (Resolve-Path -LiteralPath $IsisPrefix).Path
$env:ISISROOT = $env:ISIS_PREFIX
$env:PYISIS_DEP_PREFIX = (Resolve-Path -LiteralPath $DependencyPrefix).Path

$RuntimeStageDir = Join-Path $PWD "build\packaging\$RuntimeDistribution"
$DependencyReport = Join-Path $OutputDir "$RuntimeDistribution-dll-dependencies.json"
& $PythonExecutable tools\packaging\stage_runtime_win64.py `
    --isis-prefix $env:ISIS_PREFIX `
    --dependency-prefix $env:PYISIS_DEP_PREFIX `
    --dependency-copy-mode closure `
    --distribution-name $RuntimeDistribution `
    --package-version $PackageVersion `
    --dependency-report $DependencyReport `
    --stage-dir $RuntimeStageDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build $RuntimeStageDir --wheel --no-isolation --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$RuntimeWheelPrefix = $RuntimeDistribution.Replace("-", "_")
$RuntimeAnyWheel = Get-ChildItem -LiteralPath $OutputDir -Filter "$RuntimeWheelPrefix-*-py3-none-any.whl" | Select-Object -First 1
if ($RuntimeAnyWheel) {
    & $PythonExecutable -m wheel tags --platform-tag win_amd64 --remove $RuntimeAnyWheel.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PythonExecutable -m build packaging\isisdata-minimal --wheel --no-isolation --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build $BindingProjectDir --wheel --no-isolation --skip-dependency-check `
    --config-setting "build-dir=build/{wheel_tag}-ninja" --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$BindingWheelPrefix = $DistributionName.Replace("-", "_")
$BindingWheel = Get-ChildItem -LiteralPath $OutputDir -Filter "$BindingWheelPrefix-*-win_amd64.whl" |
    Select-Object -First 1
if (-not $BindingWheel) {
    throw "Binding wheel was not produced for distribution: $DistributionName"
}

Get-ChildItem -LiteralPath $OutputDir -Filter "*.whl" | Sort-Object Name | ForEach-Object {
    Write-Host $_.FullName
}
