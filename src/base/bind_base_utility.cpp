// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS utility classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Column/Column.h
 *   - isis/src/base/objs/IString/IString.h
 * Source header author(s): not explicitly stated in upstream header
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-03-27
 * Purpose: Expose Column, IString and related utility classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Column.h"
#include "IString.h"
#include "helpers.h"

namespace py = pybind11;

void bind_base_utility(py::module_ &m) {
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
   * @brief Bindings for the Isis::IString class
   * IString extends std::string with ISIS-specific functionality.
   * Note: This class is deprecated in ISIS but still used in legacy code.
   * @see Isis::IString
   * Added: 2026-03-27 - expose IString for backward compatibility
   */
  py::class_<Isis::IString, std::string>(m, "IString")
      // Constructors
      .def(py::init<>(), "Default constructor")
      .def(py::init<const std::string &>(), py::arg("str"), "Construct from std::string")
      .def(py::init<const Isis::IString &>(), py::arg("str"), "Copy constructor")
      .def(py::init<const char *>(), py::arg("str"), "Construct from C string")
      .def(py::init<const int &>(), py::arg("num"), "Construct from integer")
      .def(py::init<const double &, const int>(),
           py::arg("num"), py::arg("precision") = 14,
           "Construct from double with optional precision")
      .def(py::init([](const std::string &qstr) {
        return Isis::IString(stdStringToQString(qstr));
      }), py::arg("str"), "Construct from string (as QString)")

      // String manipulation methods - instance versions
      .def("trim",
           [](Isis::IString &self, const std::string &chars) {
             return self.Trim(chars);
           },
           py::arg("chars"),
           "Remove leading and trailing characters")
      .def("trim_head",
           [](Isis::IString &self, const std::string &chars) {
             return self.TrimHead(chars);
           },
           py::arg("chars"),
           "Remove leading characters")
      .def("trim_tail",
           [](Isis::IString &self, const std::string &chars) {
             return self.TrimTail(chars);
           },
           py::arg("chars"),
           "Remove trailing characters")
      .def("up_case",
           [](Isis::IString &self) {
             return self.UpCase();
           },
           "Convert to uppercase")
      .def("down_case",
           [](Isis::IString &self) {
             return self.DownCase();
           },
           "Convert to lowercase")
      .def("compress",
           [](Isis::IString &self, bool force) {
             return self.Compress(force);
           },
           py::arg("force") = false,
           "Compress whitespace")
      .def("replace",
           py::overload_cast<const std::string &, const std::string &, int>(
               &Isis::IString::Replace),
           py::arg("from"), py::arg("to"), py::arg("max_replace_count") = 20,
           "Replace substring with optional count limit")
      .def("replace",
           py::overload_cast<const std::string &, const std::string &, bool>(
               &Isis::IString::Replace),
           py::arg("from"), py::arg("to"), py::arg("honor_quotes"),
           "Replace substring honoring quotes")
      .def("convert",
           [](Isis::IString &self, const std::string &listofchars, const char &to) {
             return self.Convert(listofchars, to);
           },
           py::arg("list_of_chars"), py::arg("to"),
           "Convert characters in list to target character")
      .def("convert_white_space",
           [](Isis::IString &self) {
             return self.ConvertWhiteSpace();
           },
           "Convert all whitespace to single spaces")
      .def("remove",
           [](Isis::IString &self, const std::string &del) {
             return self.Remove(del);
           },
           py::arg("del"),
           "Remove all occurrences of characters")
      .def("token",
           [](Isis::IString &self, const Isis::IString &separator) {
             return self.Token(separator);
           },
           py::arg("separator"),
           "Extract next token from string")

      // Conversion methods
      .def("to_integer",
           &Isis::IString::ToInteger,
           "Convert string to integer")
      .def("to_big_integer",
           &Isis::IString::ToBigInteger,
           "Convert string to big integer")
      .def("to_double",
           &Isis::IString::ToDouble,
           "Convert string to double")
      .def("to_qt",
           [](const Isis::IString &self) {
             return qStringToStdString(self.ToQt());
           },
           "Convert to QString (returned as std::string)")

      // Static methods
      .def_static("trim_static",
                  &Isis::IString::Trim,
                  py::arg("chars"), py::arg("str"),
                  "Static: Remove leading and trailing characters")
      .def_static("trim_head_static",
                  &Isis::IString::TrimHead,
                  py::arg("chars"), py::arg("str"),
                  "Static: Remove leading characters")
      .def_static("trim_tail_static",
                  &Isis::IString::TrimTail,
                  py::arg("chars"), py::arg("str"),
                  "Static: Remove trailing characters")
      .def_static("up_case_static",
                  &Isis::IString::UpCase,
                  py::arg("str"),
                  "Static: Convert to uppercase")
      .def_static("down_case_static",
                  &Isis::IString::DownCase,
                  py::arg("str"),
                  "Static: Convert to lowercase")
      .def_static("to_integer_static",
                  &Isis::IString::ToInteger,
                  py::arg("str"),
                  "Static: Convert string to integer")
      .def_static("to_big_integer_static",
                  &Isis::IString::ToBigInteger,
                  py::arg("str"),
                  "Static: Convert string to big integer")
      .def_static("to_double_static",
                  &Isis::IString::ToDouble,
                  py::arg("str"),
                  "Static: Convert string to double")
      .def_static("to_qt_static",
                  [](const std::string &str) {
                    return qStringToStdString(Isis::IString::ToQt(str));
                  },
                  py::arg("str"),
                  "Static: Convert to QString (returned as std::string)")
      .def_static("to_std",
                  [](const std::string &str) {
                    return Isis::IString::ToStd(stdStringToQString(str));
                  },
                  py::arg("str"),
                  "Static: Convert QString to std::string")
      .def_static("compress_static",
                  &Isis::IString::Compress,
                  py::arg("str"), py::arg("force") = false,
                  "Static: Compress whitespace")
      .def_static("replace_static",
                  py::overload_cast<const std::string &, const std::string &,
                                    const std::string &, int>(
                      &Isis::IString::Replace),
                  py::arg("str"), py::arg("from"), py::arg("to"),
                  py::arg("max_replacement_count") = 20,
                  "Static: Replace substring with optional count limit")
      .def_static("replace_static_quotes",
                  py::overload_cast<const std::string &, const std::string &,
                                    const std::string &, bool>(
                      &Isis::IString::Replace),
                  py::arg("str"), py::arg("from"), py::arg("to"),
                  py::arg("honor_quotes"),
                  "Static: Replace substring honoring quotes")
      .def_static("convert_static",
                  &Isis::IString::Convert,
                  py::arg("str"), py::arg("list_of_chars"), py::arg("to"),
                  "Static: Convert characters in list to target character")
      .def_static("convert_white_space_static",
                  &Isis::IString::ConvertWhiteSpace,
                  py::arg("str"),
                  "Static: Convert all whitespace to single spaces")
      .def_static("remove_static",
                  &Isis::IString::Remove,
                  py::arg("del"), py::arg("str"),
                  "Static: Remove all occurrences of characters")
      .def_static("split",
                  [](const char separator, const std::string &instr,
                     bool allow_empty_entries) {
                    std::vector<std::string> tokens;
                    Isis::IString::Split(separator, instr, tokens, allow_empty_entries);
                    return tokens;
                  },
                  py::arg("separator"), py::arg("instr"),
                  py::arg("allow_empty_entries") = true,
                  "Static: Split string by separator")
      .def_static("equal",
                  py::overload_cast<const std::string &, const std::string &>(
                      &Isis::IString::Equal),
                  py::arg("str1"), py::arg("str2"),
                  "Static: Compare two strings for equality")

      // Comparison method (instance)
      .def("equal",
           py::overload_cast<const std::string &>(&Isis::IString::Equal, py::const_),
           py::arg("str"),
           "Compare this string with another")

      // Python special methods
      .def("__repr__", [](const Isis::IString &self) {
        return "IString('" + std::string(self) + "')";
      })
      .def("__str__", [](const Isis::IString &self) {
        return std::string(self);
      })
      .def("__int__", [](const Isis::IString &self) {
        return self.ToInteger();
      })
      .def("__float__", [](const Isis::IString &self) {
        return self.ToDouble();
      });

  // Standalone conversion functions
  m.def("to_bool",
        [](const std::string &str) {
          return Isis::toBool(stdStringToQString(str));
        },
        py::arg("str"),
        "Convert QString to bool");
  m.def("to_int",
        [](const std::string &str) {
          return Isis::toInt(stdStringToQString(str));
        },
        py::arg("str"),
        "Convert QString to int");
  m.def("to_big_int",
        [](const std::string &str) {
          return Isis::toBigInt(stdStringToQString(str));
        },
        py::arg("str"),
        "Convert QString to BigInt");
  m.def("to_double",
        [](const std::string &str) {
          return Isis::toDouble(stdStringToQString(str));
        },
        py::arg("str"),
        "Convert QString to double");
  m.def("to_string",
        py::overload_cast<bool>(&Isis::toString),
        py::arg("value"),
        "Convert bool to QString (returned as std::string)");
  m.def("to_string",
        [](char value) {
          return qStringToStdString(Isis::toString(value));
        },
        py::arg("value"),
        "Convert char to QString (returned as std::string)");
  m.def("to_string",
        py::overload_cast<const int &>(&Isis::toString),
        py::arg("value"),
        "Convert int to QString (returned as std::string)");
  m.def("to_string",
        py::overload_cast<const unsigned int &>(&Isis::toString),
        py::arg("value"),
        "Convert unsigned int to QString (returned as std::string)");
  m.def("to_string",
        py::overload_cast<double, int>(&Isis::toString),
        py::arg("value"), py::arg("precision") = 14,
        "Convert double to QString (returned as std::string)");
}
