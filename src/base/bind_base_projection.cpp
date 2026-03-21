// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>
#include <tuple>

#include <pybind11/pybind11.h>

#include "Cube.h"
#include "Displacement.h"
#include "Pvl.h"
#include "Projection.h"
#include "ProjectionFactory.h"
#include "RingPlaneProjection.h"
#include "TProjection.h"
#include "WorldMapper.h"
#include "helpers.h"

namespace py = pybind11;

namespace {
template <typename TProjectionLike>
py::object xyRangeOrNone(TProjectionLike &self) {
  double min_x = 0.0;
  double max_x = 0.0;
  double min_y = 0.0;
  double max_y = 0.0;
  if (!self.XYRange(min_x, max_x, min_y, max_y)) {
    return py::none();
  }
  return py::make_tuple(min_x, max_x, min_y, max_y);
}
}  // namespace

void bind_base_projection(py::module_ &m) {
  py::class_<Isis::WorldMapper> world_mapper(m, "WorldMapper");
  world_mapper
      .def("projection_x", &Isis::WorldMapper::ProjectionX, py::arg("world_x"))
      .def("projection_y", &Isis::WorldMapper::ProjectionY, py::arg("world_y"))
      .def("world_x", &Isis::WorldMapper::WorldX, py::arg("projection_x"))
      .def("world_y", &Isis::WorldMapper::WorldY, py::arg("projection_y"))
      .def("resolution", &Isis::WorldMapper::Resolution);

  py::class_<Isis::PFPixelMapper, Isis::WorldMapper>(m, "PFPixelMapper")
      .def(py::init<double, double, double>(),
           py::arg("pixel_resolution"),
           py::arg("upper_left_x"),
           py::arg("upper_left_y"));

  py::class_<Isis::Projection> projection(m, "Projection");

  py::enum_<Isis::Projection::ProjectionType>(projection, "ProjectionType")
      .value("Triaxial", Isis::Projection::Triaxial)
      .value("RingPlane", Isis::Projection::RingPlane);

  projection
      .def("projection_type", &Isis::Projection::projectionType)
      .def("is_sky", &Isis::Projection::IsSky)
      .def("name", [](const Isis::Projection &self) { return qStringToStdString(self.Name()); })
      .def("local_radius", py::overload_cast<>(&Isis::Projection::LocalRadius, py::const_))
      .def("version", [](const Isis::Projection &self) { return qStringToStdString(self.Version()); })
      .def("is_equatorial_cylindrical", &Isis::Projection::IsEquatorialCylindrical)
      .def("has_ground_range", &Isis::Projection::HasGroundRange)
      .def("rotation", &Isis::Projection::Rotation)
      .def("set_ground", &Isis::Projection::SetGround, py::arg("coord1"), py::arg("coord2"))
      .def("set_coordinate", &Isis::Projection::SetCoordinate, py::arg("x"), py::arg("y"))
      .def("is_good", &Isis::Projection::IsGood)
      .def("x_coord", &Isis::Projection::XCoord)
      .def("y_coord", &Isis::Projection::YCoord)
      .def("set_universal_ground", &Isis::Projection::SetUniversalGround, py::arg("coord1"), py::arg("coord2"))
      .def("set_unbound_universal_ground", &Isis::Projection::SetUnboundUniversalGround, py::arg("coord1"), py::arg("coord2"))
      .def("set_world", &Isis::Projection::SetWorld, py::arg("x"), py::arg("y"))
      .def("world_x", &Isis::Projection::WorldX)
      .def("world_y", &Isis::Projection::WorldY)
      .def("to_world_x", &Isis::Projection::ToWorldX, py::arg("projection_x"))
      .def("to_world_y", &Isis::Projection::ToWorldY, py::arg("projection_y"))
      .def("to_projection_x", &Isis::Projection::ToProjectionX, py::arg("world_x"))
      .def("to_projection_y", &Isis::Projection::ToProjectionY, py::arg("world_y"))
      .def("resolution", &Isis::Projection::Resolution)
      .def("scale", &Isis::Projection::Scale)
      .def("xy_range", &xyRangeOrNone<Isis::Projection>)
      .def("set_upper_left_corner", &Isis::Projection::SetUpperLeftCorner, py::arg("x"), py::arg("y"))
      .def("mapping", &Isis::Projection::Mapping)
      .def_static("to_hours", &Isis::Projection::ToHours, py::arg("angle"))
      .def_static("to_dms", [](double angle) { return qStringToStdString(Isis::Projection::ToDMS(angle)); }, py::arg("angle"))
      .def_static("to_hms", [](double angle) { return qStringToStdString(Isis::Projection::ToHMS(angle)); }, py::arg("angle"))
      .def("__repr__", [](const Isis::Projection &self) {
        return "Projection('" + qStringToStdString(self.Name()) + "')";
      });

  py::class_<Isis::TProjection, Isis::Projection> tprojection(m, "TProjection");

  py::enum_<Isis::TProjection::LatitudeType>(tprojection, "LatitudeType")
      .value("Planetocentric", Isis::TProjection::Planetocentric)
      .value("Planetographic", Isis::TProjection::Planetographic);

  py::enum_<Isis::TProjection::LongitudeDirection>(tprojection, "LongitudeDirection")
      .value("PositiveEast", Isis::TProjection::PositiveEast)
      .value("PositiveWest", Isis::TProjection::PositiveWest);

  tprojection
      .def("equatorial_radius", &Isis::TProjection::EquatorialRadius)
      .def("polar_radius", &Isis::TProjection::PolarRadius)
      .def("eccentricity", &Isis::TProjection::Eccentricity)
      .def("local_radius_at", py::overload_cast<double>(&Isis::TProjection::LocalRadius, py::const_), py::arg("latitude"))
      .def("true_scale_latitude", &Isis::TProjection::TrueScaleLatitude)
      .def("is_planetocentric", &Isis::TProjection::IsPlanetocentric)
      .def("is_planetographic", &Isis::TProjection::IsPlanetographic)
      .def("latitude_type_string", [](const Isis::TProjection &self) { return qStringToStdString(self.LatitudeTypeString()); })
      .def("to_planetocentric", py::overload_cast<const double>(&Isis::TProjection::ToPlanetocentric, py::const_), py::arg("latitude"))
      .def("to_planetographic", py::overload_cast<const double>(&Isis::TProjection::ToPlanetographic, py::const_), py::arg("latitude"))
      .def("is_positive_east", &Isis::TProjection::IsPositiveEast)
      .def("is_positive_west", &Isis::TProjection::IsPositiveWest)
      .def("longitude_direction_string", [](const Isis::TProjection &self) { return qStringToStdString(self.LongitudeDirectionString()); })
      .def("has_180_domain", &Isis::TProjection::Has180Domain)
      .def("has_360_domain", &Isis::TProjection::Has360Domain)
      .def("longitude_domain_string", [](const Isis::TProjection &self) { return qStringToStdString(self.LongitudeDomainString()); })
      .def("minimum_latitude", &Isis::TProjection::MinimumLatitude)
      .def("maximum_latitude", &Isis::TProjection::MaximumLatitude)
      .def("minimum_longitude", &Isis::TProjection::MinimumLongitude)
      .def("maximum_longitude", &Isis::TProjection::MaximumLongitude)
      .def("latitude", &Isis::TProjection::Latitude)
      .def("longitude", &Isis::TProjection::Longitude)
      .def("universal_latitude", &Isis::TProjection::UniversalLatitude)
      .def("universal_longitude", &Isis::TProjection::UniversalLongitude)
      .def("mapping_latitudes", &Isis::TProjection::MappingLatitudes)
      .def("mapping_longitudes", &Isis::TProjection::MappingLongitudes)
      .def_static("to_planetocentric_static",
                  [](double latitude, double equatorial_radius, double polar_radius) {
                    return Isis::TProjection::ToPlanetocentric(latitude, equatorial_radius, polar_radius);
                  },
                  py::arg("latitude"),
                  py::arg("equatorial_radius"),
                  py::arg("polar_radius"))
      .def_static("to_planetographic_static",
                  [](double latitude, double equatorial_radius, double polar_radius) {
                    return Isis::TProjection::ToPlanetographic(latitude, equatorial_radius, polar_radius);
                  },
                  py::arg("latitude"),
                  py::arg("equatorial_radius"),
                  py::arg("polar_radius"))
      .def_static("to_positive_east", &Isis::TProjection::ToPositiveEast, py::arg("longitude"), py::arg("domain"))
      .def_static("to_positive_west", &Isis::TProjection::ToPositiveWest, py::arg("longitude"), py::arg("domain"))
      .def_static("to_180_domain", &Isis::TProjection::To180Domain, py::arg("longitude"))
      .def_static("to_360_domain", &Isis::TProjection::To360Domain, py::arg("longitude"));

  py::class_<Isis::RingPlaneProjection, Isis::Projection> ring_projection(m, "RingPlaneProjection");

  py::enum_<Isis::RingPlaneProjection::RingLongitudeDirection>(ring_projection, "RingLongitudeDirection")
      .value("Clockwise", Isis::RingPlaneProjection::Clockwise)
      .value("CounterClockwise", Isis::RingPlaneProjection::CounterClockwise);

  ring_projection
      .def("true_scale_ring_radius", &Isis::RingPlaneProjection::TrueScaleRingRadius)
      .def("is_clockwise", &Isis::RingPlaneProjection::IsClockwise)
      .def("is_counter_clockwise", &Isis::RingPlaneProjection::IsCounterClockwise)
      .def("ring_longitude_direction_string", &Isis::RingPlaneProjection::RingLongitudeDirectionString)
      .def("has_180_domain", &Isis::RingPlaneProjection::Has180Domain)
      .def("has_360_domain", &Isis::RingPlaneProjection::Has360Domain)
      .def("ring_longitude_domain_string", &Isis::RingPlaneProjection::RingLongitudeDomainString)
      .def("minimum_ring_radius", &Isis::RingPlaneProjection::MinimumRingRadius)
      .def("maximum_ring_radius", &Isis::RingPlaneProjection::MaximumRingRadius)
      .def("minimum_ring_longitude", &Isis::RingPlaneProjection::MinimumRingLongitude)
      .def("maximum_ring_longitude", &Isis::RingPlaneProjection::MaximumRingLongitude)
      .def("ring_radius", &Isis::RingPlaneProjection::RingRadius)
      .def("ring_longitude", &Isis::RingPlaneProjection::RingLongitude)
      .def("universal_ring_radius", &Isis::RingPlaneProjection::UniversalRingRadius)
      .def("universal_ring_longitude", &Isis::RingPlaneProjection::UniversalRingLongitude)
      .def("mapping_ring_radii", &Isis::RingPlaneProjection::MappingRingRadii)
      .def("mapping_ring_longitudes", &Isis::RingPlaneProjection::MappingRingLongitudes)
      .def_static("to_clockwise", &Isis::RingPlaneProjection::ToClockwise, py::arg("ring_longitude"), py::arg("domain"))
      .def_static("to_counter_clockwise", &Isis::RingPlaneProjection::ToCounterClockwise, py::arg("ring_longitude"), py::arg("domain"))
      .def_static("to_180_domain", &Isis::RingPlaneProjection::To180Domain, py::arg("ring_longitude"))
      .def_static("to_360_domain", &Isis::RingPlaneProjection::To360Domain, py::arg("ring_longitude"));

  py::class_<Isis::ProjectionFactory, std::unique_ptr<Isis::ProjectionFactory, py::nodelete>>(m, "ProjectionFactory")
      .def_static("create",
                  [](Isis::Pvl &label, bool allow_defaults) { return Isis::ProjectionFactory::Create(label, allow_defaults); },
                  py::arg("label"),
                  py::arg("allow_defaults") = false)
      .def_static("rings_create",
                  [](Isis::Pvl &label, bool allow_defaults) { return Isis::ProjectionFactory::RingsCreate(label, allow_defaults); },
                  py::arg("label"),
                  py::arg("allow_defaults") = false)
      .def_static("create_from_cube",
                  py::overload_cast<Isis::Cube &>(&Isis::ProjectionFactory::CreateFromCube),
                  py::arg("cube"))
      .def_static("create_from_cube_label",
                  py::overload_cast<Isis::Pvl &>(&Isis::ProjectionFactory::CreateFromCube),
                  py::arg("label"))
      .def_static("rings_create_from_cube",
                  py::overload_cast<Isis::Cube &>(&Isis::ProjectionFactory::RingsCreateFromCube),
                  py::arg("cube"))
      .def_static("rings_create_from_cube_label",
                  py::overload_cast<Isis::Pvl &>(&Isis::ProjectionFactory::RingsCreateFromCube),
                  py::arg("label"))
      .def_static("create_for_cube",
                  [](Isis::Pvl &label, bool size_match) {
                    int samples = 0;
                    int lines = 0;
                    Isis::Projection *projection = Isis::ProjectionFactory::CreateForCube(label, samples, lines, size_match);
                    return py::make_tuple(projection, samples, lines);
                  },
                  py::arg("label"),
                  py::arg("size_match") = true)
      .def_static("rings_create_for_cube",
                  [](Isis::Pvl &label, bool size_match) {
                    int samples = 0;
                    int lines = 0;
                    Isis::Projection *projection = Isis::ProjectionFactory::RingsCreateForCube(label, samples, lines, size_match);
                    return py::make_tuple(projection, samples, lines);
                  },
                  py::arg("label"),
                  py::arg("size_match") = true);
}