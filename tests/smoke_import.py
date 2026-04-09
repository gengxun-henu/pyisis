import os
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT/ "tests" / "data" / "isisdata" / "mockup"
print(f"Using workspace ISISDATA mockup at {WORKSPACE_ISISDATA_MOCKUP}")
print(f"Using PROJECT_ROOT at {PROJECT_ROOT}")
print(f"Using BUILD_PYTHON_DIR at {BUILD_PYTHON_DIR}")

def _has_leap_second_kernels(data_root):
    lsk_dir = Path(data_root) / "base" / "kernels" / "lsk"
    return lsk_dir.exists() and any(lsk_dir.glob("naif*.tls"))


def _ensure_isisdata_for_tests():
    configured = os.environ.get("ISISDATA")

    if configured and _has_leap_second_kernels(configured):
        print(f"ISISDATA is already configured to {configured} and contains leap second kernels.")
        print(f"Leap second kernels are required for some tests, so this environment variable will be used as is.")
        return

    if WORKSPACE_ISISDATA_MOCKUP.exists() and _has_leap_second_kernels(WORKSPACE_ISISDATA_MOCKUP):
        os.environ["ISISDATA"] = str(WORKSPACE_ISISDATA_MOCKUP)


_ensure_isisdata_for_tests()

if BUILD_PYTHON_DIR.exists():
    sys.path.insert(0, str(BUILD_PYTHON_DIR))

import isis_pybind as ip

HAS_CONTROL_BINDINGS = all(
    hasattr(ip, name)
    for name in (
        "BundleImage",
        "ControlMeasureLogData",
        "ControlMeasure",
        "ControlPoint",
        "ControlNet",
        "ControlNetFilter",
        "ControlNetDiff",
        "ControlNetStatistics",
        "ControlNetValidMeasure",
        "ControlPointList",
        "ControlPointV0001",
        "ControlPointV0002",
        "ControlPointV0003",
        "BundleObservationSolveSettings",
        "BundleSettings",
        "BundleTargetBody",
        "MeasureValidationResults",
    )
)

# Temporarily disabled - bind_bundle_advanced is excluded from compilation
# HAS_ADVANCED_BUNDLE_BINDINGS = all(
#     hasattr(ip, name)
#     for name in (
#         "BundleMeasure",
#         "BundleControlPoint",
#         "BundleObservation",
#         "BundleObservationVector",
#         "BundleLidarRangeConstraint",
#         "BundleLidarControlPoint",
#         "BundleLidarPointVector",
#         "BundleResults",
#         "BundleSolutionInfo",
#     )
# )
HAS_ADVANCED_BUNDLE_BINDINGS = False


@contextmanager
def temporary_raw_input_file(name="example.raw"):
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_path = Path(temp_dir) / name

        samples = 16
        lines = 8
        bands = 2
        bytes_per_pixel = 2
        file_header_bytes = 64
        data_prefix_bytes = 8
        total_bytes = file_header_bytes + bands * lines * (data_prefix_bytes + samples * bytes_per_pixel)

        raw_path.write_bytes(b"\x00" * total_bytes)
        yield raw_path


