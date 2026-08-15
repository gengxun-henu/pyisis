# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Findings: Build and verify the ISIS 9.0.0 native prefix

## Verified Facts

- Milestone ID: `windows-isis9-m02-isis-prefix`.
- The active plan pointer and registry both select this milestone as `in_progress`.
- The current checkout is the repository-root worktree on branch `main` at
  `0c6269e7787a12d9c00d85173861a47563b15d0e`; it is four commits ahead of
  `origin/main`.
- The source plans require the pinned ISIS `9.0.0` source at commit
  `950a5606ffeaa13ddb40101fbf25a8737e88902a`, followed by the tracked Windows
  patch queue, an MSVC/Ninja serial build, prefix verification, representative
  APP smoke, and the 150-APP batch gate.
- The repository-owned default source path is
  `build/windows/external/isis-9.0.0-src`.
- The M1 readiness report and all three registered prerequisite paths exist on
  this workstation. Fresh machine-readable SHA-256 values exactly match the M1
  completion evidence in `.planning/milestones.v1.json`:
  readiness report `68fb27ba98faa908456cb1a11d379991bc43282f93fb5013eaffc1a190209489`,
  `kernel32.dll` `0ab61f2e0d412a585233f1b308c120cba74f800c1030bffe0aabd20df8c6d907`,
  MSVC `cl.exe` `dc1ef4e36c7044ae9bd0ce24d27de45f8fe26dc1210897b8717e8ef0232360e8`,
  and Micromamba `b645a5259cb92b5869b0e60943390dd0d362cae45bc7e2f5ba8c7e4a4b06c7aa`.
- The readiness report records conda-classic prefix `D:\pyisis-win-env`, the
  expected MSVC/CMake/Ninja/Python commands, and a 150-entry Windows APP
  manifest count.
- The first fetch invocation was interrupted after the shallow clone created
  `.git` and set HEAD to `950a5606ffeaa13ddb40101fbf25a8737e88902a`, but
  before sparse-checkout/reset populated the worktree. No related child process
  remained. `fetch_isis.ps1` explicitly supports resuming an existing Git
  checkout by fetching, checking out the ref, applying sparse paths, and
  resetting the worktree.
- Resuming through the Git partial-clone path reached `checkout 9.0.0`, then
  its lazy blob HTTPS request remained connected to GitHub for about seven
  minutes while the temporary pack stayed at 0 bytes. The outer execution
  termination did not stop four child Git processes; their command lines were
  verified and those exact PIDs were stopped. The partial source directory was
  preserved unchanged for provenance and diagnosis.
- The documented archive fallback retried four connections to
  `github.com:443`; each failed after about 21 seconds with curl exit 28
  (`Could not connect to server`). It produced no usable archive source tree.
- On resume, a fresh `curl.exe` probe of the same ISIS 9.0.0 GitHub archive URL
  returned HTTP 302 with a 0.163580-second connect time and 0.949252-second
  total time. This is recorded in `resolution-evidence.json` and was accepted
  by the milestone manager to clear the exact recorded network blocker.
- The resumed archive fetch initially wrote payload bytes (up to about 9.5 MB)
  but later regressed to 0 bytes. The 15-minute execution controller timed out
  while its child curl process remained active and reconnected to GitHub. That
  exact orphaned `curl.exe` was stopped after command-line verification. A
  successful HTTP redirect/handshake therefore does not establish the sustained
  payload transfer required to fetch the source.
- A subsequent 1 MiB Range probe to the same archive URL connected in 1.179032
  seconds but received 0 bytes; it failed after 29.210310 seconds with curl 56
  (`Recv failure: Connection was reset`). No fetch-related process remained
  after the probe.
- A later fresh 1 MiB, 30-second payload probe again received 0 bytes and
  failed with HTTP 000 / curl 56 after about 27.5 seconds, so the recorded
  sustained-transfer blocker remains current.
