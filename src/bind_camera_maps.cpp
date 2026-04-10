// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added camera detector, focal-plane, distortion, ground, sky, and line-scan map bindings
// Updated: 2026-04-10  Geng Xun added PushFrameCameraDetectorMap, RollingShutterCameraDetectorMap, VariableLineScanCameraDetectorMap bindings
// Updated: 2026-04-10  Geng Xun added PushFrameCameraCcdLayout and FrameletInfo struct bindings
// Updated: 2026-04-10  Geng Xun added PushFrameCameraGroundMap, RadarSkyMap, IrregularBodyCameraGroundMap, CSMSkyMap bindings
// Updated: 2026-04-10  Geng Xun added RadarGroundRangeMap, ReseauDistortionMap, MarciDistortionMap bindings
// Updated: 2026-04-10  Geng Xun fixed QString-based constructor wrappers for FrameletInfo and ReseauDistortionMap.
// Updated: 2026-04-10  Geng Xun added RadarGroundMap and RadarPulseMap bindings
// Updated: 2026-04-10  Geng Xun added RadarSlantRangeMap binding
// Purpose: pybind11 bindings for ISIS camera map helper classes that translate between detector, focal-plane, ground, and sky coordinate systems

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <utility>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CSMCamera.h"
#include "CSMSkyMap.h"
#include "CameraDetectorMap.h"
#include "CameraDistortionMap.h"
#include "CameraFocalPlaneMap.h"
#include "CameraGroundMap.h"
#include "CameraSkyMap.h"
#include "Distance.h"
#include "IrregularBodyCameraGroundMap.h"
#include "Latitude.h"
#include "LineScanCameraDetectorMap.h"
#include "LineScanCameraGroundMap.h"
#include "LineScanCameraSkyMap.h"
#include "Longitude.h"
#include "MarciDistortionMap.h"
#include "Pvl.h"
#include "PushFrameCameraCcdLayout.h"
#include "PushFrameCameraDetectorMap.h"
#include "PushFrameCameraGroundMap.h"
#include "RadarGroundMap.h"
#include "RadarGroundRangeMap.h"
#include "RadarPulseMap.h"
#include "RadarSlantRangeMap.h"
#include "RadarSkyMap.h"
#include "ReseauDistortionMap.h"
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

  // PushFrameCameraCcdLayout::FrameletInfo — nested struct holding framelet layout data.
  // Added: 2026-04-10
  py::class_<Isis::PushFrameCameraCcdLayout::FrameletInfo>(m, "FrameletInfo")
      .def(py::init<>(),
           "Construct an empty FrameletInfo struct.")
      .def(py::init<int>(),
           py::arg("frame_id"),
           "Construct a FrameletInfo with the given frame ID.")
      .def(py::init([](int frameId,
                       const std::string &filterName,
                       int startSample,
                       int startLine,
                       int samples,
                       int lines) {
             return Isis::PushFrameCameraCcdLayout::FrameletInfo(
                 frameId,
                 QString::fromStdString(filterName),
                 startSample,
                 startLine,
                 samples,
                 lines);
           }),
           py::arg("frame_id"),
           py::arg("filter_name"),
           py::arg("start_sample"),
           py::arg("start_line"),
           py::arg("samples"),
           py::arg("lines"),
           "Construct a FrameletInfo with all fields.")
      .def_readwrite("frame_id", &Isis::PushFrameCameraCcdLayout::FrameletInfo::m_frameId,
                     "NAIF ID of the framelet.")
      .def_property("filter_name",
                    [](const Isis::PushFrameCameraCcdLayout::FrameletInfo &self) {
                      return self.m_filterName.toStdString();
                    },
                    [](Isis::PushFrameCameraCcdLayout::FrameletInfo &self,
                       const std::string &name) {
                      self.m_filterName = QString::fromStdString(name);
                    },
                    "Name of the filter for this framelet.")
      .def_readwrite("start_sample",
                     &Isis::PushFrameCameraCcdLayout::FrameletInfo::m_startSample,
                     "First sample of the framelet on the detector.")
      .def_readwrite("start_line",
                     &Isis::PushFrameCameraCcdLayout::FrameletInfo::m_startLine,
                     "First line of the framelet on the detector.")
      .def_readwrite("samples",
                     &Isis::PushFrameCameraCcdLayout::FrameletInfo::m_samples,
                     "Number of samples in the framelet.")
      .def_readwrite("lines",
                     &Isis::PushFrameCameraCcdLayout::FrameletInfo::m_lines,
                     "Number of lines in the framelet.")
      .def("__repr__",
           [](const Isis::PushFrameCameraCcdLayout::FrameletInfo &fi) {
             return "<FrameletInfo id=" + std::to_string(fi.m_frameId)
                    + " filter='" + fi.m_filterName.toStdString() + "'"
                    + " start=(" + std::to_string(fi.m_startSample)
                    + "," + std::to_string(fi.m_startLine) + ")"
                    + " size=(" + std::to_string(fi.m_samples)
                    + "," + std::to_string(fi.m_lines) + ")>";
           });

  // PushFrameCameraCcdLayout — provides CCD layout information for push-frame cameras.
  // ccdSamples() and ccdLines() require SPICE kernels to be loaded.
  // Added: 2026-04-10
  py::class_<Isis::PushFrameCameraCcdLayout>(m, "PushFrameCameraCcdLayout")
      .def(py::init<>(),
           "Construct a PushFrameCameraCcdLayout with no CCD ID.")
      .def(py::init<int>(),
           py::arg("ccd_id"),
           "Construct a PushFrameCameraCcdLayout for the given CCD NAIF ID.")
      .def("add_kernel",
           [](Isis::PushFrameCameraCcdLayout &self, const std::string &kernel) {
             return self.addKernel(QString::fromStdString(kernel));
           },
           py::arg("kernel"),
           "Add a SPICE kernel file path to the kernel manager.\n\n"
           "Returns True if the kernel was successfully added.")
      .def("ccd_samples", &Isis::PushFrameCameraCcdLayout::ccdSamples,
           "Return the number of samples on the CCD (requires SPICE kernels).")
      .def("ccd_lines", &Isis::PushFrameCameraCcdLayout::ccdLines,
           "Return the number of lines on the CCD (requires SPICE kernels).")
      .def("get_frame_info",
           [](const Isis::PushFrameCameraCcdLayout &self,
              int frame_id,
              const std::string &name) {
             return self.getFrameInfo(frame_id, QString::fromStdString(name));
           },
           py::arg("frame_id"),
           py::arg("name") = "",
           "Return the FrameletInfo for the given frame ID and optional filter name.")
      .def("__repr__", [](const Isis::PushFrameCameraCcdLayout &) {
        return "<PushFrameCameraCcdLayout>";
      });

  // PushFrameCameraGroundMap — converts between undistorted focal plane and ground
  // coordinates for push-frame cameras, handling even/odd framelet switching.
  // Added: 2026-04-10
  py::class_<Isis::PushFrameCameraGroundMap, Isis::CameraGroundMap>(
      m, "PushFrameCameraGroundMap")
      .def(py::init<Isis::Camera *, bool>(),
           py::arg("camera"),
           py::arg("even_framelets"),
           py::keep_alive<1, 2>(),
           "Construct a PushFrameCameraGroundMap.\n\n"
           "Parameters\n"
           "----------\n"
           "camera : Camera\n"
           "    Parent camera.\n"
           "even_framelets : bool\n"
           "    True if the image contains even framelets.")
      .def("set_ground",
           py::overload_cast<const Isis::Latitude &, const Isis::Longitude &>(
               &Isis::PushFrameCameraGroundMap::SetGround),
           py::arg("lat"),
           py::arg("lon"),
           "Set ground position from latitude and longitude.")
      .def("set_ground",
           py::overload_cast<const Isis::SurfacePoint &>(
               &Isis::PushFrameCameraGroundMap::SetGround),
           py::arg("surface_point"),
           "Set ground position from a SurfacePoint.")
      .def("__repr__", [](const Isis::PushFrameCameraGroundMap &) {
        return "<PushFrameCameraGroundMap>";
      });

  // RadarSkyMap — sky map for Radar cameras. SetSky always returns false
  // because radar cannot paint a star.
  // Added: 2026-04-10
  py::class_<Isis::RadarSkyMap, Isis::CameraSkyMap>(m, "RadarSkyMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("camera"),
           py::keep_alive<1, 2>(),
           "Construct a RadarSkyMap for the given Camera.")
      .def("set_focal_plane",
           &Isis::RadarSkyMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"),
           "Set the focal-plane position from unit direction vector.")
      .def("set_sky",
           &Isis::RadarSkyMap::SetSky,
           py::arg("ra"),
           py::arg("dec"),
           "Set sky coordinates from RA/Dec. Always returns False for Radar.")
      .def("__repr__", [](const Isis::RadarSkyMap &) {
        return "<RadarSkyMap>";
      });

  // IrregularBodyCameraGroundMap — ground map for irregular bodies that skips
  // the emission-angle back-of-planet test.
  // Added: 2026-04-10
  py::class_<Isis::IrregularBodyCameraGroundMap, Isis::CameraGroundMap>(
      m, "IrregularBodyCameraGroundMap")
      .def(py::init<Isis::Camera *, bool>(),
           py::arg("camera"),
           py::arg("clip_emission_angles") = false,
           py::keep_alive<1, 2>(),
           "Construct an IrregularBodyCameraGroundMap.\n\n"
           "Parameters\n"
           "----------\n"
           "camera : Camera\n"
           "    Parent camera.\n"
           "clip_emission_angles : bool, optional\n"
           "    Whether to apply emission-angle clipping (default: False).")
      .def("get_xy",
           [](Isis::IrregularBodyCameraGroundMap &self,
              const Isis::SurfacePoint &sp) {
             double cudx = 0.0, cudy = 0.0;
             bool ok = self.GetXY(sp, &cudx, &cudy);
             return py::make_tuple(ok, cudx, cudy);
           },
           py::arg("surface_point"),
           "Get the undistorted focal-plane (x, y) position for a SurfacePoint.\n\n"
           "Returns\n"
           "-------\n"
           "tuple of (bool, float, float)\n"
           "    (success, x_mm, y_mm)")
      .def("__repr__", [](const Isis::IrregularBodyCameraGroundMap &) {
        return "<IrregularBodyCameraGroundMap>";
      });

  // CSMSkyMap — sky map for Community Sensor Model cameras.
  // SetSky computes the sky position using the CSM model.
  // Added: 2026-04-10
  py::class_<Isis::CSMSkyMap, Isis::CameraSkyMap>(m, "CSMSkyMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("camera"),
           py::keep_alive<1, 2>(),
           "Construct a CSMSkyMap for the given Camera.")
      .def("set_sky",
           &Isis::CSMSkyMap::SetSky,
           py::arg("ra"),
           py::arg("dec"),
           "Set sky coordinates from RA/Dec using the CSM model.")
      .def("__repr__", [](const Isis::CSMSkyMap &) {
        return "<CSMSkyMap>";
      });

  // Radar::LookDirection enum — used by RadarGroundRangeMap::setTransform.
  // Added: 2026-04-10
  py::enum_<Isis::Radar::LookDirection>(m, "RadarLookDirection")
      .value("Left",  Isis::Radar::Left)
      .value("Right", Isis::Radar::Right)
      .export_values();

  // RadarGroundRangeMap — maps between image sample and Radar ground range using
  // NAIF IK-stored constants.
  // Added: 2026-04-10
  py::class_<Isis::RadarGroundRangeMap, Isis::CameraFocalPlaneMap>(
      m, "RadarGroundRangeMap")
      .def(py::init<Isis::Camera *, int>(),
           py::arg("camera"),
           py::arg("naif_ik_code"),
           py::keep_alive<1, 2>(),
           "Construct a RadarGroundRangeMap for the given Camera and NAIF IK code.")
      .def_static("set_transform",
                  [](int naif_ik_code,
                     double ground_range_resolution,
                     int samples,
                     Isis::Radar::LookDirection ldir) {
                    Isis::RadarGroundRangeMap::setTransform(
                        naif_ik_code, ground_range_resolution, samples, ldir);
                  },
                  py::arg("naif_ik_code"),
                  py::arg("ground_range_resolution"),
                  py::arg("samples"),
                  py::arg("look_direction"),
                  "Store the ground-range transform constants in the NAIF kernel pool.")
      .def("__repr__", [](const Isis::RadarGroundRangeMap &) {
        return "<RadarGroundRangeMap>";
      });

  // ReseauDistortionMap — distortion map using reseau mark positions.
  // Added: 2026-04-10
  py::class_<Isis::ReseauDistortionMap, Isis::CameraDistortionMap>(
      m, "ReseauDistortionMap")
       .def(py::init([](Isis::Camera *camera,
                            Isis::Pvl &labels,
                            const std::string &filename) {
                return new Isis::ReseauDistortionMap(
                     camera,
                     labels,
                     QString::fromStdString(filename));
             }),
           py::arg("camera"),
           py::arg("labels"),
           py::arg("filename"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Construct a ReseauDistortionMap.\n\n"
           "Parameters\n"
           "----------\n"
           "camera : Camera\n"
           "    Parent camera.\n"
           "labels : Pvl\n"
           "    Cube labels containing reseau mark data.\n"
           "filename : str\n"
           "    Path to the reseau correction file.")
      .def("set_focal_plane",
           &Isis::ReseauDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map from distorted to undistorted focal-plane coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::ReseauDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map from undistorted to distorted focal-plane coordinates.")
      .def("__repr__", [](const Isis::ReseauDistortionMap &) {
        return "<ReseauDistortionMap>";
      });

  // MarciDistortionMap — distortion map for MARCI camera on MRO.
  // Added: 2026-04-10
  py::class_<Isis::MarciDistortionMap, Isis::CameraDistortionMap>(
      m, "MarciDistortionMap")
      .def(py::init<Isis::Camera *, int>(),
           py::arg("camera"),
           py::arg("naif_ik_code"),
           py::keep_alive<1, 2>(),
           "Construct a MarciDistortionMap for the given Camera and NAIF IK code.")
      .def("set_focal_plane",
           &Isis::MarciDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map from distorted to undistorted focal-plane coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::MarciDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map from undistorted to distorted focal-plane coordinates.")
      .def("set_filter",
           &Isis::MarciDistortionMap::SetFilter,
           py::arg("filter"),
           "Set the MARCI filter index (0-based).")
      .def("__repr__", [](const Isis::MarciDistortionMap &) {
        return "<MarciDistortionMap>";
      });

  // RadarGroundMap — maps between undistorted focal-plane coordinate (slant
  // range) and ground lat/lon for Radar instruments.
  // Added: 2026-04-10
  py::class_<Isis::RadarGroundMap, Isis::CameraGroundMap>(m, "RadarGroundMap")
      .def(py::init<Isis::Camera *,
                    Isis::Radar::LookDirection,
                    double>(),
           py::arg("parent"),
           py::arg("look_direction"),
           py::arg("wave_length"),
           py::keep_alive<1, 2>(),
           "Construct a RadarGroundMap.")
      .def("set_focal_plane",
           &Isis::RadarGroundMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"),
           "Compute ground lat/lon from undistorted focal-plane coordinates.")
      .def("set_ground",
           py::overload_cast<const Isis::Latitude &,
                             const Isis::Longitude &>(
               &Isis::RadarGroundMap::SetGround),
           py::arg("lat"),
           py::arg("lon"),
           "Compute focal-plane coordinates from ground lat/lon.")
      .def("set_ground",
           py::overload_cast<const Isis::SurfacePoint &>(
               &Isis::RadarGroundMap::SetGround),
           py::arg("surface_point"),
           "Compute focal-plane coordinates from a SurfacePoint.")
      .def("set_range_sigma",
           &Isis::RadarGroundMap::SetRangeSigma,
           py::arg("range_sigma"),
           "Set the range sigma.")
      .def("range_sigma",
           &Isis::RadarGroundMap::RangeSigma,
           "Return the range sigma.")
      .def("set_doppler_sigma",
           &Isis::RadarGroundMap::SetDopplerSigma,
           py::arg("doppler_sigma"),
           "Set the Doppler sigma.")
      .def("y_scale",
           &Isis::RadarGroundMap::YScale,
           "Return the Doppler sigma.")
      .def("wave_length",
           &Isis::RadarGroundMap::WaveLength,
           "Return the radar wavelength.")
      .def("__repr__", [](const Isis::RadarGroundMap &) {
        return "<RadarGroundMap>";
      });

  // RadarPulseMap — detector map between alpha image coordinates and radar
  // pulse (sample, time) coordinates for radar instruments.
  // Added: 2026-04-10
  py::class_<Isis::RadarPulseMap, Isis::CameraDetectorMap>(m, "RadarPulseMap")
      .def(py::init<Isis::Camera *, double, double>(),
           py::arg("parent"),
           py::arg("et_start"),
           py::arg("line_rate"),
           py::keep_alive<1, 2>(),
           "Construct a RadarPulseMap.")
      .def("set_start_time",
           &Isis::RadarPulseMap::SetStartTime,
           py::arg("et_start"),
           "Reset the starting ephemeris time.")
      .def("set_line_rate",
           &Isis::RadarPulseMap::SetLineRate,
           py::arg("line_rate"),
           "Reset the time between lines.")
      .def("line_rate",
           &Isis::RadarPulseMap::LineRate,
           "Return the time in seconds between scan lines.")
      .def("set_x_axis_time_dependent",
           &Isis::RadarPulseMap::SetXAxisTimeDependent,
           py::arg("on"),
           "Set whether x (sample) is the time-dependent axis instead of y (line).")
      .def("__repr__", [](const Isis::RadarPulseMap &) {
        return "<RadarPulseMap>";
      });

  // RadarSlantRangeMap — maps between radar ground range and slant range
  // using stored polynomial coefficients.
  // Added: 2026-04-10
  py::class_<Isis::RadarSlantRangeMap, Isis::CameraDistortionMap>(
      m, "RadarSlantRangeMap")
      .def(py::init<Isis::Camera *, double>(),
           py::arg("parent"),
           py::arg("ground_range_resolution"),
           py::keep_alive<1, 2>(),
           "Construct a RadarSlantRangeMap.")
      .def("set_focal_plane",
           &Isis::RadarSlantRangeMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map from distorted to undistorted focal-plane (ground to slant range).")
      .def("set_undistorted_focal_plane",
           &Isis::RadarSlantRangeMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map from undistorted to distorted focal-plane (slant to ground range).")
      .def("set_coefficients",
           &Isis::RadarSlantRangeMap::SetCoefficients,
           py::arg("keyword"),
           "Set the slant-range polynomial coefficients from a PvlKeyword.")
      .def("set_weight_factors",
           &Isis::RadarSlantRangeMap::SetWeightFactors,
           py::arg("range_sigma"),
           py::arg("doppler_sigma"),
           "Set weight factors for range and Doppler residuals.")
      .def("__repr__", [](const Isis::RadarSlantRangeMap &) {
        return "<RadarSlantRangeMap>";
      });
}