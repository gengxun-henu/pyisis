// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-04-09  Geng Xun exposed CubeAttributeInput/Output and LabelAttachment helpers for cube filename attribute parsing.
// Updated: 2026-04-08  Geng Xun added Blob file/bytes helpers alongside existing low-level cube I/O bindings
// Updated: 2026-04-09  Geng Xun added Blobber bindings and Cube table-write/read helpers for low-level blob/table regression coverage.
// Updated: 2026-04-09  Geng Xun added a safe CubeTileHandler wrapper binding for tile-core label update coverage.
// Updated: 2026-04-09  Geng Xun added a safe CubeBsqHandler wrapper binding for BSQ label-update coverage.
// Updated: 2026-04-09  Geng Xun exposed the abstract CubeCachingAlgorithm symbol and a Python-friendly CacheResult surface.
// Updated: 2026-04-09  Geng Xun added a safe CubeIoHandler wrapper over the shared BSQ handler surface for read/write/cache regression checks.
// Updated: 2026-04-09  Geng Xun added OriginalLabel low-level blob/PVL round-trip bindings.
// Updated: 2026-04-09  Geng Xun added RawCubeChunk and RegionalCachingAlgorithm low-level cache helpers.
// Updated: 2026-04-09  Geng Xun added OriginalXmlLabel blob/XML round-trip bindings with Python-friendly XML string access.
// Updated: 2026-04-10  Geng Xun added HiBlob binding (inherits Blobber) with default constructor, cube constructor, and buffer accessor returning list-of-lists.
// Updated: 2026-04-12  Geng Xun exposed Buffer raw_buffer bytes plus BufferManager setpos/swap parity helpers.
// Purpose: pybind11 bindings for low-level ISIS cube I/O types including Blob, OriginalLabel, RawCubeChunk, cache helpers, CubeAttribute helpers, Cube, buffers, managers, AlphaCube, table structures, and HiBlob

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <cstring>
#include <memory>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <QFile>
#include <QList>

#include "AlphaCube.h"
#include "BandManager.h"
#include "Blob.h"
#include "Blobber.h"
#include "BoxcarManager.h"
#include "HiBlob.h"
#include "Brick.h"
#include "Buffer.h"
#include "BufferManager.h"
#include "Camera.h"
#include "Cube.h"
#include "CubeBsqHandler.h"
#include "CubeCachingAlgorithm.h"
#include "CubeAttribute.h"
#include "CubeTileHandler.h"
#include "Endian.h"
#include "FileName.h"
#include "Histogram.h"
#include "LineManager.h"
#include "OriginalLabel.h"
#include "OriginalXmlLabel.h"
#include "PixelType.h"
#include "Portal.h"
#include "Pvl.h"
#include "PvlGroup.h"
#include "Projection.h"
#include "RawCubeChunk.h"
#include "RegionalCachingAlgorithm.h"
#include "SampleManager.h"
#include "Statistics.h"
#include "Table.h"
#include "TableField.h"
#include "TableRecord.h"
#include "TileManager.h"
#include "TrackingTable.h"
#include "helpers.h"

namespace py = pybind11;

namespace {

class CubeBsqHandlerWrapper {
  public:
     CubeBsqHandlerWrapper(
         const std::string &dataFilePath,
         const Isis::Pvl &labels,
         const std::vector<int> &virtualBands,
         bool alreadyOnDisk)
         : m_dataFile(std::make_unique<QFile>(stdStringToQString(dataFilePath))) {
          QIODevice::OpenMode openMode = QIODevice::ReadWrite;
          if (!alreadyOnDisk) {
               openMode |= QIODevice::Truncate;
          }

          if (!m_dataFile->open(openMode)) {
               QString message = "Failed to open CubeBsqHandler data file [" +
                                 m_dataFile->fileName() + "]";
               throw Isis::IException(Isis::IException::Io, message, _FILEINFO_);
          }

          if (!virtualBands.empty()) {
               m_virtualBands = std::make_unique<QList<int>>();
               for (int band : virtualBands) {
                    m_virtualBands->append(band);
               }
          }

          m_handler = std::make_unique<Isis::CubeBsqHandler>(
              m_dataFile.get(),
              m_virtualBands ? m_virtualBands.get() : nullptr,
              labels,
              alreadyOnDisk);
     }

     void updateLabels(Isis::Pvl &labels) {
          m_handler->updateLabels(labels);
     }

     std::string repr() const {
          return "CubeBsqHandler(data_file='" +
                 qStringToStdString(m_dataFile->fileName()) + "')";
     }

  private:
     std::unique_ptr<QFile> m_dataFile;
     std::unique_ptr<QList<int>> m_virtualBands;
     std::unique_ptr<Isis::CubeBsqHandler> m_handler;
};

class CubeIoHandlerWrapper {
  public:
     CubeIoHandlerWrapper(
         const std::string &dataFilePath,
         const Isis::Pvl &labels,
         const std::vector<int> &virtualBands,
         bool alreadyOnDisk)
         : m_dataFile(std::make_unique<QFile>(stdStringToQString(dataFilePath))) {
          QIODevice::OpenMode openMode = QIODevice::ReadWrite;
          if (!alreadyOnDisk) {
               openMode |= QIODevice::Truncate;
          }

          if (!m_dataFile->open(openMode)) {
               QString message = "Failed to open CubeIoHandler data file [" +
                                 m_dataFile->fileName() + "]";
               throw Isis::IException(Isis::IException::Io, message, _FILEINFO_);
          }

          setVirtualBands(virtualBands);
          m_handler = std::unique_ptr<Isis::CubeIoHandler>(
              new Isis::CubeBsqHandler(
                  m_dataFile.get(),
                  m_virtualBands ? m_virtualBands.get() : nullptr,
                  labels,
                  alreadyOnDisk));
     }

