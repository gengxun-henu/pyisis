"""
Shared helpers for ISIS pybind unit tests.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-28
Updated: 2026-03-28  Geng Xun added shared test environment bootstrap helpers for ISISDATA, build-directory resolution, and reusable fixture factories.
"""

import os
from pathlib import Path
import sys
import tempfile
from contextlib import contextmanager

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PYTHON_DIR = Path(
    os.environ.get(
        "ISIS_PYBIND_BUILD_DIR",
        str(PROJECT_ROOT / "build" / "python"),
    )
)
#WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT.parent / "isis" / "tests" / "data" / "isisdata" / "mockup"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT / "tests" / "data" / "isisdata" / "mockup"


def _has_leap_second_kernels(data_root):
    lsk_dir = Path(data_root) / "base" / "kernels" / "lsk"
    return lsk_dir.exists() and any(lsk_dir.glob("naif*.tls"))


def _ensure_isisdata_for_tests():
    configured = os.environ.get("ISISDATA")

    if configured and _has_leap_second_kernels(configured):
        return

    if WORKSPACE_ISISDATA_MOCKUP.exists() and _has_leap_second_kernels(WORKSPACE_ISISDATA_MOCKUP):
        os.environ["ISISDATA"] = str(WORKSPACE_ISISDATA_MOCKUP)


_ensure_isisdata_for_tests()


if str(BUILD_PYTHON_DIR) not in sys.path and BUILD_PYTHON_DIR.exists():
    sys.path.insert(0, str(BUILD_PYTHON_DIR))


import isis_pybind as ip


DEGREES = ip.Angle.Units.Degrees
RADIANS = ip.Angle.Units.Radians
METERS = ip.Distance.Units.Meters
KILOMETERS = ip.Distance.Units.Kilometers
SOLAR_RADII = ip.Distance.Units.SolarRadii
PIXELS = ip.Distance.Units.Pixels
DISPLACEMENT_METERS = ip.Displacement.Units.Meters
DISPLACEMENT_KILOMETERS = ip.Displacement.Units.Kilometers
DISPLACEMENT_PIXELS = ip.Displacement.Units.Pixels


@contextmanager
def temporary_directory():
        with tempfile.TemporaryDirectory() as temp_dir:
                yield Path(temp_dir)


@contextmanager
def temporary_text_file(name, contents):
        with temporary_directory() as temp_dir:
                file_path = temp_dir / name
                file_path.write_text(contents, encoding="utf-8")
                yield file_path


@contextmanager
def temporary_raw_input_file(name="example.raw"):
    with temporary_directory() as temp_dir:
        raw_path = temp_dir / name

        samples = 16
        lines = 8
        bands = 2
        bytes_per_pixel = 2
        file_header_bytes = 64
        data_prefix_bytes = 8
        total_bytes = file_header_bytes + bands * lines * (data_prefix_bytes + samples * bytes_per_pixel)

        raw_path.write_bytes(b"\x00" * total_bytes)
        yield raw_path


def make_simple_pvl():
        pvl = ip.Pvl()
        pvl.from_string(
                """
Group = Instrument
    InstrumentId = HIRISE
    SpacecraftName = MRO
EndGroup
Object = Archive
    Group = Product
        ProductId = PSP_010502_2090
    EndGroup
EndObject
End
"""
        )
        return pvl


