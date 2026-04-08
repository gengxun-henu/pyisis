// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-04-08  Geng Xun added Stereo tuple-returning wrappers plus Angle arithmetic/comparison helpers
// Purpose: pybind11 bindings for ISIS geometry primitives and resampling helpers including Angle, Stereo, Distance, Latitude, Longitude, Transform, Interpolator, Enlarge, and Reduce

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <string>

#include "Angle.h"
#include "Enlarge.h"
#include "Displacement.h"
#include "Distance.h"
#include "IException.h"
#include "Interpolator.h"
#include "Latitude.h"
#include "Longitude.h"
#include "PvlGroup.h"
#include "Reduce.h"
#include "Stereo.h"
#include "Transform.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
std::vector<double> toDoubleVector(const py::sequence &values) {
  std::vector<double> result;
  result.reserve(py::len(values));
  for (const py::handle &value : values) {
    result.push_back(py::cast<double>(value));
  }
  return result;
}

void validateStereoCameraState(Isis::Camera &camera, const std::string &camera_name) {
  if (!camera.HasSurfaceIntersection()) {
    QString message = QString::fromStdString(camera_name)
                      + " does not have a valid surface intersection. "
                        "Call Camera.set_image(...) on both cameras before "
                        "calling Stereo.elevation().";
    throw Isis::IException(Isis::IException::Programmer, message, _FILEINFO_);
  }
}
}