     void read(Isis::Buffer &buffer) const {
          m_handler->read(buffer);
     }

     void write(const Isis::Buffer &buffer) {
          m_handler->write(buffer);
     }

     void clearCache(bool blockForWriteCache = true) const {
          m_handler->clearCache(blockForWriteCache);
     }

     long long getDataSize() const {
          return static_cast<long long>(m_handler->getDataSize());
     }

     void setVirtualBands(const std::vector<int> &virtualBands) {
          if (virtualBands.empty()) {
               m_virtualBands.reset();
               m_handler ? m_handler->setVirtualBands(nullptr) : void();
               return;
          }

          m_virtualBands = std::make_unique<QList<int>>();
          for (int band : virtualBands) {
               m_virtualBands->append(band);
          }

          if (m_handler) {
               m_handler->setVirtualBands(m_virtualBands.get());
          }
     }

     void updateLabels(Isis::Pvl &labels) {
          m_handler->updateLabels(labels);
     }

     py::capsule dataFileMutex() {
          return py::capsule(m_handler->dataFileMutex(), "QMutex");
     }

     std::string repr() const {
          return "CubeIoHandler(data_file='" +
                 qStringToStdString(m_dataFile->fileName()) + "')";
     }

  private:
     std::unique_ptr<QFile> m_dataFile;
     std::unique_ptr<QList<int>> m_virtualBands;
     std::unique_ptr<Isis::CubeIoHandler> m_handler;
};

class CubeTileHandlerWrapper {
  public:
     CubeTileHandlerWrapper(
         const std::string &dataFilePath,
         const Isis::Pvl &labels,
         const std::vector<int> &virtualBands,
         bool alreadyOnDisk)
         : m_dataFile(std::make_unique<QFile>(stdStringToQString(dataFilePath))) {
          QIODevice::OpenMode openMode = QIODevice::ReadWrite;
          if (!alreadyOnDisk) {
               openMode |= QIODevice::Truncate;
          }

          if (!m_dataFile->open(openMode)) {
               QString message = "Failed to open CubeTileHandler data file [" +
                                 m_dataFile->fileName() + "]";
               throw Isis::IException(Isis::IException::Io, message, _FILEINFO_);
          }

          if (!virtualBands.empty()) {
               m_virtualBands = std::make_unique<QList<int>>();
               for (int band : virtualBands) {
                    m_virtualBands->append(band);
               }
          }

          m_handler = std::make_unique<Isis::CubeTileHandler>(
              m_dataFile.get(),
              m_virtualBands ? m_virtualBands.get() : nullptr,
              labels,
              alreadyOnDisk);
     }

     void updateLabels(Isis::Pvl &labels) {
          m_handler->updateLabels(labels);
     }

     std::string repr() const {
          return "CubeTileHandler(data_file='" +
                 qStringToStdString(m_dataFile->fileName()) + "')";
     }

  private:
     std::unique_ptr<QFile> m_dataFile;
     std::unique_ptr<QList<int>> m_virtualBands;
     std::unique_ptr<Isis::CubeTileHandler> m_handler;
};

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
     py::enum_<Isis::LabelAttachment>(m, "LabelAttachment")
               .value("AttachedLabel", Isis::AttachedLabel)
               .value("DetachedLabel", Isis::DetachedLabel)
               .value("ExternalLabel", Isis::ExternalLabel);
     m.def("label_attachment_name",
                    [](Isis::LabelAttachment attachment) {
                         return qStringToStdString(Isis::LabelAttachmentName(attachment));
                    },
                    py::arg("attachment"));
     m.def("label_attachment_enumeration",
                    [](const std::string &attachment) {
                         return Isis::LabelAttachmentEnumeration(stdStringToQString(attachment));
                    },
                    py::arg("attachment"));
  m.def("is_lsb", &Isis::IsLsb);
  m.def("is_msb", &Isis::IsMsb);
  m.def("is_blob", &Isis::IsBlob, py::arg("object"));

     py::class_<Isis::CubeAttributeInput>(m, "CubeAttributeInput")
               .def(py::init<>(), "Construct an empty input cube-attribute parser.")
               .def(py::init([](const std::string &attribute_text) {
                               return Isis::CubeAttributeInput(Isis::FileName(stdStringToQString(attribute_text)));
                          }),
                          py::arg("attribute_text"),
                          "Construct an input attribute parser from a filename or attribute string like '+1-3,5'.")
               .def(py::init<const Isis::FileName &>(),
                          py::arg("file_name"),
                          "Construct an input attribute parser from a FileName.")
               .def("bands",
                          [](const Isis::CubeAttributeInput &self) {
                               std::vector<std::string> result;
                               for (const QString &band : self.bands()) {
                                    result.push_back(qStringToStdString(band));
                               }
                               return result;
                          },
                          "Return the expanded list of selected band identifiers.")
               .def("bands_string",
                          [](const Isis::CubeAttributeInput &self) {
                               return qStringToStdString(self.bandsString());
                          },
                          "Return the band attribute as a comma-delimited string.")
               .def("set_bands",
                          [](Isis::CubeAttributeInput &self, const std::vector<std::string> &bands) {
                               std::vector<QString> qbands;
                               qbands.reserve(bands.size());
                               for (const std::string &band : bands) {
                                    qbands.push_back(stdStringToQString(band));
                               }
                               self.setBands(qbands);
                          },
                          py::arg("bands"),
                          "Replace the current band selection with the provided band identifiers.")
               .def("to_string",
                          [](const Isis::CubeAttributeInput &self) {
                               return qStringToStdString(self.toString());
                          })
               .def("add_attribute",
                          [](Isis::CubeAttributeInput &self, const std::string &attribute) {
                               self.addAttribute(stdStringToQString(attribute));
                          },
                          py::arg("attribute"))
               .def("add_attributes",
                          [](Isis::CubeAttributeInput &self, const std::string &attributes) {
                               self.addAttributes(stdStringToQString(attributes));
                          },
                          py::arg("attributes"))
               .def("set_attributes",
                          [](Isis::CubeAttributeInput &self, const std::string &attribute_text) {
                               self.setAttributes(Isis::FileName(stdStringToQString(attribute_text)));
                          },
                          py::arg("attribute_text"))
               .def("__str__",
                          [](const Isis::CubeAttributeInput &self) {
                               return qStringToStdString(self.toString());
                          })
               .def("__repr__",
                          [](const Isis::CubeAttributeInput &self) {
                               return "CubeAttributeInput('" + qStringToStdString(self.toString()) + "')";
                          });

