// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added high-level cube I/O process, import, export, progress, and JP2 helper bindings
// Purpose: pybind11 bindings for ISIS high-level cube I/O workflows including Process variants, import/export helpers, and JP2 utilities

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <cfloat>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CubeAttribute.h"
#include "ExportDescription.h"
#include "FileName.h"
#include "JP2Decoder.h"
#include "JP2Encoder.h"
#include "JP2Error.h"
#include "Process.h"
#include "ProcessByBoxcar.h"
#include "ProcessByBrick.h"
#include "ProcessByLine.h"
#include "ProcessByQuickFilter.h"
#include "ProcessBySample.h"
#include "ProcessBySpectra.h"
#include "ProcessByTile.h"
#include "ProcessImport.h"
#include "ProcessImportFits.h"
#include "ProcessImportPds.h"
#include "ProcessImportVicar.h"
#include "Progress.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
std::vector<Isis::Statistics> copyStatisticsVector(const std::vector<Isis::Statistics *> &stats) {
  std::vector<Isis::Statistics> result;
  result.reserve(stats.size());
  for (const Isis::Statistics *stat : stats) {
    if (stat) {
   result.emplace_back(*stat);
    }
  }
  return result;
}

Isis::CubeAttributeInput makeCubeAttributeInput(const py::object &attributes) {
  Isis::CubeAttributeInput result;

  if (attributes.is_none()) {
    return result;
  }

  if (py::isinstance<py::str>(attributes)) {
    result.setAttributes(stdStringToQString(attributes.cast<std::string>()));
    return result;
  }

  if (py::isinstance<py::sequence>(attributes)) {
    std::vector<QString> bands;
    for (const py::handle &item : attributes.cast<py::sequence>()) {
      bands.push_back(stdStringToQString(py::str(item).cast<std::string>()));
    }
    result.setBands(bands);
    return result;
  }

  throw py::type_error("attributes must be None, a band string like '+1', or a sequence of band identifiers");
}

std::vector<std::string> cubeAttributeInputBandsToStrings(const Isis::CubeAttributeInput &attributes) {
  std::vector<std::string> result;
  for (const QString &band : attributes.bands()) {
    result.push_back(qStringToStdString(band));
  }
  return result;
}
}  // namespace

