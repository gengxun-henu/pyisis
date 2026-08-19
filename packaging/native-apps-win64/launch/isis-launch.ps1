$ErrorActionPreference = "Stop"
$PackageRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ManifestPath = Join-Path $PackageRoot "manifest\apps.json"

$ArgumentCount = 0
$ArgumentCountText = [Environment]::GetEnvironmentVariable(
    "ISIS_LAUNCH_ARG_COUNT",
    "Process"
)
if (-not [int]::TryParse($ArgumentCountText, [ref] $ArgumentCount)) {
    [Console]::Error.WriteLine("Missing APP name; not a public ISIS APP.")
    exit 2
}

[object[]] $InvocationArguments = @()
for ($ArgumentIndex = 0; $ArgumentIndex -lt $ArgumentCount; $ArgumentIndex++) {
    $ArgumentValue = [Environment]::GetEnvironmentVariable(
        "ISIS_LAUNCH_ARG_$ArgumentIndex",
        "Process"
    )
    if ($null -eq $ArgumentValue) {
        $ArgumentValue = ""
    }
    $InvocationArguments += [string] $ArgumentValue
}

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

function ConvertTo-WindowsNativeArgument([string] $Value) {
    if ($Value.Length -eq 0) {
        return '""'
    }
    $Builder = New-Object System.Text.StringBuilder
    [void] $Builder.Append('"')
    $BackslashCount = 0
    foreach ($Item in $Value.ToCharArray()) {
        if ($Item -eq '\') {
            $BackslashCount++
            continue
        }
        if ($Item -eq '"') {
            [void] $Builder.Append(('\' * (2 * $BackslashCount + 1)))
            [void] $Builder.Append('"')
        }
        else {
            [void] $Builder.Append(('\' * $BackslashCount))
            [void] $Builder.Append($Item)
        }
        $BackslashCount = 0
    }
    [void] $Builder.Append(('\' * (2 * $BackslashCount)))
    [void] $Builder.Append('"')
    return $Builder.ToString()
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

# Build the exact native command line once; Windows PowerShell 5 otherwise
# re-encodes pre-quoted values when invoking an executable with array splatting.
for ($ArgumentIndex = 0; $ArgumentIndex -lt $AppArguments.Count; $ArgumentIndex++) {
    $AppArguments[$ArgumentIndex] = ConvertTo-WindowsNativeArgument(
        $AppArguments[$ArgumentIndex]
    )
}

$StartInfo = New-Object System.Diagnostics.ProcessStartInfo
$StartInfo.FileName = $Executable
$StartInfo.UseShellExecute = $false
$StartInfo.Arguments = $AppArguments -join " "
$Process = New-Object System.Diagnostics.Process
$Process.StartInfo = $StartInfo
try {
    [void] $Process.Start()
    $Process.WaitForExit()
    $ExitCode = $Process.ExitCode
}
finally {
    $Process.Dispose()
}
exit [int] $ExitCode
