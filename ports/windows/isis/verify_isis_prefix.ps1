param([string]$Prefix)

. "$PSScriptRoot\common.ps1"

if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }
$Prefix = Resolve-FullPath $Prefix

$includeCandidates = @(
    (Join-Path $Prefix "include\isis")
    (Join-Path $Prefix "Library\include\isis")
)
$libCandidates = @(
    (Join-Path $Prefix "lib")
    (Join-Path $Prefix "Library\lib")
)
$runtimeCandidates = @(
    (Join-Path $Prefix "bin")
    (Join-Path $Prefix "lib")
    (Join-Path $Prefix "Library\bin")
    (Join-Path $Prefix "Library\lib")
)

$includeDir = $includeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$libDir = $libCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$runtimeDir = $runtimeCandidates |
    Where-Object { Test-Path (Join-Path $_ "isis.dll") } |
    Select-Object -First 1

if (-not $includeDir) { Fail "missing ISIS include directory under $Prefix" }
if (-not $libDir) { Fail "missing ISIS import library directory under $Prefix" }
if (-not $runtimeDir) { Fail "missing ISIS runtime DLL under $Prefix" }

$coreHeader = Join-Path $includeDir "Cube.h"
$coreLib = Join-Path $libDir "isis.lib"
$coreDll = Join-Path $runtimeDir "isis.dll"

if (-not (Test-Path $coreHeader)) { Fail "missing core header: $coreHeader" }
if (-not (Test-Path $coreLib)) { Fail "missing core import library: $coreLib" }
if (-not (Test-Path $coreDll)) { Fail "missing core runtime DLL: $coreDll" }

$cameraPlugin = @(
    (Join-Path $libDir "Camera.plugin")
    (Join-Path $runtimeDir "Camera.plugin")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cameraPlugin) {
    Fail "missing Camera.plugin under $libDir or $runtimeDir"
}

$python = $null
if ($env:CONDA_PREFIX) {
    $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
    if (Test-Path $condaPython) {
        $python = $condaPython
    }
}
if (-not $python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $python = $pythonCommand.Source
    }
}
if (-not $python) {
    Fail "unable to locate Python for ISIS DLL load check"
}

$originalPath = $env:PATH
$originalIsisRoot = $env:ISISROOT
$originalIsisPrefix = $env:ISIS_PREFIX
try {
    $env:ISISROOT = $Prefix
    $env:ISIS_PREFIX = $Prefix
    $pathEntries = @($runtimeDir, $libDir)
    if ($env:CONDA_PREFIX) {
        $pathEntries += @(
            (Join-Path $env:CONDA_PREFIX "Library\bin"),
            (Join-Path $env:CONDA_PREFIX "Library\lib"),
            (Join-Path $env:CONDA_PREFIX "Scripts")
        )
    }
    $env:PATH = (($pathEntries | Where-Object { Test-Path $_ }) + @($originalPath)) -join ";"
    $loadProbe = @"
import ctypes
ctypes.WinDLL(r"$coreDll")
"@
    $loadProbe | & $python -
    if ($LASTEXITCODE -ne 0) {
        Fail "ISIS runtime DLL failed to load: $coreDll"
    }
}
finally {
    $env:PATH = $originalPath
    if ($null -eq $originalIsisRoot) {
        Remove-Item Env:\ISISROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:ISISROOT = $originalIsisRoot
    }
    if ($null -eq $originalIsisPrefix) {
        Remove-Item Env:\ISIS_PREFIX -ErrorAction SilentlyContinue
    }
    else {
        $env:ISIS_PREFIX = $originalIsisPrefix
    }
}

Write-Step "ISIS prefix verified: $Prefix"
Write-Step "include: $includeDir"
Write-Step "lib: $libDir"
Write-Step "runtime: $runtimeDir"
