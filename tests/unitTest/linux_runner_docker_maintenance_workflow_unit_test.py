"""Regression tests for the temporary Linux runner Docker maintenance workflow.

Author: Geng Xun
Created: 2026-08-21
Last Modified: 2026-08-21
Updated: 2026-08-21  Geng Xun added safety and manylinux-container proof coverage.
Updated: 2026-08-21  Geng Xun added rootless Docker prerequisite probe coverage.
"""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "linux-runner-docker-maintenance.yml"
)


class LinuxRunnerDockerMaintenanceWorkflowUnitTest(unittest.TestCase):
    """Validate that remote maintenance remains narrow and self-verifying."""

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_is_manual_fixed_operation_workflow(self):
        workflow = self.workflow

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn("type: choice", workflow)
        for operation in ("probe", "install", "verify"):
            self.assertIn(f"- {operation}", workflow)
        self.assertNotIn("command:", workflow)
        self.assertNotIn("eval ", workflow)
        self.assertIn("contents: read", workflow)

    def test_targets_only_the_dedicated_linux_runner(self):
        labels = "[self-hosted, Linux, X64, pyisis, ubuntu-26.04]"

        self.assertEqual(self.workflow.count(f"runs-on: {labels}"), 2)
        self.assertIn('"${VERSION_ID:-}" != "26.04"', self.workflow)
        self.assertIn('"$(dpkg --print-architecture)" != "amd64"', self.workflow)
        self.assertIn("pyisis-ubuntu26 runner service", self.workflow)

    def test_install_refuses_unsafe_prerequisites_and_conflicts(self):
        workflow = self.workflow

        self.assertIn("sudo -n true", workflow)
        self.assertIn("refusing partial installation", workflow)
        self.assertIn("refusing to remove them automatically", workflow)
        self.assertNotIn("apt-get remove", workflow)
        self.assertNotIn("apt remove", workflow)
        self.assertIn("https://download.docker.com/linux/ubuntu", workflow)
        self.assertIn("/etc/apt/keyrings/docker.asc", workflow)
        self.assertIn("docker-ce docker-ce-cli containerd.io", workflow)
        self.assertIn("systemctl enable --now docker.service", workflow)

    def test_probe_reports_rootless_prerequisites_before_requiring_admin(self):
        workflow = self.workflow

        for prerequisite in (
            "newuidmap",
            "newgidmap",
            "/etc/subuid",
            "/etc/subgid",
            "kernel.apparmor_restrict_unprivileged_userns",
            "kernel.unprivileged_userns_clone",
            "XDG_RUNTIME_DIR",
            "unprivileged_user_namespace",
        ):
            self.assertIn(prerequisite, workflow)
        self.assertIn('loginctl show-user "$(id -u)" -p Linger -p State', workflow)

    def test_runner_permission_change_is_followed_by_delayed_restart(self):
        workflow = self.workflow

        self.assertIn('usermod -aG docker "$runner_user"', workflow)
        self.assertIn("systemd-run", workflow)
        self.assertIn("--on-active=45s", workflow)
        self.assertIn('/bin/systemctl restart "$runner_service"', workflow)

    def test_verification_proves_host_and_actions_container_access(self):
        workflow = self.workflow

        self.assertIn("docker info", workflow)
        self.assertIn(
            "docker run --rm quay.io/pypa/manylinux_2_28_x86_64 /bin/true",
            workflow,
        )
        self.assertIn("manylinux-container-proof:", workflow)
        self.assertIn("image: quay.io/pypa/manylinux_2_28_x86_64", workflow)
        self.assertIn("test -f /.dockerenv", workflow)


if __name__ == "__main__":
    unittest.main()
