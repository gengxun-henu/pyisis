param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$BuildType = "Release",
    [string]$PythonExecutable
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

function Convert-ToCMakePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return ($Path -replace "\\", "/")
}

function Select-FirstExistingPath {
    param([Parameter(Mandatory = $true)][string[]]$Candidates)
    return $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

function Select-FirstExistingFileInDir {
    param(
        [Parameter(Mandatory = $true)][string[]]$Directories,
        [Parameter(Mandatory = $true)][string]$FileName
    )
    foreach ($directory in $Directories) {
        if ($directory -and (Test-Path (Join-Path $directory $FileName))) {
            return $directory
        }
    }
    return $null
}

$repoRoot = Get-RepoRoot
if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix

if (-not $PythonExecutable) {
    $PythonExecutable = Get-DefaultPythonExecutable
}

$isisIncludeDir = Select-FirstExistingPath @(
    (Join-Path $IsisPrefix "Library\include\isis"),
    (Join-Path $IsisPrefix "include\isis")
)
$isisLibraryDir = Select-FirstExistingPath @(
    (Join-Path $IsisPrefix "Library\lib"),
    (Join-Path $IsisPrefix "lib")
)
$isisRuntimeDir = Select-FirstExistingFileInDir @(
    (Join-Path $IsisPrefix "Library\bin"),
    (Join-Path $IsisPrefix "Library\lib"),
    (Join-Path $IsisPrefix "bin"),
    (Join-Path $IsisPrefix "lib")
) "isis.dll"

if (-not $isisIncludeDir) { Fail "ISIS include directory was not found under $IsisPrefix" }
if (-not $isisLibraryDir) { Fail "ISIS library directory was not found under $IsisPrefix" }
if (-not $isisRuntimeDir) { Fail "ISIS runtime directory containing isis.dll was not found under $IsisPrefix" }

$isisCoreLibrary = Join-Path $isisLibraryDir "isis.lib"
$isisPluginFile = Select-FirstExistingPath @(
    (Join-Path $isisLibraryDir "Camera.plugin"),
    (Join-Path $isisRuntimeDir "Camera.plugin")
)
if (-not (Test-Path $isisCoreLibrary)) { Fail "ISIS core import library was not found: $isisCoreLibrary" }
if (-not $isisPluginFile) { Fail "Camera.plugin was not found under $isisLibraryDir or $isisRuntimeDir" }

$depIncludeDirs = @()
$depLibraryDirs = @()
if ($env:CONDA_PREFIX) {
    $depIncludeDirs += @(
        (Join-Path $env:CONDA_PREFIX "Library\include"),
        (Join-Path $env:CONDA_PREFIX "include")
    )
    $depLibraryDirs += @(
        (Join-Path $env:CONDA_PREFIX "Library\lib"),
        (Join-Path $env:CONDA_PREFIX "lib")
    )
}
$depIncludeDirs += @(
    (Join-Path $IsisPrefix "Library\include"),
    (Join-Path $IsisPrefix "include")
)
$depLibraryDirs += $isisLibraryDir

$depIncludeDirs = @($depIncludeDirs | Where-Object { Test-Path $_ } | Select-Object -Unique)
$depLibraryDirs = @($depLibraryDirs | Where-Object { Test-Path $_ } | Select-Object -Unique)
if ($depIncludeDirs.Count -eq 0) { Fail "no dependency include directories were found" }
if ($depLibraryDirs.Count -eq 0) { Fail "no dependency library directories were found" }

Write-Step "configuring pyisis"
$cmakeArgs = @(
    "-DCMAKE_BUILD_TYPE=$BuildType",
    "-DPython3_EXECUTABLE=$PythonExecutable",
    "-DISIS_PREFIX=$IsisPrefix",
    "-DISIS_INCLUDE_DIR=$(Convert-ToCMakePath $isisIncludeDir)",
    "-DISIS_DEP_INCLUDE_DIR=$(Convert-ToCMakePath $depIncludeDirs[0])",
    "-DISIS_DEP_INCLUDE_DIRS=$(($depIncludeDirs | ForEach-Object { Convert-ToCMakePath $_ }) -join ';')",
    "-DISIS_LIBRARY_DIR=$(Convert-ToCMakePath $isisLibraryDir)",
    "-DISIS_DEP_LIBRARY_DIRS=$(($depLibraryDirs | ForEach-Object { Convert-ToCMakePath $_ }) -join ';')",
    "-DISIS_RUNTIME_DIR=$(Convert-ToCMakePath $isisRuntimeDir)",
    "-DISIS_CORE_LIBRARY=$(Convert-ToCMakePath $isisCoreLibrary)",
    "-DISIS_PLUGIN_FILE=$(Convert-ToCMakePath $isisPluginFile)",
    "-DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON"
)

if ($env:CONDA_PREFIX) {
    $cmakeArgs += "-DCMAKE_PREFIX_PATH=$($env:CONDA_PREFIX)"
}

Invoke-CheckedCommand cmake -S $repoRoot -B $BuildDir -G Ninja @cmakeArgs
