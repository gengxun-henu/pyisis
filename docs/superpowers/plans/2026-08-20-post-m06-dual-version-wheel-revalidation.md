# Post-M06 Dual-Version Wheel Revalidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce fresh current-HEAD evidence for the Linux/Windows × ISIS 9/10 PyISIS wheel matrix without publishing a release.

**Architecture:** Use the existing `.github/workflows/wheels.yml` release lanes rather than reproducing them ad hoc. Freeze the current commit, run the existing workflow at that exact remote ref, then collect only the produced matrix evidence and classify the earliest failure layer if any job fails.

**Tech Stack:** GitHub Actions, GitHub CLI or authenticated GitHub REST dispatch, Windows PowerShell 7, Bash, CMake/Ninja, conda, CPython 3.12/3.13, Python `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-19-post-m06-dual-version-wheel-revalidation-design.md`

## Global Constraints

- Validate the exact current Git commit; do not claim rc2 artifact evidence for this HEAD.
- Use the existing `wheels.yml` workflow and its existing ISIS 9/10 pins and Windows SpiceQL 1.4.1 export/link probe.
- Do not alter product code, workflow logic, cache keys, dependency pins, or patches unless a completed run identifies the earliest failing layer and a separate repair design is approved.
- Do not create or publish a GitHub Release, upload release assets, or modify M06 artifacts.
- Preserve the guarded `print.prt`; do not stage, restore, delete, or modify it.
- Retain only reports, workflow identifiers, hashes, and release-relevant artifacts after verification; remove temporary build trees only under the repository disk-space rules.

---

## File Structure

| Path | Responsibility |
|---|---|
| `.github/workflows/wheels.yml` | Existing authoritative four-lane build/install/metadata workflow; read-only unless a later repair milestone changes it. |
| `docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json` | New schema-1 evidence report created after all run results are collected. |
| `.planning/post-m06-dual-version-wheel-revalidation-m08/*` | Durable M08 goal, findings, progress, and exact Next Step. |
| `docs/superpowers/plans/2026-08-20-post-m06-dual-version-wheel-revalidation.md` | This execution plan. |

### Task 1: Freeze current-HEAD validation inputs

**Files:**
- Create: `.planning/post-m06-dual-version-wheel-revalidation-m08/task_plan.md`
- Create: `.planning/post-m06-dual-version-wheel-revalidation-m08/findings.md`
- Create: `.planning/post-m06-dual-version-wheel-revalidation-m08/progress.md`
- Verify: `.github/workflows/wheels.yml`

**Interfaces:**
- Consumes: current branch `feature/m04-windows-pyisis-wheelhouse`, `HEAD`, guarded `print.prt`, and the committed workflow.
- Produces: one immutable commit ID, classified Git status, and a recorded mapping from the four required lanes to their workflow job IDs.

- [ ] **Step 1: Record Git state before any remote action**

Run:

```powershell
$repo = 'D:\code\pyisis\pyisis\.worktrees\m04-windows-pyisis-wheelhouse'
git -C $repo status --short --branch
git -C $repo rev-parse HEAD
git -C $repo diff --check
```

Expected: no whitespace errors; only the pre-existing guarded `print.prt` may be unstaged.

- [ ] **Step 2: Verify the required workflow contract from tracked text**

Run:

```powershell
python -m unittest `
  tests.unitTest.wheel_workflow_unit_test `
  tests.unitTest.packaging_tools_unit_test -v
```

Expected: the tests pass and assert the existing Windows ISIS 10 cp313 lane invokes `build_spiceql.ps1 -Ref 1.4.1`, builds the prefix, runs isolated installation, and uploads wheels plus DLL reports.

- [ ] **Step 3: Create the durable M08 plan files**

Set the goal to current-HEAD four-lane verification; enumerate `linux-isis9`, `linux-isis10-cp313`, `windows-cp312`, and `windows-isis10-cp313`; and record the unique Next Step as remote workflow dispatch. Include the exact HEAD and output directory in `progress.md`.

- [ ] **Step 4: Commit planning-only files when they are complete**

```powershell
git add -- .planning/post-m06-dual-version-wheel-revalidation-m08 `
  docs/superpowers/plans/2026-08-20-post-m06-dual-version-wheel-revalidation.md