def make_simple_cylindrical_label(
    include_center_longitude=True,
    include_ground_range=True,
    include_pixel_resolution=False,
    include_upper_left=False,
):
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 3396190.0",
        "  PolarRadius = 3376200.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 360",
        "  ProjectionName = SimpleCylindrical",
    ]

    if include_center_longitude:
        lines.append("  CenterLongitude = 220.0")

    if include_ground_range:
        lines.extend(
            [
                "  MinimumLatitude = 10.8920539924144",
                "  MaximumLatitude = 34.7603960060206",
                "  MinimumLongitude = 219.72432466275",
                "  MaximumLongitude = 236.186050244411",
            ]
        )

    if include_pixel_resolution:
        lines.append("  PixelResolution = 2000.0")

    if include_upper_left:
        lines.extend(
            [
                "  UpperLeftCornerX = -18000.0",
                "  UpperLeftCornerY = 2062000.0",
            ]
        )

    lines.extend(["EndGroup", "End"])

    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def attach_dom_like_projection_mapping(
    cube,
    *,
    pixel_resolution=1.0,
    upper_left_x=0.0,
    upper_left_y=None,
):
    """Attach a minimal writable DOM-like Mapping group to a synthetic cube.

    This is intentionally lightweight for unit tests that need `cube.projection()` to
    work without depending on external projected DOM fixtures.
    """
    if upper_left_y is None:
        upper_left_y = float(cube.line_count()) * float(pixel_resolution)

    mapping = ip.PvlGroup("Mapping")
    mapping.add_keyword(ip.PvlKeyword("EquatorialRadius", "3396190.0"))
    mapping.add_keyword(ip.PvlKeyword("PolarRadius", "3376200.0"))
    mapping.add_keyword(ip.PvlKeyword("LatitudeType", "Planetocentric"))
    mapping.add_keyword(ip.PvlKeyword("LongitudeDirection", "PositiveEast"))
    mapping.add_keyword(ip.PvlKeyword("LongitudeDomain", "360"))
    mapping.add_keyword(ip.PvlKeyword("ProjectionName", "SimpleCylindrical"))
    mapping.add_keyword(ip.PvlKeyword("CenterLongitude", "0.0"))
    mapping.add_keyword(ip.PvlKeyword("MinimumLatitude", "-90.0"))
    mapping.add_keyword(ip.PvlKeyword("MaximumLatitude", "90.0"))
    mapping.add_keyword(ip.PvlKeyword("MinimumLongitude", "0.0"))
    mapping.add_keyword(ip.PvlKeyword("MaximumLongitude", "360.0"))
    mapping.add_keyword(ip.PvlKeyword("PixelResolution", str(float(pixel_resolution))))
    mapping.add_keyword(ip.PvlKeyword("UpperLeftCornerX", str(float(upper_left_x))))
    mapping.add_keyword(ip.PvlKeyword("UpperLeftCornerY", str(float(upper_left_y))))
    cube.put_group(mapping)


