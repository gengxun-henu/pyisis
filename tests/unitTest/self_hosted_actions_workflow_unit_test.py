"""Regression tests for the PyISIS self-hosted Actions configuration.

Author: Geng Xun
Created: 2026-08-01
Last Modified: 2026-08-02
Updated: 2026-08-01  Geng Xun added dedicated runner resolution coverage.
Updated: 2026-08-02  Geng Xun added dual ISIS self-hosted matrix coverage.
Updated: 2026-08-02  Geng Xun required equivalent ISIS 9 and ISIS 10 test gates.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RESOLVER_PATH = REPO_ROOT / ".github" / "scripts" / "resolve_runner_config.py"


def load_resolver():
    if not RESOLVER_PATH.is_file():
        raise AssertionError(f"Missing runner resolver: {RESOLVER_PATH}")
    spec = importlib.util.spec_from_file_location("resolve_runner_config", RESOLVER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load runner resolver: {RESOLVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SelfHostedActionsWorkflowUnitTest(unittest.TestCase):
    """Validate dedicated runner profile normalization and fallback behavior."""

    def test_dedicated_profile_resolves_labels_and_resource_limits(self):
        resolver = load_resolver()
        config_text = """\
active_profile: pyisis-ubuntu26-isis9
fallback_conda_prefix: /opt/conda/envs/isis9
profiles:
  pyisis-ubuntu26-isis9:
    mode: self-hosted
    labels: [self-hosted, linux, x64, pyisis, ubuntu-26.04, isis9]
    checkout_transport: https
    environment_strategy: existing-conda
    network_profile: plain-http
    use_watt: false
    build_jobs: "16"
    ccache_max_size: 20G
    isis_major: "9"
    python_abi: cp312
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "runner-config.yml"
            config_path.write_text(config_text, encoding="utf-8")
            result = resolver.resolve_config(config_path)

        self.assertEqual(result.outputs["runner_profile"], "pyisis-ubuntu26-isis9")
        self.assertEqual(
            json.loads(result.outputs["runs_on_json"]),
            ["self-hosted", "linux", "x64", "pyisis", "ubuntu-26.04", "isis9"],
        )
        self.assertEqual(result.outputs["build_jobs"], "16")
        self.assertEqual(result.outputs["ccache_max_size"], "20G")
        self.assertEqual(result.outputs["isis_major"], "9")
        self.assertEqual(result.outputs["python_abi"], "cp312")
        self.assertEqual(result.diagnostics, ())

    def test_invalid_build_jobs_falls_back_to_sixteen(self):
        resolver = load_resolver()
        config_text = """\
active_profile: invalid-jobs
profiles:
  invalid-jobs:
    mode: self-hosted
    labels: [self-hosted, pyisis]
    build_jobs: all
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "runner-config.yml"
            config_path.write_text(config_text, encoding="utf-8")
            result = resolver.resolve_config(config_path)

        self.assertEqual(result.outputs["build_jobs"], "16")
        self.assertTrue(
            any("Invalid build_jobs 'all'" in item for item in result.diagnostics),
            result.diagnostics,
        )

    def test_repository_config_selects_the_dedicated_runner(self):
        resolver = load_resolver()

        result = resolver.resolve_config(REPO_ROOT / ".github" / "runner-config.yml")

        self.assertEqual(result.outputs["runner_profile"], "pyisis-ubuntu26-isis9")
        self.assertEqual(result.outputs["runner_mode"], "self-hosted")
        self.assertEqual(result.outputs["build_jobs"], "16")
        self.assertEqual(result.outputs["ccache_max_size"], "20G")

    def test_repository_isis10_profile_selects_asp370(self):
        resolver = load_resolver()

        result = resolver.resolve_config(
            REPO_ROOT / ".github" / "runner-config.yml",
            profile_override="pyisis-ubuntu26-isis10",
        )

        self.assertEqual(result.outputs["runner_profile"], "pyisis-ubuntu26-isis10")
        self.assertEqual(
            json.loads(result.outputs["runs_on_json"]),
            ["self-hosted", "linux", "x64", "pyisis", "ubuntu-26.04", "isis10"],
        )
        self.assertEqual(
            result.outputs["fallback_conda_prefix"],
            "/home/gengxun/miniconda3/envs/asp370",
        )
        self.assertEqual(result.outputs["isis_major"], "10")
        self.assertEqual(result.outputs["python_abi"], "cp313")

    def test_composite_action_delegates_to_the_tested_resolver(self):
        action = (
            REPO_ROOT / ".github" / "actions" / "resolve-runner-config" / "action.yml"
        ).read_text(encoding="utf-8")

        self.assertIn(".github/scripts/resolve_runner_config.py", action)
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", action)
        self.assertNotIn("python3 - <<'PY'", action)

    def test_reusable_runner_workflow_forwards_resource_outputs(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "reusable-runner-config.yml"
        ).read_text(encoding="utf-8")

        for name in ("build_jobs", "ccache_max_size", "isis_major", "python_abi"):
            self.assertIn(f"value: ${{{{ jobs.resolve.outputs.{name} }}}}", workflow)
            self.assertIn(f"{name}: ${{{{ steps.resolve.outputs.{name} }}}}", workflow)

    def test_build_workflows_consume_resolved_resource_limits(self):
        wrapper = (
            REPO_ROOT / ".github" / "workflows" / "reusable-pybind-build.yml"
        ).read_text(encoding="utf-8")
        child = (
            REPO_ROOT
            / ".github"
            / "workflows"
            / "reusable-pybind-build-self-hosted.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("build_jobs: ${{ inputs.build_jobs }}", wrapper)
        self.assertIn("ccache_max_size: ${{ inputs.ccache_max_size }}", wrapper)
        self.assertIn('default: "16"', child)
        self.assertIn('default: "20G"', child)
        self.assertIn('[[ "$build_jobs" =~ ^[1-9][0-9]*$ ]]', child)

        for relative_path in (
            ".github/workflows/ci-pybind.yml",
            ".github/workflows/agent-pybind-pr-gate.yml",
        ):
            workflow = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(
                "build_jobs: ${{ needs.resolve_runner.outputs.build_jobs }}", workflow
            )
            self.assertIn(
                "ccache_max_size: ${{ needs.resolve_runner.outputs.ccache_max_size }}",
                workflow,
            )

    def test_pr_and_main_ci_include_trusted_isis10_self_hosted_lane(self):
        for relative_path in (
            ".github/workflows/ci-pybind.yml",
            ".github/workflows/agent-pybind-pr-gate.yml",
        ):
            workflow = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("resolve_runner_isis10:", workflow)
            self.assertIn("runner_profile: pyisis-ubuntu26-isis10", workflow)
            self.assertIn("build_and_smoke_isis10:", workflow)
            self.assertIn("artifact_prefix: ", workflow)
            self.assertIn("-isis10", workflow)
            self.assertIn(
                "fallback_conda_prefix: "
                "${{ needs.resolve_runner_isis10.outputs.fallback_conda_prefix }}",
                workflow,
            )

    def test_pr_and_main_ci_run_equivalent_isis10_test_gates(self):
        pr_workflow = (
            REPO_ROOT / ".github" / "workflows" / "agent-pybind-pr-gate.yml"
        ).read_text(encoding="utf-8")
        main_workflow = (
            REPO_ROOT / ".github" / "workflows" / "ci-pybind.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("unit-tests-isis10:", pr_workflow)
        self.assertIn("needs.build_and_smoke_isis10.outputs.build_succeeded", pr_workflow)
        self.assertIn(
            "needs.build_and_smoke_isis10.outputs.local_build_cache_dir",
            pr_workflow,
        )
        self.assertIn(
            "needs.resolve_runner_isis10.outputs.fallback_conda_prefix",
            pr_workflow,
        )
        self.assertIn("ctest -R python-unit-tests", pr_workflow)

        self.assertIn("run-ctest-isis10-self-hosted:", main_workflow)
        self.assertIn("needs.build_and_smoke_isis10.outputs.build_succeeded", main_workflow)
        self.assertIn(
            "needs.build_and_smoke_isis10.outputs.local_build_cache_dir",
            main_workflow,
        )
        self.assertIn(
            "needs.resolve_runner_isis10.outputs.fallback_conda_prefix",
            main_workflow,
        )
        self.assertGreaterEqual(
            main_workflow.count(
                'ctest --test-dir "$BUILD_DIR" --output-on-failure -V'
            ),
            3,
        )

    def test_ctest_exports_the_configured_python_build_directory(self):
        cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn(
            '"ISIS_PYBIND_BUILD_DIR=${CMAKE_CURRENT_BINARY_DIR}/python"',
            cmake,
        )

    def test_manual_task_and_conda_definition_use_the_same_limits(self):
        task = (
            REPO_ROOT / ".github" / "workflows" / "agent-pybind-task.yml"
        ).read_text(encoding="utf-8")
        conda_environment = (
            REPO_ROOT / ".github" / "conda" / "pybind-ci-environment.yml"
        ).read_text(encoding="utf-8")

        self.assertIn('default: "16"', task)
        self.assertIn('default: "20G"', task)
        self.assertIn('[[ "$build_jobs" =~ ^[1-9][0-9]*$ ]]', task)
        self.assertIn("  - ccache\n", conda_environment)


if __name__ == "__main__":
    unittest.main()
