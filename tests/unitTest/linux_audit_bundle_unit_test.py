"""Unit tests for the combined, repairable Linux wheel.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun added cross-wheel audit bundle coverage.
Updated: 2026-07-23  Geng Xun covered removal of versioned ISIS runtime dependencies.
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
    """Test the payload and metadata union used before auditwheel repair."""

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
                    "usgs_pyisis-1.2.0.dist-info/METADATA": (
                        b"Metadata-Version: 2.4\n"
                        b"Name: usgs-pyisis\n"
                        b"Requires-Dist: usgs-pyisis-runtime-linux-x86_64==1.2.0; "
                        b'platform_system == "Linux"\n'
                        b"Requires-Dist: usgs-pyisis-isisdata-minimal==1.2.0\n"
                    ),
                    "usgs_pyisis-1.2.0.dist-info/RECORD": b"stale record",
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
                metadata = archive.read(
                    "usgs_pyisis-1.2.0.dist-info/METADATA"
                ).decode("utf-8")
                record = archive.read(
                    "usgs_pyisis-1.2.0.dist-info/RECORD"
                ).decode("utf-8")
            self.assertIn("isis_pybind/_isis_core.so", names)
            self.assertIn("pyisis_runtime/vendor/isis/lib/libisis.so", names)
            self.assertIn("usgs_pyisis-1.2.0.dist-info/WHEEL", names)
            self.assertNotIn("runtime-1.2.0.dist-info/WHEEL", names)
            self.assertNotIn("runtime-linux-x86_64", metadata)
            self.assertIn("usgs-pyisis-isisdata-minimal", metadata)
            self.assertIn("pyisis_runtime/vendor/isis/lib/libisis.so", record)

    def test_bundle_rejects_payload_collisions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extension = self._wheel(
                root / "extension.whl",
                {
                    "same": b"one",
                    "main.dist-info/RECORD": b"record",
                },
            )
            runtime = self._wheel(root / "runtime.whl", {"same": b"two"})
            with self.assertRaisesRegex(ValueError, "payload collision"):
                self.module.build_audit_bundle(
                    extension,
                    runtime,
                    root / "combined.whl",
                )

    def test_bundle_removes_selected_isis10_runtime_dependency(self):
        metadata = (
            b"Metadata-Version: 2.4\n"
            b"Requires-Dist: usgs-pyisis-runtime-isis10-linux-x86_64==1.4.0rc1\n"
            b"Requires-Dist: usgs-pyisis-isisdata-minimal==1.3.0rc1\n"
        )

        filtered = self.module._metadata_without_runtime_dependency(
            metadata,
            "usgs-pyisis-runtime-isis10-linux-x86_64",
        ).decode("utf-8")

        self.assertNotIn("runtime-isis10-linux", filtered)
        self.assertIn("isisdata-minimal", filtered)


if __name__ == "__main__":
    unittest.main()
