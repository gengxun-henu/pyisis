// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-04-08  Geng Xun added ControlNetStatistics summary/getter bindings and related control-core exposure updates
// Updated: 2026-04-10  Geng Xun added LidarControlPoint binding (inherits ControlPoint) with range/sigma/time/simultaneous methods.
// Updated: 2026-04-10  Geng Xun added ControlNetVersioner binding with file/ControlNet constructors and network metadata accessors.
// Updated: 2026-04-10  Geng Xun removed private default constructor from ControlNetVersioner binding (upstream has it private).
// Updated: 2026-04-11  Geng Xun reused top-level Spice interpolation enums inside BundleObservationSolveSettings to avoid duplicate pybind enum registration.
// Purpose: pybind11 bindings for ISIS control network core classes, filters, and bundle-control helpers

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>
#include <stdexcept>
#include <string>
#include <algorithm>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <QList>
#include <QString>
#include <QStringList>
#include <QVariant>
#include <QVector>

#include "BundleImage.h"
#include "Camera.h"
#include "BundleSettings.h"
#include "BundleObservationSolveSettings.h"
#include "BundleTargetBody.h"
#include "ControlNetFilter.h"
#include "ControlNetValidMeasure.h"
#include "ControlNetVersioner.h"
#include "ControlMeasure.h"
#include "ControlMeasureLogData.h"
#include "ControlNetDiff.h"
#include "ControlNet.h"
#include "ControlNetStatistics.h"
#include "ControlPoint.h"
#include "ControlPointList.h"
#include "ControlPointV0001.h"
#include "ControlPointV0002.h"
#include "ControlPointV0003.h"
#include "LidarControlPoint.h"
#include "iTime.h"
#include "FileName.h"
#include "MaximumLikelihoodWFunctions.h"
#include "MeasureValidationResults.h"
#include "Pvl.h"
#include "PvlKeyword.h"
#include "PvlObject.h"
#include "Progress.h"
#include "SpicePosition.h"
#include "SpiceRotation.h"
#include "Statistics.h"
#include "SurfacePoint.h"
#include "helpers.h"

namespace py = pybind11;

/**
 * @brief conversion from Qt container types to std::vector of strings, including QList<QString>,
 * QStringList, and QVector<QString>. These functions are used for converting data from Qt container
 * types to std::vector of strings, which can then be easily converted to Python lists of strings using pybind11.
 * The conversion functions iterate over the elements of the input Qt container and convert each QString element to a
 * std::string using the qStringToStdString helper function, then store the converted strings in a std::vector that is
 * returned to the caller.
 *
 * @author Geng Xun
 * @date 2026-03-21
 */
namespace
{
     std::vector<std::string> qListToStdVector(const QList<QString> &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          return result;
     }

     std::vector<std::string> qStringListToStdVector(const QStringList &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          return result;
     }

     std::vector<std::string> qStringVectorToStdVector(const QVector<QString> &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          return result;
     }

     std::vector<std::string> qSetToSortedStdVector(const QSet<QString> &values)
     {
          std::vector<std::string> result;
          result.reserve(values.size());
          for (const QString &value : values)
          {
               result.push_back(qStringToStdString(value));
          }
          std::sort(result.begin(), result.end());
          return result;
     }

     std::vector<double> qListDoubleToStdVector(const QList<double> &values)
     {
          std::vector<double> result;
          result.reserve(values.size());
          for (double value : values)
          {
               result.push_back(value);
          }
          return result;
     }

     QStringList stdVectorToQStringList(const std::vector<std::string> &values)
     {
          QStringList result;
          for (const std::string &value : values)
          {
               result.append(stdStringToQString(value));
          }
          return result;
     }

     QList<double> stdVectorToQList(const std::vector<double> &values)
     {
          QList<double> result;
          for (double value : values)
          {
               result.append(value);
          }
          return result;
     }

     QList<Isis::BundleObservationSolveSettings> stdVectorToQList(
         const std::vector<Isis::BundleObservationSolveSettings> &values)
     {
          QList<Isis::BundleObservationSolveSettings> result;
          for (const Isis::BundleObservationSolveSettings &value : values)
          {
               result.append(value);
          }
          return result;
     }

     py::list bundleObservationSolveSettingsToPyList(
         const QList<Isis::BundleObservationSolveSettings> &values)
     {
          py::list result;
          for (const Isis::BundleObservationSolveSettings &value : values)
          {
               result.append(py::cast(value));
          }
          return result;
     }

     /**
      * Convert a QList of QStringLists to a vector of vector of strings. This is used for converting the result of ControlMeasure::PrintableMeasureData() to a Python list of lists of strings.
      * @param values The QList of QStringLists to convert.
      * @return A vector of vector of strings containing the same data as the input QList of QString
      * Lists, but in a format that can be easily converted to a Python list of lists of strings.
      * @note This function is necessary because pybind11 does not have built-in support for converting QList of QStringLists to Python lists of lists of strings, so we need to manually convert the data to a format that pybind11 can handle.
      * @internal
      *  @history 2024-06-01 Geng Xun - Initial implementation of qNestedListToStdVector
      * @todo Add error handling for cases where the input QList of QStringLists contains null pointers or invalid data. Consider adding support for converting other nested Qt container types to
      */
     std::vector<std::vector<std::string>> qNestedListToStdVector(const QList<QList<QString>> &values)
     {
          std::vector<std::vector<std::string>> result;
          result.reserve(values.size());
          for (const QList<QString> &entry : values)
          {
               result.push_back(qListToStdVector(entry));
          }
          return result;
     }

     /**
      * Convert a QList of ControlMeasure pointers to a Python list of ControlMeasure objects.
      * @param measures The QList of ControlMeasure pointers to convert.
      * @param parent The parent Python object to associate with the ControlMeasure objects.
      * @return A Python list of ControlMeasure objects.
      * @note The ControlMeasure objects are returned with a reference_internal policy to ensure they are not deleted when the
      * Python reference goes out of scope.
      *
      * @history 2026-03-21 Geng Xun - initial implementation.
      * @internal
      */
     py::list measuresToPyList(const QList<Isis::ControlMeasure *> &measures, py::handle parent)
     {
          py::list result;
          for (Isis::ControlMeasure *measure : measures)
          {
               result.append(py::cast(measure, py::return_value_policy::reference_internal, parent));
          }
          return result;
     }

     /**
      * Convert a QList of ControlPoint pointers to a Python list of ControlPoint objects.
      * @param points The QList of ControlPoint pointers to convert.
      * @param parent The parent Python object to associate with the ControlPoint objects.
      * @return A Python list of ControlPoint objects.
      * @note The ControlPoint objects are returned with a reference_internal policy to ensure they are not deleted when the
      * Python reference goes out of scope.
      *
      * example usage:
      * @code
      * control_net = ControlNet()
      * # ... populate control_net with ControlPoints ...
      * points = pointsToPyList(control_net.points(), control_net)
      * @endcode
      *
      * @history 2026-03-21 Geng Xun - initial implementation.
      * @internal
      */
     py::list pointsToPyList(const QList<Isis::ControlPoint *> &points, py::handle parent)
     {
          py::list result;
          for (Isis::ControlPoint *point : points)
          {
               result.append(py::cast(point, py::return_value_policy::reference_internal, parent));
          }
          return result;
     }

     /**
      * Convert a QList of ControlPoint pointers to a Python list of ControlPoint objects, taking ownership of the objects.
      * @param points The QList of ControlPoint pointers to convert.
      * @return A Python list of ControlPoint objects.
      * @note The ControlPoint objects are returned with a take_ownership policy to ensure they are deleted when the Python
      * reference goes out of scope. It is different from the pointsToPyList function which returns the ControlPoint objects
      * with a reference_internal policy to ensure they are not deleted when the Python reference goes out of scope.
      *
      * example usage:
      * @code
      * control_net = ControlNet()
      * # ... populate control_net with ControlPoints ...
      * taken_points = takenPointsToPyList(control_net.points())
      * @endcode
      *
      * @history 2026-03-21 Geng Xun - initial implementation.
      * @internal
      */
     py::list takenPointsToPyList(QList<Isis::ControlPoint *> points)
     {
          py::list result;
          for (Isis::ControlPoint *point : points)
          {
               result.append(py::cast(point, py::return_value_policy::take_ownership));
          }
          return result;
     }

     py::list logDataToPyList(const QVector<Isis::ControlMeasureLogData> &entries)
     {
          py::list result;
          for (const Isis::ControlMeasureLogData &entry : entries)
          {
               result.append(py::cast(entry));
          }
          return result;
     }

     py::list printableMeasureDataToPyList(const QList<QStringList> &entries)
     {
          py::list result;
          for (const QStringList &entry : entries)
          {
               result.append(py::cast(qStringListToStdVector(entry)));
          }
          return result;
     }

     Isis::MaximumLikelihoodWFunctions::Model toMaximumLikelihoodWFunctionsModel(
         Isis::BundleSettings::MaximumLikelihoodModel model)
     {
          switch (model)
          {
          case Isis::BundleSettings::NoMaximumLikelihoodEstimator:
               throw std::invalid_argument("NoMaximumLikelihoodEstimator cannot be added as an active maximum likelihood model");
          case Isis::BundleSettings::Huber:
               return Isis::MaximumLikelihoodWFunctions::Huber;
          case Isis::BundleSettings::ModifiedHuber:
               return Isis::MaximumLikelihoodWFunctions::HuberModified;
          case Isis::BundleSettings::Welsch:
               return Isis::MaximumLikelihoodWFunctions::Welsch;
          case Isis::BundleSettings::Chen:
               return Isis::MaximumLikelihoodWFunctions::Chen;
          }

          throw std::invalid_argument("Unknown BundleSettings maximum likelihood model");
     }

     Isis::BundleSettings::MaximumLikelihoodModel fromMaximumLikelihoodWFunctionsModel(
         Isis::MaximumLikelihoodWFunctions::Model model)
     {
          switch (model)
          {
          case Isis::MaximumLikelihoodWFunctions::Huber:
               return Isis::BundleSettings::Huber;
          case Isis::MaximumLikelihoodWFunctions::HuberModified:
               return Isis::BundleSettings::ModifiedHuber;
          case Isis::MaximumLikelihoodWFunctions::Welsch:
               return Isis::BundleSettings::Welsch;
          case Isis::MaximumLikelihoodWFunctions::Chen:
               return Isis::BundleSettings::Chen;
          }

          throw std::invalid_argument("Unknown maximum likelihood estimator model");
     }

     py::list maximumLikelihoodEstimatorModelsToPyList(
         const QList<QPair<Isis::MaximumLikelihoodWFunctions::Model, double>> &models)
     {
          py::list result;
          for (const auto &model : models)
          {
               result.append(py::make_tuple(fromMaximumLikelihoodWFunctionsModel(model.first), model.second));
          }
          return result;
     }

     py::list csmParameterListToPyList(const QStringList &values)
     {
          py::list result;
          for (const QString &value : values)
          {
               result.append(qStringToStdString(value));
          }
          return result;
     }

     std::set<int> targetSolveCodesToStdSet(
         const std::vector<Isis::BundleTargetBody::TargetSolveCodes> &values)
     {
          std::set<int> result;
          for (Isis::BundleTargetBody::TargetSolveCodes value : values)
          {
               result.insert(static_cast<int>(value));
          }
          return result;
     }
}

