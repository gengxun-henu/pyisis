/**
 * Source ISIS headers:
 *   - isis/src/base/objs/PhotoModel/PhotoModel.h
 *   - isis/src/base/objs/PhotoModelFactory/PhotoModelFactory.h
 *   - isis/src/base/objs/AtmosModel/AtmosModel.h
 *   - isis/src/base/objs/AtmosModelFactory/AtmosModelFactory.h
 *   - isis/src/base/objs/AtmosModel/NumericalAtmosApprox.h
 *   - isis/src/base/objs/NormModel/NormModel.h
 *   - isis/src/base/objs/NormModelFactory/NormModelFactory.h
 *   - isis/src/base/objs/AlbedoAtm/AlbedoAtm.h
 * Source classes: PhotoModel, PhotoModelFactory, AtmosModel, AtmosModelFactory, NumericalAtmosApprox, NormModel, NormModelFactory, AlbedoAtm
 * Source header author(s): PhotoModel/AtmosModel/NormModel/AlbedoAtm class headers cite Randy Kirk; Factory headers cite Janet Barrett
 * Binding author: Geng Xun
 * Created: 2026-04-04
 * Updated: 2026-04-09  Geng Xun expanded photometry base APIs and added Hapke, ShadeAtm, and TopoAtm for the rollout queue
 * Updated: 2026-04-09  Geng Xun added NumericalAtmosApprox numerical integration bindings for the third rollout batch.
 *
 * Purpose: Expose photometric, atmospheric, and normalization model bindings including factories and concrete implementations.
 */

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Anisotropic1.h"
#include "Anisotropic2.h"
#include "AlbedoAtm.h"
#include "AtmosModel.h"
#include "AtmosModelFactory.h"
#include "Hapke.h"
#include "HapkeAtm1.h"
#include "HapkeAtm2.h"
#include "Isotropic1.h"
#include "Isotropic2.h"
#include "NumericalAtmosApprox.h"
#include "NumericalApproximation.h"
#include "NormModel.h"
#include "NormModelFactory.h"
#include "PhotoModel.h"
#include "PhotoModelFactory.h"
#include "Pvl.h"
#include "ShadeAtm.h"
#include "TopoAtm.h"
#include "helpers.h"

namespace py = pybind11;

