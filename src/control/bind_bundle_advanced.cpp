// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleMeasure.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleControlPoint.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleObservation.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleObservationVector.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleLidarRangeConstraint.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleLidarControlPoint.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/BundleLidarPointVector.h
// - reference/upstream_isis/src/control/objs/BundleResults/BundleResults.h
// - reference/upstream_isis/src/control/objs/BundleSolutionInfo/BundleSolutionInfo.h
// - reference/upstream_isis/src/control/objs/CsmBundleObservation/CsmBundleObservation.h
// - reference/upstream_isis/src/control/objs/BundleUtilities/IsisBundleObservation.h
// Source classes: BundleMeasure, BundleControlPoint, BundleObservation,
//                 BundleObservationVector, BundleLidarRangeConstraint,
//                 BundleLidarControlPoint, BundleLidarPointVector,
//                 BundleResults, BundleSolutionInfo,
//                 CsmBundleObservation, IsisBundleObservation
// Source header author(s): not explicitly stated in upstream headers
// Binding author: Geng Xun
// Created: 2026-03-24
// Updated: 2026-03-25  Geng Xun expanded advanced bundle-adjustment bindings and fixed Python exposure for control-point correction and sigma accessors
// Updated: 2026-04-10  Geng Xun re-enabled file; replaced boost::ublas bounded_vector accessors with lambda wrappers returning list; skipped SparseBlockRowMatrix/LinearAlgebra heavy methods
// Updated: 2026-04-10  Geng Xun added CsmBundleObservation and IsisBundleObservation (Batch 2) with constructor, number_parameters, parameter_list, bundle_output_csv.
// Updated: 2026-04-11  Geng Xun fixed BundleSolutionInfo null-safe filename accessors and used the pybind-safe BundleResults transfer helper.
// Updated: 2026-04-11  Geng Xun replaced non-existent BundleSolutionInfo helper calls with safe wrappers around the actual ISIS 9.0.0 API.
// Updated: 2026-04-11  Geng Xun added null-safe observation wrappers so default-constructed bundle observations return empty Python values instead of dereferencing uninitialized ISIS state.
// Purpose: pybind11 bindings for advanced ISIS bundle-adjustment classes

#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <QList>
#include <QString>
#include <QStringList>
#include <QVector>

#include "BundleControlPoint.h"
#include "BundleImage.h"
#include "BundleLidarControlPoint.h"
#include "BundleLidarPointVector.h"
#include "BundleLidarRangeConstraint.h"
#include "BundleMeasure.h"
#include "BundleObservation.h"
#include "BundleObservationSolveSettings.h"
#include "BundleObservationVector.h"
#include "BundleSettings.h"
#include "BundleTargetBody.h"
#include "Camera.h"
#include "ControlMeasure.h"
#include "ControlNet.h"
#include "ControlPoint.h"
#include "CsmBundleObservation.h"
#include "Distance.h"
#include "FileName.h"
#include "ImageList.h"
#include "IsisBundleObservation.h"
#include "MaximumLikelihoodWFunctions.h"
#include "SpicePosition.h"
#include "SpiceRotation.h"
#include "Statistics.h"
#include "SurfacePoint.h"
#include "helpers.h"

#include "BundleResults.h"
#include "BundleSolutionInfo.h"

namespace py = pybind11;

namespace
{
     /**
      * @brief Convert a QList of Statistics objects to a Python list.
      *
      * @param values QList of Statistics objects.
      * @return py::list Python list of Statistics objects.
      */
     py::list statisticsListToPyList(const QList<Isis::Statistics> &values)
     {
          py::list result;
          for (const Isis::Statistics &stat : values)
          {
               result.append(py::cast(stat));
          }
          return result;
     }

     /**
      * @brief Convert a QVector of Statistics objects to a Python list.
      *
      * @param values QVector of Statistics objects.
      * @return py::list Python list of Statistics objects.
      */
     py::list statisticsVectorToPyList(const QVector<Isis::Statistics> &values)
     {
          py::list result;
          for (const Isis::Statistics &stat : values)
          {
               result.append(py::cast(stat));
          }
          return result;
     }

     /**
      * @brief Convert a QStringList to a std::vector<std::string>.
      *
      * @param values QStringList to convert.
      * @return std::vector<std::string> converted vector.
      */
     std::vector<std::string> qStringListToVector(const QStringList &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          return result;
     }

     /**
      * @brief Convert a QList<QString> to a std::vector<std::string>.
      *
      * @param values QList<QString> to convert.
      * @return std::vector<std::string> converted vector.
      */
     std::vector<std::string> qListStringToVector(const QList<QString> &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          return result;
     }

     std::unique_ptr<Isis::BundleSolutionInfo> makeDefaultBundleSolutionInfo()
     {
          Isis::BundleSettingsQsp defaultSettings(new Isis::BundleSettings());
          Isis::BundleResults defaultResults;
          QList<Isis::ImageList *> emptyImages;

          return std::make_unique<Isis::BundleSolutionInfo>(
                    defaultSettings,
                    Isis::FileName(""),
                    Isis::FileName(""),
                    defaultResults,
                    emptyImages,
                    nullptr);
     }

