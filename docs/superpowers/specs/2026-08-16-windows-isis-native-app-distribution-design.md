# Windows ISIS 9 Native APP Distribution Design

## Status

Approved in the M05 design session on 2026-08-16.

## Purpose

Define an implementation-ready first release of standalone USGS ISIS 9.0.0
applications for Windows 11 x64. The product targets scientific and developer
users who need a zero-install archive. It is separate from every PyISIS wheel
and must run after extraction without conda, the build prefix, the source tree,
administrator privileges, or Windows installer integration.

## Scope and Product Boundary

The first release is one curated portable ZIP containing exactly 151 public
applications: the 150 tracked ISIS 9 command-line applications plus `qnet`.
It includes the recursive runtime dependency closure, application XML, Qt and
ISIS plugins, preferences, appdata, launchers, and minimum bootstrap/test
ISISDATA. A user may override the bundled data with a complete external
ISISDATA tree.

The release does not contain PyISIS wheels, Python bindings, the complete ISIS
mission-data corpus, headers, import or static libraries, CMake files, build
caches, installers, or an unfiltered copy of the installed ISIS prefix. Windows
10 and ARM64 are not supported by this release.

## Package Format and Artifact Contract

The release archive and retained reports are fixed as:

- `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64.zip`
- `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json`
- `build/windows/reports/isis-native-apps-9.0.0-win64-validation.json`

The ZIP contains one root directory named
`usgs-isis-native-apps-9.0.0-win64`:

```text
usgs-isis-native-apps-9.0.0-win64/
├── bin/                  # public APPs, approved helpers, and bin/xml
├── lib/                  # isis.dll and recursive non-system DLL closure
├── plugins/              # Qt/ISIS plugins and plugin metadata
├── appdata/              # templates, translations, and ISIS runtime assets
├── data/                 # minimum bootstrap/test ISISDATA
├── launch/
│   ├── isis-env.cmd
│   ├── isis-shell.cmd
│   ├── isis-app.cmd
│   ├── qnet.cmd
│   └── isis-launch.ps1
├── manifest/
│   ├── apps.json
│   ├── files.sha256
│   └── build-metadata.json
├── IsisPreferences
├── LICENSE.md
└── README.md
```

The archive is constructed with stable member ordering, normalized timestamps,
and normalized file attributes. `manifest/files.sha256` covers every payload
file except itself and records repository-relative POSIX paths. The validation
report records the final ZIP SHA-256 separately.

## Explicit First-Release APP Inventory

The 150 CLI APP names are exactly the sorted `apps[].name` values from
`ports/windows/isis/windows-app-manifest.json` at design time. The design-time
manifest SHA-256 is
normalized-LF SHA-256 `bca645e1bf9ba3594ef48be0cb3fbec642a98da1e6f1b91b31a4aaa9519987d5`.
The loader normalizes CRLF/CR to LF before hashing so the same tracked manifest
has one contract identity on Windows and Linux.
The release staging command must fail if the manifest no longer contains
exactly these 150 names unless a later approved design changes the inventory.

