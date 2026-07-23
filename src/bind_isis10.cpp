// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/10.0.0/isis/src/base/objs/IProj/IProj.h
// - reference/upstream_isis/10.0.0/isis/src/chandrayaan2/objs/Chandrayaan2OhrcCamera/Chandrayaan2OhrcCamera.h
// - reference/upstream_isis/10.0.0/isis/src/chandrayaan2/objs/Chandrayaan2TmcCamera/Chandrayaan2TmcCamera.h
// Source classes: IProj, Chandrayaan2OhrcCamera, Chandrayaan2TmcCamera
// Source header author(s): Adam Paquette for IProj; not explicitly stated for the camera headers
// Binding author: Geng Xun
// Created: 2026-07-23
// Updated: 2026-07-23  Geng Xun added the first ISIS 10-only non-GUI binding batch.
// Purpose: Expose stable ISIS 10-only projection and Chandrayaan-2 camera APIs.

#include <stdexcept>

#include <pybind11/pybind11.h>

#ifdef PYISIS_ISIS10_API
#include "Chandrayaan2OhrcCamera.h"
#include "Chandrayaan2TmcCamera.h"
#include "Cube.h"
#include "helpers.h"
#include "IProj.h"
#include "LineScanCamera.h"
#include "Pvl.h"
#include "TProjection.h"
#endif

namespace py = pybind11;

void bind_isis10(py::module_ &m) {
#ifdef PYISIS_ISIS10_API
  py::class_<Isis::IProj, Isis::TProjection>(m, "IProj")
      .def(py::init<Isis::Pvl &, bool>(),
           py::arg("label"),
           py::arg("allow_defaults") = false)
      .def("name", [](const Isis::IProj &self) {
        return qStringToStdString(self.Name());
      })
      .def("version", [](const Isis::IProj &self) {
        return qStringToStdString(self.Version());
      })
      .def("mapping", &Isis::IProj::Mapping)
      .def("set_ground",
           &Isis::IProj::SetGround,
           py::arg("lat"),
           py::arg("lon"))
      .def("set_coordinate",
           &Isis::IProj::SetCoordinate,
           py::arg("x"),
           py::arg("y"))
      .def("xy_range", [](Isis::IProj &self) {
        double minX;
        double maxX;
        double minY;
        double maxY;
        if (!self.XYRange(minX, maxX, minY, maxY)) {
          throw std::runtime_error("Failed to compute XY range");
        }
        return py::make_tuple(minX, maxX, minY, maxY);
      });

  py::class_<Isis::Chandrayaan2OhrcCamera, Isis::LineScanCamera>(
      m, "Chandrayaan2OhrcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Chandrayaan-2 OHRC camera model from an opened cube.")
      .def("ck_frame_id", &Isis::Chandrayaan2OhrcCamera::CkFrameId)
      .def("ck_reference_id", &Isis::Chandrayaan2OhrcCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::Chandrayaan2OhrcCamera::SpkReferenceId);

  py::class_<Isis::Chandrayaan2TmcCamera, Isis::LineScanCamera>(
      m, "Chandrayaan2TmcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Chandrayaan-2 TMC-2 camera model from an opened cube.")
      .def("ck_frame_id", &Isis::Chandrayaan2TmcCamera::CkFrameId)
      .def("ck_reference_id", &Isis::Chandrayaan2TmcCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::Chandrayaan2TmcCamera::SpkReferenceId);
#else
  (void)m;
#endif
}
