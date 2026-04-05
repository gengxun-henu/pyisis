// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocNarrowAngleSumming/MocNarrowAngleSumming.h
// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocWideAngleCamera/MocWideAngleDistortionMap.h
// Source class: MocNarrowAngleSumming, MocWideAngleDistortionMap
// Source header author(s): not explicitly stated in upstream header
// Binding author: Geng Xun
// Created: 2026-04-05
// Updated: 2026-04-05
// Purpose: pybind11 bindings for Mars Global Surveyor MOC utilities
// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocLabels/MocLabels.h
// Source ISIS header: reference/upstream_isis/src/mgs/objs/MocWideAngleCamera/MocWideAngleDetectorMap.h
// Source classes: MocNarrowAngleSumming, MocLabels, MocWideAngleDetectorMap
// Source header author(s): not explicitly stated in upstream headers
// Binding author: Geng Xun
// Created: 2026-04-05
// Updated: 2026-04-05
// Purpose: pybind11 bindings for Mars Global Surveyor MOC utilities including narrow angle summing, labels, and wide angle detector map

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <sstream>

#include "Camera.h"
#include "Cube.h"
#include "LineScanCameraDetectorMap.h"
#include "MocLabels.h"
#include "MocNarrowAngleSumming.h"
#include "MocWideAngleDistortionMap.h"
#include "Camera.h"
#include "MocWideAngleDetectorMap.h"
#include "helpers.h"

namespace py = pybind11;

