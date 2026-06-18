param(
    [string]$IsisPrefix = "$PWD\build\windows\isis-prefix",
    [string]$OutputDir = "$PWD\wheelhouse",
    [string]$PythonExecutable = "python",
    [string]$DependencyPrefix = $env:PYISIS_DEP_PREFIX
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

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

& $PythonExecutable -m pip install -U build scikit-build-core pybind11 wheel
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:ISIS_PREFIX = (Resolve-Path -LiteralPath $IsisPrefix).Path
$env:ISISROOT = $env:ISIS_PREFIX
$env:PYISIS_DEP_PREFIX = (Resolve-Path -LiteralPath $DependencyPrefix).Path

$RuntimeStageDir = Join-Path $PWD "build\packaging\pyisis-runtime-win64"
& $PythonExecutable tools\packaging\stage_runtime_win64.py `
    --isis-prefix $env:ISIS_PREFIX `
    --dependency-prefix $env:PYISIS_DEP_PREFIX `
    --stage-dir $RuntimeStageDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build $RuntimeStageDir --wheel --no-isolation --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$RuntimeAnyWheel = Get-ChildItem -LiteralPath $OutputDir -Filter "pyisis_runtime_win64-*-py3-none-any.whl" | Select-Object -First 1
if ($RuntimeAnyWheel) {
    & $PythonExecutable -m wheel tags --platform-tag win_amd64 --remove $RuntimeAnyWheel.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PythonExecutable -m build packaging\isisdata-minimal --wheel --no-isolation --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build . --wheel --no-isolation --skip-dependency-check --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-ChildItem -LiteralPath $OutputDir -Filter "*.whl" | Sort-Object Name | ForEach-Object {
    Write-Host $_.FullName
}