     py::class_<Isis::CubeAttributeOutput>(m, "CubeAttributeOutput")
               .def(py::init<>(), "Construct an empty output cube-attribute parser.")
               .def(py::init([](const std::string &attribute_text) {
                               return Isis::CubeAttributeOutput(Isis::FileName(stdStringToQString(attribute_text)));
                          }),
                          py::arg("attribute_text"),
                          "Construct an output attribute parser from a filename or attribute string like '+Real+Tile'.")
               .def(py::init<const Isis::FileName &>(),
                          py::arg("file_name"),
                          "Construct an output attribute parser from a FileName.")
               .def("propagate_pixel_type", &Isis::CubeAttributeOutput::propagatePixelType)
               .def("propagate_minimum_maximum", &Isis::CubeAttributeOutput::propagateMinimumMaximum)
               .def("file_format", &Isis::CubeAttributeOutput::fileFormat)
               .def("file_format_string",
                          [](const Isis::CubeAttributeOutput &self) {
                               return qStringToStdString(self.fileFormatString());
                          })
               .def("set_file_format", &Isis::CubeAttributeOutput::setFileFormat, py::arg("format"))
               .def("byte_order", &Isis::CubeAttributeOutput::byteOrder)
               .def("byte_order_string",
                          [](const Isis::CubeAttributeOutput &self) {
                               return qStringToStdString(self.byteOrderString());
                          })
               .def("set_byte_order", &Isis::CubeAttributeOutput::setByteOrder, py::arg("order"))
               .def("minimum", &Isis::CubeAttributeOutput::minimum)
               .def("maximum", &Isis::CubeAttributeOutput::maximum)
               .def("set_minimum", &Isis::CubeAttributeOutput::setMinimum, py::arg("minimum"))
               .def("set_maximum", &Isis::CubeAttributeOutput::setMaximum, py::arg("maximum"))
               .def("pixel_type", &Isis::CubeAttributeOutput::pixelType)
               .def("set_pixel_type", &Isis::CubeAttributeOutput::setPixelType, py::arg("pixel_type"))
               .def("set_label_attachment",
                          &Isis::CubeAttributeOutput::setLabelAttachment,
                          py::arg("attachment"))
               .def("label_attachment", &Isis::CubeAttributeOutput::labelAttachment)
               .def("to_string",
                          [](const Isis::CubeAttributeOutput &self) {
                               return qStringToStdString(self.toString());
                          })
               .def("add_attribute",
                          [](Isis::CubeAttributeOutput &self, const std::string &attribute) {
                               self.addAttribute(stdStringToQString(attribute));
                          },
                          py::arg("attribute"))
               .def("add_attributes",
                          [](Isis::CubeAttributeOutput &self, const std::string &attributes) {
                               self.addAttributes(stdStringToQString(attributes));
                          },
                          py::arg("attributes"))
               .def("set_attributes",
                          [](Isis::CubeAttributeOutput &self, const std::string &attribute_text) {
                               self.setAttributes(Isis::FileName(stdStringToQString(attribute_text)));
                          },
                          py::arg("attribute_text"))
               .def("__str__",
                          [](const Isis::CubeAttributeOutput &self) {
                               return qStringToStdString(self.toString());
                          })
               .def("__repr__",
                          [](const Isis::CubeAttributeOutput &self) {
                               return "CubeAttributeOutput('" + qStringToStdString(self.toString()) + "')";
                          });

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
               .def("raw_buffer",
                          [](const Isis::Buffer &self) {
                               const void *raw_buffer = self.RawBuffer();
                               const ssize_t raw_size = static_cast<ssize_t>(Isis::SizeOf(self.PixelType()) * self.size());
                               if (!raw_buffer || raw_size <= 0) {
                                    return py::bytes();
                               }
                               return py::bytes(static_cast<const char *>(raw_buffer), raw_size);
                          },
                          "Return a copy of the raw disk-format buffer bytes based on the buffer pixel type.")
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
      .def("set_position", &Isis::BufferManager::setpos, py::arg("map"))
      .def("setpos", &Isis::BufferManager::setpos, py::arg("map"),
           "Alias for set_position() using the upstream ISIS method name.")
      .def("swap", &Isis::BufferManager::swap, py::arg("other"),
           "Swap traversal state and cube-shape metadata with another BufferManager.");

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

  py::class_<CubeBsqHandlerWrapper>(m, "CubeBsqHandler")
      .def(py::init<const std::string &, const Isis::Pvl &, const std::vector<int> &, bool>(),
           py::arg("data_file_path"),
           py::arg("labels"),
           py::arg("virtual_bands") = std::vector<int>{},
           py::arg("already_on_disk") = false,
           "Construct a BSQ cube-I/O handler wrapper using a real data file path,\n"
           "cube labels, an optional virtual-band mapping, and an on-disk flag.")
      .def("update_labels",
           &CubeBsqHandlerWrapper::updateLabels,
           py::arg("labels"),
           "Update the supplied cube labels so the Core format is marked BandSequential.")
      .def("__repr__", &CubeBsqHandlerWrapper::repr);