void bind_mgs_utilities(py::module_ &m) {
  // MocNarrowAngleSumming - Mars Global Surveyor MOC narrow angle summing class
  // Provides sample/detector coordinate transformations for MOC narrow angle camera
  py::class_<Isis::MocNarrowAngleSumming>(m, "MocNarrowAngleSumming")
    .def(py::init<int, int>(),
      py::arg("csum"),
      py::arg("ss"),
      "Constructs the MocNarrowAngleSumming object.\n\n"
      "Args:\n"
      "    csum: Cross-track summing mode\n"
      "    ss: Starting sample")

    .def("detector", &Isis::MocNarrowAngleSumming::Detector,
      py::arg("sample"),
      "Given the sample value, computes the corresponding detector.\n\n"
      "Args:\n"
      "    sample: Sample position\n\n"
      "Returns:\n"
      "    Detector position")

    .def("sample", &Isis::MocNarrowAngleSumming::Sample,
      py::arg("detector"),
      "Given the detector value, computes the corresponding sample.\n\n"
      "Args:\n"
      "    detector: Detector position\n\n"
      "Returns:\n"
      "    Sample position")

    .def("__repr__", [](const Isis::MocNarrowAngleSumming &self) {
      std::ostringstream oss;
      oss << "<MocNarrowAngleSumming>";
      return oss.str();
    });

  // MocWideAngleDistortionMap - Mars Global Surveyor MOC wide angle distortion map
  // Inherits from CameraDistortionMap (already bound in bind_camera_maps.cpp)
  // Provides distortion/undistortion for MOC wide angle camera with red/non-red filter variants
  py::class_<Isis::MocWideAngleDistortionMap, Isis::CameraDistortionMap>(m, "MocWideAngleDistortionMap")
    .def(py::init<Isis::Camera*, bool>(),
      py::arg("parent"),
      py::arg("red"),
      py::keep_alive<1, 2>(),
      "Constructs the MocWideAngleDistortionMap object.\n\n"
      "Args:\n"
      "    parent: Pointer to the parent Camera object\n"
      "    red: True if using red filter, False otherwise")

    .def("set_focal_plane",
      &Isis::MocWideAngleDistortionMap::SetFocalPlane,
      py::arg("dx"),
      py::arg("dy"),
      "Apply distortion to focal plane coordinates.\n\n"
      "Args:\n"
      "    dx: Distorted focal plane x coordinate\n"
      "    dy: Distorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("set_undistorted_focal_plane",
      &Isis::MocWideAngleDistortionMap::SetUndistortedFocalPlane,
      py::arg("ux"),
      py::arg("uy"),
      "Remove distortion from focal plane coordinates.\n\n"
      "Args:\n"
      "    ux: Undistorted focal plane x coordinate\n"
      "    uy: Undistorted focal plane y coordinate\n\n"
      "Returns:\n"
      "    True if successful")

    .def("__repr__", [](const Isis::MocWideAngleDistortionMap &self) {
      std::ostringstream oss;
      oss << "<MocWideAngleDistortionMap>";
  // MocLabels - Mars Global Surveyor MOC label reader class
  // Reads and provides access to MOC instrument label values
  py::class_<Isis::MocLabels>(m, "MocLabels")
    .def(py::init<Isis::Cube &>(),
      py::arg("cube"),
      py::keep_alive<1, 2>(),
      "Constructs MocLabels from a Cube.\n\n"
      "Args:\n"
      "    cube: Cube object containing MOC labels")

    .def(py::init([](const std::string &file) {
      return new Isis::MocLabels(QString::fromStdString(file));
    }),
      py::arg("file"),
      "Constructs MocLabels from a file path.\n\n"
      "Args:\n"
      "    file: Path to file containing MOC labels")

    .def("narrow_angle", &Isis::MocLabels::NarrowAngle,
      "Indicates whether the camera was narrow angle.\n\n"
      "Returns:\n"
      "    True if instrument ID is MOC-NA")

    .def("wide_angle", &Isis::MocLabels::WideAngle,
      "Indicates whether the camera was wide angle.\n\n"
      "Returns:\n"
      "    True if instrument ID is MOC-WA")

    .def("wide_angle_red", &Isis::MocLabels::WideAngleRed,
      "Indicates whether the camera was red wide angle.\n\n"
      "Returns:\n"
      "    True if instrument ID is MOC-WA and filter name is RED")

    .def("wide_angle_blue", &Isis::MocLabels::WideAngleBlue,
      "Indicates whether the camera was blue wide angle.\n\n"
      "Returns:\n"
      "    True if instrument ID is MOC-WA and filter name is BLUE")

    .def("crosstrack_summing", &Isis::MocLabels::CrosstrackSumming,
      "Returns value for CrosstrackSumming from the instrument group.\n\n"
      "Returns:\n"
      "    Crosstrack summing mode")

    .def("downtrack_summing", &Isis::MocLabels::DowntrackSumming,
      "Returns value for DowntrackSumming from the instrument group.\n\n"
      "Returns:\n"
      "    Downtrack summing mode")

    .def("first_line_sample", &Isis::MocLabels::FirstLineSample,
      "Returns value for FirstLineSample from the instrument group.\n\n"
      "Returns:\n"
      "    First line sample")

    .def("focal_plane_temperature", &Isis::MocLabels::FocalPlaneTemperature,
      "Returns value for FocalPlaneTemperature from the instrument group.\n\n"
      "Returns:\n"
      "    Focal plane temperature")

    .def("line_rate", &Isis::MocLabels::LineRate,
      "Returns the value for the true line rate.\n\n"
      "Returns:\n"
      "    True line rate calculated from LineExposureDuration and DowntrackSumming")

    .def("exposure_duration", &Isis::MocLabels::ExposureDuration,
      "Returns the value for LineExposureDuration from the instrument group.\n\n"
      "Returns:\n"
      "    Line exposure duration")

    .def("start_time", [](const Isis::MocLabels &self) {
      return qstring_to_string(self.StartTime());
    },
      "Returns the value for StartTime from the instrument group.\n\n"
      "Returns:\n"
      "    Start time string")

    .def("detectors", &Isis::MocLabels::Detectors,
      "Returns 2048 if narrow angle and 3456 if wide angle.\n\n"
      "Returns:\n"
      "    Number of detectors")

    .def("start_detector", &Isis::MocLabels::StartDetector,
      py::arg("sample"),
      "Returns the starting detector for a given sample.\n\n"
      "Args:\n"
      "    sample: Sample position\n\n"
      "Returns:\n"
      "    Starting detector position")

    .def("end_detector", &Isis::MocLabels::EndDetector,
      py::arg("sample"),
      "Returns the ending detector for a given sample.\n\n"
      "Args:\n"
      "    sample: Sample position\n\n"
      "Returns:\n"
      "    Ending detector position")

    .def("sample", &Isis::MocLabels::Sample,
      py::arg("detector"),
      "Returns the sample position for a given detector.\n\n"
      "Args:\n"
      "    detector: Detector position\n\n"
      "Returns:\n"
      "    Sample position")

    .def("ephemeris_time", &Isis::MocLabels::EphemerisTime,
      py::arg("line"),
      "Returns the ephemeris time for a given line.\n\n"
      "Args:\n"
      "    line: Line number\n\n"
      "Returns:\n"
      "    Ephemeris time in seconds")

    .def("gain", &Isis::MocLabels::Gain,
      py::arg("line") = 1,
      "Returns the gain for a given line.\n\n"
      "Args:\n"
      "    line: Line number (default: 1)\n\n"
      "Returns:\n"
      "    Gain value")

    .def("offset", &Isis::MocLabels::Offset,
      py::arg("line") = 1,
      "Returns the offset for a given line.\n\n"
      "Args:\n"
      "    line: Line number (default: 1)\n\n"
      "Returns:\n"
      "    Offset value")

    .def("__repr__", [](const Isis::MocLabels &self) {
      std::ostringstream oss;
      oss << "<MocLabels ";
      if (self.NarrowAngle()) {
        oss << "narrow_angle";
      } else if (self.WideAngleRed()) {
        oss << "wide_angle_red";
      } else if (self.WideAngleBlue()) {
        oss << "wide_angle_blue";
      } else {
        oss << "wide_angle";
      }
      oss << " csum=" << self.CrosstrackSumming();
      oss << " dsum=" << self.DowntrackSumming();
      oss << ">";
      return oss.str();
    });

  // MocWideAngleDetectorMap - Mars Global Surveyor MOC wide angle detector map
  // Converts between parent image coordinates and detector coordinates for MOC wide angle camera
  // Handles variable summing modes (crosstrack summing of 13 or 27)
  py::class_<Isis::MocWideAngleDetectorMap, Isis::LineScanCameraDetectorMap>(m, "MocWideAngleDetectorMap")
    .def(py::init<Isis::Camera *, const double, const double, Isis::MocLabels *>(),
      py::arg("parent") = nullptr,
      py::arg("et_start"),
      py::arg("line_rate"),
      py::arg("moclab"),
      py::keep_alive<1, 2>(),  // Keep Camera alive
      py::keep_alive<1, 5>(),  // Keep MocLabels alive
      "Constructs a MocWideAngleDetectorMap for line scan cameras.\n\n"
      "Args:\n"
      "    parent: Parent Camera model\n"
      "    et_start: Starting ephemeris time in seconds at the top of the first line\n"
      "    line_rate: Time in seconds between lines\n"
      "    moclab: MOC labels to use for camera creation")

    .def("set_parent",
      &Isis::MocWideAngleDetectorMap::SetParent,
      py::arg("sample"),
      py::arg("line"),
      "Converts parent sample/line to detector sample/line.\n\n"
      "Handles variable summing for crosstrack summing modes 13 and 27.\n\n"
      "Args:\n"
      "    sample: Parent sample coordinate\n"
      "    line: Parent line coordinate\n\n"
      "Returns:\n"
      "    True if conversion successful")

    .def("set_detector",
      &Isis::MocWideAngleDetectorMap::SetDetector,
      py::arg("sample"),
      py::arg("line"),
      "Converts detector sample/line to parent sample/line.\n\n"
      "Handles variable summing for crosstrack summing modes 13 and 27.\n\n"
      "Args:\n"
      "    sample: Detector sample coordinate\n"
      "    line: Detector line coordinate\n\n"
      "Returns:\n"
      "    True if conversion successful")

    .def("__repr__", [](const Isis::MocWideAngleDetectorMap &self) {
      std::ostringstream oss;
      oss << "<MocWideAngleDetectorMap et_start=" << self.StartTime()
          << " line_rate=" << self.LineRate() << ">";
      return oss.str();
    });
}
