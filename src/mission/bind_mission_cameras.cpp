// Binding author: Geng Xun
// Created: 2026-04-06
// Updated: 2026-04-06  Added TgoCassisCamera methods + TgoCassisDistortionMap binding
// Purpose: pybind11 bindings for mission-specific camera models and related mission helpers

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <sstream>
#include <utility>
#include <vector>

#include <QList>
#include <QPointF>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "ApolloMetricCamera.h"
#include "ApolloPanoramicCamera.h"
#include "Camera.h"
#include "Chandrayaan1M3Camera.h"
#include "ClipperNacRollingShutterCamera.h"
#include "ClipperPushBroomCamera.h"
#include "ClipperWacFcCamera.h"
#include "CrismCamera.h"
#include "Cube.h"
#include "CTXCamera.h"
#include "DawnFcCamera.h"
#include "DawnVirCamera.h"
#include "FramingCamera.h"
#include "HayabusaAmicaCamera.h"
#include "HayabusaNirsCamera.h"
#include "HiresCamera.h"
#include "HiriseCamera.h"
#include "HrscCamera.h"
#include "Hyb2OncCamera.h"
#include "Hyb2OncDistortionMap.h"
#include "IssNACamera.h"
#include "IssWACamera.h"
#include "iTime.h"
#include "JunoCamera.h"
#include "KaguyaMiCamera.h"
#include "KaguyaTcCamera.h"
#include "LineScanCamera.h"
#include "LoHighCamera.h"
#include "LoMediumCamera.h"
#include "LroNarrowAngleCamera.h"
#include "LroWideAngleCamera.h"
#include "LwirCamera.h"
#include "MarciCamera.h"
#include "Mariner10Camera.h"
#include "MdisCamera.h"
#include "MexHrscSrcCamera.h"
#include "MiniRF.h"
#include "MocNarrowAngleCamera.h"
#include "MocWideAngleCamera.h"
#include "MsiCamera.h"
#include "NewHorizonsLeisaCamera.h"
#include "NewHorizonsLorriCamera.h"
#include "NewHorizonsMvicFrameCamera.h"
#include "NewHorizonsMvicTdiCamera.h"
#include "NirCamera.h"
#include "NirsDetectorMap.h"
#include "OsirisRexOcamsCamera.h"
#include "OsirisRexTagcamsCamera.h"
#include "PushFrameCamera.h"
#include "RadarCamera.h"
#include "RosettaOsirisCamera.h"
#include "RosettaVirtisCamera.h"
#include "RollingShutterCamera.h"
#include "SsiCamera.h"
#include "TgoCassisCamera.h"
#include "TgoCassisDistortionMap.h"
#include "ThemisIrCamera.h"
#include "ThemisVisCamera.h"
#include "UvvisCamera.h"
#include "VikingCamera.h"
#include "VimsCamera.h"
#include "VoyagerCamera.h"

namespace py = pybind11;

namespace {

std::vector<std::pair<double, double>> toOffsetPairs(const QList<QPointF> &offsets) {
     std::vector<std::pair<double, double>> result;
     result.reserve(offsets.size());

     for (const QPointF &offset : offsets) {
          result.emplace_back(offset.x(), offset.y());
     }

     return result;
}

}  // namespace

