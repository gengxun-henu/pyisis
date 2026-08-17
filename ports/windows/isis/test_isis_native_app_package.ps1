param(
    [string]$Archive,
    [string]$ReleaseConfig,
    [string]$WorkDir,
    [string]$Report,
    [string]$GuiProbeFixtureRoot,
    [Parameter(ValueFromRemainingArguments = $true)][object[]]$RuntimeArguments = @()
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

# PowerShell rejects a normally declared array parameter when callers repeat
# its name. Parse the documented repeatable -ForbiddenPath form explicitly.
$ForbiddenPath = New-Object System.Collections.Generic.List[string]
for ($argumentIndex = 0; $argumentIndex -lt $RuntimeArguments.Count; $argumentIndex += 2) {
    if ([string]$RuntimeArguments[$argumentIndex] -cne "-ForbiddenPath" -or $argumentIndex + 1 -ge $RuntimeArguments.Count) {
        throw "unknown runtime argument; expected repeatable -ForbiddenPath <path> pairs"
    }
    $ForbiddenPath.Add([string]$RuntimeArguments[$argumentIndex + 1])
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path))
}

function Assert-PathWithin {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$Parent
    )
    $candidatePath = Resolve-FullPath $Candidate
    $parentPath = (Resolve-FullPath $Parent).TrimEnd('\') + '\'
    if (-not $candidatePath.StartsWith($parentPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "path escapes its declared parent: $candidatePath"
    }
}

function New-CheckResult {
    param([string[]]$Commands, [int[]]$ExitCodes)
    return [ordered]@{
        commands = @($Commands)
        passed = @($Commands).Count
        failed = 0
        skipped = 0
        exit_codes = @($ExitCodes)
    }
}

function Invoke-PackageLauncher {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][int]$ExpectedExitCode,
        [Parameter(Mandatory = $true)][string]$LogName
    )
    $logPath = Join-Path $resolvedWorkDir $LogName
    $runnerPath = Join-Path $resolvedWorkDir ("runtime-launch-" + [Guid]::NewGuid().ToString("N") + ".cmd")
    $commandValues = @($IsisAppLauncher, $Name) + @($Arguments)
    $quotedValues = @($commandValues | ForEach-Object {
        if ([string]$_ -match '"') { throw "runtime launcher arguments must not contain quotes" }
        '"' + ([string]$_).Replace('%', '%%') + '"'
    })
    if ($logPath -match '"') { throw "runtime launcher log path must not contain quotes" }
    $logTarget = '"' + $logPath.Replace('%', '%%') + '"'
    $runnerText = "@echo off`r`nsetlocal DisableDelayedExpansion`r`n" + ($quotedValues -join " ") + " > " + $logTarget + " 2>&1`r`n"
    [System.IO.File]::WriteAllText($runnerPath, $runnerText, (New-Object System.Text.UTF8Encoding($false)))
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $env:ComSpec /d /c $runnerPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        Remove-Item -LiteralPath $runnerPath -Force -ErrorAction SilentlyContinue
    }
    if ($exitCode -ne $ExpectedExitCode) {
        $tail = ""
        if (Test-Path -LiteralPath $logPath) {
            $tail = (Get-Content -LiteralPath $logPath -Tail 40) -join [Environment]::NewLine
        }
        throw "package launcher exit mismatch for $Name (expected $ExpectedExitCode, found $exitCode)`n$tail"
    }
    return [int]$exitCode
}