void bind_base_geometry(py::module_ &m) {
  py::class_<Isis::Angle> angle(m, "Angle");

  py::enum_<Isis::Angle::Units>(angle, "Units")
      .value("Degrees", Isis::Angle::Degrees)
      .value("Radians", Isis::Angle::Radians);

  angle
      .def(py::init<>())
      .def(py::init<double, Isis::Angle::Units>(), py::arg("angle"), py::arg("unit"))
      .def(py::init<const Isis::Angle &>(), py::arg("other"))
      .def(py::init([](const std::string &angle_text) { return Isis::Angle(stdStringToQString(angle_text)); }),
           py::arg("angle_text"))
       .def("__copy__", [](const Isis::Angle &self) { return Isis::Angle(self); })
       .def("__deepcopy__", [](const Isis::Angle &self, py::dict) { return Isis::Angle(self); }, py::arg("memo"))
      .def_static("full_rotation", &Isis::Angle::fullRotation)
      .def("is_valid", &Isis::Angle::isValid)
      .def("angle", &Isis::Angle::angle, py::arg("unit"))
      .def("radians", &Isis::Angle::radians)
      .def("degrees", &Isis::Angle::degrees)
      .def("unit_wrap_value", &Isis::Angle::unitWrapValue, py::arg("unit"))
      .def("set_angle", &Isis::Angle::setAngle, py::arg("angle"), py::arg("unit"))
      .def("set_radians", &Isis::Angle::setRadians, py::arg("radians"))
      .def("set_degrees", &Isis::Angle::setDegrees, py::arg("degrees"))
      .def("ratio",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self / other;
           },
           py::arg("other"))
      .def("__add__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self + other;
           },
           py::is_operator())
      .def("__sub__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self - other;
           },
           py::is_operator())
      .def("__mul__",
           [](const Isis::Angle &self, double value) {
             return self * value;
           },
           py::arg("value"),
           py::is_operator())
      .def("__rmul__",
           [](const Isis::Angle &self, double value) {
             return value * self;
           },
           py::arg("value"),
           py::is_operator())
      .def("__truediv__",
           [](const Isis::Angle &self, double value) {
             return self / value;
           },
           py::arg("value"),
           py::is_operator())
      .def("__iadd__",
           [](Isis::Angle &self, const Isis::Angle &other) -> Isis::Angle & {
             self += other;
             return self;
           },
           py::arg("other"),
           py::return_value_policy::reference_internal,
           py::is_operator())
      .def("__isub__",
           [](Isis::Angle &self, const Isis::Angle &other) -> Isis::Angle & {
             self -= other;
             return self;
           },
           py::arg("other"),
           py::return_value_policy::reference_internal,
           py::is_operator())
      .def("__imul__",
           [](Isis::Angle &self, double value) -> Isis::Angle & {
             self *= value;
             return self;
           },
           py::arg("value"),
           py::return_value_policy::reference_internal,
           py::is_operator())
      .def("__itruediv__",
           [](Isis::Angle &self, double value) -> Isis::Angle & {
             self /= value;
             return self;
           },
           py::arg("value"),
           py::return_value_policy::reference_internal,
           py::is_operator())
      .def("__eq__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self == other;
           },
           py::is_operator())
      .def("__ne__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self != other;
           },
           py::is_operator())
      .def("__lt__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self < other;
           },
           py::is_operator())
      .def("__le__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self <= other;
           },
           py::is_operator())
      .def("__gt__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self > other;
           },
           py::is_operator())
      .def("__ge__",
           [](const Isis::Angle &self, const Isis::Angle &other) {
             return self >= other;
           },
           py::is_operator())
      .def("to_string",
           [](const Isis::Angle &self, bool include_units) {
             return qStringToStdString(self.toString(include_units));
           },
           py::arg("include_units") = true)
      .def("__str__",
           [](const Isis::Angle &self) {
             return qStringToStdString(self.toString(true));
           })
      .def("__repr__", [](const Isis::Angle &self) {
        return "Angle(" + std::to_string(self.degrees()) + " deg)";
      });

  py::class_<Isis::Stereo> stereo(m, "Stereo");

  stereo
      .def(py::init<>())

      /**
       * @brief Calculate elevation and related parameters from two cameras
       * Returns a tuple of (success, radius, latitude, longitude, sepang, error)
        * where success is a boolean indicating if the calculation was successful,
        * radius is the calculated radius at the point,
        * latitude and longitude are the calculated coordinates,
        * sepang is the separation angle between the two cameras at the point,
        * and error is an estimate of the error in the elevation calculation.
        * Note that the radius, latitude, longitude, sepang, and error values are only meaningful if success is True.
        * This method is useful for performing stereo elevation calculations given two camera models, and the returned parameters can be used to understand the geometry of the observed point in 3D space.
        * Camera::SetImage() must have been called on both cameras with the same ground point for this method to work correctly, as it relies on the cameras being pointed at the same location on the surface.
        * The method will return false if either camera does not have a valid surface intersection, which can occur if the cameras are not properly set up or if they are not pointed at the same location
        * on the surface.
       */
      .def_static(
          "elevation",
          [](Isis::Camera &cam1, Isis::Camera &cam2) {
            validateStereoCameraState(cam1, "cam1");
            validateStereoCameraState(cam2, "cam2");

            double radius = 0.0;
            double latitude = 0.0;
            double longitude = 0.0;
            double sepang = 0.0;
            double error = 0.0;

            try {
              bool success = Isis::Stereo::elevation(cam1, cam2, radius, latitude, longitude, sepang, error);
              return py::make_tuple(success, radius, latitude, longitude, sepang, error);
            }
            catch (const Isis::IException &) {
              throw;
            }
            catch (const std::exception &e) {
              QString message = "Stereo.elevation() failed after camera state validation: ";
              message += e.what();
              throw Isis::IException(Isis::IException::Programmer, message, _FILEINFO_);
            }
          },
          py::arg("cam1"),
          py::arg("cam2"))
      .def_static(
          "spherical",
          [](double latitude, double longitude, double radius) {
            double x = 0.0;
            double y = 0.0;
            double z = 0.0;

            Isis::Stereo::spherical(latitude, longitude, radius, x, y, z);
            return py::make_tuple(x, y, z);
          },
          py::arg("latitude"),
          py::arg("longitude"),
          py::arg("radius"))
      .def_static(
          "rectangular",
          [](double x, double y, double z) {
            double latitude = 0.0;
            double longitude = 0.0;
            double radius = 0.0;

            Isis::Stereo::rectangular(x, y, z, latitude, longitude, radius);
            return py::make_tuple(latitude, longitude, radius);
          },
          py::arg("x"),
          py::arg("y"),
          py::arg("z"))
      .def("__repr__", [](const Isis::Stereo &) { return "Stereo()"; });

  py::class_<Isis::Distance> distance(m, "Distance");

  py::enum_<Isis::Distance::Units>(distance, "Units")
      .value("Meters", Isis::Distance::Meters)
      .value("Kilometers", Isis::Distance::Kilometers)
      .value("Pixels", Isis::Distance::Pixels)
      .value("SolarRadii", Isis::Distance::SolarRadii);

  distance
      .def(py::init<>())
      .def(py::init<double, Isis::Distance::Units>(), py::arg("distance"), py::arg("unit"))
      .def(py::init<double, double>(), py::arg("distance_in_pixels"), py::arg("pixels_per_meter"))
      .def(py::init<const Isis::Distance &>(), py::arg("other"))
      .def("meters", &Isis::Distance::meters)
      .def("set_meters", &Isis::Distance::setMeters, py::arg("meters"))
      .def("kilometers", &Isis::Distance::kilometers)
      .def("set_kilometers", &Isis::Distance::setKilometers, py::arg("kilometers"))
      .def("pixels", &Isis::Distance::pixels, py::arg("pixels_per_meter") = 1.0)
      .def("set_pixels", &Isis::Distance::setPixels, py::arg("distance_in_pixels"), py::arg("pixels_per_meter") = 1.0)
      .def("solar_radii", &Isis::Distance::solarRadii)
      .def("set_solar_radii", &Isis::Distance::setSolarRadii, py::arg("solar_radii"))
      .def("to_string", [](const Isis::Distance &self) { return qStringToStdString(self.toString()); })
      .def("is_valid", &Isis::Distance::isValid)
      .def("__repr__", [](const Isis::Distance &self) {
        return "Distance(" + std::to_string(self.meters()) + " m)";
      });

  py::class_<Isis::Displacement> displacement(m, "Displacement");

  py::enum_<Isis::Displacement::Units>(displacement, "Units")
      .value("Meters", Isis::Displacement::Meters)
      .value("Kilometers", Isis::Displacement::Kilometers)
      .value("Pixels", Isis::Displacement::Pixels);

  displacement
      .def(py::init<>())
      .def(py::init<double, Isis::Displacement::Units>(), py::arg("displacement"), py::arg("unit"))
      .def(py::init<double, double>(), py::arg("distance_in_pixels"), py::arg("pixels_per_meter"))
      .def(py::init<const Isis::Distance &>(), py::arg("distance"))
      .def("meters", &Isis::Displacement::meters)
      .def("set_meters", &Isis::Displacement::setMeters, py::arg("meters"))
      .def("kilometers", &Isis::Displacement::kilometers)
      .def("set_kilometers", &Isis::Displacement::setKilometers, py::arg("kilometers"))
      .def("pixels", &Isis::Displacement::pixels, py::arg("pixels_per_meter") = 1.0)
      .def("set_pixels", &Isis::Displacement::setPixels, py::arg("distance_in_pixels"), py::arg("pixels_per_meter") = 1.0)
      .def("is_valid", &Isis::Displacement::isValid)
      .def("__repr__", [](const Isis::Displacement &self) {
        return "Displacement(" + std::to_string(self.meters()) + " m)";
      });

  py::class_<Isis::Latitude, Isis::Angle> latitude(m, "Latitude");

  py::enum_<Isis::Latitude::ErrorChecking>(latitude, "ErrorChecking")
      .value("ThrowAllErrors", Isis::Latitude::ThrowAllErrors)
      .value("AllowPastPole", Isis::Latitude::AllowPastPole);

  py::enum_<Isis::Latitude::CoordinateType>(latitude, "CoordinateType")
      .value("Planetocentric", Isis::Latitude::Planetocentric)
      .value("Planetographic", Isis::Latitude::Planetographic);

  latitude
      .def(py::init<>())
      .def(py::init<double, Isis::Angle::Units, Isis::Latitude::ErrorChecking>(),
           py::arg("latitude"),
           py::arg("latitude_units"),
           py::arg("errors") = Isis::Latitude::AllowPastPole)
      .def(py::init<Isis::Angle, Isis::Latitude::ErrorChecking>(),
           py::arg("latitude"),
           py::arg("errors") = Isis::Latitude::AllowPastPole)
      .def(py::init<double,
                    Isis::Distance,
                    Isis::Distance,
                    Isis::Latitude::CoordinateType,
                    Isis::Angle::Units,
                    Isis::Latitude::ErrorChecking>(),
           py::arg("latitude"),
           py::arg("equatorial_radius"),
           py::arg("polar_radius"),
           py::arg("coordinate_type") = Isis::Latitude::Planetocentric,
           py::arg("latitude_units") = Isis::Angle::Radians,
           py::arg("errors") = Isis::Latitude::ThrowAllErrors)
      .def(py::init<const Isis::Latitude &>(), py::arg("other"))
      .def("planetocentric", &Isis::Latitude::planetocentric, py::arg("units") = Isis::Angle::Radians)
      .def("set_planetocentric", &Isis::Latitude::setPlanetocentric, py::arg("latitude"), py::arg("units") = Isis::Angle::Radians)
      .def("planetographic", &Isis::Latitude::planetographic, py::arg("units") = Isis::Angle::Radians)
      .def("set_planetographic", &Isis::Latitude::setPlanetographic, py::arg("latitude"), py::arg("units") = Isis::Angle::Radians)
      .def("error_checking", &Isis::Latitude::errorChecking)
      .def("set_error_checking", &Isis::Latitude::setErrorChecking, py::arg("errors"))
      .def("in_range", &Isis::Latitude::inRange, py::arg("minimum"), py::arg("maximum"))
      .def("__repr__", [](const Isis::Latitude &self) {
        return "Latitude(" + std::to_string(self.planetocentric(Isis::Angle::Degrees)) + " deg)";
      });

  py::class_<Isis::Longitude, Isis::Angle> longitude(m, "Longitude");

  py::enum_<Isis::Longitude::Direction>(longitude, "Direction")
      .value("PositiveEast", Isis::Longitude::PositiveEast)
      .value("PositiveWest", Isis::Longitude::PositiveWest);

  py::enum_<Isis::Longitude::Domain>(longitude, "Domain")
      .value("Domain360", Isis::Longitude::Domain360)
      .value("Domain180", Isis::Longitude::Domain180);

  longitude
      .def(py::init<>())
      .def(py::init<double, Isis::Angle::Units, Isis::Longitude::Direction, Isis::Longitude::Domain>(),
           py::arg("longitude"),
           py::arg("longitude_units"),
           py::arg("direction") = Isis::Longitude::PositiveEast,
           py::arg("domain") = Isis::Longitude::Domain360)
      .def(py::init<Isis::Angle, Isis::Longitude::Direction, Isis::Longitude::Domain>(),
           py::arg("longitude"),
           py::arg("direction") = Isis::Longitude::PositiveEast,
           py::arg("domain") = Isis::Longitude::Domain360)
      .def(py::init<const Isis::Longitude &>(), py::arg("other"))
      .def("positive_east", &Isis::Longitude::positiveEast, py::arg("units") = Isis::Angle::Radians)
      .def("set_positive_east", &Isis::Longitude::setPositiveEast, py::arg("longitude"), py::arg("units") = Isis::Angle::Radians)
      .def("positive_west", &Isis::Longitude::positiveWest, py::arg("units") = Isis::Angle::Radians)
      .def("set_positive_west", &Isis::Longitude::setPositiveWest, py::arg("longitude"), py::arg("units") = Isis::Angle::Radians)
      .def("force_180_domain", &Isis::Longitude::force180Domain)
      .def("force_360_domain", &Isis::Longitude::force360Domain)
      .def("in_range", &Isis::Longitude::inRange, py::arg("minimum"), py::arg("maximum"))
      .def("__repr__", [](const Isis::Longitude &self) {
        return "Longitude(" + std::to_string(self.positiveEast(Isis::Angle::Degrees)) + " deg E)";
      });

  py::class_<Isis::Transform> transform(m, "Transform");

  transform
      .def(py::init<>())
      .def("output_samples", &Isis::Transform::OutputSamples)
      .def("output_lines", &Isis::Transform::OutputLines)
      .def("xform",
           [](Isis::Transform &self, double out_sample, double out_line) {
             double in_sample = 0.0;
             double in_line = 0.0;
             bool success = self.Xform(in_sample, in_line, out_sample, out_line);
             return py::make_tuple(success, in_sample, in_line);
           },
           py::arg("out_sample"),
           py::arg("out_line"))
      .def("__repr__", [](const Isis::Transform &self) {
        return "Transform(output_samples=" + std::to_string(self.OutputSamples()) +
               ", output_lines=" + std::to_string(self.OutputLines()) + ")";
      });

  py::class_<Isis::Interpolator> interpolator(m, "Interpolator");

  py::enum_<Isis::Interpolator::interpType>(interpolator, "InterpType")
      .value("None", Isis::Interpolator::None)
      .value("NearestNeighborType", Isis::Interpolator::NearestNeighborType)
      .value("BiLinearType", Isis::Interpolator::BiLinearType)
      .value("CubicConvolutionType", Isis::Interpolator::CubicConvolutionType);

  interpolator
      .def(py::init<>())
      .def(py::init<const Isis::Interpolator::interpType &>(), py::arg("interp_type"))
      .def("interpolate",
           [](Isis::Interpolator &self, double input_sample, double input_line, const py::sequence &buffer_values) {
             std::vector<double> values = toDoubleVector(buffer_values);
             int expected_size = self.Samples() * self.Lines();
             if (static_cast<int>(values.size()) != expected_size) {
               throw std::runtime_error(
                   "Interpolator buffer size mismatch: expected " + std::to_string(expected_size) +
                   ", got " + std::to_string(values.size()));
             }
             return self.Interpolate(input_sample, input_line, values.data());
           },
           py::arg("input_sample"),
           py::arg("input_line"),
           py::arg("buffer_values"))
      .def("set_type", &Isis::Interpolator::SetType, py::arg("interp_type"))
      .def("samples", &Isis::Interpolator::Samples)
      .def("lines", &Isis::Interpolator::Lines)
      .def("hot_sample", &Isis::Interpolator::HotSample)
      .def("hot_line", &Isis::Interpolator::HotLine)
      .def("__repr__", [](Isis::Interpolator &self) {
        return "Interpolator(samples=" + std::to_string(self.Samples()) +
               ", lines=" + std::to_string(self.Lines()) + ")";
      });

  py::class_<Isis::Enlarge, Isis::Transform> enlarge(m, "Enlarge");

  enlarge
      .def(py::init([](Isis::Cube &input_cube, double sample_scale, double line_scale) {
             return std::make_unique<Isis::Enlarge>(&input_cube, sample_scale, line_scale);
           }),
           py::arg("input_cube"),
           py::arg("sample_scale"),
           py::arg("line_scale"),
           py::keep_alive<1, 2>())
      .def("set_input_area",
           &Isis::Enlarge::SetInputArea,
           py::arg("start_sample"),
           py::arg("end_sample"),
           py::arg("start_line"),
           py::arg("end_line"))
      .def("update_output_label",
           [](Isis::Enlarge &self, Isis::Cube &output_cube) {
             return self.UpdateOutputLabel(&output_cube);
           },
           py::arg("output_cube"))
      .def("__repr__", [](const Isis::Enlarge &self) {
        return "Enlarge(output_samples=" + std::to_string(self.OutputSamples()) +
               ", output_lines=" + std::to_string(self.OutputLines()) + ")";
      });

  py::class_<Isis::Reduce> reduce(m, "Reduce");

  reduce
      .def(py::init([](Isis::Cube &input_cube, double sample_scale, double line_scale) {
             return std::make_unique<Isis::Reduce>(&input_cube, sample_scale, line_scale);
           }),
           py::arg("input_cube"),
           py::arg("sample_scale"),
           py::arg("line_scale"),
           py::keep_alive<1, 2>())
      .def("set_input_boundary",
           &Isis::Reduce::setInputBoundary,
           py::arg("start_sample"),
           py::arg("end_sample"),
           py::arg("start_line"),
           py::arg("end_line"))
      .def("update_output_label",
           [](Isis::Reduce &self, Isis::Cube &output_cube) {
             return self.UpdateOutputLabel(&output_cube);
           },
           py::arg("output_cube"))
      .def("__repr__", [](Isis::Reduce &) { return "Reduce()"; });
}