def test_basic_symbols_present():
    assert hasattr(ip, "CollectorMap")
    assert hasattr(ip, "CubeAttributeInput")
    assert hasattr(ip, "CubeAttributeOutput")
    assert hasattr(ip, "Blobber")
    assert hasattr(ip, "LabelAttachment")
    assert hasattr(ip, "Message")
    assert hasattr(ip, "Progress")
    assert hasattr(ip, "IExceptionErrorType")
    assert hasattr(ip, "Ransac")
    assert hasattr(ip, "SurfaceModel")
    assert hasattr(ip, "TrackingTable")
    assert hasattr(ip, "Resource")
    assert hasattr(ip, "Calculator")
    assert hasattr(ip, "Centroid")
    assert hasattr(ip, "Affine")
    assert hasattr(ip, "BasisFunction")
    assert hasattr(ip, "NthOrderPolynomial")
    assert hasattr(ip, "InfixToPostfix")
    assert hasattr(ip, "CubeInfixToPostfix")
    assert hasattr(ip, "InlineInfixToPostfix")
    assert hasattr(ip, "Process")
    assert hasattr(ip, "ProcessByBrick")
    assert hasattr(ip, "ProcessByLine")
    assert hasattr(ip, "ProcessBySample")
    assert hasattr(ip, "ProcessBySpectra")
    assert hasattr(ip, "ProcessByTile")
    assert hasattr(ip, "ProcessImport")
    assert hasattr(ip, "ProcessImportFits")
    assert hasattr(ip, "ProcessImportPds")
    assert hasattr(ip, "ProcessImportVicar")
    assert hasattr(ip, "ProcessByBoxcar")
    assert hasattr(ip, "ProcessByQuickFilter")
    assert hasattr(ip, "Statistics")
    assert hasattr(ip, "Histogram")
    assert hasattr(ip, "ImageHistogram")
    assert hasattr(ip, "GaussianDistribution")
    assert hasattr(ip, "GroupedStatistics")
    assert hasattr(ip, "MultivariateStatistics")
    assert hasattr(ip, "VecFilter")
    assert hasattr(ip, "Angle")
    assert hasattr(ip, "Environment")
    assert hasattr(ip, "Stereo")
    assert hasattr(ip, "AtmosModel")
    assert hasattr(ip, "Anisotropic1")
    assert hasattr(ip, "Anisotropic2")
    assert hasattr(ip, "HapkeAtm1")
    assert hasattr(ip, "HapkeAtm2")
    assert hasattr(ip, "Hapke")
    assert hasattr(ip, "Isotropic1")
    assert hasattr(ip, "Isotropic2")
    assert hasattr(ip, "NumericalAtmosApprox")
    assert hasattr(ip, "ShadeAtm")
    assert hasattr(ip, "PhotoModel")
    assert hasattr(ip, "PhotoModelFactory")
    assert hasattr(ip, "TopoAtm")
    assert hasattr(ip, "BundleImage")
    assert hasattr(ip, "BundleObservationSolveSettings")
    assert hasattr(ip, "BundleSettings")
    assert hasattr(ip, "BundleTargetBody")
    assert hasattr(ip, "ControlNetFilter")
    assert hasattr(ip, "ControlNetStatistics")
    assert hasattr(ip, "ControlNetValidMeasure")
    # Temporarily disabled - bind_bundle_advanced is excluded from compilation
    # assert hasattr(ip, "BundleMeasure")
    # assert hasattr(ip, "BundleControlPoint")
    # assert hasattr(ip, "BundleObservation")
    # assert hasattr(ip, "BundleObservationVector")
    # assert hasattr(ip, "BundleLidarRangeConstraint")
    # assert hasattr(ip, "BundleLidarControlPoint")
    # assert hasattr(ip, "BundleLidarPointVector")
    # assert hasattr(ip, "BundleResults")
    # assert hasattr(ip, "BundleSolutionInfo")
    assert hasattr(ip, "ControlPointV0001")
    assert hasattr(ip, "ControlPointV0002")
    assert hasattr(ip, "ControlPointV0003")
    assert hasattr(ip, "Transform")
    assert hasattr(ip, "Interpolator")
    assert hasattr(ip, "Enlarge")
    assert hasattr(ip, "Reduce")
    assert hasattr(ip, "ExportDescription")
    assert hasattr(ip, "JP2Error")
    assert hasattr(ip, "JP2Decoder")
    assert hasattr(ip, "JP2Encoder")
    assert hasattr(ip, "LineEquation")
    assert hasattr(ip, "PixelType")
    assert hasattr(ip, "ByteOrder")
    assert hasattr(ip, "Buffer")
    assert hasattr(ip, "BufferManager")
    assert hasattr(ip, "BandManager")
    assert hasattr(ip, "BoxcarManager")
    assert hasattr(ip, "Blob")
    assert hasattr(ip, "Brick")
    assert hasattr(ip, "Portal")
    assert hasattr(ip, "AlphaCube")
    assert hasattr(ip, "TableField")
    assert hasattr(ip, "TableRecord")
    assert hasattr(ip, "Table")
    assert hasattr(ip, "LineManager")
    assert hasattr(ip, "SampleManager")
    assert hasattr(ip, "TileManager")
    assert hasattr(ip, "Sensor")
    assert hasattr(ip, "Camera")
    assert hasattr(ip, "CameraDetectorMap")
    assert hasattr(ip, "CameraDistortionMap")
    assert hasattr(ip, "CameraFocalPlaneMap")
    assert hasattr(ip, "CameraGroundMap")
    assert hasattr(ip, "CameraPointInfo")
    assert hasattr(ip, "CameraSkyMap")
    assert hasattr(ip, "CameraFactory")
    assert hasattr(ip, "Cube")
    assert hasattr(ip, "FileName")
    assert hasattr(ip, "Projection")
    assert hasattr(ip, "ProjectionFactory")
    assert hasattr(ip, "UniversalGroundMap")
    assert hasattr(ip, "SerialNumber")
    assert hasattr(ip, "SerialNumberList")
    assert hasattr(ip, "ObservationNumber")
    assert hasattr(ip, "SimpleCylindrical")
    assert hasattr(ip, "SurfacePoint")
    assert hasattr(ip, "ShapeModel")
    assert hasattr(ip, "Target")
    assert hasattr(ip, "ShapeModelFactory")
    assert hasattr(ip, "Intercept")
    assert hasattr(ip, "AbstractPlate")
    assert hasattr(ip, "TriangularPlate")
    assert hasattr(ip, "NaifDskPlateModel")
    assert hasattr(ip, "EmbreeTargetShape")
    assert hasattr(ip, "EmbreeTargetManager")
    assert hasattr(ip, "BulletTargetShape")
    assert hasattr(ip, "BulletWorldManager")
    assert hasattr(ip, "EllipsoidShape")
    assert hasattr(ip, "DemShape")
    assert hasattr(ip, "PlaneShape")
    assert hasattr(ip, "NaifDskShape")
    assert hasattr(ip, "EmbreeShapeModel")
    assert hasattr(ip, "BulletShapeModel")
    assert hasattr(ip, "LineScanCameraDetectorMap")
    assert hasattr(ip, "LineScanCameraGroundMap")
    assert hasattr(ip, "LineScanCameraSkyMap")
    assert hasattr(ip, "HayabusaAmicaCamera")
    assert hasattr(ip, "HayabusaNirsCamera")
    assert hasattr(ip, "NirsDetectorMap")
    assert hasattr(ip, "Hyb2OncCamera")
    assert hasattr(ip, "Hyb2OncDistortionMap")
    assert hasattr(ip, "HiriseCamera")
    assert hasattr(ip, "HrscCamera")
    assert hasattr(ip, "IssNACamera")
    assert hasattr(ip, "MeasureValidationResults")
    assert hasattr(ip, "MexHrscSrcCamera")
    assert hasattr(ip, "MiniRF")
    assert hasattr(ip, "Mariner10Camera")
    assert hasattr(ip, "NewHorizonsLeisaCamera")
    assert hasattr(ip, "NewHorizonsLorriCamera")
    assert hasattr(ip, "NewHorizonsLorriDistortionMap")
    assert hasattr(ip, "NewHorizonsMvicFrameCamera")
    assert hasattr(ip, "NewHorizonsMvicFrameCameraDistortionMap")
    assert hasattr(ip, "NewHorizonsMvicTdiCamera")
    assert hasattr(ip, "NewHorizonsMvicTdiCameraDistortionMap")
    assert hasattr(ip, "TaylorCameraDistortionMap")
    assert hasattr(ip, "ThemisIrCamera")
    assert hasattr(ip, "ThemisIrDistortionMap")
    assert hasattr(ip, "ThemisVisCamera")
    assert hasattr(ip, "ThemisVisDistortionMap")
    assert hasattr(ip, "Pvl")
    assert hasattr(ip, "VikingCamera")
    assert hasattr(ip.Sensor, "get_surface_point")
    assert hasattr(ip.Camera, "get_surface_point")