function Invoke-GuiProbe {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][string]$Launcher,
        [Parameter(Mandatory = $true)][string]$ExpectedExecutable,
        [Parameter(Mandatory = $true)][string]$StandardOutputLog,
        [Parameter(Mandatory = $true)][string]$StandardErrorLog
    )

    $expectedPath = Resolve-FullPath $ExpectedExecutable
    $beforePids = @{}
    foreach ($item in @(Get-CimInstance Win32_Process)) {
        if ($item.ExecutablePath -and $item.ExecutablePath.Equals($expectedPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            $beforePids[[int]$item.ProcessId] = $true
        }
    }
    New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName((Resolve-FullPath $StandardOutputLog))) | Out-Null
    if ($Launcher.Contains('"') -or @($Arguments | Where-Object { $_.Contains('"') }).Count) {
        throw "GUI probe launcher and arguments must not contain quotes"
    }
    $launcherCommand = '"' + $Launcher + '"'
    foreach ($argument in $Arguments) { $launcherCommand += ' "' + $argument + '"' }
    $commandLine = '/d /s /c "' + $launcherCommand + '"'
    $startArguments = @{
        FilePath = $env:ComSpec
        ArgumentList = $commandLine
        PassThru = $true
        RedirectStandardOutput = $StandardOutputLog
        RedirectStandardError = $StandardErrorLog
    }
    $wrapper = Start-Process @startArguments
    $ownedPids = New-Object System.Collections.Generic.HashSet[int]
    $null = $ownedPids.Add([int]$wrapper.Id)
    $candidatePids = New-Object System.Collections.Generic.HashSet[int]
    $target = $null
    $probeError = $null
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 250
            $processRows = @(Get-CimInstance Win32_Process)
            do {
                $addedDescendant = $false
                foreach ($row in $processRows) {
                    $pidValue = [int]$row.ProcessId
                    if (-not $ownedPids.Contains($pidValue) -and $ownedPids.Contains([int]$row.ParentProcessId)) {
                        $null = $ownedPids.Add($pidValue)
                        $addedDescendant = $true
                    }
                }
            } while ($addedDescendant)
            foreach ($row in $processRows) {
                if (-not $row.ExecutablePath -or -not $row.ExecutablePath.Equals($expectedPath, [System.StringComparison]::OrdinalIgnoreCase)) { continue }
                $pidValue = [int]$row.ProcessId
                if ($beforePids.ContainsKey($pidValue) -or -not $ownedPids.Contains($pidValue)) { continue }
                $null = $candidatePids.Add($pidValue)
                $candidate = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
                if ($null -eq $candidate) { continue }
                $candidate.Refresh()
                if ($candidate.MainWindowHandle -ne 0 -and $candidate.MainWindowTitle) {
                    $target = $candidate
                    break
                }
                $candidate.Dispose()
            }
            if ($null -ne $target) { break }
            $wrapper.Refresh()
            if ($wrapper.HasExited) { throw "GUI launcher exited before the target window appeared for $Name" }
        } while ([DateTime]::UtcNow -lt $deadline)
        if ($null -eq $target -or $target.MainWindowHandle -eq 0 -or -not $target.MainWindowTitle) {
            throw "GUI launch probe failed for $Name"
        }
        $null = $target.CloseMainWindow()
    }
    catch { $probeError = $_ }
    finally {
        $cleanupPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            foreach ($processId in @($candidatePids)) {
                & taskkill.exe /PID $processId /T /F *> $null
            }
            & taskkill.exe /PID $wrapper.Id /T /F *> $null
        }
        finally {
            $ErrorActionPreference = $cleanupPreference
        }
        if (-not $wrapper.HasExited) { $null = $wrapper.WaitForExit(10000) }
        $cleanupDeadline = [DateTime]::UtcNow.AddSeconds(10)
        do {
            foreach ($row in @(Get-CimInstance Win32_Process)) {
                if ($row.ExecutablePath -and $row.ExecutablePath.Equals($expectedPath, [System.StringComparison]::OrdinalIgnoreCase) -and -not $beforePids.ContainsKey([int]$row.ProcessId)) {
                    $null = $candidatePids.Add([int]$row.ProcessId)
                }
            }
            $cleanupPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = "Continue"
                foreach ($processId in @($candidatePids)) {
                    & taskkill.exe /PID $processId /T /F *> $null
                }
            }
            finally { $ErrorActionPreference = $cleanupPreference }
            $remaining = @($candidatePids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
            if (-not $remaining) { break }
            Start-Sleep -Milliseconds 100
        } while ([DateTime]::UtcNow -lt $cleanupDeadline)
        if ($remaining -and $null -eq $probeError) {
            $probeError = "GUI cleanup left target process IDs for ${Name}: $($remaining -join ', ')"
        }
        if ($null -ne $target) { $target.Dispose() }
        $wrapper.Dispose()
    }
    if ($null -ne $probeError) { throw $probeError }
}

