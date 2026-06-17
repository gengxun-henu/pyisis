param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$PythonExecutable
)

. "$PSScriptRoot\common.ps1"

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix
if (-not $PythonExecutable) { $PythonExecutable = (Get-Command python).Source }

Set-PyisisTestEnvironment -BuildDir $BuildDir -IsisPrefix $IsisPrefix

$repoRoot = Get-RepoRoot
Write-Step "running smoke import"
Invoke-CheckedCommand $PythonExecutable (Join-Path $repoRoot "tests\smoke_import.py")