git commit -m 'docs: plan post-M06 wheel revalidation'
```

Expected: the commit excludes `print.prt`, release outputs, and product code.

### Task 2: Make the frozen commit available to the workflow

**Files:**
- Verify: `.github/workflows/wheels.yml`
- Verify: `docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json` (created in Task 4)

**Interfaces:**
- Consumes: the Task 1 committed SHA and authorized `origin` remote.
- Produces: a remote branch/ref resolving to exactly that SHA, suitable for `workflow_dispatch`.

- [ ] **Step 1: Confirm the remote and branch relation without rewriting history**

Run:

```powershell
git remote -v
git status --short --branch
git rev-parse HEAD
```

Expected: `origin` resolves to the PyISIS repository. If the tracked upstream remains `[gone]`, retain the current local branch name and create a normal non-force upstream push; do not use `--force` or rewrite history.

- [ ] **Step 2: Push the frozen branch normally**

Run:

```powershell
git push --set-upstream origin feature/m04-windows-pyisis-wheelhouse
```

Expected: remote `origin/feature/m04-windows-pyisis-wheelhouse` resolves to the recorded Task 1 SHA. If the server rejects the push or the remote branch has diverged, stop and record the server message; do not merge, force-push, or select another ref.

- [ ] **Step 3: Verify remote SHA equality**

Run:

```powershell
$local = (git rev-parse HEAD).Trim()
$remote = (git ls-remote origin refs/heads/feature/m04-windows-pyisis-wheelhouse).Split()[0]
if ($local -ne $remote) { throw "Remote SHA mismatch: local=$local remote=$remote" }
```

Expected: exact SHA equality.

### Task 3: Dispatch and monitor the four-lane workflow

**Files:**
- Verify: `.github/workflows/wheels.yml`
- Create: `docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json` (Task 4)

**Interfaces:**
- Consumes: the remote SHA from Task 2 and the `wheels.yml` workflow.
- Produces: one workflow run ID with the four required lane conclusions and downloadable artifacts.

- [ ] **Step 1: Dispatch only the validation workflow at the frozen ref**

Run:

```powershell
gh workflow run wheels.yml `
  --repo gengxun-henu/pyisis `
  --ref feature/m04-windows-pyisis-wheelhouse `
  -f release_line=none
```

Expected: GitHub accepts a new workflow-dispatch event. If authentication or input names differ, use `gh workflow view wheels.yml --repo gengxun-henu/pyisis --yaml` and update only the command invocation; do not change the workflow file.

- [ ] **Step 2: Record the new run ID and wait for completion**

Run:

```powershell
gh run list --repo gengxun-henu/pyisis --workflow wheels.yml --branch feature/m04-windows-pyisis-wheelhouse --limit 1
gh run watch <RUN_ID> --repo gengxun-henu/pyisis --exit-status
```

Expected: `gh run watch` exits 0 only when the whole workflow completes successfully. Record `<RUN_ID>`, its `headSha`, start/end times, and each job conclusion in M08 progress.

- [ ] **Step 3: On any failure, capture the earliest failed job and stop**

Run:

```powershell
gh run view <RUN_ID> --repo gengxun-henu/pyisis --json headSha,conclusion,jobs,url
gh run view <RUN_ID> --repo gengxun-henu/pyisis --log-failed > build\windows\reports\m08-failed-workflow.log
```

Expected: a failed workflow has one identified earliest failure layer. Do not rerun, edit code, alter cache keys, or publish; update `findings.md` with the failed job, log path, and proposed diagnostic boundary.

### Task 4: Collect and validate current-HEAD evidence

**Files:**
- Create: `docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json`
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/findings.md`
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/progress.md`
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/task_plan.md`

**Interfaces:**
- Consumes: a successful Task 3 run and its uploaded Linux/Windows wheel artifacts and reports.
- Produces: a schema-1 evidence document with four exact lanes, run/job IDs, package/Python identities, pass/fail/skip counts, hashes, and artifact paths.

- [ ] **Step 1: Download only the required artifacts to a task-scoped directory**

Run:

```powershell
$out = 'build\windows\m08-release-evidence'
New-Item -ItemType Directory -Force -Path $out | Out-Null
gh run download <RUN_ID> --repo gengxun-henu/pyisis --dir $out
```

Expected: the directory contains the Linux ISIS 9/10 wheelhouses and reports plus Windows ISIS 9/10 wheelhouses and `*-dll-dependencies.json` reports. If an expected artifact is absent, mark the lane failed even if its job conclusion was success.

- [ ] **Step 2: Hash every retained evidence file**

Run:

```powershell
Get-ChildItem -LiteralPath 'build\windows\m08-release-evidence' -Recurse -File |
  Get-FileHash -Algorithm SHA256 |
  Sort-Object Path |
  Format-Table -AutoSize
