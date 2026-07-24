"""
Unit tests for Python packaging metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-07-25
Updated: 2026-06-18  Geng Xun added CMake wheel staging coverage for scikit-build-core.
Updated: 2026-06-18  Geng Xun added packaging license metadata coverage for wheel builds.
Updated: 2026-06-18  Geng Xun raised scikit-build-core coverage for PEP 639 license metadata.
Updated: 2026-06-18  Geng Xun added CMake install coverage for the pyisis runtime helper.
Updated: 2026-06-18  Geng Xun prevented cached scikit-build wheel install paths.
Updated: 2026-06-18  Geng Xun added minimal ISISDATA package coverage.
Updated: 2026-06-18  Geng Xun added Windows runtime package metadata coverage.
Updated: 2026-06-19  Geng Xun renamed public wheel distributions to the usgs-pyisis namespace.
Updated: 2026-06-19  Geng Xun added Linux runtime package metadata coverage.
Updated: 2026-07-22  Geng Xun covered relocatable Linux wheel RPATH configuration.
Updated: 2026-07-23  Geng Xun aligned package metadata with the ISIS 9.0.0 release manifest.
Updated: 2026-07-23  Geng Xun covered Qt discovery from the separate Windows dependency prefix.
Updated: 2026-07-23  Geng Xun covered Qt6 Core5Compat linkage for the developer benchmark.
Updated: 2026-07-23  Geng Xun covered the separate ISIS 10 binding distribution manifest.
Updated: 2026-07-23  Geng Xun required full prerelease versions in generated build metadata.
Updated: 2026-07-23  Geng Xun required ISIS 10 Bullet float64 ABI selection.
Updated: 2026-07-23  Geng Xun covered separate ISIS 9 and ISIS 10 release manifests.
Updated: 2026-07-25  Geng Xun covered Windows PCL and Eigen alignment compatibility.
"""

