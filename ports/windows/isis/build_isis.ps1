param(
    [string]$BuildDir,
    [string]$Config = "Release",
    [int]$Jobs = 1
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if (-not (Test-Path $BuildDir)) {
    Fail "ISIS build directory not found: $BuildDir"
}

$cmakeArgs = @("--build", $BuildDir, "--config", $Config)
if ($Jobs -gt 0) {
    $cmakeArgs += @("--parallel", $Jobs)
}

Invoke-CheckedCommand cmake @cmakeArgs
