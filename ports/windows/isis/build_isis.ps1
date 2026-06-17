param(
    [string]$BuildDir,
    [int]$Jobs = 0
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if (-not (Test-Path $BuildDir)) {
    Fail "ISIS build directory not found: $BuildDir"
}

if ($Jobs -gt 0) {
    Invoke-CheckedCommand cmake --build $BuildDir --parallel $Jobs
} else {
    Invoke-CheckedCommand cmake --build $BuildDir
}
