param(
    [string]$SourceDir,
    [string]$PatchDir
)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir
if (-not $PatchDir) {
    $PatchDir = Join-Path $PSScriptRoot "patches"
}
$PatchDir = Resolve-FullPath $PatchDir

if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    Fail "ISIS source checkout not found: $SourceDir"
}

$patches = @(Get-ChildItem -Path $PatchDir -Filter "*.patch" | Sort-Object Name)
if ($patches.Count -eq 0) {
    Write-Step "no patch files found in $PatchDir"
    exit 0
}

foreach ($patch in $patches) {
    Write-Step "applying $($patch.Name)"
    Invoke-CheckedCommand git -C $SourceDir apply --ignore-space-change --unidiff-zero --check $patch.FullName
    Invoke-CheckedCommand git -C $SourceDir apply --ignore-space-change --unidiff-zero $patch.FullName
}
