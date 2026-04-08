// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added CameraFactory static bindings for cube-driven camera creation and plugin version queries
// Purpose: pybind11 bindings for ISIS CameraFactory static helpers that construct and inspect cube-backed cameras

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>

#include <pybind11/pybind11.h>

#include "Camera.h"
#include "CameraFactory.h"
#include "Cube.h"

namespace py = pybind11;

/**
 * @brief Bindings for CameraFactory class
 * This class provides static methods for creating Camera objects from Cube objects, as well as retrieving camera version 
 * information and initializing camera plugins. The create method returns a pointer to a Camera object associated with the given Cube, 
 * while the camera_version method retrieves the version of the camera plugin used for the Cube. The init_plugin method initializes 
 * any necessary camera plugins.
 * @param m The pybind11 module to which the CameraFactory bindings will be added.
 * @note The create method returns a pointer to a Camera object that is owned by the Cube object, so the return 
 * value is marked with py::return_value_policy::reference_internal to ensure that the Camera object is not deleted when the 
 * Python reference goes out of scope.
 * @internal
 * @todo Add error handling for cases where the Cube does not have an associated Camera or when the camera plugin cannot be initialized.
 * 
 */
void bind_camera_factory(py::module_ &m) {
  py::class_<Isis::CameraFactory, std::unique_ptr<Isis::CameraFactory, py::nodelete>>(m, "CameraFactory")
      .def_static("create",
                  [](Isis::Cube &cube) -> Isis::Camera * { return cube.camera(); },
                  py::arg("cube"),
                  py::return_value_policy::reference_internal)
      .def_static("camera_version",
                  py::overload_cast<Isis::Cube &>(&Isis::CameraFactory::CameraVersion),
                  py::arg("cube"))
      .def_static("init_plugin", &Isis::CameraFactory::initPlugin);
}
