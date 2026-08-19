param(
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)][string]$IsisPrefix,
    [Parameter(Mandatory = $true)][string]$MinimalDataRoot,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][string]$ReportDir,
    [Parameter(Mandatory = $true)][string]$WorkDir,
    [Parameter(ValueFromRemainingArguments = $true)][object[]]$BuildArguments = @()
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

# Windows PowerShell rejects repeated declared array parameters before the
# script runs, so parse the documented repeated form explicitly.
$DependencyPrefix = New-Object System.Collections.Generic.List[string]
for ($argumentIndex = 0; $argumentIndex -lt $BuildArguments.Count; $argumentIndex += 2) {
    if ([string]$BuildArguments[$argumentIndex] -cne "-DependencyPrefix" -or $argumentIndex + 1 -ge $BuildArguments.Count) {
        throw "unknown build argument; expected repeatable -DependencyPrefix <path> pairs"
    }
    $DependencyPrefix.Add([string]$BuildArguments[$argumentIndex + 1])
}
if ($DependencyPrefix.Count -eq 0) {
    throw "at least one -DependencyPrefix <path> is required"
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path))
}

function Assert-PathWithin {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$Parent
    )
    $candidatePath = Resolve-FullPath $Candidate
    $parentPath = Resolve-FullPath $Parent
    if ($candidatePath.Equals($parentPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "work directory must be a child of build/windows, not build/windows itself"
    }
    $prefix = $parentPath.TrimEnd('\') + '\'
    if (-not $candidatePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "path escapes build/windows: $candidatePath"
    }
}

function Resolve-RepositoryPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) { return Resolve-FullPath $Path }
    return Resolve-FullPath (Join-Path $repoRoot $Path)
}

