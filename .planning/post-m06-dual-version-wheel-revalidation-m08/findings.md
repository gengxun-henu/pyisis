# Findings: Post-M06 dual-version wheel revalidation (M08)

## Verified Facts

- M06 is complete and current-HEAD behavior must be validated independently of the earlier rc2 release.
- The authoritative workflow is `.github/workflows/wheels.yml`.
- The Windows ISIS 10 workflow lane includes the existing SpiceQL 1.4.1 export and downstream MSVC link probe.
- Failed M08 validation run `32373382592` used `b50506e365b1af6d80fdbefbba919d70b5779197` on `feature/m04-windows-pyisis-wheelhouse`; no release was published.
- Pre-remote Git classification was only the guarded pre-existing unstaged `print.prt`; `git diff --check` produced no whitespace errors.
- Before dispatch, the workflow contract suite passed 33 tests. After the repair, `python -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test -v` passed 35 tests (0 failed, 0 skipped), including package-specific distribution metadata and Windows bootstrap/runtime checks.
- The four required lanes map to workflow job IDs: `linux-isis9` → `linux-cp312-build` + `linux-cp312-clean-install`; `linux-isis10-cp313` → `linux-isis10-cp313-build` + `linux-isis10-cp313-clean-install`; `windows-cp312` → `windows-cp312`; `windows-isis10-cp313` → `windows-isis10-cp313`.
- In replacement run `32433373707`, both Linux builds and all six hosted Ubuntu clean-install jobs passed. Windows ISIS 10 built and verified its prefix, then runtime staging rejected six operating-system DLL imports that were absent from the system allowlist.
- Local `System32` verification confirms all six newly classified imports are provided by Windows: `authz.dll`, `d3d12.dll`, `dwrite.dll`, `odbc32.dll`, `psapi.dll`, and `winhttp.dll`.
- Windows build helpers already defaulted to `min(24, ProcessorCount)`, but `wheels.yml` overrode the ISIS 10 and SpiceQL builds with `-Jobs 2`. The Windows workstation exposes 16 logical processors.
- The approved balanced design keeps clean-install portability jobs GitHub-hosted while routing only build jobs to the dedicated Linux/Windows runners and preserving hosted runner fallbacks.
- Run `32436488892` confirmed the Linux capability probe selects hosted Ubuntu when the dedicated Linux runner lacks Docker. Its Windows ISIS 10 job then stalled in `actions/checkout@v7`; the local runner worker log showed the checkout Node process remained alive while GitHub traffic was not completing.
- The Windows workstation proxy at `http://127.0.0.1:7890` is already proven for repository pushes. Job-level `HTTP_PROXY` and `HTTPS_PROXY` now apply only when `windows_is_self_hosted` is true, so checkout, Miniconda setup, and build downloads share the working route without changing hosted Windows behavior.
- Run `32437219483` proved the proxy repair: Windows ISIS 10 checkout completed successfully. Both Windows jobs then failed in `setup-miniconda` with `Failed to extract packages`; the action log showed Miniforge targeting `C:\WINDOWS\system32\config\systemprofile\miniconda3`, while C: had only 6.50 GiB free and D: had about 1.6 TiB free.
- Run `32437828115` targeted `D:\actions-runner-pyisis\_work\_tool\pyisis-miniforge3` exactly as configured but the same Miniforge 26.3.2-3 installer failed during package extraction, disproving installation volume as the root cause.
- setup-miniconda v4's bundled installer provider explicitly uses the `CONDA` environment variable when no Miniconda/Miniforge version is requested. `C:\Users\gx\miniconda3` has conda 26.5.3 and grants `NT AUTHORITY\SYSTEM` FullControl, so it is a valid self-hosted base without running the failing installer.
- In run `32438209261`, the intended empty `miniforge-version` became `latest` because GitHub expression `condition && '' || 'latest'` treats the selected empty string as falsy and evaluates the fallback. Explicit `if`-guarded action steps are required for this empty/nonempty choice.
- Run `32438639372` logged `... will use bundled Miniconda`, proving the split setup path works. Environment processing then failed only when `conda init` attempted persistent shell/profile changes under the service account; setup-miniconda supports `run-init: false` for this noninteractive CI case.
- In run `32439037432`, self-hosted cp312 correctly used bundled Conda with `run-init: false`, but the forced classic solver consumed more than 10 minutes of one CPU core and about 3.7 GB working set. The installed Conda 26.5.3 reports libmamba as its default and has conda-libmamba-solver 26.7.0 available.
- Run `32439954637` confirmed libmamba reduced solve working set to roughly 0.4 GB and moved quickly into package extraction, but setup-miniconda's default `pkgs_dir` remained under the SYSTEM profile on C:. C: free space fell from 6.50 GiB to 2.69 GiB while D: retained about 1.6 TiB free.
- GitHub's official self-hosted runner documentation recommends lowercase proxy variables in a runner-root `.env` and requires a runner restart. `D:\actions-runner-pyisis\.env` now contains the local proxy settings, but the current non-elevated Codex process could not restart the Windows service; the file will take effect on its next restart.

