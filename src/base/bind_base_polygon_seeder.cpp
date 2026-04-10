// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/base/objs/PolygonSeeder/PolygonSeeder.h
// - reference/upstream_isis/src/base/objs/GridPolygonSeeder/GridPolygonSeeder.h
// - reference/upstream_isis/src/base/objs/LimitPolygonSeeder/LimitPolygonSeeder.h
// - reference/upstream_isis/src/base/objs/StripPolygonSeeder/StripPolygonSeeder.h
// - reference/upstream_isis/src/base/objs/PolygonSeederFactory/PolygonSeederFactory.h
// Source classes: PolygonSeeder, GridPolygonSeeder, LimitPolygonSeeder,
//                 StripPolygonSeeder, PolygonSeederFactory
// Source header author(s): not explicitly stated in upstream headers
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun added PolygonSeeder family bindings
//                       (abstract base + Grid/Limit/Strip subclasses + factory).
// Purpose: Expose PolygonSeeder abstract base, GridPolygonSeeder, LimitPolygonSeeder,
//          StripPolygonSeeder, and PolygonSeederFactory to Python via pybind11.

#include <memory>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "GridPolygonSeeder.h"
#include "LimitPolygonSeeder.h"
#include "PolygonSeeder.h"
#include "PolygonSeederFactory.h"
#include "Pvl.h"
#include "PvlGroup.h"
#include "StripPolygonSeeder.h"

#include "helpers.h"

namespace py = pybind11;

void bind_base_polygon_seeder(py::module_ &m) {
  // PolygonSeeder — abstract base class for polygon point-seeding algorithms.
  // Cannot be instantiated directly from Python; use a concrete subclass or factory.
  // Added: 2026-04-10
  py::class_<Isis::PolygonSeeder,
             std::unique_ptr<Isis::PolygonSeeder, py::nodelete>>(m, "PolygonSeeder")
      .def("minimum_thickness", &Isis::PolygonSeeder::MinimumThickness,
           "Return the minimum thickness threshold for seeding a polygon.")
      .def("minimum_area", &Isis::PolygonSeeder::MinimumArea,
           "Return the minimum area threshold for seeding a polygon.")
      .def("algorithm", &Isis::PolygonSeeder::Algorithm,
           "Return the name of the seeding algorithm.")
      .def("plugin_parameters",
           [](Isis::PolygonSeeder &self, const std::string &grpName) {
             return self.PluginParameters(QString::fromStdString(grpName));
           },
           py::arg("grp_name"),
           "Return the plugin parameters as a PvlGroup for this seeder algorithm.")
      .def("invalid_input", &Isis::PolygonSeeder::InvalidInput,
           "Return the leftover (unconsumed) Pvl input as a Pvl object.")
      .def("__repr__", [](Isis::PolygonSeeder &s) {
        return "<PolygonSeeder algorithm='" + s.Algorithm().toStdString() + "'>";
      });

  // GridPolygonSeeder — seeds points on a regular grid within a polygon.
  // Added: 2026-04-10
  py::class_<Isis::GridPolygonSeeder, Isis::PolygonSeeder>(m, "GridPolygonSeeder")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct a GridPolygonSeeder from PVL configuration.\n\n"
           "The PVL must contain an Object=AutoSeed with a Group=PolygonSeederAlgorithm\n"
           "that includes Name=Grid, XSpacing, and YSpacing (plus optional\n"
           "MinimumThickness, MinimumArea, SubGrid).")
      .def("sub_grid", &Isis::GridPolygonSeeder::SubGrid,
           "Return True if sub-grid seeding is enabled.")
      .def("plugin_parameters",
           [](Isis::GridPolygonSeeder &self, const std::string &grpName) {
             return self.PluginParameters(QString::fromStdString(grpName));
           },
           py::arg("grp_name"),
           "Return the plugin parameters as a PvlGroup for this grid seeder.")
      .def("__repr__", [](Isis::GridPolygonSeeder &s) {
        return "<GridPolygonSeeder algorithm='" + s.Algorithm().toStdString()
               + "' sub_grid=" + (s.SubGrid() ? "True" : "False") + ">";
      });

  // LimitPolygonSeeder — seeds points using major/minor axis limits within a polygon.
  // Added: 2026-04-10
  py::class_<Isis::LimitPolygonSeeder, Isis::PolygonSeeder>(m, "LimitPolygonSeeder")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct a LimitPolygonSeeder from PVL configuration.\n\n"
           "The PVL must contain an Object=AutoSeed with a Group=PolygonSeederAlgorithm\n"
           "that includes Name=Limit, MajorAxisPoints, MinorAxisPoints (plus optional\n"
           "MinimumThickness, MinimumArea).")
      .def("plugin_parameters",
           [](Isis::LimitPolygonSeeder &self, const std::string &grpName) {
             return self.PluginParameters(QString::fromStdString(grpName));
           },
           py::arg("grp_name"),
           "Return the plugin parameters as a PvlGroup for this limit seeder.")
      .def("__repr__", [](Isis::LimitPolygonSeeder &s) {
        return "<LimitPolygonSeeder algorithm='" + s.Algorithm().toStdString() + "'>";
      });

  // StripPolygonSeeder — seeds pairs of offset points in a staggered-strip pattern.
  // Added: 2026-04-10
  py::class_<Isis::StripPolygonSeeder, Isis::PolygonSeeder>(m, "StripPolygonSeeder")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct a StripPolygonSeeder from PVL configuration.\n\n"
           "The PVL must contain an Object=AutoSeed with a Group=PolygonSeederAlgorithm\n"
           "that includes Name=Strip, XSpacing, YSpacing (plus optional\n"
           "MinimumThickness, MinimumArea).")
      .def("plugin_parameters",
           [](Isis::StripPolygonSeeder &self, const std::string &grpName) {
             return self.PluginParameters(QString::fromStdString(grpName));
           },
           py::arg("grp_name"),
           "Return the plugin parameters as a PvlGroup for this strip seeder.")
      .def("__repr__", [](Isis::StripPolygonSeeder &s) {
        return "<StripPolygonSeeder algorithm='" + s.Algorithm().toStdString() + "'>";
      });

  // PolygonSeederFactory — static factory for creating PolygonSeeder instances from PVL.
  // Added: 2026-04-10
  py::class_<Isis::PolygonSeederFactory,
             std::unique_ptr<Isis::PolygonSeederFactory, py::nodelete>>(
      m, "PolygonSeederFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl) -> Isis::PolygonSeeder * {
                    return Isis::PolygonSeederFactory::Create(pvl);
                  },
                  py::arg("pvl"),
                  py::return_value_policy::take_ownership,
                  "Create a PolygonSeeder instance from PVL configuration.\n\n"
                  "The PVL must contain an Object=AutoSeed with a\n"
                  "Group=PolygonSeederAlgorithm that includes Name=<algorithm>\n"
                  "(e.g. Grid, Limit, Strip). Requires ISISROOT/lib/PolygonSeeder.plugin.\n\n"
                  "Parameters\n"
                  "----------\n"
                  "pvl : Pvl\n"
                  "    PVL object containing the PolygonSeeder configuration.\n\n"
                  "Returns\n"
                  "-------\n"
                  "PolygonSeeder\n"
                  "    A concrete PolygonSeeder subclass instance.\n\n"
                  "Raises\n"
                  "------\n"
                  "IException\n"
                  "    If the configuration is invalid or ISISROOT is not set.");
}
