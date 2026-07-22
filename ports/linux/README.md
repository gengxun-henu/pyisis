# Linux x86_64 wheel prototype

The Linux wheel job uses the pinned conda environment in
`env/pyisis-isis-linux-64.yml` to build CPython 3.12 wheels against USGS ISIS
9.0.0. A second GitHub-hosted runner downloads the wheelhouse and verifies a
clean install without access to the build-time conda prefix.

These artifacts use the honest `linux_x86_64` platform tag. They are release
prototypes, not PyPI-ready manylinux wheels. A future release job must build in
the selected PyPA manylinux container, run an ABI/dependency audit, and only
then apply a manylinux platform tag.
