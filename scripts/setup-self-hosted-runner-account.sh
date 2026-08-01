#!/usr/bin/env bash
# Prepare the low-privilege account used by the PyISIS self-hosted runner.
#
# Author: Geng Xun
# Created: 2026-08-02
# Updated: 2026-08-02  Geng Xun added idempotent account, directory, and ACL setup.

set -Eeuo pipefail

readonly RUNNER_USER="pyisis-runner"
readonly RUNNER_GROUP="pyisis-runner"
readonly RUNNER_HOME="/var/lib/pyisis-runner"
readonly RUNNER_SHELL="/usr/sbin/nologin"
readonly RUNNER_ROOT="/opt/actions-runner-pyisis"
readonly RUNNER_CACHE="/var/lib/pyisis-runner/.cache/pyisis-gha"
readonly CONDA_ROOT="/home/gengxun/miniconda3"
readonly CONDA_ENV="/home/gengxun/miniconda3/envs/asp360_new"
readonly CONDA_PYTHON="$CONDA_ENV/bin/python"

trap 'printf "Error: setup failed at line %s.\n" "$LINENO" >&2' ERR

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Error: required command not found: %s\n' "$command_name" >&2
    exit 1
  fi
}

for command_name in sudo getent id install setfacl stat; do
  require_command "$command_name"
done

for executable in /usr/sbin/useradd "$RUNNER_SHELL" "$CONDA_PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    printf 'Error: required executable not found: %s\n' "$executable" >&2
    exit 1
  fi
done

printf 'Authenticating for system account setup...\n'
sudo -v

if getent passwd "$RUNNER_USER" >/dev/null; then
  IFS=: read -r _ _ _ _ _ existing_home existing_shell \
    < <(getent passwd "$RUNNER_USER")
  existing_group="$(id -gn "$RUNNER_USER")"

  if [[ "$existing_home" != "$RUNNER_HOME" ]]; then
    printf 'Error: %s has unexpected home: %s\n' \
      "$RUNNER_USER" "$existing_home" >&2
    exit 1
  fi
  if [[ "$existing_shell" != "$RUNNER_SHELL" ]]; then
    printf 'Error: %s has unexpected shell: %s\n' \
      "$RUNNER_USER" "$existing_shell" >&2
    exit 1
  fi
  if [[ "$existing_group" != "$RUNNER_GROUP" ]]; then
    printf 'Error: %s has unexpected primary group: %s\n' \
      "$RUNNER_USER" "$existing_group" >&2
    exit 1
  fi
  printf 'Reusing existing account: %s\n' "$RUNNER_USER"
else
  sudo /usr/sbin/useradd \
    --system \
    --user-group \
    --create-home \
    --home-dir "$RUNNER_HOME" \
    --shell "$RUNNER_SHELL" \
    "$RUNNER_USER"
fi

sudo install -d -o "$RUNNER_USER" -g "$RUNNER_GROUP" \
  "$RUNNER_ROOT" "$RUNNER_CACHE"

sudo setfacl -m "u:$RUNNER_USER:x" \
  /home/gengxun "$CONDA_ROOT" "$CONDA_ROOT/envs"
sudo setfacl -R -m "u:$RUNNER_USER:rX" "$CONDA_ENV"

printf '\nVerifying runner account and filesystem access...\n'
getent passwd "$RUNNER_USER"
stat -c '%U:%G %a %n' "$RUNNER_ROOT" "$RUNNER_HOME" "$RUNNER_CACHE"
sudo -u "$RUNNER_USER" "$CONDA_PYTHON" --version
printf 'Runner account setup completed successfully.\n'
