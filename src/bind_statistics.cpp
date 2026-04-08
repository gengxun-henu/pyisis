// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-21  Geng Xun added Statistics, Histogram, GroupedStatistics, MultivariateStatistics, and VecFilter bindings
// Purpose: pybind11 bindings for ISIS statistics, histogram, grouped-statistics, multivariate-statistics, and vector-filter utilities

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <stdexcept>
#include <vector>

#include <QVector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Cube.h"
#include "GaussianDistribution.h"
#include "GroupedStatistics.h"
#include "Histogram.h"
#include "ImageHistogram.h"
#include "MultivariateStatistics.h"
#include "Statistics.h"
#include "VecFilter.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
    /**
     * Helper function to convert a QVector<QString> to a std::vector<std::string>. This is needed because some ISIS APIs use QVector<QString> and we want to be able to return those as std::vector<std::string> in Python for better interoperability with Python code.
     * @param values The QVector<QString> to convert.
     * @return A std::vector<std::string> containing the same strings as the input QVector<QString>.
     * @throws std::runtime_error if any of the QStrings in the input QVector cannot be converted to std::string (this should not happen under normal circumstances, but we include it for completeness).
     * 
     */
std::vector<std::string> qStringVectorToStdVector(const QVector<QString> &values) {
  std::vector<std::string> result;
  result.reserve(values.size());
  for (const QString &value : values) {
    result.push_back(qStringToStdString(value));
  }
  return result;
}
}  // namespace

/**
 * Bind the Isis::Statistics and Isis::Histogram classes to Python using pybind11. These classes provide functionality for 
 * computing statistics and histograms on image data, and are commonly used in ISIS applications for analyzing image cubes. 
 * The bindings will allow Python users to create Statistics and Histogram objects, add data to them, and compute various statistical 
 * measures and histogram properties.
 * @see Isis::Statistics
 * @see Isis::Histogram
 * @param m The pybind11 module to which the bindings will be added.
 * 
 */

/**
 * @brief Bindings for Statistics and Histogram classes
 * This function creates Python bindings for the Isis::Statistics and Isis::Histogram classes using pybind11. The Statistics 
 * class provides methods for computing various statistical measures on image data, while the Histogram class 
 * extends Statistics to provide functionality for creating and manipulating histograms. These bindings allow Python 
 * users to utilize the powerful statistical analysis capabilities of these classes in their Python code when working with ISIS image cubes.
 */
