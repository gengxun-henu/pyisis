// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>
#include <stdexcept>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "AbstractPlate.h"
#include "BulletTargetShape.h"
#include "BulletWorldManager.h"
#include "EmbreeTargetManager.h"
#include "EmbreeTargetShape.h"
#include "Intercept.h"
#include "Latitude.h"
#include "Longitude.h"
#include "NaifDskApi.h"
#include "NaifDskPlateModel.h"
#include "SurfacePoint.h"
#include "TriangularPlate.h"
#include "helpers.h"

namespace py = pybind11;

namespace {

Isis::NaifVertex toNaifVertex3(const std::vector<double> &values, const char *name) {
	if (values.size() != 3) {
		throw std::invalid_argument(std::string(name) + " must contain exactly 3 values");
	}

	Isis::NaifVertex vertex(3);
	for (int i = 0; i < 3; i++) {
		vertex[i] = values[i];
	}
	return vertex;
}

Isis::NaifVector toNaifVector3(const std::vector<double> &values, const char *name) {
	if (values.size() != 3) {
		throw std::invalid_argument(std::string(name) + " must contain exactly 3 values");
	}

	Isis::NaifVector vector(3);
	for (int i = 0; i < 3; i++) {
		vector[i] = values[i];
	}
	return vector;
}

std::vector<double> fromNaifVector3(const Isis::NaifVector &values) {
	std::vector<double> result;
	result.reserve(3);
	for (int i = 0; i < 3; i++) {
		result.push_back(values[i]);
	}
	return result;
}

std::vector<double> fromNaifVertex3(const Isis::NaifVertex &values) {
	std::vector<double> result;
	result.reserve(3);
	for (int i = 0; i < 3; i++) {
		result.push_back(values[i]);
	}
	return result;
}

Isis::NaifTriangle toNaifTriangle(const std::vector<std::vector<double>> &vertices) {
	if (vertices.size() != 3) {
		throw std::invalid_argument("vertices must contain exactly 3 rows");
	}

	Isis::NaifTriangle triangle(3, 3, 0.0);
	for (int row = 0; row < 3; row++) {
		if (vertices[row].size() != 3) {
			throw std::invalid_argument("each triangle vertex must contain exactly 3 values");
		}
		for (int column = 0; column < 3; column++) {
			triangle[row][column] = vertices[row][column];
		}
	}
	return triangle;
}

std::vector<std::vector<double>> fromNaifTriangle(const Isis::NaifTriangle &triangle) {
	std::vector<std::vector<double>> vertices(3, std::vector<double>(3, 0.0));
	for (int row = 0; row < 3; row++) {
		for (int column = 0; column < 3; column++) {
			vertices[row][column] = triangle[row][column];
		}
	}
	return vertices;
}

py::object maybeSurfacePoint(Isis::SurfacePoint *point) {
	if (!point) {
		return py::none();
	}
	return py::cast(point, py::return_value_policy::take_ownership);
}

py::object maybeIntercept(Isis::Intercept *intercept) {
	if (!intercept) {
		return py::none();
	}
	return py::cast(intercept, py::return_value_policy::take_ownership);
}

}  // namespace

