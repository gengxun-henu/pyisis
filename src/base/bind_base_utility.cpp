// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS utility classes
 *
 * Source ISIS headers:
 *   - reference/upstream_isis/src/base/objs/CollectorMap/CollectorMap.h
 *   - isis/src/base/objs/Column/Column.h
 *   - reference/upstream_isis/src/base/objs/EndianSwapper/EndianSwapper.h
 *   - isis/src/base/objs/Environment/Environment.h
 *   - reference/upstream_isis/src/base/objs/ID/ID.h
 *   - reference/upstream_isis/src/base/objs/IString/IString.h
 *   - isis/src/base/objs/LineEquation/LineEquation.h
 *   - reference/upstream_isis/src/base/objs/Message/Message.h
 *   - reference/upstream_isis/src/base/objs/Pixel/Pixel.h
 *   - reference/upstream_isis/src/base/objs/Plugin/Plugin.h
 *   - reference/upstream_isis/src/base/objs/TextFile/TextFile.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-04-09  Geng Xun exposed Message namespace helpers as a Python submodule.
 * Updated: 2026-04-09  Geng Xun added CollectorMap binding using the stable int->QString specialization.
 * Updated: 2026-04-09  Geng Xun added Resource binding (PVL keyword container with name/value/status management)
 * Updated: 2026-04-09  Geng Xun added Plugin binding with opaque function-address lookup for runtime plugin resolution tests.
 * Updated: 2026-04-09  Geng Xun added IString binding and free-function helpers (to_bool/to_int/to_double/to_string).
 * Updated: 2026-04-10  Geng Xun added Pixel, ID, EndianSwapper, and TextFile bindings.
 * Updated: 2026-04-10  Geng Xun fixed Pixel predicate bindings to evaluate SpecialPixel semantics explicitly in Python wrappers.
 * Updated: 2026-04-11  Geng Xun fixed PolygonTools/GSLUtility bindings to match the actual ISIS 9.0.0 public API and singleton lifetime rules.
 * Updated: 2026-04-11  Geng Xun exported PolygonTools as a real Python utility class while preserving module-level helper aliases for backward compatibility.
 * Purpose: Expose CollectorMap, Column, EndianSwapper, Environment, ID, IString, LineEquation, Message helpers, Pixel, Plugin, Resource, and TextFile utility classes to Python via pybind11.
 */

#include <cmath>
#include <cstdint>
#include <fstream>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CollectorMap.h"
#include "Column.h"
#include "EndianSwapper.h"
#include "Environment.h"
#include "GSLUtility.h"
#include "ID.h"
#include "IString.h"
#include "LineEquation.h"
#include "Message.h"
#include "Pixel.h"
#include "Plugin.h"
#include "PolygonTools.h"
#include "PvlKeyword.h"
#include "PvlObject.h"
#include "Resource.h"
#include "SpecialPixel.h"
#include "TextFile.h"
#include "helpers.h"

namespace py = pybind11;

namespace {

bool isRuntimeSpecialPixel(double dn) {
     return dn < -1.0e300;
}

int polygonDecimalPlace(double num) {
     if (num == 0.0) {
          return 0;
     }

     num = std::fabs(num);

     int decimalPlace = 1;
     while (num < 1.0) {
          num *= 10.0;
          decimalPlace--;
     }

     while (num > 10.0) {
          num /= 10.0;
          decimalPlace++;
     }

     return decimalPlace;
}

class PolygonToolsWrapper {
  public:
     PolygonToolsWrapper() = default;
};

class PluginWrapper {
  public:
     PluginWrapper() = default;

     void read(const std::string &fileName) {
          m_plugin.read(stdStringToQString(fileName));
     }

     void addGroup(Isis::PvlGroup &group) {
          m_plugin.addGroup(group);
     }

     Isis::PvlGroup &findGroup(const std::string &name) {
          return m_plugin.findGroup(stdStringToQString(name));
     }

     int groups() const {
          return m_plugin.groups();
     }

     std::uintptr_t getPlugin(const std::string &group) {
          const auto plugin = m_plugin.GetPlugin(stdStringToQString(group));
          return reinterpret_cast<std::uintptr_t>(plugin);
     }

