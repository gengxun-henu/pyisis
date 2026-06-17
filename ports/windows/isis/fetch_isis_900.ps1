param(
    [string]$SourceDir,
    [string]$Repository = "https://github.com/DOI-USGS/ISIS3.git",
    [string]$Ref = "9.0.0"
)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir

if (Test-Path (Join-Path $SourceDir ".git")) {
    Write-Step "source checkout already exists: $SourceDir"
    Invoke-CheckedCommand git -C $SourceDir fetch --tags --prune
    Invoke-CheckedCommand git -C $SourceDir checkout $Ref
} else {
    Write-Step "cloning ISIS source to $SourceDir"
    Invoke-CheckedCommand git clone --branch $Ref --depth 1 $Repository $SourceDir
}

Write-Step "ISIS source is ready at $SourceDir"
