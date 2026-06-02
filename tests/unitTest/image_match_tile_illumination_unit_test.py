from __future__ import annotations

import sys
import types
from pathlib import Path
import unittest
from unittest import mock

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.tile_illumination import (
    RepresentativePoint,
    TileIlluminationPair,
    TileIlluminationSample,
    TileWindowMetadata,
    angular_difference_degrees,
    illumination_difference_score,
    illumination_pair_to_payload,
    summarize_tile_illumination_pairs,
)


def _float32_from_bits(bits: int) -> float:
    return float(np.array([bits], dtype=np.uint32).view(np.float32)[0])


class ImageMatchTileIlluminationUnitTest(unittest.TestCase):
    def test_angular_difference_handles_wraparound(self):
        self.assertEqual(angular_difference_degrees(359.0, 1.0), 2.0)
        self.assertEqual(angular_difference_degrees(10.0, 350.0), 20.0)

    def test_illumination_difference_score_returns_none_when_all_inputs_none(self):
        self.assertIsNone(
            illumination_difference_score(
                azimuth_difference_degrees=None,
                incidence_difference_degrees=None,
                elevation_difference_degrees=None,
            )
        )

    def test_illumination_difference_score_returns_none_when_all_inputs_non_finite(self):
        self.assertIsNone(
            illumination_difference_score(
                azimuth_difference_degrees=float("nan"),
                incidence_difference_degrees=float("inf"),
                elevation_difference_degrees=float("-inf"),
            )
        )

    def test_illumination_difference_score_uses_only_finite_inputs(self):
        score = illumination_difference_score(
            azimuth_difference_degrees=float("nan"),
            incidence_difference_degrees=45.0,
            elevation_difference_degrees=float("inf"),
        )

        self.assertEqual(score, 0.5)

    def test_pair_payload_preserves_solar_elevation(self):
        point = RepresentativePoint(
            status="center_projectable",
            selection_reason="center pixel projected to source camera",
            local_x_0_based=5,
            local_y_0_based=6,
            dom_sample_1_based=11.0,
            dom_line_1_based=12.0,
            pixel_available=True,
            radiometric_valid_for_matching=False,
            source_projectable=True,
            failure_reason=None,
        )
        sample = TileIlluminationSample(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=3,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=32, height=32),
            representative_point=point,
            latitude=-88.5,
            longitude=123.0,
            source_sample_1_based=21.5,
            source_line_1_based=22.5,
            sun_azimuth_degrees=359.0,
            incidence_angle_degrees=87.0,
            solar_elevation_degrees=3.0,
        )
        pair = TileIlluminationPair.from_samples(tile_index=3, left=sample, right=sample)

        payload = illumination_pair_to_payload(pair)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["left"]["solar_elevation_degrees"], 3.0)
        self.assertEqual(payload["azimuth_difference_degrees"], 0.0)

    def test_summary_counts_projectable_and_skipped_tiles(self):
        failed_point = RepresentativePoint(
            status="no_projectable_pixel",
            selection_reason="no pixel projected to source camera",
            local_x_0_based=None,
            local_y_0_based=None,
            dom_sample_1_based=None,
            dom_line_1_based=None,
            pixel_available=False,
            radiometric_valid_for_matching=None,
            source_projectable=False,
            failure_reason="no_projectable_pixel",
        )
        failed_sample = TileIlluminationSample.failed(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=1,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=16, height=16),
            representative_point=failed_point,
        )
        summary = summarize_tile_illumination_pairs((
            TileIlluminationPair.from_samples(tile_index=1, left=failed_sample, right=failed_sample),
        ))

        self.assertEqual(summary["tile_count"], 1)
        self.assertEqual(summary["projectable_tile_count"], 0)
        self.assertEqual(summary["skipped_tile_count"], 1)
        self.assertEqual(summary["skip_reasons"]["both_failed"], 1)

    def test_source_metadata_resolves_reduced_pair_csv(self):
        import tempfile
        from image_match.tile_illumination import load_dom_source_metadata_csv, resolve_dom_source_metadata

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "reduced_selected_pair_paths.csv"
            csv_path.write_text(
                "source_echo_cal_cube,echo_cal_cube,source_dom_cube,dom_cube\n"
                "/full/M123.echo.cal.cub,/reduced/REDUCED_M123.echo.cal.cub,/dom/full_dom_M123.cub,/dom/dom_REDUCED_M123.cub\n",
                encoding="utf-8",
            )

            lookup = load_dom_source_metadata_csv(csv_path)
            metadata = resolve_dom_source_metadata("/dom/dom_REDUCED_M123.cub", lookup)

        self.assertEqual(metadata["dom_source_cube"], "/reduced/REDUCED_M123.echo.cal.cub")
        self.assertEqual(metadata["upstream_source_cube"], "/full/M123.echo.cal.cub")
        self.assertEqual(metadata["dom_source_kind"], "reduced")

    def test_source_metadata_resolves_unique_basename_csv(self):
        import tempfile
        from image_match.tile_illumination import load_dom_source_metadata_csv, resolve_dom_source_metadata

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "reduced_selected_pair_paths.csv"
            csv_path.write_text(
                "source_echo_cal_cube,echo_cal_cube,source_dom_cube,dom_cube\n"
                "/full/M123.echo.cal.cub,/reduced/REDUCED_M123.echo.cal.cub,/dom/full_dom_M123.cub,/dom/dom_REDUCED_M123.cub\n",
                encoding="utf-8",
            )

            lookup = load_dom_source_metadata_csv(csv_path)
            metadata = resolve_dom_source_metadata("dom_REDUCED_M123.cub", lookup)

        self.assertEqual(metadata["dom_source_cube"], "/reduced/REDUCED_M123.echo.cal.cub")
        self.assertEqual(metadata["upstream_source_cube"], "/full/M123.echo.cal.cub")
        self.assertEqual(metadata["dom_source_kind"], "reduced")

    def test_source_metadata_unknown_lookup_uses_empty_source_cube(self):
        from image_match.tile_illumination import resolve_dom_source_metadata

        metadata = resolve_dom_source_metadata("/dom/missing.cub", {})

        self.assertEqual(metadata["dom_path"], "/dom/missing.cub")
        self.assertEqual(metadata["dom_source_cube"], "")
        self.assertIsNone(metadata["upstream_source_cube"])
        self.assertEqual(metadata["dom_source_kind"], "unknown")

    def test_source_metadata_duplicate_basename_returns_unknown_for_basename_lookup(self):
        import tempfile
        from image_match.tile_illumination import load_dom_source_metadata_csv, resolve_dom_source_metadata

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "reduced_selected_pair_paths.csv"
            csv_path.write_text(
                "source_echo_cal_cube,echo_cal_cube,source_dom_cube,dom_cube\n"
                "/full/A.echo.cal.cub,/reduced/REDUCED_A.echo.cal.cub,/dom/a_full.cub,/dom/a/dom_DUP.cub\n"
                "/full/B.echo.cal.cub,/reduced/REDUCED_B.echo.cal.cub,/dom/b_full.cub,/dom/b/dom_DUP.cub\n",
                encoding="utf-8",
            )

            lookup = load_dom_source_metadata_csv(csv_path)
            metadata = resolve_dom_source_metadata("dom_DUP.cub", lookup)

        self.assertEqual(metadata["dom_path"], "dom_DUP.cub")
        self.assertEqual(metadata["dom_source_cube"], "")
        self.assertIsNone(metadata["upstream_source_cube"])
        self.assertEqual(metadata["dom_source_kind"], "unknown")

    def test_source_metadata_exact_key_wins_when_exact_path_is_ambiguous_basename(self):
        import tempfile
        from image_match.tile_illumination import load_dom_source_metadata_csv, resolve_dom_source_metadata

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "reduced_selected_pair_paths.csv"
            csv_path.write_text(
                "source_echo_cal_cube,echo_cal_cube,source_dom_cube,dom_cube\n"
                "/full/A.echo.cal.cub,/reduced/REDUCED_A.echo.cal.cub,/dom/a_full.cub,dom_DUP.cub\n"
                "/full/B.echo.cal.cub,/reduced/REDUCED_B.echo.cal.cub,/dom/b_full.cub,/other/dom_DUP.cub\n",
                encoding="utf-8",
            )

            lookup = load_dom_source_metadata_csv(csv_path)
            exact_metadata = resolve_dom_source_metadata("dom_DUP.cub", lookup)
            basename_metadata = resolve_dom_source_metadata("/unlisted/dom_DUP.cub", lookup)

        self.assertEqual(exact_metadata["dom_source_cube"], "/reduced/REDUCED_A.echo.cal.cub")
        self.assertEqual(exact_metadata["upstream_source_cube"], "/full/A.echo.cal.cub")
        self.assertEqual(exact_metadata["dom_source_kind"], "reduced")
        self.assertEqual(basename_metadata["dom_path"], "/unlisted/dom_DUP.cub")
        self.assertEqual(basename_metadata["dom_source_cube"], "")
        self.assertIsNone(basename_metadata["upstream_source_cube"])
        self.assertEqual(basename_metadata["dom_source_kind"], "unknown")

    def test_shadowed_pixel_can_be_selected_when_source_projectable(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.full((5, 5), 10.0, dtype=np.float64)
        radiometric_mask = np.ones((5, 5), dtype=bool)
        radiometric_mask[2, 2] = False

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=100,
            tile_start_y=200,
            radiometric_valid_for_matching_mask=radiometric_mask,
            project_source_pixel=lambda sample, line: {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": 11.0,
                "source_line": 12.0,
                "sun_azimuth": 250.0,
                "incidence": 87.5,
            },
        )

        self.assertEqual(selected.representative_point.status, "center_projectable")
        self.assertFalse(selected.representative_point.radiometric_valid_for_matching)
        self.assertEqual(selected.representative_point.dom_sample_1_based, 103.0)
        self.assertEqual(selected.representative_point.dom_line_1_based, 203.0)
        self.assertEqual(selected.solar_elevation_degrees, 2.5)

    def test_center_projection_failure_uses_nearest_projectable_pixel(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.ones((3, 3), dtype=np.float64)
        calls = []

        def projector(sample, line):
            calls.append((sample, line))
            if (sample, line) == (2.0, 2.0):
                raise RuntimeError("center outside source camera")
            return {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": sample + 10.0,
                "source_line": line + 10.0,
                "sun_azimuth": 180.0,
                "incidence": 80.0,
            }

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=projector,
        )

        self.assertEqual(selected.representative_point.status, "nearest_projectable_pixel")
        self.assertEqual(calls[0], (2.0, 2.0))
        self.assertGreaterEqual(len(calls), 2)

    def test_finite_isis_special_center_pixel_is_skipped_by_default(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.ones((3, 3), dtype=np.float64)
        values[1, 1] = _float32_from_bits(0xFF7FFFFB)
        calls = []

        def projector(sample, line):
            calls.append((sample, line))
            return {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": sample + 10.0,
                "source_line": line + 10.0,
                "sun_azimuth": 180.0,
                "incidence": 80.0,
            }

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=projector,
        )

        self.assertEqual(selected.representative_point.status, "nearest_projectable_pixel")
        self.assertEqual(selected.representative_point.local_x_0_based, 1)
        self.assertEqual(selected.representative_point.local_y_0_based, 0)
        self.assertNotIn((2.0, 2.0), calls)

    def test_pixel_available_rejects_non_finite_values(self):
        from image_match.tile_illumination_geometry import pixel_available

        self.assertFalse(pixel_available(float("nan")))
        self.assertFalse(pixel_available(float("inf")))
        self.assertFalse(pixel_available(float("-inf")))

    def test_pixel_available_rejects_all_isis_float_special_values(self):
        from image_match.tile_illumination_geometry import pixel_available

        special_pixel_bits = (
            0xFF7FFFFB,  # NULL4
            0xFF7FFFFC,  # LOW_REPR_SAT4
            0xFF7FFFFD,  # LOW_INSTR_SAT4
            0xFF7FFFFE,  # HIGH_INSTR_SAT4
            0xFF7FFFFF,  # HIGH_REPR_SAT4
        )

        for bits in special_pixel_bits:
            with self.subTest(bits=hex(bits)):
                self.assertFalse(pixel_available(_float32_from_bits(bits)))

    def test_no_projectable_pixel_reports_failure(self):
        from image_match.tile_illumination_geometry import select_representative_point

        selected = select_representative_point(
            dom_values=np.ones((2, 2), dtype=np.float64),
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=lambda sample, line: (_ for _ in ()).throw(RuntimeError("not covered")),
        )

        self.assertEqual(selected.representative_point.status, "no_projectable_pixel")
        self.assertEqual(selected.representative_point.failure_reason, "no_projectable_pixel")

    def test_no_projectable_pixel_preserves_classified_projection_failure(self):
        from image_match.tile_illumination_geometry import select_representative_point

        selected = select_representative_point(
            dom_values=np.ones((2, 2), dtype=np.float64),
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=lambda sample, line: (_ for _ in ()).throw(
                RuntimeError("source_ground_map_set_universal_ground_failed")
            ),
        )

        self.assertEqual(selected.representative_point.status, "no_projectable_pixel")
        self.assertEqual(
            selected.representative_point.failure_reason,
            "source_ground_map_set_universal_ground_failed",
        )

    def test_malformed_projector_output_raises_key_error(self):
        from image_match.tile_illumination_geometry import select_representative_point

        with self.assertRaises(KeyError):
            select_representative_point(
                dom_values=np.ones((2, 2), dtype=np.float64),
                tile_start_x=0,
                tile_start_y=0,
                radiometric_valid_for_matching_mask=None,
                project_source_pixel=lambda sample, line: {
                    "latitude": -88.0,
                    "longitude": 123.0,
                    "source_sample": 11.0,
                    "source_line": 12.0,
                    "incidence": 80.0,
                },
            )

    def test_pyisis_projector_is_context_managed_and_closes_cubes(self):
        from image_match import runtime
        from image_match.tile_illumination_geometry import build_pyisis_projector

        created_cubes = []

        class FakeCube:
            def __init__(self):
                self.closed = False
                self.opened = []
                created_cubes.append(self)

            def open(self, path, mode):
                self.opened.append((path, mode))

            def close(self):
                self.closed = True

            def camera(self):
                return FakeCamera()

        class FakeCamera:
            def set_image(self, sample, line):
                return True

            def sun_azimuth(self):
                return 120.0

            def incidence_angle(self):
                return 80.0

        class FakeUniversalGroundMap:
            class CameraPriority:
                ProjectionFirst = "ProjectionFirst"
                CameraFirst = "CameraFirst"

            def __init__(self, cube, priority):
                self.priority = priority

            def set_image(self, sample, line):
                return True

            def universal_latitude(self):
                return -88.0

            def universal_longitude(self):
                return 123.0

            def set_universal_ground(self, latitude, longitude):
                return True

            def sample(self):
                return 11.0

            def line(self):
                return 12.0

        fake_ip = types.SimpleNamespace(Cube=FakeCube, UniversalGroundMap=FakeUniversalGroundMap)

        with mock.patch.object(runtime, "bootstrap_runtime_environment"), mock.patch.dict(
            sys.modules,
            {"isis_pybind": fake_ip},
        ):
            projector = build_pyisis_projector(dom_path="dom.cub", source_cube_path="source.cub")
            self.assertTrue(callable(projector))
            self.assertTrue(hasattr(projector, "close"))
            self.assertTrue(hasattr(projector, "__enter__"))
            self.assertTrue(hasattr(projector, "__exit__"))

            with projector as active_projector:
                self.assertIs(active_projector, projector)
                self.assertEqual(
                    active_projector(1.0, 2.0)["source_sample"],
                    11.0,
                )

        self.assertEqual(len(created_cubes), 2)
        self.assertTrue(all(cube.closed for cube in created_cubes))

    def test_pyisis_projector_close_is_best_effort_when_source_close_raises(self):
        from image_match.tile_illumination_geometry import PyISISProjector

        class FakeCube:
            def __init__(self, name):
                self.name = name
                self.closed = False

            def open(self, path, mode):
                pass

            def camera(self):
                return object()

            def close(self):
                self.closed = True
                if self.name == "source":
                    raise RuntimeError("source close failed")

        class FakeUniversalGroundMap:
            class CameraPriority:
                ProjectionFirst = "ProjectionFirst"
                CameraFirst = "CameraFirst"

            def __init__(self, cube, priority):
                self.cube = cube
                self.priority = priority

        class FakeIP:
            UniversalGroundMap = FakeUniversalGroundMap

            def __init__(self):
                self.cubes = [FakeCube("dom"), FakeCube("source")]

            def Cube(self):
                return self.cubes.pop(0)

        fake_ip = FakeIP()
        projector = PyISISProjector(ip_module=fake_ip, dom_path="dom.cub", source_cube_path="source.cub")
        dom_cube = projector._dom_cube
        source_cube = projector._source_cube

        with self.assertRaisesRegex(RuntimeError, "source close failed"):
            projector.close()

        self.assertTrue(source_cube.closed)
        self.assertTrue(dom_cube.closed)
        self.assertIsNone(projector._source_cube)
        self.assertIsNone(projector._dom_cube)
        self.assertIsNone(projector._source_ground_map)
        self.assertIsNone(projector._dom_ground_map)

    def test_pyisis_projector_closes_dom_cube_when_source_open_fails(self):
        from image_match import runtime
        from image_match.tile_illumination_geometry import build_pyisis_projector

        created_cubes = []

        class FakeCube:
            def __init__(self):
                self.closed = False
                created_cubes.append(self)

            def open(self, path, mode):
                if path == "source.cub":
                    raise RuntimeError("source open failed")

            def close(self):
                self.closed = True

        class FakeUniversalGroundMap:
            class CameraPriority:
                ProjectionFirst = "ProjectionFirst"
                CameraFirst = "CameraFirst"

        fake_ip = types.SimpleNamespace(Cube=FakeCube, UniversalGroundMap=FakeUniversalGroundMap)

        with mock.patch.object(runtime, "bootstrap_runtime_environment"), mock.patch.dict(
            sys.modules,
            {"isis_pybind": fake_ip},
        ):
            with self.assertRaisesRegex(RuntimeError, "source open failed"):
                build_pyisis_projector(dom_path="dom.cub", source_cube_path="source.cub")

        self.assertEqual(len(created_cubes), 2)
        self.assertTrue(all(cube.closed for cube in created_cubes))


if __name__ == "__main__":
    unittest.main()
