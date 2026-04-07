// Binding author: Geng Xun
// Created: 2026-04-06
// Updated: 2026-04-07  Added Rosetta mission bindings (RosettaOsirisCamera, RosettaVirtisCamera, RosettaOsirisCameraDistortionMap) and completed VoyagerCamera binding
// Updated: 2026-04-07  Added complete OSIRIS-REx mission bindings (OsirisRexOcamsCamera, OsirisRexTagcamsCamera, OsirisRexDistortionMap, OsirisRexTagcamsDistortionMap) and Rosetta mission bindings
// Updated: 2026-04-07  Completed Viking, Mars Odyssey, Messenger Taylor distortion, and Mariner mission bindings
// Updated: 2026-04-07  Added Lunar Orbiter camera bindings (LoHighCamera, LoMediumCamera) with fiducial and distortion map helpers
// Updated: 2026-04-07  Added New Horizons mission camera and distortion helper bindings
// Updated: 2026-04-07  Completed Apollo, Cassini, Chandrayaan-1, Clementine, Clipper, Galileo, and Juno mission camera/helper bindings
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
#include "ApolloMetricDistortionMap.h"
#include "ApolloPanoramicCamera.h"
#include "ApolloPanoramicDetectorMap.h"
#include "Camera.h"
#include "Chandrayaan1M3Camera.h"
#include "Chandrayaan1M3DistortionMap.h"
#include "ClipperNacRollingShutterCamera.h"
#include "ClipperPushBroomCamera.h"
#include "ClipperWacFcCamera.h"
#include "ClementineUvvisDistortionMap.h"
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
#include "JunoDistortionMap.h"
#include "KaguyaMiCamera.h"
#include "KaguyaTcCamera.h"
#include "Latitude.h"
#include "LineScanCamera.h"
#include "LoCameraFiducialMap.h"
#include "LoHighCamera.h"
#include "LoHighDistortionMap.h"
#include "Longitude.h"
#include "LoMediumCamera.h"
#include "LoMediumDistortionMap.h"
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
#include "NewHorizonsLorriDistortionMap.h"
#include "NewHorizonsMvicFrameCamera.h"
#include "NewHorizonsMvicFrameCameraDistortionMap.h"
#include "NewHorizonsMvicTdiCamera.h"
#include "NewHorizonsMvicTdiCameraDistortionMap.h"
#include "NirCamera.h"
#include "NirsDetectorMap.h"
#include "OsirisRexOcamsCamera.h"
#include "OsirisRexDistortionMap.h"
#include "OsirisRexTagcamsCamera.h"
#include "OsirisRexTagcamsDistortionMap.h"
#include "Pvl.h"
#include "PushFrameCamera.h"
#include "RadarCamera.h"
#include "RosettaOsirisCamera.h"
#include "RosettaOsirisCameraDistortionMap.h"
#include "RosettaVirtisCamera.h"
#include "RollingShutterCamera.h"
#include "SsiCamera.h"
#include "SurfacePoint.h"
#include "TgoCassisCamera.h"
#include "TgoCassisDistortionMap.h"
#include "TaylorCameraDistortionMap.h"
#include "ThemisIrCamera.h"
#include "ThemisIrDistortionMap.h"
#include "ThemisVisCamera.h"
#include "ThemisVisDistortionMap.h"
#include "UvvisCamera.h"
#include "VikingCamera.h"
#include "VimsCamera.h"
#include "VimsGroundMap.h"
#include "VimsSkyMap.h"
#include "VoyagerCamera.h"
#include "PvlGroup.h"

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
  py::class_<Isis::ApolloMetricCamera, Isis::FramingCamera>(m, "ApolloMetricCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an Apollo metric framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::ApolloMetricCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::ApolloMetricCamera::CkFrameId)
      .def("ck_reference_id", &Isis::ApolloMetricCamera::CkReferenceId)
      .def("spk_target_id", &Isis::ApolloMetricCamera::SpkTargetId)
      .def("spk_reference_id", &Isis::ApolloMetricCamera::SpkReferenceId);
  py::class_<Isis::ApolloMetricDistortionMap, Isis::CameraDistortionMap>(m, "ApolloMetricDistortionMap")
      .def(py::init<Isis::Camera *, double, double, double, double, double, double, double, double>(),
           py::arg("parent"),
           py::arg("xp"),
           py::arg("yp"),
           py::arg("k1"),
           py::arg("k2"),
           py::arg("k3"),
           py::arg("j1"),
           py::arg("j2"),
           py::arg("t0"),
           py::keep_alive<1, 2>(),
           "Construct the Apollo metric camera distortion-map helper.")
      .def("set_focal_plane",
           &Isis::ApolloMetricDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::ApolloMetricDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"));
  py::class_<Isis::ApolloPanoramicCamera, Isis::LineScanCamera>(m, "ApolloPanoramicCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an Apollo panoramic line-scan camera model from an opened cube.")
      .def("ck_frame_id", &Isis::ApolloPanoramicCamera::CkFrameId)
      .def("ck_reference_id", &Isis::ApolloPanoramicCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::ApolloPanoramicCamera::SpkReferenceId)
      .def("int_ori_residuals_report", &Isis::ApolloPanoramicCamera::intOriResidualsReport)
      .def("int_ori_residual_max", &Isis::ApolloPanoramicCamera::intOriResidualMax)
      .def("int_ori_residual_mean", &Isis::ApolloPanoramicCamera::intOriResidualMean)
      .def("int_ori_residual_stdev", &Isis::ApolloPanoramicCamera::intOriResidualStdev);
  py::class_<Isis::ApolloPanoramicDetectorMap, Isis::CameraDetectorMap>(m, "ApolloPanoramicDetectorMap")
      .def(py::init<Isis::Camera *, double, double, Isis::Pvl *>(),
           py::arg("parent"),
           py::arg("et_middle"),
           py::arg("line_rate"),
           py::arg("labels"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 5>(),
           "Construct the Apollo panoramic detector-map helper.")
      .def("set_parent",
           &Isis::ApolloPanoramicDetectorMap::SetParent,
           py::arg("sample"),
           py::arg("line"))
      .def("set_detector",
           &Isis::ApolloPanoramicDetectorMap::SetDetector,
           py::arg("sample"),
           py::arg("line"))
      .def("set_line_rate",
           &Isis::ApolloPanoramicDetectorMap::SetLineRate,
           py::arg("line_rate"))
      .def("line_rate", &Isis::ApolloPanoramicDetectorMap::LineRate)
      .def("mean_residual", &Isis::ApolloPanoramicDetectorMap::meanResidual)
      .def("max_residual", &Isis::ApolloPanoramicDetectorMap::maxResidual)
      .def("stdev_residual", &Isis::ApolloPanoramicDetectorMap::stdevResidual);
  py::class_<Isis::IssNACamera, Isis::FramingCamera>(m, "IssNACamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Cassini ISS narrow-angle framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::IssNACamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::IssNACamera::CkFrameId)
      .def("ck_reference_id", &Isis::IssNACamera::CkReferenceId)
      .def("spk_reference_id", &Isis::IssNACamera::SpkReferenceId);
  py::class_<Isis::IssWACamera, Isis::FramingCamera>(m, "IssWACamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Cassini ISS wide-angle framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::IssWACamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::IssWACamera::CkFrameId)
      .def("ck_reference_id", &Isis::IssWACamera::CkReferenceId)
      .def("spk_reference_id", &Isis::IssWACamera::SpkReferenceId);
  py::class_<Isis::VimsCamera, Isis::Camera>(m, "VimsCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Cassini VIMS point camera model from an opened cube.")
      .def("get_camera_type", &Isis::VimsCamera::GetCameraType)
      .def("ck_frame_id", &Isis::VimsCamera::CkFrameId)
      .def("ck_reference_id", &Isis::VimsCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::VimsCamera::SpkReferenceId)
      .def("pixel_ifov_offsets",
           [](Isis::VimsCamera &self) {
             return toOffsetPairs(self.PixelIfovOffsets());
           },
           "Return pixel IFOV offsets as a list of (x, y) tuples in focal-plane units.");
  py::class_<Isis::VimsGroundMap, Isis::CameraGroundMap>(m, "VimsGroundMap")
      .def(py::init<Isis::Camera *, Isis::Pvl &>(),
           py::arg("parent"),
           py::arg("labels"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Construct the Cassini VIMS ground-map helper.")
      .def("set_focal_plane",
           &Isis::VimsGroundMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"))
      .def("set_ground",
           static_cast<bool (Isis::VimsGroundMap::*)(const Isis::Latitude &, const Isis::Longitude &)>(&Isis::VimsGroundMap::SetGround),
           py::arg("latitude"),
           py::arg("longitude"))
      .def("set_ground",
           static_cast<bool (Isis::VimsGroundMap::*)(const Isis::SurfacePoint &)>(&Isis::VimsGroundMap::SetGround),
           py::arg("surface_point"))
      .def("init", &Isis::VimsGroundMap::Init, py::arg("labels"));
  py::class_<Isis::VimsSkyMap, Isis::CameraSkyMap>(m, "VimsSkyMap")
      .def(py::init<Isis::Camera *, Isis::Pvl &>(),
           py::arg("parent"),
           py::arg("labels"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Construct the Cassini VIMS sky-map helper.")
      .def("set_focal_plane",
           &Isis::VimsSkyMap::SetFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           py::arg("uz"))
      .def("set_sky", &Isis::VimsSkyMap::SetSky, py::arg("ra"), py::arg("dec"))
      .def("init", &Isis::VimsSkyMap::Init, py::arg("labels"));
  py::class_<Isis::Chandrayaan1M3Camera, Isis::LineScanCamera>(m, "Chandrayaan1M3Camera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Chandrayaan-1 M3 line-scan camera model from an opened cube.")
      .def("ck_frame_id", &Isis::Chandrayaan1M3Camera::CkFrameId)
      .def("ck_reference_id", &Isis::Chandrayaan1M3Camera::CkReferenceId)
      .def("spk_reference_id", &Isis::Chandrayaan1M3Camera::SpkReferenceId);
  py::class_<Isis::Chandrayaan1M3DistortionMap, Isis::CameraDistortionMap>(m, "Chandrayaan1M3DistortionMap")
      .def(py::init<Isis::Camera *, double, double, double, double, double, double, double>(),
           py::arg("parent"),
           py::arg("xp"),
           py::arg("yp"),
           py::arg("k1"),
           py::arg("k2"),
           py::arg("k3"),
           py::arg("p1"),
           py::arg("p2"),
           py::keep_alive<1, 2>(),
           "Construct the Chandrayaan-1 M3 distortion-map helper.")
      .def("set_focal_plane",
           &Isis::Chandrayaan1M3DistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::Chandrayaan1M3DistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"));
  py::class_<Isis::HiresCamera, Isis::FramingCamera>(m, "HiresCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Clementine HIRES framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::HiresCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::HiresCamera::CkFrameId)
      .def("ck_reference_id", &Isis::HiresCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::HiresCamera::SpkReferenceId);
  py::class_<Isis::LwirCamera, Isis::FramingCamera>(m, "LwirCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Clementine LWIR framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::LwirCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::LwirCamera::CkFrameId)
      .def("ck_reference_id", &Isis::LwirCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::LwirCamera::SpkReferenceId);
  py::class_<Isis::NirCamera, Isis::FramingCamera>(m, "NirCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Clementine NIR framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::NirCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::NirCamera::CkFrameId)
      .def("ck_reference_id", &Isis::NirCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::NirCamera::SpkReferenceId);
  py::class_<Isis::UvvisCamera, Isis::FramingCamera>(m, "UvvisCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Clementine UVVIS framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::UvvisCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::UvvisCamera::CkFrameId)
      .def("ck_reference_id", &Isis::UvvisCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::UvvisCamera::SpkReferenceId);
  py::class_<Isis::ClementineUvvisDistortionMap, Isis::CameraDistortionMap>(m, "ClementineUvvisDistortionMap")
      .def(py::init<Isis::Camera *, double, double, double, double, double, double, double>(),
           py::arg("parent"),
           py::arg("xp"),
           py::arg("yp"),
           py::arg("k1"),
           py::arg("k2"),
           py::arg("k3"),
           py::arg("p1"),
           py::arg("p2"),
           py::keep_alive<1, 2>(),
           "Construct the Clementine UVVIS distortion-map helper.")
      .def("set_focal_plane",
           &Isis::ClementineUvvisDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::ClementineUvvisDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"));
  py::class_<Isis::ClipperNacRollingShutterCamera, Isis::RollingShutterCamera>(m, "ClipperNacRollingShutterCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an Europa Clipper NAC rolling-shutter camera model from an opened cube.")
      .def("ck_frame_id", &Isis::ClipperNacRollingShutterCamera::CkFrameId)
      .def("ck_reference_id", &Isis::ClipperNacRollingShutterCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::ClipperNacRollingShutterCamera::SpkReferenceId);
  py::class_<Isis::ClipperPushBroomCamera, Isis::LineScanCamera>(m, "ClipperPushBroomCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an Europa Clipper push-broom camera model from an opened cube.")
      .def("ck_frame_id", &Isis::ClipperPushBroomCamera::CkFrameId)
      .def("ck_reference_id", &Isis::ClipperPushBroomCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::ClipperPushBroomCamera::SpkReferenceId);
  py::class_<Isis::ClipperWacFcCamera, Isis::FramingCamera>(m, "ClipperWacFcCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an Europa Clipper WAC framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::ClipperWacFcCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::ClipperWacFcCamera::CkFrameId)
      .def("ck_reference_id", &Isis::ClipperWacFcCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::ClipperWacFcCamera::SpkReferenceId);
  py::class_<Isis::DawnFcCamera, Isis::FramingCamera>(m, "DawnFcCamera");
  py::class_<Isis::DawnVirCamera, Isis::LineScanCamera>(m, "DawnVirCamera");
  py::class_<Isis::SsiCamera, Isis::FramingCamera>(m, "SsiCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Galileo SSI framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::SsiCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::SsiCamera::CkFrameId)
      .def("ck_reference_id", &Isis::SsiCamera::CkReferenceId)
      .def("spk_reference_id", &Isis::SsiCamera::SpkReferenceId);
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
  py::class_<Isis::JunoCamera, Isis::FramingCamera>(m, "JunoCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a JunoCam framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::JunoCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"))
      .def("ck_frame_id", &Isis::JunoCamera::CkFrameId)
      .def("ck_reference_id", &Isis::JunoCamera::CkReferenceId)
      .def("spk_target_id", &Isis::JunoCamera::SpkTargetId)
      .def("spk_reference_id", &Isis::JunoCamera::SpkReferenceId);
  py::class_<Isis::JunoDistortionMap, Isis::CameraDistortionMap>(m, "JunoDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent"),
           py::keep_alive<1, 2>(),
           "Construct the JunoCam distortion-map helper.")
      .def("set_distortion",
           &Isis::JunoDistortionMap::SetDistortion,
           py::arg("naif_ik_code"))
      .def("set_focal_plane",
           &Isis::JunoDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"))
      .def("set_undistorted_focal_plane",
           &Isis::JunoDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"));
  py::class_<Isis::KaguyaMiCamera, Isis::LineScanCamera>(m, "KaguyaMiCamera");
  py::class_<Isis::KaguyaTcCamera, Isis::LineScanCamera>(m, "KaguyaTcCamera");
  py::class_<Isis::LoCameraFiducialMap>(m, "LoCameraFiducialMap")
      .def(py::init<Isis::PvlGroup &, const int>(),
           py::arg("instrument_group"),
           py::arg("naif_ik_code"),
           "Compute fiducial-based focal-plane affine transform coefficients for a Lunar Orbiter camera.")
      .def("__repr__", [](const Isis::LoCameraFiducialMap &) {
        std::ostringstream stream;
        stream << "<LoCameraFiducialMap>";
        return stream.str();
      });
  py::class_<Isis::LoHighCamera, Isis::FramingCamera>(m, "LoHighCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Lunar Orbiter High Resolution camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::LoHighCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::LoHighCamera::CkFrameId,
           "CK frame ID - LO 3/4/5 instrument code determined at runtime")
      .def("ck_reference_id", &Isis::LoHighCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::LoHighCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::LoHighDistortionMap, Isis::CameraDistortionMap>(m, "LoHighDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent") = nullptr,
           py::keep_alive<1, 2>(),
           "Construct the Lunar Orbiter High Resolution distortion map helper.")
      .def("set_distortion",
           &Isis::LoHighDistortionMap::SetDistortion,
           py::arg("naif_ik_code"),
           "Load perspective factors and distortion coefficients from the instrument kernel.")
      .def("set_focal_plane",
           &Isis::LoHighDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::LoHighDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::LoHighDistortionMap &) {
        std::ostringstream stream;
        stream << "<LoHighDistortionMap>";
        return stream.str();
      });
  auto loMediumCamera =
      py::class_<Isis::LoMediumCamera, Isis::FramingCamera>(m, "LoMediumCamera")
          .def(py::init<Isis::Cube &>(),
               py::arg("cube"),
               py::keep_alive<1, 2>(),
               "Construct a Lunar Orbiter Medium Resolution camera model from an opened cube.")
          .def("shutter_open_close_times",
               &Isis::LoMediumCamera::ShutterOpenCloseTimes,
               py::arg("time"),
               py::arg("exposure_duration"),
               "Return shutter open/close times as a pair of iTime values.")
          .def("ck_frame_id", &Isis::LoMediumCamera::CkFrameId,
               "CK frame ID - LO 3/4/5 instrument code determined at runtime")
          .def("ck_reference_id", &Isis::LoMediumCamera::CkReferenceId,
               "CK Reference ID - J2000")
          .def("spk_reference_id", &Isis::LoMediumCamera::SpkReferenceId,
               "SPK Reference ID - J2000");
  py::enum_<Isis::LoMediumCamera::FocalPlaneMapType>(loMediumCamera, "FocalPlaneMapType")
      .value("Fiducial", Isis::LoMediumCamera::FocalPlaneMapType::Fiducial)
      .value("Boresight", Isis::LoMediumCamera::FocalPlaneMapType::Boresight)
      .value("None", Isis::LoMediumCamera::FocalPlaneMapType::None)
      .export_values();
  py::class_<Isis::LoMediumDistortionMap, Isis::CameraDistortionMap>(m, "LoMediumDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent") = nullptr,
           py::keep_alive<1, 2>(),
           "Construct the Lunar Orbiter Medium Resolution distortion map helper.")
      .def("set_distortion",
           &Isis::LoMediumDistortionMap::SetDistortion,
           py::arg("naif_ik_code"),
           "Load distortion coefficients from the instrument kernel for the given NAIF IK code.")
      .def("set_focal_plane",
           &Isis::LoMediumDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::LoMediumDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::LoMediumDistortionMap &) {
        std::ostringstream stream;
        stream << "<LoMediumDistortionMap>";
        return stream.str();
      });
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
  py::class_<Isis::Mariner10Camera, Isis::FramingCamera>(m, "Mariner10Camera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Mariner 10 camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::Mariner10Camera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::Mariner10Camera::CkFrameId,
           "CK frame ID - Mariner 10 scan platform instrument code (-76000)")
      .def("ck_reference_id", &Isis::Mariner10Camera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::Mariner10Camera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::MdisCamera, Isis::FramingCamera>(m, "MdisCamera");
  py::class_<Isis::TaylorCameraDistortionMap, Isis::CameraDistortionMap>(m, "TaylorCameraDistortionMap")
      .def(py::init<Isis::Camera *, double>(),
           py::arg("parent") = nullptr,
           py::arg("z_direction") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the Messenger MDIS Taylor-series distortion map helper.")
      .def("set_distortion",
           &Isis::TaylorCameraDistortionMap::SetDistortion,
           py::arg("naif_ik_code"),
           "Load Taylor-series distortion coefficients from the instrument kernel.")
      .def("set_focal_plane",
           &Isis::TaylorCameraDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::TaylorCameraDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::TaylorCameraDistortionMap &) {
        std::ostringstream stream;
        stream << "<TaylorCameraDistortionMap>";
        return stream.str();
      });
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
  py::class_<Isis::NewHorizonsLeisaCamera, Isis::LineScanCamera>(m, "NewHorizonsLeisaCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a New Horizons LEISA line-scan camera model from an opened cube.")
      .def("set_band",
           &Isis::NewHorizonsLeisaCamera::SetBand,
           py::arg("band"),
           "Set the active virtual band used by the LEISA focal-plane transforms.")
      .def("is_band_independent",
           &Isis::NewHorizonsLeisaCamera::IsBandIndependent,
           "Return whether the camera model is band independent.")
      .def("ck_frame_id", &Isis::NewHorizonsLeisaCamera::CkFrameId,
           "CK frame ID - New Horizons LEISA instrument code (-98000)")
      .def("ck_reference_id", &Isis::NewHorizonsLeisaCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::NewHorizonsLeisaCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::NewHorizonsLorriCamera, Isis::FramingCamera>(m, "NewHorizonsLorriCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a New Horizons LORRI framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::NewHorizonsLorriCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return simulated shutter open/close times for the center-timed LORRI exposure.")
      .def("ck_frame_id", &Isis::NewHorizonsLorriCamera::CkFrameId,
           "CK frame ID - New Horizons LORRI instrument code")
      .def("ck_reference_id", &Isis::NewHorizonsLorriCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::NewHorizonsLorriCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::NewHorizonsLorriDistortionMap, Isis::CameraDistortionMap>(m, "NewHorizonsLorriDistortionMap")
      .def(py::init<Isis::Camera *, double, double, double, double>(),
           py::arg("parent"),
           py::arg("e2"),
           py::arg("e5"),
           py::arg("e6"),
           py::arg("z_direction") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the New Horizons LORRI distortion map helper.")
      .def("set_focal_plane",
           &Isis::NewHorizonsLorriDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::NewHorizonsLorriDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::NewHorizonsLorriDistortionMap &) {
        std::ostringstream stream;
        stream << "<NewHorizonsLorriDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::NewHorizonsMvicFrameCamera, Isis::FramingCamera>(m, "NewHorizonsMvicFrameCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a New Horizons MVIC framing camera model from an opened cube.")
      .def("set_band",
           &Isis::NewHorizonsMvicFrameCamera::SetBand,
           py::arg("band"),
           "Set the active framelet band and corresponding acquisition time.")
      .def("shutter_open_close_times",
           &Isis::NewHorizonsMvicFrameCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times for the MVIC frame exposure.")
      .def("ck_frame_id", &Isis::NewHorizonsMvicFrameCamera::CkFrameId,
           "CK frame ID - New Horizons MVIC framing instrument code")
      .def("ck_reference_id", &Isis::NewHorizonsMvicFrameCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::NewHorizonsMvicFrameCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::NewHorizonsMvicFrameCameraDistortionMap, Isis::CameraDistortionMap>(m, "NewHorizonsMvicFrameCameraDistortionMap")
      .def(py::init<Isis::Camera *, std::vector<double>, std::vector<double>>(),
           py::arg("parent"),
           py::arg("x_distortion_coeffs"),
           py::arg("y_distortion_coeffs"),
           py::keep_alive<1, 2>(),
           "Construct the New Horizons MVIC framing distortion map helper.")
      .def("set_focal_plane",
           &Isis::NewHorizonsMvicFrameCameraDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::NewHorizonsMvicFrameCameraDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::NewHorizonsMvicFrameCameraDistortionMap &) {
        std::ostringstream stream;
        stream << "<NewHorizonsMvicFrameCameraDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::NewHorizonsMvicTdiCamera, Isis::LineScanCamera>(m, "NewHorizonsMvicTdiCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a New Horizons MVIC TDI line-scan camera model from an opened cube.")
      .def("ck_frame_id", &Isis::NewHorizonsMvicTdiCamera::CkFrameId,
           "CK frame ID - New Horizons MVIC TDI instrument code")
      .def("ck_reference_id", &Isis::NewHorizonsMvicTdiCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::NewHorizonsMvicTdiCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::NewHorizonsMvicTdiCameraDistortionMap, Isis::CameraDistortionMap>(m, "NewHorizonsMvicTdiCameraDistortionMap")
      .def(py::init<Isis::Camera *, std::vector<double>, std::vector<double>, std::vector<double>, std::vector<double>>(),
           py::arg("parent"),
           py::arg("x_distortion_coeffs"),
           py::arg("y_distortion_coeffs"),
           py::arg("residual_col_dist_coeffs"),
           py::arg("residual_row_dist_coeffs"),
           py::keep_alive<1, 2>(),
           "Construct the New Horizons MVIC TDI distortion map helper.")
      .def("set_focal_plane",
           &Isis::NewHorizonsMvicTdiCameraDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::NewHorizonsMvicTdiCameraDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::NewHorizonsMvicTdiCameraDistortionMap &) {
        std::ostringstream stream;
        stream << "<NewHorizonsMvicTdiCameraDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::ThemisIrCamera, Isis::LineScanCamera>(m, "ThemisIrCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a THEMIS IR line-scan camera model from an opened cube.")
      .def("set_band",
           &Isis::ThemisIrCamera::SetBand,
           py::arg("band"),
           "Set the active band for band-dependent timing and distortion behavior.")
      .def("is_band_independent",
           &Isis::ThemisIrCamera::IsBandIndependent,
           "Return whether the camera model is band independent.")
      .def("ck_frame_id", &Isis::ThemisIrCamera::CkFrameId,
           "CK frame ID - THEMIS IR instrument code (-53000)")
      .def("ck_reference_id", &Isis::ThemisIrCamera::CkReferenceId,
           "CK Reference ID - MARSIAU/J2000 frame code used by the upstream model")
      .def("spk_reference_id", &Isis::ThemisIrCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::ThemisIrDistortionMap, Isis::CameraDistortionMap>(m, "ThemisIrDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent") = nullptr,
           py::keep_alive<1, 2>(),
           "Construct the THEMIS IR distortion map helper.")
      .def("set_band",
           &Isis::ThemisIrDistortionMap::SetBand,
           py::arg("band"),
           "Set the active detector band used by the distortion coefficients.")
      .def("set_focal_plane",
           &Isis::ThemisIrDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::ThemisIrDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::ThemisIrDistortionMap &) {
        std::ostringstream stream;
        stream << "<ThemisIrDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::ThemisVisCamera, Isis::PushFrameCamera>(m, "ThemisVisCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a THEMIS VIS push-frame camera model from an opened cube.")
      .def("set_band",
           &Isis::ThemisVisCamera::SetBand,
           py::arg("band"),
           "Set the active VIS band for frame timing and detector geometry.")
      .def("band_ephemeris_time_offset",
           &Isis::ThemisVisCamera::BandEphemerisTimeOffset,
           py::arg("band"),
           "Return the per-band ephemeris-time offset in seconds.")
      .def("is_band_independent",
           &Isis::ThemisVisCamera::IsBandIndependent,
           "Return whether the camera model is band independent.")
      .def("ck_frame_id", &Isis::ThemisVisCamera::CkFrameId,
           "CK frame ID - THEMIS VIS instrument code (-53000)")
      .def("ck_reference_id", &Isis::ThemisVisCamera::CkReferenceId,
           "CK Reference ID - MARSIAU (16)")
      .def("spk_reference_id", &Isis::ThemisVisCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::ThemisVisDistortionMap, Isis::CameraDistortionMap>(m, "ThemisVisDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent") = nullptr,
           py::keep_alive<1, 2>(),
           "Construct the THEMIS VIS distortion map helper.")
      .def("set_focal_plane",
           &Isis::ThemisVisDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Map distorted focal-plane coordinates to undistorted coordinates.")
      .def("set_undistorted_focal_plane",
           &Isis::ThemisVisDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Map undistorted focal-plane coordinates to distorted coordinates.")
      .def("__repr__", [](const Isis::ThemisVisDistortionMap &) {
        std::ostringstream stream;
        stream << "<ThemisVisDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::OsirisRexOcamsCamera, Isis::FramingCamera>(m, "OsirisRexOcamsCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an OSIRIS-REx OCAMS camera model from an opened cube.\n\n"
           "OCAMS includes MapCam, PolyCam, and SamCam cameras.")
      .def("shutter_open_close_times",
           &Isis::OsirisRexOcamsCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::OsirisRexOcamsCamera::CkFrameId,
           "CK frame ID - OSIRIS-REx spacecraft instrument code")
      .def("ck_reference_id", &Isis::OsirisRexOcamsCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::OsirisRexOcamsCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::OsirisRexTagcamsCamera, Isis::FramingCamera>(m, "OsirisRexTagcamsCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct an OSIRIS-REx TAGCAMS camera model from an opened cube.\n\n"
           "TAGCAMS includes NavCam, NFTCam, and StowCam navigation cameras.")
      .def("shutter_open_close_times",
           &Isis::OsirisRexTagcamsCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::OsirisRexTagcamsCamera::CkFrameId,
           "CK frame ID - OSIRIS-REx spacecraft instrument code")
      .def("ck_reference_id", &Isis::OsirisRexTagcamsCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::OsirisRexTagcamsCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::OsirisRexDistortionMap, Isis::CameraDistortionMap>(m, "OsirisRexDistortionMap")
      .def(py::init<Isis::Camera *, double>(),
           py::arg("parent"),
           py::arg("z_direction") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the OSIRIS-REx OCAMS distortion map.\n\n"
           "Args:\n"
           "    parent: Pointer to the parent Camera object\n"
           "    z_direction: Direction of the z-axis (1.0 or -1.0)")
      .def("set_distortion",
           &Isis::OsirisRexDistortionMap::SetDistortion,
           py::arg("naif_ik_code"),
           py::arg("filter_name"),
           "Load distortion coefficients from the instrument kernel for the given NAIF code and filter.")
      .def("set_focal_plane",
           &Isis::OsirisRexDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Compute undistorted focal plane (x,y) from distorted (x,y).\n\n"
           "Args:\n"
           "    dx: Distorted focal plane x, in millimeters\n"
           "    dy: Distorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("set_undistorted_focal_plane",
           &Isis::OsirisRexDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Compute distorted focal plane (x,y) from undistorted (x,y).\n\n"
           "Args:\n"
           "    ux: Undistorted focal plane x, in millimeters\n"
           "    uy: Undistorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("__repr__", [](const Isis::OsirisRexDistortionMap &) {
        std::ostringstream stream;
        stream << "<OsirisRexDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::OsirisRexTagcamsDistortionMap, Isis::CameraDistortionMap>(m, "OsirisRexTagcamsDistortionMap")
      .def(py::init<Isis::Camera *, int, const double>(),
           py::arg("parent"),
           py::arg("naif_ik_code"),
           py::arg("zdir") = 1.0,
           py::keep_alive<1, 2>(),
           "Construct the OSIRIS-REx TAGCAMS distortion map with advanced OpenCV model.\n\n"
           "Args:\n"
           "    parent: Pointer to the parent Camera object\n"
           "    naif_ik_code: NAIF IK code for loading distortion coefficients\n"
           "    zdir: Direction of the z-axis (1.0 or -1.0)")
      .def("set_camera_temperature",
           &Isis::OsirisRexTagcamsDistortionMap::SetCameraTemperature,
           py::arg("temp"),
           "Set the camera head temperature for temperature-dependent focal length adjustment.\n\n"
           "Args:\n"
           "    temp: Camera temperature in Celsius")
      .def("set_focal_plane",
           &Isis::OsirisRexTagcamsDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Compute undistorted focal plane (x,y) from distorted (x,y).\n\n"
           "Args:\n"
           "    dx: Distorted focal plane x, in millimeters\n"
           "    dy: Distorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("set_undistorted_focal_plane",
           &Isis::OsirisRexTagcamsDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Compute distorted focal plane (x,y) from undistorted (x,y).\n\n"
           "Args:\n"
           "    ux: Undistorted focal plane x, in millimeters\n"
           "    uy: Undistorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("__repr__", [](const Isis::OsirisRexTagcamsDistortionMap &) {
        std::ostringstream stream;
        stream << "<OsirisRexTagcamsDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::RosettaOsirisCamera, Isis::FramingCamera>(m, "RosettaOsirisCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Rosetta OSIRIS NAC/WAC framing camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::RosettaOsirisCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::RosettaOsirisCamera::CkFrameId,
           "CK frame ID - Rosetta orbiter instrument code (-226000)")
      .def("ck_reference_id", &Isis::RosettaOsirisCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::RosettaOsirisCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
  py::class_<Isis::RosettaOsirisCameraDistortionMap, Isis::CameraDistortionMap>(m, "RosettaOsirisCameraDistortionMap")
      .def(py::init<Isis::Camera *>(),
           py::arg("parent"),
           py::keep_alive<1, 2>(),
           "Construct the Rosetta OSIRIS polynomial distortion map.\n\n"
           "Args:\n"
           "    parent: Pointer to the parent Camera object")
      .def("set_focal_plane",
           &Isis::RosettaOsirisCameraDistortionMap::SetFocalPlane,
           py::arg("dx"),
           py::arg("dy"),
           "Compute undistorted focal plane (x,y) from distorted (x,y).\n\n"
           "Args:\n"
           "    dx: Distorted focal plane x, in millimeters\n"
           "    dy: Distorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("set_undistorted_focal_plane",
           &Isis::RosettaOsirisCameraDistortionMap::SetUndistortedFocalPlane,
           py::arg("ux"),
           py::arg("uy"),
           "Compute distorted focal plane (x,y) from undistorted (x,y).\n\n"
           "Args:\n"
           "    ux: Undistorted focal plane x, in millimeters\n"
           "    uy: Undistorted focal plane y, in millimeters\n\n"
           "Returns:\n"
           "    True if successful")
      .def("set_un_distorted_x_matrix",
           &Isis::RosettaOsirisCameraDistortionMap::setUnDistortedXMatrix,
           py::arg("x_mat"),
           "Set the undistorted X polynomial coefficient matrix.")
      .def("set_un_distorted_y_matrix",
           &Isis::RosettaOsirisCameraDistortionMap::setUnDistortedYMatrix,
           py::arg("y_mat"),
           "Set the undistorted Y polynomial coefficient matrix.")
      .def("set_boresight",
           &Isis::RosettaOsirisCameraDistortionMap::setBoresight,
           py::arg("sample"),
           py::arg("line"),
           "Set the camera boresight pixel coordinates.")
      .def("set_pixel_pitch",
           &Isis::RosettaOsirisCameraDistortionMap::setPixelPitch,
           py::arg("pitch"),
           "Set the camera pixel pitch in millimeters.")
      .def("__repr__", [](const Isis::RosettaOsirisCameraDistortionMap &) {
        std::ostringstream stream;
        stream << "<RosettaOsirisCameraDistortionMap>";
        return stream.str();
      });
  py::class_<Isis::RosettaVirtisCamera, Isis::LineScanCamera>(m, "RosettaVirtisCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Rosetta VIRTIS-M line scan camera model from an opened cube.")
      .def("ck_frame_id", &Isis::RosettaVirtisCamera::CkFrameId,
           "CK frame ID - VIRTIS instrument code (-226110)")
      .def("ck_reference_id", &Isis::RosettaVirtisCamera::CkReferenceId,
           "CK Reference ID - J2000")
      .def("spk_reference_id", &Isis::RosettaVirtisCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
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
  py::class_<Isis::VikingCamera, Isis::FramingCamera>(m, "VikingCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Viking Orbiter camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::VikingCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::VikingCamera::CkFrameId,
           "CK frame ID - Viking Orbiter platform code, mission dependent")
      .def("ck_reference_id", &Isis::VikingCamera::CkReferenceId,
           "CK Reference ID - B1950")
      .def("spk_target_id", &Isis::VikingCamera::SpkTargetId,
           "SPK Target Body ID - Viking Orbiter spacecraft, mission dependent")
      .def("spk_reference_id", &Isis::VikingCamera::SpkReferenceId,
           "SPK Reference ID - B1950");
  py::class_<Isis::VoyagerCamera, Isis::FramingCamera>(m, "VoyagerCamera")
      .def(py::init<Isis::Cube &>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a Voyager camera model from an opened cube.")
      .def("shutter_open_close_times",
           &Isis::VoyagerCamera::ShutterOpenCloseTimes,
           py::arg("time"),
           py::arg("exposure_duration"),
           "Return the shutter open/close times as a pair of iTime values.")
      .def("ck_frame_id", &Isis::VoyagerCamera::CkFrameId,
           "CK frame ID - Voyager scan platform (VG1/2_SCAN_PLATFORM)")
      .def("ck_reference_id", &Isis::VoyagerCamera::CkReferenceId,
           "CK Reference ID - B1950")
      .def("spk_target_id", &Isis::VoyagerCamera::SpkTargetId,
           "SPK Target Body ID (-31 for Voyager 1, -32 for Voyager 2)")
      .def("spk_reference_id", &Isis::VoyagerCamera::SpkReferenceId,
           "SPK Reference ID - J2000");
}
