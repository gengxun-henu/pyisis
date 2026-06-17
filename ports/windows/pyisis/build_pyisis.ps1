param(
    [string]$BuildDir,
    [int]$Jobs = 0
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if (-not (Test-Path $BuildDir)) {
    Fail "pyisis build directory not found: $BuildDir"
}

if ($Jobs -gt 0) {
    Invoke-CheckedCommand cmake --build $BuildDir --parallel $Jobs
} else {
    Invoke-CheckedCommand cmake --build $BuildDir
}

$packageDir = Join-Path $BuildDir "python\isis_pybind"
$pyd = Get-ChildItem -Path $packageDir -Filter "_isis_core*.pyd" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pyd) {
    Fail "build completed but _isis_core*.pyd was not found under $packageDir"
}
Write-Step "built $($pyd.FullName)"