void bind_high_level_cube_io(py::module_ &m) {
  py::module_ high_level =
   m.def_submodule("high_level_cube_io", "High Level Cube I/O bindings under active development.");
  high_level.doc() = "High Level Cube I/O bindings under active development.";

  m.attr("SizeMatch") = py::int_(Isis::SizeMatch);
  m.attr("SpatialMatch") = py::int_(Isis::SpatialMatch);
  m.attr("OneBand") = py::int_(Isis::OneBand);
  m.attr("BandMatchOrOne") = py::int_(Isis::BandMatchOrOne);
  m.attr("ReadWrite") = py::int_(Isis::ReadWrite);
  m.attr("AllMatchOrOne") = py::int_(Isis::AllMatchOrOne);

  py::class_<Isis::Progress>(m, "Progress")
   .def(py::init<>())
   .def("set_text",
     [](Isis::Progress &self, const std::string &text) {
       self.SetText(stdStringToQString(text));
     },
     py::arg("text"))
   .def("text", [](const Isis::Progress &self) { return qStringToStdString(self.Text()); })
   .def("set_maximum_steps", &Isis::Progress::SetMaximumSteps, py::arg("steps"))
   .def("add_steps", &Isis::Progress::AddSteps, py::arg("steps"))
   .def("check_status", &Isis::Progress::CheckStatus)
   .def("disable_automatic_display", &Isis::Progress::DisableAutomaticDisplay)
   .def("maximum_steps", &Isis::Progress::MaximumSteps)
   .def("current_step", &Isis::Progress::CurrentStep);

  py::class_<Isis::Process>(m, "Process")
   .def(py::init<>())
   .def("set_input_cube",
           [](Isis::Process &self, const std::string &parameter, int requirements) {
             return self.SetInputCube(stdStringToQString(parameter), requirements);
           },
     py::arg("parameter"),
     py::arg("requirements") = 0,
     py::return_value_policy::reference_internal)
   .def("set_input_cube",
     [](Isis::Process &self, Isis::Cube &cube, int requirements) {
       self.SetInputCube(&cube, requirements);
     },
     py::arg("cube"),
     py::arg("requirements") = 0)
   .def("set_output_cube",
           [](Isis::Process &self, const std::string &parameter) {
             return self.SetOutputCube(stdStringToQString(parameter));
           },
     py::arg("parameter"),
     py::return_value_policy::reference_internal)
   .def("set_output_cube",
           [](Isis::Process &self, const std::string &parameter, int samples, int lines, int bands) {
             return self.SetOutputCube(stdStringToQString(parameter), samples, lines, bands);
           },
     py::arg("parameter"),
     py::arg("samples"),
     py::arg("lines"),
     py::arg("bands") = 1,
     py::return_value_policy::reference_internal)
   .def("set_output_cube_stretch",
           [](Isis::Process &self, const std::string &parameter) {
             return self.SetOutputCubeStretch(stdStringToQString(parameter), nullptr);
           },
     py::arg("parameter"),
     py::return_value_policy::reference_internal)
   .def("set_output_cube_stretch",
           [](Isis::Process &self, const std::string &parameter, int samples, int lines, int bands) {
             return self.SetOutputCubeStretch(stdStringToQString(parameter), samples, lines, bands, nullptr);
           },
     py::arg("parameter"),
     py::arg("samples"),
     py::arg("lines"),
     py::arg("bands") = 1,
     py::return_value_policy::reference_internal)
   .def("add_input_cube",
     [](Isis::Process &self, Isis::Cube &cube, bool owned) {
       self.AddInputCube(&cube, owned);
     },
     py::arg("cube"),
     py::arg("owned") = true)
   .def("add_output_cube",
     [](Isis::Process &self, Isis::Cube &cube, bool owned) {
       self.AddOutputCube(&cube, owned);
     },
     py::arg("cube"),
     py::arg("owned") = true)
   .def("check_requirements",
     [](Isis::Process &self, const Isis::Cube &cube, int requirements) {
       self.CheckRequirements(&cube, requirements);
     },
     py::arg("cube"),
     py::arg("requirements"))
   .def("clear_cubes", &Isis::Process::ClearCubes)
   .def("clear_input_cubes", &Isis::Process::ClearInputCubes)
   .def("clear_output_cubes", &Isis::Process::ClearOutputCubes)
   .def("propagate_labels",
     static_cast<void (Isis::Process::*)(const bool)>(&Isis::Process::PropagateLabels),
     py::arg("propagate"))
   .def("propagate_labels_from",
     [](Isis::Process &self, const std::string &cube_path) {
       self.PropagateLabels(stdStringToQString(cube_path));
     },
     py::arg("cube_path"))
   .def("propagate_tables",
     static_cast<void (Isis::Process::*)(const bool)>(&Isis::Process::PropagateTables),
     py::arg("propagate"))
   .def("propagate_tables_from",
     [](Isis::Process &self, const std::string &from_name, const std::vector<std::string> &table_names) {
       QList<QString> names;
       for (const auto &name : table_names) {
      names.append(stdStringToQString(name));
       }
       self.PropagateTables(stdStringToQString(from_name), names);
     },
     py::arg("from_name"),
     py::arg("table_names") = std::vector<std::string>{})
   .def("propagate_polygons", &Isis::Process::PropagatePolygons, py::arg("propagate"))
   .def("propagate_history", &Isis::Process::PropagateHistory, py::arg("propagate"))
   .def("propagate_original_label", &Isis::Process::PropagateOriginalLabel, py::arg("propagate"))
   .def("progress",
     &Isis::Process::Progress,
     py::return_value_policy::reference_internal)
   .def("mission_data",
     [](Isis::Process &self, const std::string &mission, const std::string &file, bool highest_version) {
       return qStringToStdString(self.MissionData(stdStringToQString(mission), stdStringToQString(file), highest_version));
     },
     py::arg("mission"),
     py::arg("file"),
     py::arg("highest_version") = false)
   .def("write_history", &Isis::Process::WriteHistory, py::arg("cube"))
   .def("calculate_statistics", &Isis::Process::CalculateStatistics)
   .def("band_statistics",
     [](Isis::Process &self, unsigned int index) {
       return copyStatisticsVector(self.BandStatistics(index));
     },
     py::arg("index"))
   .def("cube_statistics",
     [](Isis::Process &self, unsigned int index) {
       return Isis::Statistics(*self.CubeStatistics(index));
     },
     py::arg("index"))
   .def("end_process", &Isis::Process::EndProcess)
   .def("finalize", &Isis::Process::Finalize);

  py::class_<Isis::ProcessByBrick, Isis::Process> process_by_brick(m, "ProcessByBrick");

  py::enum_<Isis::ProcessByBrick::IOCubes>(process_by_brick, "IOCubes")
   .value("InPlace", Isis::ProcessByBrick::IOCubes::InPlace)
   .value("InputOutput", Isis::ProcessByBrick::IOCubes::InputOutput)
   .value("InputOutputList", Isis::ProcessByBrick::IOCubes::InputOutputList);

  py::enum_<Isis::ProcessByBrick::ProcessingDirection>(process_by_brick, "ProcessingDirection")
   .value("LinesFirst", Isis::ProcessByBrick::ProcessingDirection::LinesFirst)
   .value("BandsFirst", Isis::ProcessByBrick::ProcessingDirection::BandsFirst);

  process_by_brick
   .def(py::init<>())
   .def("set_input_cube",
           [](Isis::ProcessByBrick &self, const std::string &parameter, int requirements) {
             return self.SetInputCube(stdStringToQString(parameter), requirements);
           },
     py::arg("parameter"),
     py::arg("requirements") = 0,
     py::return_value_policy::reference_internal)
   .def("set_bricks", &Isis::ProcessByBrick::SetBricks, py::arg("cube_set"))
   .def("verify_cubes", &Isis::ProcessByBrick::VerifyCubes, py::arg("cube_set"))
   .def("set_brick_size", &Isis::ProcessByBrick::SetBrickSize,
     py::arg("samples"), py::arg("lines"), py::arg("bands"))
   .def("set_input_brick_size",
     static_cast<void (Isis::ProcessByBrick::*)(int, int, int)>(&Isis::ProcessByBrick::SetInputBrickSize),
     py::arg("samples"), py::arg("lines"), py::arg("bands"))
   .def("set_input_brick_size_for_cube",
     static_cast<void (Isis::ProcessByBrick::*)(int, int, int, int)>(&Isis::ProcessByBrick::SetInputBrickSize),
     py::arg("samples"), py::arg("lines"), py::arg("bands"), py::arg("cube_index"))
   .def("set_output_brick_size",
     static_cast<void (Isis::ProcessByBrick::*)(int, int, int)>(&Isis::ProcessByBrick::SetOutputBrickSize),
     py::arg("samples"), py::arg("lines"), py::arg("bands"))
   .def("set_output_brick_size_for_cube",
     static_cast<void (Isis::ProcessByBrick::*)(int, int, int, int)>(&Isis::ProcessByBrick::SetOutputBrickSize),
     py::arg("samples"), py::arg("lines"), py::arg("bands"), py::arg("cube_index"))
   .def("set_processing_direction", &Isis::ProcessByBrick::SetProcessingDirection, py::arg("direction"))
   .def("get_processing_direction", &Isis::ProcessByBrick::GetProcessingDirection)
   .def("set_output_requirements", &Isis::ProcessByBrick::SetOutputRequirements, py::arg("requirements"))
   .def("set_wrap", &Isis::ProcessByBrick::SetWrap, py::arg("wrap"))
   .def("wraps", &Isis::ProcessByBrick::Wraps)
   .def("end_process", &Isis::ProcessByBrick::EndProcess)
   .def("finalize", &Isis::ProcessByBrick::Finalize);

  py::class_<Isis::ProcessByLine, Isis::ProcessByBrick>(m, "ProcessByLine")
   .def(py::init<>())
   .def("set_input_cube",
           [](Isis::ProcessByLine &self, const std::string &parameter, int requirements) {
             return self.SetInputCube(stdStringToQString(parameter), requirements);
           },
     py::arg("parameter"),
     py::arg("requirements") = 0,
     py::return_value_policy::reference_internal)
   .def("set_bricks", &Isis::ProcessByLine::SetBricks, py::arg("cube_set"));

  py::class_<Isis::ProcessBySample, Isis::ProcessByBrick>(m, "ProcessBySample")
   .def(py::init<>())
   .def("set_input_cube",
           [](Isis::ProcessBySample &self, const std::string &parameter, int requirements) {
             return self.SetInputCube(stdStringToQString(parameter), requirements);
           },
     py::arg("parameter"),
     py::arg("requirements") = 0,
     py::return_value_policy::reference_internal);

  py::class_<Isis::ProcessBySpectra, Isis::ProcessByBrick> process_by_spectra(m, "ProcessBySpectra");
  process_by_spectra
    .attr("PerPixel") = py::int_(0);
  process_by_spectra
    .attr("ByLine") = py::int_(1);
  process_by_spectra
    .attr("BySample") = py::int_(2);
  process_by_spectra
    .def(py::init<const int>(), py::arg("type") = 0)
   .def("set_input_cube",
       [](Isis::ProcessBySpectra &self, const std::string &parameter, int requirements) {
       return self.SetInputCube(stdStringToQString(parameter), requirements);
       },
     py::arg("parameter"),
     py::arg("requirements") = 0,
     py::return_value_policy::reference_internal)
   .def("set_type", &Isis::ProcessBySpectra::SetType, py::arg("type"))
   .def("type", &Isis::ProcessBySpectra::Type);

  py::class_<Isis::ProcessByTile, Isis::ProcessByBrick>(m, "ProcessByTile")
   .def(py::init<>())
   .def("set_tile_size", &Isis::ProcessByTile::SetTileSize, py::arg("samples"), py::arg("lines"))
   .def("end_process", &Isis::ProcessByTile::EndProcess)
   .def("finalize", &Isis::ProcessByTile::Finalize);

  py::class_<Isis::ProcessByBoxcar, Isis::Process>(m, "ProcessByBoxcar")
    .def(py::init<>())
    .def("set_boxcar_size", &Isis::ProcessByBoxcar::SetBoxcarSize, py::arg("samples"), py::arg("lines"))
    .def("end_process", &Isis::ProcessByBoxcar::EndProcess)
    .def("finalize", &Isis::ProcessByBoxcar::Finalize);

  py::class_<Isis::ProcessByQuickFilter, Isis::Process>(m, "ProcessByQuickFilter")
    .def(py::init<>())
    .def("set_filter_parameters", &Isis::ProcessByQuickFilter::SetFilterParameters,
       py::arg("samples"), py::arg("lines"), py::arg("low") = -DBL_MAX,
       py::arg("high") = DBL_MAX, py::arg("minimum") = 0);

  py::class_<Isis::ProcessImport, Isis::Process> process_import(m, "ProcessImport");

  py::enum_<Isis::ProcessImport::VAXDataType>(process_import, "VAXDataType")
   .value("VAX_REAL", Isis::ProcessImport::VAX_REAL)
   .value("VAX_INT", Isis::ProcessImport::VAX_INT);

  py::enum_<Isis::ProcessImport::VAXSpecialPixel>(process_import, "VAXSpecialPixel")
   .value("VAX_MIN4", Isis::ProcessImport::VAX_MIN4)
   .value("VAX_NULL4", Isis::ProcessImport::VAX_NULL4)
   .value("VAX_LRS4", Isis::ProcessImport::VAX_LRS4)
   .value("VAX_LIS4", Isis::ProcessImport::VAX_LIS4)
   .value("VAX_HIS4", Isis::ProcessImport::VAX_HIS4)
   .value("VAX_HRS4", Isis::ProcessImport::VAX_HRS4);

  py::enum_<Isis::ProcessImport::Interleave>(process_import, "Interleave")
   .value("InterleaveUndefined", Isis::ProcessImport::InterleaveUndefined)
   .value("JP2", Isis::ProcessImport::JP2)
   .value("BSQ", Isis::ProcessImport::BSQ)
   .value("BIL", Isis::ProcessImport::BIL)
   .value("BIP", Isis::ProcessImport::BIP);

  process_import
   .def(py::init<>())
   .def("set_input_file",
     [](Isis::ProcessImport &self, const std::string &file) {
       self.SetInputFile(stdStringToQString(file));
     },
     py::arg("file"))
   .def("input_file", [](Isis::ProcessImport &self) { return qStringToStdString(self.InputFile()); })
   .def("set_output_cube",
           [](Isis::ProcessImport &self, const std::string &parameter) {
             return self.SetOutputCube(stdStringToQString(parameter));
           },
     py::arg("parameter"),
     py::return_value_policy::reference_internal)
   .def("set_pixel_type", &Isis::ProcessImport::SetPixelType, py::arg("pixel_type"))
   .def("pixel_type", &Isis::ProcessImport::PixelType)
   .def("set_dimensions", &Isis::ProcessImport::SetDimensions,
     py::arg("samples"), py::arg("lines"), py::arg("bands"))
   .def("samples", &Isis::ProcessImport::Samples)
   .def("lines", &Isis::ProcessImport::Lines)
   .def("bands", &Isis::ProcessImport::Bands)
   .def("set_byte_order", &Isis::ProcessImport::SetByteOrder, py::arg("byte_order"))
   .def("byte_order", &Isis::ProcessImport::ByteOrder)
   .def("set_suffix_offset", &Isis::ProcessImport::SetSuffixOffset,
     py::arg("samples"), py::arg("lines"), py::arg("core_bands"), py::arg("item_bytes"))
   .def("set_suffix_pixel_type", &Isis::ProcessImport::SetSuffixPixelType, py::arg("pixel_type"))
   .def("set_vax_convert", &Isis::ProcessImport::SetVAXConvert, py::arg("vax_convert"))
   .def("set_file_header_bytes", &Isis::ProcessImport::SetFileHeaderBytes, py::arg("bytes"))
   .def("set_file_trailer_bytes", &Isis::ProcessImport::SetFileTrailerBytes, py::arg("bytes"))
   .def("set_data_header_bytes", &Isis::ProcessImport::SetDataHeaderBytes, py::arg("bytes"))
   .def("set_data_trailer_bytes", &Isis::ProcessImport::SetDataTrailerBytes, py::arg("bytes"))
   .def("set_data_prefix_bytes", &Isis::ProcessImport::SetDataPrefixBytes, py::arg("bytes"))
   .def("set_data_suffix_bytes", &Isis::ProcessImport::SetDataSuffixBytes, py::arg("bytes"))
   .def("save_file_header", &Isis::ProcessImport::SaveFileHeader)
   .def("save_file_trailer", &Isis::ProcessImport::SaveFileTrailer)
   .def("save_data_header", &Isis::ProcessImport::SaveDataHeader)
   .def("save_data_trailer", &Isis::ProcessImport::SaveDataTrailer)
   .def("save_data_prefix", &Isis::ProcessImport::SaveDataPrefix)
   .def("save_data_suffix", &Isis::ProcessImport::SaveDataSuffix)
   .def("file_header_bytes", &Isis::ProcessImport::FileHeaderBytes)
   .def("file_trailer_bytes", &Isis::ProcessImport::FileTrailerBytes)
   .def("data_header_bytes", &Isis::ProcessImport::DataHeaderBytes)
   .def("data_trailer_bytes", &Isis::ProcessImport::DataTrailerBytes)
   .def("data_prefix_bytes", &Isis::ProcessImport::DataPrefixBytes)
   .def("data_suffix_bytes", &Isis::ProcessImport::DataSuffixBytes)
   .def("set_organization", &Isis::ProcessImport::SetOrganization, py::arg("organization"))
   .def("organization", &Isis::ProcessImport::Organization)
   .def("set_base",
     static_cast<void (Isis::ProcessImport::*)(const double)>(&Isis::ProcessImport::SetBase),
     py::arg("base"))
   .def("set_base",
     static_cast<void (Isis::ProcessImport::*)(const std::vector<double>)>(&Isis::ProcessImport::SetBase),
     py::arg("base"))
   .def("set_multiplier",
     static_cast<void (Isis::ProcessImport::*)(const double)>(&Isis::ProcessImport::SetMultiplier),
     py::arg("multiplier"))
   .def("set_multiplier",
     static_cast<void (Isis::ProcessImport::*)(const std::vector<double>)>(&Isis::ProcessImport::SetMultiplier),
     py::arg("multiplier"))
   .def("set_special_values", &Isis::ProcessImport::SetSpecialValues,
     py::arg("null"), py::arg("lrs"), py::arg("lis"), py::arg("hrs"), py::arg("his"))
   .def("set_null", &Isis::ProcessImport::SetNull, py::arg("minimum"), py::arg("maximum"))
   .def("set_lrs", &Isis::ProcessImport::SetLRS, py::arg("minimum"), py::arg("maximum"))
   .def("set_lis", &Isis::ProcessImport::SetLIS, py::arg("minimum"), py::arg("maximum"))
   .def("set_hrs", &Isis::ProcessImport::SetHRS, py::arg("minimum"), py::arg("maximum"))
   .def("set_his", &Isis::ProcessImport::SetHIS, py::arg("minimum"), py::arg("maximum"))
   .def("test_pixel", &Isis::ProcessImport::TestPixel, py::arg("pixel"))
   .def("check_pixel_range",
     [](Isis::ProcessImport &self, const std::string &pixel_name, double minimum, double maximum) {
       self.CheckPixelRange(stdStringToQString(pixel_name), minimum, maximum);
     },
     py::arg("pixel_name"), py::arg("minimum"), py::arg("maximum"));

  py::class_<Isis::ProcessImportFits, Isis::ProcessImport>(m, "ProcessImportFits")
   .def(py::init<>())
   .def("standard_instrument_group", &Isis::ProcessImportFits::standardInstrumentGroup, py::arg("fits_label"))
   .def("extra_fits_label", &Isis::ProcessImportFits::extraFitsLabel, py::arg("label_number"))
   .def("fits_image_label", &Isis::ProcessImportFits::fitsImageLabel, py::arg("label_number"))
   .def("set_fits_file", &Isis::ProcessImportFits::setFitsFile, py::arg("fits_file"))
   .def("set_process_file_structure", &Isis::ProcessImportFits::setProcessFileStructure, py::arg("label_number"));

  py::class_<Isis::ProcessImportPds, Isis::ProcessImport> process_import_pds(m, "ProcessImportPds");

  py::enum_<Isis::ProcessImportPds::PdsFileType>(process_import_pds, "PdsFileType")
   .value("Image", Isis::ProcessImportPds::Image)
   .value("Qube", Isis::ProcessImportPds::Qube)
   .value("SpectralQube", Isis::ProcessImportPds::SpectralQube)
   .value("L0", Isis::ProcessImportPds::L0)
   .value("Rdn", Isis::ProcessImportPds::Rdn)
   .value("Loc", Isis::ProcessImportPds::Loc)
   .value("Obs", Isis::ProcessImportPds::Obs)
   .value("CombinedSpectrum", Isis::ProcessImportPds::CombinedSpectrum)
   .value("All", Isis::ProcessImportPds::All);

  process_import_pds
   .def(py::init<>())
   .def("get_projection_offset_change", &Isis::ProcessImportPds::GetProjectionOffsetChange)
   .def("get_projection_offset_group", &Isis::ProcessImportPds::GetProjectionOffsetGroup)
   .def("set_pds_file",
       [](Isis::ProcessImportPds &self, const std::string &pds_label_file, const std::string &pds_data_file,
          Isis::Pvl &pds_label, Isis::ProcessImportPds::PdsFileType allowed_types) {
         self.SetPdsFile(stdStringToQString(pds_label_file), stdStringToQString(pds_data_file), pds_label,
                allowed_types);
       },
     py::arg("pds_label_file"), py::arg("pds_data_file"), py::arg("pds_label"), py::arg("allowed_types") = Isis::ProcessImportPds::All)
   .def("set_pds_file_from_label",
       [](Isis::ProcessImportPds &self, const Isis::Pvl &pds_label, const std::string &pds_data_file,
          Isis::ProcessImportPds::PdsFileType allowed_types) {
         self.SetPdsFile(pds_label, stdStringToQString(pds_data_file), allowed_types);
       },
     py::arg("pds_label"), py::arg("pds_data_file"), py::arg("allowed_types") = Isis::ProcessImportPds::All)
   .def("process_label",
       [](Isis::ProcessImportPds &self, const std::string &pds_data_file,
          Isis::ProcessImportPds::PdsFileType allowed_types) {
         self.ProcessLabel(stdStringToQString(pds_data_file), allowed_types);
       },
     py::arg("pds_data_file"), py::arg("allowed_types"))
   .def("translate_pds_projection", &Isis::ProcessImportPds::TranslatePdsProjection, py::arg("label"))
   .def("translate_isis2_labels", &Isis::ProcessImportPds::TranslateIsis2Labels, py::arg("label"))
   .def("translate_pds_labels", &Isis::ProcessImportPds::TranslatePdsLabels, py::arg("label"))
   .def("is_isis2", &Isis::ProcessImportPds::IsIsis2)
   .def("omit_original_label", &Isis::ProcessImportPds::OmitOriginalLabel);

  py::class_<Isis::ProcessImportVicar, Isis::ProcessImport>(m, "ProcessImportVicar")
   .def(py::init<>())
   .def("set_vicar_file",
           [](Isis::ProcessImportVicar &self, const std::string &vicar_file, Isis::Pvl &vicar_label) {
             self.SetVicarFile(stdStringToQString(vicar_file), vicar_label);
           },
     py::arg("vicar_file"), py::arg("vicar_label"));

  py::class_<Isis::ExportDescription> export_description(m, "ExportDescription");

  py::class_<Isis::ExportDescription::ChannelDescription>(export_description, "ChannelDescription")
   .def(py::init([](const Isis::FileName &file_name, py::object attributes) {
          Isis::FileName file = file_name;
          Isis::CubeAttributeInput att = makeCubeAttributeInput(attributes);
          return std::make_unique<Isis::ExportDescription::ChannelDescription>(file, att);
        }),
     py::arg("file_name"),
     py::arg("attributes") = py::none())
   .def("filename", &Isis::ExportDescription::ChannelDescription::filename)
   .def("attributes",
     [](const Isis::ExportDescription::ChannelDescription &self) {
       return qStringToStdString(self.attributes().toString());
     })
   .def("bands",
     [](const Isis::ExportDescription::ChannelDescription &self) {
       return cubeAttributeInputBandsToStrings(self.attributes());
     })
   .def("set_input_range", &Isis::ExportDescription::ChannelDescription::setInputRange,
     py::arg("minimum"), py::arg("maximum"))
   .def("input_minimum", &Isis::ExportDescription::ChannelDescription::inputMinimum)
   .def("input_maximum", &Isis::ExportDescription::ChannelDescription::inputMaximum)
   .def("has_custom_range", &Isis::ExportDescription::ChannelDescription::hasCustomRange)
   .def("__repr__",
     [](const Isis::ExportDescription::ChannelDescription &self) {
       return "ChannelDescription(filename='" + qStringToStdString(self.filename().toString())
              + "', attributes='" + qStringToStdString(self.attributes().toString()) + "')";
     });

  export_description
   .def(py::init<>())
   .def(py::init<const Isis::ExportDescription &>(), py::arg("other"))
   .def("set_pixel_type", &Isis::ExportDescription::setPixelType, py::arg("pixel_type"))
   .def("pixel_type", &Isis::ExportDescription::pixelType)
   .def("output_pixel_null", &Isis::ExportDescription::outputPixelNull)
   .def("output_pixel_valid_min", &Isis::ExportDescription::outputPixelValidMin)
   .def("output_pixel_valid_max", &Isis::ExportDescription::outputPixelValidMax)
   .def("output_pixel_absolute_min", &Isis::ExportDescription::outputPixelAbsoluteMin)
   .def("output_pixel_absolute_max", &Isis::ExportDescription::outputPixelAbsoluteMax)
   .def("add_channel",
     [](Isis::ExportDescription &self, const Isis::FileName &file_name, py::object attributes) {
       Isis::FileName file = file_name;
       Isis::CubeAttributeInput att = makeCubeAttributeInput(attributes);
       return self.addChannel(file, att);
     },
     py::arg("file_name"),
     py::arg("attributes") = py::none())
   .def("add_channel",
     [](Isis::ExportDescription &self, const Isis::FileName &file_name, py::object attributes,
        double minimum, double maximum) {
       Isis::FileName file = file_name;
       Isis::CubeAttributeInput att = makeCubeAttributeInput(attributes);
       return self.addChannel(file, att, minimum, maximum);
     },
     py::arg("file_name"),
     py::arg("attributes"),
     py::arg("minimum"),
     py::arg("maximum"))
   .def("channel", &Isis::ExportDescription::channel,
     py::arg("index"),
     py::return_value_policy::reference_internal)
   .def("channel_count", &Isis::ExportDescription::channelCount)
   .def("__repr__",
     [](const Isis::ExportDescription &self) {
       return "ExportDescription(channel_count=" + std::to_string(self.channelCount()) + ")";
     });

  py::class_<Isis::JP2Error>(m, "JP2Error")
   .def(py::init<>())
   .def("put_text", &Isis::JP2Error::put_text, py::arg("message"))
   .def("add_text", &Isis::JP2Error::add_text, py::arg("message"))
   .def("flush", &Isis::JP2Error::flush, py::arg("end_of_message") = false)
   .def_readwrite("message", &Isis::JP2Error::Message)
   .def("__repr__",
     [](const Isis::JP2Error &self) {
       return "JP2Error(message='" + self.Message + "')";
     });

  py::class_<Isis::JP2Decoder>(m, "JP2Decoder")
   .def(py::init([](const std::string &jp2file) {
          return std::make_unique<Isis::JP2Decoder>(stdStringToQString(jp2file));
        }),
     py::arg("jp2file"))
   .def("kakadu_error", &Isis::JP2Decoder::kakadu_error,
     py::return_value_policy::reference_internal)
   .def("open_file", &Isis::JP2Decoder::OpenFile)
   .def("sample_dimension", &Isis::JP2Decoder::GetSampleDimension)
   .def("line_dimension", &Isis::JP2Decoder::GetLineDimension)
   .def("band_dimension", &Isis::JP2Decoder::GetBandDimension)
   .def("pixel_bytes", &Isis::JP2Decoder::GetPixelBytes)
   .def("signed_data", &Isis::JP2Decoder::GetSignedData)
   .def_static("is_jp2",
     [](const std::string &filename) {
       return Isis::JP2Decoder::IsJP2(stdStringToQString(filename));
     },
     py::arg("filename"))
   .def("__repr__",
     [](const Isis::JP2Decoder &self) {
       return "JP2Decoder(samples=" + std::to_string(self.GetSampleDimension())
              + ", lines=" + std::to_string(self.GetLineDimension())
              + ", bands=" + std::to_string(self.GetBandDimension()) + ")";
     });

  py::class_<Isis::JP2Encoder>(m, "JP2Encoder")
   .def(py::init([](const std::string &jp2file, unsigned int samples, unsigned int lines,
                    unsigned int bands, Isis::PixelType pixel_type) {
          return std::make_unique<Isis::JP2Encoder>(
              stdStringToQString(jp2file), samples, lines, bands, pixel_type);
        }),
     py::arg("jp2file"),
     py::arg("samples"),
     py::arg("lines"),
     py::arg("bands"),
     py::arg("pixel_type"))
   .def("kakadu_error", &Isis::JP2Encoder::kakadu_error,
     py::return_value_policy::reference_internal)
   .def("open_file", &Isis::JP2Encoder::OpenFile)
   .def("__repr__",
     [](const Isis::JP2Encoder &) {
       return "JP2Encoder()";
     });

}