void bind_mission_cameras(py::module_ &m) {
  py::class_<Isis::ApolloMetricCamera, Isis::FramingCamera>(m, "ApolloMetricCamera");
  py::class_<Isis::ApolloPanoramicCamera, Isis::LineScanCamera>(m, "ApolloPanoramicCamera");
  py::class_<Isis::IssNACamera, Isis::FramingCamera>(m, "IssNACamera");
  py::class_<Isis::IssWACamera, Isis::FramingCamera>(m, "IssWACamera");
  py::class_<Isis::VimsCamera, Isis::Camera>(m, "VimsCamera");
  py::class_<Isis::Chandrayaan1M3Camera, Isis::LineScanCamera>(m, "Chandrayaan1M3Camera");
  py::class_<Isis::HiresCamera, Isis::FramingCamera>(m, "HiresCamera");
  py::class_<Isis::LwirCamera, Isis::FramingCamera>(m, "LwirCamera");
  py::class_<Isis::NirCamera, Isis::FramingCamera>(m, "NirCamera");
  py::class_<Isis::UvvisCamera, Isis::FramingCamera>(m, "UvvisCamera");
  py::class_<Isis::ClipperNacRollingShutterCamera, Isis::RollingShutterCamera>(m, "ClipperNacRollingShutterCamera");
  py::class_<Isis::ClipperPushBroomCamera, Isis::LineScanCamera>(m, "ClipperPushBroomCamera");
  py::class_<Isis::ClipperWacFcCamera, Isis::FramingCamera>(m, "ClipperWacFcCamera");
  py::class_<Isis::DawnFcCamera, Isis::FramingCamera>(m, "DawnFcCamera");
  py::class_<Isis::DawnVirCamera, Isis::LineScanCamera>(m, "DawnVirCamera");
  py::class_<Isis::SsiCamera, Isis::FramingCamera>(m, "SsiCamera");
  py::class_<Isis::HayabusaAmicaCamera, Isis::FramingCamera>(m, "HayabusaAmicaCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Hayabusa AMICA camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::HayabusaAmicaCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::HayabusaAmicaCamera::CkFrameId)
      .def("ck_reference_id", &Isis::HayabusaAmicaCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::HayabusaAmicaCamera::SpkReferenceId);
  py::class_<Isis::HayabusaNirsCamera, Isis::FramingCamera>(m, "HayabusaNirsCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Hayabusa NIRS camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::HayabusaNirsCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::HayabusaNirsCamera::CkFrameId)
      .def("ck_reference_id", &Isis::HayabusaNirsCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::HayabusaNirsCamera::SpkReferenceId)
      .def("pixel_ifov_offsets",
           [](Isis::HayabusaNirsCamera &self) {
             return toOffsetPairs(self.PixelIfovOffsets());
           },
           "Return pixel IFOV offsets as a list of (x, y) tuples in focal-plane units.");
  py::class_<Isis::Hyb2OncCamera, Isis::FramingCamera>(m, "Hyb2OncCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Hayabusa2 ONC camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::Hyb2OncCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::Hyb2OncCamera::CkFrameId)
      .def("ck_reference_id", &Isis::Hyb2OncCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::Hyb2OncCamera::SpkReferenceId);
  py::class_<Isis::NirsDetectorMap, Isis::CameraDetectorMap>(m, "NirsDetectorMap")
      .def(py::init<double, Isis::Camera *>(),
           py::arg("exposure_duration"),
           py::arg("parent") = nullptr,
           py::keep_alive<1, 3>(),
           "Construct the Hayabusa NIRS detector map helper.")
      .def("set_exposure_duration",
           &Isis::NirsDetectorMap::setExposureDuration,
           py::arg("exposure_duration"),
           "Update the constant exposure duration returned by the detector map.")
      .def("exposure_duration",
           &Isis::NirsDetectorMap::exposureDuration,
           py::arg("sample"),
           py::arg("line"),
           py::arg("band"),
           "Return the configured exposure duration for the provided detector position.");
  py::class_<Isis::Hyb2OncDistortionMap, Isis::CameraDistortionMap>(m, "Hyb2OncDistortionMap")
      .def(py::init<Isis::Camera *, double>(),
           py::arg("parent"),
           py::arg("z_direction") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the Hayabusa2 ONC distortion map helper.")
      .def("set_focal_plane",
           &Isis::Hyb2OncDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::Hyb2OncDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::Hyb2OncDistortionMap &) {
        std::ostringstream stream;
        stream << "<Hyb2OncDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::JunoCamera, Isis::FramingCamera>(m, "JunoCamera");
  py::class_<Isis::KaguyaMiCamera, Isis::LineScanCamera>(m, "KaguyaMiCamera");
  py::class_<Isis::KaguyaTcCamera, Isis::LineScanCamera>(m, "KaguyaTcCamera");
  py::class_<Isis::LoHighCamera, Isis::FramingCamera>(m, "LoHighCamera");
  py::class_<Isis::LoMediumCamera, Isis::FramingCamera>(m, "LoMediumCamera");
  py::class_<Isis::LroNarrowAngleCamera, Isis::LineScanCamera>(m, "LroNarrowAngleCamera")
      .def("ck_frame_id", &Isis::LroNarrowAngleCamera::CkFrameId,
           "CK frame ID - Instrument Code from spacit run on CK")
      .def("ck_reference_id", &Isis::LroNarrowAngleCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::LroNarrowAngleCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::LroWideAngleCamera, Isis::PushFrameCamera>(m, "LroWideAngleCamera")
      .def("set_band", &Isis::LroWideAngleCamera::SetBand,
           py::arg("band"),
           "Set the band for camera model calculations.\n\n"
           "Each band may have different focal length, boresight, and distortion parameters.\n\n"
           "Args:\n"
           "    band: Band number (1-based)")
      .def("is_band_independent", &Isis::LroWideAngleCamera::IsBandIndependent,
           "Check if camera parameters are band-independent.\n\n"
           "Returns:\n"
           "    True if parameters vary by band, False otherwise")
      .def("ck_frame_id", &Isis::LroWideAngleCamera::CkFrameId,
           "CK frame ID - Instrument Code from spacit run on CK")
      .def("ck_reference_id", &Isis::LroWideAngleCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::LroWideAngleCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::MiniRF, Isis::RadarCamera>(m, "MiniRF")
      .def("ck_frame_id", &Isis::MiniRF::CkFrameId,
           "CK frame ID - throws exception as CK cannot be generated for MiniRF")
      .def("ck_reference_id", &Isis::MiniRF::CkReferenceId,
           "CK Reference ID - throws exception as CK cannot be generated for MiniRF")
      .def("spk_target_id", &Isis::MiniRF::SpkTargetId,
           "SPK Target Body ID - Lunar Reconnaissance Orbiter spacecraft")
      .def("spk_reference_id", &Isis::MiniRF::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::Mariner10Camera, Isis::FramingCamera>(m, "Mariner10Camera");
  py::class_<Isis::MdisCamera, Isis::FramingCamera>(m, "MdisCamera");
  py::class_<Isis::HrscCamera, Isis::LineScanCamera>(m, "HrscCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an HRSC line-scan camera model from an opened Cube.")
      .def("ck_frame_id", &Isis::HrscCamera::CkFrameId,
           "CK frame ID - Instrument Code from spacit run on CK")
      .def("ck_reference_id", &Isis::HrscCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::HrscCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::MexHrscSrcCamera, Isis::FramingCamera>(m, "MexHrscSrcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Mars Express HRSC SRC framing camera model from an opened Cube.")
      .def("shutter_open_close_times", &Isis::MexHrscSrcCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times for the given center exposure time.")
      .def("ck_frame_id", &Isis::MexHrscSrcCamera::CkFrameId,
           "CK frame ID - Instrument Code from spacit run on CK")
      .def("ck_reference_id", &Isis::MexHrscSrcCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::MexHrscSrcCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::MocNarrowAngleCamera, Isis::LineScanCamera>(m, "MocNarrowAngleCamera");
  py::class_<Isis::MocWideAngleCamera, Isis::LineScanCamera>(m, "MocWideAngleCamera")
      .def("ck_frame_id", &Isis::MocWideAngleCamera::CkFrameId,
           "CK frame ID - Instrument Code from spacit run on CK")
      .def("ck_reference_id", &Isis::MocWideAngleCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::MocWideAngleCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::HiriseCamera, Isis::LineScanCamera>(m, "HiriseCamera");
  py::class_<Isis::CTXCamera, Isis::LineScanCamera>(m, "CTXCamera");
  py::class_<Isis::CrismCamera, Isis::LineScanCamera>(m, "CrismCamera");
  py::class_<Isis::MarciCamera, Isis::PushFrameCamera>(m, "MarciCamera");
  py::class_<Isis::MsiCamera, Isis::FramingCamera>(m, "MsiCamera");
  py::class_<Isis::NewHorizonsLeisaCamera, Isis::LineScanCamera>(m, "NewHorizonsLeisaCamera");
  py::class_<Isis::NewHorizonsLorriCamera, Isis::FramingCamera>(m, "NewHorizonsLorriCamera");
  py::class_<Isis::NewHorizonsMvicFrameCamera, Isis::FramingCamera>(m, "NewHorizonsMvicFrameCamera");
  py::class_<Isis::NewHorizonsMvicTdiCamera, Isis::LineScanCamera>(m, "NewHorizonsMvicTdiCamera");
  py::class_<Isis::ThemisIrCamera, Isis::LineScanCamera>(m, "ThemisIrCamera");
  py::class_<Isis::ThemisVisCamera, Isis::PushFrameCamera>(m, "ThemisVisCamera");
  py::class_<Isis::OsirisRexOcamsCamera, Isis::FramingCamera>(m, "OsirisRexOcamsCamera");
  py::class_<Isis::OsirisRexTagcamsCamera, Isis::FramingCamera>(m, "OsirisRexTagcamsCamera");
  py::class_<Isis::RosettaOsirisCamera, Isis::FramingCamera>(m, "RosettaOsirisCamera");
  py::class_<Isis::RosettaVirtisCamera, Isis::LineScanCamera>(m, "RosettaVirtisCamera");
  py::class_<Isis::TgoCassisCamera, Isis::FramingCamera>(m, "TgoCassisCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a TGO CaSSIS framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::TgoCassisCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::TgoCassisCamera::CkFrameId,
           "CK frame ID - TGO CaSSIS instrument code (TGO_CASSIS_FSA)")
      .def("ck_reference_id", &Isis::TgoCassisCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_target_id", &Isis::TgoCassisCamera::SpkTargetId,
           "SPK Target Body ID - TGO spacecraft (-143)")
      .def("spk_reference_id", &Isis::TgoCassisCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::TgoCassisDistortionMap, Isis::CameraDistortionMap>(m, "TgoCassisDistortionMap")
      .def(py::init<Isis::Camera *, int>(),
           py::arg("parent"),
           py::arg("naif_ik_code"),
           py::keep_alive<1, 2>(),
           "Construct the TGO CaSSIS rational distortion map.\n\n"
           "Args:\n"
           "    parent: Pointer to the parent Camera object\n"
           "    naif_ik_code: NAIF IK code for the instrument")
      .def("set_focal_plane",
           &Isis::TgoCassisDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Compute undistorted focal plane (x,y) from distorted (x,y).\n\n"
           "Args:\n"
           "    dx: Distorted focal plane x, in millimeters\n"
           "    dy: Distorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("set_undistorted_focal_plane",
           &Isis::TgoCassisDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Compute distorted focal plane (x,y) from undistorted (x,y).\n\n"
           "Args:\n"
           "    ux: Undistorted focal plane x, in millimeters\n"
           "    uy: Undistorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("__repr__", [](const Isis::TgoCassisDistortionMap &) {
        std::ostringstream stream;
        stream << "<TgoCassisDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::VikingCamera, Isis::FramingCamera>(m, "VikingCamera");
  py::class_<Isis::VoyagerCamera, Isis::FramingCamera>(m, "VoyagerCamera");
}
