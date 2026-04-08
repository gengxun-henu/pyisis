// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added derived camera hierarchy bindings for framing, line-scan, push-frame, radar, rolling-shutter, CSM, and ideal cameras
// Purpose: pybind11 bindings for ISIS camera subclass hierarchy and line-scan map accessors layered on the base Camera binding

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "Camera.h"
#include "CSMCamera.h"
#include "FramingCamera.h"
#include "IdealCamera.h"
#include "LineScanCamera.h"
#include "LineScanCameraDetectorMap.h"
#include "LineScanCameraGroundMap.h"
#include "LineScanCameraSkyMap.h"
#include "PushFrameCamera.h"
#include "RadarCamera.h"
#include "RollingShutterCamera.h"

namespace py = pybind11;

void bind_camera_hierarchy(py::module_ &m) {
  py::class_<Isis::FramingCamera, Isis::Camera>(m, "FramingCamera");
  py::class_<Isis::LineScanCamera, Isis::Camera>(m, "LineScanCamera")
   .def("detector_map",
     [](Isis::LineScanCamera &self) -> Isis::LineScanCameraDetectorMap * { return self.DetectorMap(); },
     py::return_value_policy::reference_internal)
   .def("ground_map",
     [](Isis::LineScanCamera &self) -> Isis::LineScanCameraGroundMap * { return self.GroundMap(); },
     py::return_value_policy::reference_internal)
   .def("sky_map",
     [](Isis::LineScanCamera &self) -> Isis::LineScanCameraSkyMap * { return self.SkyMap(); },
     py::return_value_policy::reference_internal);
  py::class_<Isis::PushFrameCamera, Isis::Camera>(m, "PushFrameCamera");
  py::class_<Isis::RadarCamera, Isis::Camera>(m, "RadarCamera");
  py::class_<Isis::RollingShutterCamera, Isis::Camera>(m, "RollingShutterCamera");
  py::class_<Isis::CSMCamera, Isis::Camera>(m, "CSMCamera");
  py::class_<Isis::IdealCamera, Isis::Camera>(m, "IdealCamera");
}
