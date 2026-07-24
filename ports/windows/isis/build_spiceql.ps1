param(
    [string]$SourceDir,
    [string]$BuildDir,
    [string]$Prefix = $env:CONDA_PREFIX,
    [string]$Repository = "https://github.com/DOI-USGS/SpiceQL.git",
    [string]$Ref = "1.4.1",
    [int]$Jobs = 2,
    [switch]$Force
)

. "$PSScriptRoot\common.ps1"

Require-Command git
Require-Command cmake
Require-Command ninja
Require-Command dumpbin

$repoRoot = Get-RepoRoot
if (-not $SourceDir) {
    $SourceDir = Join-Path $repoRoot "build\windows\external\spiceql-$Ref-src"
}
if (-not $BuildDir) {
    $BuildDir = Join-Path $repoRoot "build\windows\spiceql-$Ref-build"
}
if (-not $Prefix) {
    Fail "SpiceQL install prefix is not set; activate the Windows conda environment"
}

$SourceDir = Resolve-FullPath $SourceDir
$BuildDir = Resolve-FullPath $BuildDir
$Prefix = Resolve-FullPath $Prefix

if ((Test-Path $SourceDir) -and $Force) {
    Write-Step "removing existing SpiceQL source directory: $SourceDir"
    Remove-Item -LiteralPath $SourceDir -Recurse -Force
}
if ((Test-Path $BuildDir) -and $Force) {
    Write-Step "removing existing SpiceQL build directory: $BuildDir"
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}

if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    Write-Step "cloning SpiceQL $Ref"
    Invoke-CheckedCommand git clone `
        --branch $Ref `
        --single-branch `
        --depth 1 `
        --recurse-submodules `
        --shallow-submodules `
        $Repository `
        $SourceDir
}

$patchDir = Join-Path $PSScriptRoot "patches\spiceql-$Ref"
if (Test-Path $patchDir) {
    $patches = Get-ChildItem -LiteralPath $patchDir -Filter "*.patch" -File |
        Sort-Object Name
    foreach ($patch in $patches) {
        & git -C $SourceDir apply --unidiff-zero --reverse --check $patch.FullName 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Step "SpiceQL patch already applied: $($patch.Name)"
            continue
        }
        Write-Step "applying SpiceQL patch: $($patch.Name)"
        Invoke-CheckedCommand git -C $SourceDir apply --unidiff-zero --check $patch.FullName
        Invoke-CheckedCommand git -C $SourceDir apply --unidiff-zero $patch.FullName
    }
}

Write-Step "configuring SpiceQL $Ref"
Invoke-CheckedCommand cmake `
    -S $SourceDir `
    -B $BuildDir `
    -G Ninja `
    "-DCMAKE_BUILD_TYPE=Release" `
    "-DCMAKE_INSTALL_PREFIX=$Prefix" `
    "-DCMAKE_PREFIX_PATH=$Prefix" `
    "-DSPICEQL_BUILD_DOCS=OFF" `
    "-DSPICEQL_BUILD_TESTS=OFF" `
    "-DSPICEQL_BUILD_BINDINGS=OFF"

Write-Step "building and installing SpiceQL $Ref"
Invoke-CheckedCommand cmake --build $BuildDir --parallel $Jobs
Invoke-CheckedCommand cmake --install $BuildDir

$spiceqlHeader = Join-Path $Prefix "include\SpiceQL\spiceql.h"
$spiceqlBinDir = Join-Path $Prefix "bin"
$spiceqlLibDir = Join-Path $Prefix "lib"
New-Item -ItemType Directory -Force -Path $spiceqlBinDir, $spiceqlLibDir | Out-Null

# SpiceQL only declares a CMake LIBRARY install destination. MSVC
# classifies the DLL and import library as RUNTIME and ARCHIVE artifacts, so
# copy those two generated files when the upstream install rule omits them.
$builtSpiceqlDll = Get-ChildItem -LiteralPath $BuildDir -Recurse -Filter "SpiceQL.dll" -File |
    Select-Object -First 1
$builtSpiceqlLib = Get-ChildItem -LiteralPath $BuildDir -Recurse -Filter "SpiceQL.lib" -File |
    Select-Object -First 1
if (-not $builtSpiceqlDll) {
    Fail "SpiceQL DLL was not produced under $BuildDir"
}
if (-not $builtSpiceqlLib) {
    Fail "SpiceQL import library was not produced under $BuildDir"
}

$spiceqlExports = & dumpbin /nologo /exports $builtSpiceqlDll.FullName
if ($LASTEXITCODE -ne 0) {
    Fail "dumpbin could not inspect SpiceQL exports"
}
if (-not ($spiceqlExports -match "strSclkToEt")) {
    Fail "SpiceQL DLL does not export strSclkToEt"
}

if ($builtSpiceqlDll) {
    Copy-Item -LiteralPath $builtSpiceqlDll.FullName -Destination $spiceqlBinDir -Force
}
if ($builtSpiceqlLib) {
    Copy-Item -LiteralPath $builtSpiceqlLib.FullName -Destination $spiceqlLibDir -Force
}

$spiceqlLibraryCandidates = @(
    (Join-Path $Prefix "Library\lib\SpiceQL.lib")
    (Join-Path $Prefix "lib\SpiceQL.lib")
)
$spiceqlLibrary = $spiceqlLibraryCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not (Test-Path $spiceqlHeader)) {
    Fail "SpiceQL header was not installed: $spiceqlHeader"
}
if (-not $spiceqlLibrary) {
    Fail "SpiceQL import library was not installed under $Prefix"
}

Write-Step "SpiceQL prefix verified: $Prefix"
