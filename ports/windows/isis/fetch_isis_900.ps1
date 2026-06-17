param(
    [string]$SourceDir,
    [string]$Repository = "https://github.com/DOI-USGS/ISIS3.git",
    [string]$Ref = "9.0.0",
    [ValidateSet("archive", "git")]
    [string]$Method = "archive",
    [int]$DownloadTimeoutSeconds = 300,
    [int]$LowSpeedLimitBytesPerSecond = 1024,
    [int]$LowSpeedTimeoutSeconds = 60,
    [int]$DownloadRetries = 3,
    [switch]$Force
)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir
$externalDir = Split-Path -Parent $SourceDir

if ((Test-Path $SourceDir) -and $Force) {
    Write-Step "removing existing source directory: $SourceDir"
    Remove-Item -LiteralPath $SourceDir -Recurse -Force
}

if ((Test-Path $SourceDir) -and -not (Test-Path (Join-Path $SourceDir ".git"))) {
    Fail "source directory exists but is not a git worktree: $SourceDir; pass -Force to recreate it"
}

if (Test-Path (Join-Path $SourceDir ".git")) {
    Write-Step "source checkout already exists: $SourceDir"
    if ($Method -eq "git") {
        Invoke-CheckedCommand git -C $SourceDir fetch --tags --prune
        Invoke-CheckedCommand git -C $SourceDir checkout $Ref
    }
} elseif ($Method -eq "git") {
    Write-Step "cloning ISIS source to $SourceDir"
    Invoke-CheckedCommand git clone --branch $Ref --single-branch --depth 1 --filter=blob:none $Repository $SourceDir
} else {
    $archiveUrl = "https://github.com/DOI-USGS/ISIS3/archive/refs/tags/$Ref.zip"
    $archivePath = Join-Path $externalDir "ISIS3-$Ref.zip"
    $extractDir = Join-Path $externalDir "ISIS3-$Ref-extract"
    $extractedSourceDir = Join-Path $extractDir "ISIS3-$Ref"

    if (Test-Path $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    if (Test-Path $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }

    Write-Step "downloading ISIS source archive: $archiveUrl"
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        Invoke-CheckedCommand curl.exe `
            --location `
            --fail `
            --retry $DownloadRetries `
            --retry-delay 5 `
            --connect-timeout 30 `
            --max-time $DownloadTimeoutSeconds `
            --speed-limit $LowSpeedLimitBytesPerSecond `
            --speed-time $LowSpeedTimeoutSeconds `
            --show-error `
            --progress-bar `
            --output $archivePath `
            $archiveUrl
    } else {
        Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath -TimeoutSec $DownloadTimeoutSeconds
    }

    Write-Step "expanding ISIS source archive"
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir
    if (-not (Test-Path $extractedSourceDir)) {
        Fail "expected extracted source directory not found: $extractedSourceDir"
    }

    Move-Item -LiteralPath $extractedSourceDir -Destination $SourceDir
    Remove-Item -LiteralPath $extractDir -Recurse -Force

    Write-Step "initializing local git worktree for patch application"
    Invoke-CheckedCommand git -C $SourceDir init
    Invoke-CheckedCommand git -C $SourceDir add -A
}

Write-Step "ISIS source is ready at $SourceDir"
