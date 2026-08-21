"""Unit tests for Linux wheelhouse ABI evidence.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-08-21
Updated: 2026-07-23  Geng Xun added streaming GLIBC policy audit coverage.
Updated: 2026-07-24  Geng Xun added versioned ISIS distribution wheel selection.
Updated: 2026-07-25  Geng Xun aligned wheel selection fixtures with the ISIS 10 rc2 identity.
Updated: 2026-08-21  Geng Xun aligned wheel selection fixtures with the ISIS 10 rc3 identity.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "audit_linux_wheelhouse.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_linux_wheelhouse", AUDIT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {AUDIT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _write_wheel(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


class LinuxWheelAuditUnitTest(unittest.TestCase):
    """Test streaming Linux wheel ABI evidence. Added: 2026-07-23."""

    @classmethod
    def setUpClass(cls):
        cls.audit = _load_audit_module()

    def _wheelhouse(self, root: Path, platform_tag: str = "linux_x86_64") -> Path:
        wheelhouse = root / "wheelhouse"
        wheelhouse.mkdir()
        runtime_payload = b"\x7fELF\x00GLIBC_2.17\x00"
        _write_wheel(
            wheelhouse / f"usgs_pyisis-1.2.0-cp312-cp312-{platform_tag}.whl",
            {
                "isis_pybind/_isis_core.so": b"\x7fELF\x00GLIBC_2.34\x00",
                "pyisis_runtime/vendor/isis/lib/libisis.so": runtime_payload,
                "pyisis_runtime/vendor/isis/lib/libisis.so.9": runtime_payload,
                "pyisis_runtime/vendor/isis/IsisPreferences": b"preferences",
            },
        )
        return wheelhouse

    def test_report_records_maximum_glibc_without_expanding_duplicate_payloads(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse = self._wheelhouse(Path(temp_dir))
            report = self.audit.audit_wheelhouse(wheelhouse, (2, 28))

        self.assertFalse(report["target_met"])
        self.assertEqual(report["maximum_glibc"], "2.34")
        wheel = report["wheels"][0]
        self.assertEqual(wheel["elf_payloads"], 2)
        self.assertEqual(wheel["unique_native_payloads"], 2)

    def test_manylinux_claim_is_rejected_when_target_is_not_met(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse = self._wheelhouse(Path(temp_dir), "manylinux_2_28_x86_64")
            with self.assertRaisesRegex(RuntimeError, "claims manylinux"):
                self.audit.audit_wheelhouse(wheelhouse, (2, 28))

    def test_require_target_rejects_prototype_above_target(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse = self._wheelhouse(Path(temp_dir))
            with self.assertRaisesRegex(RuntimeError, "above target 2.28"):
                self.audit.audit_wheelhouse(
                    wheelhouse,
                    (2, 28),
                    require_target=True,
                )

    def test_report_is_json_serializable(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse = self._wheelhouse(Path(temp_dir))
            report = self.audit.audit_wheelhouse(wheelhouse, (2, 39))

        encoded = json.dumps(report)
        self.assertTrue(report["target_met"])
        self.assertIn("necessary but not sufficient", encoded)

    def test_versioned_isis_wheel_pattern_selects_isis10_distribution(self):
        with TemporaryDirectory() as temp_dir:
            wheelhouse = Path(temp_dir) / "wheelhouse"
            wheelhouse.mkdir()
            _write_wheel(
                wheelhouse
                / "usgs_pyisis_isis10-1.4.0rc3-cp313-cp313-manylinux_2_35_x86_64.whl",
                {"isis_pybind/_isis_core.so": b"\x7fELF\x00GLIBC_2.34\x00"},
            )

            report = self.audit.audit_wheelhouse(
                wheelhouse,
                (2, 35),
                require_target=True,
                wheel_pattern="usgs_pyisis_isis10-*.whl",
            )

        self.assertTrue(report["target_met"])
        self.assertEqual(report["maximum_glibc"], "2.34")


if __name__ == "__main__":
    unittest.main()
