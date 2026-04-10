// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added camera detector, focal-plane, distortion, ground, sky, and line-scan map bindings
// Updated: 2026-04-10  Geng Xun added PushFrameCameraDetectorMap, RollingShutterCameraDetectorMap, VariableLineScanCameraDetectorMap bindings
// Purpose: pybind11 bindings for ISIS camera map helper classes that translate between detector, focal-plane, ground, and sky coordinate systems

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <utility>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CameraDetectorMap.h"
#include "CameraDistortionMap.h"
#include "CameraFocalPlaneMap.h"
#include "CameraGroundMap.h"
#include "CameraSkyMap.h"
#include "Distance.h"
#include "Latitude.h"
#include "LineScanCameraDetectorMap.h"
#include "LineScanCameraGroundMap.h"
#include "LineScanCameraSkyMap.h"
#include "Longitude.h"
#include "PushFrameCameraDetectorMap.h"
#include "RollingShutterCameraDetectorMap.h"
#include "SurfacePoint.h"
#include "VariableLineScanCameraDetectorMap.h"

namespace py = pybind11;

namespace {
std::vector<double> coefficients_to_vector(const double *coefficients) {
  return std::vector<double>(coefficients, coefficients + 3);
}
}  // namespace

void bind_camera_maps(py::module_ &m) {
  py::class_<Isis::CameraDistortionMap> distortion_map(m, "CameraDistortionMap");

  distortion_map
      .def("set_distortion", &Isis::CameraDistortionMap::SetDistortion, py::arg("naif_ik_code"))
      .def("set_focal_plane",
           &Isis::CameraDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::CameraDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"))
      .def("optical_distortion_coefficients", &Isis::CameraDistortionMap::OpticalDistortionCoefficients)
      .def("z_direction", &Isis::CameraDistortionMap::ZDirection)
      .def("focal_plane_x", &Isis::CameraDistortionMap::FocalPlaneX)
      .def("focal_plane_y", &Isis::CameraDistortionMap::FocalPlaneY)
      .def("undistorted_focal_plane_x", &Isis::CameraDistortionMap::UndistortedFocalPlaneX)
      .def("undistorted_focal_plane_y", &Isis::CameraDistortionMap::UndistortedFocalPlaneY)
      .def("undistorted_focal_plane_z", &Isis::CameraDistortionMap::UndistortedFocalPlaneZ);

  py::class_<Isis::CameraDetectorMap> detector_map(m, "CameraDetectorMap");

  detector_map
      .def("set_parent",
           py::overload_cast<const double, const double>(&Isis::CameraDetectorMap::SetParent),
           py::arg("sample"), py::arg("line"))
      .def("set_parent_with_time_offset",
           py::overload_cast<const double, const double, const double>(&Isis::CameraDetectorMap::SetParent),
           py::arg("sample"), py::arg("line"), py::arg("delta_t"))
      .def("set_detector",
           &Isis::CameraDetectorMap::SetDetector,
           py::arg("sample"),
           py::arg("line"))
      .def("adjusted_starting_sample", &Isis::CameraDetectorMap::AdjustedStartingSample)
      .def("adjusted_starting_line", &Isis::CameraDetectorMap::AdjustedStartingLine)
      .def("parent_sample", &Isis::CameraDetectorMap::ParentSample)
      .def("parent_line", &Isis::CameraDetectorMap::ParentLine)
      .def("detector_sample", &Isis::CameraDetectorMap::DetectorSample)
      .def("detector_line", &Isis::CameraDetectorMap::DetectorLine)
      .def("set_starting_detector_sample", &Isis::CameraDetectorMap::SetStartingDetectorSample, py::arg("sample"))
      .def("set_starting_detector_line", &Isis::CameraDetectorMap::SetStartingDetectorLine, py::arg("line"))
      .def("set_detector_sample_summing", &Isis::CameraDetectorMap::SetDetectorSampleSumming, py::arg("summing"))
      .def("set_detector_line_summing", &Isis::CameraDetectorMap::SetDetectorLineSumming, py::arg("summing"))
      .def("sample_scale_factor", &Isis::CameraDetectorMap::SampleScaleFactor)
      .def("line_scale_factor", &Isis::CameraDetectorMap::LineScaleFactor)
      .def("line_rate", &Isis::CameraDetectorMap::LineRate)
      .def("exposure_duration",
           &Isis::CameraDetectorMap::exposureDuration,
           py::arg("sample"),
           py::arg("line"),
           py::arg("band"));

  py::class_<Isis::CameraFocalPlaneMap> focal_plane_map(m, "CameraFocalPlaneMap");

  py::enum_<Isis::CameraFocalPlaneMap::FocalPlaneXDependencyType>(focal_plane_map, "FocalPlaneXDependencyType")
      .value("Sample", Isis::CameraFocalPlaneMap::Sample)
      .value("Line", Isis::CameraFocalPlaneMap::Line);

  focal_plane_map
      .def("set_detector",
           &Isis::CameraFocalPlaneMap::SetDetector,
           py::arg("sample"),
           py::arg("line"))
      .def("set_focal_plane",
           &Isis::CameraFocalPlaneMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("focal_plane_x", &Isis::CameraFocalPlaneMap::FocalPlaneX)
      .def("focal_plane_y", &Isis::CameraFocalPlaneMap::FocalPlaneY)
      .def("detector_sample", &Isis::CameraFocalPlaneMap::DetectorSample)
      .def("detector_line", &Isis::CameraFocalPlaneMap::DetectorLine)
      .def("centered_detector_sample", &Isis::CameraFocalPlaneMap::CenteredDetectorSample)
      .def("centered_detector_line", &Isis::CameraFocalPlaneMap::CenteredDetectorLine)
      .def("set_detector_origin",
           &Isis::CameraFocalPlaneMap::SetDetectorOrigin,
           py::arg("sample"),
           py::arg("line"))
      .def("detector_line_origin", &Isis::CameraFocalPlaneMap::DetectorLineOrigin)
      .def("detector_sample_origin", &Isis::CameraFocalPlaneMap::DetectorSampleOrigin)
      .def("set_detector_offset",
           &Isis::CameraFocalPlaneMap::SetDetectorOffset,
           py::arg("sample_offset"),
           py::arg("line_offset"))
      .def("detector_line_offset", &Isis::CameraFocalPlaneMap::DetectorLineOffset)
      .def("detector_sample_offset", &Isis::CameraFocalPlaneMap::DetectorSampleOffset)
      .def("trans_l", [](const Isis::CameraFocalPlaneMap &self) { return coefficients_to_vector(self.TransL()); })
      .def("trans_s", [](const Isis::CameraFocalPlaneMap &self) { return coefficients_to_vector(self.TransS()); })
      .def("trans_x", [](const Isis::CameraFocalPlaneMap &self) { return coefficients_to_vector(self.TransX()); })
      .def("trans_y", [](const Isis::CameraFocalPlaneMap &self) { return coefficients_to_vector(self.TransY()); })
      .def("focal_plane_x_dependency", &Isis::CameraFocalPlaneMap::FocalPlaneXDependency)
      .def("sign_most_sig_x", &Isis::CameraFocalPlaneMap::SignMostSigX)
      .def("sign_most_sig_y", &Isis::CameraFocalPlaneMap::SignMostSigY);

  py::class_<Isis::CameraGroundMap> ground_map(m, "CameraGroundMap");

  py::enum_<Isis::CameraGroundMap::PartialType>(ground_map, "PartialType")
      .value("WRT_Latitude", Isis::CameraGroundMap::WRT_Latitude)
      .value("WRT_Longitude", Isis::CameraGroundMap::WRT_Longitude)
      .value("WRT_Radius", Isis::CameraGroundMap::WRT_Radius)
      .value("WRT_MajorAxis", Isis::CameraGroundMap::WRT_MajorAxis)
      .value("WRT_MinorAxis", Isis::CameraGroundMap::WRT_MinorAxis)
      .value("WRT_PolarAxis", Isis::CameraGroundMap::WRT_PolarAxis);

  ground_map
      .def("set_focal_plane",
           &Isis::CameraGroundMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"))
      .def("set_ground",
           py::overload_cast<const Isis::Latitude &, const Isis::Longitude &>(&Isis::CameraGroundMap::SetGround),
           py::arg("latitude"),
           py::arg("longitude"))
      .def("set_ground_surface_point",
           py::overload_cast<const Isis::SurfacePoint &>(&Isis::CameraGroundMap::SetGround),
           py::arg("surface_point"))
      .def("get_xy",
           [](Isis::CameraGroundMap &self, const Isis::SurfacePoint &surface_point, bool test) {
             double cudx = 0.0;
             double cudy = 0.0;
             bool success = self.GetXY(surface_point, &cudx, &cudy, test);
             return py::make_tuple(success, cudx, cudy);
           },
           py::arg("surface_point"),
           py::arg("test") = true)
      .def("focal_plane_x", &Isis::CameraGroundMap::FocalPlaneX)
      .def("focal_plane_y", &Isis::CameraGroundMap::FocalPlaneY);

  py::class_<Isis::CameraSkyMap> sky_map(m, "CameraSkyMap");

  sky_map
      .def("set_focal_plane",
           &Isis::CameraSkyMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"))
      .def("set_sky",
           &Isis::CameraSkyMap::SetSky,
           py::arg("right_ascension"),
           py::arg("declination"))
      .def("focal_plane_x", &Isis::CameraSkyMap::FocalPlaneX)
      .def("focal_plane_y", &Isis::CameraSkyMap::FocalPlaneY);

  py::class_<Isis::LineScanCameraDetectorMap, Isis::CameraDetectorMap>(m, "LineScanCameraDetectorMap")
      .def(py::init<Isis::Camera *, const double, const double>(),
           py::arg("parent") = nullptr,
           py::arg("et_start"),
           py::arg("line_rate"))
      .def("set_start_time", &Isis::LineScanCameraDetectorMap::SetStartTime, py::arg("et_start"))
      .def("set_line_rate", &Isis::LineScanCameraDetectorMap::SetLineRate, py::arg("line_rate"))
      .def("line_rate", &Isis::LineScanCameraDetectorMap::LineRate)
      .def("start_time", &Isis::LineScanCameraDetectorMap::StartTime)
      .def("exposure_duration",
           &Isis::LineScanCameraDetectorMap::exposureDuration,
           py::arg("sample"),
           py::arg("line"),
           py::arg("band"));

  py::class_<Isis::LineScanCameraGroundMap, Isis::CameraGroundMap>(m, "LineScanCameraGroundMap");
  py::class_<Isis::LineScanCameraSkyMap, Isis::CameraSkyMap>(m, "LineScanCameraSkyMap");

  // ── PushFrameCameraDetectorMap ──────────────────────────────────────────────
  // Added: 2026-04-10 - expose PushFrameCameraDetectorMap for push-frame detector mapping.
  py::class_<Isis::PushFrameCameraDetectorMap, Isis::CameraDetectorMap>(m, "PushFrameCameraDetectorMap")
      .def(py::init<Isis::Camera *, const double, const double, int>(),
           py::arg("parent"),
           py::arg("et_start"),
           py::arg("framelet_rate"),
           py::arg("framelet_height"),
           py::keep_alive<1, 2>(),
           "Construct a PushFrameCameraDetectorMap for a push-frame camera.")
      .def("set_parent",
           py::overload_cast<const double, const double>(&Isis::PushFrameCameraDetectorMap::SetParent),
           py::arg("sample"),
           py::arg("line"),
           "Convert parent image coordinates to detector coordinates.")
      .def("set_detector",
           &Isis::PushFrameCameraDetectorMap::SetDetector,
           py::arg("sample"),
           py::arg("line"),
           "Convert detector coordinates to parent image coordinates.")
      .def("framelet_rate",    &Isis::PushFrameCameraDetectorMap::FrameletRate,
           "Return the framelet rate (seconds per framelet).")
      .def("set_framelet_rate",&Isis::PushFrameCameraDetectorMap::SetFrameletRate,
           py::arg("framelet_rate"),
           "Set the framelet rate.")
      .def("framelet_offset",  &Isis::PushFrameCameraDetectorMap::FrameletOffset,
           "Return the current framelet offset.")
      .def("set_framelet_offset",&Isis::PushFrameCameraDetectorMap::SetFrameletOffset,
           py::arg("framelet_offset"),
           "Set the framelet offset.")
      .def("framelet",         &Isis::PushFrameCameraDetectorMap::Framelet,
           "Return the current framelet number.")
      .def("set_band_first_detector_line",
           &Isis::PushFrameCameraDetectorMap::SetBandFirstDetectorLine,
           py::arg("first_line"),
           "Set the first detector line for the current band.")
      .def("get_band_first_detector_line",
           &Isis::PushFrameCameraDetectorMap::GetBandFirstDetectorLine,
           "Return the first detector line for the current band.")
      .def("set_start_time",   &Isis::PushFrameCameraDetectorMap::SetStartTime,
           py::arg("et_start"),
           "Update the start ephemeris time.")
      .def("__repr__", [](const Isis::PushFrameCameraDetectorMap &) {
            return "PushFrameCameraDetectorMap()"; });

  // ── RollingShutterCameraDetectorMap ────────────────────────────────────────
  // Added: 2026-04-10 - expose RollingShutterCameraDetectorMap for rolling-shutter cameras.
  py::class_<Isis::RollingShutterCameraDetectorMap, Isis::CameraDetectorMap>(
        m, "RollingShutterCameraDetectorMap")
      .def(py::init<Isis::Camera *,
                    std::vector<double>,
                    std::vector<double>,
                    std::vector<double>>(),
           py::arg("parent"),
           py::arg("times"),
           py::arg("sample_coeffs"),
           py::arg("line_coeffs"),
           py::keep_alive<1, 2>(),
           "Construct a RollingShutterCameraDetectorMap with jitter correction coefficients.")
      .def("set_parent",
           py::overload_cast<const double, const double>(&Isis::RollingShutterCameraDetectorMap::SetParent),
           py::arg("sample"),
           py::arg("line"),
           "Convert parent image coordinates to detector coordinates.")
      .def("set_detector",
           &Isis::RollingShutterCameraDetectorMap::SetDetector,
           py::arg("sample"),
           py::arg("line"),
           "Convert detector coordinates to parent image coordinates.")
      .def("apply_jitter",
           [](Isis::RollingShutterCameraDetectorMap &self,
              double sample, double line) {
             return self.applyJitter(sample, line);
           },
           py::arg("sample"),
           py::arg("line"),
           "Apply rolling-shutter jitter correction. Returns (corrected_sample, corrected_line).")
      .def("__repr__", [](const Isis::RollingShutterCameraDetectorMap &) {
            return "RollingShutterCameraDetectorMap()"; });

  // ── VariableLineScanCameraDetectorMap ──────────────────────────────────────
  // Added: 2026-04-10 - expose VariableLineScanCameraDetectorMap for variable-rate line-scan cameras.
  // Note: The constructor takes std::vector<LineRateChange> by reference (lifetime managed by caller).
  py::class_<Isis::VariableLineScanCameraDetectorMap, Isis::LineScanCameraDetectorMap>(
        m, "VariableLineScanCameraDetectorMap")
      .def("set_parent",
           py::overload_cast<const double, const double>(&Isis::VariableLineScanCameraDetectorMap::SetParent),
           py::arg("sample"),
           py::arg("line"),
           "Convert parent image coordinates to detector coordinates.")
      .def("set_detector",
           &Isis::VariableLineScanCameraDetectorMap::SetDetector,
           py::arg("sample"),
           py::arg("line"),
           "Convert detector coordinates to parent image coordinates.")
      .def("exposure_duration",
           &Isis::VariableLineScanCameraDetectorMap::exposureDuration,
           py::arg("sample"),
           py::arg("line"),
           py::arg("band"),
           "Return the exposure duration for the given detector position.")
      .def("__repr__", [](const Isis::VariableLineScanCameraDetectorMap &) {
            return "VariableLineScanCameraDetectorMap()"; });
}