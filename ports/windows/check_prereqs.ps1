Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Check {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-prereqs] $Message"
}

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        Write-Check "found ${Name}: $($command.Source)"
        return $true
    }
    Write-Check "missing ${Name}"
    return $false
}

$missing = New-Object System.Collections.Generic.List[string]

if (-not (Test-Command git)) { $missing.Add("git") }
if (-not (Test-Command cmake)) { $missing.Add("cmake") }
if (-not (Test-Command ninja)) { $missing.Add("ninja") }

$hasConda = Test-Command conda
$hasMamba = Test-Command mamba
if (-not ($hasConda -or $hasMamba)) {
    $missing.Add("conda or mamba")
}

$hasCl = Test-Command cl
if (-not $hasCl) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        Write-Check "found vswhere: $vswhere"
        Write-Check "MSVC cl.exe is not on PATH; run from an x64 Native Tools prompt or call vcvars64.bat."
    } else {
        Write-Check "Visual Studio Build Tools were not detected via vswhere."
    }
    $missing.Add("MSVC cl.exe on PATH")
}

if ($env:CONDA_PREFIX) {
    Write-Check "CONDA_PREFIX: $env:CONDA_PREFIX"
} else {
    Write-Check "CONDA_PREFIX is not set; activate pyisis-isis-win64 before configuring ISIS or pyisis."
    $missing.Add("active conda environment")
}

if ($missing.Count -gt 0) {
    Write-Error "Windows port prerequisites missing: $($missing -join ', ')"
    exit 1
}

Write-Check "all prerequisite commands are available"