def make_simple_cylindrical_label():
    pvl = ip.Pvl()
    pvl.from_string(
        """
Group = Mapping
  EquatorialRadius = 3396190.0
  PolarRadius = 3376200.0
  LatitudeType = Planetographic
  LongitudeDirection = PositiveEast
  LongitudeDomain = 360
  MinimumLatitude = -10.0
  MaximumLatitude = 10.0
  MinimumLongitude = 200.0
  MaximumLongitude = 240.0
  PixelResolution = 1000.0
  ProjectionName = SimpleCylindrical
  CenterLongitude = 220.0
EndGroup
End
"""
    )
    return pvl


def make_ring_cylindrical_label():
    pvl = ip.Pvl()
    pvl.from_string(
"""
Group = Mapping
  RingLongitudeDirection = CounterClockwise
  RingLongitudeDomain = 360
  MinimumRingRadius = 100000.0
  MaximumRingRadius = 200000.0
  MinimumRingLongitude = 10.0
  MaximumRingLongitude = 50.0
  PixelResolution = 100.0
  ProjectionName = RingCylindrical
  CenterRingLongitude = 20.0
  CenterRingRadius = 150000.0
EndGroup
End
"""
    )
    return pvl


def make_sky_target_label():
        pvl = ip.Pvl()
        pvl.from_string(
                """
Group = Instrument
    TargetName = Sky
EndGroup
Group = Kernels
    NaifIkCode = -94031
EndGroup
End
"""
        )
        return pvl


