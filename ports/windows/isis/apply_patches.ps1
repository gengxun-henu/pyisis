param([string]$SourceDir)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir
$patchDir = Join-Path $PSScriptRoot "patches"

if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    Fail "ISIS source checkout not found: $SourceDir"
}

$patches = @(Get-ChildItem -Path $patchDir -Filter "*.patch" | Sort-Object Name)
if ($patches.Count -eq 0) {
    Write-Step "no patch files found in $patchDir"
    exit 0
}

foreach ($patch in $patches) {
    Write-Step "applying $($patch.Name)"
    Invoke-CheckedCommand git -C $SourceDir apply --check $patch.FullName
    Invoke-CheckedCommand git -C $SourceDir apply $patch.FullName
}