void bind_base_shape_support(py::module_ &m) {
	py::class_<Isis::AbstractPlate> abstract_plate(m, "AbstractPlate");

	abstract_plate
			.def("name", [](const Isis::AbstractPlate &self) { return qStringToStdString(self.name()); })
			.def("min_radius", &Isis::AbstractPlate::minRadius)
			.def("max_radius", &Isis::AbstractPlate::maxRadius)
			.def("area", &Isis::AbstractPlate::area)
			.def("normal",
					 [](const Isis::AbstractPlate &self) {
						 return fromNaifVector3(self.normal());
					 })
			.def("separation_angle",
					 [](const Isis::AbstractPlate &self, const std::vector<double> &ray_direction) {
						 return self.separationAngle(toNaifVector3(ray_direction, "ray_direction"));
					 },
					 py::arg("ray_direction"))
			.def("has_intercept",
					 [](const Isis::AbstractPlate &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 return self.hasIntercept(toNaifVertex3(observer, "observer"),
																			toNaifVector3(ray_direction, "ray_direction"));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("has_point", &Isis::AbstractPlate::hasPoint, py::arg("latitude"), py::arg("longitude"))
			.def("point",
					 [](const Isis::AbstractPlate &self, const Isis::Latitude &latitude, const Isis::Longitude &longitude) {
						 return maybeSurfacePoint(self.point(latitude, longitude));
					 },
					 py::arg("latitude"),
					 py::arg("longitude"))
			.def("intercept",
					 [](const Isis::AbstractPlate &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 return maybeIntercept(self.intercept(toNaifVertex3(observer, "observer"),
																									toNaifVector3(ray_direction, "ray_direction")));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("clone",
					 [](const Isis::AbstractPlate &self) {
						 return self.clone();
					 },
					 py::return_value_policy::take_ownership);

	py::class_<Isis::TriangularPlate, Isis::AbstractPlate>(m, "TriangularPlate")
			.def(py::init([](const std::vector<std::vector<double>> &vertices, int plate_id) {
						 return new Isis::TriangularPlate(toNaifTriangle(vertices), plate_id);
					 }),
					 py::arg("vertices"),
					 py::arg("plate_id") = 0)
			.def("id", &Isis::TriangularPlate::id)
			.def("name", [](const Isis::TriangularPlate &self) { return qStringToStdString(self.name()); })
			.def("min_radius", &Isis::TriangularPlate::minRadius)
			.def("max_radius", &Isis::TriangularPlate::maxRadius)
			.def("area", &Isis::TriangularPlate::area)
			.def("normal",
					 [](const Isis::TriangularPlate &self) {
						 return fromNaifVector3(self.normal());
					 })
			.def("center",
					 [](const Isis::TriangularPlate &self) {
						 return fromNaifVector3(self.center());
					 })
			.def("separation_angle",
					 [](const Isis::TriangularPlate &self, const std::vector<double> &ray_direction) {
						 return self.separationAngle(toNaifVector3(ray_direction, "ray_direction"));
					 },
					 py::arg("ray_direction"))
			.def("has_intercept",
					 [](const Isis::TriangularPlate &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 return self.hasIntercept(toNaifVertex3(observer, "observer"),
																			toNaifVector3(ray_direction, "ray_direction"));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("has_point", &Isis::TriangularPlate::hasPoint, py::arg("latitude"), py::arg("longitude"))
			.def("point",
					 [](const Isis::TriangularPlate &self, const Isis::Latitude &latitude, const Isis::Longitude &longitude) {
						 return maybeSurfacePoint(self.point(latitude, longitude));
					 },
					 py::arg("latitude"),
					 py::arg("longitude"))
			.def("intercept",
					 [](const Isis::TriangularPlate &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 return maybeIntercept(self.intercept(toNaifVertex3(observer, "observer"),
																									toNaifVector3(ray_direction, "ray_direction")));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("vertex",
					 [](const Isis::TriangularPlate &self, int index) {
						 return fromNaifVertex3(self.vertex(index));
					 },
					 py::arg("index"))
			.def("clone",
					 [](const Isis::TriangularPlate &self) {
						 return self.clone();
					 },
					 py::return_value_policy::take_ownership);

	py::class_<Isis::Intercept> intercept(m, "Intercept");

	intercept
			.def(py::init<>())
			.def("is_valid", &Isis::Intercept::isValid)
			.def("observer",
					 [](const Isis::Intercept &self) {
						 return fromNaifVertex3(self.observer());
					 })
			.def("look_direction_ray",
					 [](const Isis::Intercept &self) {
						 return fromNaifVector3(self.lookDirectionRay());
					 })
			.def("location", &Isis::Intercept::location)
			.def("normal",
					 [](const Isis::Intercept &self) {
						 return fromNaifVector3(self.normal());
					 })
			.def("emission", &Isis::Intercept::emission)
			.def("separation_angle",
					 [](const Isis::Intercept &self, const std::vector<double> &ray_direction) {
						 return self.separationAngle(toNaifVector3(ray_direction, "ray_direction"));
					 },
					 py::arg("ray_direction"))
			.def("shape",
					 [](const Isis::Intercept &self) -> py::object {
						 const Isis::AbstractPlate *shape = self.shape();
						 if (!shape) {
							 return py::none();
						 }
						 return py::cast(shape, py::return_value_policy::reference_internal, py::cast(&self));
					 });

	py::class_<Isis::NaifDskPlateModel>(m, "NaifDskPlateModel")
			.def(py::init<>())
			.def(py::init([](const std::string &dsk_file) {
						 return Isis::NaifDskPlateModel(stdStringToQString(dsk_file));
					 }),
					 py::arg("dsk_file"))
			.def("is_valid", &Isis::NaifDskPlateModel::isValid)
			.def("filename", [](const Isis::NaifDskPlateModel &self) { return qStringToStdString(self.filename()); })
			.def("size", &Isis::NaifDskPlateModel::size)
			.def("number_plates", &Isis::NaifDskPlateModel::numberPlates)
			.def("number_vertices", &Isis::NaifDskPlateModel::numberVertices)
			.def("point",
					 [](const Isis::NaifDskPlateModel &self, const Isis::Latitude &latitude, const Isis::Longitude &longitude) {
						 return maybeSurfacePoint(self.point(latitude, longitude));
					 },
					 py::arg("latitude"),
					 py::arg("longitude"))
			.def("intercept",
					 [](const Isis::NaifDskPlateModel &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 return maybeIntercept(self.intercept(toNaifVertex3(observer, "observer"),
																									toNaifVector3(ray_direction, "ray_direction")));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("is_plate_id_valid", &Isis::NaifDskPlateModel::isPlateIdValid, py::arg("plate_id"))
			.def("plate_id_of_intercept",
					 [](const Isis::NaifDskPlateModel &self,
							const std::vector<double> &observer,
							const std::vector<double> &ray_direction) {
						 Isis::NaifVertex xpoint(3);
						 SpiceInt plate_id = self.plateIdOfIntercept(toNaifVertex3(observer, "observer"),
																												 toNaifVector3(ray_direction, "ray_direction"),
																												 xpoint);
						 return py::make_tuple(plate_id, fromNaifVertex3(xpoint));
					 },
					 py::arg("observer"),
					 py::arg("ray_direction"))
			.def("plate",
					 [](const Isis::NaifDskPlateModel &self, int plate_id) {
						 return fromNaifTriangle(self.plate(plate_id));
					 },
					 py::arg("plate_id"));

	py::class_<Isis::EmbreeTargetShape>(m, "EmbreeTargetShape")
			.def(py::init<>())
			.def("name", [](const Isis::EmbreeTargetShape &self) { return qStringToStdString(self.name()); })
			.def("is_valid", &Isis::EmbreeTargetShape::isValid)
			.def("number_of_polygons", &Isis::EmbreeTargetShape::numberOfPolygons)
			.def("number_of_vertices", &Isis::EmbreeTargetShape::numberOfVertices)
			.def("maximum_scene_distance", &Isis::EmbreeTargetShape::maximumSceneDistance);

	py::class_<Isis::EmbreeTargetManager, std::unique_ptr<Isis::EmbreeTargetManager, py::nodelete>>(m, "EmbreeTargetManager")
			.def_static("instance",
									[]() {
										return Isis::EmbreeTargetManager::getInstance();
									},
									py::return_value_policy::reference)
			.def("create",
					 [](Isis::EmbreeTargetManager &self, const std::string &shape_file) {
						 return self.create(stdStringToQString(shape_file));
					 },
					 py::arg("shape_file"),
					 py::return_value_policy::reference)
			.def("free",
					 [](Isis::EmbreeTargetManager &self, const std::string &shape_file) {
						 self.free(stdStringToQString(shape_file));
					 },
					 py::arg("shape_file"))
			.def("current_cache_size", &Isis::EmbreeTargetManager::currentCacheSize)
			.def("max_cache_size", &Isis::EmbreeTargetManager::maxCacheSize)
			.def("in_cache",
					 [](const Isis::EmbreeTargetManager &self, const std::string &shape_file) {
						 return self.inCache(stdStringToQString(shape_file));
					 },
					 py::arg("shape_file"))
			.def("set_max_cache_size", &Isis::EmbreeTargetManager::setMaxCacheSize, py::arg("num_shapes"));

	py::class_<Isis::BulletTargetShape>(m, "BulletTargetShape")
			.def(py::init<>())
			.def("name", [](const Isis::BulletTargetShape &self) { return qStringToStdString(self.name()); })
			.def("maximum_distance", &Isis::BulletTargetShape::maximumDistance)
			.def("write_bullet",
					 [](const Isis::BulletTargetShape &self, const std::string &file_name) {
						 self.writeBullet(stdStringToQString(file_name));
					 },
					 py::arg("file_name"))
			.def_static("load",
									[](const std::string &dem) {
										return Isis::BulletTargetShape::load(stdStringToQString(dem));
									},
									py::arg("dem"),
									py::return_value_policy::take_ownership)
			.def_static("load_pc",
									[](const std::string &dem) {
										return Isis::BulletTargetShape::loadPC(stdStringToQString(dem));
									},
									py::arg("dem"),
									py::return_value_policy::take_ownership)
			.def_static("load_dsk",
									[](const std::string &dem) {
										return Isis::BulletTargetShape::loadDSK(stdStringToQString(dem));
									},
									py::arg("dem"),
									py::return_value_policy::take_ownership)
			.def_static("load_cube",
									[](const std::string &dem) {
										return Isis::BulletTargetShape::loadCube(stdStringToQString(dem));
									},
									py::arg("dem"),
									py::return_value_policy::take_ownership);

	py::class_<Isis::BulletWorldManager>(m, "BulletWorldManager")
			.def(py::init([]() {
						 return new Isis::BulletWorldManager();
					 }))
			.def(py::init([](const std::string &name) {
						 return new Isis::BulletWorldManager(stdStringToQString(name));
					 }),
					 py::arg("name"))
			.def("name", [](const Isis::BulletWorldManager &self) { return qStringToStdString(self.name()); })
			.def("size", &Isis::BulletWorldManager::size)
			.def("get_target",
					 py::overload_cast<const int &>(&Isis::BulletWorldManager::getTarget, py::const_),
					 py::arg("index") = 0,
					 py::return_value_policy::reference_internal)
			.def("get_target",
					 [](const Isis::BulletWorldManager &self, const std::string &name) {
						 return self.getTarget(stdStringToQString(name));
					 },
					 py::arg("name"),
					 py::return_value_policy::reference_internal)
			.def("add_target", &Isis::BulletWorldManager::addTarget, py::arg("target"));
}
