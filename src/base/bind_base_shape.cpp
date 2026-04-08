// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added ShapeModel hierarchy bindings covering ellipsoid, DEM, plane, DSK, Embree, and Bullet-backed shape helpers
// Purpose: pybind11 bindings for ISIS shape-model abstractions and concrete surface-intersection implementations

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <QVector>

#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "BulletShapeModel.h"
#include "DemShape.h"
#include "Distance.h"
#include "EllipsoidShape.h"
#include "EmbreeShapeModel.h"
#include "Latitude.h"
#include "Longitude.h"
#include "NaifDskShape.h"
#include "PlaneShape.h"
#include "ShapeModel.h"
#include "SurfacePoint.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
std::vector<double> qVectorToStdVector(const QVector<double> &values) {
  return std::vector<double>(values.begin(), values.end());
}
}  // namespace

void bind_base_shape(py::module_ &m) {
  py::class_<Isis::ShapeModel> shape_model(m, "ShapeModel");

  shape_model
      .def("name", [](const Isis::ShapeModel &self) { return qStringToStdString(self.name()); })
      .def("surface_intersection",
           [](Isis::ShapeModel &self) -> Isis::SurfacePoint & { return *self.surfaceIntersection(); },
           py::return_value_policy::reference_internal)
      .def("has_intersection", &Isis::ShapeModel::hasIntersection)
      .def("has_normal", &Isis::ShapeModel::hasNormal)
      .def("has_local_normal", &Isis::ShapeModel::hasLocalNormal)
      .def("clear_surface_point", &Isis::ShapeModel::clearSurfacePoint)
      .def("emission_angle", &Isis::ShapeModel::emissionAngle, py::arg("observer_body_fixed_position"))
      .def("incidence_angle", &Isis::ShapeModel::incidenceAngle, py::arg("illuminator_body_fixed_position"))
      .def("phase_angle", &Isis::ShapeModel::phaseAngle, py::arg("observer_body_fixed_position"), py::arg("illuminator_body_fixed_position"))
      .def("local_radius", &Isis::ShapeModel::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("is_dem", &Isis::ShapeModel::isDEM)
      .def("set_has_intersection", &Isis::ShapeModel::setHasIntersection, py::arg("has_intersection"))
      .def("set_surface_point", &Isis::ShapeModel::setSurfacePoint, py::arg("surface_point"))
      .def("normal", &Isis::ShapeModel::normal)
      .def("local_normal", &Isis::ShapeModel::localNormal)
      .def("is_visible_from", &Isis::ShapeModel::isVisibleFrom, py::arg("observer_position"), py::arg("look_direction"))
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::ShapeModel::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("intersect_surface",
           py::overload_cast<const Isis::Latitude &, const Isis::Longitude &, const std::vector<double> &, const bool &>(&Isis::ShapeModel::intersectSurface),
           py::arg("latitude"),
           py::arg("longitude"),
           py::arg("observer_position"),
           py::arg("back_check") = true)
      .def("intersect_surface",
           py::overload_cast<const Isis::SurfacePoint &, const std::vector<double> &, const bool &>(&Isis::ShapeModel::intersectSurface),
           py::arg("surface_point"),
           py::arg("observer_position"),
           py::arg("back_check") = true)
      .def("calculate_default_normal", &Isis::ShapeModel::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::ShapeModel::calculateSurfaceNormal)
      .def("__repr__",
           [](const Isis::ShapeModel &self) {
             return "ShapeModel('" + qStringToStdString(self.name()) + "')";
           });

  py::class_<Isis::EllipsoidShape, Isis::ShapeModel>(m, "EllipsoidShape")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::EllipsoidShape::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("calculate_default_normal", &Isis::EllipsoidShape::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::EllipsoidShape::calculateSurfaceNormal)
      .def("local_radius", &Isis::EllipsoidShape::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("is_dem", &Isis::EllipsoidShape::isDEM);

  py::class_<Isis::DemShape, Isis::ShapeModel>(m, "DemShape")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::DemShape::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("local_radius", &Isis::DemShape::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("dem_scale", &Isis::DemShape::demScale)
      .def("calculate_default_normal", &Isis::DemShape::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::DemShape::calculateSurfaceNormal)
      .def("is_dem", &Isis::DemShape::isDEM);

  py::class_<Isis::PlaneShape, Isis::ShapeModel>(m, "PlaneShape")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::PlaneShape::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("calculate_default_normal", &Isis::PlaneShape::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::PlaneShape::calculateSurfaceNormal)
      .def("emission_angle", &Isis::PlaneShape::emissionAngle, py::arg("observer_body_fixed_position"))
      .def("incidence_angle", &Isis::PlaneShape::incidenceAngle, py::arg("illuminator_body_fixed_position"))
      .def("local_radius", &Isis::PlaneShape::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("is_dem", &Isis::PlaneShape::isDEM);

  py::class_<Isis::NaifDskShape, Isis::ShapeModel>(m, "NaifDskShape")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::NaifDskShape::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("intersect_surface",
           py::overload_cast<const Isis::SurfacePoint &, const std::vector<double> &, const bool &>(&Isis::NaifDskShape::intersectSurface),
           py::arg("surface_point"),
           py::arg("observer_position"),
           py::arg("back_check") = true)
      .def("calculate_default_normal", &Isis::NaifDskShape::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::NaifDskShape::calculateSurfaceNormal)
      .def("local_radius", &Isis::NaifDskShape::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("ellipsoid_normal", [](Isis::NaifDskShape &self) { return qVectorToStdVector(self.ellipsoidNormal()); })
      .def("is_dem", &Isis::NaifDskShape::isDEM);

  py::class_<Isis::EmbreeShapeModel, Isis::ShapeModel>(m, "EmbreeShapeModel")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::EmbreeShapeModel::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("intersect_surface",
           py::overload_cast<const Isis::Latitude &, const Isis::Longitude &, const std::vector<double> &, const bool &>(&Isis::EmbreeShapeModel::intersectSurface),
           py::arg("latitude"),
           py::arg("longitude"),
           py::arg("observer_position"),
           py::arg("back_check") = true)
      .def("intersect_surface",
           py::overload_cast<const Isis::SurfacePoint &, const std::vector<double> &, const bool &>(&Isis::EmbreeShapeModel::intersectSurface),
           py::arg("surface_point"),
           py::arg("observer_position"),
           py::arg("back_check") = true)
      .def("clear_surface_point", &Isis::EmbreeShapeModel::clearSurfacePoint)
      .def("is_dem", &Isis::EmbreeShapeModel::isDEM)
      .def("get_tolerance", &Isis::EmbreeShapeModel::getTolerance)
      .def("set_tolerance", &Isis::EmbreeShapeModel::setTolerance, py::arg("tolerance"))
      .def("calculate_default_normal", &Isis::EmbreeShapeModel::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::EmbreeShapeModel::calculateSurfaceNormal)
      .def("ellipsoid_normal", [](Isis::EmbreeShapeModel &self) { return qVectorToStdVector(self.ellipsoidNormal()); })
      .def("incidence_angle", &Isis::EmbreeShapeModel::incidenceAngle, py::arg("illuminator_body_fixed_position"))
      .def("local_radius", &Isis::EmbreeShapeModel::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("is_visible_from", &Isis::EmbreeShapeModel::isVisibleFrom, py::arg("observer_position"), py::arg("look_direction"));

  py::class_<Isis::BulletShapeModel, Isis::ShapeModel>(m, "BulletShapeModel")
      .def(py::init<>())
      .def("intersect_surface",
           py::overload_cast<std::vector<double>, std::vector<double>>(&Isis::BulletShapeModel::intersectSurface),
           py::arg("observer_position"),
           py::arg("look_direction"))
      .def("intersect_surface",
           py::overload_cast<const Isis::Latitude &, const Isis::Longitude &, const std::vector<double> &, const bool &>(&Isis::BulletShapeModel::intersectSurface),
           py::arg("latitude"),
           py::arg("longitude"),
           py::arg("observer_position"),
           py::arg("check_occlusion") = true)
      .def("intersect_surface",
           py::overload_cast<const Isis::SurfacePoint &, const std::vector<double> &, const bool &>(&Isis::BulletShapeModel::intersectSurface),
           py::arg("surface_point"),
           py::arg("observer_position"),
           py::arg("check_occlusion") = true)
      .def("set_surface_point", &Isis::BulletShapeModel::setSurfacePoint, py::arg("surface_point"))
      .def("clear_surface_point", &Isis::BulletShapeModel::clearSurfacePoint)
      .def("calculate_default_normal", &Isis::BulletShapeModel::calculateDefaultNormal)
      .def("calculate_surface_normal", &Isis::BulletShapeModel::calculateSurfaceNormal)
      .def("local_radius", &Isis::BulletShapeModel::localRadius, py::arg("latitude"), py::arg("longitude"))
      .def("ellipsoid_normal", [](Isis::BulletShapeModel &self) { return qVectorToStdVector(self.ellipsoidNormal()); })
      .def("get_tolerance", &Isis::BulletShapeModel::getTolerance)
      .def("set_tolerance", &Isis::BulletShapeModel::setTolerance, py::arg("tolerance"))
      .def("is_dem", &Isis::BulletShapeModel::isDEM)
      .def("is_visible_from", &Isis::BulletShapeModel::isVisibleFrom, py::arg("observer_position"), py::arg("look_direction"));
}