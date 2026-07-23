# Linux x86_64 manylinux wheel build

The Linux wheel job runs inside the official PyPA
`quay.io/pypa/manylinux_2_28_x86_64` container. It uses the pinned conda
environment in `env/pyisis-isis-linux-64.yml` to build CPython 3.12 wheels
against USGS ISIS 9.0.0. Separate Ubuntu 22.04 and 24.04 GitHub-hosted runners
download the same wheelhouse and verify clean installs without access to the
build-time conda prefix.

The binding runtime is assembled from files owned by the ISIS conda package
plus the transitive native-library closure. ISIS command-line apps, headers,
build files, and unrelated environment libraries are excluded. CI enforces a
650 MB expanded-runtime budget and a 350 MB compressed-wheel budget.

The hosted build records two complementary ABI reports. `auditwheel show`
records each native wheel and evaluates a temporary union of the extension and
runtime payloads, matching their installed layout without changing the three
published wheels. The combined policy result must be manylinux 2.28 or older.
Meanwhile,
`tools/packaging/audit_linux_wheelhouse.py` streams GLIBC symbol versions from
both native wheels without expanding them. The manylinux tag is accepted only
when the GLIBC 2.28 symbol gate and combined auditwheel policy gate pass,
followed by the two clean-install jobs.