     std::string bundleSolutionInfoInputControlNetFileName(const Isis::BundleSolutionInfo &self)
     {
          return qStringToStdString(self.inputControlNetFileName());
     }

     std::string bundleSolutionInfoInputLidarDataFileName(const Isis::BundleSolutionInfo &self)
     {
          return qStringToStdString(self.inputLidarDataFileName());
     }

     std::vector<std::string> csmBundleObservationParameterListSafe(Isis::CsmBundleObservation &self)
     {
          if (self.numberParameters() == 0)
          {
               return {};
          }

          return qStringListToVector(self.parameterList());
     }

     std::string csmBundleObservationBundleOutputCsvSafe(Isis::CsmBundleObservation &self, bool errorPropagation)
     {
          if (self.numberParameters() == 0)
          {
               return "";
          }

          return qStringToStdString(self.bundleOutputCSV(errorPropagation));
     }

     bool isisBundleObservationHasSolveSettings(Isis::IsisBundleObservation &self)
     {
          return !self.solveSettings().isNull();
     }

     int isisBundleObservationNumberPositionParametersSafe(Isis::IsisBundleObservation &self)
     {
          if (!isisBundleObservationHasSolveSettings(self))
          {
               return 0;
          }

          return self.numberPositionParameters();
     }

     int isisBundleObservationNumberPointingParametersSafe(Isis::IsisBundleObservation &self)
     {
          if (!isisBundleObservationHasSolveSettings(self))
          {
               return 0;
          }

          return self.numberPointingParameters();
     }

     int isisBundleObservationNumberParametersSafe(Isis::IsisBundleObservation &self)
     {
          if (!isisBundleObservationHasSolveSettings(self))
          {
               return 0;
          }

          return self.numberParameters();
     }

     std::vector<std::string> isisBundleObservationParameterListSafe(Isis::IsisBundleObservation &self)
     {
          if (!isisBundleObservationHasSolveSettings(self))
          {
               return {};
          }

          return qStringListToVector(self.parameterList());
     }

     std::string isisBundleObservationBundleOutputCsvSafe(Isis::IsisBundleObservation &self, bool errorPropagation)
     {
          if (!isisBundleObservationHasSolveSettings(self))
          {
               return "";
          }

          return qStringToStdString(self.bundleOutputCSV(errorPropagation));
     }
}

