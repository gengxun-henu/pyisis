param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$PythonExecutable,
    [string]$TestList
)

. "$PSScriptRoot\common.ps1"

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix
if (-not $PythonExecutable) { $PythonExecutable = (Get-Command python).Source }
if (-not $TestList) { $TestList = Join-Path $PSScriptRoot "basic_tests.txt" }

if (-not (Test-Path $TestList)) {
    Fail "test list not found: $TestList"
}

Set-PyisisTestEnvironment -BuildDir $BuildDir -IsisPrefix $IsisPrefix

$modules = Get-Content $TestList | Where-Object {
    $line = $_.Trim()
    $line -and -not $line.StartsWith("#")
}

foreach ($module in $modules) {
    Write-Step "running unittest module: $module"
    Invoke-CheckedCommand $PythonExecutable -m unittest $module -v
}
