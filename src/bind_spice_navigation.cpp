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
// Updated: 2026-04-12  Geng Xun added Spice binding for cube-backed SPICE access.
// Updated: 2026-04-12  Geng Xun kept Spice enum values scoped to avoid clashing with the Spice class binding.
// Updated: 2026-04-13  Geng Xun extended SpiceRotation with core matrix/cache/polynomial methods cluster.
// Purpose: Expose Isis::SpicePosition, Isis::SpiceRotation, and Isis::SpacecraftPosition
//          to Python for SPICE-based spacecraft navigation access.

#include <array>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Cube.h"
#include "Distance.h"
#include "IException.h"
#include "LightTimeCorrectionState.h"
#include "Longitude.h"
#include "Pvl.h"
#include "PvlObject.h"
#include "Spice.h"
#include "SpicePosition.h"
#include "SpiceRotation.h"
#include "SpacecraftPosition.h"
#include "Target.h"
#include "iTime.h"
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
             Isis::SpicePosition::PolyFunctionOverHermiteConstant);

  py::enum_<Isis::SpicePosition::PartialType>(m, "SpicePositionPartialType")
      .value("WRT_X", Isis::SpicePosition::WRT_X)
      .value("WRT_Y", Isis::SpicePosition::WRT_Y)
      .value("WRT_Z", Isis::SpicePosition::WRT_Z)
      .export_values();

  py::enum_<Isis::SpicePosition::OverrideType>(m, "SpicePositionOverrideType")
      .value("NoOverrides", Isis::SpicePosition::NoOverrides)
      .value("ScaleOnly", Isis::SpicePosition::ScaleOnly)
      .value("BaseAndScale", Isis::SpicePosition::BaseAndScale)
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
      // Coordinate and velocity access
      .def("set_ephemeris_time",
           [](Isis::SpicePosition &self, double et) -> std::vector<double> {
               return self.SetEphemerisTime(et);
           },
           py::arg("et"),
           "Set ephemeris time and return the J2000 position vector.")
      .def("coordinate",
           [](Isis::SpicePosition &self) -> std::vector<double> {
               return self.Coordinate();
           },
           "Return the current J2000 position vector [x, y, z] in km.")
      .def("velocity",
           [](Isis::SpicePosition &self) -> std::vector<double> {
               return self.Velocity();
           },
           "Return the current J2000 velocity vector [vx, vy, vz] in km/s.")
      .def("get_center_coordinate",
           [](Isis::SpicePosition &self) -> std::vector<double> {
               return self.GetCenterCoordinate();
           },
           "Return the J2000 center coordinate.")
      // Cache loading methods
      .def("load_cache",
           py::overload_cast<double, double, int>(&Isis::SpicePosition::LoadCache),
           py::arg("start_time"), py::arg("end_time"), py::arg("size"),
           "Load position cache for time range [start_time, end_time] with size entries.")
      .def("load_cache",
           py::overload_cast<double>(&Isis::SpicePosition::LoadCache),
           py::arg("time"),
           "Load position cache for a single time.")
      .def("load_cache",
           py::overload_cast<Isis::Table&>(&Isis::SpicePosition::LoadCache),
           py::arg("table"),
           "Load position cache from an ISIS Table.")
      .def("load_cache",
           py::overload_cast<nlohmann::json&>(&Isis::SpicePosition::LoadCache),
           py::arg("isd"),
           "Load position cache from a JSON ISD (Image Support Data).")
      .def("line_cache",
           [](Isis::SpicePosition &self, const std::string &table_name) -> Isis::Table {
               return self.LineCache(stdStringToQString(table_name));
           },
           py::arg("table_name"),
           "Return a Table with linear position cache.")
      .def("load_hermite_cache",
           [](Isis::SpicePosition &self, const std::string &table_name) -> Isis::Table {
               return self.LoadHermiteCache(stdStringToQString(table_name));
           },
           py::arg("table_name"),
           "Load and return a Hermite spline cache as a Table.")
      .def("reload_cache",
           py::overload_cast<>(&Isis::SpicePosition::ReloadCache),
           "Reload position cache from current state.")
      .def("reload_cache",
           py::overload_cast<Isis::Table&>(&Isis::SpicePosition::ReloadCache),
           py::arg("table"),
           "Reload position cache from an ISIS Table.")
      .def("cache",
           [](Isis::SpicePosition &self, const std::string &table_name) -> Isis::Table {
               return self.Cache(stdStringToQString(table_name));
           },
           py::arg("table_name"),
           "Return the current position cache as a Table.")
      // Polynomial methods
      .def("set_polynomial",
           py::overload_cast<const Isis::SpicePosition::Source>(&Isis::SpicePosition::SetPolynomial),
           py::arg("type") = Isis::SpicePosition::PolyFunction,
           "Fit polynomial to cached positions using specified source type.")
      .def("set_polynomial",
           [](Isis::SpicePosition &self,
              const std::vector<double> &xc,
              const std::vector<double> &yc,
              const std::vector<double> &zc,
              Isis::SpicePosition::Source type) {
               self.SetPolynomial(xc, yc, zc, type);
           },
           py::arg("xc"), py::arg("yc"), py::arg("zc"),
           py::arg("type") = Isis::SpicePosition::PolyFunction,
           "Set polynomial coefficients for X, Y, Z coordinates.")
      .def("get_polynomial",
           [](Isis::SpicePosition &self) -> py::tuple {
               std::vector<double> xc, yc, zc;
               self.GetPolynomial(xc, yc, zc);
               return py::make_tuple(xc, yc, zc);
           },
           "Return polynomial coefficients as (xc, yc, zc) tuple.")
      .def("set_polynomial_degree",
           &Isis::SpicePosition::SetPolynomialDegree,
           py::arg("degree"),
           "Set the degree of the polynomial fit.")
      .def("get_source",
           [](Isis::SpicePosition &self) { return self.GetSource(); },
           "Return the current source type (Spice, Memcache, HermiteCache, etc.).")
      // Base time and scaling methods
      .def("compute_base_time",
           &Isis::SpicePosition::ComputeBaseTime,
           "Compute the base time from cached positions.")
      .def("set_override_base_time",
           &Isis::SpicePosition::SetOverrideBaseTime,
           py::arg("base_time"), py::arg("time_scale"),
           "Override the base time and time scale for polynomial fits.")
      // Advanced polynomial and partial derivative methods
      .def("d_polynomial",
           &Isis::SpicePosition::DPolynomial,
           py::arg("coeff_index"),
           "Return the derivative of the polynomial at coefficient index.")
      .def("coordinate_partial",
           &Isis::SpicePosition::CoordinatePartial,
           py::arg("partial_var"), py::arg("coeff_index"),
           "Return coordinate partial derivative with respect to given variable.")
      .def("velocity_partial",
           &Isis::SpicePosition::VelocityPartial,
           py::arg("partial_var"), py::arg("coeff_index"),
           "Return velocity partial derivative with respect to given variable.")
      // Hermite and extrapolation methods
      .def("memcache2_hermite_cache",
           &Isis::SpicePosition::Memcache2HermiteCache,
           py::arg("tolerance"),
           "Convert memory cache to Hermite cache with given tolerance.")
      .def("extrapolate",
           &Isis::SpicePosition::Extrapolate,
           py::arg("time_et"),
           "Extrapolate position to given ephemeris time.")
      .def("hermite_coordinate",
           &Isis::SpicePosition::HermiteCoordinate,
           "Return Hermite interpolated coordinate.")
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
      .value("PckPolyFunction",           Isis::SpiceRotation::PckPolyFunction);

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
      // Time and ephemeris methods
      .def("set_ephemeris_time",
           &Isis::SpiceRotation::SetEphemerisTime,
           py::arg("et"),
           "Set the ephemeris time and compute rotation matrices.")
      // Matrix and rotation access methods
      .def("matrix",
           [](Isis::SpiceRotation &self) -> std::vector<double> {
               return self.Matrix();
           },
           "Return the 3x3 rotation matrix from J2000 to reference frame.")
      .def("angular_velocity",
           [](Isis::SpiceRotation &self) -> std::vector<double> {
               return self.AngularVelocity();
           },
           "Return the angular velocity vector [wx, wy, wz].")
      .def("constant_rotation",
           [](Isis::SpiceRotation &self) -> std::vector<double> {
               return self.ConstantRotation();
           },
           "Return the constant part of the rotation.")
      .def("constant_matrix",
           [](Isis::SpiceRotation &self) -> std::vector<double> & {
               return self.ConstantMatrix();
           },
           py::return_value_policy::reference_internal,
           "Return reference to constant rotation matrix.")
      .def("set_constant_matrix",
           &Isis::SpiceRotation::SetConstantMatrix,
           py::arg("constant_matrix"),
           "Set the constant rotation matrix.")
      .def("time_based_rotation",
           [](Isis::SpiceRotation &self) -> std::vector<double> {
               return self.TimeBasedRotation();
           },
           "Return the time-based part of the rotation.")
      .def("time_based_matrix",
           [](Isis::SpiceRotation &self) -> std::vector<double> & {
               return self.TimeBasedMatrix();
           },
           py::return_value_policy::reference_internal,
           "Return reference to time-based rotation matrix.")
      .def("set_time_based_matrix",
           &Isis::SpiceRotation::SetTimeBasedMatrix,
           py::arg("time_based_matrix"),
           "Set the time-based rotation matrix.")
      // Vector rotation methods
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
      // Cache loading methods
      .def("load_cache",
           py::overload_cast<double, double, int>(&Isis::SpiceRotation::LoadCache),
           py::arg("start_time"), py::arg("end_time"), py::arg("size"),
           "Load rotation cache for time range [start_time, end_time] with size entries.")
      .def("load_cache",
           py::overload_cast<double>(&Isis::SpiceRotation::LoadCache),
           py::arg("time"),
           "Load rotation cache for a single time.")
      .def("load_cache",
           py::overload_cast<Isis::Table&>(&Isis::SpiceRotation::LoadCache),
           py::arg("table"),
           "Load rotation cache from an ISIS Table.")
      .def("load_cache",
           py::overload_cast<nlohmann::json&>(&Isis::SpiceRotation::LoadCache),
           py::arg("isd"),
           "Load rotation cache from a JSON ISD (Image Support Data).")
      .def("reload_cache",
           &Isis::SpiceRotation::ReloadCache,
           "Reload rotation cache from current state.")
      .def("cache",
           [](Isis::SpiceRotation &self, const std::string &table_name) -> Isis::Table {
               return self.Cache(stdStringToQString(table_name));
           },
           py::arg("table_name"),
           "Return the current rotation cache as a Table.")
      .def("line_cache",
           [](Isis::SpiceRotation &self, const std::string &table_name) -> Isis::Table {
               return self.LineCache(stdStringToQString(table_name));
           },
           py::arg("table_name"),
           "Return a Table with linear rotation cache.")
      // Frame type and chain methods
      .def("get_frame_type",
           &Isis::SpiceRotation::getFrameType,
           "Return the frame type (INERTL, PCK, CK, etc.).")
      .def("constant_frame_chain",
           [](Isis::SpiceRotation &self) -> std::vector<int> {
               return self.ConstantFrameChain();
           },
           "Return the constant frame chain.")
      .def("time_frame_chain",
           [](Isis::SpiceRotation &self) -> std::vector<int> {
               return self.TimeFrameChain();
           },
           "Return the time-based frame chain.")
      // Source and polynomial methods
      .def("set_source",
           &Isis::SpiceRotation::SetSource,
           py::arg("source"),
           "Set the rotation source type.")
      .def("set_polynomial",
           py::overload_cast<const Isis::SpiceRotation::Source>(&Isis::SpiceRotation::SetPolynomial),
           py::arg("type") = Isis::SpiceRotation::PolyFunction,
           "Fit polynomial to cached rotations using specified source type.")
      .def("set_polynomial_degree",
           &Isis::SpiceRotation::SetPolynomialDegree,
           py::arg("degree"),
           "Set the degree of the polynomial fit.")
      .def("compute_base_time",
           &Isis::SpiceRotation::ComputeBaseTime,
           "Compute the base time from cached rotations.")
      .def("set_override_base_time",
           &Isis::SpiceRotation::SetOverrideBaseTime,
           py::arg("base_time"), py::arg("time_scale"),
           "Override the base time and time scale for polynomial fits.")
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

  // -----------------------------------------------------------------------
  // Spice (high-level SPICE accessor using cube labels/tables)
  // -----------------------------------------------------------------------
  py::class_<Isis::Spice>(m, "Spice")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct Spice from a cube's labels and embedded SPICE tables.")
      .def("set_time",
           &Isis::Spice::setTime,
           py::arg("time"),
           "Set the ephemeris time used for subsequent SPICE queries.")
      .def("instrument_position_vector",
           [](Isis::Spice &self) {
             std::array<double, 3> position{};
             self.instrumentPosition(position.data());
             return position;
           },
           "Return the instrument position (body-fixed, km) at the current time.")
      .def("instrument_body_fixed_position",
           [](Isis::Spice &self) {
             std::array<double, 3> position{};
             self.instrumentBodyFixedPosition(position.data());
             return position;
           },
           "Return the instrument body-fixed position (km) at the current time.")
      .def("instrument_body_fixed_velocity",
           [](Isis::Spice &self) {
             std::array<double, 3> velocity{};
             self.instrumentBodyFixedVelocity(velocity.data());
             return velocity;
           },
           "Return the instrument body-fixed velocity (km/s) at the current time.")
      .def("sun_position_vector",
           [](Isis::Spice &self) {
             std::array<double, 3> position{};
             self.sunPosition(position.data());
             return position;
           },
           "Return the sun position in the body-fixed frame (km) at the current time.")
      .def("target_center_distance",
           &Isis::Spice::targetCenterDistance,
           "Distance from spacecraft to target center (km).")
      .def("sun_to_body_distance",
           &Isis::Spice::sunToBodyDist,
           "Distance from the sun to the target body (km).")
      .def("solar_longitude",
           &Isis::Spice::solarLongitude,
           "Solar longitude for the current time.")
      .def("time",
           &Isis::Spice::time,
           "Return the currently set ephemeris time.")
      .def("radii",
           [](Isis::Spice &self) {
             std::array<Isis::Distance, 3> radii{};
             self.radii(radii.data());
             return radii;
           },
           "Return the target body radii as Distance objects.")
      .def("create_cache",
           &Isis::Spice::createCache,
           py::arg("start_time"),
           py::arg("end_time"),
           py::arg("size"),
           py::arg("tolerance"),
           "Cache spacecraft/sun states between start and end times.")
      .def("cache_start_time",
           &Isis::Spice::cacheStartTime,
           "Return the cache start time (if available).")
      .def("cache_end_time",
           &Isis::Spice::cacheEndTime,
           "Return the cache end time (if available).")
      .def("sub_spacecraft_point",
           [](Isis::Spice &self) {
             double lat = 0.0;
             double lon = 0.0;
             self.subSpacecraftPoint(lat, lon);
             return py::make_tuple(lat, lon);
           },
           "Return the sub-spacecraft point latitude/longitude (degrees).")
      .def("sub_solar_point",
           [](Isis::Spice &self) {
             double lat = 0.0;
             double lon = 0.0;
             self.subSolarPoint(lat, lon);
             return py::make_tuple(lat, lon);
           },
           "Return the sub-solar point latitude/longitude (degrees).")
      .def("target",
           &Isis::Spice::target,
           py::return_value_policy::reference_internal,
           "Return the Target associated with this Spice object.")
      .def("target_name",
           [](Isis::Spice &self) { return qStringToStdString(self.targetName()); },
           "Return the target name.")
      .def("get_clock_time",
           [](Isis::Spice &self, const std::string &clock_value, int sclk_code, bool clock_ticks) {
             return self.getClockTime(stdStringToQString(clock_value), sclk_code, clock_ticks);
           },
           py::arg("clock_value"),
           py::arg("sclk_code") = -1,
           py::arg("clock_ticks") = false,
           "Convert spacecraft clock to ephemeris time.")
      .def("get_double",
           [](Isis::Spice &self, const std::string &key, int index) {
             return self.getDouble(stdStringToQString(key), index);
           },
           py::arg("key"),
           py::arg("index") = 0,
           "Look up a double NAIF keyword value.")
      .def("get_integer",
           [](Isis::Spice &self, const std::string &key, int index) {
             return self.getInteger(stdStringToQString(key), index);
           },
           py::arg("key"),
           py::arg("index") = 0,
           "Look up an integer NAIF keyword value.")
      .def("get_string",
           [](Isis::Spice &self, const std::string &key, int index) {
             return qStringToStdString(self.getString(stdStringToQString(key), index));
           },
           py::arg("key"),
           py::arg("index") = 0,
           "Look up a string NAIF keyword value.")
      .def("sun_position",
           py::overload_cast<>(&Isis::Spice::sunPosition, py::const_),
           py::return_value_policy::reference_internal,
           "Return the cached SpicePosition for the sun.")
      .def("instrument_position",
           py::overload_cast<>(&Isis::Spice::instrumentPosition, py::const_),
           py::return_value_policy::reference_internal,
           "Return the cached instrument SpicePosition.")
      .def("body_rotation",
           &Isis::Spice::bodyRotation,
           py::return_value_policy::reference_internal,
           "Return the body rotation SpiceRotation.")
      .def("instrument_rotation",
           &Isis::Spice::instrumentRotation,
           py::return_value_policy::reference_internal,
           "Return the instrument rotation SpiceRotation.")
      .def("is_using_ale",
           &Isis::Spice::isUsingAle,
           "Return True if ALE metadata was used.")
      .def("has_kernels",
           &Isis::Spice::hasKernels,
           py::arg("label"),
           "Return True if the provided label contains SPICE kernels.")
      .def("is_time_set",
           &Isis::Spice::isTimeSet,
           "Return True if set_time has been called.")
      .def("naif_body_code",
           &Isis::Spice::naifBodyCode,
           "Return the NAIF body code.")
      .def("naif_spk_code",
           &Isis::Spice::naifSpkCode,
           "Return the NAIF SPK code.")
      .def("naif_ck_code",
           &Isis::Spice::naifCkCode,
           "Return the NAIF CK code.")
      .def("naif_ik_code",
           &Isis::Spice::naifIkCode,
           "Return the NAIF IK code.")
      .def("naif_sclk_code",
           &Isis::Spice::naifSclkCode,
           "Return the NAIF SCLK code.")
      .def("naif_body_frame_code",
           &Isis::Spice::naifBodyFrameCode,
           "Return the NAIF body frame code.")
      .def("get_stored_naif_keywords",
           &Isis::Spice::getStoredNaifKeywords,
           "Return the stored NaifKeywords PVL object.")
      .def("resolution",
           &Isis::Spice::resolution,
           "Return the instrument resolution (meters per pixel).");
}
