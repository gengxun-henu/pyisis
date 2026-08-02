cmake_minimum_required(VERSION 3.18)

if(POLICY CMP0177)
  cmake_policy(SET CMP0177 NEW)
endif()

if(NOT WIN32 AND NOT DEFINED CMAKE_CXX_COMPILER AND DEFINED ENV{CONDA_PREFIX})
  find_program(CONDA_CXX_COMPILER
    NAMES x86_64-conda-linux-gnu-c++
    HINTS
      "$ENV{CONDA_PREFIX}/bin"
      "$ENV{CONDA_PREFIX}/../bin"
      "$ENV{CONDA_PREFIX}/../../bin")

  if(CONDA_CXX_COMPILER)
    set(CMAKE_CXX_COMPILER "${CONDA_CXX_COMPILER}" CACHE FILEPATH
      "C++ compiler selected from the active conda toolchain" FORCE)
  endif()
endif()

project(isis_pybind_standalone LANGUAGES CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if((NOT DEFINED CMAKE_CXX_COMPILER_LAUNCHER OR CMAKE_CXX_COMPILER_LAUNCHER STREQUAL "")
   AND NOT DEFINED ENV{CMAKE_CXX_COMPILER_LAUNCHER})
  find_program(CCACHE_PROGRAM NAMES ccache)
  if(CCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}" CACHE STRING
      "Compiler launcher used for C++ compilation" FORCE)
  endif()
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

function(pyisis_first_existing_path out_var)
  foreach(candidate IN LISTS ARGN)
    if(candidate AND EXISTS "${candidate}")
      set(${out_var} "${candidate}" PARENT_SCOPE)
      return()
    endif()
  endforeach()
  set(${out_var} "" PARENT_SCOPE)
endfunction()

function(pyisis_existing_paths out_var)
  set(existing_paths "")
  foreach(candidate IN LISTS ARGN)
    if(candidate AND EXISTS "${candidate}")
      list(APPEND existing_paths "${candidate}")
    endif()
  endforeach()
  if(existing_paths)
    list(REMOVE_DUPLICATES existing_paths)
  endif()
  set(${out_var} "${existing_paths}" PARENT_SCOPE)
endfunction()

function(pyisis_first_runtime_dir out_var)
  foreach(candidate IN LISTS ARGN)
    if(candidate AND EXISTS "${candidate}/isis.dll")
      set(${out_var} "${candidate}" PARENT_SCOPE)
      return()
    endif()
  endforeach()
  pyisis_first_existing_path(existing_runtime_dir ${ARGN})
  set(${out_var} "${existing_runtime_dir}" PARENT_SCOPE)
endfunction()

set(ISIS_PREFIX "$ENV{ISIS_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment")
if(NOT ISIS_PREFIX AND DEFINED ENV{CONDA_PREFIX})
  if(WIN32)
    if((EXISTS "$ENV{CONDA_PREFIX}/Library/include/isis" OR EXISTS "$ENV{CONDA_PREFIX}/include/isis")
       AND (EXISTS "$ENV{CONDA_PREFIX}/Library/lib/isis.lib" OR EXISTS "$ENV{CONDA_PREFIX}/lib/isis.lib"))
      set(ISIS_PREFIX "$ENV{CONDA_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment" FORCE)
    endif()
  else()
    if(EXISTS "$ENV{CONDA_PREFIX}/include/isis" AND EXISTS "$ENV{CONDA_PREFIX}/lib/libisis.so")
      set(ISIS_PREFIX "$ENV{CONDA_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment" FORCE)
    endif()
  endif()
endif()

if(NOT ISIS_PREFIX)
  message(FATAL_ERROR "ISIS_PREFIX is not set. Point it to the external ISIS installation (for example the asp360_new conda environment).")
endif()

set(PYISIS_ISIS_VERSION_FILE "${ISIS_PREFIX}/isis_version.txt")
if(NOT EXISTS "${PYISIS_ISIS_VERSION_FILE}")
  message(FATAL_ERROR
    "ISIS version metadata is missing: ${PYISIS_ISIS_VERSION_FILE}. "
    "Use a complete ISIS development/runtime prefix.")
endif()
file(STRINGS "${PYISIS_ISIS_VERSION_FILE}" _pyisis_isis_version_line LIMIT_COUNT 1)
string(REGEX MATCH
  "^[ \t]*([0-9]+)\\.([0-9]+)\\.([0-9]+)"
  _pyisis_isis_version_match
  "${_pyisis_isis_version_line}")
if(NOT _pyisis_isis_version_match)
  message(FATAL_ERROR
    "Unable to parse an ISIS semantic version from ${PYISIS_ISIS_VERSION_FILE}: "
    "${_pyisis_isis_version_line}")
endif()
set(PYISIS_ISIS_VERSION "${CMAKE_MATCH_1}.${CMAKE_MATCH_2}.${CMAKE_MATCH_3}")
set(PYISIS_ISIS_VERSION_MAJOR "${CMAKE_MATCH_1}")
set(PYISIS_ISIS_VERSION_MINOR "${CMAKE_MATCH_2}")
set(PYISIS_ISIS_VERSION_PATCH "${CMAKE_MATCH_3}")
set(PYISIS_PACKAGE_VERSION "1.3.0rc2" CACHE STRING
  "Python distribution version embedded in the generated package metadata")
if(DEFINED SKBUILD_PROJECT_VERSION_FULL AND NOT SKBUILD_PROJECT_VERSION_FULL STREQUAL "")
  set(PYISIS_PACKAGE_VERSION "${SKBUILD_PROJECT_VERSION_FULL}" CACHE STRING
    "Python distribution version embedded in the generated package metadata" FORCE)