```text
algebra, amica2isis, apollo2isis, apollocal, ascii2isis, automos, autoseed,
bandtrim, barscale, bit2bit, cam2map, caminfo, campt, camrange, camstats,
camtrim, cathist, catlab, ciss2isis, clemhirescal, clemnircal, clemuvviscal,
cnetadd, cnetcheck, cnetdiff, cnetedit, cnetextract, cnethist, cnetmerge,
cnetref, cnetstats, crism2isis, crop, cropspecial, csv2table, ctxcal, cubeatt,
cubeavg, cubediff, cubefunc, cubeit, cubenorm, dawnfc2isis, dawnvir2isis,
decorstretch, divfilter, dsk2isis, eis2isis, enlarge, fakecube, fillgap,
findimageoverlaps, fits2isis, flip, footprintinit, footprintmerge, fplanemap,
fx, gaussstretch, getkey, gllssi2isis, gradient, greyscale, handmos,
hirdr2isis, hist, histeq, histmatch, hrsc2isis, hyb2onc2isis, interestcube,
isis2fits, isis2pds, isis2std, jigsaw, junocam2isis, kaguyasp2isis,
kaguyatc2isis, kernfilter, leisa2isis, lo2isis, lorri2isis, lrolola2isis,
lronac2isis, lronaccal, lronacecho, lrowac2isis, lrowaccal, makecube,
map2cam, map2map, mapgrid, maplab, mapmos, mappt, mapsize, maptemplate,
maptrim, mar102isis, mar10cal, mask, mdis2isis, mer2isis, mimap2isis,
mirror, moccal, mosrange, mrf2isis, mroctx2isis, msi2isis, mvic2isis,
mvstats, nocam2map, noisefilter, ocams2isis, overlapstats, pds2isis, phocube,
phoemplocal, photrim, pixel2map, pointreg, ratio, raw2isis, reduce,
ringsautomos, ringsmappt, rolo2isis, rososiris2isis, sigmastretch, skymap,
slpmap, specdivfilter, spicefit, spiceinit, spiceserver, stats, std2isis,
stretch, sumspice, svfilter, table2cube, tabledump, tagcams2isis, thm2isis,
trim, trimfilter, uncrop, voycal, warp
```

`qnet` is the 151st public APP and the only public APP added outside the tracked
CLI manifest. `reduce`, `jigsaw`, and `qnet` are mandatory and receive both
specific presence checks and launch tests. Other executable files may enter the
archive only when dependency or launch evidence classifies them as non-public
runtime helpers in `manifest/build-metadata.json`; they do not expand the
supported APP inventory.

## Staging and Dependency Data Flow

1. Resolve and validate the ISIS prefix, dependency prefix, tracked APP
   manifest, minimal-data source, staging directory, and output paths.
2. Verify the prefix reports ISIS 9.0.0. Verify the tracked manifest hash and
   exact 150-name inventory, then add `qnet` to the public release manifest.
3. Copy each public executable and the applicable APP XML. `qnet` is a native
   GUI application and does not require a synthetic CLI XML file.
4. Seed dependency discovery with all public executables, approved helper
   executables, and `isis.dll`. Walk normal PE imports and export-forwarder
   targets recursively with MSVC `dumpbin`.
5. Exclude only a documented Windows system-DLL allowlist. Resolve every other
   DLL from the ISIS/dependency prefixes and copy it once to the staged runtime.
   Emit the source, destination, parents, import kind, and SHA-256 in the DLL
   dependency report.
6. Copy Qt plugin categories and ISIS plugin metadata through explicit
   allowlists. Do not broaden a directory glob to silence an unresolved loader
   failure.
7. Copy `IsisPreferences`, required `appdata`, licenses, and the curated
   minimal-data payload. The minimal-data source is the repository-owned
   `packaging/isisdata-minimal` payload, not the full external ISISDATA tree or
   arbitrary test outputs.
8. Generate launchers and manifests, scan for forbidden content and absolute
   build/conda paths, calculate payload hashes, and create the deterministic
   ZIP.
9. Discard the staging tree only after the archive and both reports have been
   independently resolved, hashed, and validated.

## Launcher Contract

`launch/isis-env.cmd` is the only environment-setup implementation. It resolves
the package root relative to `%~dp0`, sets `ISISROOT` and `ISIS_PREFIX` to that
root, prepends bundled `bin`, `lib`, and required runtime directories to PATH,
and points Qt at the bundled plugins. It must not preserve conda or source-prefix
runtime entries as hidden dependencies.

If the caller's `ISISDATA` names an existing directory, the launcher preserves
it. Otherwise it sets `ISISDATA` to the bundled `data` directory. A nonexistent
explicit `ISISDATA` is an error rather than a reason to silently fall back.