void bind_statistics(py::module_ &m) {
  py::class_<Isis::Statistics>(m, "Statistics")
      .def(py::init<>())
      .def(py::init<const Isis::PvlGroup &>(), py::arg("stats_group"))
      .def(py::init<const Isis::Statistics &>(), py::arg("other"))
      .def("reset", &Isis::Statistics::Reset)
      .def("add_data",
           [](Isis::Statistics &self, const std::vector<double> &data) {
             self.AddData(data.data(), static_cast<unsigned int>(data.size()));
           },
           py::arg("data"))
      .def("add_data",
           static_cast<void (Isis::Statistics::*)(const double)>(&Isis::Statistics::AddData),
           py::arg("value"))
      .def("remove_data",
           [](Isis::Statistics &self, const std::vector<double> &data) {
             self.RemoveData(data.data(), static_cast<unsigned int>(data.size()));
           },
           py::arg("data"))
      .def("remove_data",
           static_cast<void (Isis::Statistics::*)(const double)>(&Isis::Statistics::RemoveData),
           py::arg("value"))
      .def("set_valid_range", &Isis::Statistics::SetValidRange,
           py::arg("minimum") = Isis::ValidMinimum,
           py::arg("maximum") = Isis::ValidMaximum)
      .def("valid_minimum", &Isis::Statistics::ValidMinimum)
      .def("valid_maximum", &Isis::Statistics::ValidMaximum)
      .def("in_range", &Isis::Statistics::InRange, py::arg("value"))
      .def("above_range", &Isis::Statistics::AboveRange, py::arg("value"))
      .def("below_range", &Isis::Statistics::BelowRange, py::arg("value"))
      .def("average", &Isis::Statistics::Average)
      .def("standard_deviation", &Isis::Statistics::StandardDeviation)
      .def("variance", &Isis::Statistics::Variance)
      .def("sum", &Isis::Statistics::Sum)
      .def("sum_square", &Isis::Statistics::SumSquare)
      .def("rms", &Isis::Statistics::Rms)
      .def("minimum", &Isis::Statistics::Minimum)
      .def("maximum", &Isis::Statistics::Maximum)
      .def("chebyshev_minimum", &Isis::Statistics::ChebyshevMinimum, py::arg("percent") = 99.5)
      .def("chebyshev_maximum", &Isis::Statistics::ChebyshevMaximum, py::arg("percent") = 99.5)
      .def("best_minimum", &Isis::Statistics::BestMinimum, py::arg("percent") = 99.5)
      .def("best_maximum", &Isis::Statistics::BestMaximum, py::arg("percent") = 99.5)
      .def("z_score", &Isis::Statistics::ZScore, py::arg("value"))
      .def("total_pixels", &Isis::Statistics::TotalPixels)
      .def("valid_pixels", &Isis::Statistics::ValidPixels)
      .def("over_range_pixels", &Isis::Statistics::OverRangePixels)
      .def("under_range_pixels", &Isis::Statistics::UnderRangePixels)
      .def("null_pixels", &Isis::Statistics::NullPixels)
      .def("lis_pixels", &Isis::Statistics::LisPixels)
      .def("lrs_pixels", &Isis::Statistics::LrsPixels)
      .def("his_pixels", &Isis::Statistics::HisPixels)
      .def("hrs_pixels", &Isis::Statistics::HrsPixels)
      .def("out_of_range_pixels", &Isis::Statistics::OutOfRangePixels)
      .def("removed_data", &Isis::Statistics::RemovedData)
      .def("to_pvl",
           [](const Isis::Statistics &self, const std::string &name) {
             return self.toPvl(stdStringToQString(name));
           },
           py::arg("name") = "Statistics")
      .def("copy", [](const Isis::Statistics &self) { return Isis::Statistics(self); })
      .def("__repr__",
           [](const Isis::Statistics &self) {
             return "Statistics(valid_pixels=" + std::to_string(self.ValidPixels()) + ")";
           });
  /**
   * @brief Bindings for Histogram class
   * This class provides functionality for creating and manipulating histograms, which are used to represent the distribution of data values.
   * @param m The pybind11 module to which the Histogram bindings will be added.
   */
  py::class_<Isis::Histogram, Isis::Statistics>(m, "Histogram")
      .def(py::init<>())
      .def(py::init<double, double, int>(), py::arg("minimum"), py::arg("maximum"), py::arg("bins") = 1024)
      .def("set_bins", &Isis::Histogram::SetBins, py::arg("bins"))
      .def("reset", &Isis::Histogram::Reset)
      .def("add_data",
           [](Isis::Histogram &self, const std::vector<double> &data) {
             self.AddData(data.data(), static_cast<unsigned int>(data.size()));
           },
           py::arg("data"))
      .def("add_data",
           static_cast<void (Isis::Histogram::*)(const double)>(&Isis::Histogram::AddData),
           py::arg("value"))
      .def("remove_data",
           [](Isis::Histogram &self, const std::vector<double> &data) {
             self.RemoveData(data.data(), static_cast<unsigned int>(data.size()));
           },
           py::arg("data"))
      .def("median", &Isis::Histogram::Median)
      .def("mode", &Isis::Histogram::Mode)
      .def("percent", &Isis::Histogram::Percent, py::arg("percent"))
      .def("skew", &Isis::Histogram::Skew)
      .def("bin_count", &Isis::Histogram::BinCount, py::arg("index"))
      .def("bin_range",
           [](const Isis::Histogram &self, int index) {
             double low = 0.0;
             double high = 0.0;
             self.BinRange(index, low, high);
             return py::make_tuple(low, high);
           },
           py::arg("index"))
      .def("bin_middle", &Isis::Histogram::BinMiddle, py::arg("index"))
      .def("bin_size", &Isis::Histogram::BinSize)
      .def("bins", &Isis::Histogram::Bins)
      .def("max_bin_count", &Isis::Histogram::MaxBinCount)
      .def("bin_range_start", &Isis::Histogram::BinRangeStart)
      .def("bin_range_end", &Isis::Histogram::BinRangeEnd)
      .def("set_valid_range", &Isis::Histogram::SetValidRange,
           py::arg("minimum") = Isis::ValidMinimum,
           py::arg("maximum") = Isis::ValidMaximum);

  py::class_<Isis::ImageHistogram, Isis::Histogram>(m, "ImageHistogram")
       .def(py::init<double, double, int>(), py::arg("minimum"), py::arg("maximum"), py::arg("bins") = 1024);

  py::class_<Isis::GaussianDistribution, Isis::Statistics>(m, "GaussianDistribution")
      .def(py::init<double, double>(), py::arg("mean") = 0.0, py::arg("standard_deviation") = 1.0)
      .def("probability", &Isis::GaussianDistribution::Probability, py::arg("value"))
      .def("cumulative_distribution", &Isis::GaussianDistribution::CumulativeDistribution, py::arg("value"))
      .def("inverse_cumulative_distribution", &Isis::GaussianDistribution::InverseCumulativeDistribution,
           py::arg("percent"))
      .def("mean", &Isis::GaussianDistribution::Mean)
      .def("distribution_standard_deviation", &Isis::GaussianDistribution::StandardDeviation);

  py::class_<Isis::GroupedStatistics>(m, "GroupedStatistics")
      .def(py::init<>())
      .def(py::init<const Isis::GroupedStatistics &>(), py::arg("other"))
      .def("add_statistic",
           [](Isis::GroupedStatistics &self, const std::string &stat_type, double new_stat) {
             self.AddStatistic(stdStringToQString(stat_type), new_stat);
           },
           py::arg("stat_type"), py::arg("new_stat"))
      .def("get_statistics",
           [](const Isis::GroupedStatistics &self, const std::string &stat_type) -> const Isis::Statistics & {
             return self.GetStatistics(stdStringToQString(stat_type));
           },
           py::arg("stat_type"),
           py::return_value_policy::reference_internal)
      .def("get_statistic_types",
           [](const Isis::GroupedStatistics &self) {
             return qStringVectorToStdVector(self.GetStatisticTypes());
           });

  py::class_<Isis::MultivariateStatistics>(m, "MultivariateStatistics")
      .def(py::init<>())
      .def(py::init<const Isis::PvlObject &>(), py::arg("stats_object"))
      .def("reset", &Isis::MultivariateStatistics::Reset)
      .def("add_data",
           [](Isis::MultivariateStatistics &self, const std::vector<double> &x, const std::vector<double> &y) {
             if (x.size() != y.size()) {
               throw std::invalid_argument("x and y must have the same length");
             }
             self.AddData(x.data(), y.data(), static_cast<unsigned int>(x.size()));
           },
           py::arg("x"), py::arg("y"))
      .def("add_data",
           static_cast<void (Isis::MultivariateStatistics::*)(double, double, unsigned int)>(&Isis::MultivariateStatistics::AddData),
           py::arg("x"), py::arg("y"), py::arg("count") = 1)
      .def("remove_data",
           [](Isis::MultivariateStatistics &self, const std::vector<double> &x, const std::vector<double> &y) {
             if (x.size() != y.size()) {
               throw std::invalid_argument("x and y must have the same length");
             }
             self.RemoveData(x.data(), y.data(), static_cast<unsigned int>(x.size()));
           },
           py::arg("x"), py::arg("y"))
      .def("x_statistics", &Isis::MultivariateStatistics::X)
      .def("y_statistics", &Isis::MultivariateStatistics::Y)
      .def("sum_xy", &Isis::MultivariateStatistics::SumXY)
      .def("covariance", &Isis::MultivariateStatistics::Covariance)
      .def("correlation", &Isis::MultivariateStatistics::Correlation)
      .def("linear_regression",
           [](const Isis::MultivariateStatistics &self) {
             double a = 0.0;
             double b = 0.0;
             self.LinearRegression(a, b);
             return py::make_tuple(a, b);
           })
      .def("valid_pixels", &Isis::MultivariateStatistics::ValidPixels)
      .def("invalid_pixels", &Isis::MultivariateStatistics::InvalidPixels)
      .def("total_pixels", &Isis::MultivariateStatistics::TotalPixels)
      .def("to_pvl",
           [](const Isis::MultivariateStatistics &self, const std::string &name) {
             return self.toPvl(stdStringToQString(name));
           },
           py::arg("name") = "MultivariateStatistics");

  py::class_<Isis::VecFilter>(m, "VecFilter")
      .def(py::init<>())
      .def("low_pass", &Isis::VecFilter::LowPass, py::arg("input"), py::arg("box_size"))
      .def("high_pass",
           [](Isis::VecFilter &self, const std::vector<double> &in1, const std::vector<double> &in2) {
             return self.HighPass(in1, in2);
           },
           py::arg("input1"), py::arg("input2"))
      .def("high_pass",
           [](Isis::VecFilter &self,
              const std::vector<double> &in1,
              const std::vector<double> &in2,
              const std::vector<int> &valid_points,
              int max_points,
              const std::string &mode) {
             return self.HighPass(in1, in2, valid_points, max_points, stdStringToQString(mode));
           },
           py::arg("input1"),
           py::arg("input2"),
           py::arg("valid_points"),
           py::arg("max_points"),
           py::arg("mode") = "SUBTRACT");
}
