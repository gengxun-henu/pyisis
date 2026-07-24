# ISIS Version Expansion Policy

## Purpose

This document defines the mandatory workflow for adding a new USGS ISIS version
to this repository. `AGENTS.md` and `CLAUDE.md` both require repository agents
to follow it.

The goal is not merely to compile against a new prefix. A version expansion is
complete only when the installed API has been fully audited, every discovered
change has a disposition, supported bindings are implemented and tested, and
the required release matrix passes.

## 1. Identify the Exact Target

Record all of the following before comparing or binding:

- official ISIS semantic version
- official source tag and commit
- conda package name and version
- conda build string and build number
- conda channel and subdir
- operating system and architecture
- compiler, Python version, and Python ABI
- relevant dependency transitions such as Qt, GDAL, CSPICE, or SpiceQL

Never assume that two packages named `isis X.Y.Z` expose identical APIs.
Channel-specific builds may apply patches that are absent from the official
tag. When the installed prefix and the official source differ, record the
difference and bind against the installed prefix.

## 2. Use Multiple Evidence Sources

Use these sources together:

1. target conda headers and libraries: compile/link authority
2. previous supported conda headers and libraries: compatibility baseline
3. official tagged source: implementation, lifecycle, tests, and call sites
4. official `CHANGELOG.md` and release page: Added, Changed, Deprecated,
   Removed, and Breaking intent
5. conda recipe or patch set when available: package-specific divergence
6. application XML, CMake install rules, plugin files, and public documentation
7. actual Linux and Windows exported library symbols

The Changelog is evidence, not a complete API manifest. A change missing from
the Changelog still requires classification if it appears in the installed
package.

## 3. Generate a Bidirectional Raw Diff

The raw inventory must discover, rather than presuppose:

- added installed headers
- removed installed headers
- likely renames or compatibility replacements
- byte-changed headers with the same name
- added, removed, or changed public classes
- inheritance changes
- constructor and method signature changes
- free-function and callable-application changes
- enum and constant changes
- default-argument and const-qualification changes
- `@deprecated`, deprecation macro, or replacement guidance changes
- installed library additions/removals and exported-symbol changes

File-name comparison alone is insufficient. Content-only and ABI changes must
remain visible even when a header name is unchanged.

## 4. Separate Discovery from Binding Decisions

Maintain two layers:

- **Raw diff:** complete machine-discovered version/package differences.
- **Curated inventory:** human-reviewed Python binding decisions, priorities,
  API details, risks, and validation state.

Every raw item must receive exactly one auditable disposition:

- `bind`: public, useful, linkable, and suitable for Python
- `compatibility`: rename or compatibility surface already represented
- `replaced`: obsolete API with a documented replacement
- `excluded`: GUI, Qt signal/slot plumbing, fixture, generated/internal,
  third-party implementation, empty placeholder, or unsuitable raw ownership
- `blocked`: potentially useful but currently not linkable or testable, with a
  concrete blocker and revisit condition

No item may silently disappear between raw discovery and the curated queue.
"All new functionality complete" means every discovered item has a disposition
and every `bind` item is implemented and verified. It does not require exposing
unsafe or internal APIs.

## 5. Verify Bindability and ABI

For each proposed binding:

1. read the active conda header
2. read the official or package-matched implementation
3. read upstream tests and representative call sites
4. identify runtime data and plugin dependencies
5. verify constructor and method symbols in the target libraries
6. verify inheritance registration and object lifetime
7. design Python adapters for `QString`, Qt containers, raw pointers,
   `UserInterface`, output parameters, and ownership-sensitive APIs

Run symbol checks separately for:

- Linux shared libraries (`.so`)
- Windows DLLs and import libraries (`.dll`, `.lib`)

A header declaration is not sufficient evidence that a callable symbol exists.

## 6. Preserve Multi-Version Maintainability

- Keep compatible ISIS 9/10/later bindings in shared source files.
- Use compile-time feature/version guards for genuine API differences.
- Put version-only bindings in a small, explicit version module.
- Keep Python names and behavior stable across versions where the underlying
  semantics are compatible.
- Test both symbol presence in the newer version and intentional absence or
  fallback behavior in older versions.
- Do not copy the full binding directory for each ISIS version.

## 7. Required Records

Update these artifacts together when applicable:

- raw version-difference inventory
- curated class/function summaries
- per-class method inventories
- compatibility report
- `pybind_progress_log.md`
- build and test reports
- release plan and user installation documentation

Each record must state which exact ISIS package build and platform produced the
result.

## 8. Release Gate

For the current ISIS 9 and ISIS 10 release objective, all four lanes are
required:

| Platform | ISIS target | Required result |
|---|---|---|
| Linux | ISIS 9 | build, wheel install, import, focused tests |
| Linux | ISIS 10 | build, wheel install, import, focused tests |
| Windows | ISIS 9 | build, wheel install, import, focused tests |
| Windows | ISIS 10 | build, wheel install, import, focused tests |

Before publishing:

- verify a clean installation into a fresh environment
- verify bundled or resolved runtime libraries
- record Python ABI and architecture
- run version-gated symbol tests
- retain wheels/installers, reports, checksums, and required shared libraries
- remove disposable build and staging directories after artifact verification

Do not publish a partial matrix as a complete dual-version release. If an
experimental asset is intentionally published, label its limitations explicitly
and keep it separate from the final release gate.
