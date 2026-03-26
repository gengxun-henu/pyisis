// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS image processing filter and utility classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Stretch/Stretch.h
 *   - isis/src/base/objs/GaussianStretch/GaussianStretch.h
 *   - isis/src/base/objs/QuickFilter/QuickFilter.h
 *   - isis/src/base/objs/Kernels/Kernels.h
 *   - isis/src/base/objs/CSVReader/CSVReader.h
 * Binding author: Geng Xun
 * Created: 2026-03-25
 * Purpose: Expose Stretch, GaussianStretch, QuickFilter, Kernels, and CSVReader classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Stretch.h"
#include "GaussianStretch.h"
#include "QuickFilter.h"
#include "Kernels.h"
#include "CSVReader.h"
#include "Pvl.h"
#include "Histogram.h"
#include "helpers.h"

namespace py = pybind11;

void bind_base_filters(py::module_ &m) {
  /**
   * @brief Bindings for the Isis::Stretch class (abstract base)
   * Stretch class provides pixel value remapping for image contrast adjustment.
   * @see Isis::Stretch
   */
  py::class_<Isis::Stretch>(m, "Stretch")
      .def(py::init<>())
      // Mutation/Configuration methods
      .def("add_pair",
           &Isis::Stretch::AddPair,
           py::arg("input"),
           py::arg("output"),
           "Add an input-output pair for stretch mapping")
      .def("set_null",
           &Isis::Stretch::SetNull,
           py::arg("value"),
           "Set the value for NULL special pixels")
      .def("set_lis",
           &Isis::Stretch::SetLis,
           py::arg("value"),
           "Set the value for LIS (Low Instrument Saturation) special pixels")
      .def("set_lrs",
           &Isis::Stretch::SetLrs,
           py::arg("value"),
           "Set the value for LRS (Low Representation Saturation) special pixels")
      .def("set_his",
           &Isis::Stretch::SetHis,
           py::arg("value"),
           "Set the value for HIS (High Instrument Saturation) special pixels")
      .def("set_hrs",
           &Isis::Stretch::SetHrs,
           py::arg("value"),
           "Set the value for HRS (High Representation Saturation) special pixels")
      .def("set_minimum",
           &Isis::Stretch::SetMinimum,
           py::arg("value"),
           "Set the minimum valid input value")
      .def("set_maximum",
           &Isis::Stretch::SetMaximum,
           py::arg("value"),
           "Set the maximum valid input value")
      // Load/Save methods
      .def("load",
           static_cast<void (Isis::Stretch::*)(Isis::Pvl &, QString &)>(&Isis::Stretch::Load),
           py::arg("pvl"),
           py::arg("grp_name"),
           "Load stretch from PVL object")
      .def("save",
           static_cast<void (Isis::Stretch::*)(Isis::Pvl &, QString &)>(&Isis::Stretch::Save),
           py::arg("pvl"),
           py::arg("grp_name"),
           "Save stretch to PVL object")
      .def("load",
           [](Isis::Stretch &self, const std::string &file, const std::string &grp_name) {
             QString qfile = stdStringToQString(file);
             QString qgrp = stdStringToQString(grp_name);
             self.Load(qfile, qgrp);
           },
           py::arg("file"),
           py::arg("grp_name"),
           "Load stretch from file")
      .def("save",
           [](Isis::Stretch &self, const std::string &file, const std::string &grp_name) {
             QString qfile = stdStringToQString(file);
             QString qgrp = stdStringToQString(grp_name);
             self.Save(qfile, qgrp);
           },
           py::arg("file"),
           py::arg("grp_name"),
           "Save stretch to file")
      // Public API methods
      .def("map",
           &Isis::Stretch::Map,
           py::arg("value"),
           "Apply the stretch mapping to a value")
      .def("parse",
           static_cast<void (Isis::Stretch::*)(const QString &)>(&Isis::Stretch::Parse),
           py::arg("pairs"),
           "Parse stretch pairs from a string")
      .def("parse",
           static_cast<void (Isis::Stretch::*)(const QString &, const Isis::Histogram *)>(&Isis::Stretch::Parse),
           py::arg("pairs"),
           py::arg("hist"),
           "Parse stretch pairs from a string with histogram reference")
      .def("text",
           [](const Isis::Stretch &self) {
             return qStringToStdString(self.Text());
           },
           "Get the stretch mapping as a text string")
      .def("pairs",
           &Isis::Stretch::Pairs,
           "Get the number of stretch pairs")
      .def("input",
           &Isis::Stretch::Input,
           py::arg("index"),
           "Get the input value at the specified index")
      .def("output",
           &Isis::Stretch::Output,
           py::arg("index"),
           "Get the output value at the specified index")
      .def("clear_pairs",
           &Isis::Stretch::ClearPairs,
           "Clear all stretch pairs")
      .def("copy_pairs",
           &Isis::Stretch::CopyPairs,
           py::arg("other"),
           "Copy pairs from another Stretch object")
      .def("__repr__", [](const Isis::Stretch &self) {
        return "Stretch(pairs=" + std::to_string(self.Pairs()) + ")";
      });

  /**
   * @brief Bindings for the Isis::GaussianStretch class
   * GaussianStretch applies a Gaussian-based stretch to pixel values.
   * Inherits from Stretch but bound independently due to pybind11 limitations.
   * @see Isis::GaussianStretch
   */
  py::class_<Isis::GaussianStretch>(m, "GaussianStretch")
      .def(py::init<Isis::Histogram &, const double, const double>(),
           py::arg("histogram"),
           py::arg("mean") = 0.0,
           py::arg("standard_deviation") = 1.0,
           "Construct a GaussianStretch with a histogram and optional mean/standard deviation")
      .def("map",
           &Isis::GaussianStretch::Map,
           py::arg("value"),
           "Apply the Gaussian stretch mapping to a value")
      .def("__repr__", []() {
        return "GaussianStretch()";
      });

  /**
   * @brief Bindings for the Isis::QuickFilter class
   * QuickFilter provides efficient windowed statistics computation.
   * @see Isis::QuickFilter
   */
  py::class_<Isis::QuickFilter>(m, "QuickFilter")
      .def(py::init<int, int, int>(),
           py::arg("ns"),
           py::arg("width"),
           py::arg("height"),
           "Construct a QuickFilter with the specified number of samples, width, and height")
      // Public API methods
      .def("average",
           &Isis::QuickFilter::Average,
           py::arg("index"),
           "Get the average at the specified sample index")
      .def("variance",
           &Isis::QuickFilter::Variance,
           py::arg("index"),
           "Get the variance at the specified sample index")
      .def("count",
           &Isis::QuickFilter::Count,
           py::arg("index"),
           "Get the valid pixel count at the specified sample index")
      // Query methods
      .def("width",
           &Isis::QuickFilter::Width,
           "Get the filter window width")
      .def("half_width",
           &Isis::QuickFilter::HalfWidth,
           "Get half of the filter window width")
      .def("height",
           &Isis::QuickFilter::Height,
           "Get the filter window height")
      .def("half_height",
           &Isis::QuickFilter::HalfHeight,
           "Get half of the filter window height")
      .def("samples",
           &Isis::QuickFilter::Samples,
           "Get the number of samples")
      .def("low",
           &Isis::QuickFilter::Low,
           "Get the low valid data range")
      .def("high",
           &Isis::QuickFilter::High,
           "Get the high valid data range")
      .def("minimum_pixels",
           &Isis::QuickFilter::MinimumPixels,
           "Get the minimum number of valid pixels required")
      // Mutation methods
      .def("add_line",
           [](Isis::QuickFilter &self, const std::vector<double> &buffer) {
             self.AddLine(buffer.data());
           },
           py::arg("buffer"),
           "Add a line of data to the filter")
      .def("remove_line",
           [](Isis::QuickFilter &self, const std::vector<double> &buffer) {
             self.RemoveLine(buffer.data());
           },
           py::arg("buffer"),
           "Remove a line of data from the filter")
      .def("reset",
           &Isis::QuickFilter::Reset,
           "Reset the filter state")
      .def("set_min_max",
           &Isis::QuickFilter::SetMinMax,
           py::arg("minimum"),
           py::arg("maximum"),
           "Set the minimum and maximum valid data range")
      .def("set_minimum_pixels",
           &Isis::QuickFilter::SetMinimumPixels,
           py::arg("minimum_valid"),
           "Set the minimum number of valid pixels required")
      .def("__repr__", [](const Isis::QuickFilter &self) {
        return "QuickFilter(width=" + std::to_string(self.Width()) +
               ", height=" + std::to_string(self.Height()) +
               ", samples=" + std::to_string(self.Samples()) + ")";
      });

  /**
   * @brief Bindings for the Isis::Kernels class
   * Kernels manages SPICE kernel files for spacecraft and instrument positioning.
   * @see Isis::Kernels
   */
  py::class_<Isis::Kernels>(m, "Kernels")
      .def(py::init<>())
      // Query methods
      .def("size",
           &Isis::Kernels::size,
           "Get the number of kernel files")
      .def("missing",
           &Isis::Kernels::Missing,
           "Get the number of missing kernel files")
      .def("is_managed",
           &Isis::Kernels::IsManaged,
           "Check if kernels are managed")
      .def("camera_version",
           &Isis::Kernels::CameraVersion,
           "Get the camera version")
      // Initialization and configuration
      .def("init",
           &Isis::Kernels::Init,
           py::arg("pvl"),
           "Initialize kernels from PVL object")
      .def("add",
           [](Isis::Kernels &self, const std::string &kfile) {
             return self.Add(stdStringToQString(kfile));
           },
           py::arg("kfile"),
           "Add a kernel file")
      .def("clear",
           &Isis::Kernels::Clear,
           "Clear all kernel files")
      .def("discover",
           &Isis::Kernels::Discover,
           "Discover kernel files")
      .def("manage",
           &Isis::Kernels::Manage,
           "Enable kernel management")
      .def("un_manage",
           &Isis::Kernels::UnManage,
           "Disable kernel management")
      .def("initialize_naif_kernel_pool",
           &Isis::Kernels::InitializeNaifKernelPool,
           "Initialize the NAIF kernel pool")
      // Load/Unload methods
      .def("load",
           static_cast<int (Isis::Kernels::*)(const QString &)>(&Isis::Kernels::Load),
           py::arg("ktype"),
           "Load kernels of a specific type")
      .def("load",
           static_cast<int (Isis::Kernels::*)()>(&Isis::Kernels::Load),
           "Load all kernels")
      .def("un_load",
           [](Isis::Kernels &self, const std::string &ktype) {
             return self.UnLoad(stdStringToQString(ktype));
           },
           py::arg("ktype"),
           "Unload kernels of a specific type")
      .def("un_load",
           static_cast<int (Isis::Kernels::*)()>(&Isis::Kernels::UnLoad),
           "Unload all kernels")
      .def("update_load_status",
           &Isis::Kernels::UpdateLoadStatus,
           "Update the load status of kernels")
      .def("merge",
           &Isis::Kernels::Merge,
           py::arg("other"),
           "Merge kernels from another Kernels object")
      // Query kernel lists
      .def("get_kernel_types",
           [](const Isis::Kernels &self) {
             QStringList types = self.getKernelTypes();
             std::vector<std::string> result;
             for (const QString &type : types) {
               result.push_back(qStringToStdString(type));
             }
             return result;
           },
           "Get a list of kernel types")
      .def("get_kernel_list",
           [](const Isis::Kernels &self, const std::string &ktype) {
             QStringList list = self.getKernelList(stdStringToQString(ktype));
             std::vector<std::string> result;
             for (const QString &item : list) {
               result.push_back(qStringToStdString(item));
             }
             return result;
           },
           py::arg("ktype") = "",
           "Get a list of kernel files for a specific type")
      .def("get_loaded_list",
           [](const Isis::Kernels &self, const std::string &ktypes) {
             QStringList list = self.getLoadedList(stdStringToQString(ktypes));
             std::vector<std::string> result;
             for (const QString &item : list) {
               result.push_back(qStringToStdString(item));
             }
             return result;
           },
           py::arg("ktypes") = "",
           "Get a list of loaded kernel files")
      .def("get_missing_list",
           [](const Isis::Kernels &self) {
             QStringList list = self.getMissingList();
             std::vector<std::string> result;
             for (const QString &item : list) {
               result.push_back(qStringToStdString(item));
             }
             return result;
           },
           "Get a list of missing kernel files")
      .def("__repr__", [](const Isis::Kernels &self) {
        return "Kernels(size=" + std::to_string(self.size()) +
               ", missing=" + std::to_string(self.Missing()) + ")";
      });

  /**
   * @brief Bindings for the Isis::CSVReader class
   * CSVReader provides CSV file parsing and table data access.
   * @see Isis::CSVReader
   */
  py::class_<Isis::CSVReader>(m, "CSVReader")
      .def(py::init<>())
      // Query methods
      .def("size",
           &Isis::CSVReader::size,
           "Get the total number of lines")
      .def("rows",
           &Isis::CSVReader::rows,
           "Get the number of data rows (excluding header and skipped lines)")
      .def("columns",
           static_cast<int (Isis::CSVReader::*)() const>(&Isis::CSVReader::columns),
           "Get the number of columns")
      .def("have_header",
           &Isis::CSVReader::haveHeader,
           "Check if the CSV has a header row")
      .def("get_skip",
           &Isis::CSVReader::getSkip,
           "Get the number of lines to skip at the beginning")
      .def("get_delimiter",
           &Isis::CSVReader::getDelimiter,
           "Get the field delimiter character")
      .def("keep_empty_parts",
           &Isis::CSVReader::keepEmptyParts,
           "Check if empty fields are kept")
      // Configuration methods
      .def("set_comment",
           &Isis::CSVReader::setComment,
           py::arg("ignore") = true,
           "Set whether to ignore comment lines")
      .def("set_skip",
           &Isis::CSVReader::setSkip,
           py::arg("nskip"),
           "Set the number of lines to skip at the beginning")
      .def("set_header",
           &Isis::CSVReader::setHeader,
           py::arg("got_it") = true,
           "Set whether the first row is a header")
      .def("set_delimiter",
           &Isis::CSVReader::setDelimiter,
           py::arg("delimiter"),
           "Set the field delimiter character")
      .def("set_keep_empty_parts",
           &Isis::CSVReader::setKeepEmptyParts,
           "Keep empty fields when parsing")
      .def("set_skip_empty_parts",
           &Isis::CSVReader::setSkipEmptyParts,
           "Skip empty fields when parsing")
      // Read/Write methods
      .def("read",
           [](Isis::CSVReader &self, const std::string &fname) {
             self.read(stdStringToQString(fname));
           },
           py::arg("fname"),
           "Read a CSV file")
      // Data access methods
      .def("get_header",
           [](const Isis::CSVReader &self) {
             Isis::CSVReader::CSVAxis header = self.getHeader();
             std::vector<std::string> result;
             for (int i = 0; i < header.dim(); i++) {
               result.push_back(qStringToStdString(header[i]));
             }
             return result;
           },
           "Get the header row")
      .def("get_row",
           [](const Isis::CSVReader &self, int index) {
             Isis::CSVReader::CSVAxis row = self.getRow(index);
             std::vector<std::string> result;
             for (int i = 0; i < row.dim(); i++) {
               result.push_back(qStringToStdString(row[i]));
             }
             return result;
           },
           py::arg("index"),
           "Get a data row by index")
      .def("get_column",
           [](const Isis::CSVReader &self, int index) {
             Isis::CSVReader::CSVAxis col = self.getColumn(index);
             std::vector<std::string> result;
             for (int i = 0; i < col.dim(); i++) {
               result.push_back(qStringToStdString(col[i]));
             }
             return result;
           },
           py::arg("index"),
           "Get a column by index")
      .def("get_column",
           [](const Isis::CSVReader &self, const std::string &hname) {
             Isis::CSVReader::CSVAxis col = self.getColumn(stdStringToQString(hname));
             std::vector<std::string> result;
             for (int i = 0; i < col.dim(); i++) {
               result.push_back(qStringToStdString(col[i]));
             }
             return result;
           },
           py::arg("hname"),
           "Get a column by header name")
      .def("clear",
           &Isis::CSVReader::clear,
           "Clear all data")
      .def("__repr__", [](const Isis::CSVReader &self) {
        return "CSVReader(rows=" + std::to_string(self.rows()) +
               ", columns=" + std::to_string(self.columns()) + ")";
      });
}
