"""Unit tests for cross-platform wheel workflow metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-07-23
Updated: 2026-06-18  Geng Xun added workflow coverage for pip wheel builds.
Updated: 2026-06-19  Geng Xun added optional TestPyPI publish workflow coverage.
Updated: 2026-07-22  Geng Xun required clean Windows wheels to run the basic binding test list.
Updated: 2026-07-22  Geng Xun added isolated Linux wheel build and install coverage.
Updated: 2026-07-23  Geng Xun required manylinux 2.35 builds and Ubuntu 22.04/24.04 install tests.
"""

from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WHEEL_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "wheels.yml"


class WheelWorkflowUnitTest(unittest.TestCase):
    """Test suite for the cross-platform pip wheel workflow. Added: 2026-06-18."""

    def _workflow_text(self) -> str:
        self.assertTrue(WHEEL_WORKFLOW.is_file(), f"Missing workflow: {WHEEL_WORKFLOW}")
        return WHEEL_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_manual_and_pr_triggers_for_packaging_paths(self):
        workflow = self._workflow_text()

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn('"pyproject.toml"', workflow)
        self.assertIn('"packaging/**"', workflow)
        self.assertIn('"tools/packaging/**"', workflow)
        self.assertIn('"ports/linux/**"', workflow)
        self.assertIn('".github/workflows/wheels.yml"', workflow)

    def test_workflow_uses_windows_runner_and_isis_prefix_resolution(self):
        workflow = self._workflow_text()

        self.assertIn("runs-on: windows-2022", workflow)
        self.assertIn("shell: pwsh", workflow)
        self.assertIn("actions/checkout@v4", workflow)
        self.assertIn("actions/setup-python@v5", workflow)
        self.assertIn("mamba-org/setup-micromamba@v3", workflow)
        self.assertIn("ports\\windows\\activate_msvc.ps1", workflow)
        self.assertIn("ports\\windows\\isis\\verify_isis_prefix.ps1", workflow)
        self.assertIn("PYISIS_WINDOWS_ISIS_PREFIX", workflow)
        self.assertIn("PYISIS_WINDOWS_DEP_PREFIX", workflow)

    def test_workflow_builds_tests_checks_and_uploads_wheels(self):
        workflow = self._workflow_text()

        self.assertIn("tools\\packaging\\build_wheels.ps1", workflow)
        self.assertIn("tools\\packaging\\test_wheel_install.py", workflow)
        self.assertIn("--test-list tools\\packaging\\basic_tests.txt", workflow)
        self.assertIn("tools\\packaging\\publish_testpypi.ps1", workflow)
        self.assertIn("-Wheelhouse $env:WHEELHOUSE", workflow)
        self.assertIn("-CheckOnly", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("wheelhouse/*.whl", workflow)

    def test_workflow_can_optionally_publish_and_verify_testpypi(self):
        workflow = self._workflow_text()

        self.assertIn("publish_testpypi:", workflow)
        self.assertIn("secrets.TESTPYPI_API_TOKEN", workflow)
        self.assertIn("TESTPYPI_API_TOKEN secret is required", workflow)
        self.assertIn("-Upload", workflow)
        self.assertIn("tools\\packaging\\test_testpypi_install.py", workflow)
        self.assertIn("build\\packaging\\testpypi-venv", workflow)

    def test_workflow_builds_linux_wheels_and_tests_on_a_clean_runner(self):
        workflow = self._workflow_text()

        self.assertIn("linux-cp312-build:", workflow)
        self.assertIn("linux-cp312-clean-install:", workflow)
        self.assertIn("needs: linux-cp312-build", workflow)
        self.assertIn("ports/linux/env/pyisis-isis-linux-64.yml", workflow)
        self.assertIn("MAMBA_ROOT_PREFIX: /opt/pyisis-micromamba", workflow)
        self.assertIn("HOSTED_CONDA_PREFIX: /opt/pyisis-conda", workflow)
        self.assertIn("tools/packaging/build_wheels_linux.sh", workflow)
        self.assertIn("x86_64-conda-linux-gnu-c++", workflow)
        self.assertIn("x86_64-conda-linux-gnu-g++", workflow)
        self.assertIn('candidate="$(command -v "$compiler_name" || true)"', workflow)
        self.assertIn("quay.io/pypa/manylinux_2_28_x86_64", workflow)
        self.assertIn("--platform-tag manylinux_2_35_x86_64", workflow)
        self.assertIn("Audit Linux ABI and wheel policy", workflow)
        self.assertIn("audit_linux_wheelhouse.py", workflow)
        self.assertIn("--target-glibc 2.28", workflow)
        self.assertIn("--require-target", workflow)
        self.assertIn("--target 2.35", workflow)
        self.assertIn("env -u LD_LIBRARY_PATH auditwheel show", workflow)
        self.assertIn("auditwheel-manylinux-wheel.txt", workflow)
        self.assertIn("validate_auditwheel_policy.py", workflow)
        self.assertIn("test \"$native_wheel_count\" -eq 1", workflow)
        self.assertIn("usgs-pyisis-linux-cp312-abi-report", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("ubuntu-22.04", workflow)
        self.assertIn("ubuntu-24.04", workflow)
        self.assertIn("runs-on: ${{ matrix.os }}", workflow)
        self.assertIn("--test-list tools/packaging/basic_tests.txt", workflow)


if __name__ == "__main__":
    unittest.main()
