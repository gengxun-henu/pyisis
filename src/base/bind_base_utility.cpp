// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS utility classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Column/Column.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Purpose: Expose Column and related utility classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Column.h"
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
}