     std::string repr() const {
          return "Plugin(groups=" + std::to_string(m_plugin.groups()) + ")";
     }

  private:
     Isis::Plugin m_plugin;
};

}  // namespace

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

     py::class_<PluginWrapper>(m, "Plugin")
               .def(py::init<>(), "Construct an empty Plugin PVL container.")
               .def("read",
                          &PluginWrapper::read,
                          py::arg("file_name"),
                          "Read a plugin definition file into this Plugin wrapper.")
               .def("add_group",
                          &PluginWrapper::addGroup,
                          py::arg("group"),
                          "Add a PVL group containing Library/Routine metadata.")
               .def("find_group",
                          &PluginWrapper::findGroup,
                          py::arg("name"),
                          py::return_value_policy::reference_internal,
                          "Return a reference to a named PVL group stored in this Plugin wrapper.")
               .def("groups",
                          &PluginWrapper::groups,
                          "Return the number of top-level groups stored in this Plugin wrapper.")
               .def("get_plugin",
                          &PluginWrapper::getPlugin,
                          py::arg("group"),
                          "Resolve the named plugin group and return the loaded function address as a Python integer.")
               .def("__repr__", &PluginWrapper::repr);

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

  // Added: 2026-04-09 - IString binding and module-level free-function helpers
  // Free functions exposed at module level
  m.def("to_bool",
        [](const std::string &s) {
          return Isis::toBool(stdStringToQString(s));
        },
        py::arg("string"),
        "Convert a string to bool. Recognises true/false/yes/no/on/off/1/0 (case-insensitive).");

  m.def("to_int",
        [](const std::string &s) {
          return Isis::toInt(stdStringToQString(s));
        },
        py::arg("string"),
        "Convert a string to int. Raises IException on failure.");

  m.def("to_big_int",
        [](const std::string &s) -> long long {
          return static_cast<long long>(Isis::toBigInt(stdStringToQString(s)));
        },
        py::arg("string"),
        "Convert a string to a 64-bit integer. Raises IException on failure.");

  m.def("to_double",
        [](const std::string &s) {
          return Isis::toDouble(stdStringToQString(s));
        },
        py::arg("string"),
        "Convert a string to double. Raises IException on failure.");

  m.def("to_string",
        [](bool v) { return qStringToStdString(Isis::toString(v)); },
        py::arg("value"),
        "Convert bool to string.");
  m.def("to_string",
        [](int v) { return qStringToStdString(Isis::toString(v)); },
        py::arg("value"),
        "Convert int to string.");
  m.def("to_string",
        [](long long v) { return qStringToStdString(Isis::toString(static_cast<Isis::BigInt>(v))); },
        py::arg("value"),
        "Convert 64-bit integer to string.");
  m.def("to_string",
        [](double v, int precision) { return qStringToStdString(Isis::toString(v, precision)); },
        py::arg("value"), py::arg("precision") = 14,
        "Convert double to string with optional precision.");

  // IString class binding
  py::class_<Isis::IString>(m, "IString")
      .def(py::init<>(), "Construct an empty IString.")
      .def(py::init<const std::string &>(), py::arg("str"),
           "Construct IString from a Python str.")
      .def(py::init<const Isis::IString &>(), py::arg("other"),
           "Copy-construct from another IString.")
      .def(py::init<int>(), py::arg("num"),
           "Construct IString from an integer.")
      .def(py::init([](double v) { return Isis::IString(v); }), py::arg("num"),
           "Construct IString from a double.")
      .def(py::init([](long long v) {
            return Isis::IString(static_cast<Isis::BigInt>(v));
           }), py::arg("num"),
           "Construct IString from a 64-bit integer.")

      // Instance methods
      .def("trim",
           [](Isis::IString &self, const std::string &chars) -> std::string {
             return std::string(self.Trim(chars));
           },
           py::arg("chars"),
           "Remove leading and trailing characters from the given set.")
      .def_static("trim_static",
                  [](const std::string &chars, const std::string &str) {
                    return Isis::IString::Trim(chars, str);
                  },
                  py::arg("chars"), py::arg("str"),
                  "Static: trim leading/trailing chars from str.")
      .def("trim_head",
           [](Isis::IString &self, const std::string &chars) -> std::string {
             return std::string(self.TrimHead(chars));
           },
           py::arg("chars"),
           "Remove leading characters from the given set.")
      .def_static("trim_head_static",
                  [](const std::string &chars, const std::string &str) {
                    return Isis::IString::TrimHead(chars, str);
                  },
                  py::arg("chars"), py::arg("str"),
                  "Static: trim leading chars from str.")
      .def("trim_tail",
           [](Isis::IString &self, const std::string &chars) -> std::string {
             return std::string(self.TrimTail(chars));
           },
           py::arg("chars"),
           "Remove trailing characters from the given set.")
      .def_static("trim_tail_static",
                  [](const std::string &chars, const std::string &str) {
                    return Isis::IString::TrimTail(chars, str);
                  },
                  py::arg("chars"), py::arg("str"),
                  "Static: trim trailing chars from str.")
      .def("up_case",
           [](Isis::IString &self) -> std::string {
             return std::string(self.UpCase());
           },
           "Convert the string to uppercase in place and return it.")
      .def_static("up_case_static",
                  [](const std::string &str) { return Isis::IString::UpCase(str); },
                  py::arg("str"),
                  "Static: return uppercase copy of str.")
      .def("down_case",
           [](Isis::IString &self) -> std::string {
             return std::string(self.DownCase());
           },
           "Convert the string to lowercase in place and return it.")
      .def_static("down_case_static",
                  [](const std::string &str) { return Isis::IString::DownCase(str); },
                  py::arg("str"),
                  "Static: return lowercase copy of str.")
      .def("to_integer",
           [](const Isis::IString &self) { return self.ToInteger(); },
           "Convert the string to an integer. Raises IException on failure.")
      .def_static("to_integer_static",
                  [](const std::string &str) { return Isis::IString::ToInteger(str); },
                  py::arg("str"),
                  "Static: convert str to integer.")
      .def("to_double",
           [](const Isis::IString &self) { return self.ToDouble(); },
           "Convert the string to a double. Raises IException on failure.")
      .def_static("to_double_static",
                  [](const std::string &str) { return Isis::IString::ToDouble(str); },
                  py::arg("str"),
                  "Static: convert str to double.")
      .def("to_big_integer",
           [](const Isis::IString &self) -> long long {
             return static_cast<long long>(self.ToBigInteger());
           },
           "Convert the string to a 64-bit integer. Raises IException on failure.")
      .def("token",
           [](Isis::IString &self, const std::string &separator) -> std::string {
             Isis::IString sep(separator);
             return std::string(self.Token(sep));
           },
           py::arg("separator"),
           "Extract and return the next token delimited by any character in separator. Modifies the string in place.")
      .def_static("split",
                  [](char separator, const std::string &instr, bool allow_empty) {
                    std::vector<std::string> tokens;
                    Isis::IString::Split(separator, instr, tokens, allow_empty);
                    return tokens;
                  },
                  py::arg("separator"), py::arg("instr"),
                  py::arg("allow_empty") = true,
                  "Static: split instr on separator char, return list of tokens.")
      .def("compress",
           [](Isis::IString &self, bool force) -> std::string {
             return std::string(self.Compress(force));
           },
           py::arg("force") = false,
           "Compress consecutive whitespace to single spaces (force=True collapses quoted whitespace too).")
      .def_static("compress_static",
                  [](const std::string &str, bool force) {
                    return Isis::IString::Compress(str, force);
                  },
                  py::arg("str"), py::arg("force") = false,
                  "Static: compress whitespace in str.")
      .def("replace",
           [](Isis::IString &self, const std::string &from, const std::string &to, int max_count) -> std::string {
             return std::string(self.Replace(from, to, max_count));
           },
           py::arg("from_str"), py::arg("to_str"), py::arg("max_count") = 20,
           "Replace occurrences of from_str with to_str (up to max_count replacements).")
      .def("replace_honor_quotes",
           [](Isis::IString &self, const std::string &from, const std::string &to, bool honor_quotes) -> std::string {
             return std::string(self.Replace(from, to, honor_quotes));
           },
           py::arg("from_str"), py::arg("to_str"), py::arg("honor_quotes"),
           "Replace from_str with to_str, optionally honouring quoted substrings.")
      .def("convert",
           [](Isis::IString &self, const std::string &list_of_chars, char to) -> std::string {
             return std::string(self.Convert(list_of_chars, to));
           },
           py::arg("list_of_chars"), py::arg("to"),
           "Replace every character in list_of_chars with the character to.")
      .def("convert_whitespace",
           [](Isis::IString &self) -> std::string {
             return std::string(self.ConvertWhiteSpace());
           },
           "Replace all whitespace characters (tab, newline, etc.) with a space.")
      .def("remove",
           [](Isis::IString &self, const std::string &del) -> std::string {
             return std::string(self.Remove(del));
           },
           py::arg("chars"),
           "Remove all characters in chars from the string.")
      .def("equal",
           [](const Isis::IString &self, const std::string &str) {
             return self.Equal(str);
           },
           py::arg("str"),
           "Return True if both strings are equal (case-insensitive). Deprecated: prefer ==.")

      // Python protocol methods
      .def("__str__",
           [](const Isis::IString &self) { return std::string(self); })
      .def("__repr__",
           [](const Isis::IString &self) {
             return "IString('" + std::string(self) + "')";
           })
      .def("__int__",
           [](const Isis::IString &self) { return self.ToInteger(); })
      .def("__float__",
           [](const Isis::IString &self) { return self.ToDouble(); })
      .def("__len__",
           [](const Isis::IString &self) { return self.size(); })
      .def("__eq__",
           [](const Isis::IString &self, const std::string &other) {
             return std::string(self) == other;
           }, py::arg("other"));

  // ── Pixel ──────────────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::Pixel value type with constructors, accessors,
  //   conversion methods, and static special-pixel predicates.
  py::class_<Isis::Pixel>(m, "Pixel")
      .def(py::init<>(),
           "Construct a default Pixel (sample=0, line=0, band=0, DN=NULL).")
      .def(py::init<int, int, int, double>(),
           py::arg("sample"), py::arg("line"), py::arg("band"), py::arg("dn"),
           "Construct a Pixel with sample, line, band, and DN.")
      .def("line", &Isis::Pixel::line, "Return the line coordinate.")
      .def("sample", &Isis::Pixel::sample, "Return the sample coordinate.")
      .def("band", &Isis::Pixel::band, "Return the band coordinate.")
      .def("dn", &Isis::Pixel::DN, "Return the DN (data number) value.")
      // Instance conversion methods
      .def("to_8bit",
           static_cast<unsigned char (Isis::Pixel::*)()>(&Isis::Pixel::To8Bit),
           "Convert DN to 8-bit unsigned char.")
      .def("to_16bit",
           static_cast<short int (Isis::Pixel::*)()>(&Isis::Pixel::To16Bit),
           "Convert DN to 16-bit signed short.")
      .def("to_16ubit",
           static_cast<short unsigned int (Isis::Pixel::*)()>(&Isis::Pixel::To16Ubit),
           "Convert DN to 16-bit unsigned short.")
      .def("to_32bit",
           static_cast<float (Isis::Pixel::*)()>(&Isis::Pixel::To32Bit),
           "Convert DN to 32-bit float.")
      .def("to_double",
           static_cast<double (Isis::Pixel::*)()>(&Isis::Pixel::ToDouble),
           "Convert DN to double.")
      .def("to_float",
           static_cast<float (Isis::Pixel::*)()>(&Isis::Pixel::ToFloat),
           "Convert DN to float.")
      .def("to_string",
           static_cast<std::string (Isis::Pixel::*)()>(&Isis::Pixel::ToString),
           "Convert DN to string representation.")
      // Instance special-pixel predicates
      .def("is_special",
                          [](Isis::Pixel &self) {
                               const double dn = self.DN();
             return isRuntimeSpecialPixel(dn);
                          },
           "Return True if the pixel DN is a special value.")
      .def("is_valid",
                          [](Isis::Pixel &self) {
             return !isRuntimeSpecialPixel(self.DN());
                          },
           "Return True if the pixel DN is a valid (non-special) value.")
      .def("is_null",
                          [](Isis::Pixel &self) {
             return isRuntimeSpecialPixel(self.DN());
                          },
           "Return True if the pixel DN is the NULL special value.")
      .def("is_high",
                          [](Isis::Pixel &self) {
                               const double dn = self.DN();
                               return dn == Isis::Hrs || dn == Isis::His;
                          },
           "Return True if the pixel DN is HRS or HIS.")
      .def("is_low",
                          [](Isis::Pixel &self) {
                               const double dn = self.DN();
                               return dn == Isis::Lrs || dn == Isis::Lis;
                          },
           "Return True if the pixel DN is LRS or LIS.")
      .def("is_hrs",
                          [](Isis::Pixel &self) {
                               return self.DN() == Isis::HIGH_REPR_SAT8;
                          },
           "Return True if the pixel DN is High Representation Saturation.")
      .def("is_his",
                          [](Isis::Pixel &self) {
                               return self.DN() == Isis::HIGH_INSTR_SAT8;
                          },
           "Return True if the pixel DN is High Instrument Saturation.")
      .def("is_lis",
                          [](Isis::Pixel &self) {
                               return self.DN() == Isis::LOW_INSTR_SAT8;
                          },
           "Return True if the pixel DN is Low Instrument Saturation.")
      .def("is_lrs",
                          [](Isis::Pixel &self) {
                               return self.DN() == Isis::LOW_REPR_SAT8;
                          },
           "Return True if the pixel DN is Low Representation Saturation.")
      // Static conversion methods (operate on a raw double/float value)
      .def_static("to_8bit_value",
                  static_cast<unsigned char (*)(const double)>(&Isis::Pixel::To8Bit),
                  py::arg("d"),
                  "Convert a double DN value to 8-bit unsigned char.")
      .def_static("to_16bit_value",
                  static_cast<short int (*)(const double)>(&Isis::Pixel::To16Bit),
                  py::arg("d"),
                  "Convert a double DN value to 16-bit signed short.")
      .def_static("to_16ubit_value",
                  static_cast<short unsigned int (*)(const double)>(&Isis::Pixel::To16UBit),
                  py::arg("d"),
                  "Convert a double DN value to 16-bit unsigned short.")
      .def_static("to_32bit_value",
                  static_cast<float (*)(const double)>(&Isis::Pixel::To32Bit),
                  py::arg("d"),
                  "Convert a double DN value to 32-bit float.")
      .def_static("to_double_from_float",
                  static_cast<double (*)(const float)>(&Isis::Pixel::ToDouble),
                  py::arg("f"),
                  "Convert a 32-bit float pixel value to double.")
      .def_static("to_string_value",
                  static_cast<std::string (*)(double)>(&Isis::Pixel::ToString),
                  py::arg("d"),
                  "Convert a double DN value to its string representation.")
      // Static special-pixel predicates (operate on a raw double)
      .def_static("is_special_value",
                                             [](double d) {
                                                  return isRuntimeSpecialPixel(d);
                                             },
                  py::arg("d"),
                  "Return True if d is a special pixel value.")
      .def_static("is_valid_value",
                                             [](double d) {
                                                  return !isRuntimeSpecialPixel(d);
                                             },
                  py::arg("d"),
                  "Return True if d is a valid (non-special) pixel value.")
      .def_static("is_null_value",
                                             [](double d) {
                                                  return isRuntimeSpecialPixel(d);
                                             },
                  py::arg("d"),
                  "Return True if d is the NULL special value.")
      .def_static("is_high_value",
                                             [](double d) {
                                                  return d == Isis::Hrs || d == Isis::His;
                                             },
                  py::arg("d"),
                  "Return True if d is HRS or HIS.")
      .def_static("is_low_value",
                                             [](double d) {
                                                  return d == Isis::Lrs || d == Isis::Lis;
                                             },
                  py::arg("d"),
                  "Return True if d is LRS or LIS.")
      .def_static("is_hrs_value",
                                             [](double d) {
                                                  return d == Isis::Hrs;
                                             },
                  py::arg("d"),
                  "Return True if d is High Representation Saturation.")
      .def_static("is_his_value",
                                             [](double d) {
                                                  return d == Isis::His;
                                             },
                  py::arg("d"),
                  "Return True if d is High Instrument Saturation.")
      .def_static("is_lis_value",
                                             [](double d) {
                                                  return d == Isis::Lis;
                                             },
                  py::arg("d"),
                  "Return True if d is Low Instrument Saturation.")
      .def_static("is_lrs_value",
                                             [](double d) {
                                                  return d == Isis::Lrs;
                                             },
                  py::arg("d"),
                  "Return True if d is Low Representation Saturation.")
      .def("__repr__", [](const Isis::Pixel &p) {
            return "Pixel(sample=" + std::to_string(p.sample()) +
                   ", line=" + std::to_string(p.line()) +
                   ", band=" + std::to_string(p.band()) +
                   ", dn=" + std::to_string(p.DN()) + ")";
          });

  // ── ID ─────────────────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::ID sequential ID generator.
  py::class_<Isis::ID>(m, "ID")
      .def(py::init([](const std::string &name, int basenum) {
             return new Isis::ID(stdStringToQString(name), basenum);
           }),
           py::arg("name"), py::arg("basenum") = 1,
           "Construct an ID generator from a template string containing '?' "
           "placeholders and an optional start number (default 1).")
      .def("next",
           [](Isis::ID &self) {
             return qStringToStdString(self.Next());
           },
           "Return the next ID in the sequence and advance the counter.")
      .def("__repr__", [](Isis::ID &self) {
            return "ID(next='" + qStringToStdString(self.Next()) + "')";
          });

  // ── EndianSwapper ──────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::EndianSwapper byte-swap utilities.
  // The upstream methods take raw void* pointers.  We wrap each one to accept
  // a Python bytes/bytearray object and return the swapped value.
  py::class_<Isis::EndianSwapper>(m, "EndianSwapper")
      .def(py::init([](const std::string &endian) {
             return new Isis::EndianSwapper(stdStringToQString(endian));
           }),
           py::arg("endian"),
           "Construct an EndianSwapper for the given endian type ('LSB' or 'MSB').")
      .def("will_swap", &Isis::EndianSwapper::willSwap,
           "Return True if byte-swapping is required for the current platform.")
      .def("swap_double",
           [](Isis::EndianSwapper &self, py::bytes buf) {
             std::string s(buf);
             if (s.size() < sizeof(double)) {
               throw py::value_error("Buffer too small for double (need 8 bytes)");
             }
             return self.Double(static_cast<void *>(s.data()));
           },
           py::arg("buf"),
           "Swap bytes in an 8-byte buffer and return as double.")
      .def("swap_float",
           [](Isis::EndianSwapper &self, py::bytes buf) {
             std::string s(buf);
             if (s.size() < sizeof(float)) {
               throw py::value_error("Buffer too small for float (need 4 bytes)");
             }
             return self.Float(static_cast<void *>(s.data()));
           },
           py::arg("buf"),
           "Swap bytes in a 4-byte buffer and return as float.")
      .def("swap_int",
           [](Isis::EndianSwapper &self, py::bytes buf) {
             std::string s(buf);
             if (s.size() < sizeof(int)) {
               throw py::value_error("Buffer too small for int (need 4 bytes)");
             }
             return self.Int(static_cast<void *>(s.data()));
           },
           py::arg("buf"),
           "Swap bytes in a 4-byte buffer and return as int.")
      .def("swap_short",
           [](Isis::EndianSwapper &self, py::bytes buf) {
             std::string s(buf);
             if (s.size() < sizeof(short int)) {
               throw py::value_error("Buffer too small for short int (need 2 bytes)");
             }
             return self.ShortInt(static_cast<void *>(s.data()));
           },
           py::arg("buf"),
           "Swap bytes in a 2-byte buffer and return as short int.")
      .def("swap_unsigned_short",
           [](Isis::EndianSwapper &self, py::bytes buf) {
             std::string s(buf);
             if (s.size() < sizeof(unsigned short int)) {
               throw py::value_error("Buffer too small for unsigned short int (need 2 bytes)");
             }
             return self.UnsignedShortInt(static_cast<void *>(s.data()));
           },
           py::arg("buf"),
           "Swap bytes in a 2-byte buffer and return as unsigned short int.")
      .def("__repr__", [](const Isis::EndianSwapper &self) {
            return std::string("EndianSwapper(will_swap=") +
                   (self.willSwap() ? "True" : "False") + ")";
          });

  // ── TextFile ───────────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::TextFile sequential ASCII file I/O.
  py::class_<Isis::TextFile>(m, "TextFile")
      .def(py::init<>(), "Construct an empty TextFile (not yet opened).")
      .def(py::init([](const std::string &filename,
                       const std::string &openmode,
                       const std::string &extension) {
             return new Isis::TextFile(
                 stdStringToQString(filename), openmode.c_str(), extension.c_str());
           }),
           py::arg("filename"),
           py::arg("openmode") = "input",
           py::arg("extension") = "",
           "Construct a TextFile and open the given file.")
      .def("open",
           [](Isis::TextFile &self,
              const std::string &filename,
              const std::string &openmode,
              const std::string &extension) {
             self.Open(stdStringToQString(filename), openmode.c_str(), extension.c_str());
           },
           py::arg("filename"),
           py::arg("openmode") = "input",
           py::arg("extension") = "",
           "Open a file for reading or writing.")
      .def("open_chk",
           &Isis::TextFile::OpenChk,
           py::arg("bail_if_not_open") = false,
           "Check whether the file is currently open.")
      .def("rewind", &Isis::TextFile::Rewind, "Seek back to the beginning of the file.")
      .def("close", &Isis::TextFile::Close, "Close the file.")
      .def("get_file",
           [](Isis::TextFile &self,
              int max_lines,
              bool skip_comments) -> std::vector<std::string> {
             std::vector<QString> lines;
             self.GetFile(lines, max_lines, skip_comments);
             std::vector<std::string> result;
             result.reserve(lines.size());
             for (const auto &l : lines) {
               result.push_back(qStringToStdString(l));
             }
             return result;
           },
           py::arg("max_lines") = 0,
           py::arg("skip_comments") = true,
           "Read all (or up to max_lines) lines from the file and return as a list.")
      .def("put_file",
           [](Isis::TextFile &self, const std::vector<std::string> &lines, int max_lines) {
             std::vector<QString> qlines;
             qlines.reserve(lines.size());
             for (const auto &l : lines) {
               qlines.push_back(stdStringToQString(l));
             }
             self.PutFile(qlines, max_lines);
           },
           py::arg("lines"),
           py::arg("max_lines") = 0,
           "Write all (or up to max_lines) lines to the file.")
      .def("get_line",
           [](Isis::TextFile &self, bool skip_comments) -> py::object {
             QString line;
             bool ok = self.GetLine(line, skip_comments);
             if (!ok) {
               return py::none();
             }
             return py::str(qStringToStdString(line));
           },
           py::arg("skip_comments") = true,
           "Read the next line; returns None at end-of-file.")
      .def("get_line_no_filter",
           [](Isis::TextFile &self) -> py::object {
             QString line;
             bool ok = self.GetLineNoFilter(line);
             if (!ok) {
               return py::none();
             }
             return py::str(qStringToStdString(line));
           },
           "Read the next line without comment filtering; returns None at end-of-file.")
      .def("put_line",
           [](Isis::TextFile &self, const std::string &line) {
             self.PutLine(stdStringToQString(line));
           },
           py::arg("line") = "",
           "Write a single line to the file.")
      .def("put_line_comment",
           [](Isis::TextFile &self, const std::string &line) {
             self.PutLineComment(stdStringToQString(line));
           },
           py::arg("line") = "",
           "Write a comment line to the file.")
      .def("get_comment",
           [](Isis::TextFile &self) {
             return qStringToStdString(self.GetComment());
           },
           "Return the current comment string (default '#').")
      .def("get_new_line",
           [](Isis::TextFile &self) {
             return qStringToStdString(self.GetNewLine());
           },
           "Return the current newline string.")
      .def("set_comment",
           [](Isis::TextFile &self, const std::string &comment) {
             self.SetComment(comment.c_str());
           },
           py::arg("comment_string") = "#",
           "Set the comment character/string.")
      .def("set_new_line",
           [](Isis::TextFile &self, const std::string &newline) {
             self.SetNewLine(newline.c_str());
           },
           py::arg("new_line_string") = "\n",
           "Set the newline string.")
      .def("line_count",
           &Isis::TextFile::LineCount,
           py::arg("max_lines") = 0,
           "Return the number of lines in the file.")
      .def("size",
           &Isis::TextFile::Size,
           "Return the size of the file in bytes.")
      .def("__repr__", [](Isis::TextFile &self) {
            return "TextFile(open=" +
                   std::string(self.OpenChk() ? "True" : "False") + ")";
          });

  // Added: 2026-04-10 - GSLUtility singleton wrapper
     py::class_<Isis::GSL::GSLUtility, std::unique_ptr<Isis::GSL::GSLUtility, py::nodelete>>(m, "GSLUtility")
      .def_static("get_instance",
           &Isis::GSL::GSLUtility::getInstance,
           py::return_value_policy::reference,
           "Return the singleton GSLUtility instance, initializing GSL error handling.")
      .def("success",
           [](const Isis::GSL::GSLUtility &self, int gsl_status) {
               return self.success(gsl_status);
           },
           py::arg("gsl_status"),
           "Return True if gsl_status == GSL_SUCCESS (0).")
      .def("status",
           [](const Isis::GSL::GSLUtility &self, int gsl_errno) {
               return qStringToStdString(self.status(gsl_errno));
           },
           py::arg("gsl_errno"),
           "Return the human-readable name of the given GSL error code.")
      .def("__repr__", [](const Isis::GSL::GSLUtility &) {
           return std::string("GSLUtility()");
      });

  // Added: 2026-04-10 - PolygonTools static utility wrapper
     py::class_<PolygonToolsWrapper> polygonTools(m, "PolygonTools");

  polygonTools
      .def(py::init<>(), "Construct a PolygonTools utility object.")
      .def_static("equal",
                  [](double d1, double d2) {
                       return Isis::PolygonTools::Equal(d1, d2);
                  },
                  py::arg("d1"),
                  py::arg("d2"),
                  "Return True if d1 and d2 are equal within floating-point tolerance.")
      .def_static("reduce_precision",
                  [](double num, unsigned int precision) {
                       return Isis::PolygonTools::ReducePrecision(num, precision);
                  },
                  py::arg("num"),
                  py::arg("precision"),
                  "Round num to the given number of significant decimal places.")
      .def_static("decimal_place",
                  [](double num) {
                       return polygonDecimalPlace(num);
                  },
                  py::arg("num"),
                  "Return the position of the decimal point for the given double.")
      .def_static("gml_schema",
                  []() {
                       return qStringToStdString(Isis::PolygonTools::GMLSchema());
                  },
                  "Return the GML schema string for polygons.")
      .def("__repr__", [](const PolygonToolsWrapper &) {
           return std::string("PolygonTools()");
      });

  // Preserve the older module-level helper aliases for compatibility.
  m.def("polygon_equal",
        [](double d1, double d2) {
             return Isis::PolygonTools::Equal(d1, d2);
        },
        py::arg("d1"),
        py::arg("d2"),
        "Return True if d1 and d2 are equal within floating-point tolerance.");
  m.def("polygon_reduce_precision",
        [](double num, unsigned int precision) {
             return Isis::PolygonTools::ReducePrecision(num, precision);
        },
        py::arg("num"),
        py::arg("precision"),
        "Round num to the given number of significant decimal places.");
  m.def("polygon_decimal_place",
        [](double num) {
             return polygonDecimalPlace(num);
        },
        py::arg("num"),
        "Return the position of the decimal point for the given double.");
  m.def("polygon_gml_schema",
        []() { return qStringToStdString(Isis::PolygonTools::GMLSchema()); },
        "Return the GML schema string for polygons.");
}


