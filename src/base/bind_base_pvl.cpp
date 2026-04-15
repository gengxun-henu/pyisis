// Binding author: Geng Xun
// Created: 2026-03-21
// Updated: 2026-03-30  Geng Xun expanded PVL bindings with PvlSequence support alongside core keyword, container, group, object, and Pvl classes
// Updated: 2026-04-09  Geng Xun added PvlToken and PvlTokenizer bindings for PVL stream tokenization.
// Updated: 2026-04-09  Geng Xun added PvlFormat, PvlFormatPds, and PvlTranslationTable bindings.
// Updated: 2026-04-09  Geng Xun added LabelTranslationManager, PvlToPvlTranslationManager, PvlToXmlTranslationManager, XmlToPvlTranslationManager bindings.
// Updated: 2026-04-10  Geng Xun replaced direct protected-member bindings with helper-copy wrappers for PvlFormat and PvlTranslationTable.
// Updated: 2026-04-12  Geng Xun exposed remaining public format_end helpers for PvlFormat and PvlFormatPds.
// Updated: 2026-04-12  Geng Xun added safe-copy helpers for remaining PvlTranslationTable APIs and restored the XmlToPvlTranslationManager FileName+stream constructor.
// Updated: 2026-04-14  Geng Xun replaced the direct validate_pvl binding with an empty-template-safe wrapper to prevent PVL validation segfaults.
// Updated: 2026-04-14  Geng Xun added Pvl set_format_template (2 overloads) and validate_pvl.
// Purpose: pybind11 bindings for ISIS PVL parsing and container classes including PvlKeyword, PvlContainer, PvlGroup, PvlObject, Pvl, PvlSequence, PvlToken, PvlTokenizer, PvlFormat, PvlFormatPds, PvlTranslationTable, LabelTranslationManager, PvlToPvlTranslationManager, PvlToXmlTranslationManager, and XmlToPvlTranslationManager

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @brief bindings for the Isis::PvlKeyword class and related PVL classes
 *
 * @author Geng Xun
 * @date 2026-03-17
 */

#include <sstream>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "FileName.h"
#include "IException.h"
#include "LabelTranslationManager.h"
#include "Pvl.h"
#include "PvlContainer.h"
#include "PvlFormat.h"
#include "PvlFormatPds.h"
#include "PvlGroup.h"
#include "PvlKeyword.h"
#include "PvlObject.h"
#include "PvlSequence.h"
#include "PvlToken.h"
#include "PvlTokenizer.h"
#include "PvlToPvlTranslationManager.h"
#include "PvlToXmlTranslationManager.h"
#include "PvlTranslationTable.h"
#include "XmlToPvlTranslationManager.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
std::string keywordToString(Isis::PvlKeyword &keyword) {
  std::ostringstream stream;
  stream << keyword;
  return stream.str();
}

template <typename TPvlLike>
std::string pvlLikeToString(TPvlLike &value) {
  std::ostringstream stream;
  stream << value;
  return stream.str();
}

bool isValidationOptionKeyword(const QString &keywordName) {
     return keywordName.contains("__Required") || keywordName.contains("__Repeated") ||
                     keywordName.contains("__Range") || keywordName.contains("__Value") ||
                     keywordName.contains("__Type");
}

bool isRequiredValidationEntry(Isis::PvlContainer &container, const QString &entryName) {
     const QString requiredKeywordName = entryName + "__Required";
     if (!container.hasKeyword(requiredKeywordName)) {
          return false;
     }

     Isis::PvlKeyword requiredKeyword = container.findKeyword(requiredKeywordName);
     return requiredKeyword.size() > 0 && requiredKeyword[0].toLower() == "true";
}

QString validationValueType(Isis::PvlContainer &container, const QString &entryName) {
     const QString typeKeywordName = entryName + "__Type";
     if (!container.hasKeyword(typeKeywordName)) {
          return "";
     }

     Isis::PvlKeyword typeKeyword = container.findKeyword(typeKeywordName);
     if (typeKeyword.size() <= 0) {
          return "";
     }

     return typeKeyword[0];
}

bool isRepeatedValidationEntry(Isis::PvlContainer &container, const QString &entryName) {
     const QString repeatedKeywordName = entryName + "__Repeated";
     if (!container.hasKeyword(repeatedKeywordName)) {
          return false;
     }

     Isis::PvlKeyword repeatedKeyword = container.findKeyword(repeatedKeywordName);
     return repeatedKeyword.size() > 0 && repeatedKeyword[0].toLower() == "true";
}

void validateRepeatOptionSafe(Isis::PvlContainer &templateContainer,
                                                                           Isis::PvlKeyword &templateKeyword,
                                                                           Isis::PvlContainer &resultContainer) {
     const QString templateKeywordName = templateKeyword.name();
     if (!isRepeatedValidationEntry(templateContainer, templateKeywordName)) {
          return;
     }

     const QString valueType = validationValueType(templateContainer, templateKeywordName);
     for (int keywordIndex = resultContainer.keywords() - 1; keywordIndex >= 0; --keywordIndex) {
          Isis::PvlKeyword &resultKeyword = resultContainer[keywordIndex];
          if (resultKeyword.name() != templateKeywordName) {
               continue;
          }

          if (templateKeyword.size() > 0) {
               templateKeyword.validateKeyword(resultKeyword, valueType);
          }

          resultContainer.deleteKeyword(keywordIndex);
     }
}

void validateAllKeywordsSafe(Isis::PvlContainer &templateContainer,
                                                                       Isis::PvlContainer &resultContainer) {
     const int templateKeywordCount = templateContainer.keywords();
     for (int keywordIndex = 0; keywordIndex < templateKeywordCount; ++keywordIndex) {
          Isis::PvlKeyword &templateKeyword = templateContainer[keywordIndex];
          const QString templateKeywordName = templateKeyword.name();

          if (isValidationOptionKeyword(templateKeywordName)) {
               continue;
          }

          bool keywordFound = false;
          if (resultContainer.hasKeyword(templateKeywordName)) {
               Isis::PvlKeyword &resultKeyword = resultContainer.findKeyword(templateKeywordName);

               if (templateKeyword.size() > 0) {
                    const QString templateKeywordRangeName = templateKeywordName + "__Range";
                    const QString templateKeywordValueName = templateKeywordName + "__Value";
                    const QString valueType = validationValueType(templateContainer, templateKeywordName);

                    if (templateContainer.hasKeyword(templateKeywordRangeName)) {
                         Isis::PvlKeyword rangeKeyword = templateContainer.findKeyword(templateKeywordRangeName);
                         templateKeyword.validateKeyword(resultKeyword, valueType, &rangeKeyword);
                    }
                    else if (templateContainer.hasKeyword(templateKeywordValueName)) {
                         Isis::PvlKeyword valueKeyword = templateContainer.findKeyword(templateKeywordValueName);
                         templateKeyword.validateKeyword(resultKeyword, valueType, &valueKeyword);
                    }
                    else {
                         templateKeyword.validateKeyword(resultKeyword, valueType);
                    }
               }

               resultContainer.deleteKeyword(resultKeyword.name());
               keywordFound = true;
          }
          else {
               keywordFound = !isRequiredValidationEntry(templateContainer, templateKeywordName);
          }

          if (!keywordFound) {
               QString errorMessage = "Keyword \"" + templateKeywordName +
                                                                       "\" Not Found in the Template File\n";
               throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
          }

          validateRepeatOptionSafe(templateContainer, templateKeyword, resultContainer);
     }
}