function Assert-OutputFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "expected output file was not created: $Path"
    }
    if ((Get-Item -LiteralPath $Path).Length -le 0) {
        throw "expected output file is empty: $Path"
    }
}

if ($GuiProbeFixtureRoot) {
    $fixtureRoot = Resolve-FullPath $GuiProbeFixtureRoot
    foreach ($fixtureName in @("reduce", "jigsaw", "qnet")) {
        Invoke-GuiProbe `
            -Name $fixtureName `
            -Arguments @() `
            -Launcher (Join-Path $fixtureRoot "$fixtureName.cmd") `
            -ExpectedExecutable (Join-Path $fixtureRoot "$fixtureName.exe") `
            -StandardOutputLog (Join-Path $fixtureRoot "$fixtureName-stdout.log") `
            -StandardErrorLog (Join-Path $fixtureRoot "$fixtureName-stderr.log")
    }
    $global:LASTEXITCODE = 0
    return
}

foreach ($requiredInput in @($Archive, $ReleaseConfig, $WorkDir, $Report)) {
    if ([string]::IsNullOrWhiteSpace($requiredInput)) {
        throw "Archive, ReleaseConfig, WorkDir, and Report are required for the production runtime matrix"
    }
}

$resolvedArchive = Resolve-FullPath $Archive
$resolvedReleaseConfig = Resolve-FullPath $ReleaseConfig
$resolvedWorkDir = Resolve-FullPath $WorkDir
$resolvedReport = Resolve-FullPath $Report
if (Test-Path -LiteralPath $resolvedReport) {
    if (-not (Test-Path -LiteralPath $resolvedReport -PathType Leaf)) { throw "runtime report target is not a file: $resolvedReport" }
    Remove-Item -LiteralPath $resolvedReport -Force
}
if (-not (Test-Path -LiteralPath $resolvedArchive -PathType Leaf)) { throw "archive not found: $resolvedArchive" }
if (-not (Test-Path -LiteralPath $resolvedReleaseConfig -PathType Leaf)) { throw "release config not found: $resolvedReleaseConfig" }
foreach ($path in $ForbiddenPath) {
    if (Test-Path -LiteralPath $path) {
        throw "forbidden path exists on the runtime host: $path"
    }
}

$release = Get-Content -Raw -LiteralPath $resolvedReleaseConfig | ConvertFrom-Json
if ($release.archive_name -cne [System.IO.Path]::GetFileName($resolvedArchive)) {
    throw "archive name does not match release config"
}
if (-not $release.root_name -or [System.IO.Path]::GetFileName([string]$release.root_name) -cne [string]$release.root_name) {
    throw "release root_name is unsafe"
}

New-Item -ItemType Directory -Force -Path $resolvedWorkDir | Out-Null
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($resolvedReport)) | Out-Null
$cleanParent = Join-Path ([System.IO.Path]::GetTempPath()) ("pyisis-native-runtime-" + [Guid]::NewGuid().ToString("N"))
$extractScratch = Join-Path $cleanParent "archive scratch"
$extractionPath = Join-Path $cleanParent "native package with spaces"
New-Item -ItemType Directory -Path $extractScratch -Force | Out-Null
Assert-PathWithin -Candidate $extractScratch -Parent $cleanParent
Assert-PathWithin -Candidate $extractionPath -Parent $cleanParent

$scrubbedVariables = @("CONDA_PREFIX", "ISISROOT", "ISIS_PREFIX", "ISISDATA", "QT_PLUGIN_PATH")
$savedEnvironment = @{}
foreach ($name in $scrubbedVariables) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}
$savedPath = $env:PATH
$pathEntriesRemoved = 0

