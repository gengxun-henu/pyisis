"""
Unit tests for DOM-to-original coordinate conversion geometry helpers.

Author: Geng Xun
Created: 2026-04-18
Last Modified: 2026-04-18
Updated: 2026-04-18  Geng Xun added a focused DOM-like projection to original-camera round-trip covering map/world coordinates, ShapeModel radius lookup, and Camera reprojection with radius.
Updated: 2026-04-18  Geng Xun added a configurable real LRO DOM/original cube regression while preserving the synthetic DOM-like geometry test.
Updated: 2026-04-18  Geng Xun added a real-data unit test that directly calls the dom2ori core conversion function with temporary .key inputs.
Updated: 2026-04-18  Geng Xun added a lightweight _unit_test_support import fallback for repo-root unittest module execution.
Updated: 2026-04-18  Geng Xun added a timestamped JSON report for DOM-to-original geometry test inputs and outputs.
Updated: 2026-04-18  Geng Xun verified the correctness using qview based on the dom2ori results by opening the related CUBE images.
"""

import json
from datetime import datetime
import importlib
import os
from pathlib import Path
import sys
import unittest

try:
	from _unit_test_support import ip, temporary_directory, workspace_test_data_path
except ModuleNotFoundError:
	UNIT_TEST_DIR = Path(__file__).resolve().parent
	if str(UNIT_TEST_DIR) not in sys.path:
		sys.path.insert(0, str(UNIT_TEST_DIR))
	from _unit_test_support import ip, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
	sys.path.insert(0, str(EXAMPLES_DIR))

dom2ori = importlib.import_module("controlnet_construct.dom2ori")
keypoints = importlib.import_module("controlnet_construct.keypoints")

convert_dom_keypoints_to_original = dom2ori.convert_dom_keypoints_to_original
Keypoint = keypoints.Keypoint
KeypointFile = keypoints.KeypointFile
read_key_file = keypoints.read_key_file
write_key_file = keypoints.write_key_file


MDIS_CAMERA_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")

# Real-data regression configuration.
# These defaults match the current local LRO dataset, and can be overridden for later tests.
REAL_DOM_CUBE_ENV = "ISIS_PYBIND_DOM2ORI_REAL_DOM_CUBE"
REAL_ORIGINAL_CUBE_ENV = "ISIS_PYBIND_DOM2ORI_REAL_ORIGINAL_CUBE"
REAL_DOM_SAMPLE_ENV = "ISIS_PYBIND_DOM2ORI_REAL_DOM_SAMPLE"
REAL_DOM_LINE_ENV = "ISIS_PYBIND_DOM2ORI_REAL_DOM_LINE"
JSON_REPORT_PATH_ENV = "ISIS_PYBIND_DOM2ORI_UNIT_TEST_REPORT_JSON"

DEFAULT_REAL_DOM_CUBE = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")
DEFAULT_REAL_ORIGINAL_CUBE = Path(
	"/media/gengxun/Elements/data/lro/test_controlnet_python/REDUCED_M104318871RE.echo.cal.cub"
)


def _configured_real_dataset_paths():
	dom_cube = Path(os.environ.get(REAL_DOM_CUBE_ENV, str(DEFAULT_REAL_DOM_CUBE))).expanduser()
	original_cube = Path(
		os.environ.get(REAL_ORIGINAL_CUBE_ENV, str(DEFAULT_REAL_ORIGINAL_CUBE))
	).expanduser()
	return dom_cube, original_cube


def _configured_real_dom_seed(default_sample, default_line):
	sample = float(os.environ.get(REAL_DOM_SAMPLE_ENV, default_sample))
	line = float(os.environ.get(REAL_DOM_LINE_ENV, default_line))
	return sample, line


def _default_json_report_path():
	timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
	return PROJECT_ROOT / "tests" / "unitTest" / f"controlnet_construct_dom2ori_unit_test_{timestamp}.json"


def _configured_json_report_path():
	configured_path = os.environ.get(JSON_REPORT_PATH_ENV)
	if configured_path:
		return Path(configured_path).expanduser()
	return _default_json_report_path()


