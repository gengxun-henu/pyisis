# M10 Findings

## Verified Facts

- Local checkout is `main...origin/main` at session start.
- The only dirty path is the guarded, unrelated `print.prt`; it must remain untouched and unstaged.
- Canonical milestone verification passes.
- No SSH configuration or reachable SSH channel for the other computer was previously found; GitHub Actions is the available remote execution channel.
- `pyisis-ubuntu26` was previously online with labels `self-hosted`, `Linux`, `X64`, `pyisis`, `ubuntu-26.04`, `isis9`, and `isis10`.
- Existing wheel workflow previously fell back to GitHub-hosted Linux because `docker` was not installed on this runner.
- Docker's official Ubuntu instructions now explicitly support Ubuntu Resolute 26.04 LTS on x86_64 and prescribe the Docker apt repository plus `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, and `docker-compose-plugin`.
- GitHub's official self-hosted-runner guidance requires Docker on Linux for job containers and recommends checking the Docker service and the runner service account's socket permission.
- GitHub documents the runner unit convention as `actions.runner.<org>-<repo>.<runnerName>.service` and recommends discovering the exact unit from the runner `.service` file or `systemctl`.
- Probe run `32482513889` succeeded on runner version 2.336.0 at host `gengxun-ThinkStation-P3-Tower`.
- Target OS is Ubuntu 26.04 LTS Resolute, kernel 7.0.0-22-generic, x86_64.
- Runner service account is `pyisis-runner` (UID 997), with no supplementary groups; service unit is `actions.runner.gengxun-henu-pyisis.pyisis-ubuntu26.service`.
- Root filesystem has 74 GB available (384 GB total, 80% used).
- `docker` is absent and `docker.service` is inactive. The package probe printed no installed conflicting Docker/container-runtime packages.
- `sudo -n true` is denied for `pyisis-runner`; the workflow cannot perform a system-level apt installation or service mutation.
- Docker's official rootless mode still requires `newuidmap`, `newgidmap`, and at least 65,536 subordinate UIDs/GIDs for the account.
- On Ubuntu 24.04 and later, Docker documents restricted unprivileged user namespaces: script-based rootless installation needs an AppArmor profile and an AppArmor restart, both privileged operations. Installing `docker-ce-rootless-extras` via apt supplies the profile, but apt also requires privilege.
- Rootless daemon persistence normally requires `loginctl enable-linger`, another administrator action, unless a suitable persistent user session is already configured.
- Rootless prerequisite probe run `32482923261` succeeded and confirmed that `newuidmap`, `newgidmap`, `slirp4netns`, and `fuse-overlayfs` are all absent.
- No subordinate UID/GID mapping was reported for `pyisis-runner`; `XDG_RUNTIME_DIR` is unset.
- `kernel.apparmor_restrict_unprivileged_userns = 1`; an actual `unshare --user --map-root-user true` probe failed.
- Official rootless Docker therefore cannot be installed or started safely on this host without administrator changes.

## Evidence-Based Inferences

- A workflow committed to the default branch is required before `workflow_dispatch` can invoke it reliably.
- Adding the runner account to the `docker` group may require restarting the Actions runner listener so new jobs inherit the group.
- Rootless Docker is unlikely to be viable without one-time administrator setup on stock Ubuntu 26.04, but the exact host prerequisites must be probed before ruling it out.

## Unresolved Items

- Administrator access is required once on the Ubuntu host to install Docker Engine and grant `pyisis-runner` access; GitHub Actions cannot cross this privilege boundary.

## Decisions

- Prefer Docker's official apt repository because Ubuntu 26.04 is explicitly supported and Docker documents distro `docker.io` as a conflicting unofficial package. Probe and refuse to mutate if an existing conflicting Docker/container runtime installation is detected instead of silently removing it.
- Verification must include an Actions-level job container, not only `sudo docker info`.
- Do not dispatch the system-level `install` operation after the probe proved passwordless sudo is unavailable.
- Do not attempt script-based rootless Docker: the host fails multiple mandatory prerequisites and Ubuntu 26.04's required AppArmor setup is privileged.

## Resources

- Repository workflows under `.github/workflows/`.
- Docker Engine on Ubuntu: `https://docs.docker.com/engine/install/ubuntu/`.
- GitHub self-hosted runner troubleshooting: `https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/monitor-and-troubleshoot`.
- GitHub Actions job-container syntax: `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer`.
- Docker rootless mode: `https://docs.docker.com/engine/security/rootless/`.
- Docker rootless troubleshooting: `https://docs.docker.com/engine/security/rootless/troubleshoot/`.