elseif(DEFINED SKBUILD_PROJECT_VERSION AND NOT SKBUILD_PROJECT_VERSION STREQUAL "")
  set(PYISIS_PACKAGE_VERSION "${SKBUILD_PROJECT_VERSION}" CACHE STRING
    "Python distribution version embedded in the generated package metadata" FORCE)
endif()

if(NOT DEFINED pybind11_DIR OR pybind11_DIR STREQUAL "")
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
    RESULT_VARIABLE _pybind11_cmakedir_result
    OUTPUT_VARIABLE _pybind11_cmakedir
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
  if(_pybind11_cmakedir_result EQUAL 0
     AND EXISTS "${_pybind11_cmakedir}/pybind11Config.cmake")
    set(pybind11_DIR "${_pybind11_cmakedir}" CACHE PATH
      "pybind11 config supplied by the selected Python interpreter" FORCE)
  else()
    message(FATAL_ERROR
      "The selected Python interpreter (${Python3_EXECUTABLE}) does not provide "
      "pybind11. Install pybind11 in that conda/build environment or pass an "
      "explicit -Dpybind11_DIR=...; fallback to another conda environment is "
      "disabled.")
  endif()
endif()
find_package(pybind11 CONFIG REQUIRED PATHS "${pybind11_DIR}" NO_DEFAULT_PATH)

if(WIN32)
  pyisis_first_existing_path(_qt_cmake_root
    "$ENV{PYISIS_DEP_PREFIX}/Library/lib/cmake"
    "$ENV{PYISIS_DEP_PREFIX}/lib/cmake"
    "$ENV{CONDA_PREFIX}/Library/lib/cmake"
    "$ENV{CONDA_PREFIX}/lib/cmake"
    "${ISIS_PREFIX}/Library/lib/cmake"
    "${ISIS_PREFIX}/lib/cmake")
  pyisis_first_existing_path(_qt_isis_include_dir
    "${ISIS_PREFIX}/Library/include/isis"
    "${ISIS_PREFIX}/include/isis")
else()
  set(_qt_cmake_root "${ISIS_PREFIX}/lib/cmake")
  set(_qt_isis_include_dir "${ISIS_PREFIX}/include/isis")
endif()
set(PYISIS_QT_MAJOR "AUTO" CACHE STRING
  "Qt major version linked by the target ISIS runtime (AUTO, 5, or 6)")
set_property(CACHE PYISIS_QT_MAJOR PROPERTY STRINGS AUTO 5 6)
if(PYISIS_QT_MAJOR STREQUAL "AUTO")
  if(EXISTS "${_qt_isis_include_dir}/IEndian.h"
     AND EXISTS "${_qt_cmake_root}/Qt6/Qt6Config.cmake")
    set(_pyisis_qt_major 6)
  elseif(EXISTS "${_qt_isis_include_dir}/Endian.h"
         AND EXISTS "${_qt_cmake_root}/Qt5/Qt5Config.cmake")
    set(_pyisis_qt_major 5)
  elseif(EXISTS "${_qt_cmake_root}/Qt6/Qt6Config.cmake"
         AND NOT EXISTS "${_qt_cmake_root}/Qt5/Qt5Config.cmake")
    set(_pyisis_qt_major 6)
  elseif(EXISTS "${_qt_cmake_root}/Qt5/Qt5Config.cmake"
         AND NOT EXISTS "${_qt_cmake_root}/Qt6/Qt6Config.cmake")
    set(_pyisis_qt_major 5)
  else()
    message(FATAL_ERROR
      "Unable to select the Qt major version for the target ISIS prefix. "
      "Pass -DPYISIS_QT_MAJOR=5 or -DPYISIS_QT_MAJOR=6 explicitly.")
  endif()
elseif(PYISIS_QT_MAJOR STREQUAL "5" OR PYISIS_QT_MAJOR STREQUAL "6")
  set(_pyisis_qt_major "${PYISIS_QT_MAJOR}")
else()
  message(FATAL_ERROR
    "PYISIS_QT_MAJOR must be AUTO, 5, or 6; got ${PYISIS_QT_MAJOR}.")
endif()
set(PYISIS_QT_PACKAGE "Qt${_pyisis_qt_major}")
if(NOT EXISTS "${_qt_cmake_root}/${PYISIS_QT_PACKAGE}/${PYISIS_QT_PACKAGE}Config.cmake")
  message(FATAL_ERROR
    "${PYISIS_QT_PACKAGE} was selected for the target ISIS runtime, but its "
    "CMake config is missing under ${_qt_cmake_root}.")
endif()

set(${PYISIS_QT_PACKAGE}_DIR
  "${_qt_cmake_root}/${PYISIS_QT_PACKAGE}" CACHE PATH
  "${PYISIS_QT_PACKAGE} config directory from the selected ISIS prefix" FORCE)
set(PYISIS_QT_COMPONENTS Core Concurrent Xml Widgets)
if(PYISIS_QT_PACKAGE STREQUAL "Qt6")
  list(APPEND PYISIS_QT_COMPONENTS Core5Compat)
endif()
find_package(${PYISIS_QT_PACKAGE} CONFIG REQUIRED
  COMPONENTS ${PYISIS_QT_COMPONENTS}
  PATHS "${_qt_cmake_root}/${PYISIS_QT_PACKAGE}"
  NO_DEFAULT_PATH)
set(PYISIS_QT_TARGETS
  ${PYISIS_QT_PACKAGE}::Core
  ${PYISIS_QT_PACKAGE}::Concurrent
  ${PYISIS_QT_PACKAGE}::Xml
  ${PYISIS_QT_PACKAGE}::Widgets)
