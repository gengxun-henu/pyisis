// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "AlphaCube.h"
#include "BandManager.h"
#include "BoxcarManager.h"
#include "Brick.h"
#include "Buffer.h"
#include "BufferManager.h"
#include "Camera.h"
#include "Cube.h"
#include "Endian.h"
#include "FileName.h"
#include "Histogram.h"
#include "LineManager.h"
#include "PixelType.h"
#include "Portal.h"
#include "Pvl.h"
#include "PvlGroup.h"
#include "Projection.h"
#include "SampleManager.h"
#include "Statistics.h"
#include "Table.h"
#include "TableField.h"
#include "TableRecord.h"
#include "TileManager.h"
#include "helpers.h"

namespace py = pybind11;

namespace {

py::object tableFieldValue(const Isis::TableField &field) {
     if (field.isText()) {
          return py::cast(qStringToStdString(static_cast<QString>(field)));
     }
     if (field.isInteger()) {
          if (field.size() == 1) {
               return py::cast(static_cast<int>(field));
          }
          return py::cast(static_cast<std::vector<int>>(field));
     }
     if (field.isDouble()) {
          if (field.size() == 1) {
               return py::cast(static_cast<double>(field));
          }
          return py::cast(static_cast<std::vector<double>>(field));
     }
     if (field.size() == 1) {
          return py::cast(static_cast<float>(field));
     }
     return py::cast(static_cast<std::vector<float>>(field));
}

void setTableFieldValue(Isis::TableField &field, const py::object &value) {
     if (field.isText()) {
          field = stdStringToQString(value.cast<std::string>());
          return;
     }

     if (field.isInteger()) {
          if (field.size() == 1) {
               field = value.cast<int>();
          }
          else {
               field = value.cast<std::vector<int>>();
          }
          return;
     }

     if (field.isDouble()) {
          if (field.size() == 1) {
               field = value.cast<double>();
          }
          else {
               field = value.cast<std::vector<double>>();
          }
          return;
     }

     if (field.size() == 1) {
          field = value.cast<float>();
     }
     else {
          field = value.cast<std::vector<float>>();
     }
}

}  // namespace