```

Expected: every evidence file receives one SHA-256 value. Copy the complete path/hash mapping into the matrix JSON; do not infer hashes from historical rc2 assets.

- [ ] **Step 3: Write the exact four-lane schema-1 matrix**

Use the following shape, replacing every placeholder with observed values before saving:

```json
{
  "schema_version": 1,
  "subject": "post-m06-dual-version-wheel-revalidation",
  "head_sha": "<40-character-current-head>",
  "workflow": {"path": ".github/workflows/wheels.yml", "run_id": 0, "conclusion": "success"},
  "lanes": {
    "linux-isis9": {"conclusion": "success", "python_abi": "cp312", "artifacts": []},
    "linux-isis10": {"conclusion": "success", "python_abi": "cp313", "artifacts": []},
    "windows-isis9": {"conclusion": "success", "python_abi": "cp312", "artifacts": []},
    "windows-isis10": {"conclusion": "success", "python_abi": "cp313", "artifacts": []}
  }
}
```

Expected: each lane identifies its job, installed ISIS/package identity, build/install/import/focused-test result counts, artifact relative paths, and SHA-256 values. The Windows ISIS 10 lane also names the successful SpiceQL export/link probe and its DLL-dependency report.

- [ ] **Step 4: Verify the matrix against the finished workflow and live Git state**

Run:

```powershell
python -c "import json,pathlib; p=pathlib.Path('docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json'); d=json.loads(p.read_text()); assert d['schema_version']==1; assert set(d['lanes'])=={'linux-isis9','linux-isis10','windows-isis9','windows-isis10'}; assert d['workflow']['conclusion']=='success'; assert all(v['conclusion']=='success' and v['artifacts'] for v in d['lanes'].values())"
git diff --check
git status --short --branch
```

Expected: all four lanes are successful, every lane has retained artifacts, no whitespace error exists, and `print.prt` remains the only unrelated change.

### Task 5: Close the validation milestone without publishing

**Files:**
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/task_plan.md`
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/findings.md`
- Modify: `.planning/post-m06-dual-version-wheel-revalidation-m08/progress.md`
- Modify: `docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json`

**Interfaces:**
- Consumes: the successful, hash-complete Task 4 matrix.
- Produces: a concise release-readiness decision that explicitly withholds release publication.

- [ ] **Step 1: Record completion or the exact blocker**

For success, mark every plan checkbox complete and record the four workflow jobs, total pass/fail/skip counts, exact artifact hashes, and Git state. For failure, leave the plan incomplete with exactly one Next Step naming the first failing layer and its diagnostic command.

- [ ] **Step 2: Run final local structural validation**

Run:

```powershell
git diff --check
git status --short --branch
python "$env:USERPROFILE\.codex\skills\milestone-session-manager\scripts\verify_milestones.py" --repo 'D:\code\pyisis\pyisis\.worktrees\m04-windows-pyisis-wheelhouse'
```

Expected: no whitespace errors; the canonical M06 registry still verifies unchanged; all newly changed paths are M08 evidence/planning only; `print.prt` remains unstaged.

- [ ] **Step 3: Commit evidence and planning records only**

```powershell
git add -- .planning/post-m06-dual-version-wheel-revalidation-m08 `
  docs/superpowers/evidence/2026-08-20-post-m06-wheel-matrix.json
git commit -m 'docs: record post-M06 wheel revalidation'
```

Expected: no release tag, GitHub Release, wheel-upload command, or M06 artifact enters this commit.

## Plan Self-Review

- Spec coverage: Tasks 1–2 freeze the exact source, Task 3 runs the established matrix and stops at first failure, Task 4 records fresh four-lane hashes, and Task 5 records a non-publishing readiness conclusion.
- Placeholder scan: the only angle-bracket values are explicitly runtime-observed evidence fields in a JSON schema template; no task asks an executor to guess a code change.
- Interface consistency: every task consumes the preceding task's SHA or run ID; the four canonical lane names remain `linux-isis9`, `linux-isis10`, `windows-isis9`, and `windows-isis10` throughout.
