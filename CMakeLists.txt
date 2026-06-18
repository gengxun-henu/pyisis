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
find_package(pybind11 CONFIG REQUIRED)

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

if(WIN32)
  pyisis_first_existing_path(_qt5_cmake_root
    "${ISIS_PREFIX}/Library/lib/cmake"
    "${ISIS_PREFIX}/lib/cmake")
else()
  set(_qt5_cmake_root "${ISIS_PREFIX}/lib/cmake")
endif()
set(_qt5_config_dir "${_qt5_cmake_root}/Qt5")
if(EXISTS "${_qt5_config_dir}/Qt5Config.cmake")
  set(Qt5_DIR "${_qt5_config_dir}" CACHE PATH
    "Qt5 config directory preferred from the active ISIS/conda prefix" FORCE)
  set(Qt5Core_DIR "${_qt5_cmake_root}/Qt5Core" CACHE PATH
    "Qt5Core config directory preferred from the active ISIS/conda prefix" FORCE)
  set(Qt5Concurrent_DIR "${_qt5_cmake_root}/Qt5Concurrent" CACHE PATH
    "Qt5Concurrent config directory preferred from the active ISIS/conda prefix" FORCE)
  set(Qt5Xml_DIR "${_qt5_cmake_root}/Qt5Xml" CACHE PATH
    "Qt5Xml config directory preferred from the active ISIS/conda prefix" FORCE)
  set(Qt5Widgets_DIR "${_qt5_cmake_root}/Qt5Widgets" CACHE PATH
    "Qt5Widgets config directory preferred from the active ISIS/conda prefix" FORCE)
  set(Qt5Gui_DIR "${_qt5_cmake_root}/Qt5Gui" CACHE PATH
    "Qt5Gui config directory preferred from the active ISIS/conda prefix" FORCE)
endif()

find_package(Qt5 CONFIG REQUIRED COMPONENTS Core Concurrent Xml Widgets)

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
  find_library(BULLET_LIB_${bullet_lib_name}
               NAMES ${bullet_lib_name}
               PATHS ${ISIS_DEP_LIBRARY_SEARCH_DIRS}
               NO_DEFAULT_PATH)
  if(BULLET_LIB_${bullet_lib_name})
    list(APPEND BULLET_RUNTIME_LIBS "${BULLET_LIB_${bullet_lib_name}}")
  endif()
endforeach()
list(REMOVE_DUPLICATES BULLET_RUNTIME_LIBS)

set(ISIS_RUNTIME_DEP_LIB_NAMES
    ale
    csmapi
    geos
    geos_c
    gsl
    gslcblas
    libprotobuf
    libprotobuf-lite
    xerces-c_3)

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
set(ISIS_PYBIND_BUILD_INIT_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/__init__.py")
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
    "${PYISIS_FACADE_SOURCE_INIT_FILE}"
    "${PYISIS_FACADE_SOURCE_RUNTIME_FILE}"
    "${ISIS_PYBIND_LICENSE_FILE}"
  COMMENT "Syncing Python package files into build/python"
  VERBATIM)

add_custom_target(sync_python_package_files
  DEPENDS
    "${ISIS_PYBIND_BUILD_INIT_FILE}"
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
  src/bind_camera_factory.cpp)

if(NOT WIN32)
  target_compile_definitions(_isis_core PRIVATE _GNU_SOURCE)
endif()

if(PYISIS_HAS_EMBREE_SHAPE_MODEL)
  target_compile_definitions(_isis_core PRIVATE PYISIS_HAS_EMBREE_SHAPE_MODEL=1)
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
    ${Qt5Core_INCLUDE_DIRS}
    ${Qt5Concurrent_INCLUDE_DIRS}
    ${Qt5Xml_INCLUDE_DIRS}
    ${Qt5Widgets_INCLUDE_DIRS}
    "${CMAKE_CURRENT_SOURCE_DIR}/reference/SensorUtilities/include")

target_link_libraries(_isis_core
  PRIVATE
    "${ISIS_CORE_LIBRARY}"
    ${ISIS_EXTRA_MODULE_LIBS}
    ${ISIS_EXTRA_CAMERA_LIBS}
    ${ISIS_EXTRA_PROJECTION_LIBS}
    ${ISIS_RUNTIME_DEP_LIBS}
    ${BULLET_RUNTIME_LIBS}
    Qt5::Core
    Qt5::Concurrent
    Qt5::Xml
    Qt5::Widgets
    Python3::Module)

set_target_properties(_isis_core PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
  LIBRARY_OUTPUT_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}"
  RUNTIME_OUTPUT_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}")

if(NOT WIN32)
  set_target_properties(_isis_core PROPERTIES
    BUILD_RPATH "${ISIS_LIBRARY_DIR}"
    INSTALL_RPATH "${ISIS_LIBRARY_DIR}")
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
      ${ISIS_OPTIONAL_INCLUDE_DIRS}
      ${Qt5Core_INCLUDE_DIRS})

  target_link_libraries(isis_cpp_benchmark
    PRIVATE
      "${ISIS_CORE_LIBRARY}"
      ${ISIS_EXTRA_MODULE_LIBS}
      ${ISIS_EXTRA_CAMERA_LIBS}
      ${ISIS_EXTRA_PROJECTION_LIBS}
      ${ISIS_RUNTIME_DEP_LIBS}
      ${BULLET_RUNTIME_LIBS}
      Qt5::Core)

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
      "PATH=${_test_path_escaped}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
else()
  set(_test_ld_library_path "${ISIS_LIBRARY_DIR}")
  if(DEFINED ENV{LD_LIBRARY_PATH} AND NOT "$ENV{LD_LIBRARY_PATH}" STREQUAL "")
    set(_test_ld_library_path "${_test_ld_library_path}:$ENV{LD_LIBRARY_PATH}")
  endif()
  set(_python_test_environment
      "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
      "LD_LIBRARY_PATH=${_test_ld_library_path}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
endif()

set_tests_properties(python-unit-tests PROPERTIES
  ENVIRONMENT "${_python_test_environment}")

message(STATUS "Using external ISIS prefix: ${ISIS_PREFIX}")
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
message(STATUS "Using Qt5 config dir: ${Qt5_DIR}")
if(DEFINED CMAKE_CXX_COMPILER_LAUNCHER AND NOT CMAKE_CXX_COMPILER_LAUNCHER STREQUAL "")
  message(STATUS "Using C++ compiler launcher: ${CMAKE_CXX_COMPILER_LAUNCHER}")
else()
  message(STATUS "No C++ compiler launcher configured")
endif()
