# Third-party notices

PyISIS binding-layer and Python facade code authored in this repository are
distributed under the repository `LICENSE`.

The platform wheelhouses also contain or dynamically use software from other
projects. Those components remain under their own licenses; the repository MIT
license does not replace them.

## USGS ISIS 9.0.0

The runtime is built from
[`DOI-USGS/ISIS3` tag `9.0.0`](https://github.com/DOI-USGS/ISIS3/tree/9.0.0).
The upstream project states that, unless otherwise noted, its work is in the
public domain in the United States and is also dedicated through CC0 1.0.
See the upstream
[`LICENSE.md`](https://github.com/DOI-USGS/ISIS3/blob/9.0.0/LICENSE.md) and
[`DISCLAIMER.md`](https://github.com/DOI-USGS/ISIS3/blob/9.0.0/DISCLAIMER.md).

The Windows build applies the repository patch queue under
`ports/windows/isis/patches/` to that tagged source.

## Runtime dependencies

The bundled runtime dependency closure is produced from the pinned environment
definitions:

- `ports/linux/env/pyisis-isis-linux-64.yml`
- `ports/windows/env/pyisis-isis-win64.yml`

It includes libraries from the conda-forge and USGS Astrogeology ecosystems,
including Qt, Qwt, CSPICE, CSM/USGSCSM, Armadillo, Boost, Bullet, Embree, GEOS,
GeoTIFF, GSL, HDF5, OpenCV, OpenBLAS, PNG, Protobuf, SuiteSparse, TIFF,
Xerces-C, and their transitive runtime dependencies. Each component retains
its upstream copyright, attribution, notice, patent, and license terms.

This notice is an attribution guide, not a replacement for those licenses.
For compliance-sensitive redistribution, inspect the exact wheel payload and
the package metadata from the workflow run used to create the release.
