param(
    [string]$Prefix,
    [string]$WorkDir,
    [string]$InputCube
)

. "$PSScriptRoot\common.ps1"

if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }
$Prefix = Resolve-FullPath $Prefix

$repoRoot = Get-RepoRoot
if (-not $WorkDir) {
    $WorkDir = Join-Path $repoRoot "build\windows\isis-reduce-smoke"
}
if (-not $InputCube) {
    $InputCube = Join-Path $repoRoot "tests\data\hidtmgen\ortho\PSP_002118_1510_1m_o_forPDS_cropped.cub"
}

$WorkDir = Resolve-FullPath $WorkDir
$InputCube = Resolve-FullPath $InputCube
$reduceExecutable = Join-Path $Prefix "bin\reduce.exe"
$outputCube = Join-Path $WorkDir "reduce_probe.cub"
$logPath = Join-Path $WorkDir "reduce.log"

if (-not (Test-Path -LiteralPath $reduceExecutable)) {
    Fail "ISIS reduce executable not found: $reduceExecutable"
}
if (-not (Test-Path -LiteralPath $InputCube)) {
    Fail "input cube not found: $InputCube"
}

& "$PSScriptRoot\verify_isis_prefix.ps1" -Prefix $Prefix
if ($LASTEXITCODE -ne 0) {
    Fail "ISIS prefix verification failed: $Prefix"
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Remove-Item -LiteralPath $outputCube, $logPath -ErrorAction SilentlyContinue

$originalPath = $env:PATH
$originalIsisRoot = $env:ISISROOT
$originalIsisPrefix = $env:ISIS_PREFIX
try {
    $env:ISISROOT = $Prefix
    $env:ISIS_PREFIX = $Prefix
    $pathEntries = @(
        (Join-Path $Prefix "bin"),
        (Join-Path $Prefix "lib")
    )
    if ($env:CONDA_PREFIX) {
        $pathEntries += @(
            (Join-Path $env:CONDA_PREFIX "Library\bin"),
            (Join-Path $env:CONDA_PREFIX "Library\usr\bin"),
            (Join-Path $env:CONDA_PREFIX "Library\mingw-w64\bin"),
            (Join-Path $env:CONDA_PREFIX "Scripts"),
            (Join-Path $env:CONDA_PREFIX "bin"),
            $env:CONDA_PREFIX
        )
    }
    $env:PATH = (($pathEntries | Where-Object { Test-Path $_ }) + @($originalPath)) -join ";"

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $reduceExecutable `
            "from=$InputCube" `
            "to=$outputCube" `
            "sscale=4" `
            "lscale=4" *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($exitCode -ne 0) {
        $tail = ""
        if (Test-Path -LiteralPath $logPath) {
            $tail = (Get-Content -LiteralPath $logPath -Tail 40) -join [Environment]::NewLine
        }
        Fail "reduce failed with exit code ${exitCode}`n$tail"
    }
    if (-not (Test-Path -LiteralPath $outputCube)) {
        Fail "reduce did not create output cube: $outputCube"
    }
    if ((Get-Item -LiteralPath $outputCube).Length -le 0) {
        Fail "reduce output cube is empty: $outputCube"
    }

    Write-Step "reduce smoke test passed: $outputCube"
}
finally {
    $env:PATH = $originalPath
    if ($null -eq $originalIsisRoot) {
        Remove-Item Env:\ISISROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:ISISROOT = $originalIsisRoot
    }
    if ($null -eq $originalIsisPrefix) {
        Remove-Item Env:\ISIS_PREFIX -ErrorAction SilentlyContinue
    }
    else {
        $env:ISIS_PREFIX = $originalIsisPrefix
    }
}