void bind_bundle_advanced(py::module_ &m)
{
     // ─── BundleMeasure ──────────────────────────────────────────────────
     py::class_<Isis::BundleMeasure, std::shared_ptr<Isis::BundleMeasure>> bundle_measure(m, "BundleMeasure");

     bundle_measure
         .def(py::init<Isis::ControlMeasure *, Isis::BundleControlPoint *>(),
              py::arg("control_measure"),
              py::arg("bundle_control_point"),
              py::keep_alive<1, 2>(),
              py::keep_alive<1, 3>())
         .def(py::init<const Isis::BundleMeasure &>(), py::arg("other"))
         .def("set_rejected", &Isis::BundleMeasure::setRejected, py::arg("reject"))
         .def("is_rejected", &Isis::BundleMeasure::isRejected)
         .def("camera", &Isis::BundleMeasure::camera, py::return_value_policy::reference_internal)
         .def("parent_control_point", &Isis::BundleMeasure::parentControlPoint,
              py::return_value_policy::reference_internal)
         .def("sample", &Isis::BundleMeasure::sample)
         .def("sample_residual", &Isis::BundleMeasure::sampleResidual)
         .def("line", &Isis::BundleMeasure::line)
         .def("line_residual", &Isis::BundleMeasure::lineResidual)
         .def("sigma", &Isis::BundleMeasure::sigma)
         .def("weight", &Isis::BundleMeasure::weight)
         .def("weight_sqrt", &Isis::BundleMeasure::weightSqrt)
         .def("residual_magnitude", &Isis::BundleMeasure::residualMagnitude)
         .def("x_focal_plane_residual", &Isis::BundleMeasure::xFocalPlaneResidual)
         .def("y_focal_plane_residual", &Isis::BundleMeasure::yFocalPlaneResidual)
         .def("cube_serial_number", [](const Isis::BundleMeasure &self)
              { return qStringToStdString(self.cubeSerialNumber()); })
         .def("focal_plane_computed_x", &Isis::BundleMeasure::focalPlaneComputedX)
         .def("focal_plane_computed_y", &Isis::BundleMeasure::focalPlaneComputedY)
         .def("focal_plane_measured_x", &Isis::BundleMeasure::focalPlaneMeasuredX)
         .def("focal_plane_measured_y", &Isis::BundleMeasure::focalPlaneMeasuredY)
         .def("observation_index", &Isis::BundleMeasure::observationIndex)
         .def("set_image", &Isis::BundleMeasure::setImage)
         .def("set_focal_plane_residuals_millimeters", &Isis::BundleMeasure::setFocalPlaneResidualsMillimeters)
         .def("set_sigma", &Isis::BundleMeasure::setSigma, py::arg("sigma"))
         .def("set_normals_position_block_index", &Isis::BundleMeasure::setNormalsPositionBlockIndex, py::arg("index"))
         .def("set_normals_pointing_block_index", &Isis::BundleMeasure::setNormalsPointingBlockIndex, py::arg("index"))
         .def("position_normals_block_index", &Isis::BundleMeasure::positionNormalsBlockIndex)
         .def("pointing_normals_block_index", &Isis::BundleMeasure::pointingNormalsBlockIndex)
         .def("copy", [](const Isis::BundleMeasure &self)
              { return Isis::BundleMeasure(self); })
         .def("__repr__", [](const Isis::BundleMeasure &self)
              { return "BundleMeasure(serial='" + qStringToStdString(self.cubeSerialNumber()) +
                       "', sample=" + std::to_string(self.sample()) +
                       ", line=" + std::to_string(self.line()) + ")"; });

     // ─── BundleControlPoint ─────────────────────────────────────────────
     py::class_<Isis::BundleControlPoint, std::shared_ptr<Isis::BundleControlPoint>> bundle_control_point(m, "BundleControlPoint");

     bundle_control_point
         .def(py::init([](Isis::BundleSettings &settings, Isis::ControlPoint *point)
                       {
                            Isis::BundleSettingsQsp settingsQsp(new Isis::BundleSettings(settings));
                            return std::make_shared<Isis::BundleControlPoint>(settingsQsp, point); }),
              py::arg("settings"),
              py::arg("point"),
              py::keep_alive<1, 3>())
         .def(py::init<const Isis::BundleControlPoint &>(), py::arg("other"))
         .def("compute_residuals", &Isis::BundleControlPoint::computeResiduals)
         .def("set_adjusted_surface_point", &Isis::BundleControlPoint::setAdjustedSurfacePoint, py::arg("surface_point"))
         .def("set_number_of_rejected_measures", &Isis::BundleControlPoint::setNumberOfRejectedMeasures, py::arg("num_rejected"))
         .def("set_rejected", &Isis::BundleControlPoint::setRejected, py::arg("reject"))
         .def("zero_number_of_rejected_measures", &Isis::BundleControlPoint::zeroNumberOfRejectedMeasures)
         .def("vtpv", &Isis::BundleControlPoint::vtpv)
         .def("vtpv_measures", &Isis::BundleControlPoint::vtpvMeasures)
         .def("raw_control_point", &Isis::BundleControlPoint::rawControlPoint,
              py::return_value_policy::reference_internal)
         .def("is_rejected", &Isis::BundleControlPoint::isRejected)
         .def("number_of_measures", &Isis::BundleControlPoint::numberOfMeasures)
         .def("number_of_rejected_measures", &Isis::BundleControlPoint::numberOfRejectedMeasures)
         .def("residual_rms", &Isis::BundleControlPoint::residualRms)
         .def("adjusted_surface_point", &Isis::BundleControlPoint::adjustedSurfacePoint)
         .def("id", [](const Isis::BundleControlPoint &self)
              { return qStringToStdString(self.id()); })
         .def("type", &Isis::BundleControlPoint::type)
         .def("coord_type_reports", &Isis::BundleControlPoint::coordTypeReports)
         .def("coord_type_bundle", &Isis::BundleControlPoint::coordTypeBundle)
         // boost::ublas bounded_vector<double,3> accessors wrapped to return Python list
         .def("corrections", [](Isis::BundleControlPoint &self) {
              auto &v = self.corrections();
              return std::vector<double>(v.begin(), v.end()); })
         .def("apriori_sigmas", [](Isis::BundleControlPoint &self) {
              auto &v = self.aprioriSigmas();
              return std::vector<double>(v.begin(), v.end()); })
         .def("adjusted_sigmas", [](Isis::BundleControlPoint &self) {
              auto &v = self.adjustedSigmas();
              return std::vector<double>(v.begin(), v.end()); })
         .def("weights", [](Isis::BundleControlPoint &self) {
              auto &v = self.weights();
              return std::vector<double>(v.begin(), v.end()); })
         .def("nic_vector", [](Isis::BundleControlPoint &self) {
              auto &v = self.nicVector();
              return std::vector<double>(v.begin(), v.end()); })
         // cholmod_q_matrix returns SparseBlockRowMatrix& which is not bound in Python; skipped

         .def("format_bundle_output_summary_string", [](const Isis::BundleControlPoint &self, bool error_propagation)
              { return qStringToStdString(self.formatBundleOutputSummaryString(error_propagation)); }, py::arg("error_propagation"))
         .def("format_bundle_output_detail_string", [](const Isis::BundleControlPoint &self, bool error_propagation, bool solve_radius)
              { return qStringToStdString(self.formatBundleOutputDetailString(error_propagation, solve_radius)); }, py::arg("error_propagation"), py::arg("solve_radius") = false)
         .def("__len__", &Isis::BundleControlPoint::numberOfMeasures)
         .def("__repr__", [](const Isis::BundleControlPoint &self)
              { return "BundleControlPoint(id='" + qStringToStdString(self.id()) +
                       "', measures=" + std::to_string(self.numberOfMeasures()) + ")"; });

     // ─── BundleObservation (abstract base class) ────────────────────────
     py::class_<Isis::BundleObservation, std::shared_ptr<Isis::BundleObservation>> bundle_observation(m, "BundleObservation");

     bundle_observation
         .def("set_index", &Isis::BundleObservation::setIndex, py::arg("n"))
         .def("index", &Isis::BundleObservation::index)
         .def("instrument_id", [](Isis::BundleObservation &self)
              { return qStringToStdString(self.instrumentId()); })
         .def("vtpv", &Isis::BundleObservation::vtpv)
         .def("image_names", [](Isis::BundleObservation &self)
              { return qStringListToVector(self.imageNames()); })
         .def("number_parameters", &Isis::BundleObservation::numberParameters)
         .def("parameter_list", [](Isis::BundleObservation &self)
              { return qStringListToVector(self.parameterList()); })
         .def("__repr__", [](Isis::BundleObservation &self)
              { return "BundleObservation(instrument_id='" + qStringToStdString(self.instrumentId()) +
                       "', index=" + std::to_string(self.index()) + ")"; });

     // ─── BundleObservationVector ────────────────────────────────────────
     py::class_<Isis::BundleObservationVector> bundle_observation_vector(m, "BundleObservationVector");

     bundle_observation_vector
         .def(py::init<>())
         .def(py::init<const Isis::BundleObservationVector &>(), py::arg("other"))
         .def("number_parameters", &Isis::BundleObservationVector::numberParameters)
         .def("observation_by_cube_serial_number", [](Isis::BundleObservationVector &self, const std::string &serial_number)
              { return self.observationByCubeSerialNumber(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("vtpv_contribution", &Isis::BundleObservationVector::vtpvContribution)
         .def("instrument_ids", [](const Isis::BundleObservationVector &self)
              { return qListStringToVector(self.instrumentIds()); })
         .def("observations_by_inst_id", [](const Isis::BundleObservationVector &self, const std::string &instrument_id) -> py::list
              {
                   py::list result;
                   QList<Isis::BundleObservationQsp> observations = self.observationsByInstId(stdStringToQString(instrument_id));
                   for (const Isis::BundleObservationQsp &obs : observations)
                   {
                        result.append(py::cast(obs));
                   }
                   return result; }, py::arg("instrument_id"))
         .def("__len__", &Isis::BundleObservationVector::size)
         .def("__getitem__", [](Isis::BundleObservationVector &self, int index) -> Isis::BundleObservationQsp
              {
                   if (index < 0 || index >= self.size())
                   {
                        throw py::index_error("BundleObservationVector index out of range");
                   }
                   return self[index]; }, py::arg("index"))
         .def("__repr__", [](const Isis::BundleObservationVector &self)
              { return "BundleObservationVector(size=" + std::to_string(self.size()) + ")"; });

     // ─── BundleLidarRangeConstraint ─────────────────────────────────────
     py::class_<Isis::BundleLidarRangeConstraint, std::shared_ptr<Isis::BundleLidarRangeConstraint>> bundle_lidar_range_constraint(m, "BundleLidarRangeConstraint");

     bundle_lidar_range_constraint
         .def(py::init<const Isis::BundleLidarRangeConstraint &>(), py::arg("other"))
         .def("vtpv", &Isis::BundleLidarRangeConstraint::vtpv)
         .def("compute_range", &Isis::BundleLidarRangeConstraint::computeRange)
         .def("range_observed", &Isis::BundleLidarRangeConstraint::rangeObserved)
         .def("range_computed", &Isis::BundleLidarRangeConstraint::rangeComputed)
         .def("range_observed_sigma", &Isis::BundleLidarRangeConstraint::rangeObservedSigma)
         .def("range_adjusted_sigma", &Isis::BundleLidarRangeConstraint::rangeAdjustedSigma)
         .def("format_bundle_output_string", [](Isis::BundleLidarRangeConstraint &self, bool error_prop)
              { return qStringToStdString(self.formatBundleOutputString(error_prop)); }, py::arg("error_propagation") = false)
         .def("copy", [](const Isis::BundleLidarRangeConstraint &self)
              { return Isis::BundleLidarRangeConstraint(self); })
         .def("__repr__", [](Isis::BundleLidarRangeConstraint &self)
              { return "BundleLidarRangeConstraint(observed=" + std::to_string(self.rangeObserved()) +
                       ", computed=" + std::to_string(self.rangeComputed()) + ")"; });

     // ─── BundleLidarControlPoint ────────────────────────────────────────
     py::class_<Isis::BundleLidarControlPoint, Isis::BundleControlPoint, std::shared_ptr<Isis::BundleLidarControlPoint>> bundle_lidar_control_point(m, "BundleLidarControlPoint");

     bundle_lidar_control_point
         .def("initialize_range_constraints", &Isis::BundleLidarControlPoint::initializeRangeConstraints)
         .def("compute_residuals", &Isis::BundleLidarControlPoint::computeResiduals)
         .def("range_constraint", &Isis::BundleLidarControlPoint::rangeConstraint, py::arg("n"))
         .def("vtpv_range_contribution", &Isis::BundleLidarControlPoint::vtpvRangeContribution)
         .def("number_range_constraints", &Isis::BundleLidarControlPoint::numberRangeConstraints)
         .def("range", &Isis::BundleLidarControlPoint::range)
         .def("sigma_range", &Isis::BundleLidarControlPoint::sigmaRange)
         .def("__repr__", [](Isis::BundleLidarControlPoint &self)
              { return "BundleLidarControlPoint(id='" + qStringToStdString(self.id()) +
                       "', range_constraints=" + std::to_string(self.numberRangeConstraints()) + ")"; });

     // ─── BundleLidarPointVector ─────────────────────────────────────────
     py::class_<Isis::BundleLidarPointVector> bundle_lidar_point_vector(m, "BundleLidarPointVector");

     bundle_lidar_point_vector
         .def(py::init<>())
         .def(py::init<const Isis::BundleLidarPointVector &>(), py::arg("other"))
         .def("compute_measure_residuals", &Isis::BundleLidarPointVector::computeMeasureResiduals)
         .def("vtpv_contribution", &Isis::BundleLidarPointVector::vtpvContribution)
         .def("vtpv_measure_contribution", &Isis::BundleLidarPointVector::vtpvMeasureContribution)
         .def("vtpv_range_contribution", &Isis::BundleLidarPointVector::vtpvRangeContribution)
         .def("__len__", &Isis::BundleLidarPointVector::size)
         .def("__getitem__", [](Isis::BundleLidarPointVector &self, int index) -> Isis::BundleLidarControlPointQsp
              {
                   if (index < 0 || index >= self.size())
                   {
                        throw py::index_error("BundleLidarPointVector index out of range");
                   }
                   return self[index]; }, py::arg("index"))
         .def("copy", [](const Isis::BundleLidarPointVector &self)
              { return Isis::BundleLidarPointVector(self); })
         .def("__repr__", [](const Isis::BundleLidarPointVector &self)
              { return "BundleLidarPointVector(size=" + std::to_string(self.size()) + ")"; });

     // ─── BundleResults ──────────────────────────────────────────────────
     py::class_<Isis::BundleResults> bundle_results(m, "BundleResults");

     bundle_results
         .def(py::init<>())
         // NOTE: BundleResults copy constructor causes segfault with ISIS 9.0.0
         // .def(py::init([](const Isis::BundleResults &other)
         //               {
         //                    auto copy = std::make_unique<Isis::BundleResults>(other);
         //                    return copy; }),
         //      py::arg("other"))
         .def("initialize", &Isis::BundleResults::initialize)
         .def("resize_sigma_statistics_vectors", &Isis::BundleResults::resizeSigmaStatisticsVectors, py::arg("number_images"))
         // ── Residual setters ──
         .def("set_rms_xy_residuals", &Isis::BundleResults::setRmsXYResiduals, py::arg("rx"), py::arg("ry"), py::arg("rxy"))
         // ── Sigma range setters ──
         .def("set_sigma_coord1_range", [](Isis::BundleResults &self, const Isis::Distance &min_dist, const Isis::Distance &max_dist, const std::string &min_point_id, const std::string &max_point_id)
              { self.setSigmaCoord1Range(min_dist, max_dist, stdStringToQString(min_point_id), stdStringToQString(max_point_id)); }, py::arg("min_dist"), py::arg("max_dist"), py::arg("min_point_id"), py::arg("max_point_id"))
         .def("set_sigma_coord2_range", [](Isis::BundleResults &self, const Isis::Distance &min_dist, const Isis::Distance &max_dist, const std::string &min_point_id, const std::string &max_point_id)
              { self.setSigmaCoord2Range(min_dist, max_dist, stdStringToQString(min_point_id), stdStringToQString(max_point_id)); }, py::arg("min_dist"), py::arg("max_dist"), py::arg("min_point_id"), py::arg("max_point_id"))
         .def("set_sigma_coord3_range", [](Isis::BundleResults &self, const Isis::Distance &min_dist, const Isis::Distance &max_dist, const std::string &min_point_id, const std::string &max_point_id)
              { self.setSigmaCoord3Range(min_dist, max_dist, stdStringToQString(min_point_id), stdStringToQString(max_point_id)); }, py::arg("min_dist"), py::arg("max_dist"), py::arg("min_point_id"), py::arg("max_point_id"))
         .def("set_rms_from_sigma_statistics", &Isis::BundleResults::setRmsFromSigmaStatistics, py::arg("rms_coord1"), py::arg("rms_coord2"), py::arg("rms_coord3"))
         // ── Observation/parameter count setters ──
         .def("set_number_rejected_observations", &Isis::BundleResults::setNumberRejectedObservations, py::arg("number_observations"))
         .def("set_number_image_observations", &Isis::BundleResults::setNumberImageObservations, py::arg("number_observations"))
         .def("set_number_lidar_image_observations", &Isis::BundleResults::setNumberLidarImageObservations, py::arg("number_lidar_observations"))
         .def("set_number_observations", &Isis::BundleResults::setNumberObservations, py::arg("number_observations"))
         .def("set_number_image_parameters", &Isis::BundleResults::setNumberImageParameters, py::arg("number_parameters"))
         .def("set_number_constrained_point_parameters", &Isis::BundleResults::setNumberConstrainedPointParameters, py::arg("number_parameters"))
         .def("set_number_constrained_lidar_point_parameters", &Isis::BundleResults::setNumberConstrainedLidarPointParameters, py::arg("number_parameters"))
         .def("reset_number_constrained_point_parameters", &Isis::BundleResults::resetNumberConstrainedPointParameters)
         .def("increment_number_constrained_point_parameters", &Isis::BundleResults::incrementNumberConstrainedPointParameters, py::arg("increment_amount"))
         .def("reset_number_constrained_image_parameters", &Isis::BundleResults::resetNumberConstrainedImageParameters)
         .def("increment_number_constrained_image_parameters", &Isis::BundleResults::incrementNumberConstrainedImageParameters, py::arg("increment_amount"))
         .def("reset_number_constrained_target_parameters", &Isis::BundleResults::resetNumberConstrainedTargetParameters)
         .def("increment_number_constrained_target_parameters", &Isis::BundleResults::incrementNumberConstrainedTargetParameters, py::arg("increment_amount"))
         .def("set_number_lidar_range_constraints", &Isis::BundleResults::setNumberLidarRangeConstraints, py::arg("number_constraints"))
         .def("set_number_unknown_parameters", &Isis::BundleResults::setNumberUnknownParameters, py::arg("number_parameters"))
         // ── Convergence/solution setters ──
         .def("set_degrees_of_freedom", &Isis::BundleResults::setDegreesOfFreedom, py::arg("degrees_of_freedom"))
         .def("set_sigma0", &Isis::BundleResults::setSigma0, py::arg("sigma0"))
         .def("set_elapsed_time", &Isis::BundleResults::setElapsedTime, py::arg("time"))
         .def("set_elapsed_time_error_prop", &Isis::BundleResults::setElapsedTimeErrorProp, py::arg("time"))
         .def("set_converged", &Isis::BundleResults::setConverged, py::arg("converged"))
         .def("set_iterations", &Isis::BundleResults::setIterations, py::arg("iterations"))
         .def("set_observations", &Isis::BundleResults::setObservations, py::arg("observations"))
         .def("set_rejection_limit", &Isis::BundleResults::setRejectionLimit, py::arg("rejection_limit"))
         // ── Fixed/held/ignored counters ──
         .def("increment_fixed_points", &Isis::BundleResults::incrementFixedPoints)
         .def("number_fixed_points", &Isis::BundleResults::numberFixedPoints)
         .def("increment_held_images", &Isis::BundleResults::incrementHeldImages)
         .def("number_held_images", &Isis::BundleResults::numberHeldImages)
         .def("increment_ignored_points", &Isis::BundleResults::incrementIgnoredPoints)
         .def("number_ignored_points", &Isis::BundleResults::numberIgnoredPoints)
         // ── Maximum likelihood ──
         .def("increment_maximum_likelihood_model_index", &Isis::BundleResults::incrementMaximumLikelihoodModelIndex)
         .def("number_maximum_likelihood_models", &Isis::BundleResults::numberMaximumLikelihoodModels)
         .def("maximum_likelihood_model_index", &Isis::BundleResults::maximumLikelihoodModelIndex)
         .def("maximum_likelihood_median_r2_residuals", &Isis::BundleResults::maximumLikelihoodMedianR2Residuals)
         // ── Residual statistics accessors ──
         .def("rms_image_sample_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsImageSampleResiduals()); })
         .def("rms_image_line_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsImageLineResiduals()); })
         .def("rms_image_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsImageResiduals()); })
         .def("rms_lidar_image_sample_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsLidarImageSampleResiduals()); })
         .def("rms_lidar_image_line_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsLidarImageLineResiduals()); })
         .def("rms_lidar_image_residuals", [](const Isis::BundleResults &self)
              { return statisticsListToPyList(self.rmsLidarImageResiduals()); })
         // ── Sigma statistics vectors ──
         .def("rms_image_x_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageXSigmas()); })
         .def("rms_image_y_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageYSigmas()); })
         .def("rms_image_z_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageZSigmas()); })
         .def("rms_image_ra_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageRASigmas()); })
         .def("rms_image_dec_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageDECSigmas()); })
         .def("rms_image_twist_sigmas", [](const Isis::BundleResults &self)
              { return statisticsVectorToPyList(self.rmsImageTWISTSigmas()); })
         // ── Sigma range accessors ──
         .def("coord_type_reports", &Isis::BundleResults::coordTypeReports)
         .def("min_sigma_coord1_distance", &Isis::BundleResults::minSigmaCoord1Distance)
         .def("max_sigma_coord1_distance", &Isis::BundleResults::maxSigmaCoord1Distance)
         .def("min_sigma_coord2_distance", &Isis::BundleResults::minSigmaCoord2Distance)
         .def("max_sigma_coord2_distance", &Isis::BundleResults::maxSigmaCoord2Distance)
         .def("min_sigma_coord3_distance", &Isis::BundleResults::minSigmaCoord3Distance)
         .def("max_sigma_coord3_distance", &Isis::BundleResults::maxSigmaCoord3Distance)
         .def("min_sigma_coord1_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.minSigmaCoord1PointId()); })
         .def("max_sigma_coord1_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.maxSigmaCoord1PointId()); })
         .def("min_sigma_coord2_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.minSigmaCoord2PointId()); })
         .def("max_sigma_coord2_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.maxSigmaCoord2PointId()); })
         .def("min_sigma_coord3_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.minSigmaCoord3PointId()); })
         .def("max_sigma_coord3_point_id", [](const Isis::BundleResults &self)
              { return qStringToStdString(self.maxSigmaCoord3PointId()); })
         .def("sigma_coord1_statistics_rms", &Isis::BundleResults::sigmaCoord1StatisticsRms)
         .def("sigma_coord2_statistics_rms", &Isis::BundleResults::sigmaCoord2StatisticsRms)
         .def("sigma_coord3_statistics_rms", &Isis::BundleResults::sigmaCoord3StatisticsRms)
         // ── RMS residuals ──
         .def("rms_rx", &Isis::BundleResults::rmsRx)
         .def("rms_ry", &Isis::BundleResults::rmsRy)
         .def("rms_rxy", &Isis::BundleResults::rmsRxy)
         .def("rejection_limit", &Isis::BundleResults::rejectionLimit)
         // ── Observation/parameter counts ──
         .def("number_rejected_observations", &Isis::BundleResults::numberRejectedObservations)
         .def("number_observations", &Isis::BundleResults::numberObservations)
         .def("number_image_observations", &Isis::BundleResults::numberImageObservations)
         .def("number_lidar_image_observations", &Isis::BundleResults::numberLidarImageObservations)
         .def("number_image_parameters", &Isis::BundleResults::numberImageParameters)
         .def("number_constrained_point_parameters", &Isis::BundleResults::numberConstrainedPointParameters)
         .def("number_constrained_image_parameters", &Isis::BundleResults::numberConstrainedImageParameters)
         .def("number_constrained_target_parameters", &Isis::BundleResults::numberConstrainedTargetParameters)
         .def("number_lidar_range_constraint_equations", &Isis::BundleResults::numberLidarRangeConstraintEquations)
         .def("number_unknown_parameters", &Isis::BundleResults::numberUnknownParameters)
         // ── Solution status ──
         .def("degrees_of_freedom", &Isis::BundleResults::degreesOfFreedom)
         .def("sigma0", &Isis::BundleResults::sigma0)
         .def("elapsed_time", &Isis::BundleResults::elapsedTime)
         .def("elapsed_time_error_prop", &Isis::BundleResults::elapsedTimeErrorProp)
         .def("converged", &Isis::BundleResults::converged)
         .def("iterations", &Isis::BundleResults::iterations)
         // ── Observation access ──
         .def("observations", [](const Isis::BundleResults &self) -> const Isis::BundleObservationVector &
              { return self.observations(); }, py::return_value_policy::reference_internal)
         // ── Repr ──
         // NOTE: copy method removed - BundleResults copy constructor causes segfault with ISIS 9.0.0
         .def("__repr__", [](const Isis::BundleResults &self)
              { return "BundleResults(converged=" + std::string(self.converged() ? "True" : "False") +
                       ", sigma0=" + std::to_string(self.sigma0()) +
                       ", iterations=" + std::to_string(self.iterations()) + ")"; });

     // ─── BundleSolutionInfo ─────────────────────────────────────────────
     py::class_<Isis::BundleSolutionInfo> bundle_solution_info(m, "BundleSolutionInfo");

     bundle_solution_info
         .def(py::init(&makeDefaultBundleSolutionInfo))
         .def("set_run_time", [](Isis::BundleSolutionInfo &self, const std::string &run_time)
              { self.setRunTime(stdStringToQString(run_time)); }, py::arg("run_time"))
         .def("set_name", [](Isis::BundleSolutionInfo &self, const std::string &name)
              { self.setName(stdStringToQString(name)); }, py::arg("name"))
         .def("set_output_statistics", [](Isis::BundleSolutionInfo &self, const Isis::BundleResults &statistics_results)
              { self.setOutputStatistics(statistics_results); }, py::arg("statistics_results"))
         .def("set_output_control_name", [](Isis::BundleSolutionInfo &self, const std::string &name)
              { self.setOutputControlName(stdStringToQString(name)); }, py::arg("name"))
         .def("id", [](const Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.id()); })
         .def("input_control_net_file_name", &bundleSolutionInfoInputControlNetFileName)
         .def("output_control_net_file_name", [](const Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.outputControlNetFileName()); })
         .def("output_control_name", [](const Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.outputControlName()); })
         .def("input_lidar_data_file_name", &bundleSolutionInfoInputLidarDataFileName)
         .def("bundle_settings", &Isis::BundleSolutionInfo::bundleSettings)
         // NOTE: bundle_results() commented out - upstream bundleResults() returns by value
         // which invokes BundleResults copy constructor causing segfault with ISIS 9.0.0
         // .def("bundle_results", [](Isis::BundleSolutionInfo &self)
         //      {
         //          // bundleResults() returns by value, so we create a new object on the heap
         //          auto results = std::make_unique<Isis::BundleResults>(self.bundleResults());
         //          return results.release();
         //      }, py::return_value_policy::take_ownership)
         .def("run_time", [](const Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.runTime()); })
         .def("name", [](const Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.name()); })
         .def("saved_bundle_output_filename", [](Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.savedBundleOutputFilename()); })
         .def("saved_images_filename", [](Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.savedImagesFilename()); })
         .def("saved_points_filename", [](Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.savedPointsFilename()); })
         .def("saved_residuals_filename", [](Isis::BundleSolutionInfo &self)
              { return qStringToStdString(self.savedResidualsFilename()); })
         .def("output_text", &Isis::BundleSolutionInfo::outputText)
         .def("output_images_csv", &Isis::BundleSolutionInfo::outputImagesCSV)
         .def("output_points_csv", &Isis::BundleSolutionInfo::outputPointsCSV)
         .def("output_lidar_csv", &Isis::BundleSolutionInfo::outputLidarCSV)
         .def("output_residuals", &Isis::BundleSolutionInfo::outputResiduals)
         .def("surface_point_coord_name", [](const Isis::BundleSolutionInfo &self, Isis::SurfacePoint::CoordinateType type, Isis::SurfacePoint::CoordIndex coord_index)
              { return qStringToStdString(self.surfacePointCoordName(type, coord_index)); }, py::arg("type"), py::arg("coord_index"))
         .def("__repr__", [](const Isis::BundleSolutionInfo &self)
              { return "BundleSolutionInfo(name='" + qStringToStdString(self.name()) +
                       "', run_time='" + qStringToStdString(self.runTime()) + "')"; });

  // Added: 2026-04-10 - CsmBundleObservation and IsisBundleObservation (Batch 2)

  // ─── CsmBundleObservation ────────────────────────────────────────────────
  py::class_<Isis::CsmBundleObservation,
             Isis::BundleObservation,
             std::shared_ptr<Isis::CsmBundleObservation>>(m, "CsmBundleObservation")
      .def(py::init<>(), "Construct a default CsmBundleObservation.")
      .def("number_parameters",
           &Isis::CsmBundleObservation::numberParameters,
           "Return the total number of solve parameters for this observation.")
      .def("parameter_list",
             &csmBundleObservationParameterListSafe,
           "Return a list of parameter name strings.")
      .def("bundle_output_csv",
             &csmBundleObservationBundleOutputCsvSafe,
           py::arg("error_propagation") = false,
           "Return a CSV string summarising the observation solve results.")
      .def("__repr__", [](Isis::CsmBundleObservation &self) {
           return "CsmBundleObservation(params=" +
                  std::to_string(self.numberParameters()) + ")";
      });

  // ─── IsisBundleObservation ────────────────────────────────────────────────
  py::class_<Isis::IsisBundleObservation,
             Isis::BundleObservation,
             std::shared_ptr<Isis::IsisBundleObservation>>(m, "IsisBundleObservation")
      .def(py::init<>(), "Construct a default IsisBundleObservation.")
      .def("number_parameters",
           &isisBundleObservationNumberParametersSafe,
           "Return the total number of solve parameters.")
      .def("number_position_parameters",
           &isisBundleObservationNumberPositionParametersSafe,
           "Return the number of position solve parameters.")
      .def("number_pointing_parameters",
           &isisBundleObservationNumberPointingParametersSafe,
           "Return the number of pointing solve parameters.")
      .def("parameter_list",
           &isisBundleObservationParameterListSafe,
           "Return a list of parameter name strings.")
      .def("bundle_output_csv",
           &isisBundleObservationBundleOutputCsvSafe,
           py::arg("error_propagation") = false,
           "Return a CSV string summarising the observation solve results.")
      .def("spice_position",
           [](Isis::IsisBundleObservation &self) {
               return self.spicePosition();
           },
           py::return_value_policy::reference_internal,
           "Return the SpicePosition pointer for this observation (may be nullptr).")
      .def("spice_rotation",
           [](Isis::IsisBundleObservation &self) {
               return self.spiceRotation();
           },
           py::return_value_policy::reference_internal,
           "Return the SpiceRotation pointer for this observation (may be nullptr).")
      .def("__repr__", [](Isis::IsisBundleObservation &self) {
           return "IsisBundleObservation(params=" +
                  std::to_string(isisBundleObservationNumberParametersSafe(self)) + ")";
      });
}

