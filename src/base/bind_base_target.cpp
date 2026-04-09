// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-26  Geng Xun expanded target bindings with shape access, NAIF lookup helpers, and ShapeModelFactory creation support
// Updated: 2026-04-09  Geng Xun added Target NAIF/frame coefficient accessors for camera-derived targets with active SPICE state
// Purpose: pybind11 bindings for ISIS Target metadata, shape attachment helpers, and ShapeModelFactory construction

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Angle.h"
#include "Distance.h"
#include "Pvl.h"
#include "ShapeModel.h"
#include "ShapeModelFactory.h"
#include "Target.h"
#include "helpers.h"

namespace py = pybind11;

void bind_base_target(py::module_ &m) {
  py::class_<Isis::Target> target(m, "Target");

  target
      .def(py::init<Isis::Pvl &>(), py::arg("label"))
      .def("is_sky", &Isis::Target::isSky)
      .def("naif_body_code", &Isis::Target::naifBodyCode)
      .def("naif_planet_system_code", &Isis::Target::naifPlanetSystemCode)
      .def("name", [](const Isis::Target &self) { return qStringToStdString(self.name()); })
      .def("system_name", [](const Isis::Target &self) { return qStringToStdString(self.systemName()); })
      .def("radii", &Isis::Target::radii)
      .def("restore_shape", &Isis::Target::restoreShape)
      .def("set_shape_ellipsoid", &Isis::Target::setShapeEllipsoid)
      .def("set_radii", &Isis::Target::setRadii, py::arg("radii"))
      .def("set_name",
           [](Isis::Target &self, const std::string &name) {
             self.setName(stdStringToQString(name));
           },
           py::arg("name"))
      .def("frame_type", &Isis::Target::frameType)
      .def("pole_ra_coefs", &Isis::Target::poleRaCoefs)
      .def("pole_dec_coefs", &Isis::Target::poleDecCoefs)
      .def("pm_coefs", &Isis::Target::pmCoefs)
      .def("pole_ra_nut_prec_coefs", &Isis::Target::poleRaNutPrecCoefs)
      .def("pole_dec_nut_prec_coefs", &Isis::Target::poleDecNutPrecCoefs)
      .def("pm_nut_prec_coefs", &Isis::Target::pmNutPrecCoefs)
      .def("sys_nut_prec_constants", &Isis::Target::sysNutPrecConstants)
      .def("sys_nut_prec_coefs", &Isis::Target::sysNutPrecCoefs)
      .def("shape",
           [](Isis::Target &self) -> py::object {
             Isis::ShapeModel *shape = self.shape();
             if (!shape) {
               return py::none();
             }
             return py::cast(shape, py::return_value_policy::reference_internal, py::cast(&self));
           })
      .def_static("lookup_naif_body_code",
                  [](const std::string &name) {
                    return Isis::Target::lookupNaifBodyCode(stdStringToQString(name));
                  },
                  py::arg("name"))
      .def_static("radii_group_for_target",
                  [](const std::string &target_name) {
                    return Isis::Target::radiiGroup(stdStringToQString(target_name));
                  },
                  py::arg("target_name"))
      .def_static("radii_group_from_label",
                  [](Isis::Pvl &label, const Isis::PvlGroup &mapping_group) {
                    return Isis::Target::radiiGroup(label, mapping_group);
                  },
                  py::arg("label"),
                  py::arg("mapping_group"))
      .def("__repr__", [](const Isis::Target &self) {
        std::string name = qStringToStdString(self.name());
        return "Target(name='" + name + "')";
      });

  py::class_<Isis::ShapeModelFactory, std::unique_ptr<Isis::ShapeModelFactory, py::nodelete>>(m, "ShapeModelFactory")
      .def_static("create",
                  [](Isis::Target &target, Isis::Pvl &label) {
                    return Isis::ShapeModelFactory::create(&target, label);
                  },
                  py::arg("target"),
                  py::arg("label"));
}