void bind_control_core(py::module_ &m)
{
     py::class_<Isis::ControlMeasureLogData> control_measure_log_data(m, "ControlMeasureLogData");

     py::enum_<Isis::ControlMeasureLogData::NumericLogDataType>(control_measure_log_data, "NumericLogDataType")
         .value("InvalidNumericLogDataType", Isis::ControlMeasureLogData::InvalidNumericLogDataType)
         .value("Obsolete_Eccentricity", Isis::ControlMeasureLogData::Obsolete_Eccentricity)
         .value("GoodnessOfFit", Isis::ControlMeasureLogData::GoodnessOfFit)
         .value("MinimumPixelZScore", Isis::ControlMeasureLogData::MinimumPixelZScore)
         .value("MaximumPixelZScore", Isis::ControlMeasureLogData::MaximumPixelZScore)
         .value("PixelShift", Isis::ControlMeasureLogData::PixelShift)
         .value("WholePixelCorrelation", Isis::ControlMeasureLogData::WholePixelCorrelation)
         .value("SubPixelCorrelation", Isis::ControlMeasureLogData::SubPixelCorrelation)
         .value("Obsolete_AverageResidual", Isis::ControlMeasureLogData::Obsolete_AverageResidual);

     control_measure_log_data
         .def(py::init<>())
         .def(py::init<Isis::ControlMeasureLogData::NumericLogDataType>(), py::arg("data_type"))
         .def(py::init<const Isis::PvlKeyword &>(), py::arg("keyword_rep"))
         .def(py::init<Isis::ControlMeasureLogData::NumericLogDataType, double>(),
              py::arg("data_type"),
              py::arg("value"))
         .def(py::init<const Isis::ControlMeasureLogData &>(), py::arg("other"))
         .def("set_numerical_value", &Isis::ControlMeasureLogData::SetNumericalValue, py::arg("value"))
         .def("set_data_type", &Isis::ControlMeasureLogData::SetDataType, py::arg("data_type"))
         .def("get_numerical_value", &Isis::ControlMeasureLogData::GetNumericalValue)
         .def("get_data_type", &Isis::ControlMeasureLogData::GetDataType)
         .def("get_value", [](const Isis::ControlMeasureLogData &self)
              { return self.GetValue().toDouble(); })
         .def("is_valid", &Isis::ControlMeasureLogData::IsValid)
         .def("to_keyword", &Isis::ControlMeasureLogData::ToKeyword)
         .def("name_to_data_type", [](const Isis::ControlMeasureLogData &self, const std::string &name)
              { return self.NameToDataType(stdStringToQString(name)); }, py::arg("name"))
         .def("data_type_to_name", [](const Isis::ControlMeasureLogData &self, Isis::ControlMeasureLogData::NumericLogDataType type)
              { return qStringToStdString(self.DataTypeToName(type)); }, py::arg("type"))
         .def_property_readonly_static("maximum_numeric_log_data_type", [](py::object)
                                       { return Isis::ControlMeasureLogData::MaximumNumericLogDataType; })
         .def("copy", [](const Isis::ControlMeasureLogData &self)
              { return Isis::ControlMeasureLogData(self); })
         .def("__repr__", [](const Isis::ControlMeasureLogData &self)
              { return "ControlMeasureLogData(value=" + std::to_string(self.GetNumericalValue()) + ")"; });

     /**
      * @brief Bindings for ControlMeasure class. The ControlMeasure class represents a single measure in a control point, which is a specific observation of a feature in an image. The bindings include methods for setting and getting various properties of the ControlMeasure, such as its coordinates, date/time, diameter, edit lock status, focal plane measurements, residuals, and more. The ControlMeasure class also includes enumerations for measure type, status, modification type, and data fields. The bindings allow Python users to create and manipulate ControlMeasure objects in a way that is consistent with the C++ API, while also ensuring that memory management is handled correctly through the use of py::return_value_policy::reference_internal.
      * @param m The pybind11 module to which the ControlMeasure bindings will be added.
      * @note The ControlMeasure objects are returned with a reference_internal policy to ensure they are not deleted when the Python reference goes out of scope. It is important to ensure that the parent object
      * is kept alive as long as the ControlMeasure objects are being used in Python to prevent dangling references.
      *
      */
     py::class_<Isis::ControlMeasure> control_measure(m, "ControlMeasure");

     py::enum_<Isis::ControlMeasure::MeasureType>(control_measure, "MeasureType")
         .value("Candidate", Isis::ControlMeasure::Candidate)
         .value("Manual", Isis::ControlMeasure::Manual)
         .value("RegisteredPixel", Isis::ControlMeasure::RegisteredPixel)
         .value("RegisteredSubPixel", Isis::ControlMeasure::RegisteredSubPixel);

     py::enum_<Isis::ControlMeasure::Status>(control_measure, "Status")
         .value("Success", Isis::ControlMeasure::Success)
         .value("MeasureLocked", Isis::ControlMeasure::MeasureLocked);

     py::enum_<Isis::ControlMeasure::ModType>(control_measure, "ModType")
         .value("IgnoredModified", Isis::ControlMeasure::IgnoredModified);

     py::enum_<Isis::ControlMeasure::DataField>(control_measure, "DataField")
         .value("AprioriLine", Isis::ControlMeasure::AprioriLine)
         .value("AprioriSample", Isis::ControlMeasure::AprioriSample)
         .value("ChooserName", Isis::ControlMeasure::ChooserName)
         .value("CubeSerialNumber", Isis::ControlMeasure::CubeSerialNumber)
         .value("Coordinate", Isis::ControlMeasure::Coordinate)
         .value("DateTime", Isis::ControlMeasure::DateTime)
         .value("Diameter", Isis::ControlMeasure::Diameter)
         .value("EditLock", Isis::ControlMeasure::EditLock)
         .value("Rejected", Isis::ControlMeasure::Rejected)
         .value("FocalPlaneMeasured", Isis::ControlMeasure::FocalPlaneMeasured)
         .value("FocalPlaneComputed", Isis::ControlMeasure::FocalPlaneComputed)
         .value("Ignore", Isis::ControlMeasure::Ignore)
         .value("SampleResidual", Isis::ControlMeasure::SampleResidual)
         .value("LineResidual", Isis::ControlMeasure::LineResidual)
         .value("SampleSigma", Isis::ControlMeasure::SampleSigma)
         .value("LineSigma", Isis::ControlMeasure::LineSigma)
         .value("Type", Isis::ControlMeasure::Type);

     control_measure
         .def(py::init<>())
         .def(py::init<const Isis::ControlMeasure &>(), py::arg("other"))
         .def("parent", [](Isis::ControlMeasure &self) -> Isis::ControlPoint *
              { return self.Parent(); }, py::return_value_policy::reference_internal)
         .def("set_apriori_line", &Isis::ControlMeasure::SetAprioriLine, py::arg("apriori_line"))
         .def("set_apriori_sample", &Isis::ControlMeasure::SetAprioriSample, py::arg("apriori_sample"))
         .def("set_chooser_name", py::overload_cast<>(&Isis::ControlMeasure::SetChooserName))
         .def("set_chooser_name", [](Isis::ControlMeasure &self, const std::string &name)
              { return self.SetChooserName(stdStringToQString(name)); }, py::arg("name"))
         .def("set_coordinate", py::overload_cast<double, double>(&Isis::ControlMeasure::SetCoordinate), py::arg("sample"), py::arg("line"))
         .def("set_coordinate", py::overload_cast<double, double, Isis::ControlMeasure::MeasureType>(&Isis::ControlMeasure::SetCoordinate), py::arg("sample"), py::arg("line"), py::arg("measure_type"))
         .def("set_cube_serial_number", [](Isis::ControlMeasure &self, const std::string &serial_number)
              { return self.SetCubeSerialNumber(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("set_date_time", py::overload_cast<>(&Isis::ControlMeasure::SetDateTime))
         .def("set_date_time", [](Isis::ControlMeasure &self, const std::string &date_time)
              { return self.SetDateTime(stdStringToQString(date_time)); }, py::arg("date_time"))
         .def("set_diameter", &Isis::ControlMeasure::SetDiameter, py::arg("diameter"))
         .def("set_edit_lock", &Isis::ControlMeasure::SetEditLock, py::arg("edit_lock"))
         .def("set_focal_plane_measured", &Isis::ControlMeasure::SetFocalPlaneMeasured, py::arg("x"), py::arg("y"))
         .def("set_focal_plane_computed", &Isis::ControlMeasure::SetFocalPlaneComputed, py::arg("x"), py::arg("y"))
         .def("set_ignored", &Isis::ControlMeasure::SetIgnored, py::arg("ignored"))
         .def("set_line_sigma", &Isis::ControlMeasure::SetLineSigma, py::arg("line_sigma"))
         .def("set_rejected", &Isis::ControlMeasure::SetRejected, py::arg("rejected"))
         .def("set_residual", &Isis::ControlMeasure::SetResidual, py::arg("sample_residual"), py::arg("line_residual"))
         .def("set_sample_sigma", &Isis::ControlMeasure::SetSampleSigma, py::arg("sample_sigma"))
         .def("set_type", &Isis::ControlMeasure::SetType, py::arg("measure_type"))
         .def("delete_log_data", &Isis::ControlMeasure::DeleteLogData, py::arg("data_type"))
         .def("has_log_data", &Isis::ControlMeasure::HasLogData, py::arg("data_type"))
         .def("set_log_data", &Isis::ControlMeasure::SetLogData, py::arg("log_data"))
         .def("update_log_data", &Isis::ControlMeasure::UpdateLogData, py::arg("log_data"))
         .def("get_apriori_line", &Isis::ControlMeasure::GetAprioriLine)
         .def("get_apriori_sample", &Isis::ControlMeasure::GetAprioriSample)
         .def("get_chooser_name", [](const Isis::ControlMeasure &self)
              { return qStringToStdString(self.GetChooserName()); })
         .def("has_chooser_name", &Isis::ControlMeasure::HasChooserName)
         .def("get_cube_serial_number", [](const Isis::ControlMeasure &self)
              { return qStringToStdString(self.GetCubeSerialNumber()); })
         .def("get_date_time", [](const Isis::ControlMeasure &self)
              { return qStringToStdString(self.GetDateTime()); })
         .def("has_date_time", &Isis::ControlMeasure::HasDateTime)
         .def("get_diameter", &Isis::ControlMeasure::GetDiameter)
         .def("get_log_data", &Isis::ControlMeasure::GetLogData, py::arg("data_type"))
         .def("get_log_value", [](const Isis::ControlMeasure &self, long data_type)
              { return self.GetLogValue(data_type).toDouble(); }, py::arg("data_type"))
         .def("is_edit_locked", &Isis::ControlMeasure::IsEditLocked)
         .def("is_rejected", &Isis::ControlMeasure::IsRejected)
         .def("get_focal_plane_computed_x", &Isis::ControlMeasure::GetFocalPlaneComputedX)
         .def("get_focal_plane_computed_y", &Isis::ControlMeasure::GetFocalPlaneComputedY)
         .def("get_focal_plane_measured_x", &Isis::ControlMeasure::GetFocalPlaneMeasuredX)
         .def("get_focal_plane_measured_y", &Isis::ControlMeasure::GetFocalPlaneMeasuredY)
         .def("get_measure_data", [](const Isis::ControlMeasure &self, const std::string &name)
              { return self.GetMeasureData(stdStringToQString(name)); }, py::arg("name"))
         .def("is_ignored", &Isis::ControlMeasure::IsIgnored)
         .def("is_measured", &Isis::ControlMeasure::IsMeasured)
         .def("is_registered", &Isis::ControlMeasure::IsRegistered)
         .def("is_statistically_relevant", &Isis::ControlMeasure::IsStatisticallyRelevant, py::arg("field"))
         .def("get_line", &Isis::ControlMeasure::GetLine)
         .def("get_line_residual", &Isis::ControlMeasure::GetLineResidual)
         .def("get_line_sigma", &Isis::ControlMeasure::GetLineSigma)
         .def("get_log_data_entries", [](const Isis::ControlMeasure &self)
              { return logDataToPyList(self.GetLogDataEntries()); })
         .def("get_residual_magnitude", &Isis::ControlMeasure::GetResidualMagnitude)
         .def("get_sample", &Isis::ControlMeasure::GetSample)
         .def("get_sample_residual", &Isis::ControlMeasure::GetSampleResidual)
         .def("get_sample_sigma", &Isis::ControlMeasure::GetSampleSigma)
         .def("get_type", &Isis::ControlMeasure::GetType)
         .def("get_point_id", [](const Isis::ControlMeasure &self)
              { return qStringToStdString(self.GetPointId()); })
         .def("get_sample_shift", &Isis::ControlMeasure::GetSampleShift)
         .def("get_line_shift", &Isis::ControlMeasure::GetLineShift)
         .def("get_pixel_shift", &Isis::ControlMeasure::GetPixelShift)
         .def("get_measure_data_names", []()
              { return qStringVectorToStdVector(Isis::ControlMeasure::GetMeasureDataNames()); })
         .def("printable_class_data", [](const Isis::ControlMeasure &self)
              { return printableMeasureDataToPyList(self.PrintableClassData()); })
         .def_static("measure_type_to_string", [](Isis::ControlMeasure::MeasureType type)
                     { return qStringToStdString(Isis::ControlMeasure::MeasureTypeToString(type)); }, py::arg("measure_type"))
         .def_static("string_to_measure_type", [](const std::string &name)
                     { return Isis::ControlMeasure::StringToMeasureType(stdStringToQString(name)); }, py::arg("name"))
         .def("get_measure_type_string", [](const Isis::ControlMeasure &self)
              { return qStringToStdString(self.GetMeasureTypeString()); })
         .def("copy", [](const Isis::ControlMeasure &self)
              { return Isis::ControlMeasure(self); })
         .def("__eq__", &Isis::ControlMeasure::operator==, py::arg("other"))
         .def("__ne__", &Isis::ControlMeasure::operator!=, py::arg("other"))
         .def("__repr__", [](const Isis::ControlMeasure &self)
              { return "ControlMeasure(serial='" + qStringToStdString(self.GetCubeSerialNumber()) + "', sample=" + std::to_string(self.GetSample()) + ", line=" + std::to_string(self.GetLine()) + ")"; });

     py::class_<Isis::ControlPoint> control_point(m, "ControlPoint");

     py::enum_<Isis::ControlPoint::PointType>(control_point, "PointType")
         .value("Fixed", Isis::ControlPoint::Fixed)
         .value("Constrained", Isis::ControlPoint::Constrained)
         .value("Free", Isis::ControlPoint::Free);

     py::enum_<Isis::ControlPoint::Status>(control_point, "Status")
         .value("Failure", Isis::ControlPoint::Failure)
         .value("Success", Isis::ControlPoint::Success)
         .value("PointLocked", Isis::ControlPoint::PointLocked);

     py::enum_<Isis::ControlPoint::ConstraintStatus>(control_point, "ConstraintStatus")
         .value("Coord1Constrained", Isis::ControlPoint::Coord1Constrained)
         .value("Coord2Constrained", Isis::ControlPoint::Coord2Constrained)
         .value("Coord3Constrained", Isis::ControlPoint::Coord3Constrained);

     py::enum_<Isis::ControlPoint::ModType>(control_point, "ModType")
         .value("EditLockModified", Isis::ControlPoint::EditLockModified)
         .value("IgnoredModified", Isis::ControlPoint::IgnoredModified)
         .value("TypeModified", Isis::ControlPoint::TypeModified);

     py::enum_<Isis::ControlPoint::SurfacePointSource::Source>(control_point, "SurfacePointSource")
         .value("None", Isis::ControlPoint::SurfacePointSource::None)
         .value("User", Isis::ControlPoint::SurfacePointSource::User)
         .value("AverageOfMeasures", Isis::ControlPoint::SurfacePointSource::AverageOfMeasures)
         .value("Reference", Isis::ControlPoint::SurfacePointSource::Reference)
         .value("Basemap", Isis::ControlPoint::SurfacePointSource::Basemap)
         .value("BundleSolution", Isis::ControlPoint::SurfacePointSource::BundleSolution);

     py::enum_<Isis::ControlPoint::RadiusSource::Source>(control_point, "RadiusSource")
         .value("None", Isis::ControlPoint::RadiusSource::None)
         .value("User", Isis::ControlPoint::RadiusSource::User)
         .value("AverageOfMeasures", Isis::ControlPoint::RadiusSource::AverageOfMeasures)
         .value("Ellipsoid", Isis::ControlPoint::RadiusSource::Ellipsoid)
         .value("DEM", Isis::ControlPoint::RadiusSource::DEM)
         .value("BundleSolution", Isis::ControlPoint::RadiusSource::BundleSolution);

     control_point
         .def(py::init<>())
         .def(py::init<const Isis::ControlPoint &>(), py::arg("other"))
         .def(py::init([](const std::string &id)
                       { return Isis::ControlPoint(stdStringToQString(id)); }),
              py::arg("id"))
         .def("parent", [](Isis::ControlPoint &self) -> Isis::ControlNet *
              { return self.Parent(); }, py::return_value_policy::reference_internal)
         .def("load", &Isis::ControlPoint::Load, py::arg("pvl_object"))
         .def("add_measure", [](Isis::ControlPoint &self, const Isis::ControlMeasure &measure)
              { self.Add(new Isis::ControlMeasure(measure)); }, py::arg("measure"))
         .def("delete_measure", py::overload_cast<Isis::ControlMeasure *>(&Isis::ControlPoint::Delete), py::arg("measure"))
         .def("delete_measure", [](Isis::ControlPoint &self, const std::string &serial_number)
              { return self.Delete(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("delete_measure", py::overload_cast<int>(&Isis::ControlPoint::Delete), py::arg("index"))
         .def("reset_apriori", &Isis::ControlPoint::ResetApriori)
         .def("get_measure", [](Isis::ControlPoint &self, const std::string &serial_number) -> Isis::ControlMeasure *
              { return self.GetMeasure(stdStringToQString(serial_number)); }, py::arg("serial_number"), py::return_value_policy::reference_internal)
         .def("get_measure", py::overload_cast<int>(&Isis::ControlPoint::GetMeasure), py::arg("index"), py::return_value_policy::reference_internal)
         .def("has_ref_measure", &Isis::ControlPoint::HasRefMeasure)
         .def("get_ref_measure", py::overload_cast<>(&Isis::ControlPoint::GetRefMeasure), py::return_value_policy::reference_internal)
         .def("set_chooser_name", [](Isis::ControlPoint &self, const std::string &name)
              { return self.SetChooserName(stdStringToQString(name)); }, py::arg("name"))
         .def("set_date_time", [](Isis::ControlPoint &self, const std::string &date_time)
              { return self.SetDateTime(stdStringToQString(date_time)); }, py::arg("date_time"))
         .def("set_edit_lock", &Isis::ControlPoint::SetEditLock, py::arg("edit_lock"))
         .def("set_id", [](Isis::ControlPoint &self, const std::string &id)
              { return self.SetId(stdStringToQString(id)); }, py::arg("id"))
         .def("set_ref_measure", [](Isis::ControlPoint &self, Isis::ControlMeasure &measure)
              { return self.SetRefMeasure(&measure); }, py::arg("measure"))
         .def("set_ref_measure", py::overload_cast<int>(&Isis::ControlPoint::SetRefMeasure), py::arg("index"))
         .def("set_ref_measure", [](Isis::ControlPoint &self, const std::string &serial_number)
              { return self.SetRefMeasure(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("set_rejected", &Isis::ControlPoint::SetRejected, py::arg("rejected"))
         .def("set_ignored", &Isis::ControlPoint::SetIgnored, py::arg("ignored"))
         .def("set_adjusted_surface_point", &Isis::ControlPoint::SetAdjustedSurfacePoint, py::arg("surface_point"))
         .def("set_type", &Isis::ControlPoint::SetType, py::arg("point_type"))
         .def("set_apriori_radius_source", &Isis::ControlPoint::SetAprioriRadiusSource, py::arg("source"))
         .def("set_apriori_radius_source_file", [](Isis::ControlPoint &self, const std::string &source_file)
              { return self.SetAprioriRadiusSourceFile(stdStringToQString(source_file)); }, py::arg("source_file"))
         .def("set_apriori_surface_point", &Isis::ControlPoint::SetAprioriSurfacePoint, py::arg("surface_point"))
         .def("set_apriori_surface_point_source", &Isis::ControlPoint::SetAprioriSurfacePointSource, py::arg("source"))
         .def("set_apriori_surface_point_source_file", [](Isis::ControlPoint &self, const std::string &source_file)
              { return self.SetAprioriSurfacePointSourceFile(stdStringToQString(source_file)); }, py::arg("source_file"))
         .def("compute_apriori", &Isis::ControlPoint::ComputeApriori)
         .def("compute_residuals", &Isis::ControlPoint::ComputeResiduals)
         .def("compute_residuals_millimeters", &Isis::ControlPoint::ComputeResiduals_Millimeters)
         .def("get_adjusted_surface_point", &Isis::ControlPoint::GetAdjustedSurfacePoint)
         .def("get_best_surface_point", &Isis::ControlPoint::GetBestSurfacePoint)
         .def("get_chooser_name", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetChooserName()); })
         .def("get_date_time", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetDateTime()); })
         .def("is_edit_locked", &Isis::ControlPoint::IsEditLocked)
         .def("is_rejected", &Isis::ControlPoint::IsRejected)
         .def("get_id", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetId()); })
         .def("is_ignored", &Isis::ControlPoint::IsIgnored)
         .def("is_valid", &Isis::ControlPoint::IsValid)
         .def("is_invalid", &Isis::ControlPoint::IsInvalid)
         .def("is_free", &Isis::ControlPoint::IsFree)
         .def("is_fixed", &Isis::ControlPoint::IsFixed)
         .def("has_apriori_coordinates", &Isis::ControlPoint::HasAprioriCoordinates)
         .def("is_constrained", &Isis::ControlPoint::IsConstrained)
         .def("is_coord1_constrained", &Isis::ControlPoint::IsCoord1Constrained)
         .def("is_coord2_constrained", &Isis::ControlPoint::IsCoord2Constrained)
         .def("is_coord3_constrained", &Isis::ControlPoint::IsCoord3Constrained)
         .def("number_of_constrained_coordinates", &Isis::ControlPoint::NumberOfConstrainedCoordinates)
         .def_static("point_type_to_string", [](Isis::ControlPoint::PointType type)
                     { return qStringToStdString(Isis::ControlPoint::PointTypeToString(type)); }, py::arg("point_type"))
         .def_static("string_to_point_type", [](const std::string &name)
                     { return Isis::ControlPoint::StringToPointType(stdStringToQString(name)); }, py::arg("name"))
         .def("get_point_type_string", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetPointTypeString()); })
         .def("get_type", &Isis::ControlPoint::GetType)
         .def_static("radius_source_to_string", [](Isis::ControlPoint::RadiusSource::Source source)
                     { return qStringToStdString(Isis::ControlPoint::RadiusSourceToString(source)); }, py::arg("source"))
         .def_static("string_to_radius_source", [](const std::string &name)
                     { return Isis::ControlPoint::StringToRadiusSource(stdStringToQString(name)); }, py::arg("name"))
         .def("get_radius_source_string", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetRadiusSourceString()); })
         .def_static("surface_point_source_to_string", [](Isis::ControlPoint::SurfacePointSource::Source source)
                     { return qStringToStdString(Isis::ControlPoint::SurfacePointSourceToString(source)); }, py::arg("source"))
         .def_static("string_to_surface_point_source", [](const std::string &name)
                     { return Isis::ControlPoint::StringToSurfacePointSource(stdStringToQString(name)); }, py::arg("name"))
         .def("get_surface_point_source_string", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetSurfacePointSourceString()); })
         .def("get_apriori_surface_point", &Isis::ControlPoint::GetAprioriSurfacePoint)
         .def("get_apriori_radius_source", &Isis::ControlPoint::GetAprioriRadiusSource)
         .def("has_apriori_radius_source_file", &Isis::ControlPoint::HasAprioriRadiusSourceFile)
         .def("get_apriori_radius_source_file", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetAprioriRadiusSourceFile()); })
         .def("get_apriori_surface_point_source", &Isis::ControlPoint::GetAprioriSurfacePointSource)
         .def("has_apriori_surface_point_source_file", &Isis::ControlPoint::HasAprioriSurfacePointSourceFile)
         .def("get_apriori_surface_point_source_file", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetAprioriSurfacePointSourceFile()); })
         .def("get_num_measures", &Isis::ControlPoint::GetNumMeasures)
         .def("get_num_valid_measures", &Isis::ControlPoint::GetNumValidMeasures)
         .def("get_num_locked_measures", &Isis::ControlPoint::GetNumLockedMeasures)
         .def("has_serial_number", [](const Isis::ControlPoint &self, const std::string &serial_number)
              { return self.HasSerialNumber(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("has_chooser_name", &Isis::ControlPoint::HasChooserName)
         .def("has_date_time", &Isis::ControlPoint::HasDateTime)
         .def("index_of", [](const Isis::ControlPoint &self, Isis::ControlMeasure &measure, bool throws)
              { return self.IndexOf(&measure, throws); }, py::arg("measure"), py::arg("throws") = true)
         .def("index_of", [](const Isis::ControlPoint &self, const std::string &serial_number, bool throws)
              { return self.IndexOf(stdStringToQString(serial_number), throws); }, py::arg("serial_number"), py::arg("throws") = true)
         .def("index_of_ref_measure", &Isis::ControlPoint::IndexOfRefMeasure)
         .def("is_reference_explicit", &Isis::ControlPoint::IsReferenceExplicit)
         .def("get_reference_sn", [](const Isis::ControlPoint &self)
              { return qStringToStdString(self.GetReferenceSN()); })
         .def("get_statistic", py::overload_cast<long>(&Isis::ControlPoint::GetStatistic, py::const_), py::arg("data_type"))
         .def("get_measures", [](Isis::ControlPoint &self, bool exclude_ignored)
              { return measuresToPyList(self.getMeasures(exclude_ignored), py::cast(&self)); }, py::arg("exclude_ignored") = false)
         .def("get_cube_serial_numbers", [](const Isis::ControlPoint &self)
              { return qListToStdVector(self.getCubeSerialNumbers()); })
         .def("__getitem__", [](Isis::ControlPoint &self, const std::string &serial_number) -> Isis::ControlMeasure *
              { return self[stdStringToQString(serial_number)]; }, py::arg("serial_number"), py::return_value_policy::reference_internal)
         .def("__getitem__", [](Isis::ControlPoint &self, int index) -> Isis::ControlMeasure *
              { return self[index]; }, py::arg("index"), py::return_value_policy::reference_internal)
         .def("__len__", &Isis::ControlPoint::GetNumMeasures)
         .def("__eq__", &Isis::ControlPoint::operator==, py::arg("other"))
         .def("__ne__", &Isis::ControlPoint::operator!=, py::arg("other"))
         .def("zero_number_of_rejected_measures", &Isis::ControlPoint::ZeroNumberOfRejectedMeasures)
         .def("set_number_of_rejected_measures", &Isis::ControlPoint::SetNumberOfRejectedMeasures, py::arg("num_rejected"))
         .def("get_number_of_rejected_measures", &Isis::ControlPoint::GetNumberOfRejectedMeasures)
         .def("get_sample_residual_rms", &Isis::ControlPoint::GetSampleResidualRms)
         .def("get_line_residual_rms", &Isis::ControlPoint::GetLineResidualRms)
         .def("get_residual_rms", &Isis::ControlPoint::GetResidualRms)
         .def("clear_jigsaw_rejected", &Isis::ControlPoint::ClearJigsawRejected)
         .def("copy", [](const Isis::ControlPoint &self)
              { return Isis::ControlPoint(self); })
         .def("__repr__", [](const Isis::ControlPoint &self)
              { return "ControlPoint(id='" + qStringToStdString(self.GetId()) + "', measures=" + std::to_string(self.GetNumMeasures()) + ")"; });

     py::class_<Isis::ControlNet> control_net(m, "ControlNet");

     py::enum_<Isis::ControlNet::ModType>(control_net, "ModType")
         .value("Swapped", Isis::ControlNet::Swapped)
         .value("GraphModified", Isis::ControlNet::GraphModified);

     control_net
         .def(py::init<Isis::SurfacePoint::CoordinateType>(), py::arg("coordinate_type") = Isis::SurfacePoint::Latitudinal)
         .def(py::init<const Isis::ControlNet &>(), py::arg("other"))
         .def(py::init([](const std::string &filename,
                          Isis::Progress *progress,
                          Isis::SurfacePoint::CoordinateType coordinate_type)
                       { return Isis::ControlNet(stdStringToQString(filename), progress, coordinate_type); }),
              py::arg("filename"),
              py::arg("progress") = nullptr,
              py::arg("coordinate_type") = Isis::SurfacePoint::Latitudinal)
         .def("clear", &Isis::ControlNet::clear)
         .def("take", [](Isis::ControlNet &self)
              { return takenPointsToPyList(self.take()); })
         .def("read_control", [](Isis::ControlNet &self, const std::string &filename, Isis::Progress *progress)
              { self.ReadControl(stdStringToQString(filename), progress); }, py::arg("filename"), py::arg("progress") = nullptr)
         .def("write", [](Isis::ControlNet &self, const std::string &filename, bool pvl)
              { self.Write(stdStringToQString(filename), pvl); }, py::arg("filename"), py::arg("pvl") = false)
         .def("add_point", [](Isis::ControlNet &self, const Isis::ControlPoint &point)
              { self.AddPoint(new Isis::ControlPoint(point)); }, py::arg("point"))
         .def("delete_point", py::overload_cast<Isis::ControlPoint *>(&Isis::ControlNet::DeletePoint), py::arg("point"))
         .def("delete_point", [](Isis::ControlNet &self, const std::string &point_id)
              { return self.DeletePoint(stdStringToQString(point_id)); }, py::arg("point_id"))
         .def("delete_point", py::overload_cast<int>(&Isis::ControlNet::DeletePoint), py::arg("index"))
         .def("contains_point", [](const Isis::ControlNet &self, const std::string &point_id)
              { return self.ContainsPoint(stdStringToQString(point_id)); }, py::arg("point_id"))
         .def("get_cube_serials", [](const Isis::ControlNet &self)
              { return qListToStdVector(self.GetCubeSerials()); })
         .def("graph_to_string", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.GraphToString()); })
         .def("get_serial_connections", [](const Isis::ControlNet &self)
              { return qNestedListToStdVector(self.GetSerialConnections()); })
         .def("get_edge_count", &Isis::ControlNet::getEdgeCount)
         .def("get_adjacent_images", [](const Isis::ControlNet &self, const std::string &serial_number)
              { return qListToStdVector(self.getAdjacentImages(stdStringToQString(serial_number))); }, py::arg("serial_number"))
         .def("get_measures_in_cube", [](Isis::ControlNet &self, const std::string &serial_number)
              { return measuresToPyList(self.GetMeasuresInCube(stdStringToQString(serial_number)), py::cast(&self)); }, py::arg("serial_number"))
         .def("get_valid_measures_in_cube", [](Isis::ControlNet &self, const std::string &serial_number)
              { return measuresToPyList(self.GetValidMeasuresInCube(stdStringToQString(serial_number)), py::cast(&self)); }, py::arg("serial_number"))
         .def("compute_residuals", &Isis::ControlNet::ComputeResiduals)
         .def("compute_apriori", &Isis::ControlNet::ComputeApriori)
         .def("get_point", [](Isis::ControlNet &self, const std::string &point_id) -> Isis::ControlPoint *
              { return self.GetPoint(stdStringToQString(point_id)); }, py::arg("point_id"), py::return_value_policy::reference_internal)
         .def("get_point", py::overload_cast<int>(&Isis::ControlNet::GetPoint), py::arg("index"), py::return_value_policy::reference_internal)
         .def("average_residual", &Isis::ControlNet::AverageResidual)
         .def("camera", py::overload_cast<int>(&Isis::ControlNet::Camera), py::arg("index"), py::return_value_policy::reference_internal)
         .def("camera", [](Isis::ControlNet &self, const std::string &serial_number) -> Isis::Camera *
              { return self.Camera(stdStringToQString(serial_number)); }, py::arg("serial_number"), py::return_value_policy::reference_internal)
         .def("created_date", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.CreatedDate()); })
         .def("description", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.Description()); })
         .def("find_closest", [](Isis::ControlNet &self, const std::string &serial_number, double sample, double line) -> Isis::ControlPoint *
              { return self.FindClosest(stdStringToQString(serial_number), sample, line); }, py::arg("serial_number"), py::arg("sample"), py::arg("line"), py::return_value_policy::reference_internal)
         .def("get_maximum_residual", &Isis::ControlNet::GetMaximumResidual)
         .def("get_network_id", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.GetNetworkId()); })
         .def("get_num_edit_lock_measures", &Isis::ControlNet::GetNumEditLockMeasures)
         .def("get_num_edit_lock_points", &Isis::ControlNet::GetNumEditLockPoints)
         .def("get_num_ignored_measures", &Isis::ControlNet::GetNumIgnoredMeasures)
         .def("get_number_of_valid_measures_in_image", [](Isis::ControlNet &self, const std::string &serial_number)
              { return self.GetNumberOfValidMeasuresInImage(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("get_number_of_jigsaw_rejected_measures_in_image", [](Isis::ControlNet &self, const std::string &serial_number)
              { return self.GetNumberOfJigsawRejectedMeasuresInImage(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("clear_jigsaw_rejected", &Isis::ControlNet::ClearJigsawRejected)
         .def("increment_number_of_rejected_measures_in_image", [](Isis::ControlNet &self, const std::string &serial_number)
              { self.IncrementNumberOfRejectedMeasuresInImage(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("decrement_number_of_rejected_measures_in_image", [](Isis::ControlNet &self, const std::string &serial_number)
              { self.DecrementNumberOfRejectedMeasuresInImage(stdStringToQString(serial_number)); }, py::arg("serial_number"))
         .def("get_num_measures", &Isis::ControlNet::GetNumMeasures)
         .def("get_num_points", &Isis::ControlNet::GetNumPoints)
         .def("get_num_valid_measures", &Isis::ControlNet::GetNumValidMeasures)
         .def("get_num_valid_points", &Isis::ControlNet::GetNumValidPoints)
         .def("get_target", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.GetTarget()); })
         .def("get_user_name", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.GetUserName()); })
         .def("get_last_modified", [](const Isis::ControlNet &self)
              { return qStringToStdString(self.GetLastModified()); })
         .def("get_points", [](Isis::ControlNet &self)
              { return pointsToPyList(self.GetPoints(), py::cast(&self)); })
         .def("get_point_ids", [](const Isis::ControlNet &self)
              { return qListToStdVector(self.GetPointIds()); })
         .def("get_coord_type", &Isis::ControlNet::GetCoordType)
         .def("set_created_date", [](Isis::ControlNet &self, const std::string &date)
              { self.SetCreatedDate(stdStringToQString(date)); }, py::arg("date"))
         .def("set_description", [](Isis::ControlNet &self, const std::string &description)
              { self.SetDescription(stdStringToQString(description)); }, py::arg("description"))
         .def("set_images", [](Isis::ControlNet &self, const std::string &image_list_file)
              { self.SetImages(stdStringToQString(image_list_file)); }, py::arg("image_list_file"))
         .def("set_modified_date", [](Isis::ControlNet &self, const std::string &date)
              { self.SetModifiedDate(stdStringToQString(date)); }, py::arg("date"))
         .def("set_network_id", [](Isis::ControlNet &self, const std::string &network_id)
              { self.SetNetworkId(stdStringToQString(network_id)); }, py::arg("network_id"))
         .def("set_target", [](Isis::ControlNet &self, const std::string &target)
              { self.SetTarget(stdStringToQString(target)); }, py::arg("target"))
         .def("set_target", py::overload_cast<Isis::Pvl>(&Isis::ControlNet::SetTarget), py::arg("label"))
         .def("set_user_name", [](Isis::ControlNet &self, const std::string &user_name)
              { self.SetUserName(stdStringToQString(user_name)); }, py::arg("user_name"))
         .def("set_coord_type", &Isis::ControlNet::SetCoordType, py::arg("coordinate_type"))
         .def("swap", &Isis::ControlNet::swap, py::arg("other"))
         .def("__getitem__", [](Isis::ControlNet &self, const std::string &point_id) -> Isis::ControlPoint *
              { return self[stdStringToQString(point_id)]; }, py::arg("point_id"), py::return_value_policy::reference_internal)
         .def("__getitem__", [](Isis::ControlNet &self, int index) -> Isis::ControlPoint *
              { return self[index]; }, py::arg("index"), py::return_value_policy::reference_internal)
         .def("__len__", &Isis::ControlNet::GetNumPoints)
         .def("copy", [](const Isis::ControlNet &self)
              { return Isis::ControlNet(self); })
         .def("__repr__", [](const Isis::ControlNet &self)
              { return "ControlNet(points=" + std::to_string(self.GetNumPoints()) + ", measures=" + std::to_string(self.GetNumMeasures()) + ")"; });

     // Added: 2026-04-08 - expose stable ControlNetStatistics summary/getter cluster
     py::class_<Isis::ControlNetStatistics> control_net_statistics(m, "ControlNetStatistics");

     py::enum_<Isis::ControlNetStatistics::ePointDetails>(control_net_statistics, "ePointDetails")
         .value("total", Isis::ControlNetStatistics::total)
         .value("ignore", Isis::ControlNetStatistics::ignore)
         .value("locked", Isis::ControlNetStatistics::locked)
         .value("fixed", Isis::ControlNetStatistics::fixed)
         .value("constrained", Isis::ControlNetStatistics::constrained)
         .value("freed", Isis::ControlNetStatistics::freed);

     py::enum_<Isis::ControlNetStatistics::ePointIntStats>(control_net_statistics, "ePointIntStats")
         .value("totalPoints", Isis::ControlNetStatistics::totalPoints)
         .value("validPoints", Isis::ControlNetStatistics::validPoints)
         .value("ignoredPoints", Isis::ControlNetStatistics::ignoredPoints)
         .value("fixedPoints", Isis::ControlNetStatistics::fixedPoints)
         .value("constrainedPoints", Isis::ControlNetStatistics::constrainedPoints)
         .value("freePoints", Isis::ControlNetStatistics::freePoints)
         .value("editLockedPoints", Isis::ControlNetStatistics::editLockedPoints)
         .value("totalMeasures", Isis::ControlNetStatistics::totalMeasures)
         .value("validMeasures", Isis::ControlNetStatistics::validMeasures)
         .value("ignoredMeasures", Isis::ControlNetStatistics::ignoredMeasures)
         .value("editLockedMeasures", Isis::ControlNetStatistics::editLockedMeasures);

     py::enum_<Isis::ControlNetStatistics::ePointDoubleStats>(control_net_statistics, "ePointDoubleStats")
         .value("avgResidual", Isis::ControlNetStatistics::avgResidual)
         .value("minResidual", Isis::ControlNetStatistics::minResidual)
         .value("maxResidual", Isis::ControlNetStatistics::maxResidual)
         .value("minLineResidual", Isis::ControlNetStatistics::minLineResidual)
         .value("maxLineResidual", Isis::ControlNetStatistics::maxLineResidual)
         .value("minSampleResidual", Isis::ControlNetStatistics::minSampleResidual)
         .value("maxSampleResidual", Isis::ControlNetStatistics::maxSampleResidual)
         .value("avgPixelShift", Isis::ControlNetStatistics::avgPixelShift)
         .value("minPixelShift", Isis::ControlNetStatistics::minPixelShift)
         .value("maxPixelShift", Isis::ControlNetStatistics::maxPixelShift)
         .value("minLineShift", Isis::ControlNetStatistics::minLineShift)
         .value("maxLineShift", Isis::ControlNetStatistics::maxLineShift)
         .value("minSampleShift", Isis::ControlNetStatistics::minSampleShift)
         .value("maxSampleShift", Isis::ControlNetStatistics::maxSampleShift)
         .value("minGFit", Isis::ControlNetStatistics::minGFit)
         .value("maxGFit", Isis::ControlNetStatistics::maxGFit)
         .value("minEccentricity", Isis::ControlNetStatistics::minEccentricity)
         .value("maxEccentricity", Isis::ControlNetStatistics::maxEccentricity)
         .value("minPixelZScore", Isis::ControlNetStatistics::minPixelZScore)
         .value("maxPixelZScore", Isis::ControlNetStatistics::maxPixelZScore);

     py::enum_<Isis::ControlNetStatistics::ImageStats>(control_net_statistics, "ImageStats")
         .value("imgSamples", Isis::ControlNetStatistics::imgSamples)
         .value("imgLines", Isis::ControlNetStatistics::imgLines)
         .value("imgTotalPoints", Isis::ControlNetStatistics::imgTotalPoints)
         .value("imgIgnoredPoints", Isis::ControlNetStatistics::imgIgnoredPoints)
         .value("imgFixedPoints", Isis::ControlNetStatistics::imgFixedPoints)
         .value("imgLockedPoints", Isis::ControlNetStatistics::imgLockedPoints)
         .value("imgLocked", Isis::ControlNetStatistics::imgLocked)
         .value("imgConstrainedPoints", Isis::ControlNetStatistics::imgConstrainedPoints)
         .value("imgFreePoints", Isis::ControlNetStatistics::imgFreePoints)
         .value("imgConvexHullArea", Isis::ControlNetStatistics::imgConvexHullArea)
         .value("imgConvexHullRatio", Isis::ControlNetStatistics::imgConvexHullRatio);

     control_net_statistics
         .def(py::init([](Isis::ControlNet &control_net, Isis::Progress *progress)
                       {
                            return std::make_unique<Isis::ControlNetStatistics>(&control_net, progress);
                       }),
              py::arg("control_net"),
              py::arg("progress") = nullptr,
              py::keep_alive<1, 2>(),
              py::keep_alive<1, 3>())
         .def("generate_control_net_stats",
              [](Isis::ControlNetStatistics &self, Isis::PvlGroup &stats_group)
              {
                   self.GenerateControlNetStats(stats_group);
              },
              py::arg("stats_group"))
         .def("num_valid_points", &Isis::ControlNetStatistics::NumValidPoints)
         .def("num_fixed_points", &Isis::ControlNetStatistics::NumFixedPoints)
         .def("num_constrained_points", &Isis::ControlNetStatistics::NumConstrainedPoints)
         .def("num_free_points", &Isis::ControlNetStatistics::NumFreePoints)
         .def("num_ignored_points", &Isis::ControlNetStatistics::NumIgnoredPoints)
         .def("num_edit_locked_points", &Isis::ControlNetStatistics::NumEditLockedPoints)
         .def("num_measures", &Isis::ControlNetStatistics::NumMeasures)
         .def("num_valid_measures", &Isis::ControlNetStatistics::NumValidMeasures)
         .def("num_ignored_measures", &Isis::ControlNetStatistics::NumIgnoredMeasures)
         .def("num_edit_locked_measures", &Isis::ControlNetStatistics::NumEditLockedMeasures)
         .def("get_average_residual", &Isis::ControlNetStatistics::GetAverageResidual)
         .def("get_minimum_residual", &Isis::ControlNetStatistics::GetMinimumResidual)
         .def("get_maximum_residual", &Isis::ControlNetStatistics::GetMaximumResidual)
         .def("get_min_line_residual", &Isis::ControlNetStatistics::GetMinLineResidual)
         .def("get_min_sample_residual", &Isis::ControlNetStatistics::GetMinSampleResidual)
         .def("get_max_line_residual", &Isis::ControlNetStatistics::GetMaxLineResidual)
         .def("get_max_sample_residual", &Isis::ControlNetStatistics::GetMaxSampleResidual)
         .def("get_min_line_shift", &Isis::ControlNetStatistics::GetMinLineShift)
         .def("get_max_line_shift", &Isis::ControlNetStatistics::GetMaxLineShift)
         .def("get_min_sample_shift", &Isis::ControlNetStatistics::GetMinSampleShift)
         .def("get_max_sample_shift", &Isis::ControlNetStatistics::GetMaxSampleShift)
         .def("get_min_pixel_shift", &Isis::ControlNetStatistics::GetMinPixelShift)
         .def("get_max_pixel_shift", &Isis::ControlNetStatistics::GetMaxPixelShift)
         .def("get_avg_pixel_shift", &Isis::ControlNetStatistics::GetAvgPixelShift)
         .def("__repr__",
              [](const Isis::ControlNetStatistics &self)
              {
                   return "ControlNetStatistics(valid_points=" + std::to_string(self.NumValidPoints()) +
                          ", valid_measures=" + std::to_string(self.NumValidMeasures()) + ")";
              });

     // Added: 2026-04-07 - expose initial ControlNetFilter constructor/output helper surface
     py::class_<Isis::ControlNetFilter> control_net_filter(m, "ControlNetFilter");

     control_net_filter
           // Added: 2026-04-07 - extend ControlNetFilter with count-based point/cube filters
         .def(py::init([](Isis::ControlNet &control_net,
                          const std::string &serial_number_list_file,
                          Isis::Progress *progress)
                       {
                            QString serial_number_list_qstring = stdStringToQString(serial_number_list_file);
                            return std::make_unique<Isis::ControlNetFilter>(
                                &control_net,
                                serial_number_list_qstring,
                                progress);
                       }),
              py::arg("control_net"),
              py::arg("serial_number_list_file"),
              py::arg("progress") = nullptr,
              py::keep_alive<1, 2>(),
              py::keep_alive<1, 4>())
         .def("point_edit_lock_filter",
              &Isis::ControlNetFilter::PointEditLockFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         // Added: 2026-04-08 - expose remaining upstream ControlNetFilter point/cube filter methods
         .def("point_pixel_shift_filter",
              &Isis::ControlNetFilter::PointPixelShiftFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_num_measures_edit_lock_filter",
              &Isis::ControlNetFilter::PointNumMeasuresEditLockFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_res_magnitude_filter",
              &Isis::ControlNetFilter::PointResMagnitudeFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_goodness_of_fit_filter",
              &Isis::ControlNetFilter::PointGoodnessOfFitFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_id_filter",
              &Isis::ControlNetFilter::PointIDFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_measures_filter",
              &Isis::ControlNetFilter::PointMeasuresFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_properties_filter",
              &Isis::ControlNetFilter::PointPropertiesFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_lat_lon_filter",
              &Isis::ControlNetFilter::PointLatLonFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_distance_filter",
              &Isis::ControlNetFilter::PointDistanceFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_measure_properties_filter",
              &Isis::ControlNetFilter::PointMeasurePropertiesFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_cube_names_filter",
              &Isis::ControlNetFilter::PointCubeNamesFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("point_stats_header", &Isis::ControlNetFilter::PointStatsHeader)
         .def("point_stats", &Isis::ControlNetFilter::PointStats, py::arg("control_point"))
         .def("cube_name_expression_filter",
              &Isis::ControlNetFilter::CubeNameExpressionFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("cube_num_points_filter",
              &Isis::ControlNetFilter::CubeNumPointsFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("cube_distance_filter",
              &Isis::ControlNetFilter::CubeDistanceFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("cube_convex_hull_filter",
              &Isis::ControlNetFilter::CubeConvexHullFilter,
              py::arg("pvl_group"),
              py::arg("last_filter"))
         .def("cube_stats_header", &Isis::ControlNetFilter::CubeStatsHeader)
         .def("set_output_file",
              [](Isis::ControlNetFilter &self, const std::string &print_file)
              { self.SetOutputFile(stdStringToQString(print_file)); },
              py::arg("print_file"))
         .def("print_cube_file_serial_num",
              &Isis::ControlNetFilter::PrintCubeFileSerialNum,
              py::arg("control_measure"));

     py::class_<Isis::ControlNetDiff> control_net_diff(m, "ControlNetDiff");

     control_net_diff
         .def(py::init<>())
         .def(py::init<Isis::Pvl &>(), py::arg("diff_file"))
         .def("add_tolerances", &Isis::ControlNetDiff::addTolerances, py::arg("diff_file"))
         .def("compare",
              static_cast<Isis::Pvl (Isis::ControlNetDiff::*)(Isis::FileName &, Isis::FileName &)>(&Isis::ControlNetDiff::compare),
              py::arg("net1_name"),
              py::arg("net2_name"))
         .def("__repr__", [](const Isis::ControlNetDiff &)
              { return "ControlNetDiff()"; });

     py::class_<Isis::ControlPointList> control_point_list(m, "ControlPointList");

     control_point_list
         .def(py::init<const Isis::FileName &>(), py::arg("file_name"))
         .def("control_point_id", [](Isis::ControlPointList &self, int index)
              { return qStringToStdString(self.ControlPointId(index)); }, py::arg("index"))
         .def("control_point_index", [](Isis::ControlPointList &self, const std::string &point_id)
              { return self.ControlPointIndex(stdStringToQString(point_id)); }, py::arg("point_id"))
         .def("has_control_point", [](Isis::ControlPointList &self, const std::string &point_id)
              { return self.HasControlPoint(stdStringToQString(point_id)); }, py::arg("point_id"))
         .def("size", &Isis::ControlPointList::Size)
         .def("register_statistics", &Isis::ControlPointList::RegisterStatistics, py::arg("pvl_log"))
         .def("__len__", &Isis::ControlPointList::Size)
         .def("__repr__", [](Isis::ControlPointList &self)
              { return "ControlPointList(size=" + std::to_string(self.Size()) + ")"; });

     py::class_<Isis::ControlPointV0001> control_point_v0001(m, "ControlPointV0001");

     control_point_v0001
         .def(py::init([](Isis::PvlObject &point_object, const std::string &target_name)
                       {
                            return std::make_unique<Isis::ControlPointV0001>(point_object, stdStringToQString(target_name));
                       }),
              py::arg("point_object"),
              py::arg("target_name"))
         .def("point_data", [](Isis::ControlPointV0001 &self)
              {
                   return py::bytes(self.pointData()->SerializeAsString());
              })
         .def("log_data", [](Isis::ControlPointV0001 &self)
              {
                   return py::bytes(self.logData()->SerializeAsString());
              })
         .def("point_data_debug_string", [](Isis::ControlPointV0001 &self)
              {
                   return self.pointData()->DebugString();
              })
         .def("log_data_debug_string", [](Isis::ControlPointV0001 &self)
              {
                   return self.logData()->DebugString();
              })
         .def("__repr__", [](Isis::ControlPointV0001 &self)
              {
                   return "ControlPointV0001(bytes=" + std::to_string(self.pointData()->ByteSizeLong()) + ")";
              });

     py::class_<Isis::ControlPointV0002> control_point_v0002(m, "ControlPointV0002");

     control_point_v0002
         .def(py::init([](Isis::PvlObject &point_object)
                       {
                            return std::make_unique<Isis::ControlPointV0002>(point_object);
                       }),
              py::arg("point_object"))
         .def(py::init([](Isis::ControlPointV0001 &old_point)
                       {
                            return std::make_unique<Isis::ControlPointV0002>(old_point);
                       }),
              py::arg("old_point"))
         .def("point_data", [](Isis::ControlPointV0002 &self)
              {
                   return py::bytes(self.pointData()->SerializeAsString());
              })
         .def("log_data", [](Isis::ControlPointV0002 &self)
              {
                   return py::bytes(self.logData()->SerializeAsString());
              })
         .def("point_data_debug_string", [](Isis::ControlPointV0002 &self)
              {
                   return self.pointData()->DebugString();
              })
         .def("log_data_debug_string", [](Isis::ControlPointV0002 &self)
              {
                   return self.logData()->DebugString();
              })
         .def("__repr__", [](Isis::ControlPointV0002 &self)
              {
                   return "ControlPointV0002(bytes=" + std::to_string(self.pointData()->ByteSizeLong()) + ")";
              });

     py::class_<Isis::ControlPointV0003> control_point_v0003(m, "ControlPointV0003");

     control_point_v0003
         .def(py::init([](Isis::PvlObject &point_object)
                       {
                            return std::make_unique<Isis::ControlPointV0003>(point_object);
                       }),
              py::arg("point_object"))
         .def(py::init([](Isis::ControlPointV0002 &old_point)
                       {
                            return std::make_unique<Isis::ControlPointV0003>(old_point);
                       }),
              py::arg("old_point"))
         .def("point_data", [](Isis::ControlPointV0003 &self)
              {
                   return py::bytes(self.pointData().SerializeAsString());
              })
         .def("point_data_debug_string", [](Isis::ControlPointV0003 &self)
              {
                   return self.pointData().DebugString();
              })
         .def("__repr__", [](Isis::ControlPointV0003 &self)
              {
                   return "ControlPointV0003(bytes=" + std::to_string(self.pointData().ByteSizeLong()) + ")";
              });

     py::class_<Isis::MeasureValidationResults> measure_validation_results(m, "MeasureValidationResults");

     py::enum_<Isis::MeasureValidationResults::Option>(measure_validation_results, "Option")
         .value("EmissionAngle", Isis::MeasureValidationResults::EmissionAngle)
         .value("IncidenceAngle", Isis::MeasureValidationResults::IncidenceAngle)
         .value("DNValue", Isis::MeasureValidationResults::DNValue)
         .value("Resolution", Isis::MeasureValidationResults::Resolution)
         .value("PixelsFromEdge", Isis::MeasureValidationResults::PixelsFromEdge)
         .value("MetersFromEdge", Isis::MeasureValidationResults::MetersFromEdge)
         .value("SampleResidual", Isis::MeasureValidationResults::SampleResidual)
         .value("LineResidual", Isis::MeasureValidationResults::LineResidual)
         .value("ResidualMagnitude", Isis::MeasureValidationResults::ResidualMagnitude)
         .value("SampleShift", Isis::MeasureValidationResults::SampleShift)
         .value("LineShift", Isis::MeasureValidationResults::LineShift)
         .value("PixelShift", Isis::MeasureValidationResults::PixelShift);

     measure_validation_results
         .def(py::init<>())
         .def("is_valid", &Isis::MeasureValidationResults::isValid)
         .def("get_valid_status", &Isis::MeasureValidationResults::getValidStatus, py::arg("option"))
         .def("to_string", [](Isis::MeasureValidationResults &self)
              { return qStringToStdString(self.toString()); })
         .def("to_string", [](Isis::MeasureValidationResults &self, const std::string &serial_number, const std::string &point_id)
              { return qStringToStdString(self.toString(stdStringToQString(serial_number), stdStringToQString(point_id))); }, py::arg("serial_number"), py::arg("point_id"))
         .def("to_string",
              [](Isis::MeasureValidationResults &self,
                 const std::string &sample,
                 const std::string &line,
                 const std::string &serial_number,
                 const std::string &point_id)
              {
                   return qStringToStdString(self.toString(
                       stdStringToQString(sample),
                       stdStringToQString(line),
                       stdStringToQString(serial_number),
                       stdStringToQString(point_id)));
              },
              py::arg("sample"),
              py::arg("line"),
              py::arg("serial_number"),
              py::arg("point_id"))
         .def("add_failure",
              [](Isis::MeasureValidationResults &self,
                 Isis::MeasureValidationResults::Option option,
                 double tolerance,
                 const std::string &compare)
              {
                   self.addFailure(option, tolerance, compare.c_str());
              },
              py::arg("option"),
              py::arg("tolerance"),
              py::arg("compare") = "less")
         .def("add_failure",
              py::overload_cast<Isis::MeasureValidationResults::Option, double, double, double>(&Isis::MeasureValidationResults::addFailure),
              py::arg("option"),
              py::arg("computed"),
              py::arg("minimum"),
              py::arg("maximum"))
         .def("get_failure_prefix", [](Isis::MeasureValidationResults &self, Isis::MeasureValidationResults::Option option)
              { return qStringToStdString(self.getFailurePrefix(option)); }, py::arg("option"))
         .def("__repr__", [](Isis::MeasureValidationResults &self)
              {
                   return std::string("MeasureValidationResults(valid=") + (self.isValid() ? "True" : "False") + ")";
              });

     // Added: 2026-04-08 - expose stable ControlNetValidMeasure configuration/query helper cluster
     py::class_<Isis::ControlNetValidMeasure> control_net_valid_measure(m, "ControlNetValidMeasure");

     control_net_valid_measure
         .def(py::init<>())
         .def(py::init<Isis::Pvl &>(),
              py::arg("pvl"),
              py::keep_alive<1, 2>())
         .def("init_std_options", &Isis::ControlNetValidMeasure::InitStdOptions)
         .def("init_std_options_group", &Isis::ControlNetValidMeasure::InitStdOptionsGroup)
         .def("parse", &Isis::ControlNetValidMeasure::Parse, py::arg("pvl"))
         .def("get_log_pvl",
              &Isis::ControlNetValidMeasure::GetLogPvl,
              py::return_value_policy::reference_internal)
         .def("valid_emission_angle", &Isis::ControlNetValidMeasure::ValidEmissionAngle, py::arg("emission_angle"))
         .def("valid_incidence_angle", &Isis::ControlNetValidMeasure::ValidIncidenceAngle, py::arg("incidence_angle"))
         .def("valid_dn_value", &Isis::ControlNetValidMeasure::ValidDnValue, py::arg("dn_value"))
         .def("valid_resolution", &Isis::ControlNetValidMeasure::ValidResolution, py::arg("resolution"))
         .def("valid_residual_tolerances",
              &Isis::ControlNetValidMeasure::ValidResidualTolerances,
              py::arg("sample_residual"),
              py::arg("line_residual"),
              py::arg("residual_magnitude"),
              py::arg("results"))
         .def("valid_shift_tolerances",
              &Isis::ControlNetValidMeasure::ValidShiftTolerances,
              py::arg("sample_shift"),
              py::arg("line_shift"),
              py::arg("pixel_shift"),
              py::arg("results"))
         .def("get_std_options",
              &Isis::ControlNetValidMeasure::GetStdOptions,
              py::return_value_policy::reference_internal)
         .def("get_statistics",
              &Isis::ControlNetValidMeasure::GetStatistics,
              py::return_value_policy::reference_internal)
         .def("get_min_dn", &Isis::ControlNetValidMeasure::GetMinDN)
         .def("get_max_dn", &Isis::ControlNetValidMeasure::GetMaxDN)
         .def("get_min_emission_angle", &Isis::ControlNetValidMeasure::GetMinEmissionAngle)
         .def("get_max_emission_angle", &Isis::ControlNetValidMeasure::GetMaxEmissionAngle)
         .def("get_min_incidence_angle", &Isis::ControlNetValidMeasure::GetMinIncidenceAngle)
         .def("get_max_incidence_angle", &Isis::ControlNetValidMeasure::GetMaxIncidenceAngle)
         .def("get_pixels_from_edge", &Isis::ControlNetValidMeasure::GetPixelsFromEdge)
         .def("get_meters_from_edge", &Isis::ControlNetValidMeasure::GetMetersFromEdge)
         .def("location_string",
              [](const Isis::ControlNetValidMeasure &self, double sample, double line)
              {
                   return qStringToStdString(self.LocationString(sample, line));
              },
              py::arg("sample"),
              py::arg("line"))
         .def("is_cube_required", &Isis::ControlNetValidMeasure::IsCubeRequired)
         .def("is_camera_required", &Isis::ControlNetValidMeasure::IsCameraRequired)
         .def("__repr__",
              [](Isis::ControlNetValidMeasure &self)
              {
                   return "ControlNetValidMeasure(camera_required=" +
                          std::string(self.IsCameraRequired() ? "True" : "False") +
                          ", cube_required=" +
                          std::string(self.IsCubeRequired() ? "True" : "False") + ")";
              });

     py::class_<Isis::BundleImage> bundle_image(m, "BundleImage");

     bundle_image
         .def(py::init([](Isis::Camera *camera, const std::string &serial_number, const std::string &file_name)
                       {
                            return Isis::BundleImage(camera, stdStringToQString(serial_number), stdStringToQString(file_name));
                       }),
              py::arg("camera"),
              py::arg("serial_number"),
              py::arg("file_name"))
         .def(py::init<const Isis::BundleImage &>(), py::arg("other"))
         .def("camera", &Isis::BundleImage::camera, py::return_value_policy::reference_internal)
         .def("has_parent_observation", [](Isis::BundleImage &self)
              { return !self.parentObservation().isNull(); })
         .def("serial_number", [](Isis::BundleImage &self)
              { return qStringToStdString(self.serialNumber()); })
         .def("file_name", [](Isis::BundleImage &self)
              { return qStringToStdString(self.fileName()); })
         .def("copy", [](const Isis::BundleImage &self)
              { return Isis::BundleImage(self); })
         .def("__repr__", [](Isis::BundleImage &self)
              {
                   return "BundleImage(serial_number='" + qStringToStdString(self.serialNumber()) +
                          "', file_name='" + qStringToStdString(self.fileName()) + "')";
              });

     py::class_<Isis::BundleObservationSolveSettings> bundle_observation_solve_settings(m, "BundleObservationSolveSettings");

     py::enum_<Isis::BundleObservationSolveSettings::CSMSolveOption>(bundle_observation_solve_settings, "CSMSolveOption")
         .value("NoCSMParameters", Isis::BundleObservationSolveSettings::NoCSMParameters)
         .value("Set", Isis::BundleObservationSolveSettings::Set)
         .value("Type", Isis::BundleObservationSolveSettings::Type)
         .value("List", Isis::BundleObservationSolveSettings::List);

     py::enum_<csm::param::Set>(bundle_observation_solve_settings, "CSMSolveSet")
         .value("VALID", csm::param::VALID)
         .value("ADJUSTABLE", csm::param::ADJUSTABLE)
         .value("NON_ADJUSTABLE", csm::param::NON_ADJUSTABLE);

     py::enum_<csm::param::Type>(bundle_observation_solve_settings, "CSMSolveType")
         .value("NONE", csm::param::NONE)
         .value("FICTITIOUS", csm::param::FICTITIOUS)
         .value("REAL", csm::param::REAL)
         .value("FIXED", csm::param::FIXED);

     py::enum_<Isis::BundleObservationSolveSettings::InstrumentPointingSolveOption>(bundle_observation_solve_settings, "InstrumentPointingSolveOption")
         .value("NoPointingFactors", Isis::BundleObservationSolveSettings::NoPointingFactors)
         .value("AnglesOnly", Isis::BundleObservationSolveSettings::AnglesOnly)
         .value("AnglesVelocity", Isis::BundleObservationSolveSettings::AnglesVelocity)
         .value("AnglesVelocityAcceleration", Isis::BundleObservationSolveSettings::AnglesVelocityAcceleration)
         .value("AllPointingCoefficients", Isis::BundleObservationSolveSettings::AllPointingCoefficients);

     py::enum_<Isis::BundleObservationSolveSettings::InstrumentPositionSolveOption>(bundle_observation_solve_settings, "InstrumentPositionSolveOption")
         .value("NoPositionFactors", Isis::BundleObservationSolveSettings::NoPositionFactors)
         .value("PositionOnly", Isis::BundleObservationSolveSettings::PositionOnly)
         .value("PositionVelocity", Isis::BundleObservationSolveSettings::PositionVelocity)
         .value("PositionVelocityAcceleration", Isis::BundleObservationSolveSettings::PositionVelocityAcceleration)
         .value("AllPositionCoefficients", Isis::BundleObservationSolveSettings::AllPositionCoefficients);

      bundle_observation_solve_settings.attr("PointingInterpolationType") = m.attr("SpiceRotationSource");
      bundle_observation_solve_settings.attr("PositionInterpolationType") = m.attr("SpicePositionSource");

     bundle_observation_solve_settings
         .def(py::init<>())
         .def(py::init<const Isis::BundleObservationSolveSettings &>(), py::arg("other"))
         .def("initialize", &Isis::BundleObservationSolveSettings::initialize)
         .def("set_instrument_id", [](Isis::BundleObservationSolveSettings &self, const std::string &instrument_id)
              { self.setInstrumentId(stdStringToQString(instrument_id)); }, py::arg("instrument_id"))
         .def("instrument_id", [](const Isis::BundleObservationSolveSettings &self)
              { return qStringToStdString(self.instrumentId()); })
         .def("add_observation_number", [](Isis::BundleObservationSolveSettings &self, const std::string &observation_number)
              { self.addObservationNumber(stdStringToQString(observation_number)); }, py::arg("observation_number"))
         .def("remove_observation_number", [](Isis::BundleObservationSolveSettings &self, const std::string &observation_number)
              { return self.removeObservationNumber(stdStringToQString(observation_number)); }, py::arg("observation_number"))
         .def("observation_numbers", [](const Isis::BundleObservationSolveSettings &self)
              { return qSetToSortedStdVector(self.observationNumbers()); })
         .def_static("string_to_csm_solve_option", [](const std::string &option)
                     { return Isis::BundleObservationSolveSettings::stringToCSMSolveOption(stdStringToQString(option)); }, py::arg("option"))
         .def_static("csm_solve_option_to_string", [](Isis::BundleObservationSolveSettings::CSMSolveOption option)
                     { return qStringToStdString(Isis::BundleObservationSolveSettings::csmSolveOptionToString(option)); }, py::arg("option"))
         .def_static("string_to_csm_solve_set", [](const std::string &set_name)
                     { return Isis::BundleObservationSolveSettings::stringToCSMSolveSet(stdStringToQString(set_name)); }, py::arg("set_name"))
         .def_static("csm_solve_set_to_string", [](csm::param::Set set_name)
                     { return qStringToStdString(Isis::BundleObservationSolveSettings::csmSolveSetToString(set_name)); }, py::arg("set_name"))
         .def_static("string_to_csm_solve_type", [](const std::string &type_name)
                     { return Isis::BundleObservationSolveSettings::stringToCSMSolveType(stdStringToQString(type_name)); }, py::arg("type_name"))
         .def_static("csm_solve_type_to_string", [](csm::param::Type type_name)
                     { return qStringToStdString(Isis::BundleObservationSolveSettings::csmSolveTypeToString(type_name)); }, py::arg("type_name"))
         .def("set_csm_solve_set", &Isis::BundleObservationSolveSettings::setCSMSolveSet, py::arg("set_name"))
         .def("set_csm_solve_type", &Isis::BundleObservationSolveSettings::setCSMSolveType, py::arg("type_name"))
         .def("set_csm_solve_parameter_list", [](Isis::BundleObservationSolveSettings &self, const std::vector<std::string> &values)
              { self.setCSMSolveParameterList(stdVectorToQStringList(values)); }, py::arg("values"))
         .def("csm_solve_option", &Isis::BundleObservationSolveSettings::csmSolveOption)
         .def("csm_parameter_set", &Isis::BundleObservationSolveSettings::csmParameterSet)
         .def("csm_parameter_type", &Isis::BundleObservationSolveSettings::csmParameterType)
         .def("csm_parameter_list", [](const Isis::BundleObservationSolveSettings &self)
              { return csmParameterListToPyList(self.csmParameterList()); })
         .def_static("string_to_instrument_pointing_solve_option", [](const std::string &option)
                     { return Isis::BundleObservationSolveSettings::stringToInstrumentPointingSolveOption(stdStringToQString(option)); }, py::arg("option"))
         .def_static("instrument_pointing_solve_option_to_string", [](Isis::BundleObservationSolveSettings::InstrumentPointingSolveOption option)
                     { return qStringToStdString(Isis::BundleObservationSolveSettings::instrumentPointingSolveOptionToString(option)); }, py::arg("option"))
         .def("set_instrument_pointing_settings",
              [](Isis::BundleObservationSolveSettings &self,
                 Isis::BundleObservationSolveSettings::InstrumentPointingSolveOption option,
                 bool solve_twist,
                 int ck_degree,
                 int ck_solve_degree,
                 bool solve_polynomial_over_existing,
                 double angles_apriori_sigma,
                 double angular_velocity_apriori_sigma,
                 double angular_acceleration_apriori_sigma,
                 const std::vector<double> &additional_pointing_sigmas)
              {
                   QList<double> qt_additional_sigmas = stdVectorToQList(additional_pointing_sigmas);
                   QList<double> *additional_sigmas_ptr = additional_pointing_sigmas.empty() ? nullptr : &qt_additional_sigmas;
                   self.setInstrumentPointingSettings(option,
                                                     solve_twist,
                                                     ck_degree,
                                                     ck_solve_degree,
                                                     solve_polynomial_over_existing,
                                                     angles_apriori_sigma,
                                                     angular_velocity_apriori_sigma,
                                                     angular_acceleration_apriori_sigma,
                                                     additional_sigmas_ptr);
              },
              py::arg("option"),
              py::arg("solve_twist"),
              py::arg("ck_degree") = 2,
              py::arg("ck_solve_degree") = 2,
              py::arg("solve_polynomial_over_existing") = false,
              py::arg("angles_apriori_sigma") = -1.0,
              py::arg("angular_velocity_apriori_sigma") = -1.0,
              py::arg("angular_acceleration_apriori_sigma") = -1.0,
              py::arg("additional_pointing_sigmas") = std::vector<double>{})
         .def("instrument_pointing_solve_option", &Isis::BundleObservationSolveSettings::instrumentPointingSolveOption)
         .def("solve_twist", &Isis::BundleObservationSolveSettings::solveTwist)
         .def("ck_degree", &Isis::BundleObservationSolveSettings::ckDegree)
         .def("ck_solve_degree", &Isis::BundleObservationSolveSettings::ckSolveDegree)
         .def("number_camera_angle_coefficients_solved", &Isis::BundleObservationSolveSettings::numberCameraAngleCoefficientsSolved)
         .def("solve_poly_over_pointing", &Isis::BundleObservationSolveSettings::solvePolyOverPointing)
         .def("apriori_pointing_sigmas", [](const Isis::BundleObservationSolveSettings &self)
              { return qListDoubleToStdVector(self.aprioriPointingSigmas()); })
         .def("pointing_interpolation_type", &Isis::BundleObservationSolveSettings::pointingInterpolationType)
         .def_static("string_to_instrument_position_solve_option", [](const std::string &option)
                     { return Isis::BundleObservationSolveSettings::stringToInstrumentPositionSolveOption(stdStringToQString(option)); }, py::arg("option"))
         .def_static("instrument_position_solve_option_to_string", [](Isis::BundleObservationSolveSettings::InstrumentPositionSolveOption option)
                     { return qStringToStdString(Isis::BundleObservationSolveSettings::instrumentPositionSolveOptionToString(option)); }, py::arg("option"))
         .def("set_instrument_position_settings",
              [](Isis::BundleObservationSolveSettings &self,
                 Isis::BundleObservationSolveSettings::InstrumentPositionSolveOption option,
                 int spk_degree,
                 int spk_solve_degree,
                 bool position_over_hermite,
                 double position_apriori_sigma,
                 double velocity_apriori_sigma,
                 double acceleration_apriori_sigma,
                 const std::vector<double> &additional_position_sigmas)
              {
                   QList<double> qt_additional_sigmas = stdVectorToQList(additional_position_sigmas);
                   QList<double> *additional_sigmas_ptr = additional_position_sigmas.empty() ? nullptr : &qt_additional_sigmas;
                   self.setInstrumentPositionSettings(option,
                                                     spk_degree,
                                                     spk_solve_degree,
                                                     position_over_hermite,
                                                     position_apriori_sigma,
                                                     velocity_apriori_sigma,
                                                     acceleration_apriori_sigma,
                                                     additional_sigmas_ptr);
              },
              py::arg("option"),
              py::arg("spk_degree") = 2,
              py::arg("spk_solve_degree") = 2,
              py::arg("position_over_hermite") = false,
              py::arg("position_apriori_sigma") = -1.0,
              py::arg("velocity_apriori_sigma") = -1.0,
              py::arg("acceleration_apriori_sigma") = -1.0,
              py::arg("additional_position_sigmas") = std::vector<double>{})
         .def("instrument_position_solve_option", &Isis::BundleObservationSolveSettings::instrumentPositionSolveOption)
         .def("spk_degree", &Isis::BundleObservationSolveSettings::spkDegree)
         .def("spk_solve_degree", &Isis::BundleObservationSolveSettings::spkSolveDegree)
         .def("number_camera_position_coefficients_solved", &Isis::BundleObservationSolveSettings::numberCameraPositionCoefficientsSolved)
         .def("solve_position_over_hermite", &Isis::BundleObservationSolveSettings::solvePositionOverHermite)
         .def("apriori_position_sigmas", [](const Isis::BundleObservationSolveSettings &self)
              { return qListDoubleToStdVector(self.aprioriPositionSigmas()); })
         .def("position_interpolation_type", &Isis::BundleObservationSolveSettings::positionInterpolationType)
         .def("copy", [](const Isis::BundleObservationSolveSettings &self)
              { return Isis::BundleObservationSolveSettings(self); })
         .def("__repr__", [](const Isis::BundleObservationSolveSettings &self)
              {
                   return "BundleObservationSolveSettings(instrument_id='" + qStringToStdString(self.instrumentId()) +
                          "', observations=" + std::to_string(self.observationNumbers().size()) + ")";
              });

     py::class_<Isis::BundleTargetBody> bundle_target_body(m, "BundleTargetBody");

     py::enum_<Isis::BundleTargetBody::TargetRadiiSolveMethod>(bundle_target_body, "TargetRadiiSolveMethod")
         .value("None", Isis::BundleTargetBody::None)
         .value("Mean", Isis::BundleTargetBody::Mean)
         .value("All", Isis::BundleTargetBody::All);

     py::enum_<Isis::BundleTargetBody::TargetSolveCodes>(bundle_target_body, "TargetSolveCodes")
         .value("PoleRA", Isis::BundleTargetBody::PoleRA)
         .value("VelocityPoleRA", Isis::BundleTargetBody::VelocityPoleRA)
         .value("AccelerationPoleRA", Isis::BundleTargetBody::AccelerationPoleRA)
         .value("PoleDec", Isis::BundleTargetBody::PoleDec)
         .value("VelocityPoleDec", Isis::BundleTargetBody::VelocityPoleDec)
         .value("AccelerationPoleDec", Isis::BundleTargetBody::AccelerationPoleDec)
         .value("PM", Isis::BundleTargetBody::PM)
         .value("VelocityPM", Isis::BundleTargetBody::VelocityPM)
         .value("AccelerationPM", Isis::BundleTargetBody::AccelerationPM)
         .value("TriaxialRadiusA", Isis::BundleTargetBody::TriaxialRadiusA)
         .value("TriaxialRadiusB", Isis::BundleTargetBody::TriaxialRadiusB)
         .value("TriaxialRadiusC", Isis::BundleTargetBody::TriaxialRadiusC)
         .value("MeanRadius", Isis::BundleTargetBody::MeanRadius);

     bundle_target_body
         .def(py::init<>())
         .def(py::init<const Isis::BundleTargetBody &>(), py::arg("other"))
         .def_static("string_to_target_radii_option", [](const std::string &option)
                     { return Isis::BundleTargetBody::stringToTargetRadiiOption(stdStringToQString(option)); }, py::arg("option"))
         .def_static("target_radii_option_to_string", [](Isis::BundleTargetBody::TargetRadiiSolveMethod option)
                     { return qStringToStdString(Isis::BundleTargetBody::targetRadiiOptionToString(option)); }, py::arg("option"))
         .def("set_solve_settings",
              [](Isis::BundleTargetBody &self,
                 const std::vector<Isis::BundleTargetBody::TargetSolveCodes> &target_parameter_solve_codes,
                 const Isis::Angle &apriori_pole_ra,
                 const Isis::Angle &sigma_pole_ra,
                 const Isis::Angle &apriori_velocity_pole_ra,
                 const Isis::Angle &sigma_velocity_pole_ra,
                 const Isis::Angle &apriori_pole_dec,
                 const Isis::Angle &sigma_pole_dec,
                 const Isis::Angle &apriori_velocity_pole_dec,
                 const Isis::Angle &sigma_velocity_pole_dec,
                 const Isis::Angle &apriori_pm,
                 const Isis::Angle &sigma_pm,
                 const Isis::Angle &apriori_velocity_pm,
                 const Isis::Angle &sigma_velocity_pm,
                 Isis::BundleTargetBody::TargetRadiiSolveMethod solve_radii_method,
                 const Isis::Distance &apriori_radius_a,
                 const Isis::Distance &sigma_radius_a,
                 const Isis::Distance &apriori_radius_b,
                 const Isis::Distance &sigma_radius_b,
                 const Isis::Distance &apriori_radius_c,
                 const Isis::Distance &sigma_radius_c,
                 const Isis::Distance &apriori_mean_radius,
                 const Isis::Distance &sigma_mean_radius)
              {
                   self.setSolveSettings(targetSolveCodesToStdSet(target_parameter_solve_codes),
                                         apriori_pole_ra,
                                         sigma_pole_ra,
                                         apriori_velocity_pole_ra,
                                         sigma_velocity_pole_ra,
                                         apriori_pole_dec,
                                         sigma_pole_dec,
                                         apriori_velocity_pole_dec,
                                         sigma_velocity_pole_dec,
                                         apriori_pm,
                                         sigma_pm,
                                         apriori_velocity_pm,
                                         sigma_velocity_pm,
                                         solve_radii_method,
                                         apriori_radius_a,
                                         sigma_radius_a,
                                         apriori_radius_b,
                                         sigma_radius_b,
                                         apriori_radius_c,
                                         sigma_radius_c,
                                         apriori_mean_radius,
                                         sigma_mean_radius);
              },
              py::arg("target_parameter_solve_codes"),
              py::arg("apriori_pole_ra"),
              py::arg("sigma_pole_ra"),
              py::arg("apriori_velocity_pole_ra"),
              py::arg("sigma_velocity_pole_ra"),
              py::arg("apriori_pole_dec"),
              py::arg("sigma_pole_dec"),
              py::arg("apriori_velocity_pole_dec"),
              py::arg("sigma_velocity_pole_dec"),
              py::arg("apriori_pm"),
              py::arg("sigma_pm"),
              py::arg("apriori_velocity_pm"),
              py::arg("sigma_velocity_pm"),
              py::arg("solve_radii_method"),
              py::arg("apriori_radius_a"),
              py::arg("sigma_radius_a"),
              py::arg("apriori_radius_b"),
              py::arg("sigma_radius_b"),
              py::arg("apriori_radius_c"),
              py::arg("sigma_radius_c"),
              py::arg("apriori_mean_radius"),
              py::arg("sigma_mean_radius"))
         .def("pole_ra_coefs", &Isis::BundleTargetBody::poleRaCoefs)
         .def("pole_dec_coefs", &Isis::BundleTargetBody::poleDecCoefs)
         .def("pm_coefs", &Isis::BundleTargetBody::pmCoefs)
         .def("radii", &Isis::BundleTargetBody::radii)
         .def("mean_radius", &Isis::BundleTargetBody::meanRadius)
         .def("solve_pole_ra", &Isis::BundleTargetBody::solvePoleRA)
         .def("solve_pole_ra_velocity", &Isis::BundleTargetBody::solvePoleRAVelocity)
         .def("solve_pole_ra_acceleration", &Isis::BundleTargetBody::solvePoleRAAcceleration)
         .def("solve_pole_dec", &Isis::BundleTargetBody::solvePoleDec)
         .def("solve_pole_dec_velocity", &Isis::BundleTargetBody::solvePoleDecVelocity)
         .def("solve_pole_dec_acceleration", &Isis::BundleTargetBody::solvePoleDecAcceleration)
         .def("solve_pm", &Isis::BundleTargetBody::solvePM)
         .def("solve_pm_velocity", &Isis::BundleTargetBody::solvePMVelocity)
         .def("solve_pm_acceleration", &Isis::BundleTargetBody::solvePMAcceleration)
         .def("solve_triaxial_radii", &Isis::BundleTargetBody::solveTriaxialRadii)
         .def("solve_mean_radius", &Isis::BundleTargetBody::solveMeanRadius)
         .def("number_radius_parameters", &Isis::BundleTargetBody::numberRadiusParameters)
         .def("number_parameters", &Isis::BundleTargetBody::numberParameters)
         .def("vtpv", &Isis::BundleTargetBody::vtpv)
         .def("format_bundle_output_string", [](Isis::BundleTargetBody &self, bool error_propagation)
              { return qStringToStdString(self.formatBundleOutputString(error_propagation)); }, py::arg("error_propagation"))
         .def("parameter_list", [](Isis::BundleTargetBody &self)
              { return qStringListToStdVector(self.parameterList()); })
         .def("local_radius", &Isis::BundleTargetBody::localRadius, py::arg("latitude"), py::arg("longitude"))
         .def("copy", [](const Isis::BundleTargetBody &self)
              { return Isis::BundleTargetBody(self); })
         .def("__repr__", [](Isis::BundleTargetBody &self)
              {
                   return "BundleTargetBody(parameters=" + std::to_string(self.numberParameters()) +
                          ", radius_parameters=" + std::to_string(self.numberRadiusParameters()) + ")";
              });

     py::class_<Isis::BundleSettings> bundle_settings(m, "BundleSettings");

     py::enum_<Isis::BundleSettings::ConvergenceCriteria>(bundle_settings, "ConvergenceCriteria")
         .value("Sigma0", Isis::BundleSettings::Sigma0)
         .value("ParameterCorrections", Isis::BundleSettings::ParameterCorrections);

     py::enum_<Isis::BundleSettings::MaximumLikelihoodModel>(bundle_settings, "MaximumLikelihoodModel")
         .value("NoMaximumLikelihoodEstimator", Isis::BundleSettings::NoMaximumLikelihoodEstimator)
         .value("Huber", Isis::BundleSettings::Huber)
         .value("ModifiedHuber", Isis::BundleSettings::ModifiedHuber)
         .value("Welsch", Isis::BundleSettings::Welsch)
         .value("Chen", Isis::BundleSettings::Chen);

     bundle_settings
         .def(py::init<>())
         .def(py::init<const Isis::BundleSettings &>(), py::arg("other"))
         .def("set_validate_network", &Isis::BundleSettings::setValidateNetwork, py::arg("validate"))
         .def("validate_network", &Isis::BundleSettings::validateNetwork)
         .def("set_solve_options",
              &Isis::BundleSettings::setSolveOptions,
              py::arg("solve_observation_mode") = false,
              py::arg("update_cube_label") = false,
              py::arg("error_propagation") = false,
              py::arg("solve_radius") = false,
              py::arg("coord_type_bundle") = Isis::SurfacePoint::Latitudinal,
              py::arg("coord_type_reports") = Isis::SurfacePoint::Latitudinal,
              py::arg("global_point_coord1_apriori_sigma") = Isis::Null,
              py::arg("global_point_coord2_apriori_sigma") = Isis::Null,
              py::arg("global_point_coord3_apriori_sigma") = Isis::Null)
         .def("set_outlier_rejection",
              &Isis::BundleSettings::setOutlierRejection,
              py::arg("outlier_rejection"),
              py::arg("multiplier") = 1.0)
         .def("set_create_inverse_matrix", &Isis::BundleSettings::setCreateInverseMatrix, py::arg("create_matrix"))
         .def("control_point_coord_type_reports", &Isis::BundleSettings::controlPointCoordTypeReports)
         .def("control_point_coord_type_bundle", &Isis::BundleSettings::controlPointCoordTypeBundle)
         .def("create_inverse_matrix", &Isis::BundleSettings::createInverseMatrix)
         .def("solve_observation_mode", &Isis::BundleSettings::solveObservationMode)
         .def("solve_radius", &Isis::BundleSettings::solveRadius)
         .def("update_cube_label", &Isis::BundleSettings::updateCubeLabel)
         .def("error_propagation", &Isis::BundleSettings::errorPropagation)
         .def("outlier_rejection", &Isis::BundleSettings::outlierRejection)
         .def("outlier_rejection_multiplier", &Isis::BundleSettings::outlierRejectionMultiplier)
         .def("global_point_coord1_apriori_sigma", &Isis::BundleSettings::globalPointCoord1AprioriSigma)
         .def("global_point_coord2_apriori_sigma", &Isis::BundleSettings::globalPointCoord2AprioriSigma)
         .def("global_point_coord3_apriori_sigma", &Isis::BundleSettings::globalPointCoord3AprioriSigma)
         .def("set_observation_solve_options", [](Isis::BundleSettings &self, const std::vector<Isis::BundleObservationSolveSettings> &values)
              { self.setObservationSolveOptions(stdVectorToQList(values)); }, py::arg("values"))
         .def("set_bundle_target_body", [](Isis::BundleSettings &self, const Isis::BundleTargetBody &bundle_target_body)
              {
                   self.setBundleTargetBody(Isis::BundleTargetBodyQsp(new Isis::BundleTargetBody(bundle_target_body)));
              }, py::arg("bundle_target_body"))
         .def("number_solve_settings", &Isis::BundleSettings::numberSolveSettings)
         .def("observation_solve_settings", [] (const Isis::BundleSettings &self)
              { return bundleObservationSolveSettingsToPyList(self.observationSolveSettings()); })
         .def("observation_solve_settings", [] (const Isis::BundleSettings &self, int index)
              { return self.observationSolveSettings(index); }, py::arg("index"))
         .def("observation_solve_settings", [] (const Isis::BundleSettings &self, const std::string &observation_number)
              { return self.observationSolveSettings(stdStringToQString(observation_number)); }, py::arg("observation_number"))
         .def("bundle_target_body", [](const Isis::BundleSettings &self) -> py::object
              {
                   Isis::BundleTargetBodyQsp bundle_target_body = self.bundleTargetBody();
                   if (bundle_target_body.isNull())
                   {
                        return py::none();
                   }
                   return py::cast(Isis::BundleTargetBody(*bundle_target_body));
              })
         .def_static("string_to_convergence_criteria", [](const std::string &criteria)
                     { return Isis::BundleSettings::stringToConvergenceCriteria(stdStringToQString(criteria)); }, py::arg("criteria"))
         .def_static("convergence_criteria_to_string", [](Isis::BundleSettings::ConvergenceCriteria criteria)
                     { return qStringToStdString(Isis::BundleSettings::convergenceCriteriaToString(criteria)); }, py::arg("criteria"))
         .def("set_convergence_criteria",
              &Isis::BundleSettings::setConvergenceCriteria,
              py::arg("criteria"),
              py::arg("threshold"),
              py::arg("maximum_iterations"))
         .def("convergence_criteria", &Isis::BundleSettings::convergenceCriteria)
         .def("convergence_criteria_threshold", &Isis::BundleSettings::convergenceCriteriaThreshold)
         .def("convergence_criteria_maximum_iterations", &Isis::BundleSettings::convergenceCriteriaMaximumIterations)
         .def("add_maximum_likelihood_estimator_model",
              [](Isis::BundleSettings &self,
                 Isis::BundleSettings::MaximumLikelihoodModel model,
                 double c_quantile)
              {
                   self.addMaximumLikelihoodEstimatorModel(
                       toMaximumLikelihoodWFunctionsModel(model),
                       c_quantile);
              },
              py::arg("model"),
              py::arg("c_quantile"))
         .def("maximum_likelihood_estimator_models", [](const Isis::BundleSettings &self)
              { return maximumLikelihoodEstimatorModelsToPyList(self.maximumLikelihoodEstimatorModels()); })
         .def("number_target_body_parameters", &Isis::BundleSettings::numberTargetBodyParameters)
         .def("solve_target_body", &Isis::BundleSettings::solveTargetBody)
         .def("solve_pole_ra", &Isis::BundleSettings::solvePoleRA)
         .def("solve_pole_ra_velocity", &Isis::BundleSettings::solvePoleRAVelocity)
         .def("solve_pole_dec", &Isis::BundleSettings::solvePoleDec)
         .def("solve_pole_dec_velocity", &Isis::BundleSettings::solvePoleDecVelocity)
         .def("solve_pm", &Isis::BundleSettings::solvePM)
         .def("solve_pm_velocity", &Isis::BundleSettings::solvePMVelocity)
         .def("solve_pm_acceleration", &Isis::BundleSettings::solvePMAcceleration)
         .def("solve_triaxial_radii", &Isis::BundleSettings::solveTriaxialRadii)
         .def("solve_mean_radius", &Isis::BundleSettings::solveMeanRadius)
         .def("set_output_file_prefix", [](Isis::BundleSettings &self, const std::string &output_file_prefix)
              { self.setOutputFilePrefix(stdStringToQString(output_file_prefix)); }, py::arg("output_file_prefix"))
         .def("output_file_prefix", [](const Isis::BundleSettings &self)
              { return qStringToStdString(self.outputFilePrefix()); })
         .def("set_cube_list", [](Isis::BundleSettings &self, const std::string &file_name)
              { self.setCubeList(stdStringToQString(file_name)); }, py::arg("file_name"))
         .def("cube_list", [](const Isis::BundleSettings &self)
              { return qStringToStdString(self.cubeList()); })
         .def("copy", [](const Isis::BundleSettings &self)
              { return Isis::BundleSettings(self); })
         .def("__repr__", [](const Isis::BundleSettings &self)
              {
                   return "BundleSettings(validate_network=" + std::string(self.validateNetwork() ? "True" : "False") +
                          ", solve_observation_mode=" + std::string(self.solveObservationMode() ? "True" : "False") + ")";
              });

  // LidarControlPoint — extends ControlPoint for LOLA lidar measurements.
  // Added: 2026-04-10
  py::class_<Isis::LidarControlPoint, Isis::ControlPoint>(m, "LidarControlPoint")
      .def(py::init<>(),
           "Construct a default LidarControlPoint with zero range, sigma, and time.")
      .def("set_range",
           [](Isis::LidarControlPoint &self, double range) { return self.setRange(range); },
           py::arg("range"),
           "Set the lidar range (metres). Returns ControlPoint.Status.")
      .def("set_sigma_range",
           [](Isis::LidarControlPoint &self, double sigma_range) { return self.setSigmaRange(sigma_range); },
           py::arg("sigma_range"),
           "Set the lidar range sigma. Returns ControlPoint.Status.")
      .def("set_time",
           [](Isis::LidarControlPoint &self, Isis::iTime t) { return self.setTime(t); },
           py::arg("time"),
           "Set the acquisition time. Returns ControlPoint.Status.")
      .def("add_simultaneous",
           [](Isis::LidarControlPoint &self, const std::string &sn) {
               return self.addSimultaneous(QString::fromStdString(sn));
           },
           py::arg("serial_number"),
           "Add a serial number for a simultaneously imaged cube. Returns ControlPoint.Status.")
      .def("compute_residuals",
           [](Isis::LidarControlPoint &self) { return self.ComputeResiduals(); },
           "Compute residuals for all lidar measures. Returns ControlPoint.Status.")
      .def("range",
           [](Isis::LidarControlPoint &self) { return self.range(); },
           "Return the lidar range value.")
      .def("sigma_range",
           [](Isis::LidarControlPoint &self) { return self.sigmaRange(); },
           "Return the lidar range sigma.")
      .def("time",
           [](Isis::LidarControlPoint &self) { return self.time(); },
           "Return the acquisition iTime.")
      .def("sn_simultaneous",
           [](const Isis::LidarControlPoint &self) {
               QStringList qlist = self.snSimultaneous();
               std::vector<std::string> result;
               result.reserve(static_cast<size_t>(qlist.size()));
               for (const QString &s : qlist) {
                   result.push_back(s.toStdString());
               }
               return result;
           },
           "Return the list of serial numbers for simultaneously imaged cubes.")
      .def("is_simultaneous",
           [](Isis::LidarControlPoint &self, const std::string &sn) {
               return self.isSimultaneous(QString::fromStdString(sn));
           },
           py::arg("serial_number"),
           "Return True if the given serial number is in the simultaneous list.")
      .def("__repr__",
           [](Isis::LidarControlPoint &self) {
               return "LidarControlPoint(id='" + qStringToStdString(self.GetId()) +
                      "', range=" + std::to_string(self.range()) +
                      ", sigma_range=" + std::to_string(self.sigmaRange()) + ")";
           });

  // ControlNetVersioner — reads and writes all control network file format versions.
  // Added: 2026-04-10
  py::class_<Isis::ControlNetVersioner, std::unique_ptr<Isis::ControlNetVersioner>>(m, "ControlNetVersioner")
      // NOTE: The default constructor and copy constructor are private in upstream ISIS,
      //       so we use std::unique_ptr holder and only expose the two public constructors.
      .def(py::init([](Isis::ControlNet *net) {
               return std::unique_ptr<Isis::ControlNetVersioner>(
                   new Isis::ControlNetVersioner(net));
           }),
           py::arg("net"),
           py::keep_alive<1, 2>(),
           "Construct a ControlNetVersioner from an existing ControlNet.\n\n"
           "Parameters\n"
           "----------\n"
           "net : ControlNet\n"
           "    The control network to serialize.")
      .def(py::init([](const std::string &filename) {
               Isis::FileName fn(QString::fromStdString(filename));
               return std::unique_ptr<Isis::ControlNetVersioner>(
                   new Isis::ControlNetVersioner(fn, nullptr));
           }),
           py::arg("filename"),
           "Construct a ControlNetVersioner by reading a network file.\n\n"
           "Parameters\n"
           "----------\n"
           "filename : str\n"
           "    Path to a control network file (.net or .pvl).")
      .def("net_id",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.netId());
           },
           "Return the network ID string.")
      .def("target_name",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.targetName());
           },
           "Return the target body name (e.g. 'MARS').")
      .def("creation_date",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.creationDate());
           },
           "Return the creation date string.")
      .def("last_modification_date",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.lastModificationDate());
           },
           "Return the last modification date string.")
      .def("description",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.description());
           },
           "Return the network description string.")
      .def("user_name",
           [](const Isis::ControlNetVersioner &self) {
               return qStringToStdString(self.userName());
           },
           "Return the user name string.")
      .def("num_points",
           [](const Isis::ControlNetVersioner &self) {
               return self.numPoints();
           },
           "Return the number of control points stored in the versioner.")
      .def("write",
           [](Isis::ControlNetVersioner &self, const std::string &filename) {
               Isis::FileName fn(QString::fromStdString(filename));
               self.write(fn);
           },
           py::arg("filename"),
           "Write the control network to a file in the latest format.\n\n"
           "Parameters\n"
           "----------\n"
           "filename : str\n"
           "    Output file path.")
      .def("to_pvl",
           [](Isis::ControlNetVersioner &self) {
               return self.toPvl();
           },
           "Convert the stored network to a Pvl object.")
      .def("__repr__",
           [](Isis::ControlNetVersioner &self) {
               return "ControlNetVersioner(net_id='" + qStringToStdString(self.netId()) +
                      "', target='" + qStringToStdString(self.targetName()) +
                      "', num_points=" + std::to_string(self.numPoints()) + ")";
           });
}
