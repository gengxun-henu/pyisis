"""Unit tests for pyisis pip runtime discovery.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added runtime package discovery coverage for pip wheels.
Updated: 2026-06-18  Geng Xun kept packaged runtime discovery behind explicit envs.
"""

from __future__ import annotations

import os
import importlib
from pathlib import Path
import sys
from types import ModuleType
from unittest import mock
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PYTHON_DIR = PROJECT_ROOT / "python"
source_python_dir_text = str(SOURCE_PYTHON_DIR)
if source_python_dir_text not in sys.path:
    sys.path.insert(0, source_python_dir_text)


class PyisisRuntimeUnitTest(unittest.TestCase):
    """Test suite for packaged runtime discovery. Added: 2026-06-18."""

    def setUp(self):
        if source_python_dir_text in sys.path:
            sys.path.remove(source_python_dir_text)
        sys.path.insert(0, source_python_dir_text)
        sys.modules.pop("pyisis", None)
        sys.modules.pop("pyisis._runtime", None)
        sys.modules.pop("isis_pybind", None)

    def tearDown(self):
        sys.modules.pop("pyisis", None)
        sys.modules.pop("pyisis._runtime", None)
        sys.modules.pop("isis_pybind", None)
        sys.modules.pop("pyisis_runtime", None)
        sys.modules.pop("pyisis_isisdata_minimal", None)

    def test_configure_runtime_prefers_existing_environment(self):
        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {"ISIS_PREFIX": r"C:\external\isis"}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        self.assertEqual(config.isis_prefix, r"C:\external\isis")
        self.assertEqual(config.isisroot, r"C:\external\isis")

    def test_configure_runtime_ignores_packaged_runtime_when_environment_exists(self):
        fake_runtime = ModuleType("pyisis_runtime")
        fake_runtime.prefix = mock.Mock(return_value=r"C:\packaged\isis")
        fake_runtime.dll_directories = mock.Mock(return_value=[r"C:\packaged\isis\bin"])
        sys.modules["pyisis_runtime"] = fake_runtime

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {"ISIS_PREFIX": r"C:\external\isis"}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        fake_runtime.prefix.assert_not_called()
        fake_runtime.dll_directories.assert_not_called()
        self.assertEqual(config.isis_prefix, r"C:\external\isis")
        self.assertEqual(config.dll_directories, ())

    def test_configure_runtime_ignores_minimal_data_package_when_isisdata_exists(self):
        fake_data = ModuleType("pyisis_isisdata_minimal")
        fake_data.data_path = mock.Mock(side_effect=RuntimeError("broken optional data"))
        sys.modules["pyisis_isisdata_minimal"] = fake_data

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {"ISISDATA": r"C:\external\isisdata"}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        fake_data.data_path.assert_not_called()
        self.assertEqual(config.isisdata, r"C:\external\isisdata")

    def test_configure_runtime_uses_packaged_runtime_when_environment_is_missing(self):
        fake_runtime = ModuleType("pyisis_runtime")
        fake_runtime.prefix = lambda: r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis"
        fake_runtime.dll_directories = lambda: [
            r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis\bin",
        ]
        sys.modules["pyisis_runtime"] = fake_runtime

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {}, clear=True):
            config = configure_runtime(register_dll_directories=False)
            self.assertEqual(os.environ["ISIS_PREFIX"], fake_runtime.prefix())
            self.assertEqual(os.environ["ISISROOT"], fake_runtime.prefix())
        self.assertEqual(config.isis_prefix, fake_runtime.prefix())
        self.assertEqual(
            config.dll_directories,
            (r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis\bin",),
        )

    def test_register_windows_dll_directories_normalizes_duplicate_paths(self):
        from pyisis import _runtime

        added_paths = []

        def fake_add_dll_directory(path):
            added_paths.append(path)
            return object()

        with mock.patch.object(_runtime.os, "name", "nt"), mock.patch.object(
            _runtime.os,
            "add_dll_directory",
            side_effect=fake_add_dll_directory,
            create=True,
        ):
            _runtime._REGISTERED_DLL_DIRECTORIES.clear()
            _runtime._DLL_DIRECTORY_HANDLES.clear()
            _runtime._register_windows_dll_directories(
                [
                    r"C:\ISIS\bin",
                    r"C:\ISIS\bin\\",
                    r"C:/ISIS/bin",
                ]
            )

        self.assertEqual(added_paths, [r"C:\ISIS\bin"])

    def test_isis_pybind_import_ignores_runtime_discovery_failure(self):
        fake_pyisis = ModuleType("pyisis")
        fake_pyisis.__path__ = []
        fake_runtime = ModuleType("pyisis._runtime")
        fake_runtime.configure_runtime = mock.Mock(side_effect=RuntimeError("broken runtime"))
        sys.modules["pyisis"] = fake_pyisis
        sys.modules["pyisis._runtime"] = fake_runtime

        with self.assertRaises(ModuleNotFoundError) as context:
            importlib.import_module("isis_pybind")

        fake_runtime.configure_runtime.assert_called_once()
        self.assertEqual(context.exception.name, "isis_pybind._isis_core")

    def test_configure_runtime_uses_minimal_data_package_when_isisdata_is_missing(self):
        fake_data = ModuleType("pyisis_isisdata_minimal")
        fake_data.data_path = lambda: Path(r"C:\venv\Lib\site-packages\pyisis_isisdata_minimal\data")
        sys.modules["pyisis_isisdata_minimal"] = fake_data

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {}, clear=True):
            config = configure_runtime(register_dll_directories=False)
            self.assertEqual(os.environ["ISISDATA"], str(fake_data.data_path()))
        self.assertEqual(config.isisdata, str(fake_data.data_path()))


if __name__ == "__main__":
    unittest.main()
