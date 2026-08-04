param(
    [switch]$ExpectedWindows11
)

$ErrorActionPreference = "Stop"

$OperatingSystem = Get-CimInstance Win32_OperatingSystem
if ($OperatingSystem.OSArchitecture -notmatch "64") {
    throw "Windows x64 is required; detected: $($OperatingSystem.OSArchitecture)"
}
if ($ExpectedWindows11 -and $OperatingSystem.Caption -notmatch "Windows 11") {
    throw "Windows 11 is required; detected: $($OperatingSystem.Caption)"
}

Write-Host "Operating system: $($OperatingSystem.Caption) $($OperatingSystem.Version)"

foreach ($CommandName in @("pwsh", "conda", "git", "cmake", "ninja")) {
    $Command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $Command) {
        throw "Required command is missing: $CommandName"
    }
    Write-Host "$CommandName`: $($Command.Source)"
}

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$MsvcActivationScript = Join-Path $ProjectRoot "ports\windows\activate_msvc.ps1"
if (-not (Test-Path -LiteralPath $MsvcActivationScript -PathType Leaf)) {
    throw "MSVC activation script is missing: $MsvcActivationScript"
}
. $MsvcActivationScript

foreach ($CommandName in @("cl", "dumpbin")) {
    $Command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $Command) {
        throw "Required MSVC command is missing after activate_msvc.ps1: $CommandName"
    }
    Write-Host "$CommandName`: $($Command.Source)"
}

Write-Host "Windows 11 self-hosted runner readiness checks passed."
