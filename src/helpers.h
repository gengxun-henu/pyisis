// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-26  Geng Xun consolidated shared QString and QVector conversion helpers used across pybind binding sources
// Purpose: shared helper utilities for QString/std::string and QVector/std::vector conversions used by pybind11 binding code

#ifndef ISIS_PYBIND_HELPERS_H
#define ISIS_PYBIND_HELPERS_H

#include <string>
#include <vector>
#include <stdexcept>

#include <QString>
#include <QVector>

// QString/std::string conversion with validation
inline std::string qStringToStdString(const QString &value) {
  // QString::toStdString() can throw if the string contains invalid unicode
  try {
    return value.toStdString();
  } catch (const std::exception &e) {
    throw std::runtime_error("Failed to convert QString to std::string: " +
                           std::string(e.what()));
  }
}

inline QString stdStringToQString(const std::string &value) {
  // QString::fromStdString() is generally safe, but validate non-empty result
  QString result = QString::fromStdString(value);
  // If input was valid but result is null (shouldn't happen), throw
  if (!value.empty() && result.isNull()) {
    throw std::runtime_error("Failed to convert std::string to QString");
  }
  return result;
}

// QVector/std::vector conversion utilities (consolidated from multiple files)
template<typename T>
inline std::vector<T> qVectorToStdVector(const QVector<T> &qvec) {
  return std::vector<T>(qvec.begin(), qvec.end());
}

template<typename T>
inline QVector<T> stdVectorToQVector(const std::vector<T> &vec) {
  return QVector<T>(vec.begin(), vec.end());
}

// Specialized vector<QString> to vector<string> conversion
inline std::vector<std::string> qStringVectorToStdVector(const std::vector<QString> &values) {
  std::vector<std::string> result;
  result.reserve(values.size());
  for (const QString &value : values) {
    result.push_back(qStringToStdString(value));
  }
  return result;
}

// Specialized vector<string> to vector<QString> conversion
inline std::vector<QString> stdVectorToQStringVector(const std::vector<std::string> &values) {
  std::vector<QString> result;
  result.reserve(values.size());
  for (const std::string &value : values) {
    result.push_back(stdStringToQString(value));
  }
  return result;
}

#endif
