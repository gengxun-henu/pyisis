"""Unit tests for the Windows ISIS source-fetch script.

Author: Geng Xun
Created: 2026-08-15
Last Modified: 2026-08-15
Updated: 2026-08-15  Geng Xun added archive resume capability regression coverage.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FETCH_SCRIPT = PROJECT_ROOT / "ports" / "windows" / "isis" / "fetch_isis.ps1"


class WindowsIsisFetchScriptUnitTest(unittest.TestCase):
    """Regression coverage for archive download recovery. Added: 2026-08-15."""

    @classmethod
    def setUpClass(cls):
        cls.powershell = shutil.which("pwsh") or shutil.which("powershell")
        if cls.powershell is None:
            raise unittest.SkipTest("PowerShell is unavailable.")

    def run_fetch(
        self, archive_bytes: bytes, range_status: int, range_exit_code: int = 0
    ):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            source_dir = root / "source"
            archive_path = root / "ISIS3-9.0.0.tar.gz"
            archive_path.write_bytes(archive_bytes)
            driver_path = root / "run_fetch.ps1"
            download_arguments_path = root / "download_arguments.txt"
            driver_path.write_text(
                f"""$ErrorActionPreference = \"Stop\"
function curl.exe {{
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CurlArgs)
    if ($CurlArgs -contains \"--range\") {{
        if ($env:PYISIS_TEST_RANGE_EXIT_CODE -ne \"0\") {{
            $global:LASTEXITCODE = [int]$env:PYISIS_TEST_RANGE_EXIT_CODE
            return
        }}
        Write-Output $env:PYISIS_TEST_RANGE_STATUS
        $global:LASTEXITCODE = 0
        return
    }}
    Set-Content -LiteralPath $env:PYISIS_TEST_DOWNLOAD_ARGUMENTS -Value $CurlArgs
    $global:LASTEXITCODE = 0
}}
& '{FETCH_SCRIPT.as_posix()}' -SourceDir '{source_dir.as_posix()}' -Method archive -Ref 9.0.0 -DownloadRetries 0
""",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PSExecutionPolicyPreference"] = "Bypass"
            environment["PYISIS_TEST_RANGE_STATUS"] = str(range_status)
            environment["PYISIS_TEST_RANGE_EXIT_CODE"] = str(range_exit_code)
            environment["PYISIS_TEST_DOWNLOAD_ARGUMENTS"] = str(download_arguments_path)
            completed = subprocess.run(
                [
                    self.powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(driver_path),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            download_arguments = (
                download_arguments_path.read_text(encoding="utf-8")
                if download_arguments_path.exists()
                else ""
            )
            return completed, archive_path.read_bytes(), source_dir.exists(), download_arguments

    @staticmethod
    def valid_archive_bytes() -> bytes:
        contents = BytesIO()
        with tarfile.open(fileobj=contents, mode="w:gz") as archive:
            entry = tarfile.TarInfo("ISIS3-9.0.0/README")
            payload = b"fixture\n"
            entry.size = len(payload)
            archive.addfile(entry, BytesIO(payload))
        return contents.getvalue()

    def test_archive_mode_preserves_partial_file_when_range_resume_is_unsupported(self):
        """HTTP 200 range probes must fail before a partial archive is overwritten."""
        completed, archive_bytes, source_exists, download_arguments = self.run_fetch(
            b"partial", 200
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not support byte-range resume", completed.stderr)
        self.assertEqual(archive_bytes, b"partial")
        self.assertFalse(source_exists)
        self.assertEqual(download_arguments, "")

    def test_archive_mode_extracts_valid_archive_when_range_resume_is_supported(self):
        """HTTP 206 range probes must preserve the normal archive extraction path."""
        completed, _, source_exists, download_arguments = self.run_fetch(
            self.valid_archive_bytes(), 206
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(source_exists)
        self.assertIn("--continue-at", download_arguments)

    def test_archive_mode_preserves_partial_file_when_range_probe_fails(self):
        """A failed range probe must not start a resume download."""
        completed, archive_bytes, source_exists, download_arguments = self.run_fetch(
            b"partial", 0, range_exit_code=56
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not support byte-range resume", completed.stderr)
        self.assertIn("-Force", completed.stderr)
        self.assertEqual(archive_bytes, b"partial")
        self.assertFalse(source_exists)
        self.assertEqual(download_arguments, "")


if __name__ == "__main__":
    unittest.main()
