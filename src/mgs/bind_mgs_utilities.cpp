// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocNarrowAngleSumming/MocNarrowAngleSumming.h
// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocWideAngleCamera/MocWideAngleDistortionMap.h
// Source class: MocNarrowAngleSumming, MocWideAngleDistortionMap
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-05
// Updated: 2026-04-05
// Purpose: pybind11 bindings for Mars Global Surveyor MOC utilities

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <sstream>

#include "MocNarrowAngleSumming.h"
#include "MocWideAngleDistortionMap.h"
#include "Camera.h"

namespace py = pybind11;

void bind_mgs_utilities(py::module_ &m) {
  // MocNarrowAngleSumming - Mars Global Surveyor MOC narrow angle summing class
  // Provides sample/detector coordinate transformations for MOC narrow angle camera
  py::class_<Isis::MocNarrowAngleSumming>(m, "MocNarrowAngleSumming")
    .def(py::init<int, int>(),
      py::arg("csum"),
      py::arg("ss"),
      "Constructs the MocNarrowAngleSumming object.\n\n"
      "Args:\n"
      "    csum: Cross-track summing mode\n"
      "    ss: Starting sample")

    .def("detector", &Isis::MocNarrowAngleSumming::Detector,
      py::arg("sample"),
      "Given the sample value, computes the corresponding detector.\n\n"
      "Args:\n"
      "    sample: Sample position\n\n"
      "Returns:\n"
      "    Detector position")

    .def("sample", &Isis::MocNarrowAngleSumming::Sample,
      py::arg("detector"),
      "Given the detector value, computes the corresponding sample.\n\n"
      "Args:\n"
      "    detector: Detector position\n\n"
      "Returns:\n"
      "    Sample position")

    .def("__repr__", [](const Isis::MocNarrowAngleSumming &self) {
      std::ostringstream oss;
      oss << "<MocNarrowAngleSumming>";
      return oss.str();
    });

  // MocWideAngleDistortionMap - Mars Global Surveyor MOC wide angle distortion map
  // Inherits from CameraDistortionMap (already bound in bind_camera_maps.cpp)
  // Provides distortion/undistortion for MOC wide angle camera with red/non-red filter variants
  py::class_<Isis::MocWideAngleDistortionMap, Isis::CameraDistortionMap>(m, "MocWideAngleDistortionMap")
    .def(py::init<Isis::Camera*, bool>(),
      py::arg("parent"),
      py::arg("red"),
      py::keep_alive<1, 2>(),
      "Constructs the MocWideAngleDistortionMap object.\n\n"
      "Args:\n"
      "    parent: Pointer to the parent Camera object\n"
      "    red: True if using red filter, False otherwise")

    .def("set_focal_plane",
      &Isis::MocWideAngleDistortionMap::SetFocalPlane,
      py::arg("dx"),
      py::arg("dy"),
      "Apply distortion to focal plane coordinates.\n\n"
      "Args:\n"
      "    dx: Distorted focal plane x coordinate\n"
      "    dy: Distorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("set_undistorted_focal_plane",
      &Isis::MocWideAngleDistortionMap::SetUndistortedFocalPlane,
      py::arg("ux"),
      py::arg("uy"),
      "Remove distortion from focal plane coordinates.\n\n"
      "Args:\n"
      "    ux: Undistorted focal plane x coordinate\n"
      "    uy: Undistorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("__repr__", [](const Isis::MocWideAngleDistortionMap &self) {
      std::ostringstream oss;
      oss << "<MocWideAngleDistortionMap>";
      return oss.str();
    });
}
