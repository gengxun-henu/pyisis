# PyISIS Self-Hosted Actions Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a repository-dedicated Ubuntu 26.04 GitHub Actions runner path for ISIS 9 that is safe for a public repository, builds with exactly 16 parallel jobs, and reuses a 20 GiB `ccache` plus persistent CMake build trees.

**Architecture:** Extend the existing runner profile resolver rather than replacing it. A dedicated `pyisis-ubuntu26-isis9` profile exposes runner labels and performance settings to reusable workflows; trusted same-repository PRs and trusted `main` jobs use that profile, while fork and Dependabot PRs are forced onto `github-hosted`. A read-only preflight CLI verifies the host before the runner is registered as a low-privilege system service.

**Tech Stack:** GitHub Actions reusable workflows, YAML, Python 3.12 `unittest`, CMake, Ninja, Conda, `ccache`, GitHub Actions self-hosted runner, systemd

## Global Constraints

- Use the existing `asp360_new` environment at `/home/gengxun/miniconda3/envs/asp360_new`; do not upgrade it to ISIS 10.
- The self-hosted build parallelism is exactly `16`.
- The self-hosted `ccache` maximum size is exactly `20G`.
- The runner is repository-scoped to `https://github.com/gengxun-henu/pyisis`.
- Required labels are `self-hosted`, `linux`, `x64`, `pyisis`, `ubuntu-26.04`, and `isis9`.
- Fork PRs and Dependabot PRs must never execute on the self-hosted runner.
- Keep `.gitignore` and `print.prt` untouched.
- Use Conda for project build dependencies; do not add pip/npm environment provisioning.
- Phase 1 does not install ISIS 10, Docker, or the eight-target release matrix. Those form Phase 2 after this runner path is proven.

---

## File Structure

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `tests/unitTest/self_hosted_actions_workflow_unit_test.py` | Regression checks for dedicated labels, resolver outputs, 16-way builds, 20G cache, and trusted-PR routing. |
| Modify | `.github/runner-config.yml` | Define and activate the repository-dedicated Ubuntu 26/ISIS 9 profile. |
| Modify | `.github/actions/resolve-runner-config/action.yml` | Parse and emit build/cache/environment capability outputs. |
| Create | `.github/scripts/resolve_runner_config.py` | Testable runner profile parser used by the composite action. |
| Modify | `.github/workflows/reusable-runner-config.yml` | Forward new normalized outputs to callers. |
| Modify | `.github/workflows/reusable-pybind-build.yml` | Accept and forward self-hosted build/cache settings. |
| Modify | `.github/workflows/reusable-pybind-build-self-hosted.yml` | Validate explicit build parallelism and use the configured cache limit. |
| Modify | `.github/workflows/ci-pybind.yml` | Pass centralized build/cache settings into the trusted mainline build. |
| Modify | `.github/workflows/agent-pybind-pr-gate.yml` | Route same-repo trusted PRs to the dedicated runner and all untrusted PRs to GitHub-hosted. |
| Modify | `.github/workflows/agent-pybind-task.yml` | Make manual self-hosted defaults match 16 jobs and 20G. |
| Modify | `.github/conda/pybind-ci-environment.yml` | Ensure `ccache` is part of the reproducible CI toolchain definition. |
| Create | `scripts/check_self_hosted_runner.py` | Read-only host and Conda/ISIS 9 readiness check with machine-readable JSON output. |
| Create | `tests/unitTest/self_hosted_runner_preflight_unit_test.py` | Unit tests for preflight success and failure reporting. |
| Modify | `.github/workflows/README.md` | Document runner registration, labels, security policy, preflight, cache paths, and recovery. |

---

### Task 1: Add the Dedicated Runner Profile and Resolver Outputs

**Files:**
- Create: `tests/unitTest/self_hosted_actions_workflow_unit_test.py`
- Modify: `.github/runner-config.yml`
- Modify: `.github/actions/resolve-runner-config/action.yml`
- Create: `.github/scripts/resolve_runner_config.py`
- Modify: `.github/workflows/reusable-runner-config.yml`

**Interfaces:**
- Consumes: selected profile keys `build_jobs`, `ccache_max_size`, `isis_major`, and `python_abi`.
- Produces: a `unittest` regression contract plus reusable workflow outputs with the same names, all represented as strings.

- [ ] **Step 1: Create the focused test module**

