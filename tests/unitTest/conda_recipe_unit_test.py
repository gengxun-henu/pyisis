"""Unit tests for the conda package recipe.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-08-21
Updated: 2026-06-18  Geng Xun added conda recipe coverage for package metadata, build scripts, and smoke-test commands.
Updated: 2026-06-18  Geng Xun added git source coverage to keep local build artifacts out of conda-build work copies.
Updated: 2026-06-18  Geng Xun added compiler variant coverage for Windows conda-build packaging.
Updated: 2026-06-18  Geng Xun added coverage for the minimal ISISDATA conda package and activation scripts.
Updated: 2026-06-18  Geng Xun added regression coverage to keep conda-build helper files out of packaged ISISDATA.
Updated: 2026-06-18  Geng Xun added package-test coverage for ISISDATA activation.
Updated: 2026-07-23  Geng Xun aligned conda recipes with the 1.3.0rc1 release identity.
Updated: 2026-07-25  Geng Xun aligned conda recipes with the 1.3.0rc2 release identity.
Updated: 2026-08-21  Geng Xun aligned conda recipes with the rc3 dual-version release identity.
"""

from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECIPE_DIR = PROJECT_ROOT / "recipe"
ISISDATA_RECIPE_DIR = RECIPE_DIR / "isisdata-minimal"


