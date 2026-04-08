// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS utility classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Column/Column.h
 *   - isis/src/base/objs/LineEquation/LineEquation.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-03-30  Geng Xun added LineEquation bindings and expanded Column utility exposure
 * Purpose: Expose Column, LineEquation and related utility classes to Python via pybind11.
 * Purpose: Expose Column, LineEquation, and related utility classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Column.h"
#include "LineEquation.h"
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
}
