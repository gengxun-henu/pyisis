# ISIS 9.0.0 Windows SDK/Runtime Prefix

This directory owns the ISIS side of the Windows native pyisis port.

The scripts fetch ISIS 9.0.0 source code into a generated local directory, apply
tracked patches, configure with MSVC and Ninja, build the SDK/runtime subset,
install it into a local prefix, and verify the installed prefix. Source fetching
defaults to a sparse Git checkout of the `9.0.0` tag because it keeps the source
patchable and avoids GitHub archive resume issues seen on Windows. The archive
path remains available with `fetch_isis.ps1 -Method archive`; it prefers
`curl.exe` when available and falls back to PowerShell's `Invoke-WebRequest`.
The default archive format is `tar.gz`; pass `-ArchiveFormat zip` to use zip
extraction instead. The archive path supports `-DownloadTimeoutSeconds`,
`-DownloadRetries`, `-LowSpeedLimitBytesPerSecond`, and
`-LowSpeedTimeoutSeconds` so slow network failures are reported at the fetch
layer instead of hanging silently.

Default local paths:

- source: `build/windows/external/isis-9.0.0-src`
- build: `build/windows/isis-build`
- prefix: `build/windows/isis-prefix`

The prefix is considered usable for the first pyisis milestone when
`verify_isis_prefix.ps1` passes.

After the prefix verifies, run `test_isis_apps_smoke.ps1` for a lightweight
end-to-end check of common ISIS applications. The default smoke set covers
metadata, label export, geometry, reprojection, image export, cube stacking, and
expression-generated cube output. Use `-ListCommands` to print the command set
without running it.

## Current Windows Configure/Build Status

The Windows environment should be created under a short prefix, for example
`E:\code\pyisis-win-env`, and micromamba should be run with a short root prefix,
for example `--root-prefix E:\code\pyisis-win-mamba-root`. Longer worktree-local
package caches have failed while extracting deep Qt and Bullet include paths.

The current patch queue gets ISIS 9.0.0 past the first Windows/MSVC build
barriers:

- `0001-detect-windows-os-version.patch` adds Windows OS version detection to
  the upstream CMake utility.
- `0002-windows-cmake-portability.patch` adds MSVC-oriented CMake flags,
  optional docs, Windows library filtering, Windows-aware GeoTIFF/OpenCV
  discovery, optional PCL/NN-dependent objects, CMake-native copy/plugin
  generation, MSVC-safe app MOC handling, and the MSVC compatibility header.
- `0003-windows-code-generation-commands.patch` replaces shell-dependent code
  generation commands with CMake commands.
- `0004-windows-isis-core-msvc-portability.patch` carries the source-level
  portability fixes needed so the core ISIS objects and mission apps
  compile with MSVC.
- `0005-windows-lazy-geos-global-factory.patch` defers the GEOS
  `GeometryFactory` used by `PolygonTools` until first use.
- `0006-windows-pvl-binary-read.patch` opens PVL input streams in binary mode
  to keep nested-object stream positions stable on Windows.
- `0007-windows-blob-binary-read.patch` opens blob/table input streams in
  binary mode so `StartByte` offsets are byte-accurate on Windows.
- `0008-windows-cube-close-before-remove.patch` delays cube file removal until
  after the label/data `QFile` handles are closed, which Windows requires for
  `Cube::close(remove=true)`.

With the tracked environment file and these patches, CMake configure/generation
passes on Windows with MSVC and Ninja. The configure script generates MSVC
import libraries for the conda BLAS/LAPACK DLLs, and the CMake patch allows the
core ISIS target to export `objects/isis.lib` beside `lib/isis.dll`.

The current dependency posture is:

- Qwt is provided by `qwt=6.2.0`.
- `highfive`, CSM, JAMA, TNT, protobuf, USGSCSM, GeoTIFF, and OpenCV are
  resolved from the conda environment.
- PCL is not currently available in the environment, so Embree/PCL shape model
  objects are disabled for this milestone.
- NN is not currently available in the environment, so `cnet2dem`'s
  `NaturalNeighborRadius` support is disabled for this milestone.
- SuperLU and X11 can remain unresolved because the Windows CMake path filters
  `*-NOTFOUND` entries out of the aggregate include/library lists.

Verified so far:

- The patch queue applies cleanly to a fresh ISIS 9.0.0 checkout.
- `cmake --build build\windows\isis-build --target isis --config Release -j 1`
  has linked the core ISIS DLL/import library in this local porting worktree.
