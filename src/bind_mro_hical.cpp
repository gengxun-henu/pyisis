// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Source ISIS headers:
// - reference/upstream_isis/src/mro/objs/HiCal/GainNonLinearity.h
// - reference/upstream_isis/src/mro/objs/HiCal/GainTemperature.h
// - reference/upstream_isis/src/mro/objs/HiCal/GainUnitConversion.h
// - reference/upstream_isis/src/mro/objs/HiCal/Module.h
// - reference/upstream_isis/src/mro/objs/HiCal/HiCalTypes.h
// - reference/upstream_isis/src/mro/objs/HiLab/HiLab.h
// Source classes: Isis::GainNonLinearity, Isis::GainTemperature, Isis::GainUnitConversion,
//                 Isis::HiLab
// Source header author(s): Kris Becker (gain headers); not explicitly stated in all upstream helper headers
// Binding author: Geng Xun
// Created: 2026-04-09
// Updated: 2026-04-09  Geng Xun added Python-friendly HiCal gain wrappers backed by local Pvl+conf construction.
// Updated: 2026-04-09  Geng Xun replaced direct HiCal class bindings with stable local wrappers because the linked ISIS library does not export the required HiCalConf symbols.
// Updated: 2026-04-10  Geng Xun added HiLab binding exposing HiRise cube label accessors.
// Purpose: Expose selected MRO HiCal gain modules with stable Python-friendly constructors and vector/history helpers.
//          Also exposes HiLab for HiRise instrument label parsing.

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Cube.h"
#include "HiLab.h"
#include "Pvl.h"
#include "helpers.h"

namespace py = pybind11;
namespace fs = std::filesystem;

namespace {

class HiCalModuleWrapper {
  public:
    explicit HiCalModuleWrapper(std::string moduleName)
      : m_name(std::move(moduleName)) {
    }

    std::string name() const {
      return m_name;
    }

    std::string csvFile() const {
      return m_csvFile;
    }

    int size() const {
      return static_cast<int>(m_data.size());
    }

    const std::vector<double> &data() const {
      return m_data;
    }

    const std::vector<std::string> &history() const {
      return m_history;
    }

    double at(py::ssize_t index) const {
      py::ssize_t resolvedIndex = index;
      if (resolvedIndex < 0) {
        resolvedIndex += static_cast<py::ssize_t>(m_data.size());
      }

      if (resolvedIndex < 0 || resolvedIndex >= static_cast<py::ssize_t>(m_data.size())) {
        throw py::index_error("module index out of range");
      }

      return m_data[resolvedIndex];
    }

  protected:
    void setCsvFile(const std::string &csvFile) {
      m_csvFile = csvFile;
    }

    void setData(std::vector<double> values) {
      m_data = std::move(values);
    }

    void clearHistory() {
      m_history.clear();
    }

    void addHistory(const std::string &entry) {
      m_history.push_back(entry);
    }