if(PYISIS_QT_PACKAGE STREQUAL "Qt6")
  list(APPEND PYISIS_QT_TARGETS Qt6::Core5Compat)
endif()
set(PYISIS_QT_CORE_TARGET ${PYISIS_QT_PACKAGE}::Core)

if(WIN32)
  pyisis_first_existing_path(_default_isis_include_dir
    "${ISIS_PREFIX}/Library/include/isis"
    "${ISIS_PREFIX}/include/isis")
  pyisis_first_existing_path(_default_isis_dep_include_dir
    "$ENV{CONDA_PREFIX}/Library/include"
    "$ENV{CONDA_PREFIX}/include"
    "${ISIS_PREFIX}/Library/include"
    "${ISIS_PREFIX}/include")
  pyisis_existing_paths(_default_isis_dep_include_dirs
    "$ENV{CONDA_PREFIX}/Library/include"
    "$ENV{CONDA_PREFIX}/include"
    "${ISIS_PREFIX}/Library/include"
    "${ISIS_PREFIX}/include")
  pyisis_first_existing_path(_default_isis_library_dir
    "${ISIS_PREFIX}/Library/lib"
    "${ISIS_PREFIX}/lib")
  pyisis_existing_paths(_default_isis_dep_library_dirs
    "$ENV{CONDA_PREFIX}/Library/lib"
    "$ENV{CONDA_PREFIX}/lib")
  pyisis_first_runtime_dir(_default_isis_runtime_dir
    "${ISIS_PREFIX}/Library/bin"
    "${ISIS_PREFIX}/Library/lib"
    "${ISIS_PREFIX}/bin"
    "${ISIS_PREFIX}/lib")
  pyisis_first_existing_path(_default_isis_core_library
    "${_default_isis_library_dir}/isis.lib")
  pyisis_first_existing_path(_default_isis_plugin_file
    "${_default_isis_library_dir}/Camera.plugin"
    "${_default_isis_runtime_dir}/Camera.plugin")
else()
  set(_default_isis_include_dir "${ISIS_PREFIX}/include/isis")
  set(_default_isis_dep_include_dir "${ISIS_PREFIX}/include")
  set(_default_isis_dep_include_dirs "${_default_isis_dep_include_dir}")
  set(_default_isis_library_dir "${ISIS_PREFIX}/lib")
  set(_default_isis_dep_library_dirs "")
  set(_default_isis_runtime_dir "${ISIS_PREFIX}/lib")
  set(_default_isis_core_library "${_default_isis_library_dir}/libisis.so")
  set(_default_isis_plugin_file "${_default_isis_library_dir}/Camera.plugin")
endif()

set(ISIS_INCLUDE_DIR "${_default_isis_include_dir}" CACHE PATH "Directory containing ISIS headers")
set(ISIS_DEP_INCLUDE_DIR "${_default_isis_dep_include_dir}" CACHE PATH "Directory containing external ISIS dependencies such as CSPICE and Qt headers")
set(ISIS_DEP_INCLUDE_DIRS "${_default_isis_dep_include_dirs}" CACHE STRING "Semicolon-separated directories containing external ISIS dependency headers")
set(ISIS_LIBRARY_DIR "${_default_isis_library_dir}" CACHE PATH "Directory containing ISIS import/shared libraries")
set(ISIS_DEP_LIBRARY_DIRS "${_default_isis_dep_library_dirs}" CACHE STRING "Semicolon-separated directories containing external ISIS dependency libraries")
set(ISIS_RUNTIME_DIR "${_default_isis_runtime_dir}" CACHE PATH "Directory containing ISIS runtime shared libraries")
set(ISIS_CORE_LIBRARY "${_default_isis_core_library}" CACHE FILEPATH "Path to the ISIS core import/shared library")
set(ISIS_PLUGIN_FILE "${_default_isis_plugin_file}" CACHE FILEPATH "Path to Camera.plugin")
set(ISIS_CAMERA_LIBS ""
    CACHE STRING
    "Semicolon-separated extra ISIS camera libraries to link (empty means auto-detect a minimal set)")
option(ISIS_EXCLUDE_ASP_VW_CAMERA_LIBS
  "Exclude libAsp* and libVw* camera libraries from the extra ISIS camera link set"
  ON)
option(PYISIS_BUILD_BENCHMARKS "Build pyisis developer benchmark executables" ON)

set(ISIS_DEP_INCLUDE_SEARCH_DIRS "${ISIS_DEP_INCLUDE_DIR}" ${ISIS_DEP_INCLUDE_DIRS})
list(REMOVE_DUPLICATES ISIS_DEP_INCLUDE_SEARCH_DIRS)

set(ISIS_DEP_SUBDIR_INCLUDE_DIRS "")
foreach(dep_include_dir IN LISTS ISIS_DEP_INCLUDE_SEARCH_DIRS)
  list(APPEND ISIS_DEP_SUBDIR_INCLUDE_DIRS
    "${dep_include_dir}/csm"
    "${dep_include_dir}/cspice"
    "${dep_include_dir}/bullet"
    "${dep_include_dir}/tnt"
    "${dep_include_dir}/qt"
    "${dep_include_dir}/qt/QtCore")
endforeach()
list(REMOVE_DUPLICATES ISIS_DEP_SUBDIR_INCLUDE_DIRS)

set(ISIS_DEP_LIBRARY_SEARCH_DIRS "${ISIS_LIBRARY_DIR}" ${ISIS_DEP_LIBRARY_DIRS})
list(REMOVE_DUPLICATES ISIS_DEP_LIBRARY_SEARCH_DIRS)

