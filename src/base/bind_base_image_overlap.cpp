// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/base/objs/ImageOverlap/ImageOverlap.h
// Source classes: Isis::ImageOverlap
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun added ImageOverlap binding exposing serial number management and overlap metadata.
// Purpose: Expose Isis::ImageOverlap to Python for serial number and area management.
//          Polygon-related methods (requiring geos::geom::MultiPolygon) are not exposed.

#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "ImageOverlap.h"

#include "helpers.h"

namespace py = pybind11;

void bind_base_image_overlap(py::module_ &m) {
  // ImageOverlap — holds an area of polygon overlap along with associated serial numbers.
  // The geos MultiPolygon polygon and stream constructors are not bound here to avoid
  // exposing geos native types directly. The default constructor and serial number accessors
  // are fully functional.
  // Added: 2026-04-10
  py::class_<Isis::ImageOverlap>(m, "ImageOverlap")
      .def(py::init<>(),
           "Construct an empty ImageOverlap object with no polygon and no serial numbers.")
      .def("add",
           [](Isis::ImageOverlap &self, const std::string &sn) {
             QString q = QString::fromStdString(sn);
             self.Add(q);
           },
           py::arg("serial_number"),
           "Add a serial number to this overlap area.\n\n"
           "Parameters\n"
           "----------\n"
           "serial_number : str\n"
           "    The serial number string to associate with this overlap.")
      .def("size",
           [](const Isis::ImageOverlap &self) { return self.Size(); },
           "Return the number of serial numbers in this overlap area.")
      .def("__len__",
           [](const Isis::ImageOverlap &self) { return self.Size(); })
      .def("__getitem__",
           [](const Isis::ImageOverlap &self, int index) {
             if (index < 0 || index >= self.Size()) {
               throw py::index_error("index out of range");
             }
             return self[index].toStdString();
           },
           py::arg("index"),
           "Return the serial number at the given index.")
      .def("has_any_same_serial_number",
           [](const Isis::ImageOverlap &self, Isis::ImageOverlap &other) {
             return self.HasAnySameSerialNumber(other);
           },
           py::arg("other"),
           "Return True if any serial number in this overlap appears in 'other'.")
      .def("has_serial_number",
           [](const Isis::ImageOverlap &self, const std::string &sn) {
             QString q = QString::fromStdString(sn);
             return self.HasSerialNumber(q);
           },
           py::arg("serial_number"),
           "Return True if the given serial number is in this overlap.")
      .def("area",
           [](Isis::ImageOverlap &self) {
             return self.Area();
           },
           "Return the area of the overlap polygon (0.0 if no polygon is set).")
      .def("__repr__",
           [](const Isis::ImageOverlap &self) {
             return "<ImageOverlap size=" + std::to_string(self.Size()) + ">";
           });
}