- `cmake --build build\windows\isis-build --config Release -j 1` has completed
  the local all-target ISIS build, including mission plugin DLLs and CLI/GUI
  executables.
- `cmake --install build\windows\isis-build` installs headers, import
  libraries, runtime DLLs, plugin metadata, XML files, and executables into the
  local prefix. ISIS runtime DLLs are installed under `prefix\lib` by the
  upstream CMake rules.
- `verify_isis_prefix.ps1` passes against `build\windows\isis-prefix`,
  including a direct `isis.dll` load probe with `ISISROOT` set to the prefix.
- `test_isis_apps_smoke.ps1` passes against `build\windows\isis-prefix` for
  `stats`, `getkey`, `catlab`, `campt`, `reduce`, `cam2map`, `isis2std`,
  `cubeit`, and `fx`.

Use `-j 1` with MSVC for now; higher parallelism has exposed intermittent
object-list and file-lock issues in this porting environment.

## ISIS 10 Allowlisted Application Targets

ISIS 10 keeps application implementations out of the monolithic `isis.dll`.
Selected Windows applications are instead compiled into independent executable
targets from `windows-app-manifest.json`. The initial `reduce` target passed its
hosted Windows build/install/Cube smoke. Wave 2 expanded the allowlist to 21 base
APPs: `algebra`, `bit2bit`, `catlab`, `crop`, `cubeatt`, `cubediff`,
`cubenorm`, `enlarge`, `fillgap`, `flip`, `fx`, `getkey`, `gradient`, `mask`,
`mirror`, `noisefilter`, `ratio`, `reduce`, `stats`, `stretch`, and `trim`.
The complete W1 promotion adds all 48 high-value/easy-ranked APPs for 69 total
targets across base, control, LRO, and MEX. Every target receives the hosted
compile/install and startup gate; mission-data behavior remains a later,
data-dependent validation layer.
The next 20-APP promotion raises the allowlist to 89 targets. It adds the three
high-value/medium-risk tools `cam2map`, `spiceinit`, and `pointreg`, followed by
17 general/easy base tools: `bandtrim`, `barscale`, `camtrim`, `cathist`,
`cropspecial`, `cubeavg`, `cubefunc`, `decorstretch`, `divfilter`, `fakecube`,
`gaussstretch`, `greyscale`, `handmos`, `hist`, `histeq`, `histmatch`, and
`interestcube`. The hosted 89-APP compile/install and startup gate passed for
all of these targets.

The following general/easy promotion raises the allowlist to 109 targets:
`kernfilter`, `mapsize`, `mvstats`, `nocam2map`, `overlapstats`, `phocube`,
`phoemplocal`, `photrim`, `pixel2map`, `ringsautomos`, `ringsmappt`,
`sigmastretch`, `skymap`, `slpmap`, `specdivfilter`, `spiceserver`, `svfilter`,
`trimfilter`, `uncrop`, and `fplanemap`. The hosted 109-APP compile/install and
startup gate passed for all of these targets.

The next source-size-prioritized promotion raises the allowlist to 129 targets.
It adds the control tools `warp` and `sumspice`, plus 18 compact mission tools:
`rolo2isis`, `hirdr2isis`, `clemhirescal`, `apollocal`, `mer2isis`,
`ocams2isis`, `dawnvir2isis`, `mrf2isis`, `hyb2onc2isis`, `mimap2isis`,
`rososiris2isis`, `lrolola2isis`, `lorri2isis`, `crism2isis`, `lo2isis`,
`dawnfc2isis`, `mar10cal`, and `tagcams2isis`. The hosted 129-APP
compile/install and startup gate passed for all of these targets.

The following source-size-prioritized mission promotion raises the allowlist to
149 targets: `gllssi2isis`, `thm2isis`, `ctxcal`, `kaguyasp2isis`,
`mroctx2isis`, `clemnircal`, `kaguyatc2isis`, `clemuvviscal`, `leisa2isis`,
`voycal`, `msi2isis`, `mvic2isis`, `apollo2isis`, `mdis2isis`,
`junocam2isis`, `moccal`, `eis2isis`, `mar102isis`, `amica2isis`, and
`ciss2isis`. Their only ranked blocker is mission runtime data; the build gate
therefore validates compile, install, and startup rather than data-dependent
processing. The hosted 149-APP compile/install and startup gate passed for all
of these targets.