  py::class_<CubeIoHandlerWrapper>(m, "CubeIoHandler")
      .def(py::init<const std::string &, const Isis::Pvl &, const std::vector<int> &, bool>(),
           py::arg("data_file_path"),
           py::arg("labels"),
           py::arg("virtual_bands") = std::vector<int>{},
           py::arg("already_on_disk") = false,
           "Construct a safe CubeIoHandler wrapper backed by a BSQ handler for shared read/write/cache operations.")
      .def("read", &CubeIoHandlerWrapper::read, py::arg("buffer"))
      .def("write", &CubeIoHandlerWrapper::write, py::arg("buffer"))
      .def("clear_cache", &CubeIoHandlerWrapper::clearCache, py::arg("block_for_write_cache") = true)
      .def("get_data_size", &CubeIoHandlerWrapper::getDataSize)
      .def("set_virtual_bands", &CubeIoHandlerWrapper::setVirtualBands, py::arg("virtual_bands"))
      .def("update_labels", &CubeIoHandlerWrapper::updateLabels, py::arg("labels"))
      .def("data_file_mutex", &CubeIoHandlerWrapper::dataFileMutex)
      .def("__repr__", &CubeIoHandlerWrapper::repr);

  py::class_<CubeTileHandlerWrapper>(m, "CubeTileHandler")
      .def(py::init<const std::string &, const Isis::Pvl &, const std::vector<int> &, bool>(),
           py::arg("data_file_path"),
           py::arg("labels"),
           py::arg("virtual_bands") = std::vector<int>{},
           py::arg("already_on_disk") = false,
           "Construct a tile cube-I/O handler wrapper using a real data file path,\n"
           "cube labels, an optional virtual-band mapping, and an on-disk flag.")
      .def("update_labels",
           &CubeTileHandlerWrapper::updateLabels,
           py::arg("labels"),
           "Update the supplied cube labels so the Core format is marked Tile and tile sizes are recorded.")
      .def("__repr__", &CubeTileHandlerWrapper::repr);

     py::class_<Isis::RawCubeChunk>(m, "RawCubeChunk")
               .def(py::init<int, int, int, int, int, int, int>(),
                          py::arg("start_sample"),
                          py::arg("start_line"),
                          py::arg("start_band"),
                          py::arg("end_sample"),
                          py::arg("end_line"),
                          py::arg("end_band"),
                          py::arg("num_bytes"))
               .def("is_dirty", &Isis::RawCubeChunk::isDirty)
               .def("get_raw_data",
                          [](Isis::RawCubeChunk &self) {
                               QByteArray &raw = self.getRawData();
                               return py::bytes(raw.constData(), raw.size());
                          })
               .def("set_raw_data",
                          [](Isis::RawCubeChunk &self, const py::bytes &data) {
                               std::string raw = data;
                               self.setRawData(QByteArray(raw.data(), static_cast<int>(raw.size())));
                          },
                          py::arg("raw_data"))
               .def("get_char", &Isis::RawCubeChunk::getChar, py::arg("offset"))
               .def("get_short", &Isis::RawCubeChunk::getShort, py::arg("offset"))
               .def("get_float", &Isis::RawCubeChunk::getFloat, py::arg("offset"))
               .def("get_start_sample", &Isis::RawCubeChunk::getStartSample)
               .def("get_start_line", &Isis::RawCubeChunk::getStartLine)
               .def("get_start_band", &Isis::RawCubeChunk::getStartBand)
               .def("sample_count", &Isis::RawCubeChunk::sampleCount)
               .def("line_count", &Isis::RawCubeChunk::lineCount)
               .def("band_count", &Isis::RawCubeChunk::bandCount)
               .def("get_byte_count", &Isis::RawCubeChunk::getByteCount)
               .def("set_data",
                          [](Isis::RawCubeChunk &self, const py::object &value, int offset) {
                               if (py::isinstance<py::float_>(value)) {
                                    self.setData(value.cast<float>(), offset);
                               }
                               else if (py::isinstance<py::int_>(value)) {
                                    const int int_value = value.cast<int>();
                                    if (int_value >= 0 && int_value <= 255) {
                                         self.setData(static_cast<unsigned char>(int_value), offset);
                                    }
                                    else {
                                         self.setData(static_cast<short>(int_value), offset);
                                    }
                               }
                               else {
                                    throw py::type_error("RawCubeChunk.set_data expects an int or float value");
                               }
                          },
                          py::arg("value"),
                          py::arg("offset"))
               .def("set_dirty", &Isis::RawCubeChunk::setDirty, py::arg("dirty"))
               .def("__repr__",
                          [](const Isis::RawCubeChunk &self) {
                               return "RawCubeChunk(start=(" + std::to_string(self.getStartSample()) + ", " +
                                                  std::to_string(self.getStartLine()) + ", " + std::to_string(self.getStartBand()) +
                                                  "), size=(" + std::to_string(self.sampleCount()) + ", " +
                                                  std::to_string(self.lineCount()) + ", " + std::to_string(self.bandCount()) +
                                                  "), bytes=" + std::to_string(self.getByteCount()) + ")";
                          });

  py::class_<Isis::CubeCachingAlgorithm> cubeCachingAlgorithm(
      m,
      "CubeCachingAlgorithm",
      "Abstract base class for cube-chunk caching recommendations.");

