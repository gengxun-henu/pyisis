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

#include "Pvl.h"
#include "PvlContainer.h"
#include "PvlGroup.h"
#include "PvlKeyword.h"
#include "PvlObject.h"
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
      });

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
      .def("__str__", &pvlLikeToString<Isis::Pvl>)
      .def("__repr__", [](Isis::Pvl &self) {
        return "Pvl(" + pvlLikeToString(self) + ")";
      });
}