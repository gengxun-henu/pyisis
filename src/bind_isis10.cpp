// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/10.0.0/isis/src/base/objs/IProj/IProj.h
// - reference/upstream_isis/10.0.0/isis/src/chandrayaan2/objs/Chandrayaan2OhrcCamera/Chandrayaan2OhrcCamera.h
// - reference/upstream_isis/10.0.0/isis/src/chandrayaan2/objs/Chandrayaan2TmcCamera/Chandrayaan2TmcCamera.h
// - reference/upstream_isis/10.0.0/isis/src/osirisrex/objs/OsirisRexOcamsCamera/OsirisRexOcamsOpenCVDistortionMap.h
// - reference/upstream_isis/10.0.0/isis/src/base/objs/ImageIoHandler/ImageIoHandler.h
// - reference/upstream_isis/10.0.0/isis/src/base/objs/ImageIoHandler/GdalIoHandler.h
// - reference/upstream_isis/10.0.0/isis/src/base/apps/csv2table/csv2table.h
// Source classes: IProj, Chandrayaan2OhrcCamera, Chandrayaan2TmcCamera,
// OsirisRexOcamsOpenCVDistortionMap, ImageIoHandler, GdalIoHandler
// Source function: csv2table
// Source header author(s): Adam Paquette for IProj; Kris Becker for
// OsirisRexOcamsOpenCVDistortionMap; Jai Rideout and Steven Lambright for
// ImageIoHandler; Adam Paquette for GdalIoHandler; not explicitly stated for
// the camera headers
// Binding author: Geng Xun
// Created: 2026-07-23
// Updated: 2026-07-23  Geng Xun added the first ISIS 10-only non-GUI binding batch.
// Updated: 2026-07-24  Geng Xun added the ISIS 10-only OCAMS OpenCV distortion model.
// Updated: 2026-07-24  Geng Xun added safe ISIS 10 GDAL image-I/O bindings.
// Updated: 2026-08-02  Geng Xun added the Linux ISIS 10 csv2table native adapter.
// Purpose: Expose stable ISIS 10-only projection, camera, distortion, image-I/O, and table APIs.

#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#ifdef PYISIS_ISIS10_API
#include <QList>
#ifndef _WIN32
#include <QVector>
#endif

#include "CameraDistortionMap.h"
#include "Chandrayaan2OhrcCamera.h"
#include "Chandrayaan2TmcCamera.h"
#include "Cube.h"
#ifndef _WIN32
#include "csv2table.h"
#include "FileName.h"
#endif
#include "GdalIoHandler.h"
#include "helpers.h"
#include "ImageIoHandler.h"
#include "IProj.h"
#include "LineScanCamera.h"
#include "OsirisRexOcamsOpenCVDistortionMap.h"
#include "PixelType.h"
#include "Pvl.h"
#include "TProjection.h"
#ifndef _WIN32
#include "UserInterface.h"
#endif
#endif

namespace py = pybind11;

#ifdef PYISIS_ISIS10_API
namespace {

QList<int> toVirtualBandList(const std::vector<int> &virtualBands) {
  QList<int> result;
  for (int band : virtualBands) {
    if (band < 1) {
      throw py::value_error("virtual band numbers must be positive and 1-based");
    }
    result.append(band);
  }
  return result;
}

std::unique_ptr<Isis::GdalIoHandler> makeGdalIoHandler(
    const std::string &dataFilePath,
    const std::vector<int> &virtualBands,
    Isis::PixelType pixelType,
    bool writable) {
  if (!std::filesystem::is_regular_file(dataFilePath)) {
    throw py::value_error("data_file_path does not identify an existing file");
  }

  GDALAllRegister();

  const GDALAccess access = writable ? GA_Update : GA_ReadOnly;
  GDALDatasetH preflight = GDALOpen(dataFilePath.c_str(), access);
  if (preflight == nullptr) {
    throw py::value_error(
        "GDAL could not open data_file_path with the requested access");
  }

  const int rasterBandCount = GDALGetRasterCount(preflight);
  for (int band : virtualBands) {
    if (band < 1 || band > rasterBandCount) {
      GDALClose(preflight);
      throw py::value_error(
          "virtual band number is outside the GDAL dataset band range");
    }
  }
  GDALClose(preflight);

  const GDALDataType gdalPixelType = Isis::IsisPixelToGdal(pixelType);
  if (gdalPixelType == GDT_Unknown) {
    throw py::value_error("pixel_type is not supported by GdalIoHandler");
  }

  QString path = stdStringToQString(dataFilePath);
  QList<int> bands = toVirtualBandList(virtualBands);
  return std::make_unique<Isis::GdalIoHandler>(
      path,
      bands.empty() ? nullptr : &bands,
      gdalPixelType,
      access);
}

void setImageIoVirtualBands(
    Isis::ImageIoHandler &handler,
    const std::vector<int> &virtualBands) {
  QList<int> bands = toVirtualBandList(virtualBands);
  handler.setVirtualBands(bands.empty() ? nullptr : &bands);
}

#ifndef _WIN32
void runCsv2TableNative(const std::vector<std::string> &arguments) {
  QVector<QString> uiArguments;
  uiArguments.reserve(static_cast<int>(arguments.size()));
  for (const std::string &argument : arguments) {
    uiArguments.append(stdStringToQString(argument));
  }

  const QString xmlPath =
      Isis::FileName("$ISIS_PREFIX/bin/xml/csv2table.xml").expanded();
  Isis::UserInterface ui(xmlPath, uiArguments);
  Isis::csv2table(ui, nullptr);
}
#endif

}  // namespace
#endif

