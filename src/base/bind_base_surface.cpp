// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added SurfacePoint bindings covering coordinate enums, conversions, accessors, and distance helpers
// Purpose: pybind11 bindings for ISIS SurfacePoint coordinate storage, conversions, and geometry accessors

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <array>
#include <string>

#include <pybind11/pybind11.h>

#include "Angle.h"
#include "Displacement.h"
#include "Distance.h"
#include "Latitude.h"
#include "Longitude.h"
#include "SurfacePoint.h"

namespace py = pybind11;

void bind_base_surface(py::module_ &m) {
  py::class_<Isis::SurfacePoint> surface_point(m, "SurfacePoint");

  py::enum_<Isis::SurfacePoint::CoordinateType>(surface_point, "CoordinateType")
      .value("Latitudinal", Isis::SurfacePoint::Latitudinal)
      .value("Rectangular", Isis::SurfacePoint::Rectangular);

  py::enum_<Isis::SurfacePoint::CoordUnits>(surface_point, "CoordUnits")
      .value("Degrees", Isis::SurfacePoint::Degrees)
      .value("Kilometers", Isis::SurfacePoint::Kilometers)
      .value("Meters", Isis::SurfacePoint::Meters)
      .value("Radians", Isis::SurfacePoint::Radians);

  py::enum_<Isis::SurfacePoint::CoordIndex>(surface_point, "CoordIndex")
      .value("One", Isis::SurfacePoint::One)
      .value("Two", Isis::SurfacePoint::Two)
      .value("Three", Isis::SurfacePoint::Three);

  surface_point
      .def(py::init<>())
      .def(py::init<const Isis::SurfacePoint &>(), py::arg("other"))
      .def(py::init<const Isis::Latitude &, const Isis::Longitude &, const Isis::Distance &>(),
           py::arg("latitude"),
           py::arg("longitude"),
           py::arg("radius"))
      .def(py::init<const Isis::Displacement &, const Isis::Displacement &, const Isis::Displacement &>(),
           py::arg("x"),
           py::arg("y"),
           py::arg("z"))
      .def("set_rectangular_coordinates",
           &Isis::SurfacePoint::SetRectangularCoordinates,
           py::arg("x"),
           py::arg("y"),
           py::arg("z"))
      .def("set_spherical_coordinates",
           &Isis::SurfacePoint::SetSphericalCoordinates,
           py::arg("latitude"),
           py::arg("longitude"),
           py::arg("radius"))
      .def("reset_local_radius", &Isis::SurfacePoint::ResetLocalRadius, py::arg("radius"))
      .def("valid", &Isis::SurfacePoint::Valid)
      .def("get_x", &Isis::SurfacePoint::GetX)
      .def("get_y", &Isis::SurfacePoint::GetY)
      .def("get_z", &Isis::SurfacePoint::GetZ)
      .def("get_latitude", &Isis::SurfacePoint::GetLatitude)
      .def("get_longitude", &Isis::SurfacePoint::GetLongitude)
      .def("get_local_radius", &Isis::SurfacePoint::GetLocalRadius)
      .def("get_x_sigma", &Isis::SurfacePoint::GetXSigma)
      .def("get_y_sigma", &Isis::SurfacePoint::GetYSigma)
      .def("get_z_sigma", &Isis::SurfacePoint::GetZSigma)
      .def("get_lat_sigma", &Isis::SurfacePoint::GetLatSigma)
      .def("get_lon_sigma", &Isis::SurfacePoint::GetLonSigma)
      .def("get_local_radius_sigma", &Isis::SurfacePoint::GetLocalRadiusSigma)
      .def("get_distance_to_point",
           py::overload_cast<const Isis::SurfacePoint &>(&Isis::SurfacePoint::GetDistanceToPoint, py::const_),
           py::arg("other"))
      .def("to_naif_array",
           [](const Isis::SurfacePoint &self) {
             std::array<double, 3> coords{0.0, 0.0, 0.0};
             self.ToNaifArray(coords.data());
             return py::make_tuple(coords[0], coords[1], coords[2]);
           })
      .def("from_naif_array",
           [](Isis::SurfacePoint &self, py::sequence coordinates) {
             if (py::len(coordinates) != 3) {
               throw std::runtime_error("SurfacePoint.from_naif_array expects a length-3 sequence");
             }
             std::array<double, 3> coords{
                 coordinates[0].cast<double>(),
                 coordinates[1].cast<double>(),
                 coordinates[2].cast<double>()};
             self.FromNaifArray(coords.data());
           },
           py::arg("coordinates"))
      .def("latitude_to_meters", &Isis::SurfacePoint::LatitudeToMeters, py::arg("latitude"))
      .def("longitude_to_meters", &Isis::SurfacePoint::LongitudeToMeters, py::arg("longitude"))
      .def("meters_to_latitude", &Isis::SurfacePoint::MetersToLatitude, py::arg("distance_meters"))
      .def("meters_to_longitude", &Isis::SurfacePoint::MetersToLongitude, py::arg("distance_meters"))
      .def("get_coord",
           &Isis::SurfacePoint::GetCoord,
           py::arg("coordinate_type"),
           py::arg("coordinate_index"),
           py::arg("units"))
      .def("get_sigma",
           &Isis::SurfacePoint::GetSigma,
           py::arg("coordinate_type"),
           py::arg("coordinate_index"),
           py::arg("units"))
      .def("get_weight",
           &Isis::SurfacePoint::GetWeight,
           py::arg("coordinate_type"),
           py::arg("coordinate_index"))
      .def("copy", [](const Isis::SurfacePoint &self) { return Isis::SurfacePoint(self); })
      .def("__eq__", &Isis::SurfacePoint::operator==, py::arg("other"))
      .def("__repr__",
           [](const Isis::SurfacePoint &self) {
             if (!self.Valid()) {
               return std::string("SurfacePoint(invalid)");
             }
             return "SurfacePoint(lat="
                 + std::to_string(self.GetLatitude().degrees())
                 + ", lon="
                 + std::to_string(self.GetLongitude().degrees())
                 + ", radius_km="
                 + std::to_string(self.GetLocalRadius().kilometers())
                 + ")";
           });
}