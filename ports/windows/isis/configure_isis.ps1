param(
    [string]$SourceDir,
    [string]$BuildDir,
    [string]$Prefix,
    [string]$BuildType = "Release"
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

if (-not $SourceDir) { $SourceDir = Get-DefaultIsisSourceDir }
if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }

$SourceDir = Resolve-FullPath $SourceDir
$BuildDir = Resolve-FullPath $BuildDir
$Prefix = Resolve-FullPath $Prefix

if (-not (Test-Path $SourceDir)) {
    Fail "ISIS source directory not found: $SourceDir"
}

Write-Step "configuring ISIS"
Invoke-CheckedCommand cmake -S $SourceDir -B $BuildDir -G Ninja `
    -DCMAKE_BUILD_TYPE=$BuildType `
    -DCMAKE_INSTALL_PREFIX=$Prefix `
    -DCMAKE_PREFIX_PATH=$env:CONDA_PREFIX