The next promotion completes the remaining W3 queue and raises the allowlist to
169 targets. It adds `vims2isis`, `vimscal`, `chan1m32isis`, `clem2isis`,
`gllnims2isis`, `gllssical`, `nirs2isis`, `kaguyami2isis`, `mical`,
`mdiscal`, `hi2isis`, `hical`, `marci2isis`, `rosvirtis2isis`,
`tgocassis2isis`, `vikcal`, and `voy2isis`, followed by the compact W4 tools
`isisui`, `vicar2isis`, and `specadd`. Source review found no new compile-time
Windows patch requirement. Data-dependent mission behavior and the
`voy2isis` IMQ `vdcomp` path remain outside startup smoke coverage. These
additions passed the hosted 169-APP compile, install, prefix, and startup gate.
ISIS 10 APP support remains experimental pending the broader release matrix.

The hosted APP gate caches both the CMake build tree and installed ISIS prefix.
Its exact key includes the Windows/ISIS version, conda environment, porting
scripts and patches, plus a hash of the sorted APP names. Smoke-only changes
therefore restore the completed prefix and skip the ISIS rebuild. A later APP
wave can restore the newest compatible earlier wave through the build-input
key and incrementally configure and compile only its additions. Cache entries
are not shared across ISIS versions or incompatible build inputs.

After fetching ISIS 10.0.0 and applying
`patches\10.0.0`, configure and build the target with:

```powershell
$manifest = Get-Content `
  .\ports\windows\isis\windows-app-manifest.json `
  -Raw | ConvertFrom-Json
$apps = @($manifest.apps | ForEach-Object { $_.name })

.\ports\windows\isis\configure_isis.ps1 `
  -SourceDir $env:PYISIS_WINDOWS_ISIS_SOURCE `
  -BuildDir $env:PYISIS_WINDOWS_ISIS_BUILD `
  -Prefix $env:PYISIS_WINDOWS_ISIS_PREFIX `
  -IsisVersion 10.0.0 `
  -WindowsApps $apps

.\ports\windows\isis\build_isis.ps1 `
  -BuildDir $env:PYISIS_WINDOWS_ISIS_BUILD `
  -Jobs 1

.\ports\windows\isis\install_isis.ps1 `
  -BuildDir $env:PYISIS_WINDOWS_ISIS_BUILD

.\ports\windows\isis\test_isis_app_batch_smoke.ps1 `
  -Prefix $env:PYISIS_WINDOWS_ISIS_PREFIX `
  -IsisVersion 10.0.0
```

Each CMake target uses the `<name>_app` form to avoid case-insensitive
target-name collisions; installed executable names remain `<name>.exe`. The
batch smoke first starts every manifest APP with `-HELP`, then runs small real
Cube operations for the selected base tools. A successful build alone is not a
support claim. Same-version Linux numerical comparison and data-dependent
mission workflows must also pass before the manifest status can be promoted.

## Full APP Porting Priority

`windows-app-priority.csv` ranks all 365 APPs found at the pinned ISIS 10
source revision. `windows-app-priority.md` summarizes the recommended waves and
the top 40 candidates. The two scores are deliberately separate:

- portability estimates Windows implementation and runtime-test convenience
  from source-level platform, process, optional-stack, GUI, size, and
  mission-data signals;
- importance is calibrated for planetary navigation mapping, geometry,
  control networks, data conversion, and common image processing.

Regenerate both files after changing the pinned source or scoring policy:

```powershell
python .\ports\windows\isis\rank_isis_apps.py `
  --source-root .\reference\upstream_isis\10.0.0 `
  --manifest .\ports\windows\isis\windows-app-manifest.json `
  --csv-output .\ports\windows\isis\windows-app-priority.csv `
  --summary-output .\ports\windows\isis\windows-app-priority.md
```

The ranking is planning evidence, not a Windows support claim. An APP advances
only after the manifest, hosted compile/install, focused smoke, and applicable
cross-platform result checks pass.

Promote a complete ranked wave before regenerating the priority outputs:

```powershell
python .\ports\windows\isis\promote_windows_app_wave.py `
  --manifest .\ports\windows\isis\windows-app-manifest.json `
  --priority-csv .\ports\windows\isis\windows-app-priority.csv `
  --wave W1-high-value-easy `
  --expected-additions 48
```

Use `--apps` when one delivery batch intentionally takes an exact subset from a
larger ranked wave. Every requested APP must belong to the named wave:

```powershell
python .\ports\windows\isis\promote_windows_app_wave.py `
  --manifest .\ports\windows\isis\windows-app-manifest.json `
  --priority-csv .\ports\windows\isis\windows-app-priority.csv `
  --wave W3-general-easy `
  --expected-additions 2 `
  --apps bandtrim barscale
```