void bind_base_photometry(py::module_ &m) {
  py::class_<Isis::PhotoModel>(m, "PhotoModel")
      .def("algorithm_name",
           [](const Isis::PhotoModel &self) {
             return qStringToStdString(self.AlgorithmName());
           },
           "Get the photometric algorithm name")
      .def("set_standard_conditions",
           &Isis::PhotoModel::SetStandardConditions,
           py::arg("standard"),
           "Enable or disable standard photometric conditions")
      .def("standard_conditions",
           &Isis::PhotoModel::StandardConditions,
           "Check whether standard photometric conditions are enabled")
      .def("calc_surf_albedo",
           &Isis::PhotoModel::CalcSurfAlbedo,
           py::arg("phase"), py::arg("incidence"), py::arg("emission"),
           "Calculate surface albedo for the given geometry")
      .def("pht_topder",
           &Isis::PhotoModel::PhtTopder,
           py::arg("phase"), py::arg("incidence"), py::arg("emission"),
           "Compute the topographic derivative for the given geometry")
      .def("set_photo_k",
           &Isis::PhotoModel::SetPhotoK,
           py::arg("k"),
           "Set the photometric K parameter")
      .def("photo_k",
           &Isis::PhotoModel::PhotoK,
           "Get the photometric K parameter")
      .def("set_photo_l",
           &Isis::PhotoModel::SetPhotoL,
           py::arg("l"),
           "Set the photometric L parameter")
      .def("photo_l",
           &Isis::PhotoModel::PhotoL,
           "Get the photometric L parameter")
      .def("set_photo_hg1",
           &Isis::PhotoModel::SetPhotoHg1,
           py::arg("hg1"),
           "Set the photometric Hg1 parameter")
      .def("photo_hg1",
           &Isis::PhotoModel::PhotoHg1,
           "Get the photometric Hg1 parameter")
      .def("set_photo_hg2",
           &Isis::PhotoModel::SetPhotoHg2,
           py::arg("hg2"),
           "Set the photometric Hg2 parameter")
      .def("photo_hg2",
           &Isis::PhotoModel::PhotoHg2,
           "Get the photometric Hg2 parameter")
      .def("set_photo_bh",
           &Isis::PhotoModel::SetPhotoBh,
           py::arg("bh"),
           "Set the photometric Bh parameter")
      .def("photo_bh",
           &Isis::PhotoModel::PhotoBh,
           "Get the photometric Bh parameter")
      .def("set_photo_ch",
           &Isis::PhotoModel::SetPhotoCh,
           py::arg("ch"),
           "Set the photometric Ch parameter")
      .def("photo_ch",
           &Isis::PhotoModel::PhotoCh,
           "Get the photometric Ch parameter")
      .def("set_photo_wh",
           &Isis::PhotoModel::SetPhotoWh,
           py::arg("wh"),
           "Set the photometric Wh parameter")
      .def("photo_wh",
           &Isis::PhotoModel::PhotoWh,
           "Get the photometric Wh parameter")
      .def("set_photo_hh",
           &Isis::PhotoModel::SetPhotoHh,
           py::arg("hh"),
           "Set the photometric Hh parameter")
      .def("photo_hh",
           &Isis::PhotoModel::PhotoHh,
           "Get the photometric Hh parameter")
      .def("set_photo_b0",
           &Isis::PhotoModel::SetPhotoB0,
           py::arg("b0"),
           "Set the photometric B0 parameter")
      .def("photo_b0",
           &Isis::PhotoModel::PhotoB0,
           "Get the photometric B0 parameter")
      .def("set_photo_theta",
           &Isis::PhotoModel::SetPhotoTheta,
           py::arg("theta"),
           "Set the photometric theta parameter")
      .def("photo_theta",
           &Isis::PhotoModel::PhotoTheta,
           "Get the photometric theta parameter")
      .def("set_photo0_b0_standard",
           [](Isis::PhotoModel &self, const std::string &value) {
             self.SetPhoto0B0Standard(stdStringToQString(value));
           },
           py::arg("b0_standard"),
           "Set the ZeroB0 standardization mode")
      .def("photo0_b0_standard",
           [](const Isis::PhotoModel &self) {
             return qStringToStdString(self.Photo0B0Standard());
           },
           "Get the ZeroB0 standardization mode")
      .def("hfunc",
           &Isis::PhotoModel::Hfunc,
           py::arg("u"),
           py::arg("gamma"),
           "Evaluate Hapke's approximation to Chandrasekhar's H function")
      .def("set_photo_phase_list",
           [](Isis::PhotoModel &self, const std::string &value) {
             self.SetPhotoPhaseList(stdStringToQString(value));
           },
           py::arg("phase_list"),
           "Set the photometric phase list definition")
      .def("set_photo_k_list",
           [](Isis::PhotoModel &self, const std::string &value) {
             self.SetPhotoKList(stdStringToQString(value));
           },
           py::arg("k_list"),
           "Set the photometric k list definition")
      .def("set_photo_l_list",
           [](Isis::PhotoModel &self, const std::string &value) {
             self.SetPhotoLList(stdStringToQString(value));
           },
           py::arg("l_list"),
           "Set the photometric l list definition")
      .def("set_photo_phase_curve_list",
           [](Isis::PhotoModel &self, const std::string &value) {
             self.SetPhotoPhaseCurveList(stdStringToQString(value));
           },
           py::arg("phase_curve_list"),
           "Set the photometric phase curve list definition")
      .def("photo_phase_list",
           &Isis::PhotoModel::PhotoPhaseList,
           "Get the photometric phase list")
      .def("photo_k_list",
           &Isis::PhotoModel::PhotoKList,
           "Get the photometric k list")
      .def("photo_l_list",
           &Isis::PhotoModel::PhotoLList,
           "Get the photometric l list")
      .def("photo_phase_curve_list",
           &Isis::PhotoModel::PhotoPhaseCurveList,
           "Get the photometric phase curve list")
      .def_static("pht_acos",
                  &Isis::PhotoModel::PhtAcos,
                  py::arg("cosang"),
                  "Compute arccosine using ISIS photometric utility logic")
      .def("__repr__",
                          [](const Isis::PhotoModel &self) -> std::string {
             return "PhotoModel(algorithm='" + qStringToStdString(self.AlgorithmName()) + "')";
           });

  py::class_<Isis::PhotoModelFactory,
             std::unique_ptr<Isis::PhotoModelFactory, py::nodelete>>(m, "PhotoModelFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl) -> Isis::PhotoModel * {
                    return Isis::PhotoModelFactory::Create(pvl);
                  },
                  py::arg("pvl"),
                  py::return_value_policy::take_ownership,
                  "Create a PhotoModel instance from PVL configuration.")
      .def("__repr__",
                          [](const Isis::PhotoModelFactory &) -> std::string {
             return "PhotoModelFactory()";
           });

  py::class_<Isis::Hapke, Isis::PhotoModel>(m, "Hapke")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Create a Hapke photometric model from PVL configuration.")
      .def("set_old_theta",
           &Isis::Hapke::SetOldTheta,
           py::arg("theta"),
           "Set the cached theta value used by the roughness model")
      .def("photo_model_algorithm",
           &Isis::Hapke::PhotoModelAlgorithm,
           py::arg("phase"), py::arg("incidence"), py::arg("emission"),
           "Evaluate the Hapke photometric model directly")
      .def("__repr__",
           [](const Isis::Hapke &self) -> std::string {
             return "Hapke(algorithm='" + qStringToStdString(self.AlgorithmName()) + "')";
           });

  py::class_<Isis::AtmosModel>(m, "AtmosModel")
      .def_static("g11_prime",
                  &Isis::AtmosModel::G11Prime,
                  py::arg("tau"),
                  "Compute the second-order scattering helper G11Prime")
      .def_static("ei",
                  &Isis::AtmosModel::Ei,
                  py::arg("x"),
                  "Compute the exponential integral Ei(x)")
      .def_static("en",
                  &Isis::AtmosModel::En,
                  py::arg("n"),
                  py::arg("x"),
                  "Compute the generalized exponential integral En(x)")
      .def("algorithm_name",
           &Isis::AtmosModel::AlgorithmName,
           "Get the atmospheric algorithm name")
      .def("set_standard_conditions",
           &Isis::AtmosModel::SetStandardConditions,
           py::arg("standard"),
           "Enable or disable standard atmospheric conditions")
      .def("calc_atm_effect",
           [](Isis::AtmosModel &self, double phase, double incidence, double emission) {
             double pstd = 0.0;
             double trans = 0.0;
             double trans0 = 0.0;
             double sbar = 0.0;
             double transs = 0.0;
             self.CalcAtmEffect(phase, incidence, emission, &pstd, &trans, &trans0, &sbar, &transs);
             return py::make_tuple(pstd, trans, trans0, sbar, transs);
           },
           py::arg("phase"), py::arg("incidence"), py::arg("emission"),
           "Calculate atmospheric effect terms for the given geometry")
      .def("generate_ah_table",
           &Isis::AtmosModel::GenerateAhTable,
           "Generate the hemispheric albedo lookup table")
      .def("generate_hahg_tables",
           &Isis::AtmosModel::GenerateHahgTables,
           "Generate the Hapke/Henyey-Greenstein lookup tables")
      .def("generate_hahg_tables_shadow",
           &Isis::AtmosModel::GenerateHahgTablesShadow,
           "Generate the shadow-model Hapke/Henyey-Greenstein lookup tables")
      .def("set_atmos_atm_switch",
           &Isis::AtmosModel::SetAtmosAtmSwitch,
           py::arg("atmswitch"),
           "Set the internal atmospheric integration switch")
      .def("set_atmos_bha",
           &Isis::AtmosModel::SetAtmosBha,
           py::arg("bha"),
           "Set the atmospheric Bha parameter")
      .def("set_atmos_hga",
           &Isis::AtmosModel::SetAtmosHga,
           py::arg("hga"),
           "Set the atmospheric Hga parameter")
      .def("set_atmos_inc",
           &Isis::AtmosModel::SetAtmosInc,
           py::arg("incidence"),
           "Set the atmospheric incidence angle")
      .def("set_atmos_nulneg",
           [](Isis::AtmosModel &self, const std::string &nulneg) {
             self.SetAtmosNulneg(nulneg);
           },
           py::arg("nulneg"),
           "Set whether negative corrected values become NULL")
      .def("set_atmos_phi",
           &Isis::AtmosModel::SetAtmosPhi,
           py::arg("phi"),
           "Set the atmospheric azimuth angle")
      .def("set_atmos_tau",
           &Isis::AtmosModel::SetAtmosTau,
           py::arg("tau"),
           "Set the atmospheric optical depth")
      .def("set_atmos_tauref",
           &Isis::AtmosModel::SetAtmosTauref,
           py::arg("tauref"),
           "Set the atmospheric reference optical depth")
      .def("set_atmos_wha",
           &Isis::AtmosModel::SetAtmosWha,
           py::arg("wha"),
           "Set the atmospheric single-scattering albedo")
      .def("set_atmos_hnorm",
           &Isis::AtmosModel::SetAtmosHnorm,
           py::arg("hnorm"),
           "Set the normalized atmospheric shell thickness")
      .def("set_atmos_iord",
           [](Isis::AtmosModel &self, const std::string &offset) {
             self.SetAtmosIord(offset);
           },
           py::arg("offset"),
           "Set whether additive offset is allowed in the fit")
      .def("set_atmos_est_tau",
           [](Isis::AtmosModel &self, const std::string &estimate_tau) {
             self.SetAtmosEstTau(estimate_tau);
           },
           py::arg("estimate_tau"),
           "Set whether optical depth should be estimated from shadows")
      .def("atmos_additive_offset",
           &Isis::AtmosModel::AtmosAdditiveOffset,
           "Check whether additive offset is enabled")
      .def("atmos_hnorm",
           &Isis::AtmosModel::AtmosHnorm,
           "Get the normalized atmospheric shell thickness")
      .def("atmos_bha",
           &Isis::AtmosModel::AtmosBha,
           "Get the atmospheric Bha parameter")
      .def("atmos_tau", &Isis::AtmosModel::AtmosTau, "Get the atmospheric tau value")
      .def("atmos_wha", &Isis::AtmosModel::AtmosWha, "Get the atmospheric wha value")
      .def("atmos_hga", &Isis::AtmosModel::AtmosHga, "Get the atmospheric hga value")
      .def("atmos_tauref", &Isis::AtmosModel::AtmosTauref, "Get the atmospheric tauref value")
      .def("atmos_nulneg", &Isis::AtmosModel::AtmosNulneg, "Check whether negative corrected values become NULL")
      .def("atmos_ab", &Isis::AtmosModel::AtmosAb, "Get the bihemispheric atmospheric albedo")
      .def("atmos_hahgsb", &Isis::AtmosModel::AtmosHahgsb, "Get the Hapke/Henyey-Greenstein sky illumination term")
      .def("atmos_ninc", &Isis::AtmosModel::AtmosNinc, "Get the number of incidence samples in the atmospheric tables")
      .def("atmos_munot", &Isis::AtmosModel::AtmosMunot, "Get the cosine of the atmospheric incidence angle")
      .def("atmos_inc_table", &Isis::AtmosModel::AtmosIncTable, "Get the atmospheric incidence table")
      .def("atmos_ah_table", &Isis::AtmosModel::AtmosAhTable, "Get the atmospheric hemispheric albedo table")
      .def("atmos_hahgt_table", &Isis::AtmosModel::AtmosHahgtTable, "Get the atmospheric Hahgt table")
      .def("atmos_hahgt0_table", &Isis::AtmosModel::AtmosHahgt0Table, "Get the atmospheric Hahgt0 table")
      .def("__repr__",
                          [](const Isis::AtmosModel &self) -> std::string {
             return "AtmosModel(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::Anisotropic1, Isis::AtmosModel>(m, "Anisotropic1")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create an Anisotropic1 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
                          [](const Isis::Anisotropic1 &self) -> std::string {
                               return "Anisotropic1(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::Anisotropic2, Isis::AtmosModel>(m, "Anisotropic2")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create an Anisotropic2 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
           [](const Isis::Anisotropic2 &self) -> std::string {
             return "Anisotropic2(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::HapkeAtm1, Isis::AtmosModel>(m, "HapkeAtm1")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create a HapkeAtm1 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
           [](const Isis::HapkeAtm1 &self) -> std::string {
             return "HapkeAtm1(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::HapkeAtm2, Isis::AtmosModel>(m, "HapkeAtm2")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create a HapkeAtm2 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
           [](const Isis::HapkeAtm2 &self) -> std::string {
             return "HapkeAtm2(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::Isotropic1, Isis::AtmosModel>(m, "Isotropic1")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create an Isotropic1 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
           [](const Isis::Isotropic1 &self) -> std::string {
             return "Isotropic1(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::Isotropic2, Isis::AtmosModel>(m, "Isotropic2")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           "Create an Isotropic2 atmospheric model with the given PVL configuration and PhotoModel.")
      .def("__repr__",
           [](const Isis::Isotropic2 &self) -> std::string {
             return "Isotropic2(algorithm='" + self.AlgorithmName() + "')";
           });

  // Added: 2026-04-06 - NormModel base class binding
  py::class_<Isis::NormModel>(m, "NormModel")
      .def("algorithm_name",
           &Isis::NormModel::AlgorithmName,
           "Get the normalization algorithm name")
      .def("calc_nrm_albedo",
           [](Isis::NormModel &self, double pha, double inc, double ema, double dn) {
             double albedo = 0.0;
             double mult = 0.0;
             double base = 0.0;
             self.CalcNrmAlbedo(pha, inc, ema, dn, albedo, mult, base);
             return py::make_tuple(albedo, mult, base);
           },
           py::arg("phase"), py::arg("incidence"), py::arg("emission"), py::arg("dn"),
           "Calculate normalization albedo (without DEM) for the given geometry and DN value")
      .def("calc_nrm_albedo",
           [](Isis::NormModel &self, double pha, double inc, double ema, double deminc,
              double demema, double dn) {
             double albedo = 0.0;
             double mult = 0.0;
             double base = 0.0;
             self.CalcNrmAlbedo(pha, inc, ema, deminc, demema, dn, albedo, mult, base);
             return py::make_tuple(albedo, mult, base);
           },
           py::arg("phase"), py::arg("incidence"), py::arg("emission"),
           py::arg("dem_incidence"), py::arg("dem_emission"), py::arg("dn"),
           "Calculate normalization albedo (with DEM) for the given geometry and DN value")
      .def("set_norm_wavelength",
           &Isis::NormModel::SetNormWavelength,
           py::arg("wavelength"),
           "Set the normalization wavelength")
      .def("__repr__",
           [](const Isis::NormModel &self) -> std::string {
             return "NormModel(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::ShadeAtm, Isis::NormModel>(m, "ShadeAtm")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &, Isis::AtmosModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::arg("atmos_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           py::keep_alive<1, 4>(),
           "Create a ShadeAtm normalization model from PVL configuration, a PhotoModel, and an AtmosModel.")
      .def("__repr__",
           [](const Isis::ShadeAtm &self) -> std::string {
             return "ShadeAtm(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::TopoAtm, Isis::NormModel>(m, "TopoAtm")
      .def(py::init<Isis::Pvl &, Isis::PhotoModel &, Isis::AtmosModel &>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::arg("atmos_model"),
           py::keep_alive<1, 2>(),
           py::keep_alive<1, 3>(),
           py::keep_alive<1, 4>(),
           "Create a TopoAtm normalization model from PVL configuration, a PhotoModel, and an AtmosModel.")
      .def("__repr__",
           [](const Isis::TopoAtm &self) -> std::string {
             return "TopoAtm(algorithm='" + self.AlgorithmName() + "')";
           });

  py::class_<Isis::AtmosModelFactory,
             std::unique_ptr<Isis::AtmosModelFactory, py::nodelete>>(m, "AtmosModelFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl, Isis::PhotoModel &photoModel) -> Isis::AtmosModel * {
                    return Isis::AtmosModelFactory::Create(pvl, photoModel);
                  },
                  py::arg("pvl"),
                  py::arg("photo_model"),
                  py::return_value_policy::take_ownership,
                  "Create an AtmosModel instance from PVL configuration and a PhotoModel.")
      .def("__repr__",
                          [](const Isis::AtmosModelFactory &) -> std::string {
             return "AtmosModelFactory()";
           });

  py::class_<Isis::NumericalAtmosApprox> numericalAtmosApprox(m, "NumericalAtmosApprox");

     numericalAtmosApprox.attr("InterpType") = m.attr("NumericalApproximationInterpType");

  py::enum_<Isis::NumericalAtmosApprox::IntegFunc>(numericalAtmosApprox, "IntegFunc")
      .value("OuterFunction", Isis::NumericalAtmosApprox::IntegFunc::OuterFunction)
      .value("InnerFunction", Isis::NumericalAtmosApprox::IntegFunc::InnerFunction)
      .export_values();

  numericalAtmosApprox
      .def(py::init<const Isis::NumericalApproximation::InterpType &>(),
           py::arg("interp_type") = Isis::NumericalApproximation::InterpType::CubicNatural,
           "Construct a NumericalAtmosApprox helper with the chosen interpolation mode.")
      .def("rombergs_method",
           &Isis::NumericalAtmosApprox::RombergsMethod,
           py::arg("atmos_model"),
           py::arg("sub_function"),
           py::arg("a"),
           py::arg("b"),
           "Integrate the selected atmospheric helper function over the interval [a, b] using Romberg integration.")
      .def("refine_extended_trap",
           &Isis::NumericalAtmosApprox::RefineExtendedTrap,
           py::arg("atmos_model"),
           py::arg("sub_function"),
           py::arg("a"),
           py::arg("b"),
           py::arg("previous_sum"),
           py::arg("iteration"),
           "Perform one refinement step of the extended trapezoidal integration rule for the selected atmospheric helper function.")
      .def_static("outr_func2_bint",
                  &Isis::NumericalAtmosApprox::OutrFunc2Bint,
                  py::arg("atmos_model"),
                  py::arg("phi"),
                  "Evaluate the outer atmospheric integration helper at the given azimuth angle.")
      .def_static("inr_func2_bint",
                  &Isis::NumericalAtmosApprox::InrFunc2Bint,
                  py::arg("atmos_model"),
                  py::arg("mu"),
                  "Evaluate the inner atmospheric integration helper at the given cosine emission angle.")
      .def("__repr__",
           [](const Isis::NumericalAtmosApprox &) -> std::string {
             return "NumericalAtmosApprox()";
           });

  // Added: 2026-04-06 - NormModelFactory binding
  py::class_<Isis::NormModelFactory,
             std::unique_ptr<Isis::NormModelFactory, py::nodelete>>(m, "NormModelFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl, Isis::PhotoModel &pmodel) -> Isis::NormModel * {
                    return Isis::NormModelFactory::Create(pvl, pmodel);
                  },
                  py::arg("pvl"),
                  py::arg("photo_model"),
                  py::return_value_policy::take_ownership,
                  "Create a NormModel instance from PVL configuration and a PhotoModel.")
      .def_static("create",
                  [](Isis::Pvl &pvl, Isis::PhotoModel &pmodel, Isis::AtmosModel &amodel) -> Isis::NormModel * {
                    return Isis::NormModelFactory::Create(pvl, pmodel, amodel);
                  },
                  py::arg("pvl"),
                  py::arg("photo_model"),
                  py::arg("atmos_model"),
                  py::return_value_policy::take_ownership,
                  "Create a NormModel instance from PVL configuration, a PhotoModel, and an AtmosModel.")
      .def("__repr__",
                          [](const Isis::NormModelFactory &) -> std::string {
             return "NormModelFactory()";
           });

  // Added: 2026-04-06 - AlbedoAtm normalization model binding
  py::class_<Isis::AlbedoAtm, Isis::NormModel>(m, "AlbedoAtm")
      .def(py::init<Isis::Pvl&, Isis::PhotoModel&, Isis::AtmosModel&>(),
           py::arg("pvl"),
           py::arg("photo_model"),
           py::arg("atmos_model"),
           py::keep_alive<1, 2>(),  // Keep pvl alive as long as AlbedoAtm instance
           py::keep_alive<1, 3>(),  // Keep photo_model alive
           py::keep_alive<1, 4>(),  // Keep atmos_model alive
           "Construct an AlbedoAtm normalization model from PVL configuration")
      .def("__repr__",
                          [](const Isis::AlbedoAtm &self) -> std::string {
             return "AlbedoAtm(algorithm='" + self.AlgorithmName() + "')";
           });
}