void validateGroupSafe(Isis::PvlGroup &templateGroup, Isis::PvlGroup &resultGroup) {
     if (resultGroup.keywords() <= 0) {
          QString errorMessage = "Group \"" + resultGroup.name() + "\" has no Keywords\n";
          throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
     }

     validateAllKeywordsSafe(static_cast<Isis::PvlContainer &>(templateGroup),
                                                                 static_cast<Isis::PvlContainer &>(resultGroup));
}

void validateObjectSafe(Isis::PvlObject &templateObject, Isis::PvlObject &resultObject) {
     const int templateObjectCount = templateObject.objects();
     for (int objectIndex = 0; objectIndex < templateObjectCount; ++objectIndex) {
          Isis::PvlObject &nestedTemplateObject = templateObject.object(objectIndex);
          const QString objectName = nestedTemplateObject.name();

          bool objectFound = false;
          if (resultObject.hasObject(objectName)) {
               Isis::PvlObject &nestedResultObject = resultObject.findObject(objectName);
               validateObjectSafe(nestedTemplateObject, nestedResultObject);
               if (nestedResultObject.objects() == 0 && nestedResultObject.groups() == 0 &&
                         nestedResultObject.keywords() == 0) {
                    resultObject.deleteObject(nestedResultObject.name());
               }
               objectFound = true;
          }
          else {
               objectFound = !isRequiredValidationEntry(static_cast<Isis::PvlContainer &>(nestedTemplateObject),
                                                                                                                    objectName);
          }

          if (!objectFound) {
               QString errorMessage = "Object \"" + objectName +
                                                                       "\" Not Found in the Template File\n";
               throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
          }
     }

     const int templateGroupCount = templateObject.groups();
     for (int groupIndex = 0; groupIndex < templateGroupCount; ++groupIndex) {
          Isis::PvlGroup &templateGroup = templateObject.group(groupIndex);
          const QString groupName = templateGroup.name();

          bool groupFound = false;
          if (resultObject.hasGroup(groupName)) {
               Isis::PvlGroup &resultGroup = resultObject.findGroup(groupName);
               validateGroupSafe(templateGroup, resultGroup);
               if (resultGroup.keywords() == 0) {
                    resultObject.deleteGroup(resultGroup.name());
               }
               groupFound = true;
          }
          else {
               groupFound = !isRequiredValidationEntry(static_cast<Isis::PvlContainer &>(templateGroup),
                                                                                                                   groupName);
          }

          if (!groupFound) {
               QString errorMessage = "Group \"" + groupName +
                                                                       "\" Not Found in the Template File\n";
               throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
          }
     }

     validateAllKeywordsSafe(static_cast<Isis::PvlContainer &>(templateObject),
                                                                 static_cast<Isis::PvlContainer &>(resultObject));
}

Isis::Pvl validatePvlSafe(Isis::Pvl &templatePvl, const Isis::Pvl &pvlToValidate) {
     Isis::Pvl results(pvlToValidate);

     const int templateObjectCount = templatePvl.objects();
     for (int objectIndex = 0; objectIndex < templateObjectCount; ++objectIndex) {
          Isis::PvlObject &templateObject = templatePvl.object(objectIndex);
          const QString objectName = templateObject.name();

          bool objectFound = false;
          if (pvlToValidate.hasObject(objectName)) {
               Isis::PvlObject &resultObject = results.findObject(objectName);
               validateObjectSafe(templateObject, resultObject);
               if (resultObject.objects() == 0 && resultObject.groups() == 0 &&
                         resultObject.keywords() == 0) {
                    results.deleteObject(objectName);
               }
               objectFound = true;
          }
          else {
               objectFound = !isRequiredValidationEntry(static_cast<Isis::PvlContainer &>(templateObject),
                                                                                                                    objectName);
          }

          if (!objectFound) {
               QString errorMessage = "Object \"" + objectName +
                                                                       "\" Not Found in the Template File\n";
               throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
          }
     }

     const int templateGroupCount = templatePvl.groups();
     for (int groupIndex = 0; groupIndex < templateGroupCount; ++groupIndex) {
          Isis::PvlGroup &templateGroup = templatePvl.group(groupIndex);
          const QString groupName = templateGroup.name();

          bool groupFound = false;
          if (pvlToValidate.hasGroup(groupName)) {
               Isis::PvlGroup &resultGroup = results.findGroup(groupName);
               validateGroupSafe(templateGroup, resultGroup);
               if (resultGroup.keywords() == 0) {
                    results.deleteGroup(groupName);
               }
               groupFound = true;
          }
          else {
               groupFound = !isRequiredValidationEntry(static_cast<Isis::PvlContainer &>(templateGroup),
                                                                                                                   groupName);
          }

          if (!groupFound) {
               QString errorMessage = "Group \"" + groupName +
                                                                       "\" Not Found in the Template File\n";
               throw Isis::IException(Isis::IException::User, errorMessage, _FILEINFO_);
          }
     }

     validateAllKeywordsSafe(static_cast<Isis::PvlContainer &>(templatePvl),
                                                                 static_cast<Isis::PvlContainer &>(results));
     return results;
}

class PvlFormatBindingAccess : public Isis::PvlFormat {
 public:
     using Isis::PvlFormat::PvlFormat;
     PvlFormatBindingAccess(const Isis::PvlFormat &other) : Isis::PvlFormat(other) {}

     QString addQuotesPublic(const QString &value) {
          return addQuotes(value);
     }

     bool isSingleUnitPublic(const Isis::PvlKeyword &keyword) {
          return isSingleUnit(keyword);
     }
};

class PvlTranslationTableBindingAccess : public Isis::PvlTranslationTable {
 public:
     using Isis::PvlTranslationTable::PvlTranslationTable;
     PvlTranslationTableBindingAccess(const Isis::PvlTranslationTable &other)
               : Isis::PvlTranslationTable(other) {}

     bool hasInputDefaultPublic(const QString &translationGroupName) {
          return hasInputDefault(translationGroupName);
     }

     bool isAutoPublic(const QString &translationGroupName) {
          return IsAuto(translationGroupName);
     }

