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
$binCandidates = @(
    (Join-Path $Prefix "bin")
    (Join-Path $Prefix "Library\bin")
)

$includeDir = $includeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$libDir = $libCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$binDir = $binCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $includeDir) { Fail "missing ISIS include directory under $Prefix" }
if (-not $libDir) { Fail "missing ISIS import library directory under $Prefix" }
if (-not $binDir) { Fail "missing ISIS runtime DLL directory under $Prefix" }

$coreHeader = Join-Path $includeDir "Cube.h"
$coreLib = Join-Path $libDir "isis.lib"
$coreDll = Join-Path $binDir "isis.dll"

if (-not (Test-Path $coreHeader)) { Fail "missing core header: $coreHeader" }
if (-not (Test-Path $coreLib)) { Fail "missing core import library: $coreLib" }
if (-not (Test-Path $coreDll)) { Fail "missing core runtime DLL: $coreDll" }

$cameraPlugin = @(
    Join-Path $libDir "Camera.plugin",
    Join-Path $binDir "Camera.plugin"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cameraPlugin) {
    Fail "missing Camera.plugin under $libDir or $binDir"
}

Write-Step "ISIS prefix verified: $Prefix"
Write-Step "include: $includeDir"
Write-Step "lib: $libDir"
Write-Step "bin: $binDir"