## Unresolved Items

- Fresh four-lane outcomes and artifacts for the repaired commit.

## Failed-run evidence (run 32373382592)

- Both Linux wheel builds succeeded, but all six Linux clean-install jobs failed in `tools/packaging/test_wheel_install.py`: its generated metadata probe always requested `usgs-pyisis`, `usgs-pyisis-runtime-win64`, and `usgs-pyisis-isisdata-minimal`. Linux ISIS 9 therefore looked for the absent Windows runtime package, while Linux ISIS 10 first looked for the absent ISIS 9 distribution.
- Windows cp312 failed before build in `actions/setup-python`: Python 3.12 was absent from the local tool cache and repeated download attempts for the Windows Python archive ended with `ECONNRESET`.
- Windows ISIS 10 cp313 failed before build in `actions/checkout`: action archive acquisition initially hit DNS failure, then repository fetch exhausted three attempts because `github.com:443` was unreachable.
- The Windows self-hosted runner service is installed, automatic, online, and idle after the run. These Windows failures are bootstrap/network failures, not compile or packaging results.

## Decisions

| Decision | Rationale |
|---|---|
| Keep the existing four-lane workflow structure | The repair changes only clean-install expectations and removes a redundant Windows bootstrap; package, installation, metadata, and runtime-closure gates remain intact. |
| Dispatch with `release_line=isis10`, `publish_testpypi=false`, and `publish_github_release=false` | `release_line=none` is unsupported. These supported, explicit non-publishing inputs preserve the four-lane validation scope; the GitHub-release job is additionally restricted to `main`, so the feature-branch dispatch cannot create a release. |
| Use `windows_runner=windows-2022` for the replacement run | The self-hosted runner failed before compilation because its GitHub route was unstable. The workflow already supports the hosted runner; this isolates product validation from workstation network state. |
| Remove Windows `actions/setup-python` | The subsequent version-pinned setup-miniconda environments provide the interpreters actually used by build and packaging commands; the redundant action caused an unused Python download to fail. |
| Use runtime-detected build parallelism capped at 24 | It uses all logical processors on smaller machines and prevents excessive parallelism on larger hosts. Explicit `-Jobs 2` overrides were removed. |
| Use local self-hosted caches but retain hosted fallbacks | Linux reuses ccache and version-separated scikit-build trees under the runner tool cache. Windows reuses fingerprinted ISIS prefixes locally; `windows-2022` retains `actions/cache`. |
| Keep Ubuntu clean-install matrices hosted | A wheel built on the dedicated Linux host still receives independent portability evidence on Ubuntu 22.04/24.04/26.04. |
| Inject the workstation proxy at Windows self-hosted job scope | Bootstrap actions run before repository scripts, so job-level environment is the earliest workflow-controlled point that covers checkout and dependency setup. The expression resolves to an empty string on `windows-2022`. |
| Install Windows Miniforge under `runner.tool_cache` | This keeps the base conda installation and named environments on the runner's large D: volume and gives the two serial Windows jobs a stable shared base path. Step-level `runner.tool_cache` is a supported context; the earlier parser failure involved job-level `env`. |
| Reuse preinstalled Conda only on self-hosted Windows | The Miniforge installer fails under the runner service account on both C: and D:. Conditional action inputs select the documented bundled-Conda provider on this workstation, while GitHub-hosted Windows continues to install latest Miniforge under its tool cache. |
| Use two mutually exclusive Windows conda setup steps | This avoids falsy-empty expression semantics and makes the self-hosted versus hosted bootstrap paths directly testable. |
| Disable conda shell initialization on self-hosted Windows | Later workflow steps resolve and export the environment's Python and runtime paths explicitly, so persistent shell profile mutation is unnecessary. Hosted behavior is unchanged. |
| Use libmamba for self-hosted Windows environment solves | This removes the observed classic-solver bottleneck while keeping the existing hosted setup path and its classic solver unchanged. |
| Keep self-hosted Conda storage on the runner tool volume | Both package caches and version-specific environments use D:. A guarded pre-step deletes only the exact legacy cache created by setup-miniconda under the SYSTEM profile, preventing system-disk exhaustion. |