  py::class_<Isis::CubeCachingAlgorithm::CacheResult>(cubeCachingAlgorithm, "CacheResult")
      .def(py::init<>(), "Construct an empty cache result that signals the algorithm did not understand the data.")
      .def(py::init([](const py::iterable &chunks_to_free) {
             QList<Isis::RawCubeChunk *> chunks;
             for (py::handle entry : chunks_to_free) {
                  if (entry.is_none()) {
                       chunks.append(nullptr);
                  }
                  else {
                       chunks.append(entry.cast<Isis::RawCubeChunk *>());
                  }
             }
             return Isis::CubeCachingAlgorithm::CacheResult(chunks);
           }),
           py::arg("chunks_to_free"),
           "Construct a cache result from RawCubeChunk objects or None placeholders.")
      .def(py::init<const Isis::CubeCachingAlgorithm::CacheResult &>(), py::arg("other"))
      .def("algorithm_understood_data",
           &Isis::CubeCachingAlgorithm::CacheResult::algorithmUnderstoodData)
      .def("get_chunks_to_free",
           [](const Isis::CubeCachingAlgorithm::CacheResult &self) {
             py::list result;
             for (Isis::RawCubeChunk *chunk : self.getChunksToFree()) {
                  if (chunk) {
                       result.append(py::cast(chunk, py::return_value_policy::reference));
                  }
                  else {
                       result.append(py::none());
                  }
             }
             return result;
           },
           "Return the RawCubeChunk objects slated for eviction, with None for null entries.")
      .def("__len__",
           [](const Isis::CubeCachingAlgorithm::CacheResult &self) {
             return self.getChunksToFree().size();
           })
      .def("__repr__",
           [](const Isis::CubeCachingAlgorithm::CacheResult &self) {
             return "CubeCachingAlgorithm.CacheResult(understood=" +
                    std::string(self.algorithmUnderstoodData() ? "True" : "False") +
                    ", chunks=" + std::to_string(self.getChunksToFree().size()) + ")";
           });

  py::class_<Isis::RegionalCachingAlgorithm, Isis::CubeCachingAlgorithm>(m, "RegionalCachingAlgorithm")
      .def(py::init<>())
      .def("recommend_chunks_to_free",
           [](Isis::RegionalCachingAlgorithm &self,
              const std::vector<Isis::RawCubeChunk *> &allocated,
              const std::vector<Isis::RawCubeChunk *> &just_used,
              const Isis::Buffer &just_requested) {
             QList<Isis::RawCubeChunk *> allocated_chunks;
             for (Isis::RawCubeChunk *chunk : allocated) {
                  allocated_chunks.append(chunk);
             }

             QList<Isis::RawCubeChunk *> just_used_chunks;
             for (Isis::RawCubeChunk *chunk : just_used) {
                  just_used_chunks.append(chunk);
             }

             return self.recommendChunksToFree(allocated_chunks, just_used_chunks, just_requested);
           },
           py::arg("allocated"),
           py::arg("just_used"),
           py::arg("just_requested"))
      .def("__repr__", [](const Isis::RegionalCachingAlgorithm &) {
        return "RegionalCachingAlgorithm()";
      });

  py::class_<Isis::AlphaCube>(m, "AlphaCube")
      .def(py::init<Isis::Cube &>(), py::arg("cube"))
      .def(py::init<int, int, int, int>(),
           py::arg("alpha_samples"),
           py::arg("alpha_lines"),
           py::arg("beta_samples"),
           py::arg("beta_lines"))
      .def(py::init<int, int, int, int, double, double, double, double>(),
           py::arg("alpha_samples"),
           py::arg("alpha_lines"),
           py::arg("beta_samples"),
           py::arg("beta_lines"),
           py::arg("alpha_starting_sample"),
           py::arg("alpha_starting_line"),
           py::arg("alpha_ending_sample"),
           py::arg("alpha_ending_line"))
      .def("alpha_samples", &Isis::AlphaCube::AlphaSamples)
      .def("alpha_lines", &Isis::AlphaCube::AlphaLines)
      .def("beta_samples", &Isis::AlphaCube::BetaSamples)
      .def("beta_lines", &Isis::AlphaCube::BetaLines)
      .def("alpha_sample", &Isis::AlphaCube::AlphaSample, py::arg("beta_sample"))
      .def("alpha_line", &Isis::AlphaCube::AlphaLine, py::arg("beta_line"))
      .def("beta_sample", &Isis::AlphaCube::BetaSample, py::arg("alpha_sample"))
      .def("beta_line", &Isis::AlphaCube::BetaLine, py::arg("alpha_line"))
      .def("rehash", &Isis::AlphaCube::Rehash, py::arg("alpha_cube"))
      .def("update_group", &Isis::AlphaCube::UpdateGroup, py::arg("cube"));

     py::class_<Isis::Blob> blob(m, "Blob");