foreach(required_path IN ITEMS ISIS_INCLUDE_DIR ISIS_DEP_INCLUDE_DIR ISIS_LIBRARY_DIR ISIS_RUNTIME_DIR ISIS_CORE_LIBRARY ISIS_PLUGIN_FILE)
  if(NOT EXISTS "${${required_path}}")
    message(FATAL_ERROR "${required_path} does not exist: ${${required_path}}")
  endif()
endforeach()

if(ISIS_CAMERA_LIBS)
  set(ISIS_EXTRA_CAMERA_LIBS ${ISIS_CAMERA_LIBS})
else()
  if(WIN32)
    file(GLOB ISIS_EXTRA_CAMERA_LIBS
         "${ISIS_LIBRARY_DIR}/*Camera.lib"
         "${ISIS_LIBRARY_DIR}/MiniRF.lib")
  else()
    file(GLOB ISIS_EXTRA_CAMERA_LIBS
         "${ISIS_LIBRARY_DIR}/lib*Camera.so"
         "${ISIS_LIBRARY_DIR}/libMiniRF.so")
  endif()
  list(REMOVE_DUPLICATES ISIS_EXTRA_CAMERA_LIBS)
endif()

if(ISIS_EXCLUDE_ASP_VW_CAMERA_LIBS)
  list(FILTER ISIS_EXTRA_CAMERA_LIBS EXCLUDE REGEX "[/\\\\](lib)?(Asp|ASP|Vw|VW)[^/\\\\]*$")
endif()

set(ISIS_EXTRA_MODULE_LIBS "")
if(WIN32)
  file(GLOB ISIS_EXTRA_MODULE_LIBS "${ISIS_LIBRARY_DIR}/*.lib")
  list(FILTER ISIS_EXTRA_MODULE_LIBS EXCLUDE REGEX "[/\\\\]isis\\.lib$")
  if(ISIS_EXCLUDE_ASP_VW_CAMERA_LIBS)
    list(FILTER ISIS_EXTRA_MODULE_LIBS EXCLUDE REGEX "[/\\\\](lib)?(Asp|ASP|Vw|VW)[^/\\\\]*$")
  endif()
  list(REMOVE_DUPLICATES ISIS_EXTRA_MODULE_LIBS)
endif()

set(ISIS_PROJECTION_LIB_NAMES
    Equirectangular
    IProj
    LambertAzimuthalEqualArea
    LambertConformal
    LunarAzimuthalEqualArea
    Mercator
    Mollweide
    ObliqueCylindrical
    Orthographic
    Planar
    PointPerspective
    PolarStereographic
    RingCylindrical
    Robinson
    SimpleCylindrical
    Sinusoidal
    TransverseMercator
    UpturnedEllipsoidTransverseAzimuthal)

set(ISIS_EXTRA_PROJECTION_LIBS "")
foreach(projection_lib_name IN LISTS ISIS_PROJECTION_LIB_NAMES)
  find_library(ISIS_PROJECTION_LIB_${projection_lib_name}
               NAMES ${projection_lib_name}
               PATHS "${ISIS_LIBRARY_DIR}"
               NO_DEFAULT_PATH)
  if(ISIS_PROJECTION_LIB_${projection_lib_name})
    list(APPEND ISIS_EXTRA_PROJECTION_LIBS "${ISIS_PROJECTION_LIB_${projection_lib_name}}")
  endif()
endforeach()
list(REMOVE_DUPLICATES ISIS_EXTRA_PROJECTION_LIBS)

set(BULLET_LIBRARY_NAMES
    BulletDynamics
    BulletCollision
    LinearMath)

set(BULLET_RUNTIME_LIBS "")
foreach(bullet_lib_name IN LISTS BULLET_LIBRARY_NAMES)
  if(PYISIS_ISIS_VERSION_MAJOR GREATER_EQUAL 10)
    set(_pyisis_bullet_candidates
        "${bullet_lib_name}-float64"
        "${bullet_lib_name}")
  else()
    set(_pyisis_bullet_candidates "${bullet_lib_name}")
  endif()
  unset(BULLET_LIB_${bullet_lib_name} CACHE)
  find_library(BULLET_LIB_${bullet_lib_name}
               NAMES ${_pyisis_bullet_candidates}
               PATHS ${ISIS_DEP_LIBRARY_SEARCH_DIRS}
               NO_DEFAULT_PATH)
  if(BULLET_LIB_${bullet_lib_name})
    list(APPEND BULLET_RUNTIME_LIBS "${BULLET_LIB_${bullet_lib_name}}")
  endif()
endforeach()
unset(_pyisis_bullet_candidates)
list(REMOVE_DUPLICATES BULLET_RUNTIME_LIBS)

set(ISIS_RUNTIME_DEP_LIB_NAMES
    ale
    core
    csmapi
    geos
    geos_c
    gsl
    gslcblas
    libprotobuf
    libprotobuf-lite
    xerces-c_3)
if(PYISIS_ISIS_VERSION_MAJOR GREATER_EQUAL 10)
  list(APPEND ISIS_RUNTIME_DEP_LIB_NAMES gdal)
endif()

set(ISIS_RUNTIME_DEP_LIBS "")
foreach(runtime_dep_lib_name IN LISTS ISIS_RUNTIME_DEP_LIB_NAMES)
  find_library(ISIS_RUNTIME_DEP_LIB_${runtime_dep_lib_name}
               NAMES ${runtime_dep_lib_name}
               PATHS ${ISIS_DEP_LIBRARY_SEARCH_DIRS}
               NO_DEFAULT_PATH)
  if(ISIS_RUNTIME_DEP_LIB_${runtime_dep_lib_name})
    list(APPEND ISIS_RUNTIME_DEP_LIBS "${ISIS_RUNTIME_DEP_LIB_${runtime_dep_lib_name}}")
  endif()
