param([string]$VcVars64)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-msvc] $Message"
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw "[windows-msvc] $Message"
}

if (-not $VcVars64) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) {
        Fail "vswhere.exe was not found; install Visual Studio Build Tools or pass -VcVars64."
    }

    $vsInstall = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($LASTEXITCODE -ne 0 -or -not $vsInstall) {
        Fail "Visual Studio Build Tools with the MSVC x64 toolchain were not found."
    }

    $VcVars64 = Join-Path $vsInstall "VC\Auxiliary\Build\vcvars64.bat"
}

if (-not (Test-Path $VcVars64)) {
    Fail "vcvars64.bat not found: $VcVars64"
}

Write-Step "loading MSVC environment from $VcVars64"
$cmd = "`"$VcVars64`" >nul && set"
$envLines = cmd /d /s /c $cmd
if ($LASTEXITCODE -ne 0) {
    Fail "vcvars64.bat failed with exit code $LASTEXITCODE"
}

foreach ($line in $envLines) {
    $separator = $line.IndexOf("=")
    if ($separator -le 0) {
        continue
    }
    $name = $line.Substring(0, $separator)
    $value = $line.Substring($separator + 1)
    Set-Item -Path "Env:\$name" -Value $value
}

Write-Step "MSVC environment activated"
