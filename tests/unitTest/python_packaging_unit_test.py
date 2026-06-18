"""
Unit tests for Python packaging metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
"""

import tomllib
import unittest
from pathlib import Path


class PythonPackagingMetadataTest(unittest.TestCase):
    """Test suite for pyproject packaging metadata. Added: 2026-06-18."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.pyproject_path = cls.repo_root / "pyproject.toml"

    def load_pyproject(self):
        self.assertTrue(
            self.pyproject_path.exists(),
            "pyproject.toml should exist at the repository root",
        )
        return tomllib.loads(self.pyproject_path.read_text(encoding="utf-8"))

    def test_build_system_uses_scikit_build_core_backend(self):
        pyproject = self.load_pyproject()

        build_system = pyproject["build-system"]
        self.assertEqual("scikit_build_core.build", build_system["build-backend"])

    def test_build_requirements_include_packaging_build_tools(self):
        pyproject = self.load_pyproject()

        requirements = pyproject["build-system"]["requires"]
        self.assertTrue(
            any(requirement.startswith("scikit-build-core") for requirement in requirements)
        )
        self.assertTrue(any(requirement.startswith("pybind11") for requirement in requirements))

    def test_project_identity_and_python_metadata(self):
        pyproject = self.load_pyproject()

        project = pyproject["project"]
        self.assertEqual("pyisis", project["name"])
        self.assertEqual("1.2.0", project["version"])
        self.assertIn("README.md", project["readme"])
        self.assertIn(">=3.10", project["requires-python"])

    def test_project_dependencies_include_runtime_packages(self):
        pyproject = self.load_pyproject()

        dependencies = pyproject["project"]["dependencies"]
        self.assertIn(
            'pyisis-runtime-win64==1.2.0; platform_system == "Windows" and platform_machine == "AMD64"',
            dependencies,
        )
        self.assertIn("pyisis-isisdata-minimal==1.2.0", dependencies)

    def test_scikit_build_wheel_metadata(self):
        pyproject = self.load_pyproject()

        scikit_build = pyproject["tool"]["scikit-build"]
        self.assertEqual("build-system.requires", scikit_build["minimum-version"])
        self.assertEqual([], scikit_build["wheel"]["packages"])
        self.assertTrue(scikit_build["wheel"]["platlib"])


if __name__ == "__main__":
    unittest.main()
