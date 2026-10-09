# Task Plan: RC4 and ISIS 10 native Windows GUI package (M47)

## Goal

Create versioned RC4 wheel artifacts and Windows x64 native APP/GUI ZIPs for ISIS 9 and ISIS 10, with clean-host validation and release assets.

## Design

- Keep PyISIS wheels versioned independently: ISIS 9 `1.3.0rc4`, ISIS 10 `1.4.0rc4`.
- Add a versioned native release contract for ISIS 10 using the existing staging, dependency-closure, and clean-runtime validators.
- Extend the native workflow with a manual `isis_version` choice so the same Windows-hosted pipeline builds either version without mixing prefixes or archives.
- Publish separate prerelease tags and SHA256 manifests; all native ZIPs are Windows x64 artifacts.

## Phases

- [x] Update RC4 package/release metadata and native ISIS10 contract
- [x] Parameterize native Windows workflow and validate ISIS10 ZIP
- [x] Build and validate RC4 wheels on hosted Linux/Windows matrix
- [x] Create PR, merge, synchronize local main, and publish RC4 releases

## Next Step

M47 is complete. Continue with post-release runner health and the separate
Windows native CLI compatibility track; direct Windows 11 clean-runtime
revalidation is intentionally deferred.
