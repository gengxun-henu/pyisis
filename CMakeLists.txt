cmake_minimum_required(VERSION 3.18)

if(NOT DEFINED CMAKE_CXX_COMPILER AND DEFINED ENV{CONDA_PREFIX})
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

find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Core Concurrent Xml Widgets)

set(ISIS_PREFIX "$ENV{ISIS_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment")
if(NOT ISIS_PREFIX AND DEFINED ENV{CONDA_PREFIX})
  if(EXISTS "$ENV{CONDA_PREFIX}/include/isis" AND EXISTS "$ENV{CONDA_PREFIX}/lib/libisis.so")
    set(ISIS_PREFIX "$ENV{CONDA_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment" FORCE)
  endif()
endif()

if(NOT ISIS_PREFIX)
  message(FATAL_ERROR "ISIS_PREFIX is not set. Point it to the external ISIS installation (for example the asp360_new conda environment).")
endif()

set(ISIS_INCLUDE_DIR "${ISIS_PREFIX}/include/isis" CACHE PATH "Directory containing ISIS headers")
set(ISIS_DEP_INCLUDE_DIR "${ISIS_PREFIX}/include" CACHE PATH "Directory containing external ISIS dependencies such as CSPICE and Qt headers")
set(ISIS_LIBRARY_DIR "${ISIS_PREFIX}/lib" CACHE PATH "Directory containing ISIS shared libraries")
set(ISIS_CORE_LIBRARY "${ISIS_LIBRARY_DIR}/libisis.so" CACHE FILEPATH "Path to libisis shared library")
set(ISIS_PLUGIN_FILE "${ISIS_LIBRARY_DIR}/Camera.plugin" CACHE FILEPATH "Path to Camera.plugin")
set(ISIS_CAMERA_LIBS ""
    CACHE STRING
    "Semicolon-separated extra ISIS camera libraries to link (empty means auto-detect a minimal set)")

foreach(required_path IN ITEMS ISIS_INCLUDE_DIR ISIS_DEP_INCLUDE_DIR ISIS_LIBRARY_DIR ISIS_CORE_LIBRARY ISIS_PLUGIN_FILE)
  if(NOT EXISTS "${${required_path}}")
    message(FATAL_ERROR "${required_path} does not exist: ${${required_path}}")
  endif()
endforeach()

if(ISIS_CAMERA_LIBS)
  set(ISIS_EXTRA_CAMERA_LIBS ${ISIS_CAMERA_LIBS})
else()
  file(GLOB ISIS_EXTRA_CAMERA_LIBS
       "${ISIS_LIBRARY_DIR}/lib*Camera.so"
       "${ISIS_LIBRARY_DIR}/libMiniRF.so")
  list(REMOVE_DUPLICATES ISIS_EXTRA_CAMERA_LIBS)
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
               PATHS "${ISIS_LIBRARY_DIR}"
               NO_DEFAULT_PATH)
  if(BULLET_LIB_${bullet_lib_name})
    list(APPEND BULLET_RUNTIME_LIBS "${BULLET_LIB_${bullet_lib_name}}")
  endif()
endforeach()
list(REMOVE_DUPLICATES BULLET_RUNTIME_LIBS)

file(GLOB PCL_INCLUDE_DIRS "${ISIS_DEP_INCLUDE_DIR}/pcl-*")
list(REMOVE_DUPLICATES PCL_INCLUDE_DIRS)

find_path(EIGEN3_INCLUDE_DIR
          NAMES Eigen/StdVector
          PATHS "${ISIS_DEP_INCLUDE_DIR}/eigen3" "${ISIS_DEP_INCLUDE_DIR}"
          NO_DEFAULT_PATH)

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