def make_equirectangular_label(
    include_center_longitude=True,
    include_center_latitude=True,
    include_ground_range=True,
):
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 3396190.0",
        "  PolarRadius = 3376200.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 360",
        "  ProjectionName = Equirectangular",
    ]

    if include_center_longitude:
        lines.append("  CenterLongitude = 0.0")

    if include_center_latitude:
        lines.append("  CenterLatitude = 0.0")

    if include_ground_range:
        lines.extend(
            [
                "  MinimumLatitude = -65.0",
                "  MaximumLatitude = 65.0",
                "  MinimumLongitude = -180.0",
                "  MaximumLongitude = 180.0",
            ]
        )

    lines.extend(["EndGroup", "End"])

    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_ring_cylindrical_label(
    include_center_longitude=True,
    include_center_radius=True,
    include_ground_range=True,
    direction="Clockwise",
    domain="180",
):
    lines = [
        "Group = Mapping",
        "  ProjectionName = RingCylindrical",
        "  TargetName = Saturn",
        f"  RingLongitudeDirection = {direction}",
        f"  RingLongitudeDomain = {domain}",
    ]

    if include_ground_range:
        lines.extend(
            [
                "  MinimumRingRadius = 18000.0",
                "  MaximumRingRadius = 20000000.0",
                "  MinimumRingLongitude = -20.0",
                "  MaximumRingLongitude = 130.0",
            ]
        )

    if include_center_longitude:
        lines.append("  CenterRingLongitude = 0.0")

    if include_center_radius:
        lines.append("  CenterRingRadius = 200000.0")

    lines.extend(["EndGroup", "End"])

    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_sinusoidal_label(include_center_longitude=True):
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetocentric",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -90.0",
        "  MaximumLatitude = 90.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = Sinusoidal",
    ]
    if include_center_longitude:
        lines.append("  CenterLongitude = -90.0")
    lines.extend(["EndGroup", "End"])
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_mercator_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 6378206.4",
        "  PolarRadius = 6356583.8",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -70.0",
        "  MaximumLatitude = 70.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = Mercator",
        "  CenterLongitude = -180.0",
        "  CenterLatitude = 0.0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_robinson_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetocentric",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -90.0",
        "  MaximumLatitude = 90.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  CenterLongitude = 0.0",
        "  ProjectionName = Robinson",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_orthographic_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -70.0",
        "  MaximumLatitude = 70.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = Orthographic",
        "  CenterLongitude = -100.0",
        "  CenterLatitude = 40.0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_mollweide_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 0.7071067811865475",
        "  PolarRadius = 0.7071067811865475",
        "  LatitudeType = Planetocentric",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -90.0",
        "  MaximumLatitude = 90.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = Mollweide",
        "  CenterLongitude = 0.0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_lambert_conformal_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = 20.0",
        "  MaximumLatitude = 80.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = LambertConformal",
        "  CenterLongitude = -96.0",
        "  CenterLatitude = 23.0",
        "  FirstStandardParallel = 33",
        "  SecondStandardParallel = 45",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_lambert_azimuthal_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = 20.0",
        "  MaximumLatitude = 80.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = LambertAzimuthalEqualArea",
        "  CenterLatitude = 0",
        "  CenterLongitude = 0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_oblique_cylindrical_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 2575000.0",
        "  PolarRadius = 2575000.0",
        "  PoleLatitude = 22.858149",
        "  PoleLongitude = 297.158602",
        "  LatitudeType = Planetocentric",
        "  LongitudeDirection = PositiveWest",
        "  LongitudeDomain = 360",
        "  ProjectionName = ObliqueCylindrical",
        "  MinimumLatitude = -90",
        "  MaximumLatitude = 0.92523",
        "  MinimumLongitude = -0.8235",
        "  MaximumLongitude = 180.5",
        "  PoleRotation = 45.7832",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_point_perspective_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = 0.0",
        "  MaximumLatitude = 80.0",
        "  MinimumLongitude = 0.0",
        "  MaximumLongitude = 80.0",
        "  ProjectionName = PointPerspective",
        "  CenterLongitude = 0.0",
        "  CenterLatitude = 0.0",
        "  Distance = 0.00562",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_polar_stereographic_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 6378388.0",
        "  PolarRadius = 6356911.9",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -90.0",
        "  MaximumLatitude = 0.0",
        "  MinimumLongitude = -180.0",
        "  MaximumLongitude = 180.0",
        "  ProjectionName = PolarStereographic",
        "  CenterLongitude = -100.0",
        "  CenterLatitude = -71.0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_transverse_mercator_label():
    lines = [
        "Group = Mapping",
        "  EquatorialRadius = 1.0",
        "  PolarRadius = 1.0",
        "  LatitudeType = Planetographic",
        "  LongitudeDirection = PositiveEast",
        "  LongitudeDomain = 180",
        "  MinimumLatitude = -70.0",
        "  MaximumLatitude = 70.0",
        "  MinimumLongitude = -90.0",
        "  MaximumLongitude = -60.0",
        "  ProjectionName = TransverseMercator",
        "  CenterLongitude = -75.0",
        "  CenterLatitude = 0.0",
        "  ScaleFactor = 1.0",
        "EndGroup",
        "End",
    ]
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_planar_label(include_center_longitude=True, include_center_radius=True):
    lines = [
        "Group = Mapping",
        "  ProjectionName = Planar",
        "  TargetName = Saturn",
        "  RingLongitudeDirection = Clockwise",
        "  RingLongitudeDomain = 180",
        "  MinimumRingRadius = 0.0",
        "  MaximumRingRadius = 2000000.0",
        "  MinimumRingLongitude = -20.0",
        "  MaximumRingLongitude = 130.0",
    ]
    if include_center_longitude:
        lines.append("  CenterRingLongitude = 0.0")
    if include_center_radius:
        lines.append("  CenterRingRadius = 200000.0")
    lines.extend(["EndGroup", "End"])
    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def make_sky_target_label(shape_model=None):
    lines = [
        "Group = Instrument",
        "  TargetName = Sky",
        "EndGroup",
        "Group = Kernels",
        "  NaifIkCode = -94031",
    ]

    if shape_model is not None:
        lines.append(f"  ShapeModel = {shape_model}")

    lines.extend(["EndGroup", "End"])

    pvl = ip.Pvl()
    pvl.from_string("\n".join(lines) + "\n")
    return pvl


