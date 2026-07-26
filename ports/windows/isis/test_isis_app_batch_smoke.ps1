param(
    [string]$Prefix,
    [string]$WorkDir,
    [string]$InputCube,
    [string]$ManifestPath,
    [string]$IsisVersion = "10.0.0"
)

. "$PSScriptRoot\common.ps1"

if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }
$Prefix = Resolve-FullPath $Prefix

$repoRoot = Get-RepoRoot
if (-not $WorkDir) {
    $WorkDir = Join-Path $repoRoot "build\windows\isis-app-batch-smoke"
}
if (-not $InputCube) {
    $InputCube = Join-Path $repoRoot "tests\data\hidtmgen\ortho\PSP_002118_1510_1m_o_forPDS_cropped.cub"
}
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $PSScriptRoot "windows-app-manifest.json"
}

$WorkDir = Resolve-FullPath $WorkDir
$InputCube = Resolve-FullPath $InputCube
$ManifestPath = Resolve-FullPath $ManifestPath

if (-not (Test-Path -LiteralPath $InputCube)) {
    Fail "input cube not found: $InputCube"
}
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Fail "Windows APP manifest not found: $ManifestPath"
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$appNames = @(
    $manifest.apps |
        Where-Object {
            $version = $_.versions.PSObject.Properties[$IsisVersion]
            $version -and $version.Value.status -ne "unavailable"
        } |
        ForEach-Object { $_.name } |
        Sort-Object -Unique
)
if ($appNames.Count -lt 69) {
    Fail "expected at least 69 allowlisted APPs, found $($appNames.Count)"
}

& "$PSScriptRoot\verify_isis_prefix.ps1" `
    -Prefix $Prefix `
    -ExpectedVersion $IsisVersion
if ($LASTEXITCODE -ne 0) {
    Fail "ISIS prefix verification failed: $Prefix"
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

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

    $results = New-Object System.Collections.Generic.List[object]

    function Invoke-IsisApp {
        param(
            [Parameter(Mandatory = $true)][string]$Name,
            [Parameter(Mandatory = $true)][string[]]$Arguments,
            [Parameter(Mandatory = $true)][string]$LogName,
            [string]$ExpectedOutput
        )

        $exe = Join-Path $Prefix "bin\$Name.exe"
        if (-not (Test-Path -LiteralPath $exe)) {
            Fail "ISIS APP executable not found: $exe"
        }

        $logPath = Join-Path $WorkDir $LogName
        Remove-Item -LiteralPath $logPath -ErrorAction SilentlyContinue
        if ($ExpectedOutput) {
            Remove-Item -LiteralPath $ExpectedOutput -ErrorAction SilentlyContinue
        }

        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $exe @Arguments *> $logPath
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }

        $script:results.Add([pscustomobject]@{
            Command = $Name
            Exit = $exitCode
            Log = $logPath
        })

        if ($exitCode -ne 0) {
            $tail = ""
            if (Test-Path -LiteralPath $logPath) {
                $tail = (Get-Content -LiteralPath $logPath -Tail 40) -join [Environment]::NewLine
            }
            Fail "ISIS APP failed with exit code ${exitCode}: $Name $($Arguments -join ' ')`n$tail"
        }
        if ($ExpectedOutput) {
            if (-not (Test-Path -LiteralPath $ExpectedOutput)) {
                Fail "expected output file was not created: $ExpectedOutput"
            }
            if ((Get-Item -LiteralPath $ExpectedOutput).Length -le 0) {
                Fail "expected output file is empty: $ExpectedOutput"
            }
        }
    }

    foreach ($appName in $appNames) {
        Invoke-IsisApp $appName @("-HELP") "startup-$appName.log"
    }

    $seedCube = Join-Path $WorkDir "seed.cub"
    Invoke-IsisApp "crop" @(
        "from=$InputCube", "to=$seedCube", "sample=1", "line=1",
        "nsamples=32", "nlines=32", "overhang=shrink"
    ) "cube-crop.log" $seedCube

    $labelOutput = Join-Path $WorkDir "label.txt"
    Invoke-IsisApp "catlab" @("from=$seedCube", "to=$labelOutput", "append=false") "cube-catlab.log" $labelOutput
    Invoke-IsisApp "getkey" @("from=$seedCube", "grpname=Dimensions", "keyword=Samples", "recursive=true") "cube-getkey.log"
    Invoke-IsisApp "stats" @("from=$seedCube") "cube-stats.log"

    $cubeCommands = @(
        @{ Name = "algebra"; Args = @("from=$seedCube", "from2=$seedCube", "operator=add"); Output = "algebra.cub" },
        @{ Name = "bit2bit"; Args = @("from=$seedCube", "bittype=32bit"); Output = "bit2bit.cub" },
        @{ Name = "cubeatt"; Args = @("from=$seedCube"); Output = "cubeatt.cub" },
        @{ Name = "cubenorm"; Args = @("from=$seedCube"); Output = "cubenorm.cub" },
        @{ Name = "enlarge"; Args = @("from=$seedCube", "sscale=2", "lscale=2"); Output = "enlarge.cub" },
        @{ Name = "fillgap"; Args = @("from=$seedCube"); Output = "fillgap.cub" },
        @{ Name = "flip"; Args = @("from=$seedCube"); Output = "flip.cub" },
        @{ Name = "gradient"; Args = @("from=$seedCube"); Output = "gradient.cub" },
        @{ Name = "mask"; Args = @("from=$seedCube", "mask=$seedCube"); Output = "mask.cub" },
        @{ Name = "mirror"; Args = @("from=$seedCube"); Output = "mirror.cub" },
        @{ Name = "noisefilter"; Args = @("from=$seedCube", "samples=3", "lines=3"); Output = "noisefilter.cub" },
        @{ Name = "ratio"; Args = @("numerator=$seedCube", "denominator=$seedCube"); Output = "ratio.cub" },
        @{ Name = "reduce"; Args = @("from=$seedCube", "sscale=2", "lscale=2"); Output = "reduce.cub" },
        @{ Name = "stretch"; Args = @("from=$seedCube", "pairs=0:0 255:255"); Output = "stretch.cub" },
        @{ Name = "trim"; Args = @("from=$seedCube", "top=1", "bottom=1", "left=1", "right=1"); Output = "trim.cub" }
    )
    foreach ($command in $cubeCommands) {
        $output = Join-Path $WorkDir $command.Output
        $arguments = @($command.Args) + @("to=$output")
        Invoke-IsisApp $command.Name $arguments "cube-$($command.Name).log" $output
    }

    $fxOutput = Join-Path $WorkDir "fx.cub"
    Invoke-IsisApp "fx" @(
        "to=$fxOutput", "equation=sample+line", "mode=outputonly",
        "lines=16", "samples=16", "bands=1"
    ) "cube-fx.log" $fxOutput

    Invoke-IsisApp "cubediff" @(
        "from=$seedCube", "from2=$seedCube", "tolerance=0"
    ) "cube-cubediff.log"

    $results | Format-Table -AutoSize
    Write-Step "Windows ISIS APP batch smoke passed for $($appNames.Count) executables: $WorkDir"
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