import importlib
import sys
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
        self.assertEqual("usgs-pyisis", project["name"])
        self.assertEqual("1.3.0rc1", project["version"])
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
            'usgs-pyisis-runtime-win64==1.3.0rc1; platform_system == "Windows" and platform_machine == "AMD64"',
            dependencies,
        )
        self.assertIn(
            'usgs-pyisis-runtime-linux-x86_64==1.3.0rc1; platform_system == "Linux" and platform_machine == "x86_64"',
            dependencies,
        )
        self.assertIn("usgs-pyisis-isisdata-minimal==1.3.0rc1", dependencies)

    def test_isis10_distribution_uses_shared_cmake_source_and_cp313(self):
        manifest_path = (
            self.repo_root / "packaging" / "bindings-isis10" / "pyproject.toml"
        )
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual("usgs-pyisis-isis10", manifest["project"]["name"])
        self.assertEqual("1.4.0rc1", manifest["project"]["version"])
        self.assertEqual(">=3.13", manifest["project"]["requires-python"])
        self.assertEqual(
            "../..",
            manifest["tool"]["scikit-build"]["cmake"]["source-dir"],
        )
        self.assertIn(
            'usgs-pyisis-runtime-isis10-linux-x86_64==1.4.0rc1; platform_system == "Linux" and platform_machine == "x86_64"',
            manifest["project"]["dependencies"],
        )

    def test_release_manifest_matches_active_package_identity(self):
        pyproject = self.load_pyproject()
        release_path = self.repo_root / "packaging" / "release.toml"
        release = tomllib.loads(release_path.read_text(encoding="utf-8"))["release"]

        self.assertEqual("1.3.0rc1", release["package_version"])
        self.assertEqual("9.0.0", release["isis_version"])
        self.assertEqual("v1.3.0rc1-isis9.0.0", release["tag"])
        self.assertEqual(pyproject["project"]["version"], release["package_version"])
        self.assertTrue(release["prerelease"])

        package_init = (
            self.repo_root / "python" / "isis_pybind" / "__init__.py"
        ).read_text(encoding="utf-8")
        self.assertIn('__version__ = "1.3.0rc1"', package_init)

    def test_versioned_release_manifests_match_both_package_lines(self):
        release_root = self.repo_root / "packaging" / "releases"
        isis9 = tomllib.loads(
            (release_root / "isis9.toml").read_text(encoding="utf-8")
        )["release"]
        isis10 = tomllib.loads(
            (release_root / "isis10.toml").read_text(encoding="utf-8")
        )["release"]
        isis10_project = tomllib.loads(
            (
                self.repo_root
                / "packaging"
                / "bindings-isis10"
                / "pyproject.toml"
            ).read_text(encoding="utf-8")
        )["project"]

        self.assertEqual("usgs-pyisis", isis9["distribution"])
        self.assertEqual("1.3.0rc1", isis9["package_version"])
        self.assertEqual("9.0.0", isis9["isis_version"])
        self.assertEqual("cp312", isis9["python_abi"])

        self.assertEqual(isis10_project["name"], isis10["distribution"])
        self.assertEqual(isis10_project["version"], isis10["package_version"])
        self.assertEqual("10.0.0", isis10["isis_version"])
        self.assertEqual("cp313", isis10["python_abi"])
        self.assertEqual(
            "usgs-pyisis-runtime-isis10-win64",
            isis10["runtime_distribution"],
        )
        for release in (isis9, isis10):
            self.assertTrue(release["prerelease"])
            for key in ("notes_file", "linux_install_file", "windows_install_file"):
                self.assertTrue((self.repo_root / release[key]).is_file())

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

    def test_cmake_finds_windows_qt_in_the_dependency_prefix(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        dependency_qt_root = (
            '"$ENV{PYISIS_DEP_PREFIX}/Library/lib/cmake"'
        )
        isis_qt_root = '"${ISIS_PREFIX}/Library/lib/cmake"'

        self.assertIn(dependency_qt_root, cmake_lists)
        self.assertIn(isis_qt_root, cmake_lists)
        self.assertLess(
            cmake_lists.index(dependency_qt_root),
            cmake_lists.index(isis_qt_root),
        )

    def test_cmake_links_all_selected_qt_compatibility_targets_to_benchmark(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")
        benchmark_block = cmake_lists.split(
            "if(PYISIS_BUILD_BENCHMARKS)",
            maxsplit=1,
        )[1].split("install(TARGETS _isis_core", maxsplit=1)[0]

        self.assertIn("${PYISIS_QT_TARGETS}", benchmark_block)
        self.assertNotIn("${PYISIS_QT_CORE_TARGET})", benchmark_block)

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

    def test_cmake_embeds_full_prerelease_version(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("SKBUILD_PROJECT_VERSION_FULL", cmake_lists)
        self.assertLess(
            cmake_lists.index("SKBUILD_PROJECT_VERSION_FULL"),
            cmake_lists.index("SKBUILD_PROJECT_VERSION AND"),
        )

    def test_cmake_prefers_isis10_bullet_float64_libraries(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("PYISIS_ISIS_VERSION_MAJOR GREATER_EQUAL 10", cmake_lists)
        self.assertIn('"${bullet_lib_name}-float64"', cmake_lists)
        self.assertIn("NAMES ${_pyisis_bullet_candidates}", cmake_lists)

    def test_cmake_matches_windows_pcl_eigen_alignment(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("if(MSVC AND PYISIS_PCL_INCLUDE_DIR)", cmake_lists)
        self.assertIn(
            "target_compile_definitions(_isis_core PRIVATE EIGEN_MAX_ALIGN_BYTES=32)",
            cmake_lists,
        )

    def test_cmake_installs_pyisis_runtime_helper(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("PYISIS_FACADE_SOURCE_RUNTIME_FILE", cmake_lists)
        self.assertIn("PYISIS_FACADE_BUILD_RUNTIME_FILE", cmake_lists)
        self.assertIn("_runtime.py", cmake_lists)

    def test_cmake_uses_packaged_linux_runtime_rpath_for_wheels(self):
        cmake_lists = (self.repo_root / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn('"$ORIGIN/../pyisis_runtime/vendor/isis/lib"', cmake_lists)
        self.assertIn("if(SKBUILD)", cmake_lists)
        self.assertIn('INSTALL_RPATH "${PYISIS_INSTALL_RPATH}"', cmake_lists)

    def test_minimal_isisdata_package_metadata_exists(self):
        data_pyproject = (
            self.repo_root / "packaging" / "isisdata-minimal" / "pyproject.toml"
        )
        self.assertTrue(data_pyproject.is_file())

        config = tomllib.loads(data_pyproject.read_text(encoding="utf-8"))
        project = config["project"]
        self.assertEqual(project["name"], "usgs-pyisis-isisdata-minimal")
        self.assertEqual(project["version"], "1.3.0rc1")
        self.assertEqual(project["license"], "MIT")
        self.assertIn("setuptools>=77", config["build-system"]["requires"])
        self.assertEqual(config["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertEqual(
            config["tool"]["setuptools"]["packages"],
            ["pyisis_isisdata_minimal"],
        )
        self.assertFalse(config["tool"]["setuptools"]["include-package-data"])
        self.assertEqual(
            config["tool"]["setuptools"]["package-data"]["pyisis_isisdata_minimal"],
            ["data/**/*"],
        )

    def test_minimal_isisdata_package_exposes_packaged_data_path(self):
        package_src = self.repo_root / "packaging" / "isisdata-minimal" / "src"
        self.assertTrue(package_src.is_dir())
        sys.path.insert(0, str(package_src))
        sys.modules.pop("pyisis_isisdata_minimal", None)
        try:
            data_package = importlib.import_module("pyisis_isisdata_minimal")
            data_path = data_package.data_path()
        finally:
            sys.modules.pop("pyisis_isisdata_minimal", None)
            sys.path.remove(str(package_src))

        self.assertTrue((data_path / "base" / "kernels" / "lsk" / "naif0012.tls").is_file())

    def test_windows_runtime_package_metadata_exists(self):
        runtime_pyproject = (
            self.repo_root / "packaging" / "runtime-win64" / "pyproject.toml"
        )
        self.assertTrue(runtime_pyproject.is_file())

        config = tomllib.loads(runtime_pyproject.read_text(encoding="utf-8"))
        project = config["project"]
        self.assertEqual(project["name"], "usgs-pyisis-runtime-win64")
        self.assertEqual(project["version"], "1.3.0rc1")
        self.assertEqual(project["license"], "MIT")
        self.assertIn("setuptools>=77", config["build-system"]["requires"])
        self.assertEqual(config["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertEqual(config["tool"]["setuptools"]["packages"], ["pyisis_runtime"])
        self.assertFalse(config["tool"]["setuptools"]["include-package-data"])
        self.assertEqual(
            config["tool"]["setuptools"]["package-data"]["pyisis_runtime"],
            ["vendor/isis/**/*"],
        )

    def test_linux_runtime_package_metadata_exists(self):
        runtime_pyproject = (
            self.repo_root / "packaging" / "runtime-linux-x86_64" / "pyproject.toml"
        )
        self.assertTrue(runtime_pyproject.is_file())

        config = tomllib.loads(runtime_pyproject.read_text(encoding="utf-8"))
        project = config["project"]
        self.assertEqual(project["name"], "usgs-pyisis-runtime-linux-x86_64")
        self.assertEqual(project["version"], "1.3.0rc1")
        self.assertEqual(project["license"], "MIT")
        self.assertEqual(config["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertIn("setuptools>=77", config["build-system"]["requires"])
        self.assertEqual(config["tool"]["setuptools"]["packages"], ["pyisis_runtime"])
        self.assertFalse(config["tool"]["setuptools"]["include-package-data"])
        self.assertEqual(
            config["tool"]["setuptools"]["package-data"]["pyisis_runtime"],
            ["vendor/isis/**/*"],
        )
        setup_script = runtime_pyproject.with_name("setup.py")
        self.assertTrue(setup_script.is_file())
        setup_text = setup_script.read_text(encoding="utf-8")
        self.assertIn("has_ext_modules", setup_text)
        self.assertIn('return "py3", "none", platform_tag', setup_text)


if __name__ == "__main__":
    unittest.main()