Create `tests/unitTest/self_hosted_actions_workflow_unit_test.py` with the following content:

```python
"""Regression tests for the PyISIS self-hosted Actions configuration.

Author: Geng Xun
Created: 2026-08-01
Last Modified: 2026-08-01
Updated: 2026-08-01  Geng Xun added dedicated runner, resource, and trust-policy coverage.
"""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"Missing repository file: {path}")
    return path.read_text(encoding="utf-8")


class SelfHostedActionsWorkflowUnitTest(unittest.TestCase):
    """Validate routing and resource contracts for the dedicated runner."""

    def test_runner_profile_has_dedicated_capability_labels(self):
        config = read_repo_file(".github/runner-config.yml")

        self.assertIn("active_profile: pyisis-ubuntu26-isis9", config)
        self.assertIn("pyisis-ubuntu26-isis9:", config)
        self.assertIn(
            "labels: [self-hosted, linux, x64, pyisis, ubuntu-26.04, isis9]",
            config,
        )
        self.assertIn('build_jobs: "16"', config)
        self.assertIn("ccache_max_size: 20G", config)
        self.assertIn('isis_major: "9"', config)
        self.assertIn("python_abi: cp312", config)

    def test_runner_resolver_exports_resource_and_capability_settings(self):
        action = read_repo_file(".github/actions/resolve-runner-config/action.yml")
        reusable = read_repo_file(".github/workflows/reusable-runner-config.yml")

        for output_name in (
            "build_jobs",
            "ccache_max_size",
            "isis_major",
            "python_abi",
        ):
            self.assertIn(f"  {output_name}:", action)
            self.assertIn(f"      {output_name}:", reusable)
            self.assertIn(
                f"value: ${{{{ jobs.resolve.outputs.{output_name} }}}}", reusable
            )

    def test_shared_build_forwards_explicit_parallelism_and_cache_size(self):
        wrapper = read_repo_file(".github/workflows/reusable-pybind-build.yml")
        self_hosted = read_repo_file(
            ".github/workflows/reusable-pybind-build-self-hosted.yml"
        )

        self.assertIn("      build_jobs:", wrapper)
        self.assertIn("      ccache_max_size:", wrapper)
        self.assertIn("build_jobs: ${{ inputs.build_jobs }}", wrapper)
        self.assertIn("ccache_max_size: ${{ inputs.ccache_max_size }}", wrapper)
        self.assertIn('default: "16"', self_hosted)
        self.assertIn('default: "20G"', self_hosted)
        self.assertIn('[[ "$build_jobs" =~ ^[1-9][0-9]*$ ]]', self_hosted)

    def test_pr_gate_routes_untrusted_code_to_github_hosted(self):
        workflow = read_repo_file(".github/workflows/agent-pybind-pr-gate.yml")

        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("github.actor != 'dependabot[bot]'", workflow)
        self.assertIn("'pyisis-ubuntu26-isis9'", workflow)
        self.assertIn("'github-hosted'", workflow)

    def test_trusted_callers_pass_central_resource_outputs(self):
        for relative_path in (
            ".github/workflows/ci-pybind.yml",
            ".github/workflows/agent-pybind-pr-gate.yml",
        ):
            workflow = read_repo_file(relative_path)
            self.assertIn(
                "build_jobs: ${{ needs.resolve_runner.outputs.build_jobs }}", workflow
            )
            self.assertIn(
                "ccache_max_size: ${{ needs.resolve_runner.outputs.ccache_max_size }}",
                workflow,
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and verify the expected failures**

Run:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.self_hosted_actions_workflow_unit_test -v
```

Expected: FAIL because the dedicated profile, resolver outputs, explicit wrapper inputs, and trust routing do not exist yet.

- [ ] **Step 3: Define and activate the dedicated profile**

In `.github/runner-config.yml`, set:

```yaml
active_profile: pyisis-ubuntu26-isis9
```

Add this profile before the generic fallback profiles:

```yaml
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
```

Keep `self-hosted-http`, `self-hosted-watt`, `self-hosted-ssh`, and
`github-hosted` as explicit fallbacks. Give every fallback deterministic values:

```yaml
    build_jobs: "16"
    ccache_max_size: 20G
    isis_major: "9"
    python_abi: cp312
```

For `github-hosted`, these values describe the current ISIS 9 CI environment;
they do not change its runner image.

