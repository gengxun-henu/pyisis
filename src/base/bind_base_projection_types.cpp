// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added concrete map-projection type constructors for cylindrical, azimuthal, perspective, and ring-plane projections
// Updated: 2026-04-12  Geng Xun completed Equirectangular binding with all public methods (name/version/true_scale_latitude/is_equatorial_cylindrical/set_ground/set_coordinate/xy_range/mapping methods)
// Updated: 2026-04-12  Geng Xun expanded all concrete projection types with full public method bindings (name/version/set_ground/set_coordinate/xy_range/mapping and class-specific methods)
// Updated: 2026-04-12  Geng Xun fixed QString conversion for Equirectangular name() and version() using qStringToStdString helper
// Purpose: pybind11 bindings for concrete ISIS projection types built on Projection, TProjection, and RingPlaneProjection hierarchies

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "Equirectangular.h"
#include "helpers.h"
#include "LambertAzimuthalEqualArea.h"
#include "LambertConformal.h"
#include "LunarAzimuthalEqualArea.h"
#include "Mercator.h"
#include "Mollweide.h"
#include "ObliqueCylindrical.h"
#include "Orthographic.h"
#include "Planar.h"
#include "PointPerspective.h"
#include "PolarStereographic.h"
#include "Projection.h"
#include "Pvl.h"
#include "RingCylindrical.h"
#include "RingPlaneProjection.h"
#include "Robinson.h"
#include "SimpleCylindrical.h"
#include "Sinusoidal.h"
#include "TProjection.h"
#include "TransverseMercator.h"
#include "UpturnedEllipsoidTransverseAzimuthal.h"
#include "helpers.h"

namespace py = pybind11;

namespace {

// Bind common virtual overrides for TProjection-derived projection types.
// Adds constructor(Pvl&, allow_defaults), name, version, set_ground,
// set_coordinate, xy_range, mapping, mapping_latitudes, mapping_longitudes.
template <typename TProj>
void bindTProjectionMethods(py::class_<TProj, Isis::TProjection> &cls) {
  cls.def(py::init<Isis::Pvl &, bool>(),
          py::arg("label"),
          py::arg("allow_defaults") = false)
     .def("name", [](const TProj &self) { return qStringToStdString(self.Name()); })
     .def("version", [](const TProj &self) { return qStringToStdString(self.Version()); })
     .def("set_ground", &TProj::SetGround, py::arg("lat"), py::arg("lon"))
     .def("set_coordinate", &TProj::SetCoordinate, py::arg("x"), py::arg("y"))
     .def("xy_range", [](TProj &self) {
       double minX, maxX, minY, maxY;
       bool result = self.XYRange(minX, maxX, minY, maxY);
       if (!result) {
         throw std::runtime_error("Failed to compute XY range");
       }
       return py::make_tuple(minX, maxX, minY, maxY);
     })
     .def("mapping", &TProj::Mapping)
     .def("mapping_latitudes", &TProj::MappingLatitudes)
     .def("mapping_longitudes", &TProj::MappingLongitudes);
}

// Bind common virtual overrides for RingPlaneProjection-derived types.
// Adds constructor(Pvl&, allow_defaults), name, version, set_ground,
// set_coordinate, xy_range, mapping, mapping_ring_radii, mapping_ring_longitudes.
template <typename TProj>
void bindRingProjectionMethods(py::class_<TProj, Isis::RingPlaneProjection> &cls) {
  cls.def(py::init<Isis::Pvl &, bool>(),
          py::arg("label"),
          py::arg("allow_defaults") = false)
     .def("name", [](const TProj &self) { return qStringToStdString(self.Name()); })
     .def("version", [](const TProj &self) { return qStringToStdString(self.Version()); })
     .def("set_ground", &TProj::SetGround,
          py::arg("ring_radius"), py::arg("ring_longitude"))
     .def("set_coordinate", &TProj::SetCoordinate, py::arg("x"), py::arg("y"))
     .def("xy_range", [](TProj &self) {
       double minX, maxX, minY, maxY;
       bool result = self.XYRange(minX, maxX, minY, maxY);
       if (!result) {
         throw std::runtime_error("Failed to compute XY range");
       }
       return py::make_tuple(minX, maxX, minY, maxY);
     })
     .def("mapping", &TProj::Mapping)
     .def("mapping_ring_radii", &TProj::MappingRingRadii)
     .def("mapping_ring_longitudes", &TProj::MappingRingLongitudes);
}

}  // namespace

