"""Unit tests for Windows wheel workflow metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added workflow coverage for pip wheel builds.
"""

from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WHEEL_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "wheels.yml"


class WheelWorkflowUnitTest(unittest.TestCase):
    """Test suite for the Windows pip wheel workflow. Added: 2026-06-18."""

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
        self.assertIn("tools\\packaging\\publish_testpypi.ps1", workflow)
        self.assertIn("-Wheelhouse $env:WHEELHOUSE", workflow)
        self.assertIn("-CheckOnly", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("wheelhouse/*.whl", workflow)


if __name__ == "__main__":
    unittest.main()
