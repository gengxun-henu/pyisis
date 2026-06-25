param(
    [string]$SourceDir,
    [string]$BuildDir,
    [string]$Prefix,
    [string]$BuildType = "Release",
    [switch]$BuildTests,
    [switch]$BuildPythonBindings,
    [switch]$BuildDocs
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

function New-MsvcImportLibrary {
    param(
        [Parameter(Mandatory = $true)][string]$DllPath,
        [Parameter(Mandatory = $true)][string]$OutputDir
    )

    Require-Command dumpbin
    Require-Command lib

    if (-not (Test-Path $DllPath)) {
        Fail "DLL not found for import library generation: $DllPath"
    }

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $dllName = [System.IO.Path]::GetFileName($DllPath)
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($DllPath)
    $defPath = Join-Path $OutputDir "$baseName.def"
    $libPath = Join-Path $OutputDir "$baseName.lib"

    $exports = & dumpbin /nologo /exports $DllPath |
        ForEach-Object {
            if ($_ -match '^\s*\d+\s+[0-9A-Fa-f]+\s+(?:[0-9A-Fa-f]+)?\s+([^\s\(]+)') {
                $matches[1]
            }
        } |
        Where-Object { $_ -and $_ -ne "name" } |
        Sort-Object -Unique

    if (-not $exports -or $exports.Count -eq 0) {
        Fail "No exports found in $DllPath"
    }

    $defLines = @("LIBRARY `"$dllName`"", "EXPORTS") + $exports
    Set-Content -LiteralPath $defPath -Value $defLines -Encoding ASCII

    Invoke-CheckedCommand lib /nologo "/def:$defPath" "/machine:x64" "/out:$libPath" | Out-Null
    return $libPath
}

if (-not $SourceDir) { $SourceDir = Get-DefaultIsisSourceDir }
if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }

$SourceDir = Resolve-FullPath $SourceDir
$BuildDir = Resolve-FullPath $BuildDir
$Prefix = Resolve-FullPath $Prefix

if (-not (Test-Path $SourceDir)) {
    Fail "ISIS source directory not found: $SourceDir"
}
if (-not $env:CONDA_PREFIX) {
    Fail "CONDA_PREFIX is not set; activate the Windows conda environment before configuring ISIS"
}

$CMakeSourceDir = $SourceDir
if (-not (Test-Path (Join-Path $CMakeSourceDir "CMakeLists.txt"))) {
    $nestedSourceDir = Join-Path $SourceDir "isis"
    if (Test-Path (Join-Path $nestedSourceDir "CMakeLists.txt")) {
        $CMakeSourceDir = $nestedSourceDir
    } else {
        Fail "CMakeLists.txt not found in $SourceDir or $nestedSourceDir"
    }
}

Write-Step "configuring ISIS from $CMakeSourceDir"
$buildTestsValue = if ($BuildTests) { "ON" } else { "OFF" }
$pybindingsValue = if ($BuildPythonBindings) { "ON" } else { "OFF" }
$buildDocsValue = if ($BuildDocs) { "ON" } else { "OFF" }

$cmakeArgs = @(
    "-DCMAKE_BUILD_TYPE=$BuildType",
    "-DCMAKE_INSTALL_PREFIX=$Prefix",
    "-DCMAKE_PREFIX_PATH=$($env:CONDA_PREFIX)",
    "-DbuildTests=$buildTestsValue",
    "-Dpybindings=$pybindingsValue",
    "-DbuildDocs=$buildDocsValue"
)

$importLibDir = Join-Path $BuildDir "msvc-import-libs"
$blasLibrary = Join-Path $env:CONDA_PREFIX "Library\lib\libblas.lib"
$lapackLibrary = Join-Path $env:CONDA_PREFIX "Library\lib\liblapack.lib"
if (-not (Test-Path $blasLibrary)) {
    $blasDll = Join-Path $env:CONDA_PREFIX "Library\bin\libblas.dll"
    if (Test-Path $blasDll) {
        $blasLibrary = New-MsvcImportLibrary -DllPath $blasDll -OutputDir $importLibDir
    }
}
if (-not (Test-Path $lapackLibrary)) {
    $lapackDll = Join-Path $env:CONDA_PREFIX "Library\bin\liblapack.dll"
    if (Test-Path $lapackDll) {
        $lapackLibrary = New-MsvcImportLibrary -DllPath $lapackDll -OutputDir $importLibDir
    }
}
if ((Test-Path $blasLibrary) -and (Test-Path $lapackLibrary)) {
    $cmakeBlasLibrary = $blasLibrary -replace "\\", "/"
    $cmakeLapackLibrary = $lapackLibrary -replace "\\", "/"
    $cmakeArgs += @(
        "-DBLAS_LIBRARY=$cmakeBlasLibrary",
        "-DLAPACK_LIBRARY=$cmakeLapackLibrary",
        "-DBLAS_LIBRARIES=$cmakeBlasLibrary",
        "-DLAPACK_LIBRARIES=$cmakeLapackLibrary"
    )
}

Invoke-CheckedCommand cmake -S $CMakeSourceDir -B $BuildDir -G Ninja @cmakeArgs
