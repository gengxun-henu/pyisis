// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS pattern matching classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Chip/Chip.h
 *   - isis/src/base/objs/AutoReg/AutoReg.h
 *   - isis/src/base/objs/MaximumCorrelation/MaximumCorrelation.h
 *   - isis/src/base/objs/Centroid/Centroid.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-04-08  Geng Xun added Centroid selection bindings for Chip-based pattern tests.
 * Updated: 2026-04-09  Geng Xun added MinimumDifference binding.
 * Updated: 2026-04-10  Geng Xun added Gruen and AdaptiveGruen bindings (AutoReg subclasses).
 * Purpose: Expose Chip, AutoReg, MaximumCorrelation, MinimumDifference, Gruen, AdaptiveGruen,
 *          and Centroid pattern matching classes to Python via pybind11.
 */

#include <limits>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "AdaptiveGruen.h"
#include "Chip.h"
#include "Centroid.h"
#include "AutoReg.h"
#include "Gruen.h"
#include "MaximumCorrelation.h"
#include "MinimumDifference.h"
#include "Cube.h"
#include "Affine.h"
#include "Statistics.h"
#include "Interpolator.h"
#include "Pvl.h"
#include "PvlGroup.h"
#include "helpers.h"

namespace py = pybind11;

void bind_base_pattern(py::module_ &m) {
  /**
   * @brief Bindings for the Isis::Chip class
   * Chip class provides functionality for extracting and manipulating small image chips
   * from larger cubes, useful for pattern matching and correlation.
   * @see Isis::Chip
   */
  py::class_<Isis::Chip>(m, "Chip")
      .def(py::init<>())
      // Configuration
      .def("set_size",
           &Isis::Chip::SetSize,
           py::arg("samples"), py::arg("lines"),
           "Set the size of the chip")
      .def("set_all_values",
           &Isis::Chip::SetAllValues,
           py::arg("value"),
           "Set all chip values to a constant")
      .def("set_value",
           &Isis::Chip::SetValue,
           py::arg("sample"), py::arg("line"), py::arg("value"),
           "Set a specific chip pixel value")
      .def("set_valid_range",
           &Isis::Chip::SetValidRange,
           py::arg("minimum") = Isis::ValidMinimum,
           py::arg("maximum") = Isis::ValidMaximum,
           "Set the valid pixel value range")
      .def("set_chip_position",
           &Isis::Chip::SetChipPosition,
           py::arg("sample"), py::arg("line"),
           "Set the chip position")
      .def("set_cube_position",
           &Isis::Chip::SetCubePosition,
           py::arg("sample"), py::arg("line"),
           "Set the cube position")
      .def("set_clip_polygon",
           &Isis::Chip::SetClipPolygon,
           py::arg("clip_polygon"),
           "Set the clipping polygon")
      .def("set_transform",
           &Isis::Chip::SetTransform,
           py::arg("affine"), py::arg("keep_poly") = true,
           "Set the affine transformation")
      .def("set_read_interpolator",
           &Isis::Chip::SetReadInterpolator,
           py::arg("type"),
           "Set the interpolation type for reading")
      // Query
      .def("samples", &Isis::Chip::Samples, "Get the number of samples")
      .def("lines", &Isis::Chip::Lines, "Get the number of lines")
      .def("file_name",
           [](const Isis::Chip &self) {
             return qStringToStdString(self.FileName());
           },
           "Get the source cube filename")
      .def("get_value",
           py::overload_cast<int, int>(&Isis::Chip::GetValue),
           py::arg("sample"), py::arg("line"),
           "Get a specific chip pixel value")
      .def("tack_sample", &Isis::Chip::TackSample, "Get the tack sample")
      .def("tack_line", &Isis::Chip::TackLine, "Get the tack line")
      .def("cube_sample", &Isis::Chip::CubeSample, "Get the cube sample position")
      .def("cube_line", &Isis::Chip::CubeLine, "Get the cube line position")
      .def("chip_sample", &Isis::Chip::ChipSample, "Get the chip sample position")
      .def("chip_line", &Isis::Chip::ChipLine, "Get the chip line position")
      .def("is_inside_chip",
           &Isis::Chip::IsInsideChip,
           py::arg("sample"), py::arg("line"),
           "Check if coordinates are inside the chip")
      .def("is_valid",
           py::overload_cast<int, int>(&Isis::Chip::IsValid),
           py::arg("sample"), py::arg("line"),
           "Check if a pixel is valid")
      .def("is_valid",
           py::overload_cast<double>(&Isis::Chip::IsValid),
           py::arg("percentage"),
           "Check if chip has sufficient valid pixels")
      .def("get_transform", &Isis::Chip::GetTransform, "Get the affine transformation")
      .def("get_read_interpolator", &Isis::Chip::GetReadInterpolator, "Get the interpolation type")
      // Operations
      .def("tack_cube",
           &Isis::Chip::TackCube,
           py::arg("cube_sample"), py::arg("cube_line"),
           "Tack the chip to a cube position")
      .def("load",
           py::overload_cast<Isis::Cube &, const double, const double, const int>(
               &Isis::Chip::Load),
           py::arg("cube"), py::arg("rotation") = 0.0, py::arg("scale") = 1.0, py::arg("band") = 1,
           py::keep_alive<1, 2>(),  // Keep cube alive as long as Chip exists
           "Load chip from cube")
      .def("load",
           py::overload_cast<Isis::Cube &, const Isis::Affine &, const bool &, const int>(
               &Isis::Chip::Load),
           py::arg("cube"), py::arg("affine"), py::arg("keep_poly") = true, py::arg("band") = 1,
           py::keep_alive<1, 2>(),  // Keep cube alive as long as Chip exists
           "Load chip from cube with affine transformation")
      .def("extract",
           py::overload_cast<int, int, int, int>(&Isis::Chip::Extract),
           py::arg("samples"), py::arg("lines"), py::arg("samp"), py::arg("line"),
           "Extract a sub-chip")
      .def("statistics",
           &Isis::Chip::Statistics,
           py::return_value_policy::reference_internal,
           "Get chip statistics")
      .def("write",
           [](Isis::Chip &self, const std::string &filename) {
             self.Write(stdStringToQString(filename));
           },
           py::arg("filename"),
           "Write chip to file")
      .def("__repr__", [](const Isis::Chip &self) {
        return "Chip(samples=" + std::to_string(self.Samples()) + ", " +
               "lines=" + std::to_string(self.Lines()) + ")";
      });

     /**
      * @brief Bindings for the Isis::Centroid selection helper.
      * Centroid performs a flood-fill selection on an input Chip starting from the
      * current chip position and marks qualifying pixels into a selection Chip.
      * @see Isis::Centroid
      */
     py::class_<Isis::Centroid>(m, "Centroid")
               .def(py::init<>())
               .def("select",
                          [](Isis::Centroid &self, Isis::Chip &input_chip, Isis::Chip &selection_chip) {
                               return self.select(&input_chip, &selection_chip);
                          },
                          py::arg("input_chip"), py::arg("selection_chip"),
                          py::keep_alive<1, 2>(),
                          py::keep_alive<1, 3>(),
                          "Select connected pixels within the configured DN range")
               .def("set_dn_range",
                          &Isis::Centroid::setDNRange,
                          py::arg("minimum_dn"), py::arg("maximum_dn"),
                          "Set the accepted DN range for centroid selection")
               .def("get_min_dn", &Isis::Centroid::getMinDN, "Get the current minimum DN")
               .def("get_max_dn", &Isis::Centroid::getMaxDN, "Get the current maximum DN")
               .def("__repr__", [](Isis::Centroid &self) {
                    return "Centroid(min_dn=" + std::to_string(self.getMinDN()) + ", " +
                                    "max_dn=" + std::to_string(self.getMaxDN()) + ")";
               });

  /**
   * @brief Bindings for the Isis::AutoReg class
   * AutoReg class provides functionality for automated image registration
   * and pattern matching between images.
   * @see Isis::AutoReg
   */
  py::class_<Isis::AutoReg> autoreg(m, "AutoReg");

  // RegisterStatus enum
  py::enum_<Isis::AutoReg::RegisterStatus>(autoreg, "RegisterStatus")
      .value("SuccessPixel", Isis::AutoReg::SuccessPixel)
      .value("SuccessSubPixel", Isis::AutoReg::SuccessSubPixel)
      .value("PatternChipNotEnoughValidData", Isis::AutoReg::PatternChipNotEnoughValidData)
      .value("FitChipNoData", Isis::AutoReg::FitChipNoData)
      .value("FitChipToleranceNotMet", Isis::AutoReg::FitChipToleranceNotMet)
      .value("SurfaceModelNotEnoughValidData", Isis::AutoReg::SurfaceModelNotEnoughValidData)
      .value("SurfaceModelSolutionInvalid", Isis::AutoReg::SurfaceModelSolutionInvalid)
      .value("SurfaceModelDistanceInvalid", Isis::AutoReg::SurfaceModelDistanceInvalid)
      .value("PatternZScoreNotMet", Isis::AutoReg::PatternZScoreNotMet)
      .value("AdaptiveAlgorithmFailed", Isis::AutoReg::AdaptiveAlgorithmFailed)
      .export_values();

  // GradientFilterType enum
  py::enum_<Isis::AutoReg::GradientFilterType>(autoreg, "GradientFilterType")
      .value("NoFilter", Isis::AutoReg::None)  // Renamed from "None" to avoid Python keyword
      .value("Sobel", Isis::AutoReg::Sobel)
      .export_values();

  autoreg
      // Chip access
      .def("pattern_chip",
           &Isis::AutoReg::PatternChip,
           py::return_value_policy::reference_internal,
           "Get the pattern chip")
      .def("search_chip",
           &Isis::AutoReg::SearchChip,
           py::return_value_policy::reference_internal,
           "Get the search chip")
      .def("fit_chip",
           &Isis::AutoReg::FitChip,
           py::return_value_policy::reference_internal,
           "Get the fit chip")
      .def("registration_pattern_chip",
           &Isis::AutoReg::RegistrationPatternChip,
           py::return_value_policy::reference_internal,
           "Get the registration pattern chip")
      .def("registration_search_chip",
           &Isis::AutoReg::RegistrationSearchChip,
           py::return_value_policy::reference_internal,
           "Get the registration search chip")
      .def("reduced_pattern_chip",
           &Isis::AutoReg::ReducedPatternChip,
           py::return_value_policy::reference_internal,
           "Get the reduced pattern chip")
      .def("reduced_search_chip",
           &Isis::AutoReg::ReducedSearchChip,
           py::return_value_policy::reference_internal,
           "Get the reduced search chip")
      .def("reduced_fit_chip",
           &Isis::AutoReg::ReducedFitChip,
           py::return_value_policy::reference_internal,
           "Get the reduced fit chip")
      // Configuration
      .def("set_sub_pixel_accuracy",
           &Isis::AutoReg::SetSubPixelAccuracy,
           py::arg("on"),
           "Set sub-pixel accuracy mode")
      .def("set_pattern_valid_percent",
           &Isis::AutoReg::SetPatternValidPercent,
           py::arg("percent"),
           "Set required valid pixel percentage for pattern chip")
      .def("set_subsearch_valid_percent",
           &Isis::AutoReg::SetSubsearchValidPercent,
           py::arg("percent"),
           "Set required valid pixel percentage for subsearch")
      .def("set_tolerance",
           &Isis::AutoReg::SetTolerance,
           py::arg("tolerance"),
           "Set fit tolerance")
      .def("set_chip_interpolator",
           [](Isis::AutoReg &self, const std::string &interpolator) {
             self.SetChipInterpolator(stdStringToQString(interpolator));
           },
           py::arg("interpolator"),
           "Set chip interpolator type")
      .def("set_surface_model_window_size",
           &Isis::AutoReg::SetSurfaceModelWindowSize,
           py::arg("size"),
           "Set surface model window size")
      .def("set_surface_model_distance_tolerance",
           &Isis::AutoReg::SetSurfaceModelDistanceTolerance,
           py::arg("distance"),
           "Set surface model distance tolerance")
      .def("set_reduction_factor",
           &Isis::AutoReg::SetReductionFactor,
           py::arg("reduction_factor"),
           "Set reduction factor")
      .def("set_pattern_z_score_minimum",
           &Isis::AutoReg::SetPatternZScoreMinimum,
           py::arg("minimum"),
           "Set minimum pattern z-score")
      .def("set_gradient_filter_type",
           [](Isis::AutoReg &self, const std::string &gradient_filter_type) {
             self.SetGradientFilterType(stdStringToQString(gradient_filter_type));
           },
           py::arg("gradient_filter_type"),
           "Set gradient filter type")
      // Query
      .def("gradient_filter_string",
           [](const Isis::AutoReg &self) {
             return qStringToStdString(self.GradientFilterString());
           },
           "Get gradient filter type as string")
      .def("sub_pixel_accuracy", &Isis::AutoReg::SubPixelAccuracy, "Get sub-pixel accuracy setting")
      .def("reduction_factor", &Isis::AutoReg::ReductionFactor, "Get reduction factor")
      .def("pattern_valid_percent", &Isis::AutoReg::PatternValidPercent, "Get pattern valid percent")
      .def("subsearch_valid_percent", &Isis::AutoReg::SubsearchValidPercent, "Get subsearch valid percent")
      .def("tolerance", &Isis::AutoReg::Tolerance, "Get tolerance")
      .def("window_size", &Isis::AutoReg::WindowSize, "Get window size")
      .def("distance_tolerance", &Isis::AutoReg::DistanceTolerance, "Get distance tolerance")
      .def("distance",
           [](Isis::AutoReg &self) {
             double samp_distance, line_distance;
             self.Distance(samp_distance, line_distance);
             return py::make_tuple(samp_distance, line_distance);
           },
           "Get registration distance (returns tuple of sample and line distances)")
      .def("success", &Isis::AutoReg::Success, "Check if registration was successful")
      .def("goodness_of_fit", &Isis::AutoReg::GoodnessOfFit, "Get goodness of fit")

      // NOTE: IsIdeal() is an inline method not fully defined in the ISIS C++ library headers,
      // causing compilation errors when binding with pybind11. This method cannot be bound
      // until it is properly implemented in the upstream source code.
      // See: isis/src/base/objs/AutoReg/AutoReg.h (inline bool IsIdeal(const Fit &fit) const)
      //.def("is_ideal",
      //     &Isis::AutoReg::IsIdeal,
      //     py::arg("fit"),
      //     "Check if fit is ideal")
      .def("chip_sample", &Isis::AutoReg::ChipSample, "Get chip sample position")
      .def("chip_line", &Isis::AutoReg::ChipLine, "Get chip line position")
      .def("cube_sample", &Isis::AutoReg::CubeSample, "Get cube sample position")
      .def("cube_line", &Isis::AutoReg::CubeLine, "Get cube line position")
      // Added: 2026-04-03 - expose remaining AutoReg query methods
      .def("minimum_z_score", &Isis::AutoReg::MinimumZScore,
           "Get minimum pattern z-score threshold")
      .def("z_scores",
           [](const Isis::AutoReg &self) {
             double z_score_min, z_score_max;
             self.ZScores(z_score_min, z_score_max);
             return py::make_tuple(z_score_min, z_score_max);
           },
           "Get z-scores of the pattern chip (returns tuple of z_score_min, z_score_max)")
      .def("registration_statistics", &Isis::AutoReg::RegistrationStatistics,
           "Get registration statistics as a Pvl object")
      .def("most_lenient_tolerance", &Isis::AutoReg::MostLenientTolerance,
           "Get the most lenient tolerance specific to algorithm")
      .def("algorithm_name",
           [](const Isis::AutoReg &self) {
             return qStringToStdString(self.AlgorithmName());
           },
           "Get the algorithm name")
      .def("reg_template", &Isis::AutoReg::RegTemplate,
           "Get registration template parameters as PvlGroup")
      .def("updated_template", &Isis::AutoReg::UpdatedTemplate,
           "Get updated registration template reflecting current settings as PvlGroup")
      // Registration operation
      .def("register", &Isis::AutoReg::Register, "Perform registration")
      .def("__repr__", [](const Isis::AutoReg &self) {
        std::string status = self.Success() ? "Success" : "Failed";
        return "AutoReg(status=" + status + ", " +
               "goodness_of_fit=" + std::to_string(self.GoodnessOfFit()) + ")";
      });

  /**
   * @brief Bindings for the Isis::MaximumCorrelation class
   * MaximumCorrelation implements maximum correlation pattern matching algorithm.
   * It finds the best match by computing correlation between pattern and subsearch chips.
   * Best fit = 1.0 (pattern and subsearch chips are identical).
   *
   * Source ISIS header: isis/src/base/objs/MaximumCorrelation/MaximumCorrelation.h
   * Source header author(s): not explicitly stated in upstream header
   * Binding author: Geng Xun
   * Created: 2026-04-02
   * Updated: 2026-04-02
   *
   * @see Isis::MaximumCorrelation
   * @see Isis::AutoReg
   * Added: 2026-04-02 - expose MaximumCorrelation concrete AutoReg implementation
   */
  py::class_<Isis::MaximumCorrelation, Isis::AutoReg>(m, "MaximumCorrelation")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),  // Keep Pvl alive as long as MaximumCorrelation exists
           "Construct a MaximumCorrelation object with PVL configuration")
      .def("__repr__", [](const Isis::MaximumCorrelation &self) {
        std::string status = self.Success() ? "Success" : "Failed";
        return "MaximumCorrelation(status=" + status + ", " +
               "goodness_of_fit=" + std::to_string(self.GoodnessOfFit()) + ")";
      });

  // Added: 2026-04-09 - MinimumDifference concrete AutoReg implementation
  py::class_<Isis::MinimumDifference, Isis::AutoReg>(m, "MinimumDifference")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct a MinimumDifference object with PVL configuration.")
      .def("ideal_fit",
           [](const Isis::MinimumDifference &) { return 0.0; },
           "Return the ideal fit value (0.0 = perfect match for MinimumDifference).")
      .def("most_lenient_tolerance",
           [](const Isis::MinimumDifference &) { return std::numeric_limits<double>::max(); },
           "Return the most lenient acceptable tolerance (DBL_MAX for MinimumDifference).")
      .def("__repr__", [](const Isis::MinimumDifference &self) {
        std::string status = self.Success() ? "Success" : "Failed";
        return "MinimumDifference(status=" + status + ", " +
               "goodness_of_fit=" + std::to_string(self.GoodnessOfFit()) + ")";
      });

  // ── Gruen ──────────────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::Gruen adaptive pattern matching algorithm.
  // Exposes constructor, inherited AutoReg interface, and Gruen-specific
  // constraint accessors. GruenTypes-specific return types (AffineRadio, etc.)
  // are not exposed; their numeric scalar getters are exposed directly.
  py::class_<Isis::Gruen, Isis::AutoReg>(m, "Gruen")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct a Gruen algorithm with PVL configuration.")
      .def("ideal_fit",
           [](const Isis::Gruen &) { return 0.0; },
           "Return the ideal fit value (0.0 = perfect match).")
      .def("get_spice_constraint",
           &Isis::Gruen::getSpiceConstraint,
           "Return the SPICE tolerance constraint from the config.")
      .def("get_affine_constraint",
           &Isis::Gruen::getAffineConstraint,
           "Return the Affine tolerance constraint from the config.")
      .def("__repr__", [](const Isis::Gruen &self) {
            std::string status = self.Success() ? "Success" : "Failed";
            return "Gruen(status=" + status +
                   ", goodness_of_fit=" + std::to_string(self.GoodnessOfFit()) + ")";
          });

  // ── AdaptiveGruen ──────────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::AdaptiveGruen. Constructor delegates to Gruen.
  py::class_<Isis::AdaptiveGruen, Isis::Gruen>(m, "AdaptiveGruen")
      .def(py::init<Isis::Pvl &>(),
           py::arg("pvl"),
           py::keep_alive<1, 2>(),
           "Construct an AdaptiveGruen algorithm with PVL configuration.")
      .def("ideal_fit",
           [](const Isis::AdaptiveGruen &) { return 0.0; },
           "Return the ideal fit value (0.0 = perfect match).")
      .def("__repr__", [](const Isis::AdaptiveGruen &self) {
            std::string status = self.Success() ? "Success" : "Failed";
            return "AdaptiveGruen(status=" + status +
                   ", goodness_of_fit=" + std::to_string(self.GoodnessOfFit()) + ")";
          });
}