class CondaRecipeUnitTest(unittest.TestCase):
    """Test suite for the repository conda-build recipe. Added: 2026-06-18."""

    def test_recipe_files_are_present(self):
        self.assertTrue((RECIPE_DIR / "meta.yaml").is_file())
        self.assertTrue((RECIPE_DIR / "build.sh").is_file())
        self.assertTrue((RECIPE_DIR / "bld.bat").is_file())
        self.assertTrue((RECIPE_DIR / "conda_build_config.yaml").is_file())
        self.assertTrue((RECIPE_DIR / "README.md").is_file())

    def test_meta_yaml_declares_pyisis_package_and_git_source(self):
        recipe_file = RECIPE_DIR / "meta.yaml"
        self.assertTrue(recipe_file.is_file(), f"Missing conda recipe metadata: {recipe_file}")
        meta_yaml = recipe_file.read_text(encoding="utf-8")

        self.assertIn("{% set name = \"pyisis\" %}", meta_yaml)
        self.assertIn("{% set version = \"1.3.0rc3\" %}", meta_yaml)
        self.assertIn("name: {{ name|lower }}", meta_yaml)
        self.assertIn("source:", meta_yaml)
        self.assertIn("git_url: ..", meta_yaml)
        self.assertIn("git_rev: HEAD", meta_yaml)
        self.assertIn("script_env:", meta_yaml)
        self.assertIn("- ISIS_PREFIX", meta_yaml)
        self.assertIn("- PYISIS_DEP_PREFIX", meta_yaml)

    def test_meta_yaml_uses_git_source_to_exclude_local_build_artifacts(self):
        meta_yaml = (RECIPE_DIR / "meta.yaml").read_text(encoding="utf-8")

        self.assertIn("git_url: ..", meta_yaml)
        self.assertIn("git_rev: HEAD", meta_yaml)
        self.assertNotIn("path: ..", meta_yaml)

    def test_meta_yaml_covers_build_host_run_and_import_smoke_tests(self):
        recipe_file = RECIPE_DIR / "meta.yaml"
        self.assertTrue(recipe_file.is_file(), f"Missing conda recipe metadata: {recipe_file}")
        meta_yaml = recipe_file.read_text(encoding="utf-8")

        self.assertIn("build:", meta_yaml)
        self.assertIn("requirements:", meta_yaml)
        self.assertIn("host:", meta_yaml)
        self.assertIn("run:", meta_yaml)
        self.assertIn("- python", meta_yaml)
        self.assertIn("- pybind11", meta_yaml)
        self.assertIn("test:", meta_yaml)
        self.assertIn("- pyisis", meta_yaml)
        self.assertIn("pyisis.core()", meta_yaml)
        self.assertIn("import isis_pybind", meta_yaml)

    def test_windows_compiler_variant_uses_installed_vs2022_toolchain(self):
        config_file = RECIPE_DIR / "conda_build_config.yaml"
        self.assertTrue(config_file.is_file(), f"Missing conda-build variant config: {config_file}")
        config = config_file.read_text(encoding="utf-8")

        self.assertIn("c_compiler:", config)
        self.assertIn("cxx_compiler:", config)
        self.assertIn("- vs2022", config)

    def test_build_scripts_configure_build_and_install_with_cmake(self):
        build_sh_path = RECIPE_DIR / "build.sh"
        bld_bat_path = RECIPE_DIR / "bld.bat"
        self.assertTrue(build_sh_path.is_file(), f"Missing Unix conda build script: {build_sh_path}")
        self.assertTrue(bld_bat_path.is_file(), f"Missing Windows conda build script: {bld_bat_path}")
        build_sh = build_sh_path.read_text(encoding="utf-8")
        bld_bat = bld_bat_path.read_text(encoding="utf-8")

        for script in (build_sh, bld_bat):
            self.assertIn("ISIS_PREFIX", script)
            self.assertIn("PYISIS_DEP_PREFIX", script)
            self.assertIn("cmake -S", script)
            self.assertIn("DISIS_PREFIX", script)
            self.assertIn("DCMAKE_INSTALL_PREFIX", script)
            self.assertIn("cmake --build", script)
            self.assertIn("cmake --install", script)

    def test_build_scripts_install_python_packages_into_conda_site_packages(self):
        build_sh = (RECIPE_DIR / "build.sh").read_text(encoding="utf-8")
        bld_bat = (RECIPE_DIR / "bld.bat").read_text(encoding="utf-8")

        for script in (build_sh, bld_bat):
            self.assertIn("SP_DIR", script)
            self.assertIn("PYISIS_INSTALL_SITELIB", script)
            self.assertIn("PYISIS_INSTALL_SITEARCH", script)

    def test_cmake_exposes_conda_site_package_install_overrides(self):
        cmake_lists = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("PYISIS_INSTALL_SITELIB", cmake_lists)
        self.assertIn("PYISIS_INSTALL_SITEARCH", cmake_lists)
        self.assertIn('${PYISIS_INSTALL_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}', cmake_lists)
        self.assertIn('${PYISIS_INSTALL_SITELIB}/${PYISIS_FACADE_PACKAGE_NAME}', cmake_lists)

    def test_recipe_readme_documents_local_windows_build(self):
        readme_file = RECIPE_DIR / "README.md"
        self.assertTrue(readme_file.is_file(), f"Missing conda recipe documentation: {readme_file}")
        readme = readme_file.read_text(encoding="utf-8")

        self.assertIn("conda build", readme)
        self.assertIn("ISIS_PREFIX", readme)
        self.assertIn("PYISIS_DEP_PREFIX", readme)
        self.assertIn("build\\windows\\isis-prefix", readme)

    def test_minimal_isisdata_recipe_files_are_present(self):
        self.assertTrue((ISISDATA_RECIPE_DIR / "meta.yaml").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "build.sh").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "bld.bat").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "activate.d" / "pyisis-isisdata-minimal-activate.bat").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "deactivate.d" / "pyisis-isisdata-minimal-deactivate.bat").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "activate.d" / "pyisis-isisdata-minimal-activate.sh").is_file())
        self.assertTrue((ISISDATA_RECIPE_DIR / "deactivate.d" / "pyisis-isisdata-minimal-deactivate.sh").is_file())

    def test_minimal_isisdata_recipe_declares_data_package(self):
        meta_yaml = (ISISDATA_RECIPE_DIR / "meta.yaml").read_text(encoding="utf-8")

        self.assertIn("name: pyisis-isisdata-minimal", meta_yaml)
        self.assertIn("version: 1.3.0rc3", meta_yaml)
        self.assertIn("path: ../../tests/data/isisdata/mockup", meta_yaml)
        self.assertIn("noarch: generic", meta_yaml)
        self.assertIn("share/isisdata", meta_yaml)
        self.assertIn("naif0012.tls", meta_yaml)

    def test_minimal_isisdata_recipe_tests_activation_sets_isisdata(self):
        meta_yaml = (ISISDATA_RECIPE_DIR / "meta.yaml").read_text(encoding="utf-8")

        self.assertIn('if "%ISISDATA%"=="" exit /b 1', meta_yaml)
        self.assertIn('test -n "$ISISDATA"', meta_yaml)

    def test_minimal_isisdata_build_scripts_install_data_and_activation_hooks(self):
        build_sh = (ISISDATA_RECIPE_DIR / "build.sh").read_text(encoding="utf-8")
        bld_bat = (ISISDATA_RECIPE_DIR / "bld.bat").read_text(encoding="utf-8")

        for script in (build_sh, bld_bat):
            self.assertIn("share", script)
            self.assertIn("isisdata", script)
            self.assertIn("activate.d", script)
            self.assertIn("deactivate.d", script)

    def test_minimal_isisdata_build_scripts_copy_only_data_directories(self):
        build_sh = (ISISDATA_RECIPE_DIR / "build.sh").read_text(encoding="utf-8")
        bld_bat = (ISISDATA_RECIPE_DIR / "bld.bat").read_text(encoding="utf-8")

        self.assertNotIn('"${SRC_DIR}/."', build_sh)
        self.assertNotIn('robocopy "%SRC_DIR%" "%DATA_DIR%" /E', bld_bat)
        self.assertIn("for data_subdir in", build_sh)
        self.assertIn("for /D %%D in", bld_bat)

    def test_minimal_isisdata_activation_scripts_set_isisdata_without_overriding_user_value(self):
        scripts = [
            ISISDATA_RECIPE_DIR / "activate.d" / "pyisis-isisdata-minimal-activate.bat",
            ISISDATA_RECIPE_DIR / "activate.d" / "pyisis-isisdata-minimal-activate.sh",
        ]

        for script_path in scripts:
            script = script_path.read_text(encoding="utf-8")
            self.assertIn("ISISDATA", script)
            self.assertIn("PYISIS_OLD_ISISDATA", script)
            self.assertIn("CONDA_PREFIX", script)


if __name__ == "__main__":
    unittest.main()