- [ ] **Step 4: Add action output declarations and normalized defaults**

In `.github/actions/resolve-runner-config/action.yml`, add outputs:

```yaml
  build_jobs:
    description: Positive self-hosted CMake build parallelism.
    value: ${{ steps.resolve.outputs.build_jobs }}
  ccache_max_size:
    description: Maximum compiler cache size.
    value: ${{ steps.resolve.outputs.ccache_max_size }}
  isis_major:
    description: ISIS major line selected by the runner profile.
    value: ${{ steps.resolve.outputs.isis_major }}
  python_abi:
    description: CPython ABI selected by the runner profile.
    value: ${{ steps.resolve.outputs.python_abi }}
```

Add these keys to every built-in profile in the embedded Python defaults. After
profile selection, normalize them with:

```python
        build_jobs = str(selected_profile.get("build_jobs", "16")).strip()
        if not build_jobs.isdigit() or int(build_jobs) < 1:
            diagnostics.append(
                f"Invalid build_jobs '{build_jobs}', falling back to 16."
            )
            build_jobs = "16"
        ccache_max_size = str(
            selected_profile.get("ccache_max_size", "20G")
        ).strip() or "20G"
        isis_major = str(selected_profile.get("isis_major", "9")).strip() or "9"
        python_abi = str(
            selected_profile.get("python_abi", "cp312")
        ).strip() or "cp312"
```

Apply the same defaults in the legacy-config branch. Add all four strings to
the `outputs` mapping and Actions summary.

- [ ] **Step 5: Forward resolver outputs through the reusable workflow**

Add the four output declarations under `on.workflow_call.outputs` and the four
job outputs under `jobs.resolve.outputs` in
`.github/workflows/reusable-runner-config.yml`. Each job output must reference
`steps.resolve.outputs.build_jobs`, `steps.resolve.outputs.ccache_max_size`,
`steps.resolve.outputs.isis_major`, or `steps.resolve.outputs.python_abi`.

- [ ] **Step 6: Run the focused workflow policy test**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.self_hosted_actions_workflow_unit_test -v
```

Expected: resolver/profile tests PASS; wrapper and PR-routing tests still FAIL.

- [ ] **Step 7: Commit the profile, resolver, and regression test**

```bash
git add tests/unitTest/self_hosted_actions_workflow_unit_test.py \
  .github/runner-config.yml \
  .github/actions/resolve-runner-config/action.yml \
  .github/workflows/reusable-runner-config.yml
git commit -m "ci: add dedicated pyisis runner profile"
```

---

### Task 2: Enforce 16-Way Builds and a 20G Compiler Cache

**Files:**
- Modify: `.github/workflows/reusable-pybind-build.yml`
- Modify: `.github/workflows/reusable-pybind-build-self-hosted.yml`
- Modify: `.github/workflows/ci-pybind.yml`
- Modify: `.github/workflows/agent-pybind-pr-gate.yml`
- Modify: `.github/workflows/agent-pybind-task.yml`
- Modify: `.github/conda/pybind-ci-environment.yml`
- Test: `tests/unitTest/self_hosted_actions_workflow_unit_test.py`

**Interfaces:**
- Consumes: `build_jobs` and `ccache_max_size` outputs from Task 1.
- Produces: explicit `workflow_call` inputs forwarded to the self-hosted child workflow.

- [ ] **Step 1: Add and forward wrapper inputs**

In `.github/workflows/reusable-pybind-build.yml`, add:

```yaml
      build_jobs:
        description: Positive CMake build parallelism for self-hosted builds.
        required: false
        default: "16"
        type: string
      ccache_max_size:
        description: Maximum size for the self-hosted ccache directory.
        required: false
        default: "20G"
        type: string
```

The file already has a `ccache_max_size` input; update its default and avoid
creating a duplicate key. Under `jobs.self_hosted.with`, forward:

```yaml
      build_jobs: ${{ inputs.build_jobs }}
      ccache_max_size: ${{ inputs.ccache_max_size }}
```

Do not forward `build_jobs` to the GitHub-hosted child because Phase 1 only
reserves host resources on the dedicated machine.

- [ ] **Step 2: Validate the self-hosted build input**

In `.github/workflows/reusable-pybind-build-self-hosted.yml`, change defaults to
`"16"` and `"20G"`. Replace the `auto -> nproc` fallback in the build step with:

```bash
build_jobs="$BUILD_JOBS_INPUT"
if ! [[ "$build_jobs" =~ ^[1-9][0-9]*$ ]]; then
  echo "::error::build_jobs must be a positive integer; got: $build_jobs"
  exit 2