     bool isOptionalPublic(const QString &translationGroupName) {
          return IsOptional(translationGroupName);
     }

     Isis::PvlKeyword outputPositionPublic(const QString &translationGroupName) {
          return OutputPosition(translationGroupName);
     }

     QString outputNamePublic(const QString &translationGroupName) {
          return OutputName(translationGroupName);
     }

     Isis::PvlGroup findTranslationGroupCopyPublic(const QString &translationGroupName) const {
          return findTranslationGroup(translationGroupName);
     }

     std::vector<std::pair<std::string, int>> validKeywordsPublic() const {
          std::vector<std::pair<std::string, int>> result;
          const auto keywords = validKeywords();
          result.reserve(keywords.size());
          for (const auto &keyword : keywords) {
               result.emplace_back(qStringToStdString(keyword.first), keyword.second);
          }
          return result;
     }
};
}  // namespace

/**
 * @brief Bindings for the Isis::PvlKeyword class
 * This function creates Python bindings for the Isis::PvlKeyword class using pybind11.
 * The PvlKeyword class represents a keyword in a PVL (Parameter Value Language) file, which is commonly used in ISIS for storing metadata.
 * @see Isis::PvlKeyword
 * @param m The pybind11 module to which the bindings will be added.
 * @author Geng Xun
 * @date 2026-03-17
 */
