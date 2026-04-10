// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-22  Geng Xun expanded Sensor bindings with intersection, angle, slant-distance, solar, and spacecraft metadata accessors
// Updated: 2026-04-10  Geng Xun added SensorUtilities::Matrix binding (simple 3x3 row-Vec struct).
// Purpose: pybind11 bindings for the ISIS Sensor base class and core observation geometry accessors

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "MathUtils.h"
#include "SensorUtilities.h"
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

  // Added: 2026-04-09 - SensorUtilities lightweight value type bindings
  py::class_<SensorUtilities::Vec>(m, "Vec")
      .def(py::init<>(), "Construct a zero Vec.")
      .def(py::init<double, double, double>(),
           py::arg("x"), py::arg("y"), py::arg("z"),
           "Construct a Vec with the given x, y, z components.")
      .def(py::init([](const std::vector<double> &v) {
             if (v.size() != 3)
               throw std::invalid_argument("Vec requires exactly 3 elements.");
             double arr[3] = {v[0], v[1], v[2]};
             return SensorUtilities::Vec(arr);
           }),
           py::arg("data"),
           "Construct a Vec from a list of 3 doubles.")
      .def_readwrite("x", &SensorUtilities::Vec::x)
      .def_readwrite("y", &SensorUtilities::Vec::y)
      .def_readwrite("z", &SensorUtilities::Vec::z)
      .def("to_list",
           [](const SensorUtilities::Vec &self) {
             return std::vector<double>{self.x, self.y, self.z};
           },
           "Return the Vec as a Python list [x, y, z].")
      .def("__repr__",
           [](const SensorUtilities::Vec &self) {
             return "Vec(x=" + std::to_string(self.x) + ", y=" +
                    std::to_string(self.y) + ", z=" + std::to_string(self.z) + ")";
           });

  py::class_<SensorUtilities::GroundPt2D>(m, "GroundPt2D")
      .def(py::init([](double lat, double lon) {
             SensorUtilities::GroundPt2D g;
             g.lat = lat;
             g.lon = lon;
             return g;
           }),
           py::arg("lat") = 0.0, py::arg("lon") = 0.0,
           "Construct a GroundPt2D with latitude and longitude in radians.")
      .def_readwrite("lat", &SensorUtilities::GroundPt2D::lat)
      .def_readwrite("lon", &SensorUtilities::GroundPt2D::lon)
      .def("__repr__",
           [](const SensorUtilities::GroundPt2D &self) {
             return "GroundPt2D(lat=" + std::to_string(self.lat) +
                    ", lon=" + std::to_string(self.lon) + ")";
           });

  py::class_<SensorUtilities::GroundPt3D>(m, "GroundPt3D")
      .def(py::init([](double lat, double lon, double radius) {
             SensorUtilities::GroundPt3D g;
             g.lat = lat;
             g.lon = lon;
             g.radius = radius;
             return g;
           }),
           py::arg("lat") = 0.0, py::arg("lon") = 0.0, py::arg("radius") = 0.0,
           "Construct a GroundPt3D with latitude, longitude (radians), and radius (km).")
      .def_readwrite("lat",    &SensorUtilities::GroundPt3D::lat)
      .def_readwrite("lon",    &SensorUtilities::GroundPt3D::lon)
      .def_readwrite("radius", &SensorUtilities::GroundPt3D::radius)
      .def("__repr__",
           [](const SensorUtilities::GroundPt3D &self) {
             return "GroundPt3D(lat=" + std::to_string(self.lat) +
                    ", lon=" + std::to_string(self.lon) +
                    ", radius=" + std::to_string(self.radius) + ")";
           });

  py::class_<SensorUtilities::ImagePt>(m, "ImagePt")
      .def(py::init([](double line, double sample, int band) {
             SensorUtilities::ImagePt p;
             p.line   = line;
             p.sample = sample;
             p.band   = band;
             return p;
           }),
           py::arg("line") = 0.0, py::arg("sample") = 0.0, py::arg("band") = 1,
           "Construct an ImagePt with the given line, sample, and band.")
      .def_readwrite("line",   &SensorUtilities::ImagePt::line)
      .def_readwrite("sample", &SensorUtilities::ImagePt::sample)
      .def_readwrite("band",   &SensorUtilities::ImagePt::band)
      .def("__repr__",
           [](const SensorUtilities::ImagePt &self) {
             return "ImagePt(line=" + std::to_string(self.line) +
                    ", sample=" + std::to_string(self.sample) +
                    ", band=" + std::to_string(self.band) + ")";
           });

  py::class_<SensorUtilities::RaDec>(m, "RaDec")
      .def(py::init([](double ra, double dec) {
             SensorUtilities::RaDec r;
             r.ra  = ra;
             r.dec = dec;
             return r;
           }),
           py::arg("ra") = 0.0, py::arg("dec") = 0.0,
           "Construct a RaDec with right ascension and declination in radians.")
      .def_readwrite("ra",  &SensorUtilities::RaDec::ra)
      .def_readwrite("dec", &SensorUtilities::RaDec::dec)
      .def("__repr__",
           [](const SensorUtilities::RaDec &self) {
             return "RaDec(ra=" + std::to_string(self.ra) +
                    ", dec=" + std::to_string(self.dec) + ")";
           });

  py::class_<SensorUtilities::ObserverState>(m, "ObserverState")
      .def(py::init<>(), "Construct a default ObserverState.")
      .def_readwrite("look_vec",       &SensorUtilities::ObserverState::lookVec)
      .def_readwrite("j2000_look_vec", &SensorUtilities::ObserverState::j2000LookVec)
      .def_readwrite("sensor_pos",     &SensorUtilities::ObserverState::sensorPos)
      .def_readwrite("time",           &SensorUtilities::ObserverState::time)
      .def_readwrite("image_point",    &SensorUtilities::ObserverState::imagePoint)
      .def("__repr__",
           [](const SensorUtilities::ObserverState &self) {
             return "ObserverState(time=" + std::to_string(self.time) + ")";
           });

  py::class_<SensorUtilities::Intersection>(m, "Intersection")
      .def(py::init<>(), "Construct a default Intersection.")
      .def_readwrite("ground_pt", &SensorUtilities::Intersection::groundPt)
      .def_readwrite("normal",    &SensorUtilities::Intersection::normal)
      .def("__repr__",
           [](const SensorUtilities::Intersection &) {
             return "Intersection()";
           });

  // Added: 2026-04-10 - SensorUtilities::Matrix (3x3 matrix as three Vec rows)
  py::class_<SensorUtilities::Matrix>(m, "SensorMatrix")
      .def(py::init([]() {
             SensorUtilities::Matrix m;
             m.a = {0.0, 0.0, 0.0};
             m.b = {0.0, 0.0, 0.0};
             m.c = {0.0, 0.0, 0.0};
             return m;
           }),
           "Construct a zero-initialized 3x3 matrix.")
      .def(py::init([](SensorUtilities::Vec a,
                       SensorUtilities::Vec b,
                       SensorUtilities::Vec c) {
             SensorUtilities::Matrix mat;
             mat.a = a;
             mat.b = b;
             mat.c = c;
             return mat;
           }),
           py::arg("a"), py::arg("b"), py::arg("c"),
           "Construct a matrix from three row Vec objects.")
      .def_readwrite("a", &SensorUtilities::Matrix::a)
      .def_readwrite("b", &SensorUtilities::Matrix::b)
      .def_readwrite("c", &SensorUtilities::Matrix::c)
      .def("mat_vec_product",
           [](const SensorUtilities::Matrix &self,
              const SensorUtilities::Vec &vec) {
               return SensorUtilities::matrixVecProduct(self, vec);
           },
           py::arg("vec"),
           "Multiply this 3x3 matrix by a Vec, returning a Vec.")
      .def("__repr__",
           [](const SensorUtilities::Matrix &self) {
               return std::string("SensorMatrix(a=Vec(") +
                      std::to_string(self.a.x) + "," +
                      std::to_string(self.a.y) + "," +
                      std::to_string(self.a.z) + "))";
           });
}

