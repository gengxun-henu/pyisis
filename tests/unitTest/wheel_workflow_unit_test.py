"""Unit tests for cross-platform wheel workflow metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-08-02
Updated: 2026-06-18  Geng Xun added workflow coverage for pip wheel builds.
Updated: 2026-06-19  Geng Xun added optional TestPyPI publish workflow coverage.
Updated: 2026-07-22  Geng Xun required clean Windows wheels to run the basic binding test list.
Updated: 2026-07-22  Geng Xun added isolated Linux wheel build and install coverage.
Updated: 2026-07-23  Geng Xun required manylinux 2.35 builds and Ubuntu 22.04/24.04 install tests.
Updated: 2026-07-23  Geng Xun covered trusted Windows ISIS prefix cache reuse.
Updated: 2026-07-23  Geng Xun gated GitHub Release publication on validated platform wheelhouses.
Updated: 2026-07-23  Geng Xun covered ISIS 10 cp313 manylinux build and clean-install jobs.
Updated: 2026-07-23  Geng Xun covered measured ISIS 10 runtime size budgets.
Updated: 2026-07-23  Geng Xun covered the ISIS 10 Windows source-build wheel gate.
Updated: 2026-07-24  Geng Xun covered ISIS 10 private toolchain verification for Ubuntu 22.04 compatibility.
Updated: 2026-07-24  Geng Xun pinned the official ISIS 10 build and compatible CSM ABI.
Updated: 2026-07-25  Geng Xun pinned the Windows ISIS 10 gate to SpiceQL 1.4.1.
Updated: 2026-07-25  Geng Xun covered ISIS 10-specific Windows wheel metadata checks.
Updated: 2026-07-25  Geng Xun isolated versioned Windows prefix cache inputs and trusted saves.
Updated: 2026-07-25  Geng Xun aligned the four-matrix workflow with the rc2 releases.
Updated: 2026-08-02  Geng Xun separated daily PyISIS checks from platform release matrices.
Updated: 2026-08-02  Geng Xun added Ubuntu 26.04 wheel installation coverage.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WHEEL_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "wheels.yml"
ISIS10_LINUX_ENV = (
    PROJECT_ROOT / "ports" / "linux" / "env" / "pyisis-isis10-linux-64.yml"
)


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

    def test_daily_core_changes_do_not_trigger_release_wheel_matrix(self):
        workflow = self._workflow_text()
        trigger_block = workflow.split("concurrency:", maxsplit=1)[0]

        self.assertNotIn('"CMakeLists.txt"', trigger_block)
        self.assertNotIn('"python/**"', trigger_block)
        self.assertNotIn('"src/**"', trigger_block)

    def test_workflow_routes_linux_and_windows_packaging_changes_separately(self):
        workflow = self._workflow_text()
        scope = self._job_block(workflow, "scope")
        linux = self._job_block(workflow, "linux-cp312-build")
        linux10 = self._job_block(workflow, "linux-isis10-cp313-build")
        windows = self._job_block(workflow, "windows-cp312")
        windows10 = self._job_block(workflow, "windows-isis10-cp313")

        self.assertIn("actions/github-script@v9", scope)
        self.assertIn("pulls.listFiles", scope)
        self.assertIn("run_linux", scope)
        self.assertIn("run_windows", scope)
        for job in (linux, linux10):
            self.assertIn("needs: scope", job)
            self.assertIn("needs.scope.outputs.run_linux == 'true'", job)
        for job in (windows, windows10):
            self.assertIn("needs: scope", job)
            self.assertIn("needs.scope.outputs.run_windows == 'true'", job)

    def test_workflow_uses_windows_runner_and_isis_prefix_resolution(self):
        workflow = self._workflow_text()

        self.assertIn("runs-on: windows-2022", workflow)
        self.assertIn("shell: pwsh", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
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

    def test_workflow_reuses_trusted_windows_isis_prefix_cache(self):
        workflow = self._workflow_text()

        self.assertIn("actions/cache/restore@v6", workflow)
        self.assertIn("id: windows-isis-prefix-cache", workflow)
        self.assertIn(
            "windows-2022-isis-9.0.0-prefix-v1-${{ hashFiles(",
            workflow,
        )
        isis9_cache = workflow.split(
            "- name: Restore cached ISIS 9.0.0 Windows prefix",
            maxsplit=1,
        )[1].split("- name: Build ISIS 9.0.0 Windows prefix", maxsplit=1)[0]
        isis10_cache = workflow.split(
            "- name: Restore cached ISIS 10.0.0 Windows prefix",
            maxsplit=1,
        )[1].split("- name: Build ISIS 10.0.0 Windows prefix", maxsplit=1)[0]

        self.assertIn("'ports/windows/activate_msvc.ps1'", workflow)
        self.assertIn("'ports/windows/env/pyisis-isis-win64.yml'", workflow)
        self.assertNotIn("'ports/windows/isis/**'", workflow)
        self.assertIn("'ports/windows/isis/patches/*.patch'", isis9_cache)
        self.assertNotIn("patches/10.0.0", isis9_cache)
        self.assertNotIn("build_spiceql.ps1", isis9_cache)
        self.assertNotIn("patches/spiceql-", isis9_cache)
        self.assertIn(
            "'ports/windows/isis/patches/10.0.0/*.patch'",
            isis10_cache,
        )
        self.assertIn(
            "'ports/windows/isis/patches/spiceql-1.4.1/*.patch'",
            isis10_cache,
        )
        self.assertNotIn("'ports/windows/isis/patches/*.patch'", isis10_cache)
        self.assertEqual(
            workflow.count("'ports/windows/isis/common.ps1'"),
            2,
        )
        self.assertEqual(
            workflow.count("'ports/windows/isis/build_spiceql.ps1'"),
            1,
        )
        self.assertIn(
            "steps.windows-isis-prefix-cache.outputs.cache-hit != 'true'",
            workflow,
        )
        self.assertEqual(
            workflow.count("ports\\windows\\isis\\verify_isis_prefix.ps1"),
            2,
        )
        self.assertIn("actions/cache/save@v6", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertEqual(
            workflow.count(
                "github.event.pull_request.head.repo.full_name == github.repository"
            ),
            2,
        )
        self.assertIn(
            "steps.windows-isis-prefix-cache.outputs.cache-primary-key",
            workflow,
        )

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
        self.assertEqual(
            workflow.count("env -u LD_LIBRARY_PATH auditwheel show"),
            1,
        )
        self.assertIn("validate_auditwheel_policy.py", workflow)
        self.assertIn("test \"$native_wheel_count\" -eq 1", workflow)
        self.assertIn("usgs-pyisis-linux-cp312-abi-report", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("ubuntu-22.04", workflow)
        self.assertIn("ubuntu-24.04", workflow)
        self.assertEqual(workflow.count("- ubuntu-26.04"), 2)
        self.assertIn("runs-on: ${{ matrix.os }}", workflow)
        self.assertIn("--test-list tools/packaging/basic_tests.txt", workflow)

    def test_workflow_builds_and_tests_isis10_cp313_linux_wheels(self):
        workflow = self._workflow_text()

        self.assertIn("linux-isis10-cp313-build:", workflow)
        self.assertIn("linux-isis10-cp313-clean-install:", workflow)
        self.assertIn("ports/linux/env/pyisis-isis10-linux-64.yml", workflow)
        self.assertIn("packaging/bindings-isis10", workflow)
        self.assertIn("--distribution-name usgs-pyisis-isis10", workflow)
        self.assertIn(
            "--runtime-distribution usgs-pyisis-runtime-isis10-linux-x86_64",
            workflow,
        )
        self.assertIn('python-version: "3.13"', workflow)
        self.assertIn("--package usgs-pyisis-isis10", workflow)
        self.assertIn("--expected-isis-version 10.0.0", workflow)
        self.assertIn(
            "usgs-pyisis-isis10-linux-cp313-manylinux-wheelhouse",
            workflow,
        )
        self.assertIn('PYISIS_MAX_LINUX_RUNTIME_BYTES: "1100000000"', workflow)
        self.assertIn(
            'PYISIS_MAX_LINUX_RUNTIME_WHEEL_BYTES: "550000000"',
            workflow,
        )
        self.assertIn("--vendor-toolchain-runtime", workflow)
        self.assertIn("--target-glibc 2.35", workflow)
        self.assertIn('--wheel-pattern "usgs_pyisis_isis10-*.whl"', workflow)
        self.assertIn("--verify-only", workflow)

    def test_isis10_linux_environment_pins_official_runtime_abi(self):
        environment = ISIS10_LINUX_ENV.read_text(encoding="utf-8")

        self.assertIn("- python=3.13", environment)
        self.assertIn("- isis=10.0.0=h1f94ec8_1", environment)
        self.assertIn("- csm=3.0.3.3", environment)

    def test_workflow_builds_and_tests_isis10_cp313_windows_wheels(self):
        workflow = self._workflow_text()

        self.assertIn("windows-isis10-cp313:", workflow)
        self.assertIn("ports/windows/env/pyisis-isis10-win64.yml", workflow)
        self.assertIn("ports\\windows\\isis\\build_spiceql.ps1", workflow)
        self.assertIn("-Ref 1.4.1", workflow)
        self.assertIn("-Ref 10.0.0", workflow)
        self.assertIn("-PatchDir .\\ports\\windows\\isis\\patches\\10.0.0", workflow)
        self.assertIn("-ExpectedVersion 10.0.0", workflow)
        self.assertIn("-BindingProjectDir packaging\\bindings-isis10", workflow)
        self.assertIn("-DistributionName usgs-pyisis-isis10", workflow)
        self.assertIn(
            "-RuntimeDistribution usgs-pyisis-runtime-isis10-win64",
            workflow,
        )
        self.assertIn("-PackageVersion 1.4.0rc2", workflow)
        self.assertIn("--package usgs-pyisis-isis10", workflow)
        self.assertIn("-ExpectedVersion 1.4.0rc2", workflow)
        self.assertIn("-PythonTag cp313-cp313", workflow)
        self.assertIn("-IsisDataVersion 1.3.0rc2", workflow)
        self.assertIn("usgs-pyisis-isis10-windows-cp313-wheels", workflow)

    def test_workflow_can_publish_configured_release_after_platform_gates(self):
        workflow = self._workflow_text()

        self.assertIn("publish_github_release:", workflow)
        self.assertIn("github-release:", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("linux-cp312-clean-install", workflow)
        self.assertIn("linux-isis10-cp313-clean-install", workflow)
        self.assertIn("windows-cp312", workflow)
        self.assertIn("windows-isis10-cp313", workflow)
        self.assertIn("release_line:", workflow)
        self.assertIn('Path("packaging/releases")', workflow)
        self.assertIn("DISTRIBUTION_NORMALIZED", workflow)
        self.assertIn("RUNTIME_DISTRIBUTION_NORMALIZED", workflow)
        self.assertIn("MINIMAL_DATA_VERSION", workflow)
        self.assertIn("THIRD_PARTY_NOTICES.md", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn('gh release create "$RELEASE_TAG"', workflow)
        self.assertIn("--target \"$GITHUB_SHA\"", workflow)
        self.assertIn("--notes-file \"$RELEASE_NOTES_FILE\"", workflow)

    def _job_block(self, workflow: str, job_name: str) -> str:
        match = re.search(
            rf"^  {re.escape(job_name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
            workflow,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"job not found: {job_name}")
        return match.group(0)


if __name__ == "__main__":
    unittest.main()
