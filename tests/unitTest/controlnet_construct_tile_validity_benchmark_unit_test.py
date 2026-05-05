"""Focused unit tests for the tile-validity benchmark CLI helpers.

Author: Geng Xun
Created: 2026-05-04
Last Modified: 2026-05-04
Updated: 2026-05-04  Geng Xun added regression coverage for cell-size parsing and combination resolution.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))


benchmark_module = importlib.import_module("controlnet_construct.tile_validity_benchmark")


class ControlNetConstructTileValidityBenchmarkUnitTest(unittest.TestCase):
    def test_parse_cell_size_spec_accepts_ascii_and_unicode_separators(self):
        ascii_spec = benchmark_module.parse_cell_size_spec("1024x1071")
        unicode_spec = benchmark_module.parse_cell_size_spec("2048×1428")

        self.assertEqual((ascii_spec.width, ascii_spec.height, ascii_spec.label), (1024, 1071, "1024x1071"))
        self.assertEqual((unicode_spec.width, unicode_spec.height, unicode_spec.label), (2048, 1428, "2048x1428"))

    def test_parse_cell_size_spec_rejects_invalid_shapes(self):
        with self.assertRaisesRegex(ValueError, "Expected WIDTHxHEIGHT"):
            benchmark_module.parse_cell_size_spec("1024")
        with self.assertRaisesRegex(ValueError, "cell_width must be positive"):
            benchmark_module.parse_cell_size_spec("0x357")
        with self.assertRaisesRegex(ValueError, "cell_height must be positive"):
            benchmark_module.parse_cell_size_spec("128x-1")

    def test_resolve_cell_size_specs_uses_default_when_no_inputs_provided(self):
        specs = benchmark_module.resolve_cell_size_specs(
            explicit_sizes=None,
            widths=None,
            heights=None,
        )

        self.assertEqual([(spec.width, spec.height) for spec in specs], [(1024, 1024)])

    def test_resolve_cell_size_specs_combines_explicit_and_grid_and_dedupes(self):
        specs = benchmark_module.resolve_cell_size_specs(
            explicit_sizes=[
                benchmark_module.CellSizeSpec(width=1024, height=1071),
                benchmark_module.CellSizeSpec(width=1024, height=1071),
            ],
            widths=[1024, 2048],
            heights=[1071, 1428],
        )

        self.assertEqual(
            [(spec.width, spec.height) for spec in specs],
            [(1024, 1071), (1024, 1428), (2048, 1071), (2048, 1428)],
        )

    def test_resolve_cell_size_specs_requires_widths_and_heights_together(self):
        with self.assertRaisesRegex(ValueError, "must be provided together"):
            benchmark_module.resolve_cell_size_specs(
                explicit_sizes=None,
                widths=[1024],
                heights=None,
            )


if __name__ == "__main__":
    unittest.main()