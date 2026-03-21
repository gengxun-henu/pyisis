#ifndef ISIS_PYBIND_HELPERS_H
#define ISIS_PYBIND_HELPERS_H

#include <string>

#include <QString>

inline std::string qStringToStdString(const QString &value) {
  return value.toStdString();
}

inline QString stdStringToQString(const std::string &value) {
  return QString::fromStdString(value);
}

#endif
