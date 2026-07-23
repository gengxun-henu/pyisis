param(
    [string]$SourceDir,
    [string]$Repository = "https://github.com/DOI-USGS/ISIS3.git",
    [string]$Ref = "9.0.0",
    [ValidateSet("archive", "git")]
    [string]$Method = "git",
    [string[]]$GitSparsePaths = @("isis", "SensorUtilities"),
    [ValidateSet("tar.gz", "zip")]
    [string]$ArchiveFormat = "tar.gz",
    [int]$DownloadTimeoutSeconds = 300,
    [int]$LowSpeedLimitBytesPerSecond = 1024,
    [int]$LowSpeedTimeoutSeconds = 60,
    [int]$DownloadRetries = 3,
    [switch]$Force
)

. "$PSScriptRoot\common.ps1"

Require-Command git

function Invoke-IsisGit {
    Invoke-CheckedCommand git `
        -c http.schannelCheckRevoke=false `
        -c http.postBuffer=524288000 `
        @args
}

function Update-GitSparseCheckout {
    param([Parameter(Mandatory = $true)][string]$CheckoutDir)

    if ($GitSparsePaths.Count -eq 0) {
        return
    }

    Write-Step "using sparse checkout paths: $($GitSparsePaths -join ', ')"
    Invoke-IsisGit -C $CheckoutDir sparse-checkout init --cone
    Invoke-IsisGit -C $CheckoutDir sparse-checkout set @GitSparsePaths
}

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir -Version $Ref
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
        Invoke-IsisGit -C $SourceDir fetch --depth 1 --filter=blob:none origin $Ref
        Invoke-IsisGit -C $SourceDir checkout $Ref
        Update-GitSparseCheckout -CheckoutDir $SourceDir
        Invoke-IsisGit -C $SourceDir reset --hard HEAD
    }
} elseif ($Method -eq "git") {
    Write-Step "cloning ISIS source to $SourceDir"
    Invoke-IsisGit clone --no-checkout --branch $Ref --single-branch --depth 1 --filter=blob:none $Repository $SourceDir
    Update-GitSparseCheckout -CheckoutDir $SourceDir
    Invoke-IsisGit -C $SourceDir reset --hard HEAD
} else {
    if ($ArchiveFormat -eq "zip") {
        $archiveUrl = "https://github.com/DOI-USGS/ISIS3/archive/refs/tags/$Ref.zip"
        $archivePath = Join-Path $externalDir "ISIS3-$Ref.zip"
    } else {
        $archiveUrl = "https://github.com/DOI-USGS/ISIS3/archive/refs/tags/$Ref.tar.gz"
        $archivePath = Join-Path $externalDir "ISIS3-$Ref.tar.gz"
    }
    $extractDir = Join-Path $externalDir "ISIS3-$Ref-extract"
    $extractedSourceDir = Join-Path $extractDir "ISIS3-$Ref"

    if ((Test-Path $archivePath) -and $Force) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    if (Test-Path $extractDir) {
        Remove-Item -LiteralPath $extractDir -Recurse -Force
    }

    Write-Step "downloading ISIS source archive: $archiveUrl"
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        $curlArgs = @(
            "--location",
            "--fail",
            "--retry", $DownloadRetries,
            "--retry-all-errors",
            "--retry-delay", 5,
            "--connect-timeout", 30,
            "--max-time", $DownloadTimeoutSeconds,
            "--speed-limit", $LowSpeedLimitBytesPerSecond,
            "--speed-time", $LowSpeedTimeoutSeconds,
            "--show-error",
            "--no-progress-meter",
            "--continue-at", "-",
            "--output", $archivePath,
            $archiveUrl
        )
        if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
            $curlArgs = @("--ssl-no-revoke") + $curlArgs
        }
        Invoke-CheckedCommand curl.exe @curlArgs
    } else {
        if (Test-Path $archivePath) {
            Fail "cannot resume existing archive without curl.exe; remove $archivePath or pass -Force"
        }
        Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath -TimeoutSec $DownloadTimeoutSeconds
    }

    Write-Step "expanding ISIS source archive"
    if ($ArchiveFormat -eq "zip") {
        Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir
    } else {
        Require-Command tar
        Write-Step "validating ISIS source archive"
        tar -tzf $archivePath > $null
        if ($LASTEXITCODE -ne 0) {
            Fail "ISIS source archive is incomplete or invalid: $archivePath"
        }
        New-Item -ItemType Directory -Path $extractDir | Out-Null
        Invoke-CheckedCommand tar -xzf $archivePath -C $extractDir
    }
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
