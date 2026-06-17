param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$BuildType = "Release",
    [string]$PythonExecutable
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

$repoRoot = Get-RepoRoot
if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix

if (-not $PythonExecutable) {
    $PythonExecutable = (Get-Command python).Source
}

Write-Step "configuring pyisis"
Invoke-CheckedCommand cmake -S $repoRoot -B $BuildDir -G Ninja `
    -DCMAKE_BUILD_TYPE=$BuildType `
    -DPython3_EXECUTABLE=$PythonExecutable `
    -DISIS_PREFIX=$IsisPrefix `
    -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
