// Source ISIS headers:
// - reference/upstream_isis/src/lro/objs/LroNarrowAngleCamera/LroNarrowAngleDistortionMap.h
// - reference/upstream_isis/src/lro/objs/LroWideAngleCamera/LroWideAngleCameraDistortionMap.h
// - reference/upstream_isis/src/lro/objs/LroWideAngleCamera/LroWideAngleCameraFocalPlaneMap.h
// Source classes: LroNarrowAngleDistortionMap, LroWideAngleCameraDistortionMap, LroWideAngleCameraFocalPlaneMap
// Source header author(s): Jacob Danton, Steven Lambright, Kris Becker (see individual headers)
// Binding author: Geng Xun
// Created: 2026-04-06
// Updated: 2026-04-06  Geng Xun added LRO narrow/wide-angle distortion and focal-plane map bindings
// Purpose: pybind11 bindings for Lunar Reconnaissance Orbiter (LRO) camera utilities including distortion maps and focal plane map

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <sstream>

#include "Camera.h"
#include "CameraDistortionMap.h"
#include "CameraFocalPlaneMap.h"
#include "LroNarrowAngleDistortionMap.h"
#include "LroWideAngleCameraDistortionMap.h"
#include "LroWideAngleCameraFocalPlaneMap.h"
#include "helpers.h"

namespace py = pybind11;

void bind_lro_utilities(py::module_ &m) {
  // LroNarrowAngleDistortionMap - LRO Narrow Angle Camera distortion map
  // Inherits from CameraDistortionMap (already bound in bind_camera_maps.cpp)
  // Provides distortion/undistortion for LRO NAC
  py::class_<Isis::LroNarrowAngleDistortionMap, Isis::CameraDistortionMap>(m, "LroNarrowAngleDistortionMap")
    .def(py::init<Isis::Camera*>(),
      py::arg("parent"),
      py::keep_alive<1, 2>(),
      "Constructs the LroNarrowAngleDistortionMap object.\n\n"
      "Args:\n"
      "    parent: Pointer to the parent Camera object")

    .def("set_distortion",
      &Isis::LroNarrowAngleDistortionMap::SetDistortion,
      py::arg("naif_ik_code"),
      "Load distortion parameters from NAIF IK kernel.\n\n"
      "Args:\n"
      "    naif_ik_code: NAIF IK code for the camera")

    .def("set_focal_plane",
      &Isis::LroNarrowAngleDistortionMap::SetFocalPlane,
      py::arg("dx"),
      py::arg("dy"),
      "Apply distortion to focal plane coordinates.\n\n"
      "Args:\n"
      "    dx: Distorted focal plane x coordinate\n"
      "    dy: Distorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("set_undistorted_focal_plane",
      &Isis::LroNarrowAngleDistortionMap::SetUndistortedFocalPlane,
      py::arg("ux"),
      py::arg("uy"),
      "Remove distortion from focal plane coordinates.\n\n"
      "Args:\n"
      "    ux: Undistorted focal plane x coordinate\n"
      "    uy: Undistorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("__repr__", [](const Isis::LroNarrowAngleDistortionMap &self) {
      std::ostringstream oss;
      oss << "<LroNarrowAngleDistortionMap>";
      return oss.str();
    });

  // LroWideAngleCameraDistortionMap - LRO Wide Angle Camera distortion map
  // Inherits from CameraDistortionMap (already bound in bind_camera_maps.cpp)
  // Provides band-independent distortion/undistortion for LRO WAC (VIS and UV bands)
  py::class_<Isis::LroWideAngleCameraDistortionMap, Isis::CameraDistortionMap>(m, "LroWideAngleCameraDistortionMap")
    .def(py::init<Isis::Camera*, int>(),
      py::arg("parent"),
      py::arg("naif_ik_code"),
      py::keep_alive<1, 2>(),
      "Constructs the LroWideAngleCameraDistortionMap object.\n\n"
      "Args:\n"
      "    parent: Pointer to the parent Camera object\n"
      "    naif_ik_code: NAIF IK code for the initial filter/band")

    .def("add_filter",
      &Isis::LroWideAngleCameraDistortionMap::addFilter,
      py::arg("naif_ik_code"),
      "Add distortion parameters for another filter/band.\n\n"
      "Allows band-independent distortion models.\n\n"
      "Args:\n"
      "    naif_ik_code: NAIF IK code for the filter/band to add")

    .def("set_band",
      &Isis::LroWideAngleCameraDistortionMap::setBand,
      py::arg("vband"),
      "Set the current band for distortion calculations.\n\n"
      "Args:\n"
      "    vband: Virtual band number (0-based index)")

    .def("set_focal_plane",
      &Isis::LroWideAngleCameraDistortionMap::SetFocalPlane,
      py::arg("dx"),
      py::arg("dy"),
      "Apply distortion to focal plane coordinates.\n\n"
      "Uses the currently selected band's distortion model.\n\n"
      "Args:\n"
      "    dx: Distorted focal plane x coordinate\n"
      "    dy: Distorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("set_undistorted_focal_plane",
      &Isis::LroWideAngleCameraDistortionMap::SetUndistortedFocalPlane,
      py::arg("ux"),
      py::arg("uy"),
      "Remove distortion from focal plane coordinates.\n\n"
      "Uses the currently selected band's distortion model.\n\n"
      "Args:\n"
      "    ux: Undistorted focal plane x coordinate\n"
      "    uy: Undistorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("__repr__", [](const Isis::LroWideAngleCameraDistortionMap &self) {
      std::ostringstream oss;
      oss << "<LroWideAngleCameraDistortionMap>";
      return oss.str();
    });

  // LroWideAngleCameraFocalPlaneMap - LRO Wide Angle Camera focal plane map
  // Inherits from CameraFocalPlaneMap (already bound in bind_camera_maps.cpp)
  // Provides band-independent focal plane coordinate transformations for LRO WAC
  py::class_<Isis::LroWideAngleCameraFocalPlaneMap, Isis::CameraFocalPlaneMap>(m, "LroWideAngleCameraFocalPlaneMap")
    .def(py::init<Isis::Camera*, int>(),
      py::arg("parent"),
      py::arg("naif_ik_code"),
      py::keep_alive<1, 2>(),
      "Constructs the LroWideAngleCameraFocalPlaneMap object.\n\n"
      "Args:\n"
      "    parent: Pointer to the parent Camera object\n"
      "    naif_ik_code: NAIF IK code for the initial filter/band")

    .def("add_filter",
      &Isis::LroWideAngleCameraFocalPlaneMap::addFilter,
      py::arg("naif_ik_code"),
      "Add focal plane parameters for another filter/band.\n\n"
      "Allows band-independent translation parameters.\n\n"
      "Args:\n"
      "    naif_ik_code: NAIF IK code for the filter/band to add")

    .def("set_band",
      &Isis::LroWideAngleCameraFocalPlaneMap::setBand,
      py::arg("vband"),
      "Set the current band for focal plane transformations.\n\n"
      "Args:\n"
      "    vband: Virtual band number (0-based index)")

    .def("__repr__", [](const Isis::LroWideAngleCameraFocalPlaneMap &self) {
      std::ostringstream oss;
      oss << "<LroWideAngleCameraFocalPlaneMap>";
      return oss.str();
    });
}