def make_control_point_v0001_object():
        pvl = ip.Pvl()
        pvl.from_string(
                """
Object = ControlPoint
    PointId = CPV1
    PointType = Ground
    X = 1000.0
    Y = 2000.0
    Z = 3000.0
    Group = Measure
        SerialNumber = SN-V1
        Sample = 10.5
        Line = 20.5
        AprioriSample = 10.5
        AprioriLine = 20.5
        SampleSigma = 0.5
        LineSigma = 0.5
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.9
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")


def make_control_point_v0002_object():
        pvl = ip.Pvl()
        pvl.from_string(
                """
Object = ControlPoint
    PointId = CPV2
    PointType = Ground
    AprioriX = 1000.0
    AprioriY = 2000.0
    AprioriZ = 3000.0
    AdjustedX = 1001.0
    AdjustedY = 2001.0
    AdjustedZ = 3001.0
    Group = Measure
        SerialNumber = SN-V2
        Sample = 11.5
        Line = 21.5
        SampleResidual = 0.0
        LineResidual = 0.0
        AprioriSample = 11.5
        AprioriLine = 21.5
        SampleSigma = 0.25
        LineSigma = 0.25
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.8
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")


def make_control_point_v0003_object():
        pvl = ip.Pvl()
        pvl.from_string(
                """
Object = ControlPoint
    PointId = CPV3
    PointType = Fixed
    AprioriX = 1100.0
    AprioriY = 2100.0
    AprioriZ = 3100.0
    AdjustedX = 1101.0
    AdjustedY = 2101.0
    AdjustedZ = 3101.0
    Group = Measure
        SerialNumber = SN-V3
        Sample = 12.5
        Line = 22.5
        SampleResidual = 0.1
        LineResidual = 0.2
        AprioriSample = 12.4
        AprioriLine = 22.4
        SampleSigma = 0.2
        LineSigma = 0.2
        MeasureType = Manual
        Reference = True
        GoodnessOfFit = 0.7
    EndGroup
EndObject
End
"""
        )
        return pvl.find_object("ControlPoint")


def test_basic_base_objects_work():
    if HAS_CONTROL_BINDINGS:
        log_data = ip.ControlMeasureLogData(
            ip.ControlMeasureLogData.NumericLogDataType.GoodnessOfFit,
            0.75,
        )
        assert log_data.is_valid()
        assert log_data.get_numerical_value() == 0.75

        measure = ip.ControlMeasure()
        measure.set_cube_serial_number("SN1")
        measure.set_coordinate(10.5, 20.5)
        measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        measure.set_log_data(log_data)
        assert measure.get_cube_serial_number() == "SN1"
        assert measure.get_measure_type_string() == "Manual"

        point = ip.ControlPoint("P1")
        point.add_measure(measure)
        point.set_type(ip.ControlPoint.PointType.Free)
        point.set_ref_measure(0)
        assert point.get_id() == "P1"
        assert point.get_num_measures() == 1
        assert point.get_ref_measure().get_cube_serial_number() == "SN1"

        net = ip.ControlNet()
        net.add_point(point)
        net.set_network_id("TestNet")
        assert net.get_num_points() == 1
        assert net.get_point("P1").get_num_measures() == 1

        diff = ip.ControlNetDiff()
        assert diff is not None

        statistics = ip.ControlNetStatistics(net)
        assert statistics.num_valid_points() == 1
        assert statistics.num_valid_measures() == 1
        validator = ip.ControlNetValidMeasure()
        assert validator.location_string(0.6, 1.6) == "0,1"
        assert validator.valid_emission_angle(30.0) is True

        validation_results = ip.MeasureValidationResults()
        assert validation_results.is_valid() is True
        validation_results.add_failure(
            ip.MeasureValidationResults.Option.PixelShift,
            1.5,
            "greater",
        )
        assert validation_results.is_valid() is False
        assert "Pixel Shift" in validation_results.to_string()

        with tempfile.TemporaryDirectory() as temp_dir:
            point_list_path = Path(temp_dir) / "points.lis"
            point_list_path.write_text("P1\nP2\n", encoding="utf-8")
            point_list = ip.ControlPointList(ip.FileName(str(point_list_path)))
            assert len(point_list) == 2

        control_point_v0001 = ip.ControlPointV0001(make_control_point_v0001_object(), "Mars")
        assert len(control_point_v0001.point_data()) > 0
        assert len(control_point_v0001.log_data()) > 0

        control_point_v0002 = ip.ControlPointV0002(make_control_point_v0002_object())
        assert len(control_point_v0002.point_data()) > 0
        assert len(control_point_v0002.log_data()) > 0

        control_point_v0002_upgrade = ip.ControlPointV0002(control_point_v0001)
        assert control_point_v0002_upgrade.point_data() == control_point_v0001.point_data()

        control_point_v0003 = ip.ControlPointV0003(make_control_point_v0003_object())
        assert len(control_point_v0003.point_data()) > 0

        control_point_v0003_upgrade = ip.ControlPointV0003(control_point_v0002)
        assert len(control_point_v0003_upgrade.point_data()) > 0

        cube = ip.Cube()
        cube.open(str(PROJECT_ROOT / "tests" / "data" / "mosrange" / "EN0108828322M_iof.cub"), "r")
        try:
            camera = cube.camera()
            bundle_image = ip.BundleImage(camera, "SMOKE-SN", "smoke.cub")
            assert bundle_image.serial_number() == "SMOKE-SN"
            assert bundle_image.file_name() == "smoke.cub"
        finally:
            cube.close()

        bundle_settings = ip.BundleSettings()
        bundle_settings.set_solve_options(True, False, True)
        bundle_settings.set_create_inverse_matrix(True)
        assert bundle_settings.solve_observation_mode() is True
        assert bundle_settings.create_inverse_matrix() is True

        observation_settings = ip.BundleObservationSolveSettings()
        observation_settings.set_instrument_id("HIRISE")
        observation_settings.add_observation_number("OBS-HI-1")
        bundle_settings.set_observation_solve_options([observation_settings])
        assert bundle_settings.observation_solve_settings()[0].instrument_id() == "HIRISE"

        target_body = ip.BundleTargetBody()
        target_body.set_solve_settings(
            [ip.BundleTargetBody.TargetSolveCodes.MeanRadius],
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.Angle(0.0, ip.Angle.Units.Degrees),
            ip.Angle(-1.0, ip.Angle.Units.Degrees),
            ip.BundleTargetBody.TargetRadiiSolveMethod.Mean,
            ip.Distance(1.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1.0, ip.Distance.Units.Kilometers),
            ip.Distance(0.0, ip.Distance.Units.Kilometers),
            ip.Distance(1737.4, ip.Distance.Units.Kilometers),
            ip.Distance(1.0, ip.Distance.Units.Kilometers),
        )
        bundle_settings.set_bundle_target_body(target_body)
        assert target_body.solve_mean_radius() is True
        assert target_body.number_radius_parameters() == 1
        assert "MeanRadius" in target_body.format_bundle_output_string(False)
        assert [value.strip() for value in target_body.parameter_list()] == ["MeanRadius"]
        assert bundle_settings.solve_target_body() is True
        assert bundle_settings.bundle_target_body().mean_radius().kilometers() == 1737.4

    assert ip.pixel_type_name(ip.PixelType.Real) == "Real"
    assert ip.byte_order_name(ip.ByteOrder.Lsb) == "Lsb"
    assert isinstance(ip.is_lsb(), bool)
    assert isinstance(ip.is_msb(), bool)

    angle = ip.Angle(180.0, ip.Angle.Units.Degrees)
    assert angle.degrees() == 180.0

    distance = ip.Distance(1.5, ip.Distance.Units.Kilometers)
    assert distance.meters() == 1500.0

    displacement = ip.Displacement(-2.0, ip.Displacement.Units.Meters)
    assert displacement.meters() == -2.0

    latitude = ip.Latitude(10.0, ip.Angle.Units.Degrees)
    longitude = ip.Longitude(20.0, ip.Angle.Units.Degrees)
    assert latitude.planetocentric(ip.Angle.Units.Degrees) == 10.0
    assert longitude.positive_east(ip.Angle.Units.Degrees) == 20.0

    stereo_x, stereo_y, stereo_z = ip.Stereo.spherical(0.0, 0.0, 1000.0)
    assert stereo_x == 1.0
    assert stereo_y == 0.0
    assert stereo_z == 0.0

    stereo_latitude, stereo_longitude, stereo_radius = ip.Stereo.rectangular(1.0, 0.0, 0.0)
    assert stereo_latitude == 0.0
    assert stereo_longitude == 0.0
    assert stereo_radius == 1.0

    blob = ip.Blob("SmokeBlob", "Blob")
    blob.set_data(b"XYZ")
    assert blob.name() == "SmokeBlob"
    assert blob.type() == "Blob"
    assert blob.get_buffer() == b"XYZ"
    assert ip.is_blob(blob.label()) is False
    assert ip.is_blob(ip.PvlObject("TABLE")) is True

    centroid = ip.Centroid()
    assert centroid.set_dn_range(1.0, 2.0) == 1
    assert "Centroid" in repr(centroid)

    filename = ip.FileName("$PWD/example.cub")
    assert filename.name() == "example.cub"
    assert filename.base_name() == "example"
    assert filename.extension() == "cub"

    camera_point_info = ip.CameraPointInfo()
    camera_point_info.set_csv_output(True)
    assert repr(camera_point_info) == "CameraPointInfo()"

    keyword = ip.PvlKeyword("InstrumentId", "HIRISE")
    group = ip.PvlGroup("Instrument")
    group.add_keyword(keyword)
    pvl = ip.Pvl()
    pvl.add_group(group)
    assert pvl.find_group("Instrument").find_keyword("InstrumentId")[0] == "HIRISE"

    surface_point = ip.SurfacePoint(
        ip.Latitude(5.0, ip.Angle.Units.Degrees),
        ip.Longitude(25.0, ip.Angle.Units.Degrees),
        ip.Distance(3396.19, ip.Distance.Units.Kilometers),
    )
    assert surface_point.valid()
    naif_coords = surface_point.to_naif_array()
    assert len(naif_coords) == 3
    assert surface_point.get_local_radius().kilometers() > 0.0


def test_high_level_process_objects_work():
    assert isinstance(ip.Environment.get_environment_value("PATH", ""), str)

    progress = ip.Progress()
    progress.set_text("Working")
    progress.set_maximum_steps(5)
    progress.add_steps(2)
    progress.disable_automatic_display()
    assert progress.text() == "Working"
    assert progress.maximum_steps() == 7
    progress.check_status()
    assert isinstance(progress.current_step(), int)

    process = ip.Process()
    process.propagate_labels(False)
    process.propagate_tables(False)
    process.propagate_polygons(False)
    process.propagate_history(False)
    process.propagate_original_label(False)
    assert isinstance(process.progress(), ip.Progress)

    by_brick = ip.ProcessByBrick()
    by_brick.set_wrap(True)
    by_brick.set_processing_direction(ip.ProcessByBrick.ProcessingDirection.BandsFirst)
    by_brick.set_output_requirements(ip.OneBand)
    by_brick.set_brick_size(2, 3, 1)
    by_brick.set_input_brick_size(2, 3, 1)
    by_brick.set_output_brick_size(2, 3, 1)
    assert by_brick.wraps() is True
    assert by_brick.get_processing_direction() == ip.ProcessByBrick.ProcessingDirection.BandsFirst

    by_line = ip.ProcessByLine()
    by_sample = ip.ProcessBySample()
    by_spectra = ip.ProcessBySpectra(ip.ProcessBySpectra.BySample)
    by_tile = ip.ProcessByTile()
    by_tile.set_tile_size(4, 4)
    assert by_spectra.type() == ip.ProcessBySpectra.BySample
    assert isinstance(by_line, ip.ProcessByBrick)
    assert isinstance(by_sample, ip.ProcessByBrick)
    assert isinstance(by_tile, ip.ProcessByBrick)

    with temporary_raw_input_file() as raw_input_path:
        importer = ip.ProcessImport()
        importer.set_input_file(str(raw_input_path))
        importer.set_pixel_type(ip.PixelType.UnsignedWord)
        importer.set_dimensions(16, 8, 2)
        importer.set_byte_order(ip.ByteOrder.Lsb)
        importer.set_organization(ip.ProcessImport.Interleave.BSQ)
        importer.set_file_header_bytes(64)
        importer.set_data_prefix_bytes(8)
        importer.set_base(1.0)
        importer.set_multiplier([2.0, 3.0])
        importer.set_null(-1.0, -1.0)
        assert importer.input_file() == str(raw_input_path)
        assert importer.pixel_type() == ip.PixelType.UnsignedWord
        assert importer.samples() == 16
        assert importer.lines() == 8
        assert importer.bands() == 2
        assert importer.byte_order() == ip.ByteOrder.Lsb
        assert importer.organization() == ip.ProcessImport.Interleave.BSQ
        assert importer.file_header_bytes() == 64
        assert importer.data_prefix_bytes() == 8
        assert isinstance(importer.test_pixel(5.0), float)

    fits_import = ip.ProcessImportFits()
    fits_group = ip.PvlGroup("FitsHeader")
    fits_group.add_keyword(ip.PvlKeyword("INSTRUME", "HIRISE"))
    instrument_group = fits_import.standard_instrument_group(fits_group)
    assert isinstance(instrument_group, ip.PvlGroup)

    pds_import = ip.ProcessImportPds()
    assert isinstance(pds_import.is_isis2(), bool)
    pds_import.omit_original_label()

    vicar_import = ip.ProcessImportVicar()
    assert isinstance(vicar_import, ip.ProcessImport)

    boxcar = ip.ProcessByBoxcar()
    boxcar.set_boxcar_size(3, 3)

    quick_filter = ip.ProcessByQuickFilter()
    quick_filter.set_filter_parameters(5, 5, -10.0, 10.0, 3)


def test_statistics_and_low_level_objects_work():
    stats = ip.Statistics()
    stats.add_data([1.0, 2.0, 3.0, 4.0])
    assert stats.valid_pixels() == 4
    assert stats.average() == 2.5
    assert stats.minimum() == 1.0
    assert stats.maximum() == 4.0

    hist = ip.Histogram(0.0, 10.0, 5)
    hist.add_data([0.5, 1.5, 2.5, 9.5])
    assert hist.bins() == 5
    assert hist.valid_pixels() == 4
    low, high = hist.bin_range(0)
    assert low <= 0.5 <= high

    dist = ip.GaussianDistribution(0.0, 1.0)
    assert dist.mean() == 0.0
    assert dist.distribution_standard_deviation() == 1.0

    grouped = ip.GroupedStatistics()
    grouped.add_statistic("residual", 1.0)
    grouped.add_statistic("residual", 3.0)
    assert "residual" in grouped.get_statistic_types()
    assert grouped.get_statistics("residual").valid_pixels() == 2

    multi = ip.MultivariateStatistics()
    multi.add_data([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
    assert multi.valid_pixels() == 3
    assert multi.correlation() > 0.99

    filt = ip.VecFilter()
    assert len(filt.low_pass([1.0, 2.0, 3.0, 4.0, 5.0], 3)) == 5

    buffer = ip.Buffer(2, 2, 1, ip.PixelType.Real)
    buffer[0] = 1.5
    buffer[1] = 2.5
    assert len(buffer) == 4
    assert buffer.sample_dimension() == 2
    assert buffer.line_dimension() == 2
    assert buffer.band_dimension() == 1
    assert buffer.double_buffer()[0] == 1.5

    portal = ip.Portal(3, 3, ip.PixelType.Real)
    portal.set_hot_spot(0.0, 0.0)
    portal.set_position(10.0, 20.0, 1)
    assert portal.sample() == 10
    assert portal.line() == 20

    alpha = ip.AlphaCube(100, 200, 100, 200)
    assert alpha.alpha_samples() == 100
    assert alpha.alpha_lines() == 200
    assert isinstance(alpha.alpha_sample(1.0), float)
    assert isinstance(alpha.beta_line(10.0), float)

    field_value = ip.TableField("Value", ip.TableField.Type.Double)
    field_value.set_value(3.5)
    assert field_value.value() == 3.5

    field_name = ip.TableField("Name", ip.TableField.Type.Text, 8)
    field_name.set_value("MARS")
    assert field_name.value() == "MARS"

    record = ip.TableRecord()
    record.add_field(field_value)
    record.add_field(field_name)
    assert len(record) == 2
    assert record["Value"].value() == 3.5
    assert record[1].value() == "MARS"

    table = ip.Table("Example", record)
    table.add_record(record)
    assert len(table) == 1
    assert table[0]["Name"].value() == "MARS"
    assert "Value" in table.to_string()


def test_shape_bindings_work():
    surface_point = ip.SurfacePoint(
        ip.Latitude(2.0, ip.Angle.Units.Degrees),
        ip.Longitude(30.0, ip.Angle.Units.Degrees),
        ip.Distance(3396.19, ip.Distance.Units.Kilometers),
    )

    ellipsoid = ip.EllipsoidShape()
    assert ellipsoid.name() == "Ellipsoid"
    assert not ellipsoid.is_dem()
    ellipsoid.set_surface_point(surface_point)
    assert ellipsoid.surface_intersection().valid()

    dem_shape = ip.DemShape()
    assert dem_shape.name() == "DemShape"
    assert dem_shape.is_dem()

    plane_shape = ip.PlaneShape()
    assert plane_shape.name() == "Plane"
    assert not plane_shape.is_dem()

    naif_shape = ip.NaifDskShape()
    assert naif_shape.name() == "DSK"
    assert not naif_shape.is_dem()

    embree_shape = ip.EmbreeShapeModel()
    assert embree_shape.name() == "Embree"
    assert not embree_shape.is_dem()
    embree_shape.set_tolerance(0.25)
    assert embree_shape.get_tolerance() == 0.25

    bullet_shape = ip.BulletShapeModel()
    assert bullet_shape.name() == "Bullet"
    assert not bullet_shape.is_dem()
    bullet_shape.set_tolerance(0.5)
    assert bullet_shape.get_tolerance() == 0.5


def test_target_and_shape_factory_bindings_work():
    label = make_sky_target_label()

    target = ip.Target(label)
    assert target.name() == "Sky"
    assert target.is_sky()
    assert target.shape() is not None
    assert target.shape().name() == "Ellipsoid"

    target.set_name("CustomSky")
    assert target.name() == "CustomSky"
    target.set_radii(
        [
            ip.Distance(1000.0, ip.Distance.Units.Meters),
            ip.Distance(1000.0, ip.Distance.Units.Meters),
            ip.Distance(1000.0, ip.Distance.Units.Meters),
        ]
    )
    assert len(target.radii()) == 3

    created_shape = ip.ShapeModelFactory.create(target, label)
    assert created_shape.name() == "Ellipsoid"

    assert ip.Target.lookup_naif_body_code("Mars") == 499
    mapping_group = ip.PvlGroup("Mapping")
    mapping_group.add_keyword(ip.PvlKeyword("TargetName", "Mars"))
    mapping_group.add_keyword(ip.PvlKeyword("EquatorialRadius", "3396190.0"))
    mapping_group.add_keyword(ip.PvlKeyword("PolarRadius", "3376200.0"))
    radii_group = ip.Target.radii_group_from_label(ip.Pvl(), mapping_group)
    assert radii_group.find_keyword("TargetName")[0] == "Mars"
    assert radii_group.has_keyword("EquatorialRadius")
    assert radii_group.has_keyword("PolarRadius")


def test_lower_level_shape_support_bindings_work():
    plate = ip.TriangularPlate(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        7,
    )
    assert plate.id() == 7
    assert plate.name() == "TriangularPlate"
    assert len(plate.center()) == 3
    assert plate.area() > 0.0
    assert plate.vertex(0) == [1.0, 0.0, 0.0]
    assert plate.has_intercept([2.0, 2.0, 2.0], [-1.0, -1.0, -1.0])

    plate_intercept = plate.intercept([2.0, 2.0, 2.0], [-1.0, -1.0, -1.0])
    assert plate_intercept is not None
    assert plate_intercept.is_valid()
    assert plate_intercept.shape().name() == "TriangularPlate"

    intercept = ip.Intercept()
    assert not intercept.is_valid()

    dsk_model = ip.NaifDskPlateModel()
    assert not dsk_model.is_valid()
    assert dsk_model.filename() == ""
    assert dsk_model.number_plates() == 0
    assert dsk_model.number_vertices() == 0

    embree_target_shape = ip.EmbreeTargetShape()
    assert not embree_target_shape.is_valid()
    assert embree_target_shape.number_of_polygons() == 0
    assert embree_target_shape.number_of_vertices() == 0

    embree_manager = ip.EmbreeTargetManager.instance()
    original_max_cache_size = embree_manager.max_cache_size()
    embree_manager.set_max_cache_size(3)
    assert embree_manager.max_cache_size() == 3
    assert embree_manager.current_cache_size() >= 0
    embree_manager.set_max_cache_size(original_max_cache_size)

    bullet_target_shape = ip.BulletTargetShape()
    assert bullet_target_shape.name() == ""
    assert bullet_target_shape.maximum_distance() == 0.0

    bullet_world = ip.BulletWorldManager("PyWorld")
    assert bullet_world.name() == "PyWorld"
    assert bullet_world.size() == 0


def test_projection_bindings_work():
    label = make_simple_cylindrical_label()

    proj = ip.SimpleCylindrical(label)
    assert proj.name() == "SimpleCylindrical"
    assert proj.version()
    assert proj.set_universal_ground(0.0, 220.0)
    assert proj.is_good()
    assert proj.is_equatorial_cylindrical()
    xy_range = proj.xy_range()
    assert xy_range is not None
    assert len(xy_range) == 4

    created = ip.ProjectionFactory.create(label)
    assert created.name() == "SimpleCylindrical"
    assert created.set_universal_ground(1.0, 221.0)
    assert created.mapping().find_keyword("ProjectionName")[0] == "SimpleCylindrical"

    ring_label = make_ring_cylindrical_label()
    ring_proj = ip.RingCylindrical(ring_label)
    assert ring_proj.name() == "RingCylindrical"
    assert ring_proj.set_universal_ground(150000.0, 20.0)
    assert ring_proj.is_good()
    assert ring_proj.ring_longitude_direction_string() == "CounterClockwise"


if __name__ == "__main__":
    test_basic_symbols_present()
    test_basic_base_objects_work()
    test_high_level_process_objects_work()
    test_statistics_and_low_level_objects_work()
    test_projection_bindings_work()
    test_shape_bindings_work()
    test_target_and_shape_factory_bindings_work()
    test_lower_level_shape_support_bindings_work()
    print("smoke import ok")
