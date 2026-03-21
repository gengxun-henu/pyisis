// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "Camera.h"
#include "CameraDetectorMap.h"
#include "CameraDistortionMap.h"
#include "CameraFocalPlaneMap.h"
#include "CameraGroundMap.h"
#include "CameraSkyMap.h"
#include "Sensor.h"
#include "helpers.h"

namespace py = pybind11;

void bind_camera(py::module_ &m) {
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
      .def("get_camera_type", &Isis::Camera::GetCameraType)
      .def("ck_frame_id", &Isis::Camera::CkFrameId)
      .def("ck_reference_id", &Isis::Camera::CkReferenceId)
      .def("spk_target_id", &Isis::Camera::SpkTargetId)
      .def("spk_center_id", &Isis::Camera::SpkCenterId)
      .def("spk_reference_id", &Isis::Camera::SpkReferenceId)
      .def_static("ground_azimuth", &Isis::Camera::GroundAzimuth,
                  py::arg("ground_latitude"), py::arg("ground_longitude"),
                  py::arg("target_latitude"), py::arg("target_longitude"));
}
