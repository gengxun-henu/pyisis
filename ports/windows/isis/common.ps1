Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-isis] $Message"
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw "[windows-isis] $Message"
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

function Get-DefaultIsisSourceDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\external\isis-9.0.0-src"
}

function Get-DefaultIsisBuildDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\isis-build"
}

function Get-DefaultIsisPrefix {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\isis-prefix"
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}
