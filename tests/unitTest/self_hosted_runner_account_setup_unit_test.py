"""Behavior tests for the self-hosted runner account setup script.

Author: Geng Xun
Created: 2026-08-02
Updated: 2026-08-02  Geng Xun added syntax and safety-contract coverage.
Updated: 2026-08-02  Geng Xun covered verification below a private runner home.
Updated: 2026-08-02  Geng Xun covered read-only access to both ISIS conda environments.
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
printf 'pyisis-runner:x:998:998::%s:/usr/sbin/nologin\n' "$home"
""",
        )
        self.write_command("id", "printf 'pyisis-runner\n'")
        self.write_command(
            "sudo",
            """printf '%q ' "$@" >> "$FAKE_LOG"
printf '\n' >> "$FAKE_LOG"
if [[ " $* " == *" /usr/sbin/useradd "* ]]; then
  : > "$FAKE_CREATED"
fi
if [[ "${1:-}" == "-u" ]]; then
  printf 'Python 3.12.11\n'
fi
""",
        )
        self.write_command("install", ":")
        self.write_command("setfacl", ":")
        self.write_command(
            "stat",
            """if [[ "$FAKE_STAT_DENIED" == "1" ]]; then
  printf 'stat: Permission denied\n' >&2
  exit 13
fi
printf 'pyisis-runner:pyisis-runner 755 %s\n' "$@"
""",
        )

    def write_command(self, name, body):
        path = self.fake_bin / name
        path.write_text(f"#!/usr/bin/env bash\nset -eu\n{body}\n", encoding="utf-8")
        path.chmod(0o755)

    def run_script(self, account_mode, *, stat_denied=False):
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "FAKE_ACCOUNT_MODE": account_mode,
                "FAKE_CREATED": str(self.created_marker),
                "FAKE_LOG": str(self.call_log),
                "FAKE_STAT_DENIED": "1" if stat_denied else "0",
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
        self.assertIn(
            "setfacl -R -m u:pyisis-runner:rX "
            "/home/gengxun/miniconda3/envs/asp370",
            calls,
        )
        self.assertIn(
            "-u pyisis-runner "
            "/home/gengxun/miniconda3/envs/asp370/bin/python --version",
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

    def test_verification_uses_sudo_below_private_runner_home(self):
        result = self.run_script("existing", stat_denied=True)
        calls = self.call_log.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "stat -c %U:%G\\ %a\\ %n /opt/actions-runner-pyisis "
            "/var/lib/pyisis-runner "
            "/var/lib/pyisis-runner/.cache/pyisis-gha",
            calls,
        )


if __name__ == "__main__":
    unittest.main()