set(ISIS_PYBIND_PACKAGE_NAME isis_pybind)
set(ISIS_PYBIND_BUILD_PACKAGE_DIR "${CMAKE_CURRENT_BINARY_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}")
set(ISIS_PYBIND_LICENSE_FILE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
set(ISIS_PYBIND_SOURCE_INIT_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/__init__.py")
set(ISIS_PYBIND_BUILD_INIT_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/__init__.py")
set(ISIS_PYBIND_BUILD_LICENSE_FILE
    "${ISIS_PYBIND_BUILD_PACKAGE_DIR}/LICENSE")
file(MAKE_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}")
configure_file(
  "${ISIS_PYBIND_SOURCE_INIT_FILE}"
  "${ISIS_PYBIND_BUILD_INIT_FILE}"
  COPYONLY)
configure_file(
  "${ISIS_PYBIND_LICENSE_FILE}"
  "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
  COPYONLY)

add_custom_command(
  OUTPUT "${ISIS_PYBIND_BUILD_INIT_FILE}" "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${ISIS_PYBIND_BUILD_PACKAGE_DIR}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_SOURCE_INIT_FILE}"
          "${ISIS_PYBIND_BUILD_INIT_FILE}"
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${ISIS_PYBIND_LICENSE_FILE}"
          "${ISIS_PYBIND_BUILD_LICENSE_FILE}"
  DEPENDS "${ISIS_PYBIND_SOURCE_INIT_FILE}" "${ISIS_PYBIND_LICENSE_FILE}"
  COMMENT "Syncing Python package files into build/python/${ISIS_PYBIND_PACKAGE_NAME}"
  VERBATIM)

add_custom_target(sync_python_package_files
  DEPENDS "${ISIS_PYBIND_BUILD_INIT_FILE}" "${ISIS_PYBIND_BUILD_LICENSE_FILE}")

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
  # Temporarily disabled due to complex dependencies - will be re-enabled once resolved
  # src/control/bind_bundle_advanced.cpp
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
  src/base/bind_base_pattern.cpp
  src/base/bind_auto_reg_factory.cpp
  src/base/bind_base_filters.cpp
  src/mission/bind_mission_cameras.cpp
  src/mgs/bind_mgs_utilities.cpp
  src/lro/bind_lro_utilities.cpp
  src/bind_mro_hical.cpp
  src/bind_camera_factory.cpp)

target_compile_definitions(_isis_core
  PRIVATE
    _GNU_SOURCE)

set_source_files_properties(
  src/base/bind_base_shape.cpp
  PROPERTIES COMPILE_OPTIONS "-fpermissive")

set_source_files_properties(
  src/base/bind_base_shape_support.cpp
  PROPERTIES COMPILE_OPTIONS "-fpermissive")

target_include_directories(_isis_core
  PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${ISIS_INCLUDE_DIR}"
    "${ISIS_DEP_INCLUDE_DIR}"
    "${ISIS_DEP_INCLUDE_DIR}/csm"
    "${ISIS_DEP_INCLUDE_DIR}/cspice"
    "${ISIS_DEP_INCLUDE_DIR}/bullet"
    "${ISIS_DEP_INCLUDE_DIR}/tnt"
    ${PCL_INCLUDE_DIRS}
    ${EIGEN3_INCLUDE_DIR}
    "${ISIS_DEP_INCLUDE_DIR}/qt"
    "${ISIS_DEP_INCLUDE_DIR}/qt/QtCore"
    ${Qt5Core_INCLUDE_DIRS}
    ${Qt5Concurrent_INCLUDE_DIRS}
    ${Qt5Xml_INCLUDE_DIRS}
    ${Qt5Widgets_INCLUDE_DIRS}
    "${CMAKE_CURRENT_SOURCE_DIR}/reference/SensorUtilities/include")

target_link_libraries(_isis_core
  PRIVATE
    "${ISIS_CORE_LIBRARY}"
    ${ISIS_EXTRA_CAMERA_LIBS}
    ${ISIS_EXTRA_PROJECTION_LIBS}
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
  BUILD_RPATH "${ISIS_LIBRARY_DIR}"
  INSTALL_RPATH "${ISIS_LIBRARY_DIR}")

add_dependencies(_isis_core sync_python_package_files)

install(TARGETS _isis_core LIBRARY DESTINATION "${Python3_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/python/${ISIS_PYBIND_PACKAGE_NAME}/__init__.py"
        DESTINATION "${Python3_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
install(FILES "${ISIS_PYBIND_LICENSE_FILE}"
  DESTINATION "${Python3_SITELIB}/${ISIS_PYBIND_PACKAGE_NAME}")
if(NOT Python3_SITEARCH STREQUAL Python3_SITELIB)
  install(FILES "${ISIS_PYBIND_LICENSE_FILE}"
    DESTINATION "${Python3_SITEARCH}/${ISIS_PYBIND_PACKAGE_NAME}")
endif()

set(_test_ld_library_path "${ISIS_LIBRARY_DIR}")
if(DEFINED ENV{LD_LIBRARY_PATH} AND NOT "$ENV{LD_LIBRARY_PATH}" STREQUAL "")
  set(_test_ld_library_path "${_test_ld_library_path}:$ENV{LD_LIBRARY_PATH}")
endif()

add_test(
  NAME python-unit-tests
  COMMAND "${Python3_EXECUTABLE}" -m unittest discover
    -s "${CMAKE_CURRENT_SOURCE_DIR}/tests/unitTest"
    -p "*_unit_test.py"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")

set_tests_properties(python-unit-tests PROPERTIES
  ENVIRONMENT
    "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
    "LD_LIBRARY_PATH=${_test_ld_library_path}"
    "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")

  
message(STATUS "Using external ISIS prefix: ${ISIS_PREFIX}")
message(STATUS "Using ISIS include dir: ${ISIS_INCLUDE_DIR}")
message(STATUS "Using ISIS dependency include dir: ${ISIS_DEP_INCLUDE_DIR}")
message(STATUS "Using ISIS core library: ${ISIS_CORE_LIBRARY}")
message(STATUS "Using extra camera libs: ${ISIS_EXTRA_CAMERA_LIBS}")
message(STATUS "Using extra projection libs: ${ISIS_EXTRA_PROJECTION_LIBS}")
message(STATUS "Using Bullet runtime libs: ${BULLET_RUNTIME_LIBS}")
message(STATUS "Using PCL include dirs: ${PCL_INCLUDE_DIRS}")
message(STATUS "Using Eigen include dir: ${EIGEN3_INCLUDE_DIR}")
if(DEFINED CMAKE_CXX_COMPILER_LAUNCHER AND NOT CMAKE_CXX_COMPILER_LAUNCHER STREQUAL "")
  message(STATUS "Using C++ compiler launcher: ${CMAKE_CXX_COMPILER_LAUNCHER}")
else()
  message(STATUS "No C++ compiler launcher configured")
endif()
