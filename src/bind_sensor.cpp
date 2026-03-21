// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "Sensor.h"
#include "SurfacePoint.h"
#include "helpers.h"

namespace py = pybind11;

/**
 * @brief Binds the Sensor class to a Python module.
 *
 * This function exposes the Isis::Sensor class and its member functions
 * to Python using pybind11.
 *
 * @ingroup GroupName
 *
 * @author Geng Xun
 * @date 2026-03-21
 */  
void bind_sensor(py::module_ &m) {
  py::class_<Isis::Sensor>(m, "Sensor")
      .def("set_right_ascension_declination",
           &Isis::Sensor::SetRightAscensionDeclination,
           py::arg("right_ascension"), py::arg("declination"))
      .def("has_surface_intersection", &Isis::Sensor::HasSurfaceIntersection)
      .def("get_surface_point",
           [](const Isis::Sensor &self) {
             return Isis::SurfacePoint(self.GetSurfacePoint());
           })
      .def("universal_latitude", [](Isis::Sensor &self) { return self.UniversalLatitude(); })
               .def("universal_longitude", [](Isis::Sensor &self) { return self.UniversalLongitude(); })
      .def("phase_angle", &Isis::Sensor::PhaseAngle)
      .def("emission_angle", &Isis::Sensor::EmissionAngle)
      .def("incidence_angle", &Isis::Sensor::IncidenceAngle)
      .def("right_ascension", &Isis::Sensor::RightAscension)
      .def("declination", &Isis::Sensor::Declination)
      .def("slant_distance", &Isis::Sensor::SlantDistance)
      .def("local_solar_time", &Isis::Sensor::LocalSolarTime)
      .def("solar_distance", &Isis::Sensor::SolarDistance)
      .def("spacecraft_altitude", &Isis::Sensor::SpacecraftAltitude)
      .def("resolution", &Isis::Sensor::resolution)
      .def("ignore_elevation_model", &Isis::Sensor::IgnoreElevationModel, py::arg("ignore"))
      .def("instrument_name_long",
           [](Isis::Sensor &self) { return qStringToStdString(self.instrumentNameLong()); })
      .def("instrument_name_short",
           [](Isis::Sensor &self) { return qStringToStdString(self.instrumentNameShort()); })
      .def("spacecraft_name_long",
           [](Isis::Sensor &self) { return qStringToStdString(self.spacecraftNameLong()); })
      .def("spacecraft_name_short",
           [](Isis::Sensor &self) { return qStringToStdString(self.spacecraftNameShort()); });
}