endforeach()
list(REMOVE_DUPLICATES ISIS_RUNTIME_DEP_LIBS)

file(GLOB PCL_INCLUDE_DIRS "${ISIS_DEP_INCLUDE_DIR}/pcl-*")
foreach(dep_include_dir IN LISTS ISIS_DEP_INCLUDE_SEARCH_DIRS)
  file(GLOB dep_pcl_include_dirs "${dep_include_dir}/pcl-*")
  list(APPEND PCL_INCLUDE_DIRS ${dep_pcl_include_dirs})
endforeach()
list(REMOVE_DUPLICATES PCL_INCLUDE_DIRS)

find_path(PYISIS_PCL_INCLUDE_DIR
          NAMES pcl/io/auto_io.h
          PATHS ${ISIS_DEP_INCLUDE_SEARCH_DIRS} ${PCL_INCLUDE_DIRS}
          NO_DEFAULT_PATH)
if(PYISIS_PCL_INCLUDE_DIR)
  list(APPEND PCL_INCLUDE_DIRS "${PYISIS_PCL_INCLUDE_DIR}")
  list(REMOVE_DUPLICATES PCL_INCLUDE_DIRS)
endif()

find_path(PYISIS_EMBREE_INCLUDE_DIR
          NAMES embree3/rtcore.h
          PATHS ${ISIS_DEP_INCLUDE_SEARCH_DIRS}
          NO_DEFAULT_PATH)

set(PYISIS_HAS_EMBREE_SHAPE_MODEL OFF)
if(PYISIS_PCL_INCLUDE_DIR AND PYISIS_EMBREE_INCLUDE_DIR)
  set(PYISIS_HAS_EMBREE_SHAPE_MODEL ON)
endif()

find_path(EIGEN3_INCLUDE_DIR
          NAMES Eigen/StdVector
          PATHS ${ISIS_DEP_INCLUDE_SEARCH_DIRS}
          PATH_SUFFIXES eigen3
          NO_DEFAULT_PATH)

set(ISIS_OPTIONAL_INCLUDE_DIRS ${PCL_INCLUDE_DIRS})
if(EIGEN3_INCLUDE_DIR)
  list(APPEND ISIS_OPTIONAL_INCLUDE_DIRS "${EIGEN3_INCLUDE_DIR}")
endif()
if(PYISIS_EMBREE_INCLUDE_DIR)
  list(APPEND ISIS_OPTIONAL_INCLUDE_DIRS "${PYISIS_EMBREE_INCLUDE_DIR}")
endif()
list(REMOVE_DUPLICATES ISIS_OPTIONAL_INCLUDE_DIRS)

if(SKBUILD)
  set(PYISIS_INSTALL_SITELIB ".")
  set(PYISIS_INSTALL_SITEARCH ".")
else()
  if(NOT Python3_SITELIB)
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_path('purelib'))"
      OUTPUT_VARIABLE Python3_SITELIB
      OUTPUT_STRIP_TRAILING_WHITESPACE)
  endif()

  if(NOT Python3_SITEARCH)
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_path('platlib'))"
      OUTPUT_VARIABLE Python3_SITEARCH
      OUTPUT_STRIP_TRAILING_WHITESPACE)
  endif()

  set(PYISIS_DEFAULT_SITELIB "${Python3_SITELIB}")
  set(PYISIS_DEFAULT_SITEARCH "${Python3_SITEARCH}")
  set(PYISIS_INSTALL_SITELIB "${PYISIS_DEFAULT_SITELIB}" CACHE PATH
    "Python purelib install directory for the pyisis facade package")
  set(PYISIS_INSTALL_SITEARCH "${PYISIS_DEFAULT_SITEARCH}" CACHE PATH
    "Python platlib install directory for the compiled isis_pybind package")
endif()

