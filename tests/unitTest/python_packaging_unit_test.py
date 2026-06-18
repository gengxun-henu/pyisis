"""
Unit tests for Python packaging metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added CMake wheel staging coverage for scikit-build-core.
Updated: 2026-06-18  Geng Xun added packaging license metadata coverage for wheel builds.
Updated: 2026-06-18  Geng Xun raised scikit-build-core coverage for PEP 639 license metadata.
Updated: 2026-06-18  Geng Xun added CMake install coverage for the pyisis runtime helper.
Updated: 2026-06-18  Geng Xun prevented cached scikit-build wheel install paths.
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

    def test_build_requirements_pin_scikit_build_core_with_license_metadata_support(self):
        pyproject = self.load_pyproject()

        requirements = pyproject["build-system"]["requires"]
        self.assertIn("scikit-build-core>=0.11", requirements)

    def test_project_identity_and_python_metadata(self):
        pyproject = self.load_pyproject()

        project = pyproject["project"]
        self.assertEqual("pyisis", project["name"])
        self.assertEqual("1.2.0", project["version"])
        self.assertIn("README.md", project["readme"])
        self.assertIn(">=3.10", project["requires-python"])

    def test_project_license_metadata_avoids_deprecated_license_classifier(self):
        pyproject = self.load_pyproject()

        project = pyproject["project"]
        self.assertEqual("MIT", project["license"])
        self.assertFalse(
            any(classifier.startswith("License ::") for classifier in project["classifiers"])
        )

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

    def test_cmake_uses_development_module_for_extension_builds(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn(
            "find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)",
            cmake_lists,
        )
        self.assertNotIn(
            "find_package(Python3 REQUIRED COMPONENTS Interpreter Development)",
            cmake_lists,
        )

    def test_cmake_honors_scikit_build_wheel_staging_paths(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("if(SKBUILD)", cmake_lists)
        self.assertIn('set(PYISIS_INSTALL_SITELIB ".")', cmake_lists)
        self.assertIn('set(PYISIS_INSTALL_SITEARCH ".")', cmake_lists)
        self.assertIn(
            'set(PYISIS_INSTALL_SITELIB "${PYISIS_DEFAULT_SITELIB}" CACHE PATH',
            cmake_lists,
        )
        self.assertIn(
            'set(PYISIS_INSTALL_SITEARCH "${PYISIS_DEFAULT_SITEARCH}" CACHE PATH',
            cmake_lists,
        )

    def test_cmake_installs_pyisis_runtime_helper(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("PYISIS_FACADE_SOURCE_RUNTIME_FILE", cmake_lists)
        self.assertIn("PYISIS_FACADE_BUILD_RUNTIME_FILE", cmake_lists)
        self.assertIn("_runtime.py", cmake_lists)


if __name__ == "__main__":
    unittest.main()