fi
```

Keep the existing `cmake --build ... --parallel "$build_jobs"` command and
summary output.

- [ ] **Step 3: Pass centralized settings from trusted callers**

Add these lines to the `with` block of the shared build call in both
`.github/workflows/ci-pybind.yml` and
`.github/workflows/agent-pybind-pr-gate.yml`:

```yaml
      build_jobs: ${{ needs.resolve_runner.outputs.build_jobs }}
      ccache_max_size: ${{ needs.resolve_runner.outputs.ccache_max_size }}
```

- [ ] **Step 4: Align the manual task workflow defaults**

In `.github/workflows/agent-pybind-task.yml`, change `build_jobs.default` from
`auto` to `"16"`, change `ccache_max_size.default` from `"10G"` to `"20G"`,
and replace its `auto -> nproc` build fallback with the same positive-integer
validation used by the reusable self-hosted workflow.

- [ ] **Step 5: Add `ccache` to the CI Conda definition**

Append `ccache` to `.github/conda/pybind-ci-environment.yml` dependencies. Do
not add pip dependencies.

- [ ] **Step 6: Run the focused tests**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.self_hosted_actions_workflow_unit_test -v
```

Expected: profile/resolver/resource tests PASS; PR trust-routing test still FAIL.

- [ ] **Step 7: Commit resource enforcement**

```bash
git add .github/workflows/reusable-pybind-build.yml \
  .github/workflows/reusable-pybind-build-self-hosted.yml \
  .github/workflows/ci-pybind.yml \
  .github/workflows/agent-pybind-pr-gate.yml \
  .github/workflows/agent-pybind-task.yml \
  .github/conda/pybind-ci-environment.yml
git commit -m "ci: cap self-hosted builds at 16 jobs"
```

---

### Task 3: Keep Untrusted PRs off the Persistent Runner

**Files:**
- Modify: `.github/workflows/agent-pybind-pr-gate.yml`
- Modify: `tests/unitTest/workflow_policy_unit_test.py`
- Test: `tests/unitTest/self_hosted_actions_workflow_unit_test.py`

**Interfaces:**
- Consumes: GitHub event fields `pull_request.head.repo.full_name`, `repository`, and `actor`.
- Produces: `runner_profile` input equal to `pyisis-ubuntu26-isis9` only for trusted same-repository non-Dependabot PRs; otherwise `github-hosted`.

- [ ] **Step 1: Add a failing semantic policy assertion**

Update the metadata at the top of `tests/unitTest/workflow_policy_unit_test.py`
to include `Author`, `Created`, `Last Modified`, and an `Updated` line dated
`2026-08-01`. Add this method to `AgentPybindPrGatePolicyTest`:

```python
    def test_pr_gate_routes_only_trusted_same_repo_prs_to_self_hosted(self):
        resolve_runner_block = self._job_block("resolve_runner")

        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            resolve_runner_block,
        )
        self.assertIn("github.actor != 'dependabot[bot]'", resolve_runner_block)
        self.assertIn("'pyisis-ubuntu26-isis9'", resolve_runner_block)
        self.assertIn("'github-hosted'", resolve_runner_block)
```

Run:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.workflow_policy_unit_test -v
```

Expected: FAIL because `resolve_runner` has no trust-sensitive profile input.

- [ ] **Step 2: Route untrusted PRs to GitHub-hosted**

Change the `resolve_runner` reusable call in
`.github/workflows/agent-pybind-pr-gate.yml` to:

```yaml
  resolve_runner:
    name: Resolve runner mode
    uses: ./.github/workflows/reusable-runner-config.yml
    with:
      runner_profile: ${{ github.event.pull_request.head.repo.full_name == github.repository && github.actor != 'dependabot[bot]' && 'pyisis-ubuntu26-isis9' || 'github-hosted' }}
```

Do not use `pull_request_target`. All downstream jobs already consume the
resolved `runs_on_json`, so this one decision routes prepare/build/unit jobs
consistently.

- [ ] **Step 3: Run both policy modules**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.workflow_policy_unit_test \
  tests.unitTest.self_hosted_actions_workflow_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Commit the trust boundary**

```bash
git add .github/workflows/agent-pybind-pr-gate.yml \
  tests/unitTest/workflow_policy_unit_test.py
