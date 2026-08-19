"""Contract tests for the Windows native-APP clean-host workflow.

Author: Geng Xun
Created: 2026-08-18
Last Modified: 2026-08-18
Updated: 2026-08-18  Geng Xun added clean Windows 11 artifact provenance coverage.
"""

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/windows-native-app-clean-host.yml"


class WindowsNativeAppCleanHostWorkflowTest(unittest.TestCase):
    def test_clean_runtime_job_has_no_checkout_or_source_prefix(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        clean_job = workflow.split("  clean-runtime:", 1)[1].split(
            "  bind-evidence:", 1
        )[0]

        self.assertIn(
            "runs-on: [self-hosted, Windows, X64, pyisis, windows-11]",
            clean_job,
        )
        self.assertNotIn("actions/checkout", clean_job)
        self.assertIn("actions/download-artifact@v4", clean_job)
        self.assertIn(r"D:\code\pyisis\pyisis\build\windows\isis-prefix", clean_job)
        self.assertIn(r"D:\pyisis-win-env", clean_job)
        self.assertIn("test_isis_native_app_package.ps1", clean_job)
        self.assertIn("runtime-validation.json", clean_job)

    def test_provenance_and_final_evidence_are_bound_to_the_dispatch(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("uses: actions/checkout@v7"), 2)
        for token in (
            "github.sha",
            "github.run_id",
            "github.run_attempt",
            'job = "clean-runtime"',
            "runtime_report_sha256",
            "clean-host-provenance.json",
            "usgs-isis-native-apps-9.0.0-win64.zip",
            "usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json",
            "isis-native-apps-9.0.0-win64-validation.json",
        ):
            self.assertIn(token, workflow)
        bind_job = workflow.split("  bind-evidence:", 1)[1]
        self.assertIn("validate_windows_native_apps.py", bind_job)
        self.assertIn("actions/upload-artifact@v4", bind_job)

    def test_push_trigger_is_scoped_to_the_milestone_feature_branch(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("  push:\n    branches:\n      - feature/m04-windows-pyisis-wheelhouse", workflow)


if __name__ == "__main__":
    unittest.main()