void bind_low_level_cube_io(py::module_ &m) {
  py::enum_<Isis::PixelType>(m, "PixelType")
      .value("None", Isis::PixelType::None)
      .value("UnsignedByte", Isis::PixelType::UnsignedByte)
      .value("SignedByte", Isis::PixelType::SignedByte)
      .value("UnsignedWord", Isis::PixelType::UnsignedWord)
      .value("SignedWord", Isis::PixelType::SignedWord)
      .value("UnsignedInteger", Isis::PixelType::UnsignedInteger)
      .value("SignedInteger", Isis::PixelType::SignedInteger)
      .value("Real", Isis::PixelType::Real)
      .value("Double", Isis::PixelType::Double);

  py::enum_<Isis::ByteOrder>(m, "ByteOrder")
      .value("NoByteOrder", Isis::ByteOrder::NoByteOrder)
      .value("Lsb", Isis::ByteOrder::Lsb)
      .value("Msb", Isis::ByteOrder::Msb);

  m.def("pixel_type_name", [](Isis::PixelType pixel_type) { return qStringToStdString(Isis::PixelTypeName(pixel_type)); },
        py::arg("pixel_type"));
  m.def("pixel_type_enumeration",
        [](const std::string &pixel_type) { return Isis::PixelTypeEnumeration(stdStringToQString(pixel_type)); },
        py::arg("pixel_type"));
  m.def("byte_order_name", [](Isis::ByteOrder byte_order) { return qStringToStdString(Isis::ByteOrderName(byte_order)); },
        py::arg("byte_order"));
  m.def("byte_order_enumeration",
        [](const std::string &byte_order) { return Isis::ByteOrderEnumeration(stdStringToQString(byte_order)); },
        py::arg("byte_order"));
  m.def("is_lsb", &Isis::IsLsb);
  m.def("is_msb", &Isis::IsMsb);

  py::class_<Isis::Buffer>(m, "Buffer")
      .def(py::init<>())
      .def(py::init<int, int, int, Isis::PixelType>(),
           py::arg("samples"),
           py::arg("lines"),
           py::arg("bands"),
           py::arg("pixel_type"))
      .def(py::init<const Isis::Buffer &>(), py::arg("other"))
      .def("sample_dimension", &Isis::Buffer::SampleDimension)
      .def("line_dimension", &Isis::Buffer::LineDimension)
      .def("band_dimension", &Isis::Buffer::BandDimension)
      .def("size", &Isis::Buffer::size)
      .def("sample", &Isis::Buffer::Sample, py::arg("index") = 0)
      .def("line", &Isis::Buffer::Line, py::arg("index") = 0)
      .def("band", &Isis::Buffer::Band, py::arg("index") = 0)
      .def("position",
           [](const Isis::Buffer &self, int index) {
             int sample = 0;
             int line = 0;
             int band = 0;
             self.Position(index, sample, line, band);
             return py::make_tuple(sample, line, band);
           },
           py::arg("index"))
      .def("index", &Isis::Buffer::Index, py::arg("sample"), py::arg("line"), py::arg("band"))
      .def("at", &Isis::Buffer::at, py::arg("index"))
      .def("double_buffer",
           [](const Isis::Buffer &self) {
             const double *buffer = self.DoubleBuffer();
             return std::vector<double>(buffer, buffer + self.size());
           })
      .def("copy", &Isis::Buffer::Copy, py::arg("other"), py::arg("include_raw_buffer") = true)
      .def("copy_overlap_from", &Isis::Buffer::CopyOverlapFrom, py::arg("other"))
      .def("pixel_type", &Isis::Buffer::PixelType)
      .def("fill", [](Isis::Buffer &self, double value) { self = value; }, py::arg("value"))
      .def("__len__", &Isis::Buffer::size)
      .def("__getitem__", [](const Isis::Buffer &self, int index) { return self[index]; }, py::arg("index"))
      .def("__setitem__",
           [](Isis::Buffer &self, int index, double value) { self[index] = value; },
           py::arg("index"),
           py::arg("value"));

  py::class_<Isis::BufferManager, Isis::Buffer>(m, "BufferManager")
      .def(py::init<>())
      .def(py::init<int, int, int, int, int, int, Isis::PixelType, bool>(),
           py::arg("max_samples"),
           py::arg("max_lines"),
           py::arg("max_bands"),
           py::arg("buffer_samples"),
           py::arg("buffer_lines"),
           py::arg("buffer_bands"),
           py::arg("pixel_type"),
           py::arg("reverse") = false)
      .def("begin", &Isis::BufferManager::begin)
      .def("next", &Isis::BufferManager::next)
      .def("end", &Isis::BufferManager::end)
      .def("set_position", &Isis::BufferManager::setpos, py::arg("map"));

  py::class_<Isis::Brick, Isis::BufferManager>(m, "Brick")
      .def(py::init<int, int, int, Isis::PixelType, bool>(),
           py::arg("samples"),
           py::arg("lines"),
           py::arg("bands"),
           py::arg("pixel_type"),
           py::arg("reverse") = false)
      .def(py::init([](const Isis::Cube &cube, int buffer_samples, int buffer_lines, int buffer_bands, bool reverse) {
             return Isis::Brick(cube, buffer_samples, buffer_lines, buffer_bands, reverse);
           }),
           py::arg("cube"),
           py::arg("buffer_samples"),
           py::arg("buffer_lines"),
           py::arg("buffer_bands"),
           py::arg("reverse") = false)
      .def(py::init<int, int, int, int, int, int, Isis::PixelType, bool>(),
           py::arg("max_samples"),
           py::arg("max_lines"),
           py::arg("max_bands"),
           py::arg("buffer_samples"),
           py::arg("buffer_lines"),
           py::arg("buffer_bands"),
           py::arg("pixel_type"),
           py::arg("reverse") = false)
      .def("set_base_position", &Isis::Brick::SetBasePosition, py::arg("sample"), py::arg("line"), py::arg("band"))
      .def("set_base_sample", &Isis::Brick::SetBaseSample, py::arg("sample"))
      .def("set_base_line", &Isis::Brick::SetBaseLine, py::arg("line"))
      .def("set_base_band", &Isis::Brick::SetBaseBand, py::arg("band"))
      .def("resize", &Isis::Brick::Resize, py::arg("samples"), py::arg("lines"), py::arg("bands"))
      .def("set_brick", &Isis::Brick::SetBrick, py::arg("brick"))
      .def("bricks", &Isis::Brick::Bricks);

  py::class_<Isis::Portal, Isis::Buffer>(m, "Portal")
      .def(py::init<int, int, Isis::PixelType, double, double>(),
           py::arg("buffer_samples"),
           py::arg("buffer_lines"),
           py::arg("pixel_type"),
           py::arg("hot_sample") = -0.5,
           py::arg("hot_line") = -0.5)
      .def("set_position", &Isis::Portal::SetPosition, py::arg("sample"), py::arg("line"), py::arg("band"))
      .def("set_hot_spot", &Isis::Portal::SetHotSpot, py::arg("sample") = -0.5, py::arg("line") = -0.5);

  py::class_<Isis::LineManager, Isis::BufferManager>(m, "LineManager")
      .def(py::init<const Isis::Cube &, const bool>(), py::arg("cube"), py::arg("reverse") = false)
      .def("set_line", &Isis::LineManager::SetLine, py::arg("line"), py::arg("band") = 1);

  py::class_<Isis::SampleManager, Isis::BufferManager>(m, "SampleManager")
      .def(py::init<const Isis::Cube &, const bool>(), py::arg("cube"), py::arg("reverse") = false)
      .def("set_sample", &Isis::SampleManager::SetSample, py::arg("sample"), py::arg("band") = 1);

  py::class_<Isis::BandManager, Isis::BufferManager>(m, "BandManager")
       .def(py::init<const Isis::Cube &, const bool>(), py::arg("cube"), py::arg("reverse") = false)
       .def("set_band", &Isis::BandManager::SetBand, py::arg("sample"), py::arg("line") = 1);

  py::class_<Isis::TileManager, Isis::BufferManager>(m, "TileManager")
      .def(py::init<const Isis::Cube &, const int &, const int &>(),
           py::arg("cube"),
           py::arg("buffer_samples") = 128,
           py::arg("buffer_lines") = 128)
      .def("set_tile", &Isis::TileManager::SetTile, py::arg("tile"), py::arg("band") = 1)
      .def("tiles", &Isis::TileManager::Tiles);

  py::class_<Isis::BoxcarManager, Isis::BufferManager>(m, "BoxcarManager")
      .def(py::init<const Isis::Cube &, const int &, const int &>(),
           py::arg("cube"),
           py::arg("box_samples"),
           py::arg("box_lines"));

  py::class_<Isis::AlphaCube>(m, "AlphaCube")
       .def(py::init<Isis::Cube &>(), py::arg("cube"))
      .def(py::init<int, int, int, int, double, double, double, double>(),
           py::arg("alpha_samples"),
           py::arg("alpha_lines"),
           py::arg("beta_samples"),
           py::arg("beta_lines"),
           py::arg("base_sample") = 0.5,
           py::arg("base_line") = 0.5,
           py::arg("multiplier_sample") = 1.0,
           py::arg("multiplier_line") = 1.0)
      .def("alpha_samples", &Isis::AlphaCube::AlphaSamples)
      .def("alpha_lines", &Isis::AlphaCube::AlphaLines)
      .def("beta_samples", &Isis::AlphaCube::BetaSamples)
      .def("beta_lines", &Isis::AlphaCube::BetaLines)
      .def("alpha_sample", &Isis::AlphaCube::AlphaSample, py::arg("beta_sample"))
      .def("alpha_line", &Isis::AlphaCube::AlphaLine, py::arg("beta_line"))
      .def("beta_sample", &Isis::AlphaCube::BetaSample, py::arg("alpha_sample"))
      .def("beta_line", &Isis::AlphaCube::BetaLine, py::arg("alpha_line"))
      .def("update_group", &Isis::AlphaCube::UpdateGroup, py::arg("group"));

  py::class_<Isis::TableField> table_field(m, "TableField");

  py::enum_<Isis::TableField::Type>(table_field, "Type")
      .value("Integer", Isis::TableField::Integer)
      .value("Double", Isis::TableField::Double)
      .value("Text", Isis::TableField::Text)
      .value("Real", Isis::TableField::Real);

  table_field
      .def(py::init([](const std::string &name, Isis::TableField::Type type, int size) {
             return Isis::TableField(stdStringToQString(name), type, size);
           }),
           py::arg("name"),
           py::arg("type"),
           py::arg("size") = 1)
      .def(py::init([](Isis::PvlGroup &field) {
             return Isis::TableField(field);
           }),
           py::arg("field"))
      .def("name", [](const Isis::TableField &self) { return qStringToStdString(self.name()); })
      .def("type", &Isis::TableField::type)
      .def("is_integer", &Isis::TableField::isInteger)
      .def("is_double", &Isis::TableField::isDouble)
      .def("is_text", &Isis::TableField::isText)
      .def("is_real", &Isis::TableField::isReal)
      .def("bytes", &Isis::TableField::bytes)
      .def("size", &Isis::TableField::size)
      .def("value", &tableFieldValue)
      .def("set_value", &setTableFieldValue, py::arg("value"))
      .def("pvl_group", &Isis::TableField::pvlGroup)
      .def("to_string",
           [](const Isis::TableField &self, const std::string &delimiter) {
             return qStringToStdString(Isis::TableField::toString(self, stdStringToQString(delimiter)));
           },
           py::arg("delimiter") = ",")
      .def("__str__",
           [](const Isis::TableField &self) {
             return qStringToStdString(Isis::TableField::toString(self));
           })
      .def("__repr__",
           [](const Isis::TableField &self) {
             return "TableField(name='" + qStringToStdString(self.name()) + "', size=" +
                    std::to_string(self.size()) + ")";
           });

  py::class_<Isis::TableRecord> table_record(m, "TableRecord");

  table_record
      .def(py::init<>())
      .def(py::init([](const std::string &record_string,
                       char field_delimiter,
                       const std::vector<std::string> &field_names,
                       int num_field_values) {
             std::vector<QString> q_field_names;
             q_field_names.reserve(field_names.size());
             for (const std::string &field_name : field_names) {
               q_field_names.push_back(stdStringToQString(field_name));
             }
             return Isis::TableRecord(record_string, field_delimiter, q_field_names, num_field_values);
           }),
           py::arg("record_string"),
           py::arg("field_delimiter"),
           py::arg("field_names"),
           py::arg("num_field_values"))
      .def("add_field",
           [](Isis::TableRecord &self, Isis::TableField &field) {
             self += field;
           },
           py::arg("field"))
      .def("fields", &Isis::TableRecord::Fields)
      .def("record_size", &Isis::TableRecord::RecordSize)
      .def("field",
           [](Isis::TableRecord &self, int index) -> Isis::TableField & {
             return self[index];
           },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("field",
           [](Isis::TableRecord &self, const std::string &name) -> Isis::TableField & {
             return self[stdStringToQString(name)];
           },
           py::arg("name"),
           py::return_value_policy::reference_internal)
      .def("to_string",
           [](const Isis::TableRecord &self,
              const std::string &field_delimiter,
              bool field_names,
              bool end_line) {
             return qStringToStdString(Isis::TableRecord::toString(self,
                                                                   stdStringToQString(field_delimiter),
                                                                   field_names,
                                                                   end_line));
           },
           py::arg("field_delimiter") = ",",
           py::arg("field_names") = false,
           py::arg("end_line") = true)
      .def("__getitem__",
           [](Isis::TableRecord &self, int index) -> Isis::TableField & {
             return self[index];
           },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("__getitem__",
           [](Isis::TableRecord &self, const std::string &name) -> Isis::TableField & {
             return self[stdStringToQString(name)];
           },
           py::arg("name"),
           py::return_value_policy::reference_internal)
      .def("__len__", &Isis::TableRecord::Fields)
      .def("__repr__",
           [](const Isis::TableRecord &self) {
             return "TableRecord(fields=" + std::to_string(self.Fields()) + ")";
           });

  py::class_<Isis::Table> table(m, "Table");

  py::enum_<Isis::Table::Association>(table, "Association")
      .value("None", Isis::Table::None)
      .value("Samples", Isis::Table::Samples)
      .value("Lines", Isis::Table::Lines)
      .value("Bands", Isis::Table::Bands);

  table
      .def(py::init([](const std::string &table_name, Isis::TableRecord &record) {
             return Isis::Table(stdStringToQString(table_name), record);
           }),
           py::arg("table_name"),
           py::arg("record"))
      .def(py::init([](const std::string &table_name) {
             return Isis::Table(stdStringToQString(table_name));
           }),
           py::arg("table_name"))
      .def(py::init([](const std::string &table_name, const std::string &file_name) {
             return Isis::Table(stdStringToQString(table_name), stdStringToQString(file_name));
           }),
           py::arg("table_name"),
           py::arg("file_name"))
      .def(py::init([](const std::string &table_name, const std::string &file_name, const Isis::Pvl &file_header) {
             return Isis::Table(stdStringToQString(table_name), stdStringToQString(file_name), file_header);
           }),
           py::arg("table_name"),
           py::arg("file_name"),
           py::arg("file_header"))
      .def(py::init<const Isis::Table &>(), py::arg("other"))
      .def(py::init([](const std::string &table_name,
                       const std::string &table_string,
                       char field_delimiter,
                       const std::vector<Isis::PvlKeyword> &table_attrs) {
             return Isis::Table(stdStringToQString(table_name), table_string, field_delimiter, table_attrs);
           }),
           py::arg("table_name"),
           py::arg("table_string"),
           py::arg("field_delimiter") = ',',
           py::arg("table_attrs") = std::vector<Isis::PvlKeyword>{})
      .def("write",
           [](Isis::Table &self, const std::string &file_name) {
             self.Write(stdStringToQString(file_name));
           },
           py::arg("file_name"))
      .def("name", [](const Isis::Table &self) { return qStringToStdString(self.Name()); })
      .def("label",
           [](Isis::Table &self) -> Isis::PvlObject & { return self.Label(); },
           py::return_value_policy::reference_internal)
      .def("set_association", &Isis::Table::SetAssociation, py::arg("association"))
      .def("is_sample_associated", &Isis::Table::IsSampleAssociated)
      .def("is_line_associated", &Isis::Table::IsLineAssociated)
      .def("is_band_associated", &Isis::Table::IsBandAssociated)
      .def("records", &Isis::Table::Records)
      .def("record_fields", &Isis::Table::RecordFields)
      .def("record_size", &Isis::Table::RecordSize)
      .def("record",
           [](Isis::Table &self, int index) -> Isis::TableRecord & {
             return self[index];
           },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("add_record",
           [](Isis::Table &self, Isis::TableRecord &record) {
             self += record;
           },
           py::arg("record"))
      .def("update", &Isis::Table::Update, py::arg("record"), py::arg("index"))
      .def("delete", &Isis::Table::Delete, py::arg("index"))
      .def("clear", &Isis::Table::Clear)
      .def("to_string",
           [](const Isis::Table &self, const std::string &field_delimiter) {
             return qStringToStdString(Isis::Table::toString(self, stdStringToQString(field_delimiter)));
           },
           py::arg("field_delimiter") = ",")
      .def("__getitem__",
           [](Isis::Table &self, int index) -> Isis::TableRecord & {
             return self[index];
           },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("__len__", &Isis::Table::Records)
      .def("__repr__",
           [](const Isis::Table &self) {
             return "Table(name='" + qStringToStdString(self.Name()) + "', records=" +
                    std::to_string(self.Records()) + ")";
           });

  py::class_<Isis::Cube> cube(m, "Cube");

  py::enum_<Isis::Cube::Format>(cube, "Format")
      .value("Bsq", Isis::Cube::Format::Bsq)
      .value("Tile", Isis::Cube::Format::Tile);

  cube.def(py::init<>())
      .def(py::init([](const Isis::FileName &file_name, const std::string &access) {
                               // Updated: 2026-03-28 - construct on the heap to avoid copying
                               // Isis::Cube, which owns raw pointers and is not safe to shallow-copy.
                               return std::make_unique<Isis::Cube>(file_name, stdStringToQString(access));
           }),
           py::arg("file_name"), py::arg("access") = "r")
      .def("open",
           [](Isis::Cube &self, const std::string &path, const std::string &access) {
             self.open(stdStringToQString(path), stdStringToQString(access));
           },
           py::arg("path"), py::arg("access") = "r")
      .def("create",
           [](Isis::Cube &self, const std::string &path) {
             self.create(stdStringToQString(path));
           },
           py::arg("path"))
      .def("reopen",
           [](Isis::Cube &self, const std::string &access) {
             self.reopen(stdStringToQString(access));
           },
           py::arg("access") = "r")
      .def("close", &Isis::Cube::close, py::arg("remove") = false)
      .def("is_open", &Isis::Cube::isOpen)
      .def("is_projected", &Isis::Cube::isProjected)
      .def("is_read_only", &Isis::Cube::isReadOnly)
      .def("is_read_write", &Isis::Cube::isReadWrite)
      .def("labels_attached", &Isis::Cube::labelsAttached)
      .def("sample_count", &Isis::Cube::sampleCount)
      .def("line_count", &Isis::Cube::lineCount)
      .def("band_count", &Isis::Cube::bandCount)
      .def("base", &Isis::Cube::base)
      .def("multiplier", &Isis::Cube::multiplier)
      .def("label_size", &Isis::Cube::labelSize, py::arg("actual") = false)
      .def("stores_dn_data", &Isis::Cube::storesDnData)
      .def("physical_band", &Isis::Cube::physicalBand, py::arg("virtual_band"))
      .def("set_dimensions", &Isis::Cube::setDimensions, py::arg("samples"), py::arg("lines"), py::arg("bands"))
      .def("set_format", &Isis::Cube::setFormat, py::arg("format"))
      .def("format", &Isis::Cube::format)
      .def("set_byte_order", &Isis::Cube::setByteOrder, py::arg("byte_order"))
      .def("byte_order", &Isis::Cube::byteOrder)
      .def("set_pixel_type", &Isis::Cube::setPixelType, py::arg("pixel_type"))
      .def("pixel_type", &Isis::Cube::pixelType)
      .def("set_labels_attached", &Isis::Cube::setLabelsAttached, py::arg("attached"))
      .def("set_label_size", &Isis::Cube::setLabelSize, py::arg("label_bytes"))
      .def("set_base_multiplier", &Isis::Cube::setBaseMultiplier, py::arg("base"), py::arg("multiplier"))
      .def("set_min_max", &Isis::Cube::setMinMax, py::arg("minimum"), py::arg("maximum"))
      .def("file_name", [](Isis::Cube &self) { return qStringToStdString(self.fileName()); })
      .def("label",
           [](Isis::Cube &self) -> Isis::Pvl * { return self.label(); },
           py::return_value_policy::reference_internal)
      .def("group",
           [](const Isis::Cube &self, const std::string &name) -> Isis::PvlGroup & {
             return self.group(stdStringToQString(name));
           },
           py::arg("name"),
           py::return_value_policy::reference_internal)
      .def("has_group",
           [](const Isis::Cube &self, const std::string &name) {
             return self.hasGroup(stdStringToQString(name));
           },
           py::arg("name"))
      .def("put_group", &Isis::Cube::putGroup, py::arg("group"))
      .def("delete_group",
           [](Isis::Cube &self, const std::string &name) {
             self.deleteGroup(stdStringToQString(name));
           },
           py::arg("name"))
      .def("has_blob",
           [](Isis::Cube &self, const std::string &name, const std::string &type) {
             return self.hasBlob(stdStringToQString(name), stdStringToQString(type));
           },
           py::arg("name"), py::arg("type"))
      .def("has_table",
           [](Isis::Cube &self, const std::string &name) {
             return self.hasTable(stdStringToQString(name));
           },
           py::arg("name"))
      .def("delete_blob",
           [](Isis::Cube &self, const std::string &name, const std::string &type) {
             return self.deleteBlob(stdStringToQString(name), stdStringToQString(type));
           },
           py::arg("name"), py::arg("type"))
      .def("clear_io_cache", &Isis::Cube::clearIoCache)
      .def("camera",
           [](Isis::Cube &self) -> Isis::Camera * { return self.camera(); },
           py::return_value_policy::reference_internal)
      .def("projection",
           [](Isis::Cube &self) -> Isis::Projection * { return self.projection(); },
           py::return_value_policy::reference_internal)
      .def("read", static_cast<void (Isis::Cube::*)(Isis::Buffer &) const>(&Isis::Cube::read), py::arg("buffer"))
      .def("write", static_cast<void (Isis::Cube::*)(Isis::Buffer &)>(&Isis::Cube::write), py::arg("buffer"))
      .def("statistics",
           [](Isis::Cube &self, int band, const std::string &msg) {
             return self.statistics(band, stdStringToQString(msg));
           },
           py::arg("band") = 1,
           py::arg("msg") = "Gathering statistics",
           py::return_value_policy::take_ownership)
      .def("statistics",
           [](Isis::Cube &self, int band, double valid_min, double valid_max, const std::string &msg) {
             return self.statistics(band, valid_min, valid_max, stdStringToQString(msg));
           },
           py::arg("band"),
           py::arg("valid_min"),
           py::arg("valid_max"),
           py::arg("msg") = "Gathering statistics",
           py::return_value_policy::take_ownership)
      .def("histogram",
           [](Isis::Cube &self, int band, const std::string &msg) {
             return self.histogram(band, stdStringToQString(msg));
           },
           py::arg("band") = 1,
           py::arg("msg") = "Gathering histogram",
           py::return_value_policy::take_ownership)
      .def("histogram",
           [](Isis::Cube &self, int band, double valid_min, double valid_max, const std::string &msg) {
             return self.histogram(band, valid_min, valid_max, stdStringToQString(msg));
           },
           py::arg("band"),
           py::arg("valid_min"),
           py::arg("valid_max"),
           py::arg("msg") = "Gathering histogram",
           py::return_value_policy::take_ownership)
      .def("lat_lon_range",
           [](Isis::Cube &self) {
             double min_lat = 0.0;
             double max_lat = 0.0;
             double min_lon = 0.0;
             double max_lon = 0.0;
             self.latLonRange(min_lat, max_lat, min_lon, max_lon);
             return py::make_tuple(min_lat, max_lat, min_lon, max_lon);
           });
}
