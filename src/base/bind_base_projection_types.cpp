// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added concrete map-projection type constructors for cylindrical, azimuthal, perspective, and ring-plane projections
// Purpose: pybind11 bindings for concrete ISIS projection types built on Projection, TProjection, and RingPlaneProjection hierarchies

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "Equirectangular.h"
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

namespace py = pybind11;

namespace {
template <typename TProjectionLike, typename TBase>
void bindProjectionType(py::module_ &m, const char *python_name) {
  py::class_<TProjectionLike, TBase>(m, python_name)
      .def(py::init<Isis::Pvl &, bool>(),
           py::arg("label"),
           py::arg("allow_defaults") = false);
}
}  // namespace

void bind_base_projection_types(py::module_ &m) {
  bindProjectionType<Isis::Equirectangular, Isis::TProjection>(m, "Equirectangular");
  bindProjectionType<Isis::SimpleCylindrical, Isis::TProjection>(m, "SimpleCylindrical");
  bindProjectionType<Isis::Sinusoidal, Isis::TProjection>(m, "Sinusoidal");
  bindProjectionType<Isis::Mercator, Isis::TProjection>(m, "Mercator");
  bindProjectionType<Isis::Orthographic, Isis::TProjection>(m, "Orthographic");
  bindProjectionType<Isis::PolarStereographic, Isis::TProjection>(m, "PolarStereographic");
  bindProjectionType<Isis::Mollweide, Isis::TProjection>(m, "Mollweide");
  bindProjectionType<Isis::LambertConformal, Isis::TProjection>(m, "LambertConformal");
  bindProjectionType<Isis::LambertAzimuthalEqualArea, Isis::TProjection>(m, "LambertAzimuthalEqualArea");
  py::class_<Isis::LunarAzimuthalEqualArea, Isis::TProjection>(m, "LunarAzimuthalEqualArea")
      .def(py::init<Isis::Pvl &>(), py::arg("label"));
  bindProjectionType<Isis::ObliqueCylindrical, Isis::TProjection>(m, "ObliqueCylindrical");
  bindProjectionType<Isis::PointPerspective, Isis::TProjection>(m, "PointPerspective");
  bindProjectionType<Isis::Robinson, Isis::TProjection>(m, "Robinson");
  bindProjectionType<Isis::TransverseMercator, Isis::TProjection>(m, "TransverseMercator");
  bindProjectionType<Isis::UpturnedEllipsoidTransverseAzimuthal, Isis::TProjection>(m, "UpturnedEllipsoidTransverseAzimuthal");

  bindProjectionType<Isis::Planar, Isis::RingPlaneProjection>(m, "Planar");
  bindProjectionType<Isis::RingCylindrical, Isis::RingPlaneProjection>(m, "RingCylindrical");
}