git commit -m "ci: isolate self-hosted runner from fork PRs"
```

---

### Task 4: Add a Read-Only Host Preflight

**Files:**
- Create: `scripts/check_self_hosted_runner.py`
- Create: `tests/unitTest/self_hosted_runner_preflight_unit_test.py`

**Interfaces:**
- Produces: `inspect_host(conda_prefix: Path, expected_jobs: int, expected_isis_major: int, expected_python: tuple[int, int]) -> dict[str, object]`.
- CLI: `python scripts/check_self_hosted_runner.py --conda-prefix PATH --expected-jobs 16 --expected-isis-major 9 --expected-python 3.12 [--require-ccache] [--json]`.
- Exit status: `0` when every required check passes; `1` when a required check fails; `2` for invalid CLI input.

- [ ] **Step 1: Write failing preflight unit tests**

Create `tests/unitTest/self_hosted_runner_preflight_unit_test.py` with metadata
required by the scoped test instructions. Load the script with
`importlib.util.spec_from_file_location`, then add these tests:

```python
    def test_inspect_host_reports_expected_resources_and_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            (prefix / "include" / "isis").mkdir(parents=True)
            (prefix / "lib").mkdir()
            (prefix / "lib" / "libisis.so").touch()
            (prefix / "lib" / "Camera.plugin").touch()
            (prefix / "bin").mkdir()
            (prefix / "bin" / "python").touch()
            report = MODULE.inspect_host(
                prefix,
                expected_jobs=16,
                expected_isis_major=9,
                expected_python=(3, 12),
                cpu_count=32,
                memory_bytes=64 * 1024**3,
                available_bytes=200 * 1024**3,
                isis_version="9.0.0",
                python_version=(3, 12, 2),
            )

        self.assertEqual(report["expected_jobs"], 16)
        self.assertTrue(report["checks"]["cpu_capacity"]["ok"])
        self.assertTrue(report["checks"]["memory_capacity"]["ok"])
        self.assertTrue(report["checks"]["disk_capacity"]["ok"])
        self.assertTrue(report["checks"]["isis_prefix_shape"]["ok"])
        self.assertTrue(report["checks"]["isis_version"]["ok"])
        self.assertTrue(report["checks"]["python_version"]["ok"])

    def test_inspect_host_rejects_more_jobs_than_visible_cpus(self):
        report = MODULE.inspect_host(
            Path("/missing"),
            expected_jobs=16,
            expected_isis_major=9,
            expected_python=(3, 12),
            cpu_count=8,
            memory_bytes=64 * 1024**3,
            available_bytes=200 * 1024**3,
            isis_version="9.0.0",
            python_version=(3, 12, 2),
        )

        self.assertFalse(report["checks"]["cpu_capacity"]["ok"])

    def test_main_returns_one_when_required_tool_is_missing(self):
        with mock.patch.object(MODULE, "inspect_host") as inspect_host:
            inspect_host.return_value = {
                "ok": False,
                "checks": {"ccache": {"ok": False, "detail": "not found"}},
            }
            exit_code = MODULE.main(
                [
                    "--conda-prefix", "/missing",
                    "--expected-jobs", "16",
                    "--expected-isis-major", "9",
                    "--expected-python", "3.12",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 1)
```

Run the module and expect import failure because the script does not exist.

- [ ] **Step 2: Implement the minimum preflight CLI**

Create `scripts/check_self_hosted_runner.py` with the required metadata header.
Implement:

```python
def inspect_host(
    conda_prefix: Path,
    expected_jobs: int,
    expected_isis_major: int,
    expected_python: tuple[int, int],
    *,
    cpu_count: int | None = None,
    memory_bytes: int | None = None,
    available_bytes: int | None = None,
    isis_version: str | None = None,
    python_version: tuple[int, int, int] | None = None,
    require_ccache: bool = False,
) -> dict[str, object]:
```

Use `os.cpu_count()`, `/proc/meminfo`, `shutil.disk_usage(conda_prefix.parent)`,
`shutil.which`, and explicit checks for `include/isis`, `lib/libisis.so`,
`lib/Camera.plugin`, and `bin/python`. Require at least `expected_jobs` visible
CPUs, 16 GiB total memory, and 20 GiB free disk. Check `cmake`, `ninja`, the
Conda compiler `bin/x86_64-conda-linux-gnu-c++`, and `ccache` either on PATH or
inside the prefix. Read the ISIS version from `conda-meta/isis-*.json` and the
Python version by invoking `bin/python`; injected versions exist only to keep
unit tests deterministic. Require ISIS major `9` and Python `3.12`.
`--require-ccache` controls whether missing `ccache` is fatal.

The JSON report must contain:

```python
{
    "ok": bool,
    "conda_prefix": str,
    "expected_jobs": int,
    "expected_isis_major": int,
    "expected_python": str,
    "checks": {str: {"ok": bool, "detail": str}},
}
```

Keep the script read-only: it must not install packages, change ACLs, register a
runner, or delete caches.

- [ ] **Step 3: Run the preflight unit tests**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.self_hosted_runner_preflight_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Run the preflight against the real ISIS 9 environment**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
python scripts/check_self_hosted_runner.py \
  --conda-prefix /home/gengxun/miniconda3/envs/asp360_new \
  --expected-jobs 16 \
  --expected-isis-major 9 \
  --expected-python 3.12 \
  --json
```

Expected before `ccache` installation: overall PASS when `--require-ccache` is
omitted, with `ccache` reported as optional and missing.

- [ ] **Step 5: Commit the preflight**

```bash
git add scripts/check_self_hosted_runner.py \
  tests/unitTest/self_hosted_runner_preflight_unit_test.py
git commit -m "ci: add self-hosted runner preflight"
```

---

### Task 5: Document Operations and Validate Repository Changes

**Files:**
- Modify: `.github/workflows/README.md`
- Test: all files changed in Tasks 1–5

**Interfaces:**
- Consumes: runner profile, preflight CLI, cache behavior, and trust policy from Tasks 1–4.
- Produces: operator runbook with exact locations and recovery checks.

- [ ] **Step 1: Add the Phase 1 runbook**

Document these exact values in `.github/workflows/README.md`:

```text
Repository: https://github.com/gengxun-henu/pyisis
Runner name: pyisis-ubuntu26
Runner account: pyisis-runner
Runner application: /opt/actions-runner-pyisis
Runner HOME/cache root: /var/lib/pyisis-runner
Conda prefix: /home/gengxun/miniconda3/envs/asp360_new
Labels: self-hosted,linux,x64,pyisis,ubuntu-26.04,isis9
Build jobs: 16
ccache max size: 20G
Build-cache retention: 7 days
```

Include the preflight command, service status/log commands, GitHub Settings path
(`Settings → Actions → Runners`), fork/Dependabot policy, cache locations, and a
recovery sequence that stops at diagnostics rather than deleting user data.

- [ ] **Step 2: Run focused workflow and preflight tests**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.workflow_policy_unit_test \
  tests.unitTest.self_hosted_actions_workflow_unit_test \
  tests.unitTest.self_hosted_runner_preflight_unit_test -v
```

Expected: PASS.

- [ ] **Step 3: Run existing packaging workflow regression tests**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.wheel_workflow_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Run smoke import**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 5: Run a local 16-way incremental build**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
cmake --build build --parallel 16
```

Expected: build completes successfully.

- [ ] **Step 6: Commit docs and any validation corrections**

```bash
git add .github/workflows/README.md
git commit -m "docs: add pyisis runner operations guide"
```

---

### Task 6: Provision and Register the Host Runner

**Files:**
- No repository files; this task changes host and GitHub repository state.

**Interfaces:**
- Consumes: repository admin access, an ephemeral GitHub registration token, the committed Phase 1 workflows, and the runbook from Task 6.
- Produces: `pyisis-ubuntu26` systemd service visible as an online repository-level runner.

- [ ] **Step 1: Install `ninja` and `ccache` into the existing Conda environment**

This is an explicit environment mutation and requires user approval before execution:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
conda install --channel conda-forge ninja ccache
```

Then require it in preflight:

```bash
python scripts/check_self_hosted_runner.py \
  --conda-prefix /home/gengxun/miniconda3/envs/asp360_new \
  --expected-jobs 16 \
  --expected-isis-major 9 \
  --expected-python 3.12 \
  --require-ccache \
  --json
```

Expected: exit `0`, ISIS prefix checks pass, and both `ninja` and `ccache` are found.

- [ ] **Step 2: Create the service account and minimal directories**

This requires administrator approval:

```bash
sudo useradd --system --create-home \
  --home-dir /var/lib/pyisis-runner \
  --shell /usr/sbin/nologin pyisis-runner
sudo install -d -o pyisis-runner -g pyisis-runner \
  /opt/actions-runner-pyisis \
  /var/lib/pyisis-runner/.cache/pyisis-gha
```

If the account already exists, verify it with `getent passwd pyisis-runner`
instead of recreating it.

- [ ] **Step 3: Grant minimum Conda traversal/read ACLs**

This requires administrator approval:

```bash
sudo setfacl -m u:pyisis-runner:x /home/gengxun
sudo setfacl -m u:pyisis-runner:x /home/gengxun/miniconda3
sudo setfacl -m u:pyisis-runner:x /home/gengxun/miniconda3/envs
sudo setfacl -R -m u:pyisis-runner:rX \
  /home/gengxun/miniconda3/envs/asp360_new
```

Verify with:

```bash
sudo -u pyisis-runner \
  /home/gengxun/miniconda3/envs/asp360_new/bin/python --version
```

Expected: Python 3.12.x. Do not add `pyisis-runner` to the `gengxun` group.

- [ ] **Step 4: Download and verify the current official runner archive**

At execution time, use the exact Linux x64 download URL and SHA-256 shown by
GitHub under `Settings → Actions → Runners → New self-hosted runner`. Download
to `/tmp`, verify the displayed digest with `sha256sum --check`, and extract as
`pyisis-runner` into `/opt/actions-runner-pyisis`. Do not execute an archive
whose digest does not match GitHub's displayed value.

- [ ] **Step 5: Obtain and enter the ephemeral registration token**

Because the current `gh` authentication is invalid, either re-authenticate with
`gh auth login -h github.com` or copy the one-hour repository registration token
from the GitHub runner page. Read it without echoing:

```bash
read -rsp "GitHub runner registration token: " PYISIS_RUNNER_TOKEN
printf '\n'
```

Register from `/opt/actions-runner-pyisis` as `pyisis-runner`:

```bash
sudo -u pyisis-runner ./config.sh \
  --unattended \
  --url https://github.com/gengxun-henu/pyisis \
  --token "$PYISIS_RUNNER_TOKEN" \
  --name pyisis-ubuntu26 \
  --labels pyisis,ubuntu-26.04,isis9 \
  --work _work
unset PYISIS_RUNNER_TOKEN
```

Run the command from `/opt/actions-runner-pyisis`. The default labels add
`self-hosted`, `linux`, and `x64` automatically.

- [ ] **Step 6: Install and start the systemd service**

From `/opt/actions-runner-pyisis`:

```bash
sudo ./svc.sh install pyisis-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

Expected: service is active and GitHub lists `pyisis-ubuntu26` as Idle/Online.

- [ ] **Step 7: Run remote sanity and build verification**

After pushing the implementation branch, manually dispatch
`runner-host-sanity-check.yml`, then `ci-pybind.yml`. Verify in the Actions
summary:

```text
runs-on labels include pyisis, ubuntu-26.04, and isis9
effective build jobs = 16
ccache max size = 20G
smoke import = success
```

Dispatch `ci-pybind.yml` a second time without source changes and verify that
the persistent build tree is reused or `ccache` reports cache hits.

- [ ] **Step 8: Verify the fork boundary before declaring success**

Use a test fork PR that changes only a harmless documentation line. Confirm the
PR gate resolves `runner_profile=github-hosted` and no job from that run appears
in the `pyisis-ubuntu26` runner service log. Close the test PR after recording
the result.

---

## Phase 1 Completion Gate

Phase 1 is complete only when:

- all focused workflow/preflight tests and `tests/smoke_import.py` pass locally;
- a local build succeeds with `--parallel 16`;
- GitHub shows the repository-level runner online with all six required labels;
- two manual self-hosted runs prove build/cache reuse and report `20G` ccache;
- a fork PR is routed to `github-hosted` and never reaches the self-hosted service.

After this gate, write the separate Phase 2 plan for Docker installation,
ISIS 10/CPython 3.13 provisioning, `manylinux_2_28_x86_64` builds, Ubuntu
22.04/24.04/26.04 install verification, Windows ISIS 10 enablement, and the
complete eight-target release gate.