void bind_base_projection_types(py::module_ &m) {
  // --- Equirectangular (fully bound previously) ---
  py::class_<Isis::Equirectangular, Isis::TProjection>(m, "Equirectangular")
      .def(py::init<Isis::Pvl &, bool>(),
           py::arg("label"),
           py::arg("allow_defaults") = false)
      .def("name", [](const Isis::Equirectangular &self) {
        return qStringToStdString(self.Name());
      })
      .def("version", [](const Isis::Equirectangular &self) {
        return qStringToStdString(self.Version());
      })
      .def("true_scale_latitude", &Isis::Equirectangular::TrueScaleLatitude)
      .def("is_equatorial_cylindrical", &Isis::Equirectangular::IsEquatorialCylindrical)
      .def("set_ground", &Isis::Equirectangular::SetGround,
           py::arg("lat"), py::arg("lon"))
      .def("set_coordinate", &Isis::Equirectangular::SetCoordinate,
           py::arg("x"), py::arg("y"))
      .def("xy_range", [](Isis::Equirectangular &self) {
        double minX, maxX, minY, maxY;
        bool result = self.XYRange(minX, maxX, minY, maxY);
        if (!result) {
          throw std::runtime_error("Failed to compute XY range");
        }
        return py::make_tuple(minX, maxX, minY, maxY);
      })
      .def("mapping", &Isis::Equirectangular::Mapping)
      .def("mapping_latitudes", &Isis::Equirectangular::MappingLatitudes)
      .def("mapping_longitudes", &Isis::Equirectangular::MappingLongitudes);

  // --- SimpleCylindrical ---
  {
    py::class_<Isis::SimpleCylindrical, Isis::TProjection> cls(m, "SimpleCylindrical");
    bindTProjectionMethods(cls);
    cls.def("is_equatorial_cylindrical", &Isis::SimpleCylindrical::IsEquatorialCylindrical);
  }

  // --- Sinusoidal ---
  {
    py::class_<Isis::Sinusoidal, Isis::TProjection> cls(m, "Sinusoidal");
    bindTProjectionMethods(cls);
  }

  // --- Mercator ---
  {
    py::class_<Isis::Mercator, Isis::TProjection> cls(m, "Mercator");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::Mercator::TrueScaleLatitude)
       .def("is_equatorial_cylindrical", &Isis::Mercator::IsEquatorialCylindrical);
  }

  // --- Orthographic ---
  {
    py::class_<Isis::Orthographic, Isis::TProjection> cls(m, "Orthographic");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::Orthographic::TrueScaleLatitude);
  }

  // --- PolarStereographic ---
  {
    py::class_<Isis::PolarStereographic, Isis::TProjection> cls(m, "PolarStereographic");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::PolarStereographic::TrueScaleLatitude);
  }

  // --- Mollweide ---
  {
    py::class_<Isis::Mollweide, Isis::TProjection> cls(m, "Mollweide");
    bindTProjectionMethods(cls);
    cls.def("newton_rapheson", [](Isis::Mollweide &self, double gamma) {
      double result;
      bool ok = self.newton_rapheson(gamma, result);
      if (!ok) {
        throw std::runtime_error("Newton-Rapheson iteration did not converge");
      }
      return result;
    }, py::arg("gamma"));
  }

  // --- LambertConformal ---
  {
    py::class_<Isis::LambertConformal, Isis::TProjection> cls(m, "LambertConformal");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::LambertConformal::TrueScaleLatitude);
  }

  // --- LambertAzimuthalEqualArea ---
  {
    py::class_<Isis::LambertAzimuthalEqualArea, Isis::TProjection> cls(m, "LambertAzimuthalEqualArea");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::LambertAzimuthalEqualArea::TrueScaleLatitude)
       .def("relative_scale_factor_longitude", &Isis::LambertAzimuthalEqualArea::relativeScaleFactorLongitude)
       .def("relative_scale_factor_latitude", &Isis::LambertAzimuthalEqualArea::relativeScaleFactorLatitude);
  }

  // --- LunarAzimuthalEqualArea (no allow_defaults, no MappingLatitudes/MappingLongitudes) ---
  py::class_<Isis::LunarAzimuthalEqualArea, Isis::TProjection>(m, "LunarAzimuthalEqualArea")
      .def(py::init<Isis::Pvl &>(), py::arg("label"))
      .def("name", [](const Isis::LunarAzimuthalEqualArea &self) {
        return qStringToStdString(self.Name());
      })
      .def("version", [](const Isis::LunarAzimuthalEqualArea &self) {
        return qStringToStdString(self.Version());
      })
      .def("set_ground", &Isis::LunarAzimuthalEqualArea::SetGround,
           py::arg("lat"), py::arg("lon"))
      .def("set_coordinate", &Isis::LunarAzimuthalEqualArea::SetCoordinate,
           py::arg("x"), py::arg("y"))
      .def("xy_range", [](Isis::LunarAzimuthalEqualArea &self) {
        double minX, maxX, minY, maxY;
        bool result = self.XYRange(minX, maxX, minY, maxY);
        if (!result) {
          throw std::runtime_error("Failed to compute XY range");
        }
        return py::make_tuple(minX, maxX, minY, maxY);
      })
      .def("mapping", &Isis::LunarAzimuthalEqualArea::Mapping);

  // --- ObliqueCylindrical ---
  {
    py::class_<Isis::ObliqueCylindrical, Isis::TProjection> cls(m, "ObliqueCylindrical");
    bindTProjectionMethods(cls);
    cls.def("pole_latitude", &Isis::ObliqueCylindrical::poleLatitude)
       .def("pole_longitude", &Isis::ObliqueCylindrical::poleLongitude)
       .def("pole_rotation", &Isis::ObliqueCylindrical::poleRotation);
  }

  // --- PointPerspective ---
  {
    py::class_<Isis::PointPerspective, Isis::TProjection> cls(m, "PointPerspective");
    bindTProjectionMethods(cls);
    cls.def("true_scale_latitude", &Isis::PointPerspective::TrueScaleLatitude);
  }

  // --- Robinson ---
  {
    py::class_<Isis::Robinson, Isis::TProjection> cls(m, "Robinson");
    bindTProjectionMethods(cls);
  }

  // --- TransverseMercator ---
  {
    py::class_<Isis::TransverseMercator, Isis::TProjection> cls(m, "TransverseMercator");
    bindTProjectionMethods(cls);
  }

  // --- UpturnedEllipsoidTransverseAzimuthal ---
  {
    py::class_<Isis::UpturnedEllipsoidTransverseAzimuthal, Isis::TProjection> cls(
        m, "UpturnedEllipsoidTransverseAzimuthal");
    bindTProjectionMethods(cls);
  }

  // --- Planar (RingPlaneProjection) ---
  {
    py::class_<Isis::Planar, Isis::RingPlaneProjection> cls(m, "Planar");
    bindRingProjectionMethods(cls);
    cls.def("true_scale_ring_radius", &Isis::Planar::TrueScaleRingRadius)
       .def("center_ring_longitude", &Isis::Planar::CenterRingLongitude)
       .def("center_ring_radius", &Isis::Planar::CenterRingRadius);
  }

  // --- RingCylindrical (RingPlaneProjection) ---
  {
    py::class_<Isis::RingCylindrical, Isis::RingPlaneProjection> cls(m, "RingCylindrical");
    bindRingProjectionMethods(cls);
    cls.def("is_equatorial_cylindrical", &Isis::RingCylindrical::IsEquatorialCylindrical)
       .def("true_scale_ring_radius", &Isis::RingCylindrical::TrueScaleRingRadius)
       .def("center_ring_longitude", &Isis::RingCylindrical::CenterRingLongitude)
       .def("center_ring_radius", &Isis::RingCylindrical::CenterRingRadius);
  }
}