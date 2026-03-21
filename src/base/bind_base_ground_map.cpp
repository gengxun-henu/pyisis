// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS header: isis/src/base/objs/UniversalGroundMap/UniversalGroundMap.h
// Source class: Isis::UniversalGroundMap
// Source header author(s): Jeff Anderson
// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21
// Purpose: Expose Isis::UniversalGroundMap image/ground conversion helpers.

#include <string>

#include <pybind11/pybind11.h>

#include "Camera.h"
#include "Cube.h"
#include "Latitude.h"
#include "Longitude.h"
#include "Projection.h"
#include "SurfacePoint.h"
#include "UniversalGroundMap.h"

namespace py = pybind11;

void bind_base_ground_map(py::module_ &m) {
  py::class_<Isis::UniversalGroundMap> ground_map(m, "UniversalGroundMap");

  py::enum_<Isis::UniversalGroundMap::CameraPriority>(ground_map, "CameraPriority")
      .value("CameraFirst", Isis::UniversalGroundMap::CameraFirst)
      .value("ProjectionFirst", Isis::UniversalGroundMap::ProjectionFirst);

  ground_map
      .def(py::init<Isis::Cube &, Isis::UniversalGroundMap::CameraPriority>(),
           py::arg("cube"),
           py::arg("priority") = Isis::UniversalGroundMap::CameraFirst)
      .def("set_band", &Isis::UniversalGroundMap::SetBand, py::arg("band"))
      .def("set_universal_ground",
           &Isis::UniversalGroundMap::SetUniversalGround,
           py::arg("latitude"),
           py::arg("longitude"))
      .def("set_unbound_ground",
           &Isis::UniversalGroundMap::SetUnboundGround,
           py::arg("latitude"),
           py::arg("longitude"))
      .def("set_ground",
           py::overload_cast<Isis::Latitude, Isis::Longitude>(&Isis::UniversalGroundMap::SetGround),
           py::arg("latitude"),
           py::arg("longitude"))
      .def("set_ground",
           py::overload_cast<const Isis::SurfacePoint &>(&Isis::UniversalGroundMap::SetGround),
           py::arg("surface_point"))
      .def("sample", &Isis::UniversalGroundMap::Sample)
      .def("line", &Isis::UniversalGroundMap::Line)
      .def("set_image", &Isis::UniversalGroundMap::SetImage, py::arg("sample"), py::arg("line"))
      .def("universal_latitude", &Isis::UniversalGroundMap::UniversalLatitude)
      .def("universal_longitude", &Isis::UniversalGroundMap::UniversalLongitude)
      .def("resolution", &Isis::UniversalGroundMap::Resolution)
      .def("ground_range",
           [](Isis::UniversalGroundMap &self, Isis::Cube *cube, bool allow_estimation) -> py::object {
             Isis::Latitude min_lat;
             Isis::Latitude max_lat;
             Isis::Longitude min_lon;
             Isis::Longitude max_lon;
             if (!self.GroundRange(cube, min_lat, max_lat, min_lon, max_lon, allow_estimation)) {
               return py::none();
             }
             return py::make_tuple(min_lat, max_lat, min_lon, max_lon);
           },
           py::arg("cube") = nullptr,
           py::arg("allow_estimation") = true)
      .def("has_projection", &Isis::UniversalGroundMap::HasProjection)
      .def("has_camera", &Isis::UniversalGroundMap::HasCamera)
      .def("projection",
           [](Isis::UniversalGroundMap &self) -> Isis::Projection * { return self.Projection(); },
           py::return_value_policy::reference_internal)
      .def("camera",
           [](Isis::UniversalGroundMap &self) -> Isis::Camera * { return self.Camera(); },
           py::return_value_policy::reference_internal)
      .def("__repr__",
           [](Isis::UniversalGroundMap &self) {
             std::string backend = self.HasCamera() ? "camera" : (self.HasProjection() ? "projection" : "none");
             return "UniversalGroundMap(backend='" + backend + "')";
           });
}