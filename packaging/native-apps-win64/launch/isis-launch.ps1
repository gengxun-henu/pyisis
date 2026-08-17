$ErrorActionPreference = "Stop"
$PackageRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ManifestPath = Join-Path $PackageRoot "manifest\apps.json"

[object[]] $InvocationArguments = @($args)
if ($InvocationArguments.Count -eq 0) {
    [Console]::Error.WriteLine("Missing APP name; not a public ISIS APP.")
    exit 2
}

$AppName = [string] $InvocationArguments[0]
[string[]] $AppArguments = @()
if ($InvocationArguments.Count -gt 1) {
    $AppArguments = [string[]] @(
        $InvocationArguments[1..($InvocationArguments.Count - 1)]
    )
}

# Windows PowerShell 5 drops an empty string at its native-process boundary.
# A quoted-empty command-line token preserves that argv element for the APP.
for ($ArgumentIndex = 0; $ArgumentIndex -lt $AppArguments.Count; $ArgumentIndex++) {
    if ($AppArguments[$ArgumentIndex].Length -eq 0) {
        $AppArguments[$ArgumentIndex] = '""'
    }
}

if ([string]::IsNullOrEmpty($AppName)) {
    [Console]::Error.WriteLine("Missing APP name; not a public ISIS APP.")
    exit 2
}

if ($AppName -notmatch "^[A-Za-z0-9_-]+$") {
    [Console]::Error.WriteLine("Requested name is not a public ISIS APP.")
    exit 4
}

try {
    $Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
}
catch {
    [Console]::Error.WriteLine("Unable to read ISIS APP manifest.")
    exit 5
}

if (@($Manifest.public_apps) -cnotcontains $AppName) {
    [Console]::Error.WriteLine("Requested name is not a public ISIS APP.")
    exit 4
}

$ExternalData = [Environment]::GetEnvironmentVariable("ISISDATA", "Process")
if ([string]::IsNullOrEmpty($ExternalData)) {
    $env:ISISDATA = Join-Path $PackageRoot "data"
}
elseif (-not (Test-Path -LiteralPath $ExternalData -PathType Container)) {
    [Console]::Error.WriteLine("Explicit ISISDATA directory does not exist.")
    exit 3
}

$env:ISIS_PACKAGE_ROOT = $PackageRoot
$env:ISISROOT = $PackageRoot
$env:ISIS_PREFIX = $PackageRoot
$env:QT_PLUGIN_PATH = Join-Path $PackageRoot "plugins"
$env:PATH = @(
    (Join-Path $PackageRoot "bin")
    (Join-Path $PackageRoot "lib")
    $env:PATH
) -join [System.IO.Path]::PathSeparator

$Executable = Join-Path (Join-Path $PackageRoot "bin") "$AppName.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    [Console]::Error.WriteLine("Public ISIS APP executable is missing.")
    exit 6
}

& $Executable @AppArguments
$ExitCode = $LASTEXITCODE
if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit [int] $ExitCode
