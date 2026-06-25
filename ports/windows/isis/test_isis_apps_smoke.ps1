param(
    [string]$Prefix,
    [string]$WorkDir,
    [string]$InputCube,
    [string]$CameraCube,
    [string]$MapFile,
    [string]$LroRawImage,
    [switch]$RunLroPipeline,
    [switch]$ListCommands
)

$requiredCommands = @(
    "stats",
    "getkey",
    "catlab",
    "campt",
    "reduce",
    "cam2map",
    "isis2std",
    "cubeit",
    "fx"
)
$optionalLroCommands = @(
    "lronac2isis",
    "spiceinit",
    "lronaccal",
    "lronacecho"
)

if ($ListCommands) {
    ($requiredCommands + $optionalLroCommands) | ForEach-Object { Write-Output $_ }
    exit 0
}

. "$PSScriptRoot\common.ps1"

if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }
$Prefix = Resolve-FullPath $Prefix

$repoRoot = Get-RepoRoot
if (-not $WorkDir) { $WorkDir = Join-Path $repoRoot "build\windows\isis-command-smoke" }
$WorkDir = Resolve-FullPath $WorkDir
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

if (-not $InputCube) {
    $InputCube = Join-Path $repoRoot "tests\data\hidtmgen\ortho\PSP_002118_1510_1m_o_forPDS_cropped.cub"
}
if (-not $CameraCube) {
    $CameraCube = Join-Path $repoRoot "tests\data\mosrange\EN0108828322M_iof.cub"
}
if (-not $MapFile) {
    $MapFile = Join-Path $Prefix "appdata\templates\maps\sinusoidal.map"
}

$InputCube = Resolve-FullPath $InputCube
$CameraCube = Resolve-FullPath $CameraCube
$MapFile = Resolve-FullPath $MapFile

if (-not (Test-Path -LiteralPath $InputCube)) { Fail "input cube not found: $InputCube" }
if (-not (Test-Path -LiteralPath $CameraCube)) { Fail "camera cube not found: $CameraCube" }
if (-not (Test-Path -LiteralPath $MapFile)) { Fail "map file not found: $MapFile" }

& "$PSScriptRoot\verify_isis_prefix.ps1" -Prefix $Prefix
if ($LASTEXITCODE -ne 0) {
    Fail "ISIS prefix verification failed: $Prefix"
}

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

    function Invoke-IsisSmokeCommand {
        param(
            [Parameter(Mandatory = $true)][string]$Name,
            [Parameter(Mandatory = $true)][string[]]$Arguments,
            [Parameter(Mandatory = $true)][string]$LogName
        )

        $exe = Join-Path $Prefix "bin\$Name.exe"
        if (-not (Test-Path -LiteralPath $exe)) {
            Fail "ISIS app not found: $exe"
        }

        $logPath = Join-Path $WorkDir $LogName
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
            Fail "ISIS app failed with exit code ${exitCode}: $Name $($Arguments -join ' ')`n$tail"
        }
    }

    function Assert-OutputFile {
        param([Parameter(Mandatory = $true)][string]$Path)
        if (-not (Test-Path -LiteralPath $Path)) {
            Fail "expected output file was not created: $Path"
        }
        $item = Get-Item -LiteralPath $Path
        if ($item.Length -le 0) {
            Fail "expected output file is empty: $Path"
        }
    }

    $labelOutput = Join-Path $WorkDir "catlab_label.txt"
    $reducedCube = Join-Path $WorkDir "reduce_probe.cub"
    $mappedCube = Join-Path $WorkDir "cam2map_probe.cub"
    $pngOutput = Join-Path $WorkDir "isis2std_probe.png"
    $cubeitList = Join-Path $WorkDir "cubeit_inputs.lis"
    $cubeitOutput = Join-Path $WorkDir "cubeit_probe.cub"
    $fxOutput = Join-Path $WorkDir "fx_probe.cub"
    $camptOutput = Join-Path $WorkDir "campt_probe.pvl"

    Remove-Item -LiteralPath $labelOutput, $reducedCube, $mappedCube, $pngOutput, $cubeitList, $cubeitOutput, $fxOutput, $camptOutput -ErrorAction SilentlyContinue

    Invoke-IsisSmokeCommand "stats" @("from=$InputCube") "stats.log"
    Invoke-IsisSmokeCommand "getkey" @("from=$InputCube", "grpname=Dimensions", "keyword=Samples", "recursive=true") "getkey.log"
    Invoke-IsisSmokeCommand "catlab" @("from=$InputCube", "to=$labelOutput") "catlab.log"
    Assert-OutputFile $labelOutput

    Invoke-IsisSmokeCommand "reduce" @("from=$InputCube", "to=$reducedCube", "sscale=4", "lscale=4") "reduce.log"
    Assert-OutputFile $reducedCube

    Invoke-IsisSmokeCommand "campt" @("from=$CameraCube", "sample=64", "line=512", "type=image", "to=$camptOutput") "campt.log"
    Assert-OutputFile $camptOutput

    Invoke-IsisSmokeCommand "cam2map" @("from=$CameraCube", "map=$MapFile", "to=$mappedCube", "pixres=mpp", "resolution=1000", "interp=bilinear") "cam2map.log"
    Assert-OutputFile $mappedCube

    Invoke-IsisSmokeCommand "isis2std" @("from=$reducedCube", "to=$pngOutput", "mode=grayscale", "format=png", "stretch=linear") "isis2std.log"
    Assert-OutputFile $pngOutput

    Set-Content -LiteralPath $cubeitList -Value @($reducedCube, $reducedCube)
    Invoke-IsisSmokeCommand "cubeit" @("fromlist=$cubeitList", "to=$cubeitOutput") "cubeit.log"
    Assert-OutputFile $cubeitOutput

    Invoke-IsisSmokeCommand "fx" @("to=$fxOutput", "equation=sample+line", "mode=outputonly", "lines=16", "samples=16", "bands=1") "fx.log"
    Assert-OutputFile $fxOutput

    if ($RunLroPipeline) {
        if (-not $LroRawImage) {
            Fail "-RunLroPipeline requires -LroRawImage."
        }
        $LroRawImage = Resolve-FullPath $LroRawImage
        if (-not (Test-Path -LiteralPath $LroRawImage)) {
            Fail "LRO raw image not found: $LroRawImage"
        }

        $lroBase = Join-Path $WorkDir "lro_probe.cub"
        $lroCal = Join-Path $WorkDir "lro_probe.cal.cub"
        $lroEcho = Join-Path $WorkDir "lro_probe.echo.cal.cub"
        Remove-Item -LiteralPath $lroBase, $lroCal, $lroEcho -ErrorAction SilentlyContinue

        Invoke-IsisSmokeCommand "lronac2isis" @("from=$LroRawImage", "to=$lroBase") "lronac2isis.log"
        Assert-OutputFile $lroBase
        Invoke-IsisSmokeCommand "spiceinit" @("from=$lroBase", "web=true", "shape=ellipsoid") "spiceinit.log"
        Invoke-IsisSmokeCommand "lronaccal" @("from=$lroBase", "to=$lroCal") "lronaccal.log"
        Assert-OutputFile $lroCal
        Invoke-IsisSmokeCommand "lronacecho" @("from=$lroCal", "to=$lroEcho") "lronacecho.log"
        Assert-OutputFile $lroEcho
    }

    $results | Format-Table -AutoSize
    Write-Step "ISIS app smoke tests passed. Logs and outputs: $WorkDir"
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
