// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <pybind11/pybind11.h>

namespace py = pybind11;

void bind_control_core(py::module_ &m);
// Temporarily disabled due to complex dependencies - will be re-enabled once resolved
// void bind_bundle_advanced(py::module_ &m);
void bind_sensor(py::module_ &m);
void bind_camera(py::module_ &m);
void bind_camera_maps(py::module_ &m);
void bind_camera_hierarchy(py::module_ &m);
void bind_cube(py::module_ &m);
void bind_base_support(py::module_ &m);
void bind_base_geometry(py::module_ &m);
void bind_base_ground_map(py::module_ &m);
void bind_base_surface(py::module_ &m);
void bind_base_pvl(py::module_ &m);
void bind_base_projection(py::module_ &m);
void bind_base_projection_types(py::module_ &m);
void bind_base_shape(py::module_ &m);
void bind_base_target(py::module_ &m);
void bind_base_shape_support(py::module_ &m);
void bind_base_math(py::module_ &m);
void bind_base_utility(py::module_ &m);
void bind_base_pattern(py::module_ &m);
void bind_base_filters(py::module_ &m);
void bind_mission_cameras(py::module_ &m);
void bind_camera_factory(py::module_ &m);
void bind_statistics(py::module_ &m);
void bind_low_level_cube_io(py::module_ &m);
void bind_high_level_cube_io(py::module_ &m);

PYBIND11_MODULE(_isis_core, m) {
  m.doc() = "Standalone pybind11 bindings for selected ISIS C++ APIs";

  bind_sensor(m);
  bind_camera(m);
  bind_camera_maps(m);
  bind_camera_hierarchy(m);
  bind_cube(m);
  bind_base_support(m);
  bind_base_geometry(m);
  bind_base_ground_map(m);
  bind_base_surface(m);
  bind_base_pvl(m);
  bind_base_projection(m);
  bind_base_projection_types(m);
  bind_base_shape(m);
  bind_base_target(m);
  bind_base_shape_support(m);
  bind_base_math(m);
  bind_base_utility(m);
  bind_base_pattern(m);
  bind_base_filters(m);
  bind_mission_cameras(m);
  bind_camera_factory(m);
  bind_statistics(m);
  bind_low_level_cube_io(m);
  bind_high_level_cube_io(m);
  bind_control_core(m);
  // Temporarily disabled due to complex dependencies - will be re-enabled once resolved
  // bind_bundle_advanced(m);
}