- The GitHub entry endpoint redirects to
  `https://codeload.github.com/DOI-USGS/ISIS3/tar.gz/refs/tags/9.0.0`. A direct
  64 KiB Range request to that codeload URL returned HTTP 200 (not 206) and
  transferred 648,725 bytes in 30 seconds before curl timed out. This proves
  that codeload payload transfer can begin but does not honour the byte-range
  request used by curl's `--continue-at -` resume path.
- Read-only searches of the conda and micromamba caches under
  `C:\Users\gx\miniconda3\pkgs`, `D:\mamba\pyisis-runner\pkgs`,
  `C:\Users\gx\.mamba\pkgs`, and
  `C:\Users\gx\AppData\Roaming\.mamba\pkgs` found no ISIS 9.0.0 source
  archive or reusable cached package. A ref/object search under `D:\code` and
  `C:\Users\gx` found the pinned commit only in the already preserved partial
  checkout. Official USGS developer documentation continues to identify the
  GitHub repository as the primary source-code distribution; no independent
  official ISIS 9.0.0 source mirror was found.

## Evidence-Based Inference

- The first valid uncompleted task is source fetch/identity verification. The
  historical "Verified so far" section in `ports/windows/isis/README.md` is
  context only and does not satisfy M2's fresh evidence gate.
- The archive script's unconditional `--continue-at -` can be incompatible
  with the observed codeload response: retrying a partially downloaded file
  relies on byte-range support that the endpoint did not provide. A minimal
  script correction, with a focused regression check, must be evaluated before
  treating another archive retry as meaningful.

## Unresolved Items

- Completion evidence has not yet been produced.
- The interrupted checkout must be resumed and then verified as clean at the
  pinned commit/tag, or the documented archive fallback must produce a usable
  source tree whose tag provenance is cross-checked against the preserved Git
  metadata, before the fetch task can be marked complete.
- Before declaring an external-network blocker, inspect local repository and
  workstation paths for an existing source/object copy at the pinned commit.
  That search found no usable second copy under the repository, `reference/`,
  `build/windows/external/`, or `D:\code`.
- `Invoke-WebRequest` with a 15-minute command timeout successfully downloaded
  the official tag archive to
  `build/windows/external/ISIS3-9.0.0-iwr2.tar.gz`: 246,082,553 bytes,
  SHA-256 `cb35421f078d91bef932e4ba365a3a4ac788ba46b90143ab9995d5dfd14984b4`.
  `tar -tzf` passed with 11,998 entries.
- The archive was extracted to
  `build/windows/external/isis-9.0.0-iwr-src`. Its copied Git metadata resolves
  HEAD to `950a5606ffeaa13ddb40101fbf25a8737e88902a`; all 60 pre-existing files
  targeted by the ISIS 9 Windows patch queue have raw blob hashes identical to
  that commit. The remaining patch target is a new file introduced by 0002.
- Windows Git's system `core.autocrlf=true` produced CRLF patch files while the
  source uses LF. This caused `git apply` context failure despite identical
  source blobs. `--ignore-space-change` resolves this boundary, and all eight
  tracked patches now apply.
- The complete MSVC/Ninja build succeeds with 24 jobs, and the installed prefix
  passes its structural checks plus a real `isis.dll` load for version 9.0.0.
- The APP gate is currently external-state blocked: the locally built
  `catlab.exe` exists before launch but is removed during launch after roughly
  60 seconds. The same content is removed under a different filename and after
  `editbin /release`, while the source copy in the build tree remains intact.
  Defender, AppLocker, and Code Integrity have no matching event; Windows
  Security Center reports Lenovo/火绒 and 360 antivirus products. Avoid source
  or binary mutations intended to evade the scanner; obtain an explicit local
  allow/exclusion, reinstall, and rerun the declared gate.

## Decisions

| Decision | Rationale |
|---|---|
| Try the documented archive fallback in `build/windows/external/isis-9.0.0-archive-src` without deleting the partial Git checkout | This changes the failing transport path, retains exact tag/commit provenance, avoids overwriting recoverable state, and uses the script's bounded timeout/low-speed/retry controls. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- Blocker-resolution evidence:
  `.planning/windows-isis9-m02-isis-prefix/resolution-evidence.json`