void bind_isis10(py::module_ &m) {
#ifdef PYISIS_ISIS10_API
#ifndef _WIN32
  m.def("_csv2table_native",
        &runCsv2TableNative,
        py::arg("arguments"),
        "Run the ISIS 10 csv2table implementation with normalized UI arguments.");
#endif

  py::class_<Isis::ImageIoHandler>(m, "ImageIoHandler")
      .def("read", &Isis::ImageIoHandler::read, py::arg("buffer"))
      .def("write", &Isis::ImageIoHandler::write, py::arg("buffer"))
      .def("get_data_size", &Isis::ImageIoHandler::getDataSize)
      .def("set_virtual_bands",
           &setImageIoVirtualBands,
           py::arg("virtual_bands"))
      .def("update_labels",
           &Isis::ImageIoHandler::updateLabels,
           py::arg("labels"));

  py::class_<Isis::GdalIoHandler, Isis::ImageIoHandler>(m, "GdalIoHandler")
      .def(py::init(&makeGdalIoHandler),
           py::arg("data_file_path"),
           py::arg("virtual_bands") = std::vector<int>{},
           py::arg("pixel_type") = Isis::PixelType::Double,
           py::arg("writable") = false,
           "Open an existing GDAL-supported raster through the ISIS 10 image-I/O backend.")
      .def("read", &Isis::GdalIoHandler::read, py::arg("buffer"))
      .def("write", &Isis::GdalIoHandler::write, py::arg("buffer"))
      .def("get_data_size", &Isis::GdalIoHandler::getDataSize)
      .def("update_labels",
           &Isis::GdalIoHandler::updateLabels,
           py::arg("labels"))
      .def("clear_cache",
           &Isis::GdalIoHandler::clearCache,
           py::arg("block_for_write_cache") = false);

  py::class_<Isis::IProj, Isis::TProjection>(m, "IProj")
      .def(py::init<Isis::Pvl &, bool>(),
           py::arg("label"),
           py::arg("allow_defaults") = false)
      .def("name", [](const Isis::IProj &self) {
        return qStringToStdString(self.Name());
      })
      .def("version", [](const Isis::IProj &self) {
        return qStringToStdString(self.Version());
      })
      .def("mapping", &Isis::IProj::Mapping)
      .def("set_ground",
           &Isis::IProj::SetGround,
           py::arg("lat"),
           py::arg("lon"))
      .def("set_coordinate",
           &Isis::IProj::SetCoordinate,
           py::arg("x"),
           py::arg("y"))
      .def("xy_range", [](Isis::IProj &self) {
        double minX;
        double maxX;
        double minY;
        double maxY;
        if (!self.XYRange(minX, maxX, minY, maxY)) {
          throw std::runtime_error("Failed to compute XY range");
        }
        return py::make_tuple(minX, maxX, minY, maxY);
      });

  py::class_<Isis::OsirisRexOcamsOpenCVDistortionMap,
             Isis::CameraDistortionMap>(
      m, "OsirisRexOcamsOpenCVDistortionMap")
      .def(py::init([](Isis::Camera *parent,
                       int naifIkCode,
                       int functionIkCode,
                       const std::string &filterName,
                       double zDirection) {
             if (parent == nullptr) {
               throw py::value_error("parent must be a valid Camera");
             }
             return std::make_unique<Isis::OsirisRexOcamsOpenCVDistortionMap>(
                 parent,
                 naifIkCode,
                 functionIkCode,
                 stdStringToQString(filterName),
                 zDirection);
           }),
           py::arg("parent"),
           py::arg("naif_ik_code"),
           py::arg("function_ik_code"),
           py::arg("filter_name") = "",
           py::arg("z_direction") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the ISIS 10 OSIRIS-REx OCAMS OpenCV distortion model.")
      .def("set_camera_temperature",
           &Isis::OsirisRexOcamsOpenCVDistortionMap::SetCameraTemperature,
           py::arg("temperature_celsius"))
      .def("set_focal_plane",
           &Isis::OsirisRexOcamsOpenCVDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::OsirisRexOcamsOpenCVDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"));

  py::class_<Isis::Chandrayaan2OhrcCamera, Isis::LineScanCamera>(
      m, "Chandrayaan2OhrcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Chandrayaan-2 OHRC camera model from an opened cube.")
      .def("ck_frame_id", &Isis::Chandrayaan2OhrcCamera::CkFrameId)
      .def("ck_reference_id", &Isis::Chandrayaan2OhrcCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::Chandrayaan2OhrcCamera::SpkReferenceId);

  py::class_<Isis::Chandrayaan2TmcCamera, Isis::LineScanCamera>(
      m, "Chandrayaan2TmcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Chandrayaan-2 TMC-2 camera model from an opened cube.")
      .def("ck_frame_id", &Isis::Chandrayaan2TmcCamera::CkFrameId)
      .def("ck_reference_id", &Isis::Chandrayaan2TmcCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::Chandrayaan2TmcCamera::SpkReferenceId);
#else
  (void)m;
#endif
}
