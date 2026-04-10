// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS header: reference/upstream_isis/src/base/objs/ImagePolygon/ImagePolygon.h
// Source class: Isis::ImagePolygon
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun added ImagePolygon binding (Batch 2) exposing
//          Create-from-coords, poly_str, setters, and vertex/dimension queries.
// Purpose: Expose Isis::ImagePolygon to Python for footprint polygon construction
//          and WKT serialization without requiring a live Cube or GEOS Python library.

#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Blob.h"
#include "ImagePolygon.h"
#include "IException.h"

namespace py = pybind11;

void bind_base_image_polygon(py::module_ &m)
{
  py::class_<Isis::ImagePolygon>(m, "ImagePolygon")
      .def(py::init<>(),
           "Construct a default empty ImagePolygon.")
      .def(py::init<Isis::Blob &>(),
           py::arg("blob"),
           "Reconstruct an ImagePolygon from a stored Blob.")
      .def("create_from_coords",
           [](Isis::ImagePolygon &self,
              const std::vector<std::vector<double>> &coords) {
               self.Create(coords);
           },
           py::arg("coords"),
           "Build a polygon from a list of [lon, lat] or [x, y] coordinate pairs.")
      .def("set_emission",
           [](Isis::ImagePolygon &self, double emission) {
               self.Emission(emission);
           },
           py::arg("emission"),
           "Set the maximum valid emission angle (degrees).")
      .def("set_incidence",
           [](Isis::ImagePolygon &self, double incidence) {
               self.Incidence(incidence);
           },
           py::arg("incidence"),
           "Set the maximum valid incidence angle (degrees).")
      .def("set_ellipsoid_limb",
           [](Isis::ImagePolygon &self, bool use_ellipsoid) {
               self.EllipsoidLimb(use_ellipsoid);
           },
           py::arg("use_ellipsoid"),
           "If True, use the ellipsoid model for limb detection.")
      .def("set_subpixel_accuracy",
           [](Isis::ImagePolygon &self, int div) {
               self.SubpixelAccuracy(div);
           },
           py::arg("div"),
           "Set the subpixel accuracy (binary-search depth, default 50).")
      .def("poly_str",
           &Isis::ImagePolygon::polyStr,
           "Return the WKT (Well Known Text) string of the polygon.")
      .def("valid_sample_dim",
           &Isis::ImagePolygon::validSampleDim,
           "Return the valid sample dimension of the source cube.")
      .def("valid_line_dim",
           &Isis::ImagePolygon::validLineDim,
           "Return the valid line dimension of the source cube.")
      .def("get_sinc",
           &Isis::ImagePolygon::getSinc,
           "Return the sample increment used to create this polygon.")
      .def("get_linc",
           &Isis::ImagePolygon::getLinc,
           "Return the line increment used to create this polygon.")
      .def("num_vertices",
           &Isis::ImagePolygon::numVertices,
           "Return the total number of polygon vertex points.")
      .def("to_blob",
           &Isis::ImagePolygon::toBlob,
           "Serialise this polygon to an ISIS Blob for cube storage.")
      .def("__repr__",
           [](const Isis::ImagePolygon &self) {
               return std::string("ImagePolygon(poly_str=\"") +
                      self.polyStr() + "\")";
           });
}