function Test-IsPathWithinOrEqual {
    param([string]$Candidate, [string]$Parent)
    $candidatePath = Resolve-FullPath $Candidate
    $parentPath = Resolve-FullPath $Parent
    return $candidatePath.Equals($parentPath, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidatePath.StartsWith($parentPath.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

$repoRoot = Resolve-FullPath (Join-Path $PSScriptRoot "..\..")
$buildWindowsRoot = Resolve-FullPath (Join-Path $repoRoot "build\windows")
$resolvedWorkDir = Resolve-FullPath $WorkDir
Assert-PathWithin -Candidate $resolvedWorkDir -Parent $buildWindowsRoot
if (Test-Path -LiteralPath $resolvedWorkDir) {
    $workItem = Get-Item -LiteralPath $resolvedWorkDir -Force
    if (-not $workItem.PSIsContainer -or ($workItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "work directory must be a normal directory: $resolvedWorkDir"
    }
}
else {
    New-Item -ItemType Directory -Path $resolvedWorkDir -Force | Out-Null
}

$resolvedPython = Resolve-RepositoryPath $PythonExecutable
$resolvedIsisPrefix = Resolve-RepositoryPath $IsisPrefix
$resolvedMinimalDataRoot = Resolve-RepositoryPath $MinimalDataRoot
$resolvedOutputDir = Resolve-RepositoryPath $OutputDir
$resolvedReportDir = Resolve-RepositoryPath $ReportDir
$resolvedDependencyPrefixes = @($DependencyPrefix | ForEach-Object { Resolve-RepositoryPath $_ })
if (Test-IsPathWithinOrEqual -Candidate $resolvedOutputDir -Parent $resolvedWorkDir) {
    throw "output directory must remain outside work directory"
}
if (Test-IsPathWithinOrEqual -Candidate $resolvedReportDir -Parent $resolvedWorkDir) {
    throw "report directory must remain outside work directory"
}
if (-not (Test-Path -LiteralPath $resolvedPython -PathType Leaf)) { throw "Python executable not found: $resolvedPython" }
if (-not (Test-Path -LiteralPath $resolvedIsisPrefix -PathType Container)) { throw "ISIS prefix not found: $resolvedIsisPrefix" }
if (-not (Test-Path -LiteralPath $resolvedMinimalDataRoot -PathType Container)) { throw "minimal ISISDATA root not found: $resolvedMinimalDataRoot" }
foreach ($prefix in $resolvedDependencyPrefixes) {
    if (-not (Test-Path -LiteralPath $prefix -PathType Container)) { throw "dependency prefix not found: $prefix" }
}
New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null
New-Item -ItemType Directory -Path $resolvedReportDir -Force | Out-Null

$releaseConfig = Join-Path $repoRoot "packaging\native-apps-win64\release.json"
$cliManifest = Join-Path $repoRoot "ports\windows\isis\windows-app-manifest.json"
$release = Get-Content -Raw -LiteralPath $releaseConfig | ConvertFrom-Json
$archive = Join-Path $resolvedOutputDir ([string]$release.archive_name)
$dependencyReport = Join-Path $resolvedOutputDir (([System.IO.Path]::GetFileNameWithoutExtension([string]$release.archive_name)) + "-dll-dependencies.json")
$validationReportName = "isis-native-apps-{0}-{1}-validation.json" -f `
    [string]$release.isis_version, [string]$release.platform
$validationReport = Join-Path $resolvedReportDir $validationReportName
$stageParent = Join-Path $resolvedWorkDir "stage"
$stageRoot = Join-Path $stageParent ([string]$release.root_name)
$runtimeWork = Join-Path $resolvedWorkDir "runtime logs"
$runtimeReport = Join-Path $resolvedWorkDir "runtime-validation.json"

$stageScript = Join-Path $repoRoot "tools\packaging\stage_windows_native_apps.py"
$archiveScript = Join-Path $repoRoot "tools\packaging\archive_windows_native_apps.py"
$runtimeScript = Join-Path $repoRoot "ports\windows\isis\test_isis_native_app_package.ps1"
$validationScript = Join-Path $repoRoot "tools\packaging\validate_windows_native_apps.py"

$completed = $false
try {
    if (Test-Path -LiteralPath $validationReport -PathType Leaf) {
        Remove-Item -LiteralPath $validationReport -Force
    }

    $stageArgs = @(
        "--isis-prefix", $resolvedIsisPrefix,
        "--minimal-data-root", $resolvedMinimalDataRoot,
        "--release", $releaseConfig,
        "--cli-manifest", $cliManifest,
        "--stage-parent", $stageParent,
        "--dependency-report", $dependencyReport
    )
    foreach ($prefix in $resolvedDependencyPrefixes) {
        $stageArgs += @("--dependency-prefix", $prefix)
    }
    & $resolvedPython $stageScript @stageArgs
    if ($LASTEXITCODE -ne 0) { throw "native APP staging failed" }

    $archiveArgs = @("--stage-root", $stageRoot, "--archive", $archive)
    & $resolvedPython $archiveScript @archiveArgs
    if ($LASTEXITCODE -ne 0) { throw "native APP archive creation failed" }

    $runtimeArgs = @{
        Archive = $archive
        ReleaseConfig = $releaseConfig
        WorkDir = $runtimeWork
        Report = $runtimeReport
    }
    & $runtimeScript @runtimeArgs
    if ($LASTEXITCODE -ne 0) { throw "native APP runtime matrix failed" }

    $validationArgs = @(
        "--archive", $archive,
        "--dependency-report", $dependencyReport,
        "--runtime-report", $runtimeReport,
        "--release", $releaseConfig,
        "--cli-manifest", $cliManifest,
        "--output-report", $validationReport
    )
    & $resolvedPython $validationScript @validationArgs
    if ($LASTEXITCODE -ne 0) { throw "native APP release validation failed" }
    $completed = $true
}
finally {
    if ($completed) {
        $resolvedWorkDir = Resolve-FullPath $resolvedWorkDir
        Assert-PathWithin -Candidate $resolvedWorkDir -Parent $buildWindowsRoot
        $workItem = Get-Item -LiteralPath $resolvedWorkDir -Force
        if ($workItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "refusing recursive cleanup of a reparse point: $resolvedWorkDir"
        }
        Remove-Item -LiteralPath $resolvedWorkDir -Recurse -Force
    }
}
