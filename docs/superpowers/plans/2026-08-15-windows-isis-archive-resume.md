# Windows ISIS Archive Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent `fetch_isis.ps1` from treating a partial archive as resumable when its server does not support byte ranges.

**Architecture:** Keep the Git path and archive extraction unchanged. Add an archive-resume capability check before constructing curl arguments for an existing archive; use `--continue-at -` only after a `206` result. Otherwise preserve the archive and issue a clear failure that directs an explicit `-Force` retry.

**Tech Stack:** Windows PowerShell 7, curl.exe, Python `unittest`.

## Global Constraints

- Use conda-only project dependencies; do not add pip/npm workflows.
- Preserve existing partial archives unless the caller explicitly passes `-Force`.
- Do not change `.gitignore`, `print.prt`, Git sparse checkout, tar validation, source layout, or ISIS pinning.
- Tests run the actual PowerShell script with a controlled curl boundary and no external network.

---

### Task 1: Add a failing archive-resume regression test

**Files:**
- Create: `tests/unitTest/windows_isis_fetch_script_unit_test.py`
- Test: `tests/unitTest/windows_isis_fetch_script_unit_test.py`

**Interfaces:**
- Consumes: `fetch_isis.ps1` archive mode, `-SourceDir`, `-Method`, `-Ref`, and `-Force`.
- Produces: a regression test proving an existing partial archive is preserved when a controlled curl range probe returns HTTP 200.

- [x] **Step 1: Write the failing test**

```python
def test_archive_mode_preserves_partial_file_when_range_resume_is_unsupported(self):
    completed = self.run_fetch_with_fake_curl(
        existing_archive=b"partial", range_probe_status=200
    )
    self.assertNotEqual(completed.returncode, 0)
    self.assertIn("does not support byte-range resume", completed.stderr)
    self.assertEqual(self.archive_path.read_bytes(), b"partial")
```

- [x] **Step 2: Run the test and observe the expected failure**

Run: `D:\pyisis-win-env\python.exe -m unittest tests.unitTest.windows_isis_fetch_script_unit_test.WindowsIsisFetchScriptUnitTest.test_archive_mode_preserves_partial_file_when_range_resume_is_unsupported -v`

Expected: FAIL because the current script unconditionally supplies `--continue-at -`.

- [x] **Step 3: Add the controlled curl boundary**

```python
def run_fetch_with_fake_curl(self, existing_archive: bytes, range_probe_status: int):
    with tempfile.TemporaryDirectory() as temporary_root:
        root = Path(temporary_root)
        source_dir = root / "source"
        external_dir = source_dir.parent
        archive_path = external_dir / "ISIS3-9.0.0.tar.gz"
        archive_path.write_bytes(existing_archive)
        driver = root / "driver.ps1"
        driver.write_text(
            self.render_fake_curl_driver(
                source_dir, range_probe_status, self.fetch_script
            ),
            encoding="utf-8",
        )
        return subprocess.run(
            [self.powershell, "-NoProfile", "-File", str(driver)],
            text=True, capture_output=True, check=False,
        )
```

- [x] **Step 4: Re-run until the failure is the missing HTTP-200 guard**

Run: same command as Step 2.

Expected: FAIL assertion that the script did not reject an unsupported resume.

### Task 2: Gate archive resume on byte-range capability

**Files:**
- Modify: `ports/windows/isis/fetch_isis.ps1`
- Modify: `tests/unitTest/windows_isis_fetch_script_unit_test.py`

**Interfaces:**
- Consumes: `$archiveUrl`, `$archivePath`, curl.exe, and existing archive length.
- Produces: `Test-ArchiveResumeSupport`, true only when the curl range probe reports `206`; archive mode calls `--continue-at -` only then.

- [x] **Step 1: Write the minimal implementation**

```powershell
function Test-ArchiveResumeSupport {
    param([Parameter(Mandatory = $true)][string]$ArchiveUrl)
    # Request one byte and return true only for final HTTP 206.
}

if ((Test-Path $archivePath) -and -not (Test-ArchiveResumeSupport $archiveUrl)) {
    Fail "archive server does not support byte-range resume for $archivePath; preserve it for diagnosis or pass -Force for a clean retry"
}
```

- [x] **Step 2: Run the unsupported-range regression test**

Run: command from Task 1 Step 2.

Expected: PASS; no archive overwrite and an explicit unsupported-range error.

- [x] **Step 3: Add and run the range-capable passing case**

```python
def test_archive_mode_uses_continue_at_only_after_206_range_probe(self):
    completed = self.run_fetch_with_fake_curl(
        existing_archive=b"partial", range_probe_status=206
    )
    self.assertEqual(completed.returncode, 0)
    self.assertIn("--continue-at", self.fake_curl_download_arguments)
```

Run: `D:\pyisis-win-env\python.exe -m unittest tests.unitTest.windows_isis_fetch_script_unit_test -v`

Expected: PASS without external network.

- [x] **Step 4: Commit only the task files**

```powershell
git add -- ports/windows/isis/fetch_isis.ps1 tests/unitTest/windows_isis_fetch_script_unit_test.py docs/superpowers/plans/2026-08-15-windows-isis-archive-resume.md
git commit -m "fix: guard Windows ISIS archive resume"
```

## Plan Self-Review

- Spec coverage: Tasks exercise both unsupported HTTP 200 and resumable HTTP 206 outcomes.
- Placeholder scan: no deferred behavior or unbounded implementation step remains.
- Interface consistency: `Test-ArchiveResumeSupport` is the sole production helper used by archive mode.
