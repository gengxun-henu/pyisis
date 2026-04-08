/**
 * Source ISIS headers:
 *   - isis/src/base/objs/PhotoModel/PhotoModel.h
 *   - isis/src/base/objs/PhotoModelFactory/PhotoModelFactory.h
 *   - isis/src/base/objs/AtmosModel/AtmosModel.h
 *   - isis/src/base/objs/AtmosModelFactory/AtmosModelFactory.h
 *   - isis/src/base/objs/NormModel/NormModel.h
 *   - isis/src/base/objs/NormModelFactory/NormModelFactory.h
 *   - isis/src/base/objs/AlbedoAtm/AlbedoAtm.h
 * Source classes: PhotoModel, PhotoModelFactory, AtmosModel, AtmosModelFactory, NormModel, NormModelFactory, AlbedoAtm
 * Source header author(s): PhotoModel/AtmosModel/NormModel/AlbedoAtm class headers cite Randy Kirk; Factory headers cite Janet Barrett
 * Binding author: Geng Xun
 * Created: 2026-04-04
 * Updated: 2026-04-06  Geng Xun added photometry factory bindings plus AlbedoAtm and Anisotropic1 concrete model exposure
 *
 * Purpose: Expose photometric, atmospheric, and normalization model bindings including factories and concrete implementations.
 */

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>

#include <pybind11/pybind11.h>

#include "Anisotropic1.h"
#include "AlbedoAtm.h"
#include "AtmosModel.h"
#include "AtmosModelFactory.h"
#include "NormModel.h"
#include "NormModelFactory.h"
#include "PhotoModel.h"
#include "PhotoModelFactory.h"
#include "Pvl.h"
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

  py::class_<Isis::AtmosModel>(m, "AtmosModel")
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
      .def("atmos_tau", &Isis::AtmosModel::AtmosTau, "Get the atmospheric tau value")
      .def("atmos_wha", &Isis::AtmosModel::AtmosWha, "Get the atmospheric wha value")
      .def("atmos_hga", &Isis::AtmosModel::AtmosHga, "Get the atmospheric hga value")
      .def("atmos_tauref", &Isis::AtmosModel::AtmosTauref, "Get the atmospheric tauref value")
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