set(ISIS_PYBIND_PACKAGE_NAME isis_pybind)
set(ISIS_PYBIND_BUILD_PACKAGE_DIR "${CMAKE_CURRENT_BINARY_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}")
set(ISIS_PYBIND_LICENSE_FILE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
set(ISIS_PYBIND_SOURCE_INIT_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/__init__.py")
set(ISIS_PYBIND_SOURCE_APP_RUNNER_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/_app_runner.py")
set(ISIS_PYBIND_SOURCE_CSV2TABLE_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/_csv2table.py")
set(ISIS_PYBIND_SOURCE_BUILD_INFO_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/_build_info.py.in")
set(ISIS_PYBIND_BUILD_INIT_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/__init__.py")
set(ISIS_PYBIND_BUILD_APP_RUNNER_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/_app_runner.py")
set(ISIS_PYBIND_BUILD_CSV2TABLE_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/_csv2table.py")
set(ISIS_PYBIND_BUILD_INFO_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/_build_info.py")
set(ISIS_PYBIND_BUILD_LICENSE_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/LICENSE")
set(PYISIS_FACADE_PACKAGE_NAME pyisis)
set(PYISIS_FACADE_BUILD_PACKAGE_DIR "${CMAKE_CURRENT_BINARY_DIR}/python/${PYISIS_FACADE_PACKAGE_NAME}")
set(PYISIS_FACADE_SOURCE_INIT_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${PYISIS_FACADE_PACKAGE_NAME}/__init__.py")
set(PYISIS_FACADE_SOURCE_RUNTIME_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${PYISIS_FACADE_PACKAGE_NAME}/_runtime.py")
set(PYISIS_FACADE_BUILD_INIT_FILE
    "${PYISIS_FACADE_BUILD_PACKAGE_DIR}/__init__.py")
set(PYISIS_FACADE_BUILD_RUNTIME_FILE
    "${PYISIS_FACADE_BUILD_PACKAGE_DIR}/_runtime.py")
set(PYISIS_FACADE_BUILD_LICENSE_FILE
    "${PYISIS_FACADE_BUILD_PACKAGE_DIR}/LICENSE")
file(MAKE_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}")
file(MAKE_DIRECTORY "${PYISIS_FACADE_BUILD_PACKAGE_DIR}")
configure_file(
  "${ISIS_PYBIND_SOURCE_INIT_FILE}"
  "${ISIS_PYBIND_BUILD_INIT_FILE}"
  COPYONLY)
configure_file(
  "${ISIS_PYBIND_SOURCE_APP_RUNNER_FILE}"
  "${ISIS_PYBIND_BUILD_APP_RUNNER_FILE}"
  COPYONLY)
configure_file(
  "${ISIS_PYBIND_SOURCE_CSV2TABLE_FILE}"
  "${ISIS_PYBIND_BUILD_CSV2TABLE_FILE}"
  COPYONLY)
configure_file(
  "${ISIS_PYBIND_SOURCE_BUILD_INFO_FILE}"
  "${ISIS_PYBIND_BUILD_INFO_FILE}"
  @ONLY)
configure_file(
  "${ISIS_PYBIND_LICENSE_FILE}"
  "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
  COPYONLY)
configure_file(
  "${PYISIS_FACADE_SOURCE_INIT_FILE}"
  "${PYISIS_FACADE_BUILD_INIT_FILE}"
  COPYONLY)
configure_file(
  "${PYISIS_FACADE_SOURCE_RUNTIME_FILE}"
  "${PYISIS_FACADE_BUILD_RUNTIME_FILE}"
  COPYONLY)
configure_file(
  "${ISIS_PYBIND_LICENSE_FILE}"
  "${PYISIS_FACADE_BUILD_LICENSE_FILE}"
  COPYONLY)

add_custom_command(
  OUTPUT
    "${ISIS_PYBIND_BUILD_INIT_FILE}"
    "${ISIS_PYBIND_BUILD_APP_RUNNER_FILE}"
    "${ISIS_PYBIND_BUILD_CSV2TABLE_FILE}"
    "${ISIS_PYBIND_BUILD_INFO_FILE}"
    "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
    "${PYISIS_FACADE_BUILD_INIT_FILE}"
    "${PYISIS_FACADE_BUILD_RUNTIME_FILE}"
    "${PYISIS_FACADE_BUILD_LICENSE_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${ISIS_PYBIND_BUILD_PACKAGE_DIR}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${PYISIS_FACADE_BUILD_PACKAGE_DIR}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_SOURCE_INIT_FILE}"
          "${ISIS_PYBIND_BUILD_INIT_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_SOURCE_APP_RUNNER_FILE}"
          "${ISIS_PYBIND_BUILD_APP_RUNNER_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_SOURCE_CSV2TABLE_FILE}"
          "${ISIS_PYBIND_BUILD_CSV2TABLE_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_LICENSE_FILE}"
          "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${PYISIS_FACADE_SOURCE_INIT_FILE}"
          "${PYISIS_FACADE_BUILD_INIT_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${PYISIS_FACADE_SOURCE_RUNTIME_FILE}"
          "${PYISIS_FACADE_BUILD_RUNTIME_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_LICENSE_FILE}"
          "${PYISIS_FACADE_BUILD_LICENSE_FILE}"
  DEPENDS
    "${ISIS_PYBIND_SOURCE_INIT_FILE}"
    "${ISIS_PYBIND_SOURCE_APP_RUNNER_FILE}"
    "${ISIS_PYBIND_SOURCE_CSV2TABLE_FILE}"
    "${ISIS_PYBIND_SOURCE_BUILD_INFO_FILE}"
    "${PYISIS_FACADE_SOURCE_INIT_FILE}"
    "${PYISIS_FACADE_SOURCE_RUNTIME_FILE}"
    "${ISIS_PYBIND_LICENSE_FILE}"
  COMMENT "Syncing Python package files into build/python"
  VERBATIM)

add_custom_target(sync_python_package_files
  DEPENDS
    "${ISIS_PYBIND_BUILD_INIT_FILE}"
    "${ISIS_PYBIND_BUILD_APP_RUNNER_FILE}"
    "${ISIS_PYBIND_BUILD_CSV2TABLE_FILE}"
    "${ISIS_PYBIND_BUILD_INFO_FILE}"
    "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
    "${PYISIS_FACADE_BUILD_INIT_FILE}"
    "${PYISIS_FACADE_BUILD_RUNTIME_FILE}"
    "${PYISIS_FACADE_BUILD_LICENSE_FILE}")

pybind11_add_module(_isis_core
  src/module.cpp
  src/bind_sensor.cpp
  src/bind_camera.cpp
  src/bind_camera_maps.cpp
  src/bind_camera_hierarchy.cpp
  src/bind_statistics.cpp
  src/bind_low_level_cube_io.cpp
  src/bind_high_level_cube_io.cpp
  src/control/bind_control_core.cpp
  src/control/bind_interest_operator_factory.cpp
  src/control/bind_bundle_advanced.cpp
  src/base/bind_base_support.cpp
  src/base/bind_base_geometry.cpp
  src/base/bind_base_ground_map.cpp
  src/base/bind_base_surface.cpp
  src/base/bind_base_photometry.cpp
  src/base/bind_base_pvl.cpp
  src/base/bind_base_projection.cpp
  src/base/bind_base_projection_types.cpp
  src/base/bind_base_shape.cpp
  src/base/bind_base_target.cpp
  src/base/bind_base_shape_support.cpp
  src/base/bind_base_math.cpp
  src/base/bind_base_utility.cpp
  src/base/bind_base_pds_io.cpp
  src/base/bind_base_pattern.cpp
  src/base/bind_auto_reg_factory.cpp
  src/base/bind_base_filters.cpp
  src/base/bind_base_image_polygon.cpp
  src/base/bind_base_polygon_seeder.cpp
  src/base/bind_base_image_overlap.cpp
  src/mission/bind_mission_cameras.cpp
  src/mgs/bind_mgs_utilities.cpp
  src/lro/bind_lro_utilities.cpp
  src/bind_mro_hical.cpp
  src/bind_spice_navigation.cpp
  src/bind_isis10.cpp
  src/bind_camera_factory.cpp)

if(NOT WIN32)
  target_compile_definitions(_isis_core PRIVATE _GNU_SOURCE)
endif()

if(EXISTS "${ISIS_INCLUDE_DIR}/IEndian.h")
  target_compile_definitions(_isis_core PRIVATE PYISIS_ISIS10_API=1)
endif()

target_compile_definitions(_isis_core PRIVATE
  PYISIS_COMPILED_ISIS_VERSION="${PYISIS_ISIS_VERSION}"
  PYISIS_COMPILED_ISIS_VERSION_MAJOR=${PYISIS_ISIS_VERSION_MAJOR})

if(EXISTS "${ISIS_INCLUDE_DIR}/JP2Error.h")
  target_compile_definitions(_isis_core PRIVATE PYISIS_HAS_JP2_ERROR=1)
endif()

if(PYISIS_HAS_EMBREE_SHAPE_MODEL)
  target_compile_definitions(_isis_core PRIVATE PYISIS_HAS_EMBREE_SHAPE_MODEL=1)
endif()

if(MSVC AND PYISIS_PCL_INCLUDE_DIR)
  # Match the 32-byte Eigen alignment used by conda-forge's Windows PCL build
  # without requiring AVX instructions from every wheel consumer.
  target_compile_definitions(_isis_core PRIVATE EIGEN_MAX_ALIGN_BYTES=32)
endif()

if(MSVC)
  # Windows SDK headers must be parsed before CSPICE defines its VOID macro.
  target_compile_options(_isis_core PRIVATE
    "/FI${CMAKE_CURRENT_SOURCE_DIR}/ports/windows/pybind_msvc_compat.h")
endif()

if(NOT MSVC)
  set_source_files_properties(
    src/base/bind_base_shape.cpp
    PROPERTIES COMPILE_OPTIONS "-fpermissive")

  set_source_files_properties(
    src/base/bind_base_shape_support.cpp
    PROPERTIES COMPILE_OPTIONS "-fpermissive")
endif()

target_include_directories(_isis_core
  PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${ISIS_INCLUDE_DIR}"
    ${ISIS_DEP_INCLUDE_SEARCH_DIRS}
    ${ISIS_DEP_SUBDIR_INCLUDE_DIRS}
    ${ISIS_OPTIONAL_INCLUDE_DIRS}
    "${CMAKE_CURRENT_SOURCE_DIR}/reference/SensorUtilities/include")

target_link_libraries(_isis_core
  PRIVATE
    "${ISIS_CORE_LIBRARY}"
    ${ISIS_EXTRA_MODULE_LIBS}
    ${ISIS_EXTRA_CAMERA_LIBS}
    ${ISIS_EXTRA_PROJECTION_LIBS}
    ${ISIS_RUNTIME_DEP_LIBS}
    ${BULLET_RUNTIME_LIBS}
    ${PYISIS_QT_TARGETS}
    Python3::Module)

set_target_properties(_isis_core PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
  LIBRARY_OUTPUT_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}"
  RUNTIME_OUTPUT_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}")

if(NOT WIN32)
  set(PYISIS_LINUX_WHEEL_RPATH
    "$ORIGIN/../pyisis_runtime/vendor/isis/lib")
  if(SKBUILD)
    set(PYISIS_INSTALL_RPATH "${PYISIS_LINUX_WHEEL_RPATH}")
  else()
    set(PYISIS_INSTALL_RPATH "${ISIS_LIBRARY_DIR}")
  endif()
  set_target_properties(_isis_core PROPERTIES
    BUILD_RPATH "${ISIS_LIBRARY_DIR}"
    INSTALL_RPATH "${PYISIS_INSTALL_RPATH}")
endif()

add_dependencies(_isis_core sync_python_package_files)

if(PYISIS_BUILD_BENCHMARKS)
  add_executable(isis_cpp_benchmark
    tools/benchmarks/isis_cpp_benchmark.cpp)

  if(NOT WIN32)
    target_compile_definitions(isis_cpp_benchmark PRIVATE _GNU_SOURCE)
  endif()

  target_include_directories(isis_cpp_benchmark
    PRIVATE
      "${ISIS_INCLUDE_DIR}"
      ${ISIS_DEP_INCLUDE_SEARCH_DIRS}
      ${ISIS_DEP_SUBDIR_INCLUDE_DIRS}
      ${ISIS_OPTIONAL_INCLUDE_DIRS})

  target_link_libraries(isis_cpp_benchmark
    PRIVATE
      "${ISIS_CORE_LIBRARY}"
      ${ISIS_EXTRA_MODULE_LIBS}
      ${ISIS_EXTRA_CAMERA_LIBS}
      ${ISIS_EXTRA_PROJECTION_LIBS}
      ${ISIS_RUNTIME_DEP_LIBS}
      ${BULLET_RUNTIME_LIBS}
      ${PYISIS_QT_TARGETS})

  set_target_properties(isis_cpp_benchmark PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tools/benchmarks")

  if(NOT WIN32)
    set_target_properties(isis_cpp_benchmark PROPERTIES
      BUILD_RPATH "${ISIS_LIBRARY_DIR}"
      INSTALL_RPATH "${ISIS_LIBRARY_DIR}")
  endif()
endif()

install(TARGETS _isis_core
        LIBRARY DESTINATION "${PYISIS_INSTALL_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}"
        RUNTIME DESTINATION "${PYISIS_INSTALL_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/__init__.py"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES
        "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/_app_runner.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/_csv2table.py"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES "${ISIS_PYBIND_BUILD_INFO_FILE}"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES "${ISIS_PYBIND_LICENSE_FILE}"
  DESTINATION "${PYISIS_INSTALL_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
if(NOT PYISIS_INSTALL_SITEARCH STREQUAL PYISIS_INSTALL_SITELIB)
  install(FILES "${ISIS_PYBIND_LICENSE_FILE}"
    DESTINATION "${PYISIS_INSTALL_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}")
endif()
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/python/${PYISIS_FACADE_PACKAGE_NAME}/__init__.py"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${PYISIS_FACADE_PACKAGE_NAME}")
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/python/${PYISIS_FACADE_PACKAGE_NAME}/_runtime.py"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${PYISIS_FACADE_PACKAGE_NAME}")
install(FILES "${ISIS_PYBIND_LICENSE_FILE}"
        DESTINATION "${PYISIS_INSTALL_SITELIB}/${PYISIS_FACADE_PACKAGE_NAME}")

add_test(
  NAME python-unit-tests
  COMMAND "${Python3_EXECUTABLE}" -m unittest discover
    -s "${CMAKE_CURRENT_SOURCE_DIR}/tests/unitTest"
    -p "*_unit_test.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")

if(WIN32)
  set(_test_path "${ISIS_RUNTIME_DIR}")
  if(DEFINED ENV{PATH} AND NOT "$ENV{PATH}" STREQUAL "")
    set(_test_path "${_test_path};$ENV{PATH}")
  endif()
  string(REPLACE ";" "\\;" _test_path_escaped "${_test_path}")
  set(_python_test_environment
      "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
      "ISIS_PYBIND_BUILD_DIR=${CMAKE_CURRENT_BINARY_DIR}/python"
      "PATH=${_test_path_escaped}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
else()
  set(_test_ld_library_path "${ISIS_LIBRARY_DIR}")
  if(DEFINED ENV{LD_LIBRARY_PATH} AND NOT "$ENV{LD_LIBRARY_PATH}" STREQUAL "")
    set(_test_ld_library_path "${_test_ld_library_path}:$ENV{LD_LIBRARY_PATH}")
  endif()
  set(_python_test_environment
      "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
      "ISIS_PYBIND_BUILD_DIR=${CMAKE_CURRENT_BINARY_DIR}/python"
      "LD_LIBRARY_PATH=${_test_ld_library_path}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
endif()

set_tests_properties(python-unit-tests PROPERTIES
  ENVIRONMENT "${_python_test_environment}")

message(STATUS "Using external ISIS prefix: ${ISIS_PREFIX}")
message(STATUS "Using ISIS version: ${PYISIS_ISIS_VERSION}")
message(STATUS "Using PyISIS package version: ${PYISIS_PACKAGE_VERSION}")
message(STATUS "Using ISIS include dir: ${ISIS_INCLUDE_DIR}")
message(STATUS "Using ISIS dependency include dir: ${ISIS_DEP_INCLUDE_DIR}")
message(STATUS "Using ISIS dependency include dirs: ${ISIS_DEP_INCLUDE_SEARCH_DIRS}")
message(STATUS "Using ISIS library dir: ${ISIS_LIBRARY_DIR}")
message(STATUS "Using ISIS dependency library dirs: ${ISIS_DEP_LIBRARY_SEARCH_DIRS}")
message(STATUS "Using ISIS runtime dir: ${ISIS_RUNTIME_DIR}")
message(STATUS "Using ISIS core library: ${ISIS_CORE_LIBRARY}")
message(STATUS "Using extra camera libs: ${ISIS_EXTRA_CAMERA_LIBS}")
message(STATUS "Exclude ASP/VW camera libs: ${ISIS_EXCLUDE_ASP_VW_CAMERA_LIBS}")
message(STATUS "Using extra ISIS module libs: ${ISIS_EXTRA_MODULE_LIBS}")
message(STATUS "Using extra projection libs: ${ISIS_EXTRA_PROJECTION_LIBS}")
message(STATUS "Using ISIS runtime dependency libs: ${ISIS_RUNTIME_DEP_LIBS}")
message(STATUS "Using Bullet runtime libs: ${BULLET_RUNTIME_LIBS}")
message(STATUS "Using PCL include dirs: ${PCL_INCLUDE_DIRS}")
message(STATUS "Using Embree shape bindings: ${PYISIS_HAS_EMBREE_SHAPE_MODEL}")
message(STATUS "Using Eigen include dir: ${EIGEN3_INCLUDE_DIR}")
message(STATUS "Using optional include dirs: ${ISIS_OPTIONAL_INCLUDE_DIRS}")
message(STATUS "Using Qt package: ${PYISIS_QT_PACKAGE}")
message(STATUS "Using Qt config dir: ${${PYISIS_QT_PACKAGE}_DIR}")
message(STATUS "Using pybind11 config dir: ${pybind11_DIR}")
if(DEFINED CMAKE_CXX_COMPILER_LAUNCHER AND NOT CMAKE_CXX_COMPILER_LAUNCHER STREQUAL "")
  message(STATUS "Using C++ compiler launcher: ${CMAKE_CXX_COMPILER_LAUNCHER}")
else()
  message(STATUS "No C++ compiler launcher configured")
endif()
