"""Unit tests for private Linux C++ toolchain runtime packaging.

Author: Geng Xun
Created: 2026-07-24
Last Modified: 2026-07-24
Updated: 2026-07-24  Geng Xun added ELF dependency redirection coverage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN_SCRIPT = (
    PROJECT_ROOT / "tools" / "packaging" / "vendor_linux_toolchain_runtime.py"
)


class LinuxToolchainRuntimeUnitTest(unittest.TestCase):
    """Test private libstdc++ and libgcc_s wheel dependency rewriting."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "vendor_linux_toolchain_runtime",
            TOOLCHAIN_SCRIPT,
        )
        assert spec is not None
        assert spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_patch_toolchain_dependencies_renames_and_redirects_elf_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library_dir = root / self.module.RUNTIME_LIBRARY_DIR
            library_dir.mkdir(parents=True)
            for name in self.module.TOOLCHAIN_RENAMES:
                (library_dir / name).write_bytes(b"\x7fELFtoolchain")
            extension = root / "isis_pybind" / "_isis_core.so"
            extension.parent.mkdir()
            extension.write_bytes(b"\x7fELFextension")

            print_calls = 0

            def completed(arguments, **kwargs):
                nonlocal print_calls
                stdout = ""
                if "--print-needed" in arguments:
                    print_calls += 1
                    if print_calls <= 3:
                        stdout = "libstdc++.so.6\nlibgcc_s.so.1\n"
                    else:
                        stdout = (
                            "libpyisis_stdc++.so.6\nlibpyisis_gcc_s.so.1\n"
                        )
                return subprocess.CompletedProcess(arguments, 0, stdout=stdout)

            with mock.patch.object(
                self.module.subprocess,
                "run",
                side_effect=completed,
            ) as run:
                replacements = self.module.patch_toolchain_dependencies(root)

            self.assertEqual(replacements, 6)
            for original, private in self.module.TOOLCHAIN_RENAMES.items():
                self.assertFalse((library_dir / original).exists())
                self.assertTrue((library_dir / private).is_file())
            commands = [call.args[0] for call in run.call_args_list]
            self.assertTrue(any("--set-soname" in command for command in commands))
            self.assertTrue(
                any("--replace-needed" in command for command in commands)
            )

    def test_verify_toolchain_dependencies_rejects_system_links(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library_dir = root / self.module.RUNTIME_LIBRARY_DIR
            library_dir.mkdir(parents=True)
            for private in self.module.TOOLCHAIN_RENAMES.values():
                (library_dir / private).write_bytes(b"\x7fELFtoolchain")
            extension = root / "isis_pybind" / "_isis_core.so"
            extension.parent.mkdir()
            extension.write_bytes(b"\x7fELFextension")

            def completed(arguments, **kwargs):
                stdout = ""
                if "--print-needed" in arguments:
                    stdout = "libstdc++.so.6\nlibpyisis_gcc_s.so.1\n"
                return subprocess.CompletedProcess(arguments, 0, stdout=stdout)

            with mock.patch.object(
                self.module.subprocess,
                "run",
                side_effect=completed,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "System toolchain dependencies remain",
                ):
                    self.module.verify_toolchain_dependencies(root)


if __name__ == "__main__":
    unittest.main()
