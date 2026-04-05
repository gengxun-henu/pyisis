// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocNarrowAngleSumming/MocNarrowAngleSumming.h
// Source class: MocNarrowAngleSumming
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-05
// Updated: 2026-04-05
// Purpose: pybind11 bindings for Mars Global Surveyor MOC narrow angle summing utilities

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <sstream>

#include "MocNarrowAngleSumming.h"

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
}
