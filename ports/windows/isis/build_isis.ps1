param(
    [string]$BuildDir,
    [string]$Config = "Release",
    [string[]]$Targets,
    [int]$Jobs = [Math]::Min(24, [Environment]::ProcessorCount)
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if (-not (Test-Path $BuildDir)) {
    Fail "ISIS build directory not found: $BuildDir"
}

$cmakeArgs = @("--build", $BuildDir, "--config", $Config)
if ($Targets -and $Targets.Count -gt 0) {
    $cmakeArgs += @("--target") + $Targets
}
if ($Jobs -gt 0) {
    $cmakeArgs += @("--parallel", $Jobs)
}

Invoke-CheckedCommand cmake @cmakeArgs
