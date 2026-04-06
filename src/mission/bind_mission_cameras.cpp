// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include "ApolloMetricCamera.h"
#include "ApolloPanoramicCamera.h"
#include "Chandrayaan1M3Camera.h"
#include "ClipperNacRollingShutterCamera.h"
#include "ClipperPushBroomCamera.h"
#include "ClipperWacFcCamera.h"
#include "CrismCamera.h"
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
#include "IssNACamera.h"
#include "IssWACamera.h"
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
#include "OsirisRexOcamsCamera.h"
#include "OsirisRexTagcamsCamera.h"
#include "PushFrameCamera.h"
#include "RadarCamera.h"
#include "RosettaOsirisCamera.h"
#include "RosettaVirtisCamera.h"
#include "RollingShutterCamera.h"
#include "SsiCamera.h"
#include "TgoCassisCamera.h"
#include "ThemisIrCamera.h"
#include "ThemisVisCamera.h"
#include "UvvisCamera.h"
#include "VikingCamera.h"
#include "VimsCamera.h"
#include "VoyagerCamera.h"

namespace py = pybind11;

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
  py::class_<Isis::HayabusaAmicaCamera, Isis::FramingCamera>(m, "HayabusaAmicaCamera");
  py::class_<Isis::HayabusaNirsCamera, Isis::FramingCamera>(m, "HayabusaNirsCamera");
  py::class_<Isis::Hyb2OncCamera, Isis::FramingCamera>(m, "Hyb2OncCamera");
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
  py::class_<Isis::HrscCamera, Isis::LineScanCamera>(m, "HrscCamera");
  py::class_<Isis::MexHrscSrcCamera, Isis::FramingCamera>(m, "MexHrscSrcCamera");
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
  py::class_<Isis::TgoCassisCamera, Isis::FramingCamera>(m, "TgoCassisCamera");
  py::class_<Isis::VikingCamera, Isis::FramingCamera>(m, "VikingCamera");
  py::class_<Isis::VoyagerCamera, Isis::FramingCamera>(m, "VoyagerCamera");
}