  private:
    std::string m_name;
    std::string m_csvFile;
    std::vector<double> m_data;
    std::vector<std::string> m_history;
};

std::string normalizeUnits(const std::string &units) {
  std::string normalized = units;
  std::transform(normalized.begin(), normalized.end(), normalized.begin(),
                 [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
  return normalized;
}

std::string keywordValue(const Isis::PvlContainer &container, const std::string &keywordName) {
  return qStringToStdString(container.findKeyword(stdStringToQString(keywordName))[0]);
}

double keywordDoubleValue(const Isis::PvlContainer &container, const std::string &keywordName) {
  return container.findKeyword(stdStringToQString(keywordName))[0].toDouble();
}

int keywordIntValue(const Isis::PvlContainer &container, const std::string &keywordName) {
  return container.findKeyword(stdStringToQString(keywordName))[0].toInt();
}

Isis::PvlObject loadHicalObject(const std::string &confPath) {
  Isis::Pvl conf(stdStringToQString(confPath));
  return conf.findObject("Hical", Isis::PvlObject::Traverse);
}

Isis::PvlGroup findProfile(const Isis::PvlObject &hicalObject, const std::string &profileName) {
  for (int groupIndex = 0; groupIndex < hicalObject.groups(); groupIndex++) {
    Isis::PvlGroup profile = hicalObject.group(groupIndex);
    if (profile.isNamed("Profile")
        && profile.hasKeyword("Name")
        && qStringToStdString(profile["Name"][0]) == profileName) {
      return profile;
    }
  }

  throw py::value_error("Unable to find HiCal profile '" + profileName + "' in conf file");
}

std::string resolvePathFromConf(const std::string &confPath, const std::string &rawPath) {
  if (rawPath.empty() || rawPath[0] == '$') {
    return rawPath;
  }

  fs::path candidate(rawPath);
  if (candidate.is_absolute()) {
    return candidate.string();
  }

  return (fs::path(confPath).parent_path() / candidate).lexically_normal().string();
}

double readFirstNumericCsvValue(const std::string &csvPath) {
  std::ifstream input(csvPath);
  if (!input) {
    throw py::value_error("Unable to open CSV file '" + csvPath + "'");
  }

  std::string line;
  while (std::getline(input, line)) {
    std::replace(line.begin(), line.end(), ',', ' ');
    std::istringstream lineStream(line);
    std::string token;
    while (lineStream >> token) {
      if (!token.empty() && token[0] == '#') {
        break;
      }

      char *end = nullptr;
      const double value = std::strtod(token.c_str(), &end);
      if (end != token.c_str() && *end == '\0') {
        return value;
      }
    }
  }

  throw py::value_error("Unable to find a numeric value in CSV file '" + csvPath + "'");
}

class GainNonLinearityWrapper : public HiCalModuleWrapper {
  public:
    GainNonLinearityWrapper()
      : HiCalModuleWrapper("GainNonLinearity") {
    }

    GainNonLinearityWrapper(Isis::Pvl &label, const std::string &confPath)
      : HiCalModuleWrapper("GainNonLinearity") {
      init(label, confPath);
    }

  private:
    void init(Isis::Pvl &, const std::string &confPath) {
      const Isis::PvlObject hicalObject = loadHicalObject(confPath);
      const Isis::PvlGroup profile = findProfile(hicalObject, "GainNonLinearity");
      const std::string csvPath = resolvePathFromConf(confPath, keywordValue(profile, "NonLinearityGain"));
      const double gainFactor = readFirstNumericCsvValue(csvPath);

      setCsvFile(csvPath);
      setData({gainFactor});
      clearHistory();
      addHistory("Profile[GainNonLinearity]");
      addHistory("NonLinearityGainFactor[" + std::to_string(gainFactor) + "]");
    }
};

class GainTemperatureWrapper : public HiCalModuleWrapper {
  public:
    GainTemperatureWrapper()
      : HiCalModuleWrapper("GainTemperature") {
    }

    GainTemperatureWrapper(Isis::Pvl &label, const std::string &confPath)
      : HiCalModuleWrapper("GainTemperature") {
      init(label, confPath);
    }

  private:
    void init(Isis::Pvl &label, const std::string &confPath) {
      const Isis::PvlObject hicalObject = loadHicalObject(confPath);
      const Isis::PvlGroup profile = findProfile(hicalObject, "GainTemperature");
      const Isis::PvlGroup dimensions = label.findGroup("Dimensions", Isis::Pvl::Traverse);
      const Isis::PvlGroup instrument = label.findGroup("Instrument", Isis::Pvl::Traverse);

      std::string csvKeyword = "FpaGain";
      if (!profile.hasKeyword(csvKeyword.c_str()) && profile.hasKeyword("FPAGain")) {
        csvKeyword = "FPAGain";
      }

      if (!profile.hasKeyword(csvKeyword.c_str())) {
        throw py::value_error("GainTemperature profile is missing FpaGain/FPAGain CSV configuration");
      }

      const std::string csvPath = resolvePathFromConf(confPath, keywordValue(profile, csvKeyword));
      const double fpaFactor = readFirstNumericCsvValue(csvPath);
      const double referenceTemperature = hicalObject.hasKeyword("FpaReferenceTemperature")
        ? keywordDoubleValue(hicalObject, "FpaReferenceTemperature")
        : 21.0;
      const double positiveTemperature = keywordDoubleValue(instrument, "FpaPositiveYTemperature");
      const double negativeTemperature = keywordDoubleValue(instrument, "FpaNegativeYTemperature");
      const double averageTemperature = (positiveTemperature + negativeTemperature) / 2.0;
      const double correction = 1.0 - (fpaFactor * (averageTemperature - referenceTemperature));
      const int samples = keywordIntValue(dimensions, "Samples");

      setCsvFile(csvPath);
      setData(std::vector<double>(samples, correction));
      clearHistory();
      addHistory("Profile[GainTemperature]");
      addHistory("FpaTemperatureFactor[" + std::to_string(fpaFactor) + "]");
      addHistory("FpaAverageTemperature[" + std::to_string(averageTemperature) + "]");
      addHistory("FpaReferenceTemperature[" + std::to_string(referenceTemperature) + "]");
      addHistory("Correction[" + std::to_string(correction) + "]");
    }
};

class GainUnitConversionWrapper : public HiCalModuleWrapper {
  public:
    GainUnitConversionWrapper()
      : HiCalModuleWrapper("GainUnitConversion") {
    }

    GainUnitConversionWrapper(Isis::Pvl &label, const std::string &, const std::string &units,
                              Isis::Cube *cube)
      : HiCalModuleWrapper("GainUnitConversion") {
      init(label, units, cube);
    }

  private:

    void init(Isis::Pvl &label, const std::string &units, Isis::Cube *cube) {
      const std::string normalizedUnits = normalizeUnits(units);
      if (normalizedUnits == "IOF") {
        if (cube == nullptr) {
          throw py::value_error("GainUnitConversion units='IOF' requires a cube so HiCalConf can compute sun distance");
        }

        throw py::value_error("GainUnitConversion units='IOF' is unavailable in this build because the linked ISIS library does not export HiCalConf::sunDistanceAU");
      }

      const Isis::PvlGroup instrument = label.findGroup("Instrument", Isis::Pvl::Traverse);
      const double scanExposureDuration = keywordDoubleValue(instrument, "ScanExposureDuration");

      clearHistory();
      addHistory("Profile[GainUnitConversion]");

      if (normalizedUnits == "DN/US") {
        setData({scanExposureDuration});
        addHistory("ScanExposureDuration[" + std::to_string(scanExposureDuration) + "]");
        addHistory("DN/uS_Factor[" + std::to_string(scanExposureDuration) + "]");
        addHistory("Units[DNs/microsecond]");
      }
      else {
        setData({1.0});
        addHistory("DN_Factor[1]");
        addHistory("Units[DN]");
      }
    }
};
template <typename WrapperType>
void bindWrapperSurface(py::class_<WrapperType> &pyClass, const std::string &pythonName) {
  pyClass
    .def("name", &WrapperType::name)
    .def("csv_file", &WrapperType::csvFile)
    .def("size", &WrapperType::size)
    .def("data", &WrapperType::data)
    .def("history", &WrapperType::history)
    .def("at", &WrapperType::at, py::arg("index"))
    .def("__len__", &WrapperType::size)
    .def("__getitem__", &WrapperType::at, py::arg("index"))
    .def("__repr__",
      [pythonName](const WrapperType &self) {
        return pythonName + "(size=" + std::to_string(self.size()) + ")";
      });
}

}  // namespace

void bind_mro_hical(py::module_ &m) {
  py::class_<GainNonLinearityWrapper> gainNonLinearity(m, "GainNonLinearity");
  gainNonLinearity
    .def(py::init<>())
    .def(py::init<Isis::Pvl &, const std::string &>(),
      py::arg("label"),
      py::arg("conf_path"));
  bindWrapperSurface(gainNonLinearity, "GainNonLinearity");

  py::class_<GainTemperatureWrapper> gainTemperature(m, "GainTemperature");
  gainTemperature
    .def(py::init<>())
    .def(py::init<Isis::Pvl &, const std::string &>(),
      py::arg("label"),
      py::arg("conf_path"));
  bindWrapperSurface(gainTemperature, "GainTemperature");

  py::class_<GainUnitConversionWrapper> gainUnitConversion(m, "GainUnitConversion");
  gainUnitConversion
    .def(py::init<>())
    .def(py::init<Isis::Pvl &, const std::string &, const std::string &, Isis::Cube *>(),
      py::arg("label"),
      py::arg("conf_path"),
      py::arg("units") = "DN",
      py::arg("cube") = nullptr);
  bindWrapperSurface(gainUnitConversion, "GainUnitConversion");

  // HiLab — HiRise cube label accessor for MRO instrument metadata.
  // Added: 2026-04-10
  py::class_<Isis::HiLab>(m, "HiLab")
      .def(py::init<Isis::Cube *>(),
           py::arg("cube"),
           py::keep_alive<1, 2>(),
           "Construct a HiLab from an open HiRise Cube.\n\n"
           "The cube must have an Instrument group with CpmmNumber, ChannelNumber,\n"
           "Summing, and Tdi keywords (standard HiRise labels).\n\n"
           "Parameters\n"
           "----------\n"
           "cube : Cube\n"
           "    Open HiRise cube with valid Instrument group labels.\n\n"
           "Raises\n"
           "------\n"
           "IException\n"
           "    If required keywords (Summing, Tdi) are missing from the label.")
      .def("get_cpmm_number", &Isis::HiLab::getCpmmNumber,
           "Return the CpmmNumber keyword value from the cube labels.")
      .def("get_channel", &Isis::HiLab::getChannel,
           "Return the ChannelNumber keyword value from the cube labels.")
      .def("get_bin", &Isis::HiLab::getBin,
           "Return the Summing (bin) keyword value from the cube labels.")
      .def("get_tdi", &Isis::HiLab::getTdi,
           "Return the Tdi keyword value from the cube labels.")
      .def("get_ccd", &Isis::HiLab::getCcd,
           "Return the CCD number derived from the cpmm-to-ccd lookup table.")
      .def("__repr__", [](Isis::HiLab &h) {
        return "<HiLab cpmm=" + std::to_string(h.getCpmmNumber())
               + " channel=" + std::to_string(h.getChannel())
               + " bin=" + std::to_string(h.getBin())
               + " tdi=" + std::to_string(h.getTdi()) + ">";
      });
}
