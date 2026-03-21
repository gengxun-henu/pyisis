// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Cube.h"
#include "FileName.h"
#include "IException.h"
#include "ObservationNumber.h"
#include "Progress.h"
#include "Pvl.h"
#include "SerialNumber.h"
#include "SerialNumberList.h"
#include "helpers.h"
#include "iTime.h"

namespace py = pybind11;

namespace {
std::vector<std::string> qStringStdVectorToStdVector(const std::vector<QString> &values) {
  std::vector<std::string> result;
  result.reserve(values.size());
  for (const QString &value : values) {
    result.push_back(qStringToStdString(value));
  }
  return result;
}
}  // namespace

void bind_base_support(py::module_ &m) {
  py::register_exception<Isis::IException>(m, "IException");

  /**
   * @brief Bindings for the Isis::FileName class
   * This function creates Python bindings for the Isis::FileName class using pybind11.
   * The FileName class provides functionality for handling file names and paths in ISIS, including parsing file names, extracting components, and managing versioned files. These bindings allow Python users to utilize the powerful file name handling capabilities of the Isis::FileName class in their Python code when working with ISIS image cubes and other files.
   * @see Isis::FileName
   * @param m The pybind11 module to which the bindings will be added.
   * @author Geng Xun
   * @date 2026-03-17
   */
  py::class_<Isis::FileName>(m, "FileName")
      .def(py::init<>())
      .def(py::init([](const std::string &file_name) {
             return Isis::FileName(stdStringToQString(file_name));
           }),
           py::arg("file_name"))
      .def(py::init<const Isis::FileName &>(), py::arg("other"))
      .def("original_path", [](const Isis::FileName &self) { return qStringToStdString(self.originalPath()); })
      .def("path", [](const Isis::FileName &self) { return qStringToStdString(self.path()); })
      .def("attributes", [](const Isis::FileName &self) { return qStringToStdString(self.attributes()); })
      .def("base_name", [](const Isis::FileName &self) { return qStringToStdString(self.baseName()); })
      .def("name", [](const Isis::FileName &self) { return qStringToStdString(self.name()); })
      .def("extension", [](const Isis::FileName &self) { return qStringToStdString(self.extension()); })
      .def("expanded", [](const Isis::FileName &self) { return qStringToStdString(self.expanded()); })
      .def("original", [](const Isis::FileName &self) { return qStringToStdString(self.original()); })
      .def("add_extension",
           [](const Isis::FileName &self, const std::string &extension) {
             return self.addExtension(stdStringToQString(extension));
           },
           py::arg("extension"))
      .def("remove_extension", &Isis::FileName::removeExtension)
      .def("set_extension",
           [](const Isis::FileName &self, const std::string &extension) {
             return self.setExtension(stdStringToQString(extension));
           },
           py::arg("extension"))
      .def("is_versioned", &Isis::FileName::isVersioned)
      .def("is_numerically_versioned", &Isis::FileName::isNumericallyVersioned)
      .def("is_date_versioned", &Isis::FileName::isDateVersioned)
      .def("highest_version", &Isis::FileName::highestVersion)
      .def("new_version", &Isis::FileName::newVersion)
      .def("file_exists", &Isis::FileName::fileExists)
      .def("to_string", [](const Isis::FileName &self) { return qStringToStdString(self.toString()); })
      .def_static("create_temp_file",
                  &Isis::FileName::createTempFile,
                  py::arg("template_file_name") = Isis::FileName("$TEMPORARY/temp"))
      .def("__str__", [](const Isis::FileName &self) { return qStringToStdString(self.toString()); })
      .def("__repr__", [](const Isis::FileName &self) {
        return "FileName('" + qStringToStdString(self.toString()) + "')";
      });

  py::class_<Isis::iTime>(m, "iTime")
      .def(py::init<>())
      .def(py::init([](const std::string &utc) { return Isis::iTime(stdStringToQString(utc)); }), py::arg("time"))
      .def(py::init<double>(), py::arg("ephemeris_time"))
      .def("year_string", [](const Isis::iTime &self) { return qStringToStdString(self.YearString()); })
      .def("year", &Isis::iTime::Year)
      .def("month_string", [](const Isis::iTime &self) { return qStringToStdString(self.MonthString()); })
      .def("month", &Isis::iTime::Month)
      .def("day_string", [](const Isis::iTime &self) { return qStringToStdString(self.DayString()); })
      .def("day", &Isis::iTime::Day)
      .def("hour_string", [](const Isis::iTime &self) { return qStringToStdString(self.HourString()); })
      .def("hour", &Isis::iTime::Hour)
      .def("minute_string", [](const Isis::iTime &self) { return qStringToStdString(self.MinuteString()); })
      .def("minute", &Isis::iTime::Minute)
      .def("second_string",
           [](const Isis::iTime &self, int precision) {
             return qStringToStdString(self.SecondString(precision));
           },
           py::arg("precision") = 8)
      .def("second", &Isis::iTime::Second)
      .def("day_of_year_string", [](const Isis::iTime &self) { return qStringToStdString(self.DayOfYearString()); })
      .def("day_of_year", &Isis::iTime::DayOfYear)
      .def("et_string", [](const Isis::iTime &self) { return qStringToStdString(self.EtString()); })
      .def("et", &Isis::iTime::Et)
      .def("utc",
           [](const Isis::iTime &self, int precision) { return qStringToStdString(self.UTC(precision)); },
           py::arg("precision") = 8)
      .def_static("current_gmt", []() { return qStringToStdString(Isis::iTime::CurrentGMT()); })
      .def_static("current_local_time", []() { return qStringToStdString(Isis::iTime::CurrentLocalTime()); })
      .def("set_et", &Isis::iTime::setEt, py::arg("et"))
      .def("set_utc",
           [](Isis::iTime &self, const std::string &utc) { self.setUtc(stdStringToQString(utc)); },
           py::arg("utc"))
      .def("__str__", [](const Isis::iTime &self) { return qStringToStdString(self.UTC()); })
      .def("__repr__", [](const Isis::iTime &self) {
        return "iTime('" + qStringToStdString(self.UTC()) + "')";
      });

  py::class_<Isis::SerialNumber>(m, "SerialNumber")
      .def(py::init<>())
      .def_static(
          "compose",
          [](Isis::Pvl &label, bool def2filename) {
            return qStringToStdString(Isis::SerialNumber::Compose(label, def2filename));
          },
          py::arg("label"), py::arg("def2filename") = false)
      .def_static(
          "compose",
          [](Isis::Cube &cube, bool def2filename) {
            return qStringToStdString(Isis::SerialNumber::Compose(cube, def2filename));
          },
          py::arg("cube"), py::arg("def2filename") = false)
      .def_static(
          "compose",
          [](const std::string &filename, bool def2filename) {
            return qStringToStdString(
                Isis::SerialNumber::Compose(stdStringToQString(filename), def2filename));
          },
          py::arg("filename"), py::arg("def2filename") = false)
      .def_static(
          "compose_observation",
          [](const std::string &serial_number, Isis::SerialNumberList &list, bool def2filename) {
            return qStringToStdString(Isis::SerialNumber::ComposeObservation(
                stdStringToQString(serial_number), list, def2filename));
          },
          py::arg("serial_number"), py::arg("list"), py::arg("def2filename") = false)
      .def("__repr__", [](const Isis::SerialNumber &) { return "SerialNumber()"; });

  py::class_<Isis::SerialNumberList>(m, "SerialNumberList")
      .def(py::init<bool>(), py::arg("check_target") = true)
      .def(
          py::init([](const std::string &list, bool check_target, Isis::Progress *progress) {
            return Isis::SerialNumberList(stdStringToQString(list), check_target, progress);
          }),
          py::arg("list"), py::arg("check_target") = true, py::arg("progress") = nullptr)
      .def(
          "add",
          [](Isis::SerialNumberList &self, const std::string &filename, bool def2filename) {
            self.add(stdStringToQString(filename), def2filename);
          },
          py::arg("filename"), py::arg("def2filename") = false)
      .def(
          "add",
          [](Isis::SerialNumberList &self, const std::string &serial_number,
             const std::string &filename) {
            self.add(stdStringToQString(serial_number), stdStringToQString(filename));
          },
          py::arg("serial_number"), py::arg("filename"))
      .def("has_serial_number",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             return self.hasSerialNumber(stdStringToQString(serial_number));
           },
           py::arg("serial_number"))
      .def("remove",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             self.remove(stdStringToQString(serial_number));
           },
           py::arg("serial_number"))
      .def("size", &Isis::SerialNumberList::size)
      .def("file_name",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             return qStringToStdString(self.fileName(stdStringToQString(serial_number)));
           },
           py::arg("serial_number"))
      .def("file_name",
           [](Isis::SerialNumberList &self, int index) {
             return qStringToStdString(self.fileName(index));
           },
           py::arg("index"))
      .def("serial_number",
           [](Isis::SerialNumberList &self, const std::string &filename) {
             return qStringToStdString(self.serialNumber(stdStringToQString(filename)));
           },
           py::arg("filename"))
      .def("serial_number",
           [](Isis::SerialNumberList &self, int index) {
             return qStringToStdString(self.serialNumber(index));
           },
           py::arg("index"))
      .def("observation_number",
           [](Isis::SerialNumberList &self, int index) {
             return qStringToStdString(self.observationNumber(index));
           },
           py::arg("index"))
      .def("spacecraft_instrument_id",
           [](Isis::SerialNumberList &self, int index) {
             return qStringToStdString(self.spacecraftInstrumentId(index));
           },
           py::arg("index"))
      .def("spacecraft_instrument_id",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             return qStringToStdString(self.spacecraftInstrumentId(stdStringToQString(serial_number)));
           },
           py::arg("serial_number"))
      .def("serial_number_index",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             return self.serialNumberIndex(stdStringToQString(serial_number));
           },
           py::arg("serial_number"))
      .def("file_name_index",
           [](Isis::SerialNumberList &self, const std::string &filename) {
             return self.fileNameIndex(stdStringToQString(filename));
           },
           py::arg("filename"))
      .def("possible_serial_numbers",
           [](Isis::SerialNumberList &self, const std::string &observation_number) {
             return qStringStdVectorToStdVector(
                 self.possibleSerialNumbers(stdStringToQString(observation_number)));
           },
           py::arg("observation_number"))
      .def("__contains__",
           [](Isis::SerialNumberList &self, const std::string &serial_number) {
             return self.hasSerialNumber(stdStringToQString(serial_number));
           },
           py::arg("serial_number"))
      .def("__len__", &Isis::SerialNumberList::size)
      .def("__repr__", [](const Isis::SerialNumberList &self) {
        return "SerialNumberList(size=" + std::to_string(self.size()) + ")";
      });

  py::class_<Isis::ObservationNumber, Isis::SerialNumber>(m, "ObservationNumber")
      .def(py::init<>())
      .def_static(
          "compose",
          [](Isis::Pvl &label, bool def2filename) {
            return qStringToStdString(Isis::ObservationNumber::Compose(label, def2filename));
          },
          py::arg("label"), py::arg("def2filename") = false)
      .def_static(
          "compose",
          [](Isis::Cube &cube, bool def2filename) {
            return qStringToStdString(Isis::ObservationNumber::Compose(cube, def2filename));
          },
          py::arg("cube"), py::arg("def2filename") = false)
      .def_static(
          "compose",
          [](const std::string &filename, bool def2filename) {
            return qStringToStdString(
                Isis::ObservationNumber::Compose(stdStringToQString(filename), def2filename));
          },
          py::arg("filename"), py::arg("def2filename") = false)
      .def("possible_serial",
           [](Isis::ObservationNumber &self, const std::string &observation_number,
              Isis::SerialNumberList &list) {
             return qStringStdVectorToStdVector(
                 self.PossibleSerial(stdStringToQString(observation_number), list));
           },
           py::arg("observation_number"), py::arg("list"))
      .def("__repr__", [](const Isis::ObservationNumber &) { return "ObservationNumber()"; });
}