// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

#include <string>

#include "Camera.h"
#include "Cube.h"
#include "helpers.h"

namespace py = pybind11;

/**
 * @brief Bindings for the Isis::Cube class
 * This function creates Python bindings for the Isis::Cube class using pybind11. The Cube
 * class provides functionality for working with ISIS image cubes, including opening and closing cube files, accessing cube dimensions, and retrieving the associated camera model. These bindings allow Python users to utilize the powerful cube handling capabilities of the Isis::Cube class in their Python code when working with ISIS image cubes.
 * @see Isis::Cube
 * @param m The pybind11 module to which the bindings will be added.
 * @author Geng Xun
 * @history 2026-03-21 13:17:53 - Initial implementation of Cube bindings.
 * 
 */
void bind_cube(py::module_ &m) {
  py::class_<Isis::Cube>(m, "Cube")
      .def(py::init<>())

      /**
       * @brief open a cube file. This method opens a cube file specified by the given path and access mode. The path is provided as a string, and the access mode is also a string that can be "r" for read-only access or "rw" for read-write access. The method uses the QString class to convert the input strings to the appropriate format for the underlying C++ implementation. If the cube file is successfully opened, it will be available for further operations such as reading data or accessing metadata.
       * @see Isis::Cube::open
       * @param self The Cube instance on which to call the open method.
       * @param path The file path of the cube to open, provided as a string.
       * @param access The access mode for opening the cube, provided as a string ("r" for read-only or "rw" for read-write). The default value is "r".
       * @return None
       * @note The method does not return a value, but it modifies the state of the Cube instance by opening the specified cube file. It is important to ensure that the path provided is valid and that the access mode is appropriate for the intended use of the cube.
       * @internal
       * @todo Add error handling for cases where the cube file cannot be opened, such as
       * when the file does not exist, when the access mode is invalid, or when there are permission issues. Consider raising appropriate exceptions in these cases to provide feedback to the user.
       * 
       * useage example:
       * @code
       * cube = ip.Cube()
       * cube.open("path/to/cube.cub", "r")
       * @endcode
       */
      .def("open",
           [](Isis::Cube &self, const std::string &path, const std::string &access) {
             self.open(QString::fromStdString(path), QString::fromStdString(access));
           },
           py::arg("path"), py::arg("access") = "r")
      .def("close", &Isis::Cube::close, py::arg("remove") = false)
      .def("is_open", &Isis::Cube::isOpen)
      .def("is_projected", &Isis::Cube::isProjected)
      .def("is_read_only", &Isis::Cube::isReadOnly)
      .def("sample_count", &Isis::Cube::sampleCount)

      /**
       * @brief get the line count of the cube. This method returns the number of lines in the cube, which is a measure of the vertical dimension of the image data. The line count is an important property of the cube that can be used for various processing tasks, such as iterating over lines of data or determining the size of the output from certain operations.
       * @see Isis::Cube::lineCount
       * @param self The Cube instance for which to retrieve the line count.
       * @return The number of lines in the cube.
       * @author Geng Xun
       * @date 2026-03-21
       */
      .def("line_count", &Isis::Cube::lineCount)
      .def("band_count", &Isis::Cube::bandCount)
      /**
       * @brief get the camera model associated with the cube. This method returns a pointer to the Camera object associated with the cube, which provides access to the camera model and related information. The camera model is an important component of the cube that allows for accurate geospatial referencing and other operations that depend on the camera's properties.
       * @see Isis::Cube::camera
       * @param self The Cube instance for which to retrieve the camera model.
       * @return A pointer to the Camera object associated with the cube.
       * @author Geng Xun
       * @date 2026-03-21
       * @note The returned Camera object is owned by the Cube instance, so the return value
       * is marked with py::return_value_policy::reference_internal to ensure that the Camera object is not deleted when the Python reference goes out of scope. It is important to ensure that the Cube instance is kept alive as long as the Camera object is being used in Python to prevent dangling references.
       * @internal 
       * @todo Add error handling for cases where the cube does not have an associated camera model or when the camera model cannot be retrieved.
       * 
       * useage example:
       * @code
       * cube = ip.Cube()
       * cube.open("path/to/cube.cub")
       * file_name = cube.file_name()
       * @endcode
       */
      .def("file_name", [](Isis::Cube &self) { return qStringToStdString(self.fileName()); })

      /**
       * @brief get the camera model associated with the cube. This method returns a pointer to the Camera object associated with the cube, which provides access to the camera model and related information. The camera model is an important component of the cube that allows for accurate geospatial referencing and other operations that depend on the camera's properties.
       * @see Isis::Cube::camera
       * @param self The Cube instance for which to retrieve the camera model.
       * @return A pointer to the Camera object associated with the cube.
       * @author Geng Xun
       * @date 2026-03-21
       * @note The returned Camera object is owned by the Cube instance, so the return value
       * is marked with py::return_value_policy::reference_internal to ensure that the Camera object
       * is not deleted when the Python reference goes out of scope. It is important to ensure that the Cube instance is kept alive as long as the Camera object is being used in Python to prevent dangling references.
       * @internal 
       * @todo Add error handling for cases where the cube does not have an associated camera model
       * or when the camera model cannot be retrieved.
       * useage example:
       * @code
       * cube = ip.Cube()
       * cube.open("path/to/cube.cub")
       * camera = cube.camera()
       * @endcode
       */
      .def("camera",
           [](Isis::Cube &self) -> Isis::Camera * { return self.camera(); },
           py::return_value_policy::reference_internal);
}