try {
    Expand-Archive -LiteralPath $resolvedArchive -DestinationPath $extractScratch
    $roots = @(Get-ChildItem -LiteralPath $extractScratch -Force)
    if ($roots.Count -ne 1 -or -not $roots[0].PSIsContainer -or $roots[0].Name -cne [string]$release.root_name) {
        throw "archive must contain exactly the declared single root"
    }
    Move-Item -LiteralPath $roots[0].FullName -Destination $extractionPath
    Remove-Item -LiteralPath $extractScratch -Force

    $manifestPath = Join-Path $extractionPath "manifest\apps.json"
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $cliApps = @($manifest.public_cli_apps | Sort-Object)
    if ($cliApps.Count -ne 150) { throw "runtime contract must contain exactly 150 public CLI APPs" }
    if (@($manifest.public_apps).Count -ne 151 -or @($manifest.public_gui_apps) -cnotcontains "qnet") {
        throw "runtime APP manifest does not match the 151-APP release contract"
    }

    Remove-Item Env:\CONDA_PREFIX -ErrorAction SilentlyContinue
    Remove-Item Env:\ISISROOT -ErrorAction SilentlyContinue
    Remove-Item Env:\ISIS_PREFIX -ErrorAction SilentlyContinue
    Remove-Item Env:\ISISDATA -ErrorAction SilentlyContinue
    Remove-Item Env:\QT_PLUGIN_PATH -ErrorAction SilentlyContinue
    $forbiddenResolved = @($ForbiddenPath | ForEach-Object { Resolve-FullPath $_ })
    $keptPathEntries = New-Object System.Collections.Generic.List[string]
    foreach ($entry in @($savedPath -split [System.IO.Path]::PathSeparator)) {
        if (-not $entry) { continue }
        $remove = $entry -match '(?i)(^|[\\/])(build(?:[-_][^\\/]*)?|\.worktrees|src|source(?:s|[-_][^\\/]*)?|conda(?:[-_][^\\/]*)?|miniconda3?|pyisis-win-env)([\\/]|$)'
        if (-not $remove) {
            foreach ($forbidden in $forbiddenResolved) {
                if ((Resolve-FullPath $entry).StartsWith($forbidden, [System.StringComparison]::OrdinalIgnoreCase)) {
                    $remove = $true
                    break
                }
            }
        }
        if ($remove) { $pathEntriesRemoved++ } else { $keptPathEntries.Add($entry) }
    }
    $env:PATH = $keptPathEntries -join [System.IO.Path]::PathSeparator

    $IsisAppLauncher = Join-Path $extractionPath "launch\isis-app.cmd"
    $QnetLauncher = Join-Path $extractionPath "launch\qnet.cmd"
    if (-not (Test-Path -LiteralPath $IsisAppLauncher -PathType Leaf)) { throw "package APP launcher is missing" }
    if (-not (Test-Path -LiteralPath $QnetLauncher -PathType Leaf)) { throw "package qnet launcher is missing" }

    $cliCommands = New-Object System.Collections.Generic.List[string]
    $cliExitCodes = New-Object System.Collections.Generic.List[int]
    foreach ($name in $cliApps) {
        $cliCommands.Add("launch/isis-app.cmd $name -HELP")
        $cliExitCodes.Add((Invoke-PackageLauncher -Name $name -Arguments @("-HELP") -ExpectedExitCode 0 -LogName "help-$name.log"))
    }

    $operationDir = Join-Path $resolvedWorkDir "real operations"
    New-Item -ItemType Directory -Force -Path $operationDir | Out-Null
    $sourceCube = Join-Path $operationDir "source.cub"
    $cameraCube = Join-Path $extractionPath "validation-data\EN0108828322M_iof.cub"
    $mapFile = Join-Path $extractionPath "validation-data\equi.map"
    $labelOutput = Join-Path $operationDir "catlab.txt"
    $camptOutput = Join-Path $operationDir "campt.pvl"
    $reducedCube = Join-Path $operationDir "reduced.cub"
    $remappedCube = Join-Path $operationDir "cam2map.cub"
    $pngOutput = Join-Path $operationDir "preview.png"
    $cubeList = Join-Path $operationDir "cubeit.lis"
    $cubeitOutput = Join-Path $operationDir "cubeit.cub"
    $fxOutput = Join-Path $operationDir "fx.cub"

    if (-not (Test-Path -LiteralPath $cameraCube -PathType Leaf)) { throw "validation camera cube is missing: validation-data\EN0108828322M_iof.cub" }
    if (-not (Test-Path -LiteralPath $mapFile -PathType Leaf)) { throw "validation map file is missing: validation-data\equi.map" }
    [void](Invoke-PackageLauncher -Name "fx" -Arguments @("to=$sourceCube", "equation=sample+line", "mode=outputonly", "lines=64", "samples=64", "bands=1") -ExpectedExitCode 0 -LogName "setup-fx.log")

    $realExitCodes = New-Object System.Collections.Generic.List[int]
    $realExitCodes.Add((Invoke-PackageLauncher "stats" @("from=$sourceCube") 0 "stats.log")); Assert-OutputFile (Join-Path $resolvedWorkDir "stats.log")
    $realExitCodes.Add((Invoke-PackageLauncher "getkey" @("from=$sourceCube", "grpname=Dimensions", "keyword=Samples", "recursive=true") 0 "getkey.log")); Assert-OutputFile (Join-Path $resolvedWorkDir "getkey.log")
    $realExitCodes.Add((Invoke-PackageLauncher "catlab" @("from=$sourceCube", "to=$labelOutput") 0 "catlab.log")); Assert-OutputFile $labelOutput
    $realExitCodes.Add((Invoke-PackageLauncher "campt" @("from=$cameraCube", "sample=64", "line=512", "type=image", "to=$camptOutput") 0 "campt.log")); Assert-OutputFile $camptOutput
    $realExitCodes.Add((Invoke-PackageLauncher "reduce" @("from=$sourceCube", "to=$reducedCube", "sscale=2", "lscale=2") 0 "reduce.log")); Assert-OutputFile $reducedCube
    $realExitCodes.Add((Invoke-PackageLauncher "cam2map" @("from=$cameraCube", "map=$mapFile", "to=$remappedCube", "pixres=mpp", "resolution=1000", "interp=bilinear") 0 "cam2map.log")); Assert-OutputFile $remappedCube
    $realExitCodes.Add((Invoke-PackageLauncher "isis2std" @("from=$reducedCube", "to=$pngOutput", "mode=grayscale", "format=png", "stretch=linear") 0 "isis2std.log")); Assert-OutputFile $pngOutput
    Set-Content -LiteralPath $cubeList -Value @($reducedCube, $reducedCube) -Encoding ASCII
    $realExitCodes.Add((Invoke-PackageLauncher "cubeit" @("fromlist=$cubeList", "to=$cubeitOutput") 0 "cubeit.log")); Assert-OutputFile $cubeitOutput
    $realExitCodes.Add((Invoke-PackageLauncher "fx" @("to=$fxOutput", "equation=sample+line", "mode=outputonly", "lines=16", "samples=16", "bands=1") 0 "fx.log")); Assert-OutputFile $fxOutput
    $realCommands = @("stats", "getkey", "catlab", "campt", "reduce", "cam2map", "isis2std", "cubeit", "fx") | ForEach-Object { "launch/isis-app.cmd $_ mode=real-operation" }

    Invoke-GuiProbe -Name "reduce" -Arguments @("reduce", "-gui") -Launcher $IsisAppLauncher -ExpectedExecutable (Join-Path $extractionPath "bin\reduce.exe") -StandardOutputLog (Join-Path $resolvedWorkDir "gui-reduce-stdout.log") -StandardErrorLog (Join-Path $resolvedWorkDir "gui-reduce-stderr.log")
    Invoke-GuiProbe -Name "jigsaw" -Arguments @("jigsaw", "-gui") -Launcher $IsisAppLauncher -ExpectedExecutable (Join-Path $extractionPath "bin\jigsaw.exe") -StandardOutputLog (Join-Path $resolvedWorkDir "gui-jigsaw-stdout.log") -StandardErrorLog (Join-Path $resolvedWorkDir "gui-jigsaw-stderr.log")
    Invoke-GuiProbe -Name "qnet" -Arguments @() -Launcher $QnetLauncher -ExpectedExecutable (Join-Path $extractionPath "bin\qnet.exe") -StandardOutputLog (Join-Path $resolvedWorkDir "gui-qnet-stdout.log") -StandardErrorLog (Join-Path $resolvedWorkDir "gui-qnet-stderr.log")

    $externalData = Join-Path $cleanParent "external isisdata"
    New-Item -ItemType Directory -Path $externalData | Out-Null
    $env:ISISDATA = $externalData
    $externalExit = Invoke-PackageLauncher "stats" @("from=$sourceCube") 0 "external-isisdata.log"
    Remove-Item Env:\ISISDATA -ErrorAction SilentlyContinue

    $undeclaredExit = Invoke-PackageLauncher "__undeclared_app__" @() 4 "negative-undeclared.log"
    $missingData = Join-Path $cleanParent "missing isisdata"
    $env:ISISDATA = $missingData
    $missingDataExit = Invoke-PackageLauncher "stats" @("-HELP") 3 "negative-missing-data.log"
    Remove-Item Env:\ISISDATA -ErrorAction SilentlyContinue

    $osVersion = [Environment]::OSVersion.Version
    if ($osVersion.Major -ne 10 -or $osVersion.Build -lt 22000) { throw "runtime host must be Windows 11" }
    $architecture = [Environment]::GetEnvironmentVariable("PROCESSOR_ARCHITECTURE", "Process")
    if ($architecture -notin @("AMD64", "x64")) { throw "runtime host must be Windows x64" }

    $checks = [ordered]@{
        "archive-extract" = New-CheckResult @("archive-extract") @(0)
        "cli-help" = [ordered]@{ commands = @($cliCommands); passed = 150; failed = 0; skipped = 0; exit_codes = @($cliExitCodes) }
        "real-operations" = New-CheckResult @($realCommands) @($realExitCodes)
        "gui-launch" = New-CheckResult @("launch/isis-app.cmd reduce -gui", "launch/isis-app.cmd jigsaw -gui", "launch/qnet.cmd") @(0, 0, 0)
        "external-isisdata" = New-CheckResult @("launch/isis-app.cmd stats isisdata=external") @($externalExit)
        "negative-launcher" = [ordered]@{ commands = @("launch/isis-app.cmd __undeclared_app__ isisdata=bundled", "launch/isis-app.cmd stats isisdata=missing"); passed = 2; failed = 0; skipped = 0; exit_codes = @(4, 3) }
    }
    $payload = [ordered]@{
        schema_version = 1
        artifact = [ordered]@{ archive_name = [System.IO.Path]::GetFileName($resolvedArchive); archive_sha256 = (Get-FileHash -LiteralPath $resolvedArchive -Algorithm SHA256).Hash.ToLowerInvariant() }
        host = [ordered]@{ os = "Windows 11"; version = $osVersion.ToString(); architecture = $architecture }
        extraction_path = $extractionPath
        scrubbed_environment = [ordered]@{ variables = $scrubbedVariables; path_entries_removed = $pathEntriesRemoved }
        checks = $checks
        summary = [ordered]@{ passed = 166; failed = 0; skipped = 0 }
    }
    $candidate = Join-Path ([System.IO.Path]::GetDirectoryName($resolvedReport)) ("." + [System.IO.Path]::GetFileName($resolvedReport) + ".tmp-" + [Guid]::NewGuid().ToString("N"))
    try {
        [System.IO.File]::WriteAllText($candidate, (($payload | ConvertTo-Json -Depth 8) + [Environment]::NewLine), (New-Object System.Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $resolvedReport -PathType Leaf) {
            $backup = $resolvedReport + ".replace-backup"
            [System.IO.File]::Replace($candidate, $resolvedReport, $backup, $true)
            Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
        }
        else {
            [System.IO.File]::Move($candidate, $resolvedReport)
        }
    }
    finally {
        Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
    }
}
finally {
    $env:PATH = $savedPath
    foreach ($name in $scrubbedVariables) {
        $value = $savedEnvironment[$name]
        if ($null -eq $value) { Remove-Item "Env:\$name" -ErrorAction SilentlyContinue } else { [Environment]::SetEnvironmentVariable($name, $value, "Process") }
    }
    if (Test-Path -LiteralPath $cleanParent) {
        Assert-PathWithin -Candidate $cleanParent -Parent ([System.IO.Path]::GetTempPath())
        Remove-Item -LiteralPath $cleanParent -Recurse -Force
    }
}

# The final negative launcher probe intentionally returns 3. Reset the caller's
# native-command status only after the complete report has been published.
$global:LASTEXITCODE = 0
