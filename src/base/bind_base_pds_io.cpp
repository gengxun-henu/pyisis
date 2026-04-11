// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/base/objs/ImportPdsTable/ImportPdsTable.h
// - reference/upstream_isis/src/base/objs/ExportPdsTable/ExportPdsTable.h
// Source classes: ImportPdsTable, ExportPdsTable
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-10
// Updated: 2026-04-10  Geng Xun initial import of ImportPdsTable and ExportPdsTable bindings
// Purpose: Expose Isis::ImportPdsTable and Isis::ExportPdsTable to Python

#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "ExportPdsTable.h"
#include "ImportPdsTable.h"
#include "PvlObject.h"
#include "Table.h"

namespace py = pybind11;

static QString toQ(const std::string &s) { return QString::fromStdString(s); }

void bind_base_pds_io(py::module_ &m) {
  // ImportPdsTable — reads a PDS table file (ASCII or BINARY) and converts it
  // to an ISIS Table object.
  py::class_<Isis::ImportPdsTable>(m, "ImportPdsTable")
      .def(py::init<>(),
           "Construct an ImportPdsTable with no label loaded (call load() before use).")
      .def(py::init([](const std::string &pds_lab_file,
                       const std::string &pds_tab_file,
                       const std::string &pds_table_name) {
             return new Isis::ImportPdsTable(
                 toQ(pds_lab_file),
                 toQ(pds_tab_file),
                 toQ(pds_table_name));
           }),
           py::arg("pds_lab_file"),
           py::arg("pds_tab_file") = "",
           py::arg("pds_table_name") = "TABLE",
           "Construct an ImportPdsTable by loading the given PDS label file.\n\n"
           "Parameters\n"
           "----------\n"
           "pds_lab_file : str\n"
           "    Path to the PDS label file.\n"
           "pds_tab_file : str, optional\n"
           "    Path to the PDS table data file (if detached from the label).\n"
           "pds_table_name : str, optional\n"
           "    Name of the table to read (default 'TABLE').")
      .def("load",
           [](Isis::ImportPdsTable &self,
              const std::string &pds_lab_file,
              const std::string &pds_tab_file,
              const std::string &pds_table_name) {
             self.load(toQ(pds_lab_file),
                       toQ(pds_tab_file),
                       toQ(pds_table_name));
           },
           py::arg("pds_lab_file"),
           py::arg("pds_tab_file") = "",
           py::arg("pds_table_name") = "TABLE",
           "Load the PDS label and table data.")
      .def("name",
           [](const Isis::ImportPdsTable &self) {
             return self.name().toStdString();
           },
           "Return the name of the currently loaded PDS table.")
      .def("set_name",
           [](Isis::ImportPdsTable &self, const std::string &name) {
             self.setName(toQ(name));
           },
           py::arg("name") = "TABLE",
           "Set the name of the PDS table to load.")
      .def("columns",
           &Isis::ImportPdsTable::columns,
           "Return the number of columns in the table.")
      .def("rows",
           &Isis::ImportPdsTable::rows,
           "Return the number of rows in the table.")
      .def("has_column",
           [](const Isis::ImportPdsTable &self, const std::string &col_name) {
             return self.hasColumn(toQ(col_name));
           },
           py::arg("col_name"),
           "Return True if the table contains a column with the given name.")
      .def("get_column_name",
           [](const Isis::ImportPdsTable &self,
              unsigned int index,
              bool formatted) {
             return self.getColumnName(index, formatted).toStdString();
           },
           py::arg("index") = 0,
           py::arg("formatted") = true,
           "Return the name of the column at the given index.")
      .def("get_column_names",
           [](const Isis::ImportPdsTable &self, bool formatted) {
             QStringList names = self.getColumnNames(formatted);
             std::vector<std::string> result;
             result.reserve(names.size());
             for (const QString &n : names) {
               result.push_back(n.toStdString());
             }
             return result;
           },
           py::arg("formatted") = true,
           "Return a list of all column names in the table.")
      // Added: 2026-04-11 - expose getFormattedName
      .def("get_formatted_name",
           [](const Isis::ImportPdsTable &self, const std::string &col_name) {
             return self.getFormattedName(toQ(col_name)).toStdString();
           },
           py::arg("col_name"),
           "Return the formatted version of the given column name.")
      .def("get_type",
           [](const Isis::ImportPdsTable &self, const std::string &col_name) {
             return self.getType(toQ(col_name)).toStdString();
           },
           py::arg("col_name"),
           "Return the PDS data type string for the given column.")
      .def("set_type",
           [](Isis::ImportPdsTable &self,
              const std::string &col_name,
              const std::string &data_type) {
             return self.setType(toQ(col_name), toQ(data_type));
           },
           py::arg("col_name"),
           py::arg("data_type"),
           "Override the data type of the given column.")
      .def("import_table",
           [](Isis::ImportPdsTable &self, const std::string &isis_table_name) {
             return self.importTable(toQ(isis_table_name));
           },
           py::arg("isis_table_name"),
           "Import the PDS table as an ISIS Table with the given name.")
      .def("import_table",
           [](Isis::ImportPdsTable &self,
              const std::string &col_names,
              const std::string &isis_table_name) {
             return self.importTable(toQ(col_names), toQ(isis_table_name));
           },
           py::arg("col_names"),
           py::arg("isis_table_name"),
           "Import selected columns (comma-separated) as an ISIS Table.")
      .def("__repr__", [](const Isis::ImportPdsTable &self) {
        return "<ImportPdsTable name=" + self.name().toStdString() +
               " cols=" + std::to_string(self.columns()) +
               " rows=" + std::to_string(self.rows()) + ">";
      });

  // ExportPdsTable — exports an ISIS Table as a binary PDS table.
  py::class_<Isis::ExportPdsTable>(m, "ExportPdsTable")
      .def(py::init<Isis::Table>(),
           py::arg("isis_table"),
           "Construct an ExportPdsTable from an ISIS Table object.")
      .def("format_pds_table_name",
           [](Isis::ExportPdsTable &self) {
             return self.formatPdsTableName().toStdString();
           },
           "Return the formatted PDS table name derived from the ISIS table name.")
      .def_static("format_pds_table_name_from",
                  [](const std::string &isis_table_name) {
                    return Isis::ExportPdsTable::formatPdsTableName(
                               toQ(isis_table_name)).toStdString();
                  },
                  py::arg("isis_table_name"),
                  "Return the formatted PDS table name for the given ISIS table name.")
      .def("__repr__", [](const Isis::ExportPdsTable &) {
        return "<ExportPdsTable>";
      });
}
