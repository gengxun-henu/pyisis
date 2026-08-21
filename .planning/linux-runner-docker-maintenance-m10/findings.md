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

## Evidence-Based Inferences

- A workflow committed to the default branch is required before `workflow_dispatch` can invoke it reliably.
- Adding the runner account to the `docker` group may require restarting the Actions runner listener so new jobs inherit the group.

## Unresolved Items

- Exact Ubuntu release/build currently installed.
- Whether `sudo -n` is available to the runner service account.
- Whether Ubuntu's `docker.io` package is available and suitable on Ubuntu 26.04.
- Exact systemd unit name for the Actions runner listener.

## Decisions

- Prefer Docker's official apt repository because Ubuntu 26.04 is explicitly supported and Docker documents distro `docker.io` as a conflicting unofficial package. Probe and refuse to mutate if an existing conflicting Docker/container runtime installation is detected instead of silently removing it.
- Verification must include an Actions-level job container, not only `sudo docker info`.

## Resources

- Repository workflows under `.github/workflows/`.
- Docker Engine on Ubuntu: `https://docs.docker.com/engine/install/ubuntu/`.
- GitHub self-hosted runner troubleshooting: `https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/monitor-and-troubleshoot`.
- GitHub Actions job-container syntax: `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer`.
