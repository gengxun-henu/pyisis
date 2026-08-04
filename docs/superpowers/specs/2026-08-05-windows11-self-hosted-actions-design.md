# Windows 11 Self-Hosted Actions Design

## Goal

Use this Windows 11 x64 workstation as the default Windows wheel validation
runner for trusted pull requests opened by `gengxun-henu` in the
`gengxun-henu/pyisis` repository. Keep untrusted and fork pull requests on
GitHub-hosted runners, and preserve a manual GitHub-hosted fallback.

The Windows gate must build the PyISIS wheelhouse, stage the ISIS runtime DLL
closure, install the wheelhouse into an isolated virtual environment, and run
the configured smoke and basic binding tests. Passing the gate must provide
evidence for Windows 11 rather than only Windows Server 2022.

## Supported Scope

- Host operating system: Windows 11 x64.
- Runner name: `pyisis-windows11`.
- Required custom labels: `pyisis` and `windows-11`, in addition to the
  automatic `self-hosted`, `Windows`, and `X64` labels.
- ISIS 9 package line: CPython 3.12.
- ISIS 10 package line: CPython 3.13, created by the existing Micromamba
  workflow environment.
- Runner installation directory: `D:\actions-runner-pyisis`.
- Runner mode: Windows service with automatic startup.
- GitHub repository scope: repository-level runner for
  `gengxun-henu/pyisis`, not an organization-wide runner.

This work does not add macOS, Windows ARM64, Cygwin, or arbitrary Python ABI
support. Full external ISISDATA remains outside the wheelhouse and outside this
runner configuration.

## Trust and Routing Policy

The self-hosted machine may execute pull-request code only when both conditions
are true:

1. `github.event.pull_request.head.repo.full_name == github.repository`;
2. `github.actor == 'gengxun-henu'`.

Forks, Dependabot, and pull requests opened by other actors must use the
GitHub-hosted Windows runner and must never be routed to this workstation.
The workflow must use `pull_request`, not `pull_request_target`, when executing
PR code.

For manual workflow dispatch, Windows 11 self-hosting is the default. A
workflow input permits an explicit fallback to `windows-2022` when the local
machine is offline or under maintenance. GitHub Release publication continues
to require the selected Windows lane to pass.

## Host Provisioning

The workstation already provides Windows 11 x64, Visual Studio 2022 Community
with the MSVC x64 toolchain, Git, CPython 3.12, and CMake.

Provision the missing host tools as follows:

- Install supported 64-bit PowerShell 7 and verify `pwsh` is available to the
  runner service.
- Install Micromamba in a stable, machine-readable location outside the
  repository. Use short root and environment prefixes on `D:` to reduce path
  length risk.
- Do not install ISIS dependencies with pip. The existing conda-forge
  environment files remain the dependency authority.
- Resolve `dumpbin.exe` by activating the Visual Studio x64 developer
  environment inside the workflow; do not depend on an interactive user's
  current `PATH`.
- Install the GitHub Actions runner under `D:\actions-runner-pyisis` and
  register it as a repository-level Windows service.

The short-lived GitHub runner registration token must be obtained at setup
time, passed directly to the runner configuration command, and never written
to a repository file, design document, workflow log, or reusable script.

## Workflow Architecture

Retain `wheels.yml` as the single release-matrix entry point. Extend its scope
job to emit the selected Windows runner as JSON:

- trusted same-repository owner PR: the Windows 11 self-hosted label set;
- other PRs: `windows-2022`;
- manual dispatch default: the Windows 11 self-hosted label set;
- manual dispatch fallback: `windows-2022`.

The ISIS 9 and ISIS 10 Windows jobs consume this resolved runner value. Their
existing environment creation, patched ISIS-prefix cache, wheel build,
metadata check, isolated installation, and artifact upload steps remain shared
so the two runner modes cannot drift into separate packaging implementations.

The runner will process only one job at a time. ISIS 9 and ISIS 10 jobs may be
ready concurrently, but GitHub queues them against the single registered
runner. Cache paths and keys must remain version-separated.

## Clean-Wheel Validation

The Windows installation check must not inherit DLL access from the Micromamba
build environment. Before importing the installed wheel, the verification
environment must remove:

- `ISIS_PREFIX`, `ISISROOT`, `ISISDATA`, and `PYTHONPATH`;
- `CONDA_PREFIX`, `PYISIS_DEP_PREFIX`, and `PYISIS_WINDOWS_DEP_PREFIX`;
- every `PATH` entry located under any captured build/dependency prefix.

The runtime staging step must treat a failed `dumpbin /DEPENDENTS` invocation
or an unresolved non-system DLL as a release error. System DLL exclusions stay
explicit and test-covered. The workflow should retain a DLL dependency report
as validation evidence.

The final import and basic tests run from a newly created venv using only the
wheelhouse, packaged runtime, Windows system libraries, and the normal Python
runtime. A passing build-environment import is not a substitute for this test.

## Failure Handling

- If the Windows 11 runner is offline, trusted PR jobs remain queued instead of
  silently claiming Windows 11 validation. A maintainer may manually rerun with
  the GitHub-hosted fallback when appropriate.
- Missing PowerShell, Micromamba, MSVC activation, `dumpbin`, or required runner
  labels fails the readiness check before the expensive ISIS build begins.
- Failed or unresolved DLL inspection blocks wheel publication.
- Runner registration and service failures are diagnosed locally; credentials
  and registration tokens are never printed.
- Generated ISIS build prefixes, Micromamba packages, wheelhouses, and caches
  use explicit locations and retention rules because workstation disk space is
  limited.

## Validation and Success Criteria

Implementation is complete when all of the following are demonstrated:

1. `pwsh`, Micromamba, MSVC x64 tools, CMake, Ninja, Git, Python, and `dumpbin`
   pass a local readiness check under the service account environment.
2. GitHub lists an online repository runner named `pyisis-windows11` with
   labels `self-hosted`, `Windows`, `X64`, `pyisis`, and `windows-11`.
3. A trusted same-repository PR that touches Windows packaging or the wheel
   workflow schedules its Windows jobs on `pyisis-windows11`.
4. A synthetic or real untrusted/fork routing test resolves to
   `windows-2022` and cannot schedule the local runner.
5. ISIS 9 and ISIS 10 Windows wheelhouse jobs build successfully on the local
   Windows 11 runner.
6. The clean-wheel verification runs with build-prefix DLL paths removed and
   passes the configured smoke/basic test list.
7. Workflow and packaging unit tests cover runner routing, environment cleanup,
   unresolved DLL failure, and release-job dependencies.
8. Installation and runner-service operations are documented without storing
   tokens or machine secrets in Git.

## Operational Boundary

The repository stores runner labels, routing policy, readiness tooling, and
operator documentation. The runner binary, Micromamba installation, Conda
packages, patched ISIS build prefix, build caches, service configuration, and
registration credentials remain local machine state and are not committed.

Stopping or uninstalling the runner service is an explicit administrative
operation. Workflow code must not alter the runner registration or service
configuration during normal CI jobs.
