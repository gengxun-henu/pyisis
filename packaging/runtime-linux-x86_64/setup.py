"""Mark the shared-library runtime distribution as a platform wheel."""

from setuptools import Distribution, setup
from wheel.bdist_wheel import bdist_wheel


class BinaryRuntimeDistribution(Distribution):
    """Force runtime payloads into platlib for wheel policy inspection."""

    def has_ext_modules(self) -> bool:
        return True


class PlatformIndependentAbiWheel(bdist_wheel):
    """Keep the data-only Python ABI while retaining a native platform tag."""

    def get_tag(self) -> tuple[str, str, str]:
        _, _, platform_tag = super().get_tag()
        return "py3", "none", platform_tag


setup(
    distclass=BinaryRuntimeDistribution,
    cmdclass={"bdist_wheel": PlatformIndependentAbiWheel},
)
