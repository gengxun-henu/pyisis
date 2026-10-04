"""Unit tests for the pyisis native application launcher.

Author: Geng Xun
Created: 2026-10-03
Last Modified: 2026-10-03
Purpose: Verify safe argument passing, environment propagation, and failure reporting.
Updated: 2026-10-03  Geng Xun added non-raising check=False coverage for native application failures.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest

import pyisis


class PyisisAppsUnitTest(unittest.TestCase):
    def make_executable(self, directory: str) -> Path:
        path = Path(directory) / "fake-isis-app.py"
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "print(os.environ.get('ISISDATA', 'missing'))\n"
            "print(repr(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_run_preserves_argument_boundaries_and_environment(self):
        with TemporaryDirectory() as temp_dir:
            executable = self.make_executable(temp_dir)
            result = pyisis.apps.run(
                str(executable),
                "--input",
                "file with spaces.cub",
                env={"ISISDATA": "/tmp/test-isisdata"},
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("/tmp/test-isisdata", result.stdout)
        self.assertIn("file with spaces.cub", result.stdout)

    def test_run_raises_pyisis_error_with_stderr_on_failure(self):
        with TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "failing-isis-app.py"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('bad input', file=sys.stderr)\n"
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

            with self.assertRaisesRegex(pyisis.PyisisError, r"exit code 7.*bad input"):
                pyisis.apps.run(str(executable), capture_output=True)

    def test_run_returns_failed_process_when_check_is_disabled(self):
        with TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "failing-isis-app.py"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "raise SystemExit(9)\n",
                encoding="utf-8",
            )
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

            result = pyisis.apps.run(str(executable), check=False)

        self.assertEqual(result.returncode, 9)


if __name__ == "__main__":
    unittest.main()