     blob.def(py::init([](const std::string &name, const std::string &type) {
                               return Isis::Blob(stdStringToQString(name), stdStringToQString(type));
                          }),
                          py::arg("name"),
                          py::arg("type"))
               .def(py::init([](const std::string &name, const std::string &type, const std::string &file_name) {
                               return Isis::Blob(stdStringToQString(name), stdStringToQString(type), stdStringToQString(file_name));
                          }),
                          py::arg("name"),
                          py::arg("type"),
                          py::arg("file_name"))
               .def(py::init<const Isis::Blob &>(), py::arg("other"))
               .def("__copy__", [](const Isis::Blob &self) { return Isis::Blob(self); })
               .def("__deepcopy__", [](const Isis::Blob &self, py::dict) { return Isis::Blob(self); }, py::arg("memo"))
               .def("type", [](const Isis::Blob &self) { return qStringToStdString(self.Type()); })
               .def("name", [](const Isis::Blob &self) { return qStringToStdString(self.Name()); })
               .def("size", &Isis::Blob::Size)
               .def("label",
                          [](Isis::Blob &self) -> Isis::PvlObject & { return self.Label(); },
                          py::return_value_policy::reference_internal)
               .def("read",
                          [](Isis::Blob &self, const std::string &file_name, const std::vector<Isis::PvlKeyword> &keywords) {
                               self.Read(stdStringToQString(file_name), keywords);
                          },
                          py::arg("file_name"),
                          py::arg("keywords") = std::vector<Isis::PvlKeyword>{})
               .def("read",
                          [](Isis::Blob &self,
                                   const std::string &file_name,
                                   const Isis::Pvl &labels,
                                   const std::vector<Isis::PvlKeyword> &keywords) {
                               self.Read(stdStringToQString(file_name), labels, keywords);
                          },
                          py::arg("file_name"),
                          py::arg("labels"),
                          py::arg("keywords") = std::vector<Isis::PvlKeyword>{})
               .def("write",
                          [](Isis::Blob &self, const std::string &file_name) {
                               self.Write(stdStringToQString(file_name));
                          },
                          py::arg("file_name"))
               .def("get_buffer",
                          [](Isis::Blob &self) {
                               if (self.Size() <= 0 || self.getBuffer() == nullptr) {
                                    return py::bytes();
                               }
                               return py::bytes(self.getBuffer(), self.Size());
                          })
               .def("set_data",
                          [](Isis::Blob &self, const py::bytes &data) {
                               std::string buffer = data;
                               self.setData(buffer.data(), static_cast<int>(buffer.size()));
                          },
                          py::arg("data"))
               .def("take_data",
                          [](Isis::Blob &self, const py::bytes &data) {
                               std::string buffer = data;
                               char *owned = new char[buffer.size()];
                               if (!buffer.empty()) {
                                    std::memcpy(owned, buffer.data(), buffer.size());
                               }
                               self.takeData(owned, static_cast<int>(buffer.size()));
                          },
                          py::arg("data"))
               .def("__bytes__",
                          [](Isis::Blob &self) {
                               if (self.Size() <= 0 || self.getBuffer() == nullptr) {
                                    return py::bytes();
                               }
                               return py::bytes(self.getBuffer(), self.Size());
                          })
               .def("__repr__",
                          [](const Isis::Blob &self) {
                               return "Blob(name='" + qStringToStdString(self.Name()) + "', type='" +
                                                  qStringToStdString(self.Type()) + "', size=" + std::to_string(self.Size()) + ")";
                          });

     py::class_<Isis::OriginalLabel>(m, "OriginalLabel")
               .def(py::init<>(), "Construct an empty OriginalLabel container.")
               .def(py::init([](const std::string &file_name) {
                               return Isis::OriginalLabel(stdStringToQString(file_name));
                          }),
                          py::arg("file_name"),
                          "Load an OriginalLabel from a blob file on disk.")
               .def(py::init<Isis::Blob &>(),
                          py::arg("blob"),
                          "Construct an OriginalLabel from an existing Blob object.")
               .def(py::init<Isis::Pvl>(),
                          py::arg("pvl"),
                          "Construct an OriginalLabel from a PVL document.")
               .def("return_labels",
                          &Isis::OriginalLabel::ReturnLabels,
                          "Return the stored original labels as a PVL object.")
               .def("to_blob",
                          &Isis::OriginalLabel::toBlob,
                          "Serialize this OriginalLabel back to a Blob.")
               .def("__repr__",
                          [](const Isis::OriginalLabel &self) {
                               Isis::Pvl labels = self.ReturnLabels();
                               int object_count = labels.objects();
                               int group_count = labels.groups();
                               return "OriginalLabel(objects=" + std::to_string(object_count) +
                                          ", groups=" + std::to_string(group_count) + ")";
                          });

     py::class_<Isis::OriginalXmlLabel>(m, "OriginalXmlLabel")
               .def(py::init<>(), "Construct an empty OriginalXmlLabel container.")
               .def(py::init([](const std::string &file_name) {
                               return Isis::OriginalXmlLabel(stdStringToQString(file_name));
                          }),
                          py::arg("file_name"),
                          "Load an OriginalXmlLabel from a serialized blob file on disk.")
               .def(py::init<Isis::Blob &>(),
                          py::arg("blob"),
                          "Construct an OriginalXmlLabel from an existing Blob object.")
               .def("to_blob",
                          &Isis::OriginalXmlLabel::toBlob,
                          "Serialize this OriginalXmlLabel back to a Blob.")
               .def("from_blob",
                          &Isis::OriginalXmlLabel::fromBlob,
                          py::arg("blob"),
                          "Load this OriginalXmlLabel from a serialized Blob.")
               .def("read_from_xml_file",
                          [](Isis::OriginalXmlLabel &self, const std::string &file_name) {
                               self.readFromXmlFile(Isis::FileName(stdStringToQString(file_name)));
                          },
                          py::arg("file_name"),
                          "Read and parse original XML labels directly from an XML file.")
               .def("return_labels",
                          [](const Isis::OriginalXmlLabel &self) {
                               return qStringToStdString(self.ReturnLabels().toString());
                          },
                          "Return the stored original XML labels as a serialized XML string.")
               .def("root_tag",
                          [](const Isis::OriginalXmlLabel &self) {
                               return qStringToStdString(self.ReturnLabels().documentElement().tagName());
                          },
                          "Return the XML document root tag name, or an empty string for an empty label.")
               .def("is_empty",
                          [](const Isis::OriginalXmlLabel &self) {
                               return self.ReturnLabels().documentElement().isNull();
                          },
                          "Return True when no XML document has been loaded yet.")
               .def("to_string",
                          [](const Isis::OriginalXmlLabel &self) {
                               return qStringToStdString(self.ReturnLabels().toString());
                          },
                          "Alias for return_labels().")
               .def("__str__",
                          [](const Isis::OriginalXmlLabel &self) {
                               return qStringToStdString(self.ReturnLabels().toString());
                          })
               .def("__repr__",
                          [](const Isis::OriginalXmlLabel &self) {
                               const QDomDocument &labels = self.ReturnLabels();
                               const QString root_tag = labels.documentElement().tagName();
                               return "OriginalXmlLabel(root='" + qStringToStdString(root_tag) +
                                          "', length=" + std::to_string(labels.toString().size()) + ")";
                          });