`isis-shell.cmd` opens a command shell after applying `isis-env.cmd`.
`isis-app.cmd <name> [arguments...]` rejects names absent from
`manifest/apps.json`, applies the same environment, and invokes the selected
APP without string re-evaluation. `qnet.cmd` is double-clickable. Both process
launching CMD entry points capture the already parsed `%~1` values into indexed
environment slots with delayed expansion disabled, then invoke an internal
`isis-launch.ps1` worker without reinserting `%*` into another command line.
The worker rebuilds argv from those slots and invokes with splatting; it never
rebuilds or evaluates a command string. Users are not required to edit PATH or create 151
per-APP wrapper scripts.

## Validation Matrix

Validation runs on Windows 11 x64 against a freshly extracted ZIP in a path
containing spaces. The gate scrubs `CONDA_PREFIX`, `ISISROOT`, `ISIS_PREFIX`,
`ISISDATA`, Qt plugin variables, the source prefix, and repository build paths
from the inherited environment before invoking package launchers. A hosted
clean Windows user or runner must repeat the launch matrix without access to
the source/build prefix; a local scrubbed-environment run is useful iteration
evidence but is not the final clean-machine claim.

Required validation cases are:

- archive structure, single root directory, forbidden-content scan, and exact
  151-name public inventory;
- recomputation of all payload, DLL-report, validation-report-input, and final
  archive SHA-256 values;
- empty unresolved non-system dependency set and successful loader probes;
- `-HELP` startup for all 150 CLI APPs, with 150 passes, zero failures, and zero
  skips;
- real minimal-data operations for `stats`, `getkey`, `catlab`, `campt`,
  `reduce`, `cam2map`, `isis2std`, `cubeit`, and `fx`;
- GUI launch probes for `reduce -gui`, `jigsaw -gui`, and `qnet`: each process
  must remain healthy long enough to create a visible top-level window without
  a DLL or Qt plugin loader error, after which the harness closes it cleanly;
- one representative CLI operation with a verified external ISISDATA override;
- negative launcher checks for an undeclared APP name and a nonexistent
  explicit ISISDATA directory.

The schema is closed. Six exact groups account for 166 passed probes: one
extraction, 150 CLI help, nine real operations, three GUI, one external
ISISDATA, and two negative launcher probes. Each group records its exact
package-relative commands and one exit code per pass. The negative undeclared
APP and invalid-ISISDATA probes must return 4 and 3 respectively; every other
recorded exit code is zero. Host OS/build, architecture, ISIS version, the
clean extraction path, scrubbed variables/PATH-entry count, and the archive
hash are recorded once in exact top-level provenance fields. Unknown keys or
groups, count mismatches, failures, or skips are fatal.

## Failure Handling

Staging and validation fail closed when the public inventory is not exactly
151; a mandatory executable or required XML/resource is absent; an unexpected
public executable appears; a non-system DLL remains unresolved; a required Qt
or ISIS plugin is missing; a file escapes the staging root; an absolute
build/conda path is embedded; forbidden development or PyISIS-wheel content is
present; a launcher depends on the source prefix; or a recorded hash cannot be
recomputed.

Failures are corrected by updating an explicit manifest, dependency rule, or
focused test with evidence. Copying the complete prefix, weakening the support
claim, adding broad globs, or borrowing DLLs from a live conda PATH is not an
acceptable workaround.

## Retention and Cleanup

Before cleanup, resolve the absolute paths of the final ZIP, dependency report,
and validation report and recompute their hashes. Retain only those three build
artifacts plus tracked design, implementation, and completion-evidence files.
Remove disposable staging trees, extracted clean-test directories, temporary
logs, and test environments created solely for the package build.

Do not delete the source ISIS prefix, reference source checkouts, reusable test
or mission data, or user files. Do not modify `.gitignore` or `print.prt`.

## Implementation Boundary

This M05 milestone approves the design only. Implementation is a subsequent
planned milestone. It may extend the existing Windows runtime staging and smoke
infrastructure, but it must preserve the separate PyISIS-wheel product boundary
and add focused tests before packaging behavior. No APP archive is built or
published as part of M05.
