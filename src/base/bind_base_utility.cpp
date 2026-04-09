// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS utility classes
 *
 * Source ISIS headers:
 *   - reference/upstream_isis/src/base/objs/CollectorMap/CollectorMap.h
 *   - isis/src/base/objs/Column/Column.h
 *   - isis/src/base/objs/Environment/Environment.h
 *   - isis/src/base/objs/LineEquation/LineEquation.h
 *   - reference/upstream_isis/src/base/objs/Message/Message.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-04-09  Geng Xun exposed Message namespace helpers as a Python submodule.
 * Updated: 2026-04-09  Geng Xun added CollectorMap binding using the stable int->QString specialization.
 * Updated: 2026-04-09  Geng Xun added Resource binding (PVL keyword container with name/value/status management)
 * Purpose: Expose CollectorMap, Column, Environment, LineEquation, Message helpers, and Resource utility classes to Python via pybind11.
 * Purpose: Expose Column, LineEquation, and related utility classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CollectorMap.h"
#include "Column.h"
#include "Environment.h"
#include "LineEquation.h"
#include "Message.h"
#include "helpers.h"
#include "PvlKeyword.h"
#include "PvlObject.h"
#include "Resource.h"

namespace py = pybind11;

void bind_base_utility(py::module_ &m) {
     using CollectorMapIntString = Isis::CollectorMap<int, QString>;

     py::class_<Isis::Environment>(m, "Environment")
               .def_static(
                         "user_name",
                         []() {
                              return qStringToStdString(Isis::Environment::userName());
                         },
                         "Get the current user name from the environment")
               .def_static(
                         "host_name",
                         []() {
                              return qStringToStdString(Isis::Environment::hostName());
                         },
                         "Get the current host name from the environment")
               .def_static(
                         "isis_version",
                         []() {
                              return qStringToStdString(Isis::Environment::isisVersion());
                         },
                         "Get the ISIS version string from $ISISROOT/isis_version.txt")
               .def_static(
                         "get_environment_value",
                         [](const std::string &variable, const std::string &default_value) {
                              return qStringToStdString(
                                        Isis::Environment::getEnvironmentValue(
                                                  stdStringToQString(variable),
                                                  stdStringToQString(default_value)));
                         },
                         py::arg("variable"),
                         py::arg("default_value") = "",
                         "Get an environment variable with an optional default value");

  // Added: 2026-04-09 - bind a stable Python-facing CollectorMap specialization.
  py::class_<CollectorMapIntString> collector_map(m, "CollectorMap");

  py::enum_<CollectorMapIntString::KeyPolicy>(collector_map, "KeyPolicy")
      .value("UniqueKeys", CollectorMapIntString::UniqueKeys)
      .value("DuplicateKeys", CollectorMapIntString::DuplicateKeys)
      .export_values();

  collector_map
      .def(py::init<>(), "Construct a CollectorMap with unique-key behavior.")
      .def(py::init<const CollectorMapIntString::KeyPolicy &>(),
           py::arg("key_policy"),
           "Construct a CollectorMap with the requested key policy.")
      .def(py::init<const CollectorMapIntString &>(),
           py::arg("other"),
           "Copy-construct a CollectorMap.")
      .def("size",
           &CollectorMapIntString::size,
           "Return the number of key/value pairs in the map.")
      .def("count",
           &CollectorMapIntString::count,
           py::arg("key"),
           "Return the number of entries stored under key.")
      .def("add",
           [](CollectorMapIntString &self, int key, const std::string &value) {
             self.add(key, stdStringToQString(value));
           },
           py::arg("key"), py::arg("value"),
           "Insert or replace a value, depending on the key policy.")
      .def("exists",
           &CollectorMapIntString::exists,
           py::arg("key"),
           "Return True if the key exists.")
      .def("get",
           [](CollectorMapIntString &self, int key) {
             return qStringToStdString(self.get(key));
           },
           py::arg("key"),
           "Return the value stored for key.")
      .def("index",
           &CollectorMapIntString::index,
           py::arg("key"),
           "Return the zero-based index of the first matching key, or -1.")
      .def("get_nth",
           [](CollectorMapIntString &self, int nth) {
             return qStringToStdString(self.getNth(nth));
           },
           py::arg("nth"),
           "Return the nth value in iteration order.")
      .def("key",
           &CollectorMapIntString::key,
           py::arg("nth"),
           "Return the nth key in iteration order.")
      .def("remove",
           &CollectorMapIntString::remove,
           py::arg("key"),
           "Remove all values stored under key and return the number removed.")
      .def("items",
           [](CollectorMapIntString &self) {
             py::list items;
             for (auto iter = self.begin(); iter != self.end(); ++iter) {
               items.append(py::make_tuple(iter->first, qStringToStdString(iter->second)));
             }
             return items;
           },
           "Return the map contents as a list of (key, value) tuples.")
      .def("__len__", &CollectorMapIntString::size)
      .def("__contains__",
           &CollectorMapIntString::exists,
           py::arg("key"))
      .def("__iter__",
           [](CollectorMapIntString &self) {
             py::list items;
             for (auto iter = self.begin(); iter != self.end(); ++iter) {
               items.append(py::make_tuple(iter->first, qStringToStdString(iter->second)));
             }
             return py::iter(items);
                          })
      .def("__repr__",
           [](CollectorMapIntString &self) {
             return "CollectorMap(size=" + std::to_string(self.size()) + ")";
           });

     py::module_ message = m.def_submodule("Message", "ISIS standardized message template helpers.");
     message.def("ArraySubscriptNotInRange",
                                   [](int index) {
                                        return qStringToStdString(Isis::Message::ArraySubscriptNotInRange(index));
                                   },
                                   py::arg("index"));
     message.def("KeywordAmbiguous",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordAmbiguous(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordUnrecognized",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordUnrecognized(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordDuplicated",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordDuplicated(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordNotArray",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordNotArray(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordNotFound",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordNotFound(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordBlockInvalid",
                                   [](const std::string &block) {
                                        return qStringToStdString(Isis::Message::KeywordBlockInvalid(stdStringToQString(block)));
                                   },
                                   py::arg("block"));
     message.def("KeywordBlockStartMissing",
                                   [](const std::string &block, const std::string &found) {
                                        return qStringToStdString(
                                                  Isis::Message::KeywordBlockStartMissing(stdStringToQString(block),
                                                                                                                                                      stdStringToQString(found)));
                                   },
                                   py::arg("block"), py::arg("found"));
     message.def("KeywordBlockEndMissing",
                                   [](const std::string &block, const std::string &found) {
                                        return qStringToStdString(
                                                  Isis::Message::KeywordBlockEndMissing(stdStringToQString(block),
                                                                                                                                                 stdStringToQString(found)));
                                   },
                                   py::arg("block"), py::arg("found"));
     message.def("KeywordValueBad",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordValueBad(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordValueBad",
                                   [](const std::string &key, const std::string &value) {
                                        return qStringToStdString(Isis::Message::KeywordValueBad(stdStringToQString(key),
                                                                                                                                                                                     stdStringToQString(value)));
                                   },
                                   py::arg("key"), py::arg("value"));
     message.def("KeywordValueExpected",
                                   [](const std::string &key) {
                                        return qStringToStdString(Isis::Message::KeywordValueExpected(stdStringToQString(key)));
                                   },
                                   py::arg("key"));
     message.def("KeywordValueNotInRange",
                                   [](const std::string &key, const std::string &value, const std::string &range) {
                                        return qStringToStdString(Isis::Message::KeywordValueNotInRange(stdStringToQString(key),
                                                                                                                                                                                                        stdStringToQString(value),
                                                                                                                                                                                                        stdStringToQString(range)));
                                   },
                                   py::arg("key"), py::arg("value"), py::arg("range"));
     message.def("KeywordValueNotInList",
                                   [](const std::string &key,
                                         const std::string &value,
                                         const std::vector<std::string> &list) {
                                        std::vector<QString> qlist;
                                        qlist.reserve(list.size());
                                        for (const std::string &item : list) {
                                             qlist.push_back(stdStringToQString(item));
                                        }
                                        return qStringToStdString(Isis::Message::KeywordValueNotInList(stdStringToQString(key),
                                                                                                                                                                                                    stdStringToQString(value),
                                                                                                                                                                                                    qlist));
                                   },
                                   py::arg("key"), py::arg("value"), py::arg("list"));
     message.def("MissingDelimiter",
                                   [](char delimiter) {
                                        return qStringToStdString(Isis::Message::MissingDelimiter(delimiter));
                                   },
                                   py::arg("delimiter"));
     message.def("MissingDelimiter",
                                   [](char delimiter, const std::string &near) {
                                        return qStringToStdString(Isis::Message::MissingDelimiter(delimiter,
                                                                                                                                                                                     stdStringToQString(near)));
                                   },
                                   py::arg("delimiter"), py::arg("near"));
     message.def("FileOpen",
                                   [](const std::string &filename) {
                                        return qStringToStdString(Isis::Message::FileOpen(stdStringToQString(filename)));
                                   },
                                   py::arg("filename"));
     message.def("FileCreate",
                                   [](const std::string &filename) {
                                        return qStringToStdString(Isis::Message::FileCreate(stdStringToQString(filename)));
                                   },
                                   py::arg("filename"));
     message.def("FileRead",
                                   [](const std::string &filename) {
                                        return qStringToStdString(Isis::Message::FileRead(stdStringToQString(filename)));
                                   },
                                   py::arg("filename"));
     message.def("FileWrite",
                                   [](const std::string &filename) {
                                        return qStringToStdString(Isis::Message::FileWrite(stdStringToQString(filename)));
                                   },
                                   py::arg("filename"));
     message.def("MemoryAllocationFailed",
                                   []() {
                                        return qStringToStdString(Isis::Message::MemoryAllocationFailed());
                                   });

  /**
   * @brief Bindings for the Isis::Column class
   * Column class provides functionality for formatting and managing table columns.
   * @see Isis::Column
   */
  py::class_<Isis::Column> column(m, "Column");

  // Align enum
  py::enum_<Isis::Column::Align>(column, "Align")
      .value("NoAlign", Isis::Column::NoAlign)
      .value("Right", Isis::Column::Right)
      .value("Left", Isis::Column::Left)
      .value("Decimal", Isis::Column::Decimal)
      .export_values();

  // Type enum
  py::enum_<Isis::Column::Type>(column, "Type")
      .value("NoType", Isis::Column::NoType)
      .value("Integer", Isis::Column::Integer)
      .value("Real", Isis::Column::Real)
      .value("String", Isis::Column::String)
      .value("Pixel", Isis::Column::Pixel)
      .export_values();

  column
      .def(py::init<>())
      // Configuration methods
      .def("set_name",
           [](Isis::Column &self, const std::string &name) {
             self.SetName(stdStringToQString(name));
           },
           py::arg("name"),
           "Set the column name")
      .def("set_width",
           &Isis::Column::SetWidth,
           py::arg("width"),
           "Set the column width")
      .def("set_type",
           &Isis::Column::SetType,
           py::arg("type"),
           "Set the column data type")
      .def("set_alignment",
           &Isis::Column::SetAlignment,
           py::arg("alignment"),
           "Set the column alignment")
      .def("set_precision",
           &Isis::Column::SetPrecision,
           py::arg("precision"),
           "Set the column precision for real numbers")
      // Query methods
      .def("name",
           [](const Isis::Column &self) {
             return qStringToStdString(self.Name());
           },
           "Get the column name")
      .def("width", &Isis::Column::Width, "Get the column width")
      .def("data_type", &Isis::Column::DataType, "Get the column data type")
      .def("alignment", &Isis::Column::Alignment, "Get the column alignment")
      .def("precision", &Isis::Column::Precision, "Get the column precision")
      .def("__repr__", [](const Isis::Column &self) {
        return "Column(name='" + qStringToStdString(self.Name()) + "', " +
               "width=" + std::to_string(self.Width()) + ", " +
               "precision=" + std::to_string(self.Precision()) + ")";
      });

  /**
   * @brief Bindings for the Isis::LineEquation class
   * Added: 2026-03-30 - expose LineEquation utility class
   *
   * LineEquation provides functionality for creating and using cartesian line equations.
   * Note: The upstream ISIS header has inline methods (Defined, Points, HaveSlope, HaveIntercept)
   * that are not marked const, requiring const_cast workarounds in __repr__.
   *
   *
   * Source ISIS header: isis/src/base/objs/LineEquation/LineEquation.h
   * Source class: LineEquation
   * Source header author(s): Debbie A. Cook (2006-10-19)
   * Binding author: Geng Xun
   * Created: 2026-03-30
   * Updated: 2026-03-30
   * Purpose: Expose cartesian line equation utilities to Python.
   *
   * LineEquation provides functionality for creating and using cartesian line equations.
   * Computes slope and intercept from two points. Throws exceptions for vertical lines
   * (identical x-coordinates) and undefined lines (less than 2 points).
   * @see Isis::LineEquation
   */
  py::class_<Isis::LineEquation>(m, "LineEquation")
      .def(py::init<>(),
           "Default constructor - creates an undefined line equation")
      .def(py::init<double, double, double, double>(),
           py::arg("x1"), py::arg("y1"), py::arg("x2"), py::arg("y2"),
           "Construct a line equation from two points")
      .def("add_point",
           &Isis::LineEquation::AddPoint,
           py::arg("x"), py::arg("y"),
           "Add a point to the line equation (max 2 points)")
      .def("slope",
           &Isis::LineEquation::Slope,
           "Compute and return the slope of the line")
      .def("intercept",
           &Isis::LineEquation::Intercept,
           "Compute and return the y-intercept of the line")
      .def("points",
           &Isis::LineEquation::Points,
           "Return the number of points added to the line equation")
      .def("have_slope",
           &Isis::LineEquation::HaveSlope,
           "Check if the slope has been computed")
      .def("have_intercept",
           &Isis::LineEquation::HaveIntercept,
           "Check if the intercept has been computed")
      .def("defined",
           &Isis::LineEquation::Defined,
           "Check if the line equation is defined (has 2 points)")
      .def("__repr__", [](Isis::LineEquation &self) {
        // Note: Using non-const reference because upstream methods are not const
        std::string repr = "LineEquation(";
        if (self.Defined()) {
          repr += "defined=True, ";
          repr += "points=" + std::to_string(self.Points());
          if (self.HaveSlope()) {
            repr += ", slope=" + std::to_string(self.Slope());
          }
          if (self.HaveIntercept()) {
            repr += ", intercept=" + std::to_string(self.Intercept());
          }
        } else {
          repr += "defined=False, points=" + std::to_string(self.Points());
        }
        repr += ")";
        return repr;
      });

  // Added: 2026-04-09 - bind Isis::Resource
  /**
   * @brief Bindings for the Isis::Resource class
   * Resource provides a named container of PVL keywords used by ISIS Strategy
   * classes. It supports keyword get/set/erase, active/discarded status, and
   * named asset slots. GisGeometry-related methods are not exposed here.
   *
   * Source ISIS header: reference/upstream_isis/src/base/objs/Resource/Resource.h
   * Source class: Isis::Resource
   * Source header author(s): Kris Becker (2012-07-15)
   * Binding author: Geng Xun
   */
  py::class_<Isis::Resource>(m, "Resource")
      .def(py::init<>(), "Construct an unnamed Resource (name defaults to 'Resource').")
      .def(py::init([](const std::string &name) {
             return Isis::Resource(stdStringToQString(name));
           }),
           py::arg("name"),
           "Construct a Resource with the given name.")
      .def(py::init<const Isis::Resource &>(), py::arg("other"), "Copy-construct a Resource.")
      .def("name",
           [](const Isis::Resource &self) {
             return qStringToStdString(self.name());
           },
           "Return the resource name.")
      .def("set_name",
           [](Isis::Resource &self, const std::string &identity) {
             self.setName(stdStringToQString(identity));
           },
           py::arg("identity"),
           "Set the resource name (also updates the Identity keyword).")
      .def("is_equal",
           &Isis::Resource::isEqual,
           py::arg("other"),
           "Test whether this Resource and other share the same keyword set.")
      .def("exists",
           [](const Isis::Resource &self, const std::string &keyword_name) {
             return self.exists(stdStringToQString(keyword_name));
           },
           py::arg("keyword_name"),
           "Return True if the named keyword exists.")
      .def("count",
           [](const Isis::Resource &self, const std::string &keyword_name) {
             return self.count(stdStringToQString(keyword_name));
           },
           py::arg("keyword_name"),
           "Return the number of values held by the named keyword.")
      .def("is_null",
           [](const Isis::Resource &self,
              const std::string &keyword_name,
              int keyword_index) {
             return self.isNull(stdStringToQString(keyword_name), keyword_index);
           },
           py::arg("keyword_name"), py::arg("keyword_index") = 0,
           "Return True if the specified keyword value is null.")
      .def("value",
           [](const Isis::Resource &self,
              const std::string &keyword_name,
              int keyword_index) {
             return qStringToStdString(
                 self.value(stdStringToQString(keyword_name), keyword_index));
           },
           py::arg("keyword_name"), py::arg("keyword_index") = 0,
           "Return the keyword value as a string.")
      .def("value",
           [](const Isis::Resource &self,
              const std::string &keyword_name,
              const std::string &default_value,
              int keyword_index) {
             return qStringToStdString(
                 self.value(stdStringToQString(keyword_name),
                            stdStringToQString(default_value),
                            keyword_index));
           },
           py::arg("keyword_name"), py::arg("default_value"), py::arg("keyword_index") = 0,
           "Return the keyword value as a string, or default_value if the keyword is absent.")
      .def("add",
           [](Isis::Resource &self,
              const std::string &keyword_name,
              const std::string &keyword_value) {
             self.add(stdStringToQString(keyword_name),
                      stdStringToQString(keyword_value));
           },
           py::arg("keyword_name"), py::arg("keyword_value"),
           "Add a keyword name/value pair.")
      .def("add",
           [](Isis::Resource &self, Isis::PvlKeyword &kw) {
             self.add(kw);
           },
           py::arg("keyword"),
           "Add a PvlKeyword object.")
      .def("append",
           [](Isis::Resource &self,
              const std::string &keyword_name,
              const std::string &keyword_value) {
             self.append(stdStringToQString(keyword_name),
                         stdStringToQString(keyword_value));
           },
           py::arg("keyword_name"), py::arg("keyword_value"),
           "Append a value to an existing keyword (creates it if absent).")
      .def("erase",
           [](Isis::Resource &self, const std::string &keyword_name) {
             return self.erase(stdStringToQString(keyword_name));
           },
           py::arg("keyword_name"),
           "Remove the named keyword. Returns number of keywords removed.")
      .def("activate",
           &Isis::Resource::activate,
           "Mark this resource as active (not discarded).")
      .def("is_active",
           &Isis::Resource::isActive,
           "Return True if this resource is active.")
      .def("discard",
           &Isis::Resource::discard,
           "Mark this resource as discarded (inactive).")
      .def("is_discarded",
           &Isis::Resource::isDiscarded,
           "Return True if this resource has been discarded.")
      .def("to_pvl",
           [](Isis::Resource &self, const std::string &pvl_name) {
             return self.toPvl(stdStringToQString(pvl_name));
           },
           py::arg("pvl_name") = "Resource",
           "Serialize this resource to a PvlObject.")
      .def("__repr__", [](const Isis::Resource &self) {
        return "Resource('" + qStringToStdString(self.name()) + "')";
      });
}
