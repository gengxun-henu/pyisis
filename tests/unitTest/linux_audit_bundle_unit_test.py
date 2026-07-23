"""Unit tests for the temporary combined Linux audit archive.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun added cross-wheel audit bundle coverage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "build_linux_audit_bundle.py"


class LinuxAuditBundleUnitTest(unittest.TestCase):
    """Test payload union semantics used only for auditwheel inspection."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("linux_audit_bundle", BUNDLE_SCRIPT)
        assert spec is not None
        assert spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def _wheel(self, path: Path, members: dict[str, bytes]) -> Path:
        with zipfile.ZipFile(path, "w") as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        return path

    def test_bundle_keeps_extension_metadata_and_runtime_payload(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extension = self._wheel(
                root / "extension.whl",
                {
                    "isis_pybind/_isis_core.so": b"extension",
                    "usgs_pyisis-1.2.0.dist-info/WHEEL": b"extension metadata",
                },
            )
            runtime = self._wheel(
                root / "runtime.whl",
                {
                    "pyisis_runtime/vendor/isis/lib/libisis.so": b"runtime",
                    "runtime-1.2.0.dist-info/WHEEL": b"runtime metadata",
                },
            )

            output = self.module.build_audit_bundle(
                extension,
                runtime,
                root / "audit" / "combined.whl",
            )
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            self.assertIn("isis_pybind/_isis_core.so", names)
            self.assertIn("pyisis_runtime/vendor/isis/lib/libisis.so", names)
            self.assertIn("usgs_pyisis-1.2.0.dist-info/WHEEL", names)
            self.assertNotIn("runtime-1.2.0.dist-info/WHEEL", names)

    def test_bundle_rejects_payload_collisions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extension = self._wheel(root / "extension.whl", {"same": b"one"})
            runtime = self._wheel(root / "runtime.whl", {"same": b"two"})
            with self.assertRaisesRegex(ValueError, "payload collision"):
                self.module.build_audit_bundle(
                    extension,
                    runtime,
                    root / "combined.whl",
                )


if __name__ == "__main__":
    unittest.main()