def workspace_test_data_path(*parts):
    #return PROJECT_ROOT.parent / "isis" / "tests" / "data" / Path(*parts)
    return PROJECT_ROOT/ "tests" / "data" / Path(*parts)


def close_cube_quietly(cube, remove=False):
    if cube is None:
        return

    try:
        if cube.is_open():
            cube.close(remove=remove)
    except Exception:
        pass


def make_test_cube(
    temp_dir,
    name="test.cub",
    samples=8,
    lines=6,
    bands=1,
    pixel_type=None,
    cube_format=None,
    byte_order=None,
    labels_attached=None,
    base_multiplier=None,
):
    if pixel_type is None:
        pixel_type = ip.PixelType.Real

    cube_path = temp_dir / name
    cube = ip.Cube()
    cube.set_dimensions(samples, lines, bands)
    cube.set_pixel_type(pixel_type)

    if cube_format is not None:
        cube.set_format(cube_format)

    if byte_order is not None:
        cube.set_byte_order(byte_order)

    if labels_attached is not None:
        cube.set_labels_attached(labels_attached)

    if base_multiplier is not None:
        base, multiplier = base_multiplier
        cube.set_base_multiplier(base, multiplier)

    cube.create(str(cube_path))
    return cube, cube_path


def make_closed_test_cube(temp_dir, **kwargs):
    cube, cube_path = make_test_cube(temp_dir, **kwargs)
    cube.close()
    return cube_path


def open_cube(path, access="r"):
    cube = ip.Cube()
    cube.open(str(path), access)
    return cube


def fill_cube_with_constant(cube, value):
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        for index in range(len(manager)):
            manager[index] = value
        cube.write(manager)
        manager.next()


def make_filled_cube(temp_dir, value=5.0, **kwargs):
    cube, cube_path = make_test_cube(temp_dir, **kwargs)
    fill_cube_with_constant(cube, value)
    cube.close()
    return cube_path


def make_tile_test_cube(
    temp_dir,
    data: np.ndarray,
    tile_samples: int,
    tile_lines: int,
    name: str = "test.cub",
) -> tuple[ip.Cube, Path]:
    """Create a tile-format ISIS cube with known data.

    Args:
        temp_dir: temporary directory (Path)
        data: 2D numpy array (lines x samples) of float64 values
        tile_samples: tile width in samples
        tile_lines: tile height in lines
        name: output filename

    Returns:
        (cube, cube_path) — the cube is open and ready for reading.
    """
    lines, samples = data.shape
    bands = 1

    cube_path = temp_dir / name
    cube = ip.Cube()
    cube.set_dimensions(samples, lines, bands)
    cube.set_pixel_type(ip.PixelType.Real)
    cube.set_format(ip.Cube.Format.Tile)
    cube.create(str(cube_path))

    # Write tile dimension keywords into the Core group.
    core = ip.PvlGroup("Core")
    core.add_keyword(ip.PvlKeyword("StartByte", str(cube.label_size(actual=True))))
    core.add_keyword(ip.PvlKeyword("Format", "Tile"))
    core.add_keyword(ip.PvlKeyword("TileSamples", str(tile_samples)))
    core.add_keyword(ip.PvlKeyword("TileLines", str(tile_lines)))
    cube.put_group(core)

    # Fill data line by line.
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(data[line_index, index])
        cube.write(manager)
        manager.next()

    return cube, cube_path