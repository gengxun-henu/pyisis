import os
from pathlib import Path
import sys
import tempfile
from contextlib import contextmanager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT.parent / "isis" / "tests" / "data" / "isisdata" / "mockup"


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
    return PROJECT_ROOT.parent / "isis" / "tests" / "data" / Path(*parts)