     py::class_<Isis::Blobber> blobber(m, "Blobber");

     blobber
               .def(py::init<>(), "Construct an empty Blobber with undefined blob and field names.")
               .def(py::init([](const std::string &blob_name,
                                const std::string &field_name,
                                const std::string &name) {
                               return Isis::Blobber(
                                   stdStringToQString(blob_name),
                                   stdStringToQString(field_name),
                                   stdStringToQString(name));
                          }),
                          py::arg("blob_name"),
                          py::arg("field_name"),
                          py::arg("name") = "Blob")
               .def(py::init([](Isis::Cube &cube,
                                const std::string &blob_name,
                                const std::string &field_name,
                                const std::string &name) {
                               return Isis::Blobber(
                                   cube,
                                   stdStringToQString(blob_name),
                                   stdStringToQString(field_name),
                                   stdStringToQString(name));
                          }),
                          py::arg("cube"),
                          py::arg("blob_name"),
                          py::arg("field_name"),
                          py::arg("name") = "Blob")
               .def(py::init<const Isis::Blobber &>(), py::arg("other"))
               .def("deepcopy", &Isis::Blobber::deepcopy)
               .def("set_name",
                          [](Isis::Blobber &self, const std::string &name) {
                               self.setName(stdStringToQString(name));
                          },
                          py::arg("name"))
               .def("set_blob_name",
                          [](Isis::Blobber &self, const std::string &blob_name) {
                               self.setBlobName(stdStringToQString(blob_name));
                          },
                          py::arg("blob_name"))
               .def("set_field_name",
                          [](Isis::Blobber &self, const std::string &field_name) {
                               self.setFieldName(stdStringToQString(field_name));
                          },
                          py::arg("field_name"))
               .def("size", &Isis::Blobber::size)
               .def("lines", &Isis::Blobber::Lines)
               .def("samples", &Isis::Blobber::Samples)
               .def("get_name",
                          [](const Isis::Blobber &self) {
                               return qStringToStdString(self.getName());
                          })
               .def("get_blob_name",
                          [](const Isis::Blobber &self) {
                               return qStringToStdString(self.getBlobName());
                          })
               .def("get_field_name",
                          [](const Isis::Blobber &self) {
                               return qStringToStdString(self.getFieldName());
                          })
               .def("load",
                          [](Isis::Blobber &self, const std::string &file_name) {
                               self.load(stdStringToQString(file_name));
                          },
                          py::arg("file_name"))
               .def("load",
                          [](Isis::Blobber &self, Isis::Cube &cube) {
                               self.load(cube);
                          },
                          py::arg("cube"))
               .def("row",
                          [](const Isis::Blobber &self, int line_index) {
                               if (line_index < 0 || line_index >= self.Lines()) {
                                    throw py::index_error("Blobber line index out of range");
                               }
                               std::vector<double> row(self.Samples());
                               for (int sample_index = 0; sample_index < self.Samples(); ++sample_index) {
                                    row[sample_index] = self[line_index][sample_index];
                               }
                               return row;
                          },
                          py::arg("line_index"),
                          "Return a copy of one 0-based row from the loaded blob.")
               .def("value",
                          [](const Isis::Blobber &self, int line_index, int sample_index) {
                               if (line_index < 0 || line_index >= self.Lines() ||
                                   sample_index < 0 || sample_index >= self.Samples()) {
                                    throw py::index_error("Blobber indices out of range");
                               }
                               return self[line_index][sample_index];
                          },
                          py::arg("line_index"),
                          py::arg("sample_index"),
                          "Return one 0-based blob value.")
               .def("set_value",
                          [](Isis::Blobber &self, int line_index, int sample_index, double value) {
                               if (line_index < 0 || line_index >= self.Lines() ||
                                   sample_index < 0 || sample_index >= self.Samples()) {
                                    throw py::index_error("Blobber indices out of range");
                               }
                               self[line_index][sample_index] = value;
                          },
                          py::arg("line_index"),
                          py::arg("sample_index"),
                          py::arg("value"),
                          "Mutate one 0-based blob value in-place.")
               .def("__len__", &Isis::Blobber::Lines)
               .def("__copy__", [](const Isis::Blobber &self) { return Isis::Blobber(self); })
               .def("__deepcopy__",
                          [](const Isis::Blobber &self, py::dict) { return self.deepcopy(); },
                          py::arg("memo"))
               .def("__getitem__",
                          [](const Isis::Blobber &self, int line_index) {
                               if (line_index < 0 || line_index >= self.Lines()) {
                                    throw py::index_error("Blobber line index out of range");
                               }
                               std::vector<double> row(self.Samples());
                               for (int sample_index = 0; sample_index < self.Samples(); ++sample_index) {
                                    row[sample_index] = self[line_index][sample_index];
                               }
                               return row;
                          },
                          py::arg("line_index"))
               .def("__getitem__",
                          [](const Isis::Blobber &self, const std::pair<int, int> &index) {
                               const int line_index = index.first;
                               const int sample_index = index.second;
                               if (line_index < 0 || line_index >= self.Lines() ||
                                   sample_index < 0 || sample_index >= self.Samples()) {
                                    throw py::index_error("Blobber indices out of range");
                               }
                               return self[line_index][sample_index];
                          },
                          py::arg("index"))
               .def("__setitem__",
                          [](Isis::Blobber &self, const std::pair<int, int> &index, double value) {
                               const int line_index = index.first;
                               const int sample_index = index.second;
                               if (line_index < 0 || line_index >= self.Lines() ||
                                   sample_index < 0 || sample_index >= self.Samples()) {
                                    throw py::index_error("Blobber indices out of range");
                               }
                               self[line_index][sample_index] = value;
                          },
                          py::arg("index"),
                          py::arg("value"))
               .def("__repr__",
                          [](const Isis::Blobber &self) {
                               return "Blobber(name='" + qStringToStdString(self.getName()) +
                                          "', blob_name='" + qStringToStdString(self.getBlobName()) +
                                          "', field_name='" + qStringToStdString(self.getFieldName()) +
                                          "', lines=" + std::to_string(self.Lines()) +
                                          ", samples=" + std::to_string(self.Samples()) + ")";
                          });