def _write_json_report(report_path, payload):
	report_path.parent.mkdir(parents=True, exist_ok=True)
	report_path.write_text(
		json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
		encoding="utf-8",
	)


def _build_dom_like_projection_label(target, projected_x, projected_y, *, pixel_resolution=500.0):
	"""Synthetic-only helper for a no-external-data DOM-like projection regression."""
	radii = target.radii()
	equatorial_radius_m = radii[0].meters()
	polar_radius_m = radii[2].meters()

	upper_left_x = projected_x - 20.0 * pixel_resolution
	upper_left_y = projected_y + 30.0 * pixel_resolution

	label = ip.Pvl()
	label.from_string(
		f"""
Group = Mapping
  EquatorialRadius = {equatorial_radius_m}
  PolarRadius = {polar_radius_m}
  LatitudeType = Planetocentric
  LongitudeDirection = PositiveEast
  LongitudeDomain = 360
  ProjectionName = SimpleCylindrical
  CenterLongitude = 0.0
  MinimumLatitude = -90.0
  MaximumLatitude = 90.0
  MinimumLongitude = 0.0
  MaximumLongitude = 360.0
  PixelResolution = {pixel_resolution}
  UpperLeftCornerX = {upper_left_x}
  UpperLeftCornerY = {upper_left_y}
EndGroup
End
"""
	)
	return label


def _projection_from_dom_cube_mapping(cube):
	"""Create a projection directly from the DOM cube's Mapping group."""
	return ip.ProjectionFactory.create_from_cube(cube)


class DomToOriginalGeometryUnitTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.json_report_path = _configured_json_report_path()
		cls.json_report_payload = {
			"test_module": str(Path(__file__).resolve()),
			"generated_at": datetime.now().isoformat(timespec="seconds"),
			"report_path": str(cls.json_report_path),
			"environment": {
				REAL_DOM_CUBE_ENV: os.environ.get(REAL_DOM_CUBE_ENV),
				REAL_ORIGINAL_CUBE_ENV: os.environ.get(REAL_ORIGINAL_CUBE_ENV),
				REAL_DOM_SAMPLE_ENV: os.environ.get(REAL_DOM_SAMPLE_ENV),
				REAL_DOM_LINE_ENV: os.environ.get(REAL_DOM_LINE_ENV),
				JSON_REPORT_PATH_ENV: os.environ.get(JSON_REPORT_PATH_ENV),
			},
			"tests": {},
		}
		_write_json_report(cls.json_report_path, cls.json_report_payload)

	@classmethod
	def _record_json_report(cls, test_name, *, status, details):
		cls.json_report_payload["tests"][test_name] = {
			"status": status,
			"recorded_at": datetime.now().isoformat(timespec="seconds"),
			**details,
		}
		_write_json_report(cls.json_report_path, cls.json_report_payload)

	def open_cube(self, path):
		cube = ip.Cube()
		cube.open(str(path), "r")
		self.addCleanup(cube.close)
		return cube

	def test_camera_ground_to_dom_projection_and_back_with_shape_radius(self):
		cube = self.open_cube(MDIS_CAMERA_CUBE)
		camera = cube.camera()

		original_sample = camera.samples() / 2.0
		original_line = camera.lines() / 2.0
		self.assertTrue(camera.set_image(original_sample, original_line))

		original_latitude = camera.universal_latitude()
		original_longitude = camera.universal_longitude()
		surface_point = camera.get_surface_point()
		self.assertTrue(surface_point.valid())

		target = camera.target()

		seed_projection = ip.SimpleCylindrical(_build_dom_like_projection_label(target, 0.0, 0.0))
		self.assertTrue(seed_projection.set_universal_ground(original_latitude, original_longitude))
		projected_x = seed_projection.x_coord()
		projected_y = seed_projection.y_coord()

		dom_projection = ip.ProjectionFactory.create_from_cube_label(
			_build_dom_like_projection_label(target, projected_x, projected_y)
		)
		self.assertEqual(dom_projection.name(), "SimpleCylindrical")

		self.assertTrue(dom_projection.set_universal_ground(original_latitude, original_longitude))
		dom_map_x = dom_projection.x_coord()
		dom_map_y = dom_projection.y_coord()
		dom_sample = dom_projection.world_x()
		dom_line = dom_projection.world_y()

		self.assertAlmostEqual(dom_projection.to_projection_x(dom_sample), dom_map_x, places=8)
		self.assertAlmostEqual(dom_projection.to_projection_y(dom_line), dom_map_y, places=8)

		self.assertTrue(dom_projection.set_world(dom_sample, dom_line))
		self.assertAlmostEqual(dom_projection.x_coord(), dom_map_x, places=8)
		self.assertAlmostEqual(dom_projection.y_coord(), dom_map_y, places=8)
		self.assertAlmostEqual(dom_projection.universal_latitude(), original_latitude, places=8)
		self.assertAlmostEqual(dom_projection.universal_longitude(), original_longitude, places=8)

		shape_model = target.shape()
		self.assertIsNotNone(shape_model)
		radius = shape_model.local_radius(
			ip.Latitude(dom_projection.universal_latitude(), ip.Angle.Units.Degrees),
			ip.Longitude(dom_projection.universal_longitude(), ip.Angle.Units.Degrees),
		)
		self.assertGreater(radius.meters(), 0.0)
		self.assertAlmostEqual(
			radius.meters(),
			surface_point.get_local_radius().meters(),
			places=6,
		)

		self.assertTrue(
			camera.set_universal_ground_with_radius(
				dom_projection.universal_latitude(),
				dom_projection.universal_longitude(),
				radius.meters(),
			)
		)
		self.assertAlmostEqual(camera.sample(), original_sample, places=6)
		self.assertAlmostEqual(camera.line(), original_line, places=6)
		self._record_json_report(
			"test_camera_ground_to_dom_projection_and_back_with_shape_radius",
			status="passed",
			details={
				"camera_cube": str(MDIS_CAMERA_CUBE),
				"original_image": {
					"sample": original_sample,
					"line": original_line,
				},
				"ground": {
					"latitude": original_latitude,
					"longitude": original_longitude,
				},
				"dom_projection": {
					"map_x": dom_map_x,
					"map_y": dom_map_y,
					"sample": dom_sample,
					"line": dom_line,
				},
				"radius_meters": radius.meters(),
				"reprojected_camera": {
					"sample": camera.sample(),
					"line": camera.line(),
				},
			},
		)

	def test_real_lro_dom_and_original_cube_round_trip_with_configurable_paths(self):
		dom_cube_path, original_cube_path = _configured_real_dataset_paths()
		if not dom_cube_path.exists() or not original_cube_path.exists():
			self._record_json_report(
				"test_real_lro_dom_and_original_cube_round_trip_with_configurable_paths",
				status="skipped",
				details={
					"reason": (
						"Real LRO DOM/original cube test data are unavailable. "
						f"Configure {REAL_DOM_CUBE_ENV} and {REAL_ORIGINAL_CUBE_ENV} if needed."
					),
					"dom_cube": str(dom_cube_path),
					"original_cube": str(original_cube_path),
				},
			)
			self.skipTest(
				"Real LRO DOM/original cube test data are unavailable. "
				f"Configure {REAL_DOM_CUBE_ENV} and {REAL_ORIGINAL_CUBE_ENV} if needed."
			)

		dom_cube = self.open_cube(dom_cube_path)
		original_cube = self.open_cube(original_cube_path)

		dom_ground_map = ip.UniversalGroundMap(
			dom_cube,
			ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
		)
		original_ground_map = ip.UniversalGroundMap(
			original_cube,
			ip.UniversalGroundMap.CameraPriority.CameraFirst,
		)
		self.assertTrue(dom_ground_map.has_projection())
		self.assertFalse(dom_ground_map.has_camera())
		self.assertTrue(original_ground_map.has_camera())

		# For real DOM cubes, use the cube's own Mapping group to build the projection.
		# This keeps the test aligned with the actual map-projected DOM metadata instead of
		# relying on any synthetic projection construction helper.
		dom_projection = _projection_from_dom_cube_mapping(dom_cube)
		self.assertIsNotNone(dom_projection)
		camera = original_cube.camera()

		dom_sample, dom_line = _configured_real_dom_seed(
			dom_cube.sample_count() / 2.0,
			dom_cube.line_count() / 2.0,
		)
		self.assertTrue(dom_ground_map.set_image(dom_sample, dom_line))

		ugm_latitude = dom_ground_map.universal_latitude()
		ugm_longitude = dom_ground_map.universal_longitude()
		self.assertTrue(dom_projection.set_world(dom_sample, dom_line))

		dom_map_x = dom_projection.x_coord()
		dom_map_y = dom_projection.y_coord()
		self.assertAlmostEqual(dom_projection.to_projection_x(dom_sample), dom_map_x, places=8)
		self.assertAlmostEqual(dom_projection.to_projection_y(dom_line), dom_map_y, places=8)
		self.assertAlmostEqual(dom_projection.universal_latitude(), ugm_latitude, places=8)
		self.assertAlmostEqual(dom_projection.universal_longitude(), ugm_longitude, places=8)

		target = camera.target()
		shape_model = target.shape()
		self.assertIsNotNone(shape_model)
		radius = shape_model.local_radius(
			ip.Latitude(dom_projection.universal_latitude(), ip.Angle.Units.Degrees),
			ip.Longitude(dom_projection.universal_longitude(), ip.Angle.Units.Degrees),
		)
		self.assertGreater(radius.meters(), 0.0)

		ugm_success = original_ground_map.set_universal_ground(ugm_latitude, ugm_longitude)
		camera_success = camera.set_universal_ground_with_radius(
			dom_projection.universal_latitude(),
			dom_projection.universal_longitude(),
			radius.meters(),
		)
		self.assertTrue(camera_success)

		camera_sample = camera.sample()
		camera_line = camera.line()
		self.assertGreaterEqual(camera_sample, -original_cube.sample_count())
		self.assertLessEqual(camera_sample, original_cube.sample_count() * 2.0)
		self.assertGreaterEqual(camera_line, -original_cube.line_count())
		self.assertLessEqual(camera_line, original_cube.line_count() * 2.0)

		if ugm_success:
			self.assertAlmostEqual(camera_sample, original_ground_map.sample(), places=6)
			self.assertAlmostEqual(camera_line, original_ground_map.line(), places=6)
			self.assertGreaterEqual(camera_sample, 1.0)
			self.assertLessEqual(camera_sample, original_cube.sample_count())
			self.assertGreaterEqual(camera_line, 1.0)
			self.assertLessEqual(camera_line, original_cube.line_count())

		self._record_json_report(
			"test_real_lro_dom_and_original_cube_round_trip_with_configurable_paths",
			status="passed",
			details={
				"dom_cube": str(dom_cube_path),
				"original_cube": str(original_cube_path),
				"dom_seed": {
					"sample": dom_sample,
					"line": dom_line,
				},
				"ground": {
					"latitude": ugm_latitude,
					"longitude": ugm_longitude,
				},
				"dom_projection": {
					"map_x": dom_map_x,
					"map_y": dom_map_y,
				},
				"radius_meters": radius.meters(),
				"ugm_success": ugm_success,
				"camera_image": {
					"sample": camera_sample,
					"line": camera_line,
				},
				"ugm_image": {
					"sample": original_ground_map.sample() if ugm_success else None,
					"line": original_ground_map.line() if ugm_success else None,
				},
			},
		)

	def test_real_lro_dom2ori_core_function_with_temporary_key_file(self):
		dom_cube_path, original_cube_path = _configured_real_dataset_paths()
		if not dom_cube_path.exists() or not original_cube_path.exists():
			self._record_json_report(
				"test_real_lro_dom2ori_core_function_with_temporary_key_file",
				status="skipped",
				details={
					"reason": (
						"Real LRO DOM/original cube test data are unavailable. "
						f"Configure {REAL_DOM_CUBE_ENV} and {REAL_ORIGINAL_CUBE_ENV} if needed."
					),
					"dom_cube": str(dom_cube_path),
					"original_cube": str(original_cube_path),
				},
			)
			self.skipTest(
				"Real LRO DOM/original cube test data are unavailable. "
				f"Configure {REAL_DOM_CUBE_ENV} and {REAL_ORIGINAL_CUBE_ENV} if needed."
			)

		dom_cube = self.open_cube(dom_cube_path)
		original_cube = self.open_cube(original_cube_path)
		dom_sample, dom_line = _configured_real_dom_seed(
			dom_cube.sample_count() / 2.0,
			dom_cube.line_count() / 2.0,
		)

		dom_ground_map = ip.UniversalGroundMap(
			dom_cube,
			ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
		)
		self.assertTrue(dom_ground_map.set_image(dom_sample, dom_line))
		dom_projection = _projection_from_dom_cube_mapping(dom_cube)
		self.assertTrue(dom_projection.set_world(dom_sample, dom_line))
		expected_latitude = dom_ground_map.universal_latitude()
		expected_longitude = dom_ground_map.universal_longitude()
		self.assertAlmostEqual(dom_projection.universal_latitude(), expected_latitude, places=8)
		self.assertAlmostEqual(dom_projection.universal_longitude(), expected_longitude, places=8)

		expected_original_ground_map = ip.UniversalGroundMap(
			original_cube,
			ip.UniversalGroundMap.CameraPriority.CameraFirst,
		)
		self.assertTrue(expected_original_ground_map.set_universal_ground(expected_latitude, expected_longitude))
		expected_sample = expected_original_ground_map.sample()
		expected_line = expected_original_ground_map.line()

		input_key_file = KeypointFile(
			dom_cube.sample_count(),
			dom_cube.line_count(),
			(Keypoint(dom_sample, dom_line),),
		)

		with temporary_directory() as temp_dir:
			input_key_path = temp_dir / "real_dom.key"
			output_key_path = temp_dir / "real_ori.key"
			failure_log_path = temp_dir / "real_dom2ori_failure_log.json"
			write_key_file(input_key_path, input_key_file)

			result = convert_dom_keypoints_to_original(
				input_key_path,
				dom_cube_path,
				original_cube_path,
				output_key_path,
				failure_log_path=failure_log_path,
			)
			converted = read_key_file(output_key_path)
			logged = json.loads(failure_log_path.read_text(encoding="utf-8"))

		self.assertEqual(result["input_count"], 1)
		self.assertEqual(result["output_count"], 1)
		self.assertEqual(result["failure_count"], 0)
		self.assertEqual(logged["failure_count"], 0)
		self.assertEqual(converted.image_width, original_cube.sample_count())
		self.assertEqual(converted.image_height, original_cube.line_count())
		self.assertEqual(len(converted.points), 1)
		self.assertAlmostEqual(converted.points[0].sample, expected_sample, places=6)
		self.assertAlmostEqual(converted.points[0].line, expected_line, places=6)
		self.assertEqual(result["dom_cube"], str(dom_cube_path))
		self.assertEqual(result["original_cube"], str(original_cube_path))
		self._record_json_report(
			"test_real_lro_dom2ori_core_function_with_temporary_key_file",
			status="passed",
			details={
				"dom_cube": str(dom_cube_path),
				"original_cube": str(original_cube_path),
				"dom_seed": {
					"sample": dom_sample,
					"line": dom_line,
				},
				"expected_ground": {
					"latitude": expected_latitude,
					"longitude": expected_longitude,
				},
				"expected_original_image": {
					"sample": expected_sample,
					"line": expected_line,
				},
				"converted_point": {
					"sample": converted.points[0].sample,
					"line": converted.points[0].line,
				},
				"conversion_result": result,
				"failure_log": logged,
			},
		)


if __name__ == "__main__":
	unittest.main()
