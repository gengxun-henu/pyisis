Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-pyisis] $Message"
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw "[windows-pyisis] $Message"
}

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "required command not found: $Name"
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Get-DefaultBuildDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\pyisis-build"
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Require-IsisPrefix {
    param([string]$Prefix)
    if (-not $Prefix) {
        $Prefix = $env:ISIS_PREFIX
    }
    if (-not $Prefix) {
        Fail "ISIS_PREFIX is not set. Set `$env:ISIS_PREFIX or pass -IsisPrefix."
    }

    $resolvedPrefix = Resolve-FullPath $Prefix
    if (-not (Test-Path $resolvedPrefix)) {
        Fail "ISIS_PREFIX does not exist: $resolvedPrefix"
    }
    return $resolvedPrefix
}

function Get-IsisRuntimeDirs {
    param([Parameter(Mandatory = $true)][string]$IsisPrefix)
    $runtimeCandidates = @(
        (Join-Path $IsisPrefix "Library\bin")
        (Join-Path $IsisPrefix "bin")
    )
    return @($runtimeCandidates | Where-Object { Test-Path $_ })
}

function Add-IsisRuntimePath {
    param([Parameter(Mandatory = $true)][string]$IsisPrefix)
    $runtimeDirs = Get-IsisRuntimeDirs -IsisPrefix $IsisPrefix
    if ($runtimeDirs.Count -eq 0) {
        Fail "no ISIS runtime DLL directory found under $IsisPrefix"
    }
    foreach ($runtimeDir in $runtimeDirs) {
        $env:PATH = "$runtimeDir;$env:PATH"
    }
}

function Set-PyisisTestEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$BuildDir,
        [Parameter(Mandatory = $true)][string]$IsisPrefix
    )
    $repoRoot = Get-RepoRoot
    $env:PYTHONPATH = "$BuildDir\python;$repoRoot\tests\unitTest"
    $env:ISISDATA = "$repoRoot\tests\data\isisdata\mockup"
    Add-IsisRuntimePath -IsisPrefix $IsisPrefix
}
