"""Regression checks for GitHub Actions workflow routing policy.

Author: Geng Xun
Created: 2026-08-01
Last Modified: 2026-08-02
Updated: 2026-08-01  Geng Xun added the public-repository self-hosted trust boundary.
Updated: 2026-08-02  Geng Xun restricted persistent runner access to the repository owner.
"""

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PR_GATE = REPO_ROOT / ".github" / "workflows" / "agent-pybind-pr-gate.yml"


class AgentPybindPrGatePolicyTest(unittest.TestCase):
    def setUp(self):
        self.workflow = PR_GATE.read_text(encoding="utf-8")

    def test_pr_gate_routes_only_trusted_same_repo_prs_to_self_hosted(self):
        resolve_runner_block = self._job_block("resolve_runner")

        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            resolve_runner_block,
        )
        self.assertIn("github.actor == 'gengxun-henu'", resolve_runner_block)
        self.assertIn("'pyisis-ubuntu26-isis9'", resolve_runner_block)
        self.assertIn("'github-hosted'", resolve_runner_block)

        isis10_block = self._job_block("resolve_runner_isis10")
        self.assertIn("github.actor == 'gengxun-henu'", isis10_block)

    def test_workflows_use_node24_official_action_majors(self):
        action_files = list((REPO_ROOT / ".github").rglob("*.yml"))
        combined = "\n".join(path.read_text(encoding="utf-8") for path in action_files)

        self.assertNotIn("actions/checkout@v4", combined)
        self.assertNotIn("actions/github-script@v7", combined)
        self.assertNotIn("actions/setup-python@v5", combined)
        self.assertIn("actions/checkout@v7", combined)
        self.assertIn("actions/github-script@v9", combined)
        self.assertIn("actions/setup-python@v7", combined)

    def test_pr_gate_avoids_full_history_checkout_for_change_summary(self):
        self.assertNotIn("fetch-depth: 0", self.workflow)
        self.assertIn("actions/github-script@v9", self.workflow)
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
        self.assertNotIn("actions/checkout@v7", metadata_block)
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