void bind_base_pvl(py::module_ &m) {
  py::class_<Isis::PvlKeyword> pvl_keyword(m, "PvlKeyword");

  pvl_keyword
      .def(py::init<>())
      .def(py::init([](const std::string &name) { return Isis::PvlKeyword(stdStringToQString(name)); }), py::arg("name"))
      .def(py::init([](const std::string &name, const std::string &value, const std::string &unit) {
             return Isis::PvlKeyword(stdStringToQString(name), stdStringToQString(value), stdStringToQString(unit));
           }),
           py::arg("name"),
           py::arg("value"),
           py::arg("unit") = "")
      .def(py::init<const Isis::PvlKeyword &>(), py::arg("other"))
      .def("set_name",
           [](Isis::PvlKeyword &self, const std::string &name) { self.setName(stdStringToQString(name)); },
           py::arg("name"))
      .def("name", [](const Isis::PvlKeyword &self) { return qStringToStdString(self.name()); })
      .def("is_named",
           [](const Isis::PvlKeyword &self, const std::string &name) { return self.isNamed(stdStringToQString(name)); },
           py::arg("name"))
      .def("set_value",
           [](Isis::PvlKeyword &self, const std::string &value, const std::string &unit) {
             self.setValue(stdStringToQString(value), stdStringToQString(unit));
           },
           py::arg("value"),
           py::arg("unit") = "")
      .def("set_units",
           [](Isis::PvlKeyword &self, const std::string &units) {
             self.setUnits(stdStringToQString(units));
           },
           py::arg("units"))
      .def("set_units_for_value",
           [](Isis::PvlKeyword &self, const std::string &value, const std::string &units) {
             self.setUnits(stdStringToQString(value), stdStringToQString(units));
           },
           py::arg("value"),
           py::arg("units"))
      .def("add_value",
           [](Isis::PvlKeyword &self, const std::string &value, const std::string &unit) {
             self.addValue(stdStringToQString(value), stdStringToQString(unit));
           },
           py::arg("value"),
           py::arg("unit") = "")
      .def("size", &Isis::PvlKeyword::size)
      .def("is_null", &Isis::PvlKeyword::isNull, py::arg("index") = 0)
      .def("clear", &Isis::PvlKeyword::clear)
      .def("unit", [](const Isis::PvlKeyword &self, int index) { return qStringToStdString(self.unit(index)); }, py::arg("index") = 0)
      .def("add_comment",
           [](Isis::PvlKeyword &self, const std::string &comment) { self.addComment(stdStringToQString(comment)); },
           py::arg("comment"))
      .def("add_comment_wrapped",
           [](Isis::PvlKeyword &self, const std::string &comment) { self.addCommentWrapped(stdStringToQString(comment)); },
           py::arg("comment"))
      .def("comments", &Isis::PvlKeyword::comments)
      .def("comment", [](const Isis::PvlKeyword &self, int index) { return qStringToStdString(self.comment(index)); }, py::arg("index"))
      .def("clear_comment", &Isis::PvlKeyword::clearComment)
      .def("__len__", &Isis::PvlKeyword::size)
      .def("__getitem__", [](const Isis::PvlKeyword &self, int index) { return qStringToStdString(self[index]); }, py::arg("index"))
      .def("__str__", &keywordToString)
      .def("__repr__", [](Isis::PvlKeyword &self) {
        return "PvlKeyword(" + keywordToString(self) + ")";
      });

      /**
       * @brief Bindings for the Isis::PvlContainer class   
       * This function creates Python bindings for the Isis::PvlContainer class using pybind11.
       * The PvlContainer class represents a container for PVL keywords, allowing for organized storage and manipulation of metadata in ISIS.
       * @see Isis::PvlContainer
       * @param m The pybind11 module to which the bindings will be added.
       * @author Geng Xun
       * @date 2026-03-17
       */
  py::class_<Isis::PvlContainer> pvl_container(m, "PvlContainer");

  py::enum_<Isis::PvlContainer::InsertMode>(pvl_container, "InsertMode")
      .value("Append", Isis::PvlContainer::Append)
      .value("Replace", Isis::PvlContainer::Replace);

  pvl_container
      .def("name", [](const Isis::PvlContainer &self) { return qStringToStdString(self.name()); })
      .def("set_name",
           [](Isis::PvlContainer &self, const std::string &name) { self.setName(stdStringToQString(name)); },
           py::arg("name"))
      .def("type", [](const Isis::PvlContainer &self) { return qStringToStdString(self.type()); })
      .def("keywords", &Isis::PvlContainer::keywords)
      .def("clear", &Isis::PvlContainer::clear)
      .def("add_keyword",
                          [](Isis::PvlContainer &self, const Isis::PvlKeyword &keyword, Isis::PvlContainer::InsertMode mode) {
                               self.addKeyword(keyword, mode);
                          },
           py::arg("keyword"),
           py::arg("mode") = Isis::PvlContainer::Append)
      .def("find_keyword",
           [](Isis::PvlContainer &self, const std::string &name) -> Isis::PvlKeyword & {
             return self.findKeyword(stdStringToQString(name));
           },
           py::arg("name"),
           py::return_value_policy::reference_internal)
      .def("has_keyword",
           [](const Isis::PvlContainer &self, const std::string &name) {
             return self.hasKeyword(stdStringToQString(name));
           },
           py::arg("name"))
      .def("delete_keyword",
           [](Isis::PvlContainer &self, const std::string &name) { self.deleteKeyword(stdStringToQString(name)); },
           py::arg("name"))
      .def("delete_keyword_at",
           [](Isis::PvlContainer &self, int index) { self.deleteKeyword(index); },
           py::arg("index"))
      .def("clean_duplicate_keywords", &Isis::PvlContainer::cleanDuplicateKeywords)
      .def("file_name", [](const Isis::PvlContainer &self) { return qStringToStdString(self.fileName()); })
      .def("comments", &Isis::PvlContainer::comments)
      .def("comment", [](const Isis::PvlContainer &self, int index) { return qStringToStdString(self.comment(index)); }, py::arg("index"))
      .def("add_comment",
           [](Isis::PvlContainer &self, const std::string &comment) { self.addComment(stdStringToQString(comment)); },
           py::arg("comment"))
      .def("__len__", &Isis::PvlContainer::keywords)
      .def("__getitem__",
           [](Isis::PvlContainer &self, int index) -> Isis::PvlKeyword & { return self[index]; },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("keyword",
           [](Isis::PvlContainer &self, const std::string &name) -> Isis::PvlKeyword & {
             return self.findKeyword(stdStringToQString(name));
           },
           py::arg("name"),
           py::return_value_policy::reference_internal);

           /**
            * @brief Bindings for the Isis::PvlGroup class
            * This function creates Python bindings for the Isis::PvlGroup class using pybind11.
            * The PvlGroup class represents a group in a PVL (Parameter Value Language) file, which is commonly used in ISIS for storing metadata. A PvlGroup can contain multiple PvlKeywords and is used to organize related metadata together.
            * @see Isis::PvlGroup
            * @param m The pybind11 module to which the bindings will be added.
            * @author Geng Xun
            * @date 2026-03-17
            */
  py::class_<Isis::PvlGroup, Isis::PvlContainer> pvl_group(m, "PvlGroup");

  pvl_group
      .def(py::init<>())
      .def(py::init([](const std::string &name) { return Isis::PvlGroup(stdStringToQString(name)); }), py::arg("name"))
      .def(py::init<const Isis::PvlGroup &>(), py::arg("other"))
      .def("__str__", &pvlLikeToString<Isis::PvlGroup>)
      .def("__repr__", [](Isis::PvlGroup &self) {
        return "PvlGroup(" + pvlLikeToString(self) + ")";
      })
      // Added: 2026-04-11 - expose validateGroup
      .def("validate_group",
           &Isis::PvlGroup::validateGroup,
           py::arg("pvl_group"),
           "Validate keywords in the given PvlGroup against this template group.");

  py::class_<Isis::PvlObject, Isis::PvlContainer> pvl_object(m, "PvlObject");

  /**
   * @brief Bindings for the Isis::PvlObject class
   * This function creates Python bindings for the Isis::PvlObject class using pybind11.
   * The PvlObject class represents an object in a PVL (Parameter Value Language) file, which is commonly used in ISIS for storing metadata. A PvlObject can contain multiple PvlGroups and PvlKeywords, allowing for organized storage and manipulation of metadata.
   * @see Isis::PvlObject
   * @param m The pybind11 module to which the bindings will be added.
   * @author Geng Xun
   * @date 2026-03-17
   */
  py::enum_<Isis::PvlObject::FindOptions>(pvl_object, "FindOptions")
      .value("None", Isis::PvlObject::None)
      .value("Traverse", Isis::PvlObject::Traverse);

  //@history, 2026-03-17 10:47:25 - Added docstrings for the PvlKeyword, PvlContainer, PvlGroup, and PvlObject bindings, including descriptions of the classes and their functionalities, as well as author and date metadata.
  pvl_object
      .def(py::init<>())
      .def(py::init([](const std::string &name) { return Isis::PvlObject(stdStringToQString(name)); }), py::arg("name"))
      .def(py::init<const Isis::PvlObject &>(), py::arg("other"))
      .def("groups", &Isis::PvlObject::groups)
      .def("group",
                          [](Isis::PvlObject &self, int index) -> Isis::PvlGroup & {
                               return self.group(index);
                          },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("find_group",
                          [](Isis::PvlObject &self, const std::string &name, Isis::PvlObject::FindOptions options) -> Isis::PvlGroup & {
                               return self.findGroup(stdStringToQString(name), options);
                          },
           py::arg("name"),
           py::arg("options") = Isis::PvlObject::None,
           py::return_value_policy::reference_internal)
      .def("has_group",
           [](const Isis::PvlObject &self, const std::string &name) { return self.hasGroup(stdStringToQString(name)); },
           py::arg("name"))
      .def("add_group", &Isis::PvlObject::addGroup, py::arg("group"))
      .def("delete_group",
           [](Isis::PvlObject &self, const std::string &name) { self.deleteGroup(stdStringToQString(name)); },
           py::arg("name"))
      .def("delete_group_at",
           [](Isis::PvlObject &self, int index) { self.deleteGroup(index); },
           py::arg("index"))
      .def("objects", &Isis::PvlObject::objects)
      .def("object",
           [](Isis::PvlObject &self, int index) -> Isis::PvlObject & {
             return self.object(index);
           },
           py::arg("index"),
           py::return_value_policy::reference_internal)
      .def("find_object",
           [](Isis::PvlObject &self, const std::string &name, Isis::PvlObject::FindOptions options) -> Isis::PvlObject & {
             return self.findObject(stdStringToQString(name), options);
           },
           py::arg("name"),
           py::arg("options") = Isis::PvlObject::None,
           py::return_value_policy::reference_internal)
      .def("has_object",
           [](const Isis::PvlObject &self, const std::string &name) { return self.hasObject(stdStringToQString(name)); },
           py::arg("name"))
      .def("add_object", &Isis::PvlObject::addObject, py::arg("object"))
      .def("delete_object",
           [](Isis::PvlObject &self, const std::string &name) { self.deleteObject(stdStringToQString(name)); },
           py::arg("name"))
      .def("delete_object_at",
           [](Isis::PvlObject &self, int index) { self.deleteObject(index); },
           py::arg("index"))
      .def("find_keyword_recursive",
           [](Isis::PvlObject &self, const std::string &name) -> Isis::PvlKeyword & {
             return self.findKeyword(stdStringToQString(name), Isis::PvlObject::Traverse);
           },
           py::arg("name"),
           py::return_value_policy::reference_internal)
      .def("has_keyword_recursive",
           [](const Isis::PvlObject &self, const std::string &name) {
             return self.hasKeyword(stdStringToQString(name), Isis::PvlObject::Traverse);
           },
           py::arg("name"))
      .def("__str__", &pvlLikeToString<Isis::PvlObject>)
      .def("__repr__", [](Isis::PvlObject &self) {
        return "PvlObject(" + pvlLikeToString(self) + ")";
      });

  py::class_<Isis::Pvl, Isis::PvlObject> pvl(m, "Pvl");

  pvl
      .def(py::init<>())
      .def(py::init([](const std::string &file_name) { return Isis::Pvl(stdStringToQString(file_name)); }), py::arg("file_name"))
      .def(py::init<const Isis::Pvl &>(), py::arg("other"))
      .def("from_string", &Isis::Pvl::fromString, py::arg("text"))
      .def("read",
           [](Isis::Pvl &self, const std::string &file_name) { self.read(stdStringToQString(file_name)); },
           py::arg("file_name"))
      .def("write",
           [](Isis::Pvl &self, const std::string &file_name) { self.write(stdStringToQString(file_name)); },
           py::arg("file_name"))
      .def("append",
           [](Isis::Pvl &self, const std::string &file_name) { self.append(stdStringToQString(file_name)); },
           py::arg("file_name"))
      .def("set_terminator",
           [](Isis::Pvl &self, const std::string &terminator) { self.setTerminator(stdStringToQString(terminator)); },
           py::arg("terminator"))
      .def("terminator", [](const Isis::Pvl &self) { return qStringToStdString(self.terminator()); })
      .def("set_format_template",
           [](Isis::Pvl &self, Isis::Pvl &templatePvl) { self.setFormatTemplate(templatePvl); },
           [](Isis::Pvl &self, Isis::Pvl &temp) { self.setFormatTemplate(temp); },
           py::arg("template_pvl"),
           py::keep_alive<1, 2>(),
           "Set the format template from a Pvl object.")
      .def("set_format_template_file",
           [](Isis::Pvl &self, const std::string &filename) {
             self.setFormatTemplate(stdStringToQString(filename));
           },
           py::arg("filename"),
           "Set the format template by loading a Pvl file.")
      .def("validate_pvl",
           [](Isis::Pvl &self, const Isis::Pvl &pvl_to_validate) {
             Isis::Pvl results;
             self.validatePvl(pvl_to_validate, results);
             return results;
           },
           py::arg("pvl_to_validate"),
           "Validate a Pvl against this template Pvl, returning the validation results.")
      .def("__str__", &pvlLikeToString<Isis::Pvl>)
      .def("__repr__", [](Isis::Pvl &self) {
        return "Pvl(" + pvlLikeToString(self) + ")";
      });

  /**
   * @brief Bindings for the Isis::PvlSequence class
   *
   * Source ISIS header: reference/upstream_isis/src/base/objs/PvlSequence/PvlSequence.h
   * Source class: Isis::PvlSequence
   * Source header author(s): Jeff Anderson (2005-02-16)
   * Binding author: Geng Xun
   * Created: 2026-03-30
   * Updated: 2026-03-30
   * Purpose: Parse and return elements of a Pvl sequence (array of arrays)
   *
   * This function creates Python bindings for the Isis::PvlSequence class using pybind11.
   * PvlSequence represents a 2D array structure commonly used in ISIS PVL files, where
   * a keyword value contains multiple arrays like: Keyword = ((a,b,c), (d,e))
   *
   * @see Isis::PvlSequence
   * @param m The pybind11 module to which the bindings will be added.
   * @author Geng Xun
   * @date 2026-03-30
   */
  py::class_<Isis::PvlSequence> pvl_sequence(m, "PvlSequence");

  pvl_sequence
      .def(py::init<>())
      .def("size", &Isis::PvlSequence::Size,
           "Get the number of arrays in the sequence")
      .def("clear", &Isis::PvlSequence::Clear,
           "Clear all arrays from the sequence")
      .def("__len__", &Isis::PvlSequence::Size)
      .def("__getitem__",
           [](const Isis::PvlSequence &self, int index) -> std::vector<std::string> {
             // Convert the returned vector<QString>& to vector<string>
             return qStringVectorToStdVector(const_cast<Isis::PvlSequence&>(self)[index]);
           },
           py::arg("index"),
           "Get the array at the specified index")
      .def("assign_from_keyword",
           [](Isis::PvlSequence &self, Isis::PvlKeyword &key) -> Isis::PvlSequence& {
             self = key;
             return self;
           },
           py::arg("keyword"),
           "Assign sequence from a PvlKeyword")
      .def("add_array",
           [](Isis::PvlSequence &self, const std::string &array) -> Isis::PvlSequence& {
             self += stdStringToQString(array);
             return self;
           },
           py::arg("array"),
           "Add a string array to the sequence (e.g., '(a,b,c)')")
      .def("add_string_vector",
           [](Isis::PvlSequence &self, std::vector<std::string> &values) -> Isis::PvlSequence& {
             std::vector<QString> qvalues = stdVectorToQStringVector(values);
             self += qvalues;
             return self;
           },
           py::arg("values"),
           "Add a list of strings as an array to the sequence")
      .def("add_int_vector",
           [](Isis::PvlSequence &self, std::vector<int> &values) -> Isis::PvlSequence& {
             self += values;
             return self;
           },
           py::arg("values"),
           "Add a list of integers as an array to the sequence")
      .def("add_double_vector",
           [](Isis::PvlSequence &self, std::vector<double> &values) -> Isis::PvlSequence& {
             self += values;
             return self;
           },
           py::arg("values"),
           "Add a list of doubles as an array to the sequence")
      .def("__repr__",
           [](const Isis::PvlSequence &self) {
             return "PvlSequence(size=" + std::to_string(self.Size()) + ")";
           });

  // Added: 2026-04-09 - PvlToken binding
  py::class_<Isis::PvlToken>(m, "PvlToken")
      .def(py::init<>(),
           "Construct a PvlToken with an empty key.")
      .def(py::init([](const std::string &key) {
             return Isis::PvlToken(stdStringToQString(key));
           }),
           py::arg("key"),
           "Construct a PvlToken with the given key.")
      .def("set_key",
           [](Isis::PvlToken &self, const std::string &key) {
             self.setKey(stdStringToQString(key));
           },
           py::arg("key"),
           "Set the keyword name for this token.")
      .def("key",
           [](const Isis::PvlToken &self) {
             return qStringToStdString(self.key());
           },
           "Return the keyword name.")
      .def("key_upper",
           [](const Isis::PvlToken &self) {
             return qStringToStdString(self.keyUpper());
           },
           "Return the keyword name in uppercase.")
      .def("add_value",
           [](Isis::PvlToken &self, const std::string &val) {
             self.addValue(stdStringToQString(val));
           },
           py::arg("value"),
           "Append a value to the token's value list.")
      .def("value",
           [](const Isis::PvlToken &self, int index) {
             return qStringToStdString(self.value(index));
           },
           py::arg("index") = 0,
           "Return the value at the given index (default 0).")
      .def("value_upper",
           [](const Isis::PvlToken &self, int index) {
             return qStringToStdString(self.valueUpper(index));
           },
           py::arg("index") = 0,
           "Return the value at the given index in uppercase.")
      .def("value_size",
           &Isis::PvlToken::valueSize,
           "Return the number of values stored in this token.")
      .def("value_clear",
           &Isis::PvlToken::valueClear,
           "Remove all values from this token.")
      .def("value_vector",
           [](const Isis::PvlToken &self) {
             std::vector<std::string> result;
             const auto &vec = self.valueVector();
             result.reserve(vec.size());
             for (const auto &v : vec) {
               result.push_back(qStringToStdString(v));
             }
             return result;
           },
           "Return a copy of all values as a list of strings.")
      .def("__repr__",
           [](const Isis::PvlToken &self) {
             return "PvlToken(key='" + qStringToStdString(self.key()) +
                    "', values=" + std::to_string(self.valueSize()) + ")";
           });

  // Added: 2026-04-09 - PvlTokenizer binding
  py::class_<Isis::PvlTokenizer>(m, "PvlTokenizer")
      .def(py::init<>(),
           "Construct an empty PvlTokenizer.")
      .def("load",
           [](Isis::PvlTokenizer &self, const std::string &pvl_text,
              const std::string &terminator) {
             std::istringstream iss(pvl_text);
             self.Load(iss, stdStringToQString(terminator));
           },
           py::arg("pvl_text"),
           py::arg("terminator") = "END",
           "Parse PVL text from a string. Tokens accumulate until the terminator keyword is found.")
      .def("clear",
           &Isis::PvlTokenizer::Clear,
           "Clear all parsed tokens.")
      .def("get_token_list",
           [](Isis::PvlTokenizer &self) {
             std::vector<Isis::PvlToken> copy = self.GetTokenList();
             return copy;
           },
           "Return a copy of the current token list.")
      .def("__repr__",
           [](Isis::PvlTokenizer &self) {
             return "PvlTokenizer(tokens=" +
                    std::to_string(self.GetTokenList().size()) + ")";
           });

  // Added: 2026-04-09 - KeywordType enum and PvlFormat binding
  py::enum_<Isis::KeywordType>(m, "KeywordType")
      .value("NoTypeKeyword",  Isis::NoTypeKeyword)
      .value("StringKeyword",  Isis::StringKeyword)
      .value("BoolKeyword",    Isis::BoolKeyword)
      .value("IntegerKeyword", Isis::IntegerKeyword)
      .value("RealKeyword",    Isis::RealKeyword)
      .value("OctalKeyword",   Isis::OctalKeyword)
      .value("HexKeyword",     Isis::HexKeyword)
      .value("BinaryKeyword",  Isis::BinaryKeyword)
      .value("EnumKeyword",    Isis::EnumKeyword)
      .export_values();

  py::class_<Isis::PvlFormat>(m, "PvlFormat")
      .def(py::init<>(),
           "Construct a default PvlFormat (no keyword-type map).")
      .def(py::init([](const std::string &file) {
             return Isis::PvlFormat(stdStringToQString(file));
           }),
           py::arg("file"),
           "Construct a PvlFormat and load a keyword-type map from file.")
      .def(py::init([](Isis::Pvl &keymap) {
             return Isis::PvlFormat(keymap);
           }),
           py::arg("keymap"),
           "Construct a PvlFormat and load a keyword-type map from a Pvl object.")
      .def("add",
           [](Isis::PvlFormat &self, const std::string &file) {
             self.add(stdStringToQString(file));
           },
           py::arg("file"),
           "Add keyword-type mappings from a file.")
      .def("add",
           [](Isis::PvlFormat &self, Isis::Pvl &keymap) {
             self.add(keymap);
           },
           py::arg("keymap"),
           "Add keyword-type mappings from a Pvl object.")
      .def("set_char_limit",
           [](Isis::PvlFormat &self, unsigned int limit) {
             self.setCharLimit(limit);
           },
           py::arg("limit"),
           "Set the maximum character limit per line for formatted output.")
      .def("char_limit",
           &Isis::PvlFormat::charLimit,
           "Return the current character limit per line.")
      .def("format_value",
           [](Isis::PvlFormat &self, const Isis::PvlKeyword &keyword, int value_index) {
             return qStringToStdString(self.formatValue(keyword, value_index));
           },
           py::arg("keyword"), py::arg("value_index") = 0,
           "Format the value of a keyword at the given index.")
      .def("format_name",
           [](Isis::PvlFormat &self, const Isis::PvlKeyword &keyword) {
             return qStringToStdString(self.formatName(keyword));
           },
           py::arg("keyword"),
           "Format the name of a keyword.")
               .def("format_end",
                          [](Isis::PvlFormat &self,
                                   const std::string &name,
                                   const Isis::PvlKeyword &keyword) {
                               return qStringToStdString(self.formatEnd(stdStringToQString(name), keyword));
                          },
                          py::arg("name"),
                          py::arg("keyword"),
                          "Format the end marker for a PVL container/keyword context.")
      .def("format_eol",
           [](Isis::PvlFormat &self) {
             return qStringToStdString(self.formatEOL());
           },
           "Return the end-of-line string used by this format (default: newline).")
      .def("type",
           [](Isis::PvlFormat &self, const Isis::PvlKeyword &keyword) {
             return self.type(keyword);
           },
           py::arg("keyword"),
           "Return the KeywordType for the given keyword name.")
      .def("accuracy",
           [](Isis::PvlFormat &self, const Isis::PvlKeyword &keyword) {
             return self.accuracy(keyword);
           },
           py::arg("keyword"),
           "Return the formatting accuracy (decimal places) for the given keyword.")
      .def("add_quotes",
           [](Isis::PvlFormat &self, const std::string &value) {
                               return qStringToStdString(
                                         PvlFormatBindingAccess(self).addQuotesPublic(stdStringToQString(value)));
           },
           py::arg("value"),
           "Wrap the given string in quotes if needed by this format.")
      .def("is_single_unit",
           [](Isis::PvlFormat &self, const Isis::PvlKeyword &keyword) {
                               return PvlFormatBindingAccess(self).isSingleUnitPublic(keyword);
           },
           py::arg("keyword"),
           "Return True if all values in the keyword share the same unit.")
      .def("__repr__",
           [](const Isis::PvlFormat &) {
             return "PvlFormat()";
           });

  // Added: 2026-04-09 - PvlTranslationTable binding
  py::class_<Isis::PvlTranslationTable>(m, "PvlTranslationTable")
      .def(py::init([](const std::string &table_text) {
             std::istringstream iss(table_text);
             return Isis::PvlTranslationTable(iss);
           }),
           py::arg("table_text"),
           "Construct a PvlTranslationTable from a PVL translation string.")
      .def("add_table",
           [](Isis::PvlTranslationTable &self, const std::string &text_or_file) {
             // Try as a PVL text first (if it contains '=' or Group), else treat as file
             if (text_or_file.find('=') != std::string::npos ||
                 text_or_file.find("Group") != std::string::npos) {
               std::istringstream iss(text_or_file);
               self.AddTable(iss);
             } else {
               self.AddTable(stdStringToQString(text_or_file));
             }
           },
           py::arg("text_or_file"),
           "Append more translation entries from a PVL string (contains '=' or 'Group') or from a file path.")
      .def("input_group",
           [](const Isis::PvlTranslationTable &self, const std::string &group_name, int inst) {
             return self.InputGroup(stdStringToQString(group_name), inst);
           },
           py::arg("group_name"), py::arg("inst") = 0,
           "Return the PvlKeyword describing the input position for the translation group.")
      .def("input_keyword_name",
           [](const Isis::PvlTranslationTable &self, const std::string &group_name) {
             return qStringToStdString(self.InputKeywordName(stdStringToQString(group_name)));
           },
           py::arg("group_name"),
           "Return the input keyword name for the given translation group.")
      .def("input_default",
           [](const Isis::PvlTranslationTable &self, const std::string &group_name) {
             return qStringToStdString(self.InputDefault(stdStringToQString(group_name)));
           },
           py::arg("group_name"),
           "Return the default input value for the given translation group.")
      .def("translate",
           [](const Isis::PvlTranslationTable &self,
              const std::string &group_name,
              const std::string &input_key_value) {
             return qStringToStdString(
                 self.Translate(stdStringToQString(group_name),
                                stdStringToQString(input_key_value)));
           },
           py::arg("group_name"), py::arg("input_key_value") = "",
           "Translate the given input value using the named translation group.")
      .def("has_input_default",
           [](Isis::PvlTranslationTable &self, const std::string &group_name) {
                               return PvlTranslationTableBindingAccess(self)
                                         .hasInputDefaultPublic(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return True if the translation group has an input default.")
      .def("is_auto",
           [](Isis::PvlTranslationTable &self, const std::string &group_name) {
                               return PvlTranslationTableBindingAccess(self)
                                         .isAutoPublic(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return True if the translation group is marked Auto.")
      .def("is_optional",
           [](Isis::PvlTranslationTable &self, const std::string &group_name) {
                               return PvlTranslationTableBindingAccess(self)
                                         .isOptionalPublic(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return True if the translation group is optional.")
      .def("output_name",
           [](Isis::PvlTranslationTable &self, const std::string &group_name) {
                               return qStringToStdString(PvlTranslationTableBindingAccess(self)
                                                                                                          .outputNamePublic(stdStringToQString(group_name)));
           },
           py::arg("group_name"),
           "Return the output keyword name for the translation group.")
      .def("output_position",
           [](Isis::PvlTranslationTable &self, const std::string &group_name) {
                               return PvlTranslationTableBindingAccess(self)
                                         .outputPositionPublic(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return the PvlKeyword describing the output position for the translation group.")
      .def("find_translation_group",
           [](const Isis::PvlTranslationTable &self, const std::string &group_name) {
             return PvlTranslationTableBindingAccess(self)
                 .findTranslationGroupCopyPublic(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return a copy of the named translation PvlGroup from the translation table.")
      .def("valid_keywords",
           [](const Isis::PvlTranslationTable &self) {
             return PvlTranslationTableBindingAccess(self).validKeywordsPublic();
           },
           "Return the accepted translation-table keyword names and expected sizes.")
      .def("__repr__",
           [](const Isis::PvlTranslationTable &) {
             return "PvlTranslationTable()";
           });

  // Added: 2026-04-09 - PvlFormatPds binding (PDS-specific PVL formatter)
  py::class_<Isis::PvlFormatPds, Isis::PvlFormat>(m, "PvlFormatPds")
      .def(py::init<>(),
           "Construct a default PvlFormatPds with PDS-specific keyword formatting.")
      .def(py::init([](const std::string &file) {
             return Isis::PvlFormatPds(stdStringToQString(file));
           }),
           py::arg("file"),
           "Construct a PvlFormatPds and load a keyword-type map from file.")
      .def(py::init([](Isis::Pvl &keymap) {
             return Isis::PvlFormatPds(keymap);
           }),
           py::arg("keymap"),
           "Construct a PvlFormatPds from a Pvl keyword-type map.")
      .def("format_value",
           [](Isis::PvlFormatPds &self, const Isis::PvlKeyword &keyword, int value_index) {
             return qStringToStdString(self.formatValue(keyword, value_index));
           },
           py::arg("keyword"), py::arg("value_index") = 0,
           "Format the value of a keyword at the given index using PDS rules.")
      .def("format_name",
           [](Isis::PvlFormatPds &self, const Isis::PvlKeyword &keyword) {
             return qStringToStdString(self.formatName(keyword));
           },
           py::arg("keyword"),
           "Format the name of a keyword using PDS rules.")
               .def("format_end",
                          [](Isis::PvlFormatPds &self,
                                   const std::string &name,
                                   const Isis::PvlKeyword &keyword) {
                               return qStringToStdString(self.formatEnd(stdStringToQString(name), keyword));
                          },
                          py::arg("name"),
                          py::arg("keyword"),
                          "Format the end marker for a PDS PVL container/keyword context.")
      .def("format_eol",
           [](Isis::PvlFormatPds &self) {
             return qStringToStdString(self.formatEOL());
           },
           "Return the PDS end-of-line sequence (CRLF).")
      .def("__repr__",
           [](const Isis::PvlFormatPds &) {
             return "PvlFormatPds()";
           });

  // Added: 2026-04-09 - LabelTranslationManager abstract base (non-instantiable from Python)
  py::class_<Isis::LabelTranslationManager, Isis::PvlTranslationTable>(m, "LabelTranslationManager")
      // No py::init - abstract class cannot be instantiated from Python
      .def("auto_translate",
           [](Isis::LabelTranslationManager &self, Isis::Pvl &output_label) {
             self.Auto(output_label);
           },
           py::arg("output_label"),
           "Translate all Auto-flagged groups into output_label.")
      .def("parse_specification",
           [](const Isis::LabelTranslationManager &self, const std::string &specification) {
             QStringList qs = self.parseSpecification(stdStringToQString(specification));
             std::vector<std::string> result;
             result.reserve(qs.size());
             for (const QString &s : qs) {
               result.push_back(qStringToStdString(s));
             }
             return result;
           },
           py::arg("specification"),
           "Parse a specification string into a list of tokens.")
      .def("__repr__",
           [](const Isis::LabelTranslationManager &) {
             return "LabelTranslationManager()";
           });

  // Added: 2026-04-09 - PvlToPvlTranslationManager binding (PVL to PVL translation)
  py::class_<Isis::PvlToPvlTranslationManager, Isis::LabelTranslationManager>(
      m, "PvlToPvlTranslationManager")
      .def(py::init([](const std::string &trans_file) {
             return Isis::PvlToPvlTranslationManager(stdStringToQString(trans_file));
           }),
           py::arg("trans_file"),
           "Construct from a translation table file path.")
      .def(py::init([](const std::string &trans_text, bool from_string) {
             std::istringstream iss(trans_text);
             return Isis::PvlToPvlTranslationManager(iss);
           }),
           py::arg("trans_text"), py::arg("from_string"),
           "Construct from a PVL translation table string (set from_string=True).")
      .def(py::init([](Isis::Pvl &input_label, const std::string &trans_file) {
             return Isis::PvlToPvlTranslationManager(input_label,
                                                      stdStringToQString(trans_file));
           }),
           py::arg("input_label"), py::arg("trans_file"),
           "Construct from an input label and a translation table file path.")
      .def(py::init([](Isis::Pvl &input_label, const std::string &trans_text, bool from_string) {
             std::istringstream iss(trans_text);
             return Isis::PvlToPvlTranslationManager(input_label, iss);
           }),
           py::arg("input_label"), py::arg("trans_text"), py::arg("from_string"),
           "Construct from an input label and a PVL translation string (set from_string=True).")
      .def("translate",
           [](Isis::PvlToPvlTranslationManager &self, const std::string &group_name,
              int findex) {
             return qStringToStdString(
                 self.Translate(stdStringToQString(group_name), findex));
           },
           py::arg("group_name"), py::arg("findex") = 0,
           "Translate a single keyword value using the named translation group.")
      .def("auto_translate",
           [](Isis::PvlToPvlTranslationManager &self, Isis::Pvl &output_label) {
             self.Auto(output_label);
           },
           py::arg("output_label"),
           "Translate all Auto-flagged groups into output_label.")
      .def("auto_translate",
           [](Isis::PvlToPvlTranslationManager &self,
              Isis::Pvl &input_label, Isis::Pvl &output_label) {
             self.Auto(input_label, output_label);
           },
           py::arg("input_label"), py::arg("output_label"),
           "Set input_label and translate all Auto groups into output_label.")
      .def("input_has_keyword",
           [](Isis::PvlToPvlTranslationManager &self, const std::string &group_name) {
             return self.InputHasKeyword(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return True if the input label contains the keyword for the named group.")
      .def("set_label",
           [](Isis::PvlToPvlTranslationManager &self, Isis::Pvl &input_label) {
             self.SetLabel(input_label);
           },
           py::arg("input_label"),
           "Set the input label to use for subsequent translations.")
      .def("__repr__",
           [](const Isis::PvlToPvlTranslationManager &) {
             return "PvlToPvlTranslationManager()";
           });

  // Added: 2026-04-09 - PvlToXmlTranslationManager binding (PVL to XML translation)
  py::class_<Isis::PvlToXmlTranslationManager, Isis::LabelTranslationManager>(
      m, "PvlToXmlTranslationManager")
      .def(py::init([](const std::string &trans_file) {
             return Isis::PvlToXmlTranslationManager(stdStringToQString(trans_file));
           }),
           py::arg("trans_file"),
           "Construct from a translation table file path.")
      .def(py::init([](Isis::Pvl &input_label, const std::string &trans_file) {
             return Isis::PvlToXmlTranslationManager(input_label,
                                                      stdStringToQString(trans_file));
           }),
           py::arg("input_label"), py::arg("trans_file"),
           "Construct from an input label and a translation table file path.")
      .def("translate",
           [](Isis::PvlToXmlTranslationManager &self, const std::string &group_name,
              int input_index) {
             return qStringToStdString(
                 self.Translate(stdStringToQString(group_name), input_index));
           },
           py::arg("group_name"), py::arg("input_index") = 0,
           "Translate a single keyword value using the named translation group.")
      .def("input_has_keyword",
           [](Isis::PvlToXmlTranslationManager &self, const std::string &group_name) {
             return self.InputHasKeyword(stdStringToQString(group_name));
           },
           py::arg("group_name"),
           "Return True if the input label contains the keyword for the named group.")
      .def("set_label",
           [](Isis::PvlToXmlTranslationManager &self, Isis::Pvl &input_label) {
             self.SetLabel(input_label);
           },
           py::arg("input_label"),
           "Set the input label for subsequent translations.")
      .def("__repr__",
           [](const Isis::PvlToXmlTranslationManager &) {
             return "PvlToXmlTranslationManager()";
           });

  // Added: 2026-04-09 - XmlToPvlTranslationManager binding (XML to PVL translation)
  py::class_<Isis::XmlToPvlTranslationManager, Isis::LabelTranslationManager>(
      m, "XmlToPvlTranslationManager")
      .def(py::init([](const std::string &trans_file) {
             return Isis::XmlToPvlTranslationManager(stdStringToQString(trans_file));
           }),
           py::arg("trans_file"),
           "Construct from a translation table file path.")
      .def(py::init([](const std::string &trans_text, bool from_string) {
             std::istringstream iss(trans_text);
             return Isis::XmlToPvlTranslationManager(iss);
           }),
           py::arg("trans_text"), py::arg("from_string"),
           "Construct from a PVL translation text string (set from_string=True).")
      .def(py::init([](Isis::FileName &input_label, const std::string &trans_file) {
             return Isis::XmlToPvlTranslationManager(input_label,
                                                      stdStringToQString(trans_file));
           }),
           py::arg("input_label"), py::arg("trans_file"),
           "Construct from an XML input-label FileName and a translation table file path.")
      .def(py::init([](Isis::FileName &input_label, const std::string &trans_text, bool from_string) {
             std::istringstream iss(trans_text);
             return Isis::XmlToPvlTranslationManager(input_label, iss);
           }),
           py::arg("input_label"), py::arg("trans_text"), py::arg("from_string"),
           "Construct from an XML input-label FileName and a PVL translation string (set from_string=True).")
      .def("translate",
           [](Isis::XmlToPvlTranslationManager &self, const std::string &group_name,
              int findex) {
             return qStringToStdString(
                 self.Translate(stdStringToQString(group_name), findex));
           },
           py::arg("group_name"), py::arg("findex") = 0,
           "Translate a single keyword value using the named translation group.")
      .def("auto_translate",
           [](Isis::XmlToPvlTranslationManager &self, Isis::FileName &input_label,
              Isis::Pvl &output_label) {
             self.Auto(input_label, output_label);
           },
           py::arg("input_label"), py::arg("output_label"),
           "Translate all Auto-flagged groups from input_label (XML FileName) into output_label (Pvl).")
      .def("__repr__",
           [](const Isis::XmlToPvlTranslationManager &) {
             return "XmlToPvlTranslationManager()";
           });
}