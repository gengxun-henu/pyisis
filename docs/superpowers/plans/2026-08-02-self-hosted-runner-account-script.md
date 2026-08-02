# Self-Hosted Runner Account Setup Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one idempotent shell script that prepares and validates the low-privilege `pyisis-runner` account, directories, ACLs, and read-only access to the existing `asp360_new` Conda environment.

**Architecture:** A repository-owned Bash entry point performs preflight checks before requesting sudo, creates or validates the fixed service identity, applies repeatable directory ownership and ACL operations, then exercises the Conda Python as that identity. A Python unit test checks shell syntax and the safety contract without performing privileged operations.

**Tech Stack:** Bash, sudo, Linux account tools, POSIX ACLs, Python 3.12 `unittest`

## Global Constraints

- The operator invokes the script as a normal user with `bash scripts/setup-self-hosted-runner-account.sh`.
- The service account and primary group are exactly `pyisis-runner`.
- The account home is exactly `/var/lib/pyisis-runner` and its shell is exactly `/usr/sbin/nologin`.
- The runner installation directory is exactly `/opt/actions-runner-pyisis`.
- The cache directory is exactly `/var/lib/pyisis-runner/.cache/pyisis-gha`.
- The existing Conda environment is exactly `/home/gengxun/miniconda3/envs/asp360_new` and remains read-only to the runner.
- The script must not download or register a GitHub Actions runner, handle a GitHub token, install packages, or modify the Conda environment.
- Keep `.gitignore` and `print.prt` untouched.

---

## File Structure

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `scripts/setup-self-hosted-runner-account.sh` | Validate prerequisites, prepare the system identity and filesystem permissions, and report verification results. |
| Create | `tests/unitTest/self_hosted_runner_account_setup_unit_test.py` | Execute the script against controlled command doubles to validate syntax, account creation, idempotent reuse, fixed paths, and conflict rejection. |

### Task 1: Add the Idempotent Account Setup Entry Point

**Files:**
- Create: `tests/unitTest/self_hosted_runner_account_setup_unit_test.py`
- Create: `scripts/setup-self-hosted-runner-account.sh`

**Interfaces:**
- Consumes: a normal Ubuntu login with `sudo`, `/usr/sbin/useradd`, `setfacl`, and the existing `/home/gengxun/miniconda3/envs/asp360_new/bin/python`.
- Produces: an executable, argument-free Bash entry point and a configured `pyisis-runner` identity with read-only Conda access.

- [ ] **Step 1: Write the failing contract test**

Create `tests/unitTest/self_hosted_runner_account_setup_unit_test.py`:

```python
"""Behavior tests for the self-hosted runner account setup script.

Author: Geng Xun
Created: 2026-08-02
Updated: 2026-08-02  Geng Xun added syntax and safety-contract coverage.
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "setup-self-hosted-runner-account.sh"


class SelfHostedRunnerAccountSetupUnitTest(unittest.TestCase):
    """Validate the privileged script without changing the host."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.fake_bin = Path(self.temp_dir.name) / "bin"
        self.fake_bin.mkdir()
        self.call_log = Path(self.temp_dir.name) / "calls.log"
        self.call_log.touch()
        self.created_marker = Path(self.temp_dir.name) / "account-created"

        self.write_command(
            "getent",
            """if [[ "$FAKE_ACCOUNT_MODE" == "missing" && ! -e "$FAKE_CREATED" ]]; then
  exit 2
fi
home="/var/lib/pyisis-runner"
[[ "$FAKE_ACCOUNT_MODE" == "wrong-home" ]] && home="/unexpected"
printf 'pyisis-runner:x:998:998::%s:/usr/sbin/nologin\\n' "$home"
""",
        )
        self.write_command("id", "printf 'pyisis-runner\\n'")
        self.write_command(
            "sudo",
            """printf '%q ' "$@" >> "$FAKE_LOG"
printf '\\n' >> "$FAKE_LOG"
if [[ " $* " == *" /usr/sbin/useradd "* ]]; then
  : > "$FAKE_CREATED"
fi
if [[ "${1:-}" == "-u" ]]; then
  printf 'Python 3.12.11\\n'
fi
""",
        )
        self.write_command("install", ":")
        self.write_command("setfacl", ":")
        self.write_command(
            "stat",
            "printf 'pyisis-runner:pyisis-runner 755 %s\\n' \"$@\"",
        )

    def write_command(self, name, body):
        path = self.fake_bin / name
        path.write_text(f"#!/usr/bin/env bash\\nset -eu\\n{body}\\n", encoding="utf-8")
        path.chmod(0o755)

    def run_script(self, account_mode):
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "FAKE_ACCOUNT_MODE": account_mode,
                "FAKE_CREATED": str(self.created_marker),
                "FAKE_LOG": str(self.call_log),
            }
        )
        return subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

    def test_script_has_valid_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_account_is_created_before_permissions_are_applied(self):
        result = self.run_script("missing")
        calls = self.call_log.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "/usr/sbin/useradd --system --user-group --create-home "
            "--home-dir /var/lib/pyisis-runner --shell /usr/sbin/nologin "
            "pyisis-runner",
            calls,
        )
        self.assertIn(
            "install -d -o pyisis-runner -g pyisis-runner "
            "/opt/actions-runner-pyisis "
            "/var/lib/pyisis-runner/.cache/pyisis-gha",
            calls,
        )
        self.assertIn(
            "setfacl -R -m u:pyisis-runner:rX "
            "/home/gengxun/miniconda3/envs/asp360_new",
            calls,
        )
        self.assertIn("Runner account setup completed successfully.", result.stdout)

    def test_existing_expected_account_is_reused(self):
        result = self.run_script("existing")
        calls = self.call_log.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reusing existing account: pyisis-runner", result.stdout)
        self.assertNotIn("/usr/sbin/useradd", calls)

    def test_existing_account_with_wrong_home_is_rejected(self):
        result = self.run_script("wrong-home")
        calls = self.call_log.read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected home: /unexpected", result.stderr)
        self.assertNotIn("install -d", calls)
        self.assertNotIn("setfacl", calls)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify the expected failure**

Run:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.self_hosted_runner_account_setup_unit_test -v
```

Expected: FAIL because `scripts/setup-self-hosted-runner-account.sh` does not exist.

- [ ] **Step 3: Implement the minimal setup script**

Create `scripts/setup-self-hosted-runner-account.sh`:

```bash
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
sudo stat -c '%U:%G %a %n' "$RUNNER_ROOT" "$RUNNER_HOME" "$RUNNER_CACHE"
sudo -u "$RUNNER_USER" "$CONDA_PYTHON" --version
printf 'Runner account setup completed successfully.\n'
```

Make it executable:

```bash
chmod 0755 scripts/setup-self-hosted-runner-account.sh
```

- [ ] **Step 4: Run focused validation**

Run:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
bash -n scripts/setup-self-hosted-runner-account.sh
python -m unittest tests.unitTest.self_hosted_runner_account_setup_unit_test -v
```

Expected: shell syntax succeeds and all four tests pass. The validation does not invoke sudo or alter the host.

- [ ] **Step 5: Commit the tested script**

```bash
git add scripts/setup-self-hosted-runner-account.sh \
  tests/unitTest/self_hosted_runner_account_setup_unit_test.py
git commit -m "ops: add runner account setup script"
```

- [ ] **Step 6: Perform operator validation**

The operator runs from the repository worktree:

```bash
bash scripts/setup-self-hosted-runner-account.sh
```

Expected: one sudo authentication prompt, a `pyisis-runner` passwd record, all three directories owned by `pyisis-runner:pyisis-runner`, Python 3.12 output from `asp360_new`, and the final success message. Running the same command a second time must reuse the account and succeed.