  // HiBlob — BLOB extraction class for HiRISE calibration data.
  // Inherits all Blobber methods. Added: 2026-04-10
  py::class_<Isis::HiBlob, Isis::Blobber>(m, "HiBlob")
      .def(py::init<>(), "Construct an empty HiBlob with no cube backing store.")
      .def(py::init([](Isis::Cube &cube,
                       const std::string &tblname,
                       const std::string &field,
                       const std::string &name) {
                          return Isis::HiBlob(cube,
                                              QString::fromStdString(tblname),
                                              QString::fromStdString(field),
                                              QString::fromStdString(name));
                     }),
           py::arg("cube"),
           py::arg("tblname"),
           py::arg("field"),
           py::arg("name") = "HiBlob",
           py::keep_alive<1, 2>(),
           "Construct a HiBlob backed by an open ISIS Cube.\n\n"
           "Parameters\n"
           "----------\n"
           "cube : Cube\n"
           "    Open ISIS Cube containing the target table.\n"
           "tblname : str\n"
           "    Name of the ISIS table (e.g. 'HiRISE Calibration Image').\n"
           "field : str\n"
           "    Name of the field inside the table to extract.\n"
           "name : str, optional\n"
           "    Label name for this blob (default 'HiBlob').")
      .def("buffer",
           [](const Isis::HiBlob &self) {
               // Convert TNT::Array2D<double> (HiMatrix) to list[list[float]]
               const auto &mat = self.buffer();
               std::vector<std::vector<double>> result;
               result.reserve(static_cast<size_t>(mat.dim1()));
               for (int r = 0; r < mat.dim1(); ++r) {
                   std::vector<double> row(mat.dim2());
                   for (int c = 0; c < mat.dim2(); ++c) {
                       row[c] = mat[r][c];
                   }
                   result.push_back(std::move(row));
               }
               return result;
           },
           "Return the HiRISE calibration data buffer as a list of rows (list[list[float]]).\n\n"
           "Requires that the blob has been loaded from a valid cube first.")
      .def("__repr__",
           [](const Isis::HiBlob &self) {
               return "HiBlob(name='" + qStringToStdString(self.getName()) +
                      "', blob_name='" + qStringToStdString(self.getBlobName()) +
                      "', field_name='" + qStringToStdString(self.getFieldName()) +
                      "', lines=" + std::to_string(self.Lines()) +
                      ", samples=" + std::to_string(self.Samples()) + ")";
           });

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
      .def("read_table",
           [](Isis::Cube &self, const std::string &name) {
             return self.readTable(stdStringToQString(name));
           },
           py::arg("name"))
      .def("write",
           static_cast<void (Isis::Cube::*)(const Isis::Table &)>(&Isis::Cube::write),
           py::arg("table"))
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

  // Added: 2026-04-09 - bind Isis::TrackingTable
  /**
   * @brief Bindings for the Isis::TrackingTable class
   * TrackingTable stores a mapping from mosaic tracking-band pixel values to
   * input image filenames and serial numbers. Used when reading or writing
   * mosaic tracking cubes.
   *
   * Source ISIS header: reference/upstream_isis/src/base/objs/TrackingTable/TrackingTable.h
   * Source class: Isis::TrackingTable
   * Source header author(s): Jesse Mapel & Summer Stapleton (2018-07-19)
   * Binding author: Geng Xun
   */
  py::class_<Isis::TrackingTable>(m, "TrackingTable")
      .def(py::init<>(), "Construct an empty TrackingTable.")
      .def(py::init<Isis::Table>(),
           py::arg("table"),
           "Construct a TrackingTable from an existing ISIS Table object.")
      .def("to_table",
           &Isis::TrackingTable::toTable,
           "Serialize this TrackingTable back to an ISIS Table object.")
      .def("pixel_to_file_name",
           [](Isis::TrackingTable &self, unsigned int pixel) {
             return self.pixelToFileName(pixel);
           },
           py::arg("pixel"),
           "Map a tracking-band pixel value to the corresponding FileName. "
           "Raises IException if pixel index is out of range.")
      .def("file_name_to_pixel",
           [](Isis::TrackingTable &self,
              const Isis::FileName &file,
              const std::string &serial_number) {
             return self.fileNameToPixel(file, stdStringToQString(serial_number));
           },
           py::arg("file"), py::arg("serial_number"),
           "Map a FileName+serial-number pair to its pixel value, "
           "adding a new entry if the pair is not yet in the table.")
      .def("file_name_to_index",
           [](Isis::TrackingTable &self,
              const Isis::FileName &file,
              const std::string &serial_number) {
             return self.fileNameToIndex(file, stdStringToQString(serial_number));
           },
           py::arg("file"), py::arg("serial_number"),
           "Return the 0-based index of a FileName+serial-number pair "
           "in the table, or -1 if not found.")
      .def("pixel_to_sn",
           [](Isis::TrackingTable &self, unsigned int pixel) {
             return qStringToStdString(self.pixelToSN(pixel));
           },
           py::arg("pixel"),
           "Map a tracking-band pixel value to the corresponding serial number string.")
      .def("__repr__", [](const Isis::TrackingTable &) {
        return "TrackingTable()";
      });
}
