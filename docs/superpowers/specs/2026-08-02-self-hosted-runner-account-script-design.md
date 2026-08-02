# PyISIS Self-Hosted Runner Account Setup Script Design

## Goal

Provide one repository script that prepares the low-privilege
`pyisis-runner` service account and its filesystem access on the Ubuntu 26.04
host. The operator runs the script as their normal login user and enters their
sudo password once.

## Scope

The script will:

- create or reuse the `pyisis-runner` system account and matching group;
- create `/opt/actions-runner-pyisis` and the runner cache directory under
  `/var/lib/pyisis-runner` with the correct ownership;
- grant the account traverse access to `/home/gengxun` and the Conda parent
  directories;
- grant read and traverse access to the existing `asp360_new` environment;
- verify the account record, directory ownership, and environment Python;
- stop at the first error and report the failing source line.

The script will not download or register the GitHub Actions runner, request or
store a GitHub registration token, modify the Conda environment, or install
system packages.

## Interface

The entry point is:

```bash
bash scripts/setup-self-hosted-runner-account.sh
```

It has no command-line options. Host paths and the service account name are
explicit constants matching the Phase 1 runner design. It calls `sudo -v`
before making system changes so the operator normally receives a single
authentication prompt.

## Safety and Idempotency

The script uses `set -Eeuo pipefail` and a concise error trap. It validates
required commands and the Conda Python executable before changing system
state. Existing accounts are accepted only when their home directory and shell
match the expected values. Directory creation and ACL application are safe to
repeat. Account creation uses absolute `/usr/sbin` paths so it does not depend
on the non-login `PATH` used by Ubuntu 26.04.

The Conda environment remains read-only to the runner. Future Conda updates may
create files without the runner ACL, so the script can be rerun after such an
update.

## Validation

Repository tests will validate the script contract without using sudo or
changing the host. `bash -n` will check shell syntax. A real execution by the
operator will finish by running the environment's Python as `pyisis-runner`
and printing the resulting account and directory ownership records.
