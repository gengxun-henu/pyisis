// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/base/objs/SpicePosition/SpicePosition.h
// - reference/upstream_isis/src/base/objs/SpiceRotation/SpiceRotation.h
// - reference/upstream_isis/src/base/objs/Spice/SpacecraftPosition.h
// Source classes: Isis::SpicePosition, Isis::SpiceRotation, Isis::SpacecraftPosition
// Source header author(s): Jeff Anderson (SpicePosition); Debbie A. Cook (SpiceRotation);
//                          Kris Becker (SpacecraftPosition)
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun added SpicePosition, SpiceRotation, SpacecraftPosition bindings.
// Purpose: Expose Isis::SpicePosition, Isis::SpiceRotation, and Isis::SpacecraftPosition
//          to Python for SPICE-based spacecraft navigation access.

#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Distance.h"
#include "IException.h"
#include "LightTimeCorrectionState.h"
#include "SpicePosition.h"
#include "SpiceRotation.h"
#include "SpacecraftPosition.h"
#include "helpers.h"

namespace py = pybind11;

void bind_spice_navigation(py::module_ &m)
{
  // -----------------------------------------------------------------------
  // SpicePosition enums
  // -----------------------------------------------------------------------
  py::enum_<Isis::SpicePosition::Source>(m, "SpicePositionSource")
      .value("Spice",                         Isis::SpicePosition::Spice)
      .value("Memcache",                       Isis::SpicePosition::Memcache)
      .value("HermiteCache",                   Isis::SpicePosition::HermiteCache)
      .value("PolyFunction",                   Isis::SpicePosition::PolyFunction)
      .value("PolyFunctionOverHermiteConstant",
             Isis::SpicePosition::PolyFunctionOverHermiteConstant)
      .export_values();

  py::enum_<Isis::SpicePosition::PartialType>(m, "SpicePositionPartialType")
      .value("WRT_X", Isis::SpicePosition::WRT_X)
      .value("WRT_Y", Isis::SpicePosition::WRT_Y)
      .value("WRT_Z", Isis::SpicePosition::WRT_Z)
      .export_values();

  // -----------------------------------------------------------------------
  // SpicePosition
  // -----------------------------------------------------------------------
  py::class_<Isis::SpicePosition>(m, "SpicePosition")
      .def(py::init<int, int>(),
           py::arg("target_code"), py::arg("observer_code"),
           "Construct SpicePosition with NAIF target and observer body codes.")
      .def("set_time_bias",
           &Isis::SpicePosition::SetTimeBias,
           py::arg("time_bias"),
           "Set time bias in seconds to adjust ephemeris time.")
      .def("get_time_bias",
           &Isis::SpicePosition::GetTimeBias,
           "Return the current time bias in seconds.")
      .def("set_aberration_correction",
           [](Isis::SpicePosition &self, const std::string &correction) {
               self.SetAberrationCorrection(stdStringToQString(correction));
           },
           py::arg("correction"),
           "Set aberration correction mode (e.g. 'LT+S', 'NONE').")
      .def("get_aberration_correction",
           [](Isis::SpicePosition &self) {
               return qStringToStdString(self.GetAberrationCorrection());
           },
           "Return the current aberration correction mode string.")
      .def("get_light_time",
           &Isis::SpicePosition::GetLightTime,
           "Return the one-way light time in seconds.")
      .def("ephemeris_time",
           [](Isis::SpicePosition &self) { return self.EphemerisTime(); },
           "Return the current ephemeris time (ET) in seconds.")
      .def("scaled_time",
           &Isis::SpicePosition::scaledTime,
           "Return time scaled by the base time and time scale.")
      .def("has_velocity",
           [](Isis::SpicePosition &self) { return self.HasVelocity(); },
           "Return True if velocity information is available.")
      .def("is_cached",
           &Isis::SpicePosition::IsCached,
           "Return True if position data is cached.")
      .def("cache_size",
           &Isis::SpicePosition::cacheSize,
           "Return the number of cached positions.")
      .def("get_base_time",
           [](Isis::SpicePosition &self) { return self.GetBaseTime(); },
           "Return the base time used to scale polynomial coefficients.")
      .def("get_time_scale",
           [](Isis::SpicePosition &self) { return self.GetTimeScale(); },
           "Return the time scale used to normalize polynomial coefficients.")
      .def("__repr__", [](const Isis::SpicePosition &) {
           return std::string("SpicePosition()");
      });

  // -----------------------------------------------------------------------
  // SpiceRotation enums
  // -----------------------------------------------------------------------
  py::enum_<Isis::SpiceRotation::Source>(m, "SpiceRotationSource")
      .value("Spice",                    Isis::SpiceRotation::Spice)
      .value("Nadir",                    Isis::SpiceRotation::Nadir)
      .value("Memcache",                  Isis::SpiceRotation::Memcache)
      .value("PolyFunction",              Isis::SpiceRotation::PolyFunction)
      .value("PolyFunctionOverSpice",     Isis::SpiceRotation::PolyFunctionOverSpice)
      .value("PckPolyFunction",           Isis::SpiceRotation::PckPolyFunction)
      .export_values();

  py::enum_<Isis::SpiceRotation::PartialType>(m, "SpiceRotationPartialType")
      .value("WRT_RightAscension", Isis::SpiceRotation::WRT_RightAscension)
      .value("WRT_Declination",    Isis::SpiceRotation::WRT_Declination)
      .value("WRT_Twist",          Isis::SpiceRotation::WRT_Twist)
      .export_values();

  py::enum_<Isis::SpiceRotation::DownsizeStatus>(m, "SpiceRotationDownsizeStatus")
      .value("Yes",  Isis::SpiceRotation::Yes)
      .value("Done", Isis::SpiceRotation::Done)
      .value("No",   Isis::SpiceRotation::No)
      .export_values();

  py::enum_<Isis::SpiceRotation::FrameType>(m, "SpiceRotationFrameType")
      .value("UNKNOWN",     Isis::SpiceRotation::UNKNOWN)
      .value("INERTL",      Isis::SpiceRotation::INERTL)
      .value("PCK",         Isis::SpiceRotation::PCK)
      .value("CK",          Isis::SpiceRotation::CK)
      .value("TK",          Isis::SpiceRotation::TK)
      .value("DYN",         Isis::SpiceRotation::DYN)
      .value("BPC",         Isis::SpiceRotation::BPC)
      .value("NOTJ2000PCK", Isis::SpiceRotation::NOTJ2000PCK)
      .export_values();

  // -----------------------------------------------------------------------
  // SpiceRotation
  // -----------------------------------------------------------------------
  py::class_<Isis::SpiceRotation>(m, "SpiceRotation")
      .def(py::init<int>(),
           py::arg("frame_code"),
           "Construct SpiceRotation with NAIF frame code.")
      .def(py::init<int, int>(),
           py::arg("frame_code"), py::arg("target_code"),
           "Construct SpiceRotation with NAIF frame and target body codes.")
      .def("set_frame",
           &Isis::SpiceRotation::SetFrame,
           py::arg("frame_code"),
           "Set the NAIF frame code.")
      .def("frame",
           &Isis::SpiceRotation::Frame,
           "Return the NAIF frame code.")
      .def("set_time_bias",
           &Isis::SpiceRotation::SetTimeBias,
           py::arg("time_bias"),
           "Set time bias in seconds.")
      .def("ephemeris_time",
           &Isis::SpiceRotation::EphemerisTime,
           "Return the current ephemeris time.")
      .def("is_cached",
           &Isis::SpiceRotation::IsCached,
           "Return True if rotation data is cached.")
      .def("cache_size",
           [](Isis::SpiceRotation &self) { return self.cacheSize(); },
           "Return the number of cached rotations.")
      .def("get_base_time",
           [](Isis::SpiceRotation &self) { return self.GetBaseTime(); },
           "Return the base time for polynomial scaling.")
      .def("get_time_scale",
           [](Isis::SpiceRotation &self) { return self.GetTimeScale(); },
           "Return the time scale for polynomial normalization.")
      .def("get_source",
           [](Isis::SpiceRotation &self) { return self.GetSource(); },
           "Return the current rotation source type.")
      .def("has_angular_velocity",
           &Isis::SpiceRotation::HasAngularVelocity,
           "Return True if angular velocity is available.")
      .def("j2000_vector",
           [](Isis::SpiceRotation &self, const std::vector<double> &rVec) {
               return self.J2000Vector(rVec);
           },
           py::arg("r_vec"),
           "Rotate a body-fixed vector to J2000.")
      .def("reference_vector",
           [](Isis::SpiceRotation &self, const std::vector<double> &jVec) {
               return self.ReferenceVector(jVec);
           },
           py::arg("j_vec"),
           "Rotate a J2000 vector to the body-fixed reference frame.")
      .def("__repr__", [](Isis::SpiceRotation &self) {
           return std::string("SpiceRotation(frame=") +
                  std::to_string(self.Frame()) + ")";
      });

  // -----------------------------------------------------------------------
  // SpacecraftPosition (inherits SpicePosition)
  // -----------------------------------------------------------------------
  py::class_<Isis::SpacecraftPosition, Isis::SpicePosition>(m, "SpacecraftPosition")
      .def(py::init([](int targetCode, int observerCode) {
               return std::make_unique<Isis::SpacecraftPosition>(
                   targetCode, observerCode);
           }),
           py::arg("target_code"), py::arg("observer_code"),
           "Construct SpacecraftPosition with NAIF target and observer codes.")
      .def(py::init([](int targetCode, int observerCode,
                       const Isis::LightTimeCorrectionState &ltState,
                       const Isis::Distance &radius) {
               return std::make_unique<Isis::SpacecraftPosition>(
                   targetCode, observerCode, ltState, radius);
           }),
           py::arg("target_code"), py::arg("observer_code"),
           py::arg("lt_state"), py::arg("radius"),
           "Construct SpacecraftPosition with light-time correction state and target radius.")
      .def("get_radius_light_time",
           &Isis::SpacecraftPosition::getRadiusLightTime,
           "Return the light-time correction to the target body surface.")
      .def_static("get_distance_light_time",
                  &Isis::SpacecraftPosition::getDistanceLightTime,
                  py::arg("distance"),
                  "Return one-way light travel time for the given distance.")
      .def("get_light_time_state",
           &Isis::SpacecraftPosition::getLightTimeState,
           py::return_value_policy::reference_internal,
           "Return the LightTimeCorrectionState controlling light-time behavior.")
      .def("set_aberration_correction",
           [](Isis::SpacecraftPosition &self, const std::string &correction) {
               self.SetAberrationCorrection(stdStringToQString(correction));
           },
           py::arg("correction"),
           "Override aberration correction mode.")
      .def("get_aberration_correction",
           [](Isis::SpacecraftPosition &self) {
               return qStringToStdString(self.GetAberrationCorrection());
           },
           "Return the current aberration correction mode.")
      .def("__repr__", [](const Isis::SpacecraftPosition &) {
           return std::string("SpacecraftPosition()");
      });
}
