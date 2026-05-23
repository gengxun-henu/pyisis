"""Regression checks for GitHub Actions workflow routing policy."""

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PR_GATE = REPO_ROOT / ".github" / "workflows" / "agent-pybind-pr-gate.yml"


class AgentPybindPrGatePolicyTest(unittest.TestCase):
    def setUp(self):
        self.workflow = PR_GATE.read_text(encoding="utf-8")

    def test_pr_gate_uses_default_runner_profile(self):
        resolve_runner_block = self._job_block("resolve_runner")

        self.assertNotIn("runner_profile: github-hosted", resolve_runner_block)
        self.assertNotIn("runner_profile:", resolve_runner_block)

    def test_pr_gate_avoids_full_history_checkout_for_change_summary(self):
        self.assertNotIn("fetch-depth: 0", self.workflow)
        self.assertIn("actions/github-script@v7", self.workflow)
        self.assertIn("changed_files:", self.workflow)

    def test_unit_tests_support_self_hosted_build_cache(self):
        unit_tests_block = self._job_block("unit-tests")

        self.assertIn("LOCAL_BUILD_CACHE_DIR:", unit_tests_block)
        self.assertIn("runner_mode == 'github-hosted'", unit_tests_block)
        self.assertIn("actions/download-artifact@v4", unit_tests_block)
        self.assertIn("runner_mode == 'self-hosted'", unit_tests_block)
        self.assertIn('cp -a "$LOCAL_BUILD_CACHE_DIR"', unit_tests_block)

    def test_metadata_audit_uses_prepare_changed_files_without_checkout(self):
        metadata_block = self._job_block("metadata-audit")

        self.assertIn("CHANGED_FILES:", metadata_block)
        self.assertNotIn("actions/checkout@v4", metadata_block)
        self.assertNotIn("normalized-safe-checkout", metadata_block)
        self.assertNotIn("git diff --name-only", metadata_block)

    def _job_block(self, job_name):
        start_match = re.search(
            rf"^  {re.escape(job_name)}:\n",
            self.workflow,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(start_match, f"job not found: {job_name}")
        start = start_match.end()
        next_match = re.search(
            r"^  [A-Za-z0-9_-]+:\n",
            self.workflow[start:],
            flags=re.MULTILINE,
        )
        end = start + next_match.start() if next_match else len(self.workflow)
        return self.workflow[start:end]


if __name__ == "__main__":
    unittest.main()
