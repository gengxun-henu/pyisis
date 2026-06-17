param([string]$BuildDir)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if (-not (Test-Path $BuildDir)) {
    Fail "ISIS build directory not found: $BuildDir"
}

Write-Step "installing ISIS from $BuildDir"
Invoke-CheckedCommand cmake --install $BuildDir
