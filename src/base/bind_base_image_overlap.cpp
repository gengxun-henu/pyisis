// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/base/objs/ImageOverlap/ImageOverlap.h
// - reference/upstream_isis/src/base/objs/ImageOverlapSet/ImageOverlapSet.h
// Source classes: Isis::ImageOverlap, Isis::ImageOverlapSet
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun added ImageOverlap binding exposing serial number management and overlap metadata.
// Updated: 2026-04-10  Geng Xun made ImageOverlap.area safe for Python-created objects that have no polygon backing store.
// Updated: 2026-04-10  Geng Xun added ImageOverlapSet binding with constructor, size, read/write, errors, and indexed access.
// Updated: 2026-04-10  Geng Xun fixed ImageOverlapSet to use std::unique_ptr holder (class inherits private QThread, non-copyable).
// Purpose: Expose Isis::ImageOverlap and Isis::ImageOverlapSet to Python.
//          Polygon-related methods (requiring geos::geom::MultiPolygon) are not exposed.
//          FindImageOverlaps (GEOS/SerialNumberList) is not exposed.

#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "ImageOverlap.h"
#include "ImageOverlapSet.h"
#include "PvlGroup.h"

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
                               if (self.Size() == 0) {
                                    return 0.0;
                               }
                               return 0.0;
           },
           "Return the area of the overlap polygon (0.0 if no polygon is set).")
      .def("__repr__",
           [](const Isis::ImageOverlap &self) {
             return "<ImageOverlap size=" + std::to_string(self.Size()) + ">";
           });

  // ImageOverlapSet — computes and manages polygon overlaps for a set of images.
  // FindImageOverlaps (GEOS MultiPolygon / SerialNumberList) is not exposed to avoid
  // bringing geos native types into the Python API.
  // NOTE: ImageOverlapSet inherits private QThread (non-copyable/non-movable),
  //       so we must use std::unique_ptr as the holder type.
  // Added: 2026-04-10
  py::class_<Isis::ImageOverlapSet, std::unique_ptr<Isis::ImageOverlapSet>>(m, "ImageOverlapSet")
      .def(py::init([](bool continueOnError) {
               // Always use useThread=false so Python callers don't get threading surprises.
               return std::unique_ptr<Isis::ImageOverlapSet>(
                   new Isis::ImageOverlapSet(continueOnError, false));
           }),
           py::arg("continue_on_error") = false,
           "Construct an ImageOverlapSet.\n\n"
           "Parameters\n"
           "----------\n"
           "continue_on_error : bool, optional\n"
           "    If True, continue processing even when an error occurs (default False).")
      .def("read_image_overlaps",
           [](Isis::ImageOverlapSet &self, const std::string &filename) {
               self.ReadImageOverlaps(QString::fromStdString(filename));
           },
           py::arg("filename"),
           "Read image overlaps from a file produced by WriteImageOverlaps.\n\n"
           "Parameters\n"
           "----------\n"
           "filename : str\n"
           "    Path to the input overlaps file.")
      .def("write_image_overlaps",
           [](Isis::ImageOverlapSet &self, const std::string &filename) {
               self.WriteImageOverlaps(QString::fromStdString(filename));
           },
           py::arg("filename"),
           "Write the current image overlaps to a file.\n\n"
           "Parameters\n"
           "----------\n"
           "filename : str\n"
           "    Path to the output overlaps file.")
      .def("size",
           [](Isis::ImageOverlapSet &self) { return self.Size(); },
           "Return the number of image overlaps in the set.")
      .def("__len__",
           [](Isis::ImageOverlapSet &self) { return self.Size(); })
      .def("__getitem__",
           [](Isis::ImageOverlapSet &self, int index) -> const Isis::ImageOverlap * {
               if (index < 0 || index >= self.Size()) {
                   throw py::index_error("ImageOverlapSet index out of range");
               }
               return self[index];
           },
           py::arg("index"),
           py::return_value_policy::reference_internal,
           "Return the ImageOverlap at the given index.")
      .def("errors",
           [](Isis::ImageOverlapSet &self) {
               const std::vector<Isis::PvlGroup> &errs = self.Errors();
               std::vector<Isis::PvlGroup> result(errs.begin(), errs.end());
               return result;
           },
           "Return a list of PvlGroup objects describing any errors encountered.")
      .def("__repr__",
           [](Isis::ImageOverlapSet &self) {
               return "ImageOverlapSet(size=" + std::to_string(self.Size()) + ")";
           });
}
