"""Unit tests for the auditwheel manylinux policy gate.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun added auditwheel report policy validation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "validate_auditwheel_policy.py"


class AuditwheelPolicyUnitTest(unittest.TestCase):
    """Test auditwheel policy parsing and target enforcement."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("auditwheel_policy", POLICY_SCRIPT)
        assert spec is not None
        assert spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def _report(self, root: Path, policy: str) -> Path:
        report = root / f"{policy}.txt"
        report.write_text(
            f'wheel.whl is consistent with the following platform tag: "{policy}".\n',
            encoding="utf-8",
        )
        return report

    def test_accepts_target_and_older_manylinux_policies(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for policy in ("manylinux_2_28_x86_64", "manylinux_2_17_x86_64"):
                with self.subTest(policy=policy):
                    self.assertEqual(
                        self.module.validate_report(
                            self._report(root, policy),
                            (2, 28),
                            "x86_64",
                        ),
                        policy,
                    )

    def test_accepts_legacy_manylinux_alias(self):
        with TemporaryDirectory() as temp_dir:
            report = self._report(Path(temp_dir), "manylinux2014_x86_64")
            self.assertEqual(
                self.module.validate_report(report, (2, 28), "x86_64"),
                "manylinux2014_x86_64",
            )

    def test_rejects_linux_and_newer_manylinux_policies(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for policy in ("linux_x86_64", "manylinux_2_34_x86_64"):
                with self.subTest(policy=policy), self.assertRaises(ValueError):
                    self.module.validate_report(
                        self._report(root, policy),
                        (2, 28),
                        "x86_64",
                    )

    def test_rejects_missing_policy_result(self):
        with TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.txt"
            report.write_text("no platform result\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing auditwheel policy"):
                self.module.validate_report(report, (2, 28), "x86_64")


if __name__ == "__main__":
    unittest.main()
