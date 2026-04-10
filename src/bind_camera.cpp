// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-04-08  Geng Xun added CameraPointInfo bindings alongside core Camera geometry accessors
// Updated: 2026-04-09  Geng Xun exposed Camera.target() so Python can inspect attached Target metadata and frame coefficients
// Updated: 2026-04-10  Geng Xun fixed Quaternion scalar multiplication binding to avoid calling a non-const ISIS operator on a const reference.
// Updated: 2026-04-10  Geng Xun added PixelFOV binding exposing latLonVertices.
// Purpose: pybind11 bindings for the ISIS Camera base class, CameraPointInfo helper, and shared camera-side geometry accessors

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Camera.h"
#include "CameraDetectorMap.h"
#include "CameraDistortionMap.h"
#include "CameraFocalPlaneMap.h"
#include "CameraGroundMap.h"
#include "CameraPointInfo.h"
#include "CameraSkyMap.h"
#include "LightTimeCorrectionState.h"
#include "PixelFOV.h"
#include "PvlGroup.h"
#include "Quaternion.h"
#include "Sensor.h"
#include "Target.h"
#include "helpers.h"

namespace py = pybind11;

void bind_camera(py::module_ &m) {
     py::class_<Isis::CameraPointInfo>(m, "CameraPointInfo")
               .def(py::init<>())
               .def("set_cube",
                          [](Isis::CameraPointInfo &self, const std::string &cube_file_name) {
                               self.SetCube(stdStringToQString(cube_file_name));
                          },
                          py::arg("cube_file_name"))
               .def("set_csv_output", &Isis::CameraPointInfo::SetCSVOutput, py::arg("csv_output"))
               .def("set_image",
                          [](Isis::CameraPointInfo &self, double sample, double line, bool outside, bool error) {
                               return self.SetImage(sample, line, outside, error);
                          },
                          py::arg("sample"),
                          py::arg("line"),
                          py::arg("outside") = false,
                          py::arg("error") = false,
                          py::return_value_policy::take_ownership)
               .def("set_center",
                          [](Isis::CameraPointInfo &self, bool outside, bool error) {
                               return self.SetCenter(outside, error);
                          },
                          py::arg("outside") = false,
                          py::arg("error") = false,
                          py::return_value_policy::take_ownership)
               .def("set_sample",
                          [](Isis::CameraPointInfo &self, double sample, bool outside, bool error) {
                               return self.SetSample(sample, outside, error);
                          },
                          py::arg("sample"),
                          py::arg("outside") = false,
                          py::arg("error") = false,
                          py::return_value_policy::take_ownership)
               .def("set_line",
                          [](Isis::CameraPointInfo &self, double line, bool outside, bool error) {
                               return self.SetLine(line, outside, error);
                          },
                          py::arg("line"),
                          py::arg("outside") = false,
                          py::arg("error") = false,
                          py::return_value_policy::take_ownership)
               .def("set_ground",
                          [](Isis::CameraPointInfo &self, double latitude, double longitude, bool outside, bool error) {
                               return self.SetGround(latitude, longitude, outside, error);
                          },
                          py::arg("latitude"),
                          py::arg("longitude"),
                          py::arg("outside") = false,
                          py::arg("error") = false,
                          py::return_value_policy::take_ownership)
               .def("__repr__", [](const Isis::CameraPointInfo &) { return "CameraPointInfo()"; });

  py::class_<Isis::Camera, Isis::Sensor> camera(m, "Camera");

  py::enum_<Isis::Camera::CameraType>(camera, "CameraType")
      .value("Framing", Isis::Camera::CameraType::Framing)
      .value("PushFrame", Isis::Camera::CameraType::PushFrame)
      .value("LineScan", Isis::Camera::CameraType::LineScan)
      .value("Radar", Isis::Camera::CameraType::Radar)
      .value("Point", Isis::Camera::CameraType::Point)
      .value("RollingShutter", Isis::Camera::CameraType::RollingShutter)
      .value("Csm", Isis::Camera::CameraType::Csm);

  camera
      .def("set_image",
           py::overload_cast<const double, const double>(&Isis::Camera::SetImage),
           py::arg("sample"), py::arg("line"))
      .def("set_image_with_time_offset",
           py::overload_cast<const double, const double, const double>(&Isis::Camera::SetImage),
           py::arg("sample"), py::arg("line"), py::arg("delta_t"))
      .def("set_universal_ground",
           py::overload_cast<const double, const double>(&Isis::Camera::SetUniversalGround),
           py::arg("latitude"), py::arg("longitude"))
      .def("set_universal_ground_with_radius",
           py::overload_cast<const double, const double, const double>(&Isis::Camera::SetUniversalGround),
           py::arg("latitude"), py::arg("longitude"), py::arg("radius"))
      .def("has_projection", &Isis::Camera::HasProjection)
      .def("is_band_independent", &Isis::Camera::IsBandIndependent)
      .def("reference_band", &Isis::Camera::ReferenceBand)
      .def("has_reference_band", &Isis::Camera::HasReferenceBand)
      .def("set_band", &Isis::Camera::SetBand, py::arg("band"))
      .def("sample", &Isis::Camera::Sample)
      .def("band", &Isis::Camera::Band)
      .def("line", &Isis::Camera::Line)
      .def("samples", &Isis::Camera::Samples)
      .def("lines", &Isis::Camera::Lines)
      .def("bands", &Isis::Camera::Bands)
      .def("parent_lines", &Isis::Camera::ParentLines)
      .def("parent_samples", &Isis::Camera::ParentSamples)
      .def("pixel_resolution", &Isis::Camera::PixelResolution)
      .def("line_resolution", &Isis::Camera::LineResolution)
      .def("sample_resolution", &Isis::Camera::SampleResolution)
      .def("detector_resolution", &Isis::Camera::DetectorResolution)
      .def("oblique_detector_resolution",
           &Isis::Camera::ObliqueDetectorResolution,
           py::arg("use_local") = true)
      .def("oblique_sample_resolution",
           &Isis::Camera::ObliqueSampleResolution,
           py::arg("use_local") = true)
      .def("oblique_line_resolution",
           &Isis::Camera::ObliqueLineResolution,
           py::arg("use_local") = true)
      .def("oblique_pixel_resolution",
           &Isis::Camera::ObliquePixelResolution,
           py::arg("use_local") = true)
      .def("focal_length", &Isis::Camera::FocalLength)
      .def("pixel_pitch", &Isis::Camera::PixelPitch)
      .def("exposure_duration",
           py::overload_cast<>(&Isis::Camera::exposureDuration, py::const_))
      .def("exposure_duration_at",
           py::overload_cast<const double, const double, const int>(&Isis::Camera::exposureDuration, py::const_),
           py::arg("sample"), py::arg("line"), py::arg("band") = -1)
      .def("universal_latitude", [](Isis::Camera &self) { return self.UniversalLatitude(); })
      .def("universal_longitude", [](Isis::Camera &self) { return self.UniversalLongitude(); })
      .def("instrument_id", [](Isis::Camera &self) { return qStringToStdString(self.instrumentId()); })
      .def("north_azimuth", &Isis::Camera::NorthAzimuth)
      .def("sun_azimuth", &Isis::Camera::SunAzimuth)
      .def("spacecraft_azimuth", &Isis::Camera::SpacecraftAzimuth)
      .def("off_nadir_angle", &Isis::Camera::OffNadirAngle)
      .def("load_cache", &Isis::Camera::LoadCache)
      .def("in_cube", &Isis::Camera::InCube)
      .def("distortion_map",
           [](Isis::Camera &self) -> Isis::CameraDistortionMap * { return self.DistortionMap(); },
           py::return_value_policy::reference_internal)
      .def("detector_map",
           [](Isis::Camera &self) -> Isis::CameraDetectorMap * { return self.DetectorMap(); },
           py::return_value_policy::reference_internal)
      .def("focal_plane_map",
           [](Isis::Camera &self) -> Isis::CameraFocalPlaneMap * { return self.FocalPlaneMap(); },
           py::return_value_policy::reference_internal)
      .def("ground_map",
           [](Isis::Camera &self) -> Isis::CameraGroundMap * { return self.GroundMap(); },
           py::return_value_policy::reference_internal)
      .def("sky_map",
           [](Isis::Camera &self) -> Isis::CameraSkyMap * { return self.SkyMap(); },
           py::return_value_policy::reference_internal)
      .def("target",
           [](Isis::Camera &self) -> Isis::Target * { return self.target(); },
           py::return_value_policy::reference_internal)
      .def("get_camera_type", &Isis::Camera::GetCameraType)
      .def("ck_frame_id", &Isis::Camera::CkFrameId)
      .def("ck_reference_id", &Isis::Camera::CkReferenceId)
      .def("spk_target_id", &Isis::Camera::SpkTargetId)
      .def("spk_center_id", &Isis::Camera::SpkCenterId)
      .def("spk_reference_id", &Isis::Camera::SpkReferenceId)
      .def_static("ground_azimuth", &Isis::Camera::GroundAzimuth,
                  py::arg("ground_latitude"), py::arg("ground_longitude"),
                  py::arg("target_latitude"), py::arg("target_longitude"));

  // Added: 2026-04-09 - Quaternion binding
  py::class_<Isis::Quaternion>(m, "Quaternion")
      .def(py::init<>(),
           "Construct a default Quaternion (identity).")
      .def(py::init<const std::vector<double>>(),
           py::arg("matrix"),
           "Construct a Quaternion from a 9-element rotation matrix (row-major std::vector<double>).")
      .def(py::init<const Isis::Quaternion &>(),
           py::arg("other"),
           "Copy constructor.")
      .def("get_quaternion",
           &Isis::Quaternion::GetQuaternion,
           "Return the quaternion as a list of 4 doubles [w, x, y, z].")
      .def("set",
           &Isis::Quaternion::Set,
           py::arg("values"),
           "Set the quaternion from a list of 4 doubles [w, x, y, z].")
      .def("to_matrix",
           &Isis::Quaternion::ToMatrix,
           "Return the equivalent 9-element rotation matrix (row-major).")
      .def("to_angles",
           &Isis::Quaternion::ToAngles,
           py::arg("axis3"), py::arg("axis2"), py::arg("axis1"),
           "Convert to Euler angles for the given rotation axis sequence.")
      .def("conjugate",
           &Isis::Quaternion::Conjugate,
           "Return the conjugate (inverse rotation) of this quaternion.")
      .def("qxv",
           &Isis::Quaternion::Qxv,
           py::arg("vin"),
           "Rotate a 3-element vector by this quaternion (Q * v).")
      .def("__mul__",
           [](const Isis::Quaternion &a, const Isis::Quaternion &b) { return a * b; },
           py::is_operator())
      .def("__mul__",
           [](const Isis::Quaternion &a, double s) {
             Isis::Quaternion copy(a);
             return copy * s;
           },
           py::is_operator())
      .def("__repr__",
           [](const Isis::Quaternion &self) {
             auto q = self.GetQuaternion();
             return "Quaternion(" +
                    std::to_string(q[0]) + ", " + std::to_string(q[1]) + ", " +
                    std::to_string(q[2]) + ", " + std::to_string(q[3]) + ")";
           });

  // Added: 2026-04-09 - LightTimeCorrectionState binding
  py::class_<Isis::LightTimeCorrectionState>(m, "LightTimeCorrectionState")
      .def(py::init<>(),
           "Construct a LightTimeCorrectionState with default state.")
      .def("set_aberration_correction",
           [](Isis::LightTimeCorrectionState &self, const std::string &correction) {
             self.setAberrationCorrection(stdStringToQString(correction));
           },
           py::arg("correction"),
           "Set the NAIF aberration correction string (e.g. 'LT+S', 'NONE').")
      .def("get_aberration_correction",
           [](const Isis::LightTimeCorrectionState &self) {
             return qStringToStdString(self.getAberrationCorrection());
           },
           "Return the current aberration correction string.")
      .def("is_light_time_corrected",
           &Isis::LightTimeCorrectionState::isLightTimeCorrected,
           "Return True if light-time correction is applied.")
      .def("is_observer_target_swapped",
           &Isis::LightTimeCorrectionState::isObserverTargetSwapped,
           "Return True if observer and target have been swapped for the correction.")
      .def("set_swap_observer_target",
           &Isis::LightTimeCorrectionState::setSwapObserverTarget,
           "Enable the observer-target swap.")
      .def("set_no_swap_observer_target",
           &Isis::LightTimeCorrectionState::setNoSwapObserverTarget,
           "Disable the observer-target swap.")
      .def("is_light_time_to_surface_corrected",
           &Isis::LightTimeCorrectionState::isLightTimeToSurfaceCorrected,
           "Return True if light-time-to-surface correction is applied.")
      .def("set_correct_light_time_to_surface",
           &Isis::LightTimeCorrectionState::setCorrectLightTimeToSurface,
           "Enable the light-time-to-surface correction.")
      .def("set_no_correct_light_time_to_surface",
           &Isis::LightTimeCorrectionState::setNoCorrectLightTimeToSurface,
           "Disable the light-time-to-surface correction.")
      .def("__eq__",
           [](const Isis::LightTimeCorrectionState &a,
              const Isis::LightTimeCorrectionState &b) { return a == b; },
           py::is_operator())
      .def("__repr__",
           [](const Isis::LightTimeCorrectionState &self) {
             return "LightTimeCorrectionState(correction='" +
                    qStringToStdString(self.getAberrationCorrection()) + "')";
           });

  // PixelFOV — computes the lat/lon boundary vertices of a pixel's field of view.
  // latLonVertices returns a list of lists of (lon, lat) float tuples.
  // Added: 2026-04-10
  py::class_<Isis::PixelFOV>(m, "PixelFOV")
      .def(py::init<>(),
           "Construct a PixelFOV object.")
      .def(py::init<const Isis::PixelFOV &>(),
           py::arg("other"),
           "Copy-construct a PixelFOV object.")
      .def("lat_lon_vertices",
           [](const Isis::PixelFOV &self,
              Isis::Camera &camera,
              double sample,
              double line,
              int num_ifovs) {
             QList<QList<QPointF>> raw = self.latLonVertices(camera, sample, line, num_ifovs);
             // Convert to Python: list of list of (x, y) tuples
             std::vector<std::vector<std::pair<double, double>>> result;
             result.reserve(raw.size());
             for (const QList<QPointF> &ring : raw) {
               std::vector<std::pair<double, double>> pts;
               pts.reserve(ring.size());
               for (const QPointF &p : ring) {
                 pts.emplace_back(p.x(), p.y());
               }
               result.push_back(std::move(pts));
             }
             return result;
           },
           py::arg("camera"),
           py::arg("sample"),
           py::arg("line"),
           py::arg("num_ifovs") = 1,
           "Compute lat/lon boundary vertices of the pixel's field of view.\n\n"
           "Parameters\n"
           "----------\n"
           "camera : Camera\n"
           "    Camera model positioned at the desired geometry.\n"
           "sample : float\n"
           "    Sample coordinate.\n"
           "line : float\n"
           "    Line coordinate.\n"
           "num_ifovs : int, optional\n"
           "    Number of instantaneous FOVs to include (default: 1).\n\n"
           "Returns\n"
           "-------\n"
           "list of list of (float, float)\n"
           "    Each inner list is a ring of (longitude, latitude) vertex pairs.")
      .def("__repr__", [](const Isis::PixelFOV &) {
        return "<PixelFOV>";
      });
}
