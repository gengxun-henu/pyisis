# Lunar Crater Semantic Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimum viable crater-semantic matcher for lunar south-pole overlap regions that uses DEM-derived coarse alignment to constrain search, crater topology as the main signal, and terrain cues as a re-scoring constraint.

**Architecture:** Keep the first version as a standalone matcher inside `examples/image_match/` instead of wiring it into the full `image_match.py` production CLI. The implementation creates a narrow crater pipeline with five focused units: crater catalog I/O, topology graph construction, DEM coarse constraints, semantic matching/orchestration, and evaluation metrics. The MVP compares three methods on the same synthetic/curated inputs: ellipse-raster LightGlue baseline, shape-only baseline, and the full DEM-constrained crater-graph method.

**Tech Stack:** Python 3.12, NumPy, OpenCV, existing `examples/image_match.deep_adapter.DeepMatcherAdapter`, CSV/JSON I/O, `unittest`.

---

## File Structure

- Create `examples/image_match/crater_catalog.py`
  - Dataclasses for crater ellipses, coarse alignment priors, and final match records.
  - CSV loading for crater catalogs and JSON writing for match artifacts.
- Create `examples/image_match/crater_graph.py`
  - Local KNN/radius graph construction and topology similarity scoring.
- Create `examples/image_match/crater_constraints.py`
  - DEM-render coarse offset estimation, search-window construction, candidate filtering, and terrain re-scoring.
- Create `examples/image_match/crater_semantic_match.py`
  - Orchestrate the three matching routes.
  - Render ellipse-raster baseline images and call the existing deep adapter for baseline A.
  - Produce candidate-score artifacts and final selected crater matches.
- Create `examples/image_match/crater_semantic_eval.py`
  - Compute recall, precision/inlier ratio, graph consistency, and shadow-stratified robustness summaries.
- Tests:
  - `tests/unitTest/image_match_crater_catalog_unit_test.py`
  - `tests/unitTest/image_match_crater_graph_unit_test.py`
  - `tests/unitTest/image_match_crater_constraints_unit_test.py`
  - `tests/unitTest/image_match_crater_semantic_match_unit_test.py`
  - `tests/unitTest/image_match_crater_eval_unit_test.py`

## Task 1: Crater Catalog Types and I/O

**Files:**
- Create: `examples/image_match/crater_catalog.py`
- Test: `tests/unitTest/image_match_crater_catalog_unit_test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unitTest/image_match_crater_catalog_unit_test.py`:

```python
"""Unit tests for crater catalog loading and artifact writing.

Author: Geng Xun
Created: 2026-06-04
Last Modified: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater catalog CSV and JSON artifact coverage.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.crater_catalog import (
    CoarseAlignmentPrior,
    CraterCatalog,
    CraterEllipse,
    CraterMatchRecord,
    read_crater_catalog_csv,
    write_crater_match_artifacts,
)


class ImageMatchCraterCatalogUnitTest(unittest.TestCase):
    def test_read_crater_catalog_csv_loads_optional_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "catalog.csv"
            csv_path.write_text(
                "crater_id,center_x,center_y,major_axis,minor_axis,angle_deg,confidence,shadow_ratio,dem_height,dem_slope_deg\n"
                "c1,10,20,8,6,15,0.95,0.2,100.0,3.5\n"
                "c2,30,40,12,11,0,0.75,,, \n",
                encoding="utf-8",
            )

            catalog = read_crater_catalog_csv(csv_path, image_id="left_dom")

        self.assertEqual(catalog.image_id, "left_dom")
        self.assertEqual([crater.crater_id for crater in catalog.craters], ["c1", "c2"])
        self.assertAlmostEqual(catalog.craters[0].shadow_ratio, 0.2)
        self.assertIsNone(catalog.craters[1].dem_height)

    def test_crater_ellipse_rejects_invalid_axes(self):
        with self.assertRaisesRegex(ValueError, "major_axis"):
            CraterEllipse(
                crater_id="bad",
                center_x=5.0,
                center_y=5.0,
                major_axis=0.0,
                minor_axis=2.0,
                angle_deg=0.0,
                confidence=0.8,
            )

    def test_write_crater_match_artifacts_serializes_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "matches.json"
            write_crater_match_artifacts(
                output_path,
                source_catalog=CraterCatalog(image_id="left", craters=(
                    CraterEllipse("c1", 10.0, 20.0, 8.0, 6.0, 10.0, 0.9),
                )),
                target_catalog=CraterCatalog(image_id="right", craters=(
                    CraterEllipse("d1", 12.0, 22.0, 8.5, 6.5, 12.0, 0.88),
                )),
                coarse_alignment=CoarseAlignmentPrior(offset_x=2.0, offset_y=2.0, scale=1.0, rotation_deg=0.0, confidence=0.7),
                matches=(
                    CraterMatchRecord(
                        source_id="c1",
                        target_id="d1",
                        node_prior_score=0.8,
                        topology_score=0.9,
                        terrain_rescore=-0.1,
                        total_score=1.6,
                        accepted=True,
                        rejection_reason=None,
                    ),
                ),
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["source_image_id"], "left")
        self.assertEqual(payload["coarse_alignment"]["offset_x"], 2.0)
        self.assertEqual(payload["matches"][0]["target_id"], "d1")
        self.assertTrue(payload["matches"][0]["accepted"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_catalog_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.crater_catalog'`.

- [ ] **Step 3: Write minimal implementation**

Create `examples/image_match/crater_catalog.py`:

```python
"""Crater catalog types and disk I/O helpers.

Author: Geng Xun
Created: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater semantic matching catalog models and JSON artifact output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
from typing import Iterable


def _optional_float(value: str | None) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return float(text)


@dataclass(frozen=True)
class CraterEllipse:
    crater_id: str
    center_x: float
    center_y: float
    major_axis: float
    minor_axis: float
    angle_deg: float
    confidence: float
    shadow_ratio: float | None = None
    dem_height: float | None = None
    dem_slope_deg: float | None = None

    def __post_init__(self) -> None:
        if float(self.major_axis) <= 0.0:
            raise ValueError("major_axis must be positive.")
        if float(self.minor_axis) <= 0.0:
            raise ValueError("minor_axis must be positive.")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be within [0, 1].")


@dataclass(frozen=True)
class CraterCatalog:
    image_id: str
    craters: tuple[CraterEllipse, ...]


@dataclass(frozen=True)
class CoarseAlignmentPrior:
    offset_x: float
    offset_y: float
    scale: float
    rotation_deg: float
    confidence: float


@dataclass(frozen=True)
class CraterMatchRecord:
    source_id: str
    target_id: str | None
    node_prior_score: float
    topology_score: float
    terrain_rescore: float
    total_score: float
    accepted: bool
    rejection_reason: str | None


def read_crater_catalog_csv(path: str | Path, *, image_id: str) -> CraterCatalog:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        craters = []
        for row in reader:
            craters.append(
                CraterEllipse(
                    crater_id=str(row["crater_id"]).strip(),
                    center_x=float(row["center_x"]),
                    center_y=float(row["center_y"]),
                    major_axis=float(row["major_axis"]),
                    minor_axis=float(row["minor_axis"]),
                    angle_deg=float(row["angle_deg"]),
                    confidence=float(row["confidence"]),
                    shadow_ratio=_optional_float(row.get("shadow_ratio")),
                    dem_height=_optional_float(row.get("dem_height")),
                    dem_slope_deg=_optional_float(row.get("dem_slope_deg")),
                )
            )
    return CraterCatalog(image_id=str(image_id), craters=tuple(craters))


def write_crater_match_artifacts(
    output_path: str | Path,
    *,
    source_catalog: CraterCatalog,
    target_catalog: CraterCatalog,
    coarse_alignment: CoarseAlignmentPrior | None,
    matches: Iterable[CraterMatchRecord],
) -> Path:
    payload = {
        "source_image_id": source_catalog.image_id,
        "target_image_id": target_catalog.image_id,
        "coarse_alignment": None if coarse_alignment is None else asdict(coarse_alignment),
        "matches": [asdict(match) for match in matches],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_catalog_unit_test -v
```

Expected: PASS with `Ran 3 tests`.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/crater_catalog.py tests/unitTest/image_match_crater_catalog_unit_test.py
git commit -m "feat: add crater catalog types"
```

## Task 2: Local Crater Graph Construction and Topology Scoring

**Files:**
- Create: `examples/image_match/crater_graph.py`
- Test: `tests/unitTest/image_match_crater_graph_unit_test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unitTest/image_match_crater_graph_unit_test.py`:

```python
"""Unit tests for local crater topology graphs.

Author: Geng Xun
Created: 2026-06-04
Last Modified: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater-graph construction and topology scoring coverage.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.crater_catalog import CraterCatalog, CraterEllipse
from image_match.crater_graph import build_local_crater_graph, topology_similarity_score


def _catalog(image_id: str, points):
    return CraterCatalog(
        image_id=image_id,
        craters=tuple(
            CraterEllipse(
                crater_id=crater_id,
                center_x=x,
                center_y=y,
                major_axis=major_axis,
                minor_axis=minor_axis,
                angle_deg=angle_deg,
                confidence=0.9,
            )
            for crater_id, x, y, major_axis, minor_axis, angle_deg in points
        ),
    )


class ImageMatchCraterGraphUnitTest(unittest.TestCase):
    def test_build_local_crater_graph_keeps_expected_neighbors(self):
        catalog = _catalog(
            "left",
            (
                ("c1", 0.0, 0.0, 8.0, 6.0, 0.0),
                ("c2", 10.0, 0.0, 7.0, 5.0, 0.0),
                ("c3", 0.0, 12.0, 9.0, 7.0, 0.0),
                ("c4", 50.0, 50.0, 9.0, 7.0, 0.0),
            ),
        )

        graph = build_local_crater_graph(catalog, neighbor_count=2)

        self.assertEqual([edge.target_id for edge in graph["c1"]], ["c2", "c3"])
        self.assertEqual(len(graph["c4"]), 2)

    def test_topology_similarity_prefers_translated_constellation(self):
        source = _catalog(
            "src",
            (
                ("c1", 0.0, 0.0, 8.0, 6.0, 0.0),
                ("c2", 10.0, 0.0, 7.0, 5.0, 0.0),
                ("c3", 0.0, 10.0, 7.0, 5.0, 0.0),
            ),
        )
        aligned_target = _catalog(
            "aligned",
            (
                ("d1", 100.0, 100.0, 8.1, 6.2, 2.0),
                ("d2", 110.0, 100.0, 7.1, 5.1, 1.0),
                ("d3", 100.0, 110.0, 7.0, 5.2, 0.0),
            ),
        )
        scrambled_target = _catalog(
            "scrambled",
            (
                ("e1", 100.0, 100.0, 8.1, 6.2, 2.0),
                ("e2", 140.0, 100.0, 7.1, 5.1, 1.0),
                ("e3", 100.0, 140.0, 7.0, 5.2, 0.0),
            ),
        )

        good_score = topology_similarity_score(
            source.craters[0],
            aligned_target.craters[0],
            build_local_crater_graph(source, neighbor_count=2),
            build_local_crater_graph(aligned_target, neighbor_count=2),
        )
        bad_score = topology_similarity_score(
            source.craters[0],
            scrambled_target.craters[0],
            build_local_crater_graph(source, neighbor_count=2),
            build_local_crater_graph(scrambled_target, neighbor_count=2),
        )

        self.assertGreater(good_score, bad_score)
        self.assertGreater(good_score, 0.8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_graph_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.crater_graph'`.

- [ ] **Step 3: Write minimal implementation**

Create `examples/image_match/crater_graph.py`:

```python
"""Local crater topology graph helpers.

Author: Geng Xun
Created: 2026-06-04
Updated: 2026-06-04  Geng Xun added local crater graph construction and topology scoring helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .crater_catalog import CraterCatalog, CraterEllipse


@dataclass(frozen=True)
class CraterEdge:
    source_id: str
    target_id: str
    distance: float
    bearing_deg: float
    scale_ratio: float


def _bearing_degrees(source: CraterEllipse, target: CraterEllipse) -> float:
    return math.degrees(math.atan2(target.center_y - source.center_y, target.center_x - source.center_x))


def build_local_crater_graph(
    catalog: CraterCatalog,
    *,
    neighbor_count: int = 5,
    max_radius_pixels: float | None = None,
) -> dict[str, list[CraterEdge]]:
    graph: dict[str, list[CraterEdge]] = {}
    for source in catalog.craters:
        candidates: list[CraterEdge] = []
        for target in catalog.craters:
            if target.crater_id == source.crater_id:
                continue
            distance = math.hypot(target.center_x - source.center_x, target.center_y - source.center_y)
            if max_radius_pixels is not None and distance > max_radius_pixels:
                continue
            candidates.append(
                CraterEdge(
                    source_id=source.crater_id,
                    target_id=target.crater_id,
                    distance=distance,
                    bearing_deg=_bearing_degrees(source, target),
                    scale_ratio=target.major_axis / source.major_axis,
                )
            )
        graph[source.crater_id] = sorted(candidates, key=lambda edge: edge.distance)[:neighbor_count]
    return graph


def topology_similarity_score(
    source: CraterEllipse,
    target: CraterEllipse,
    source_graph: dict[str, list[CraterEdge]],
    target_graph: dict[str, list[CraterEdge]],
) -> float:
    source_edges = source_graph.get(source.crater_id, [])
    target_edges = target_graph.get(target.crater_id, [])
    pair_count = min(len(source_edges), len(target_edges))
    if pair_count == 0:
        return 0.0
    score_terms = []
    for left_edge, right_edge in zip(source_edges[:pair_count], target_edges[:pair_count]):
        distance_ratio_error = abs(left_edge.distance - right_edge.distance) / max(left_edge.distance, 1.0)
        bearing_error = abs(left_edge.bearing_deg - right_edge.bearing_deg) / 180.0
        scale_ratio_error = abs(left_edge.scale_ratio - right_edge.scale_ratio)
        score_terms.append(max(0.0, 1.0 - (distance_ratio_error + bearing_error + scale_ratio_error) / 3.0))
    return sum(score_terms) / len(score_terms)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_graph_unit_test -v
```

Expected: PASS with `Ran 2 tests`.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/crater_graph.py tests/unitTest/image_match_crater_graph_unit_test.py
git commit -m "feat: add crater topology graph scoring"
```

## Task 3: DEM Coarse Constraints and Terrain Re-Scoring

**Files:**
- Create: `examples/image_match/crater_constraints.py`
- Test: `tests/unitTest/image_match_crater_constraints_unit_test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unitTest/image_match_crater_constraints_unit_test.py`:

```python
"""Unit tests for crater DEM constraints.

Author: Geng Xun
Created: 2026-06-04
Last Modified: 2026-06-04
Updated: 2026-06-04  Geng Xun added DEM coarse-alignment and terrain re-score coverage.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.crater_catalog import CoarseAlignmentPrior, CraterCatalog, CraterEllipse
from image_match.crater_constraints import (
    build_search_window,
    estimate_coarse_alignment_from_render,
    filter_catalog_to_search_window,
    terrain_rescore,
)


class ImageMatchCraterConstraintsUnitTest(unittest.TestCase):
    def test_estimate_coarse_alignment_from_render_recovers_translation(self):
        source = np.zeros((64, 64), dtype=np.float32)
        source[20:30, 18:28] = 1.0
        target = np.zeros((64, 64), dtype=np.float32)
        target[24:34, 23:33] = 1.0

        prior = estimate_coarse_alignment_from_render(source, target)

        self.assertAlmostEqual(prior.offset_x, 5.0, delta=1.0)
        self.assertAlmostEqual(prior.offset_y, 4.0, delta=1.0)
        self.assertGreater(prior.confidence, 0.1)

    def test_filter_catalog_to_search_window_keeps_local_candidates(self):
        source_crater = CraterEllipse("c1", 10.0, 20.0, 8.0, 6.0, 0.0, 0.9)
        target_catalog = CraterCatalog(
            image_id="right",
            craters=(
                CraterEllipse("d1", 16.0, 24.0, 8.0, 6.0, 0.0, 0.9),
                CraterEllipse("d2", 80.0, 90.0, 8.0, 6.0, 0.0, 0.9),
            ),
        )

        window = build_search_window(source_crater, CoarseAlignmentPrior(5.0, 4.0, 1.0, 0.0, 0.8), radius_px=10.0)
        filtered = filter_catalog_to_search_window(target_catalog, window)

        self.assertEqual([crater.crater_id for crater in filtered], ["d1"])

    def test_terrain_rescore_penalizes_height_and_shadow_mismatch(self):
        source = CraterEllipse("c1", 10.0, 20.0, 8.0, 6.0, 0.0, 0.9, shadow_ratio=0.2, dem_height=100.0, dem_slope_deg=5.0)
        similar = CraterEllipse("d1", 12.0, 22.0, 8.5, 6.5, 2.0, 0.9, shadow_ratio=0.25, dem_height=101.0, dem_slope_deg=5.5)
        different = CraterEllipse("d2", 12.0, 22.0, 8.5, 6.5, 2.0, 0.9, shadow_ratio=0.9, dem_height=150.0, dem_slope_deg=30.0)

        self.assertGreater(terrain_rescore(source, similar), terrain_rescore(source, different))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_constraints_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.crater_constraints'`.

- [ ] **Step 3: Write minimal implementation**

Create `examples/image_match/crater_constraints.py`:

```python
"""DEM-derived coarse constraints and terrain re-scoring.

Author: Geng Xun
Created: 2026-06-04
Updated: 2026-06-04  Geng Xun added coarse render alignment and crater terrain re-scoring helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np

from .crater_catalog import CoarseAlignmentPrior, CraterCatalog, CraterEllipse


@dataclass(frozen=True)
class SearchWindow:
    center_x: float
    center_y: float
    radius_px: float


def estimate_coarse_alignment_from_render(source_image: np.ndarray, target_image: np.ndarray) -> CoarseAlignmentPrior:
    source = np.asarray(source_image, dtype=np.float32)
    target = np.asarray(target_image, dtype=np.float32)
    shift, response = cv2.phaseCorrelate(source, target)
    return CoarseAlignmentPrior(
        offset_x=float(shift[0]),
        offset_y=float(shift[1]),
        scale=1.0,
        rotation_deg=0.0,
        confidence=float(max(response, 0.0)),
    )


def build_search_window(source_crater: CraterEllipse, coarse_alignment: CoarseAlignmentPrior, *, radius_px: float) -> SearchWindow:
    return SearchWindow(
        center_x=source_crater.center_x + coarse_alignment.offset_x,
        center_y=source_crater.center_y + coarse_alignment.offset_y,
        radius_px=float(radius_px),
    )


def filter_catalog_to_search_window(target_catalog: CraterCatalog, search_window: SearchWindow) -> list[CraterEllipse]:
    kept = []
    for crater in target_catalog.craters:
        distance = math.hypot(crater.center_x - search_window.center_x, crater.center_y - search_window.center_y)
        if distance <= search_window.radius_px:
            kept.append(crater)
    return kept


def terrain_rescore(source: CraterEllipse, target: CraterEllipse) -> float:
    height_penalty = 0.0 if source.dem_height is None or target.dem_height is None else abs(source.dem_height - target.dem_height) / 50.0
    slope_penalty = 0.0 if source.dem_slope_deg is None or target.dem_slope_deg is None else abs(source.dem_slope_deg - target.dem_slope_deg) / 20.0
    shadow_penalty = 0.0 if source.shadow_ratio is None or target.shadow_ratio is None else abs(source.shadow_ratio - target.shadow_ratio)
    return -(height_penalty + slope_penalty + shadow_penalty)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_constraints_unit_test -v
```

Expected: PASS with `Ran 3 tests`.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/crater_constraints.py tests/unitTest/image_match_crater_constraints_unit_test.py
git commit -m "feat: add crater DEM constraints"
```

## Task 4: Baselines and Full Semantic Matcher Orchestration

**Files:**
- Create: `examples/image_match/crater_semantic_match.py`
- Test: `tests/unitTest/image_match_crater_semantic_match_unit_test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unitTest/image_match_crater_semantic_match_unit_test.py`:

```python
"""Unit tests for crater semantic matching orchestration.

Author: Geng Xun
Created: 2026-06-04
Last Modified: 2026-06-04
Updated: 2026-06-04  Geng Xun added shape-only, ellipse-raster baseline, and semantic matcher coverage.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.crater_catalog import CoarseAlignmentPrior, CraterCatalog, CraterEllipse
from image_match.crater_semantic_match import (
    render_crater_ellipse_raster,
    run_crater_semantic_match,
    run_shape_only_baseline,
)


def _catalog(image_id: str, rows):
    return CraterCatalog(
        image_id=image_id,
        craters=tuple(
            CraterEllipse(
                crater_id=crater_id,
                center_x=x,
                center_y=y,
                major_axis=major_axis,
                minor_axis=minor_axis,
                angle_deg=angle_deg,
                confidence=confidence,
                shadow_ratio=shadow_ratio,
                dem_height=dem_height,
                dem_slope_deg=dem_slope_deg,
            )
            for crater_id, x, y, major_axis, minor_axis, angle_deg, confidence, shadow_ratio, dem_height, dem_slope_deg in rows
        ),
    )


class ImageMatchCraterSemanticMatchUnitTest(unittest.TestCase):
    def test_render_crater_ellipse_raster_draws_nonzero_pixels(self):
        catalog = _catalog("left", (("c1", 20.0, 20.0, 10.0, 8.0, 0.0, 0.9, 0.2, 100.0, 5.0),))

        raster = render_crater_ellipse_raster(catalog, image_shape=(64, 64))

        self.assertEqual(raster.shape, (64, 64))
        self.assertGreater(int(raster.sum()), 0)

    def test_shape_only_baseline_prefers_axis_and_angle_similarity(self):
        source = _catalog("left", (("c1", 10.0, 20.0, 8.0, 6.0, 10.0, 0.9, 0.2, 100.0, 5.0),))
        target = _catalog(
            "right",
            (
                ("d1", 16.0, 24.0, 8.1, 6.1, 11.0, 0.9, 0.2, 101.0, 5.0),
                ("d2", 16.0, 24.0, 14.0, 3.0, 80.0, 0.9, 0.2, 101.0, 5.0),
            ),
        )

        matches = run_shape_only_baseline(source, target, CoarseAlignmentPrior(6.0, 4.0, 1.0, 0.0, 0.8), radius_px=10.0)

        self.assertEqual(matches[0].target_id, "d1")
        self.assertTrue(matches[0].accepted)

    def test_run_crater_semantic_match_returns_score_components(self):
        source = _catalog(
            "left",
            (
                ("c1", 0.0, 0.0, 8.0, 6.0, 0.0, 0.9, 0.2, 100.0, 5.0),
                ("c2", 10.0, 0.0, 7.0, 5.0, 0.0, 0.8, 0.3, 101.0, 5.5),
                ("c3", 0.0, 10.0, 7.0, 5.0, 0.0, 0.8, 0.25, 99.5, 4.5),
            ),
        )
        target = _catalog(
            "right",
            (
                ("d1", 100.0, 100.0, 8.1, 6.2, 1.0, 0.9, 0.22, 100.5, 5.2),
                ("d2", 110.0, 100.0, 7.0, 5.1, 1.0, 0.8, 0.28, 101.0, 5.3),
                ("d3", 100.0, 110.0, 7.1, 5.1, 1.0, 0.8, 0.24, 99.8, 4.7),
            ),
        )

        result = run_crater_semantic_match(
            source,
            target,
            coarse_alignment=CoarseAlignmentPrior(100.0, 100.0, 1.0, 0.0, 0.9),
            radius_px=12.0,
            neighbor_count=2,
            candidate_limit=2,
        )

        self.assertEqual(result["matches"][0].target_id, "d1")
        self.assertGreater(len(result["candidate_scores"]), 0)
        self.assertIn("node_prior_score", result["matches"][0].__dict__)
        self.assertIn("topology_score", result["matches"][0].__dict__)
        self.assertIn("terrain_rescore", result["matches"][0].__dict__)

    def test_ellipse_raster_baseline_uses_existing_deep_adapter(self):
        source = _catalog("left", (("c1", 20.0, 20.0, 10.0, 8.0, 0.0, 0.9, 0.2, 100.0, 5.0),))
        target = _catalog("right", (("d1", 25.0, 24.0, 10.0, 8.0, 0.0, 0.9, 0.2, 100.0, 5.0),))
        fake_result = mock.Mock(left_keypoints=np.zeros((1, 2)), right_keypoints=np.zeros((1, 2)), matches=np.array([0]), scores=np.array([1.0]))

        with mock.patch("image_match.crater_semantic_match.DeepMatcherAdapter") as adapter_class:
            adapter = adapter_class.return_value
            adapter.match_pair.return_value = fake_result
            summary = run_crater_semantic_match(
                source,
                target,
                coarse_alignment=CoarseAlignmentPrior(5.0, 4.0, 1.0, 0.0, 0.8),
                radius_px=10.0,
                neighbor_count=1,
                candidate_limit=1,
                baseline_method="ellipse_raster_lightglue",
            )

        adapter.match_pair.assert_called_once()
        self.assertEqual(summary["baseline_summary"]["match_count"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_semantic_match_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.crater_semantic_match'`.

- [ ] **Step 3: Write minimal implementation**

Create `examples/image_match/crater_semantic_match.py`:

```python
"""Standalone crater semantic matching orchestration.

Author: Geng Xun
Created: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater shape baselines, ellipse-raster LightGlue baseline, and topology-first semantic matching.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

if __package__ in {None, ""}:
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from image_match.crater_catalog import CoarseAlignmentPrior, CraterCatalog, CraterMatchRecord
    from image_match.crater_constraints import build_search_window, filter_catalog_to_search_window, terrain_rescore
    from image_match.crater_graph import build_local_crater_graph, topology_similarity_score
    from image_match.deep_adapter import DeepMatcherAdapter
else:
    from .crater_catalog import CoarseAlignmentPrior, CraterCatalog, CraterMatchRecord
    from .crater_constraints import build_search_window, filter_catalog_to_search_window, terrain_rescore
    from .crater_graph import build_local_crater_graph, topology_similarity_score
    from .deep_adapter import DeepMatcherAdapter


def render_crater_ellipse_raster(catalog: CraterCatalog, *, image_shape: tuple[int, int]) -> np.ndarray:
    canvas = np.zeros(image_shape, dtype=np.uint8)
    for crater in catalog.craters:
        center = (int(round(crater.center_x)), int(round(crater.center_y)))
        axes = (max(1, int(round(crater.major_axis / 2.0))), max(1, int(round(crater.minor_axis / 2.0))))
        cv2.ellipse(canvas, center, axes, crater.angle_deg, 0.0, 360.0, 255, 1)
    return canvas


def _node_prior_score(source, target) -> float:
    axis_error = abs(source.major_axis - target.major_axis) / max(source.major_axis, 1.0)
    minor_error = abs(source.minor_axis - target.minor_axis) / max(source.minor_axis, 1.0)
    angle_error = abs(source.angle_deg - target.angle_deg) / 180.0
    confidence_term = 1.0 - abs(source.confidence - target.confidence)
    return max(0.0, 1.0 - (axis_error + minor_error + angle_error) / 3.0) * max(0.0, confidence_term)


def run_shape_only_baseline(
    source_catalog: CraterCatalog,
    target_catalog: CraterCatalog,
    coarse_alignment: CoarseAlignmentPrior,
    *,
    radius_px: float,
) -> list[CraterMatchRecord]:
    matches: list[CraterMatchRecord] = []
    for source in source_catalog.craters:
        candidates = filter_catalog_to_search_window(target_catalog, build_search_window(source, coarse_alignment, radius_px=radius_px))
        ranked = sorted(candidates, key=lambda target: _node_prior_score(source, target), reverse=True)
        best = ranked[0] if ranked else None
        score = 0.0 if best is None else _node_prior_score(source, best)
        matches.append(
            CraterMatchRecord(
                source_id=source.crater_id,
                target_id=None if best is None else best.crater_id,
                node_prior_score=score,
                topology_score=0.0,
                terrain_rescore=0.0,
                total_score=score,
                accepted=best is not None,
                rejection_reason=None if best is not None else "no_candidate_in_search_window",
            )
        )
    return matches


def run_crater_semantic_match(
    source_catalog: CraterCatalog,
    target_catalog: CraterCatalog,
    *,
    coarse_alignment: CoarseAlignmentPrior,
    radius_px: float,
    neighbor_count: int,
    candidate_limit: int,
    baseline_method: str | None = None,
) -> dict[str, Any]:
    if baseline_method == "ellipse_raster_lightglue":
        adapter = DeepMatcherAdapter(prefer_gpu=True)
        result = adapter.match_pair(
            matcher_method="lightglue",
            left_image=render_crater_ellipse_raster(source_catalog, image_shape=(512, 512)),
            right_image=render_crater_ellipse_raster(target_catalog, image_shape=(512, 512)),
        )
        return {"matches": (), "candidate_scores": (), "baseline_summary": {"match_count": len(result.matches)}}

    source_graph = build_local_crater_graph(source_catalog, neighbor_count=neighbor_count)
    target_graph = build_local_crater_graph(target_catalog, neighbor_count=neighbor_count)
    final_matches: list[CraterMatchRecord] = []
    candidate_scores: list[dict[str, float | str | None]] = []
    for source in source_catalog.craters:
        candidates = filter_catalog_to_search_window(target_catalog, build_search_window(source, coarse_alignment, radius_px=radius_px))
        scored = []
        for target in candidates[:candidate_limit]:
            node_score = _node_prior_score(source, target)
            topo_score = topology_similarity_score(source, target, source_graph, target_graph)
            terrain_score = terrain_rescore(source, target)
            total_score = node_score + topo_score + terrain_score
            scored.append((total_score, target, node_score, topo_score, terrain_score))
            candidate_scores.append(
                {
                    "source_id": source.crater_id,
                    "target_id": target.crater_id,
                    "node_prior_score": node_score,
                    "topology_score": topo_score,
                    "terrain_rescore": terrain_score,
                    "total_score": total_score,
                }
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            final_matches.append(
                CraterMatchRecord(source.crater_id, None, 0.0, 0.0, 0.0, 0.0, False, "no_candidate_in_search_window")
            )
            continue
        total_score, best_target, node_score, topo_score, terrain_score = scored[0]
        final_matches.append(
            CraterMatchRecord(
                source_id=source.crater_id,
                target_id=best_target.crater_id,
                node_prior_score=node_score,
                topology_score=topo_score,
                terrain_rescore=terrain_score,
                total_score=total_score,
                accepted=True,
                rejection_reason=None,
            )
        )
    return {"matches": tuple(final_matches), "candidate_scores": tuple(candidate_scores), "baseline_summary": None}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_semantic_match_unit_test -v
```

Expected: PASS with `Ran 4 tests`.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/crater_semantic_match.py tests/unitTest/image_match_crater_semantic_match_unit_test.py
git commit -m "feat: add crater semantic matcher"
```

## Task 5: Evaluation Metrics and Standalone CLI

**Files:**
- Create: `examples/image_match/crater_semantic_eval.py`
- Modify: `examples/image_match/crater_semantic_match.py`
- Test: `tests/unitTest/image_match_crater_eval_unit_test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unitTest/image_match_crater_eval_unit_test.py`:

```python
"""Unit tests for crater semantic evaluation metrics and CLI wiring.

Author: Geng Xun
Created: 2026-06-04
Last Modified: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater semantic metric aggregation and CLI smoke coverage.
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.crater_catalog import CraterMatchRecord
from image_match.crater_semantic_eval import summarize_crater_matching


class ImageMatchCraterEvalUnitTest(unittest.TestCase):
    def test_summarize_crater_matching_computes_shadow_strata(self):
        summary = summarize_crater_matching(
            matches=(
                CraterMatchRecord("c1", "d1", 0.8, 0.9, -0.1, 1.6, True, None),
                CraterMatchRecord("c2", None, 0.2, 0.0, 0.0, 0.2, False, "no_candidate_in_search_window"),
            ),
            ground_truth={"c1": "d1", "c2": "d2"},
            shadow_by_source={"c1": 0.2, "c2": 0.85},
        )

        self.assertAlmostEqual(summary["recall"], 0.5)
        self.assertAlmostEqual(summary["precision"], 1.0)
        self.assertIn("low_shadow", summary["shadow_strata"])
        self.assertIn("high_shadow", summary["shadow_strata"])

    def test_cli_writes_match_and_metric_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            left_csv = tmp_path / "left.csv"
            right_csv = tmp_path / "right.csv"
            truth_json = tmp_path / "truth.json"
            output_json = tmp_path / "result.json"
            left_csv.write_text(
                "crater_id,center_x,center_y,major_axis,minor_axis,angle_deg,confidence,shadow_ratio,dem_height,dem_slope_deg\n"
                "c1,10,20,8,6,0,0.9,0.2,100,5\n",
                encoding="utf-8",
            )
            right_csv.write_text(
                "crater_id,center_x,center_y,major_axis,minor_axis,angle_deg,confidence,shadow_ratio,dem_height,dem_slope_deg\n"
                "d1,16,24,8,6,0,0.9,0.2,100,5\n",
                encoding="utf-8",
            )
            truth_json.write_text(json.dumps({"c1": "d1"}), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXAMPLES_DIR / "image_match" / "crater_semantic_match.py"),
                    "--left-crater-csv",
                    str(left_csv),
                    "--right-crater-csv",
                    str(right_csv),
                    "--output-json",
                    str(output_json),
                    "--ground-truth-json",
                    str(truth_json),
                    "--offset-x",
                    "6",
                    "--offset-y",
                    "4",
                    "--radius-px",
                    "10",
                ],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(output_json.read_text(encoding="utf-8"))

        self.assertIn("matches", payload)
        self.assertIn("metrics", payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_eval_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.crater_semantic_eval'`.

- [ ] **Step 3: Write minimal implementation**

Create `examples/image_match/crater_semantic_eval.py`:

```python
"""Evaluation helpers for crater semantic matching.

Author: Geng Xun
Created: 2026-06-04
Updated: 2026-06-04  Geng Xun added crater match recall/precision and shadow-stratified summaries.
"""

from __future__ import annotations

from .crater_catalog import CraterMatchRecord


def summarize_crater_matching(*, matches, ground_truth, shadow_by_source):
    accepted = [match for match in matches if match.accepted and match.target_id is not None]
    correct = [match for match in accepted if ground_truth.get(match.source_id) == match.target_id]
    recall = 0.0 if not ground_truth else len(correct) / len(ground_truth)
    precision = 0.0 if not accepted else len(correct) / len(accepted)
    low_shadow = [match.source_id for match in matches if shadow_by_source.get(match.source_id, 0.0) < 0.5]
    high_shadow = [match.source_id for match in matches if shadow_by_source.get(match.source_id, 0.0) >= 0.5]
    return {
        "recall": recall,
        "precision": precision,
        "graph_consistency": 0.0 if not accepted else sum(match.topology_score for match in accepted) / len(accepted),
        "shadow_strata": {
            "low_shadow": {"count": len(low_shadow)},
            "high_shadow": {"count": len(high_shadow)},
        },
    }
```

Modify `examples/image_match/crater_semantic_match.py` to add CLI wiring:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from image_match.crater_catalog import CoarseAlignmentPrior, read_crater_catalog_csv, write_crater_match_artifacts
    from image_match.crater_semantic_eval import summarize_crater_matching
else:
    from .crater_catalog import CoarseAlignmentPrior, read_crater_catalog_csv, write_crater_match_artifacts
    from .crater_semantic_eval import summarize_crater_matching


def _parse_args():
    parser = argparse.ArgumentParser(description="Run DEM-constrained crater semantic matching.")
    parser.add_argument("--left-crater-csv", required=True)
    parser.add_argument("--right-crater-csv", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--ground-truth-json", default=None)
    parser.add_argument("--offset-x", type=float, required=True)
    parser.add_argument("--offset-y", type=float, required=True)
    parser.add_argument("--radius-px", type=float, default=40.0)
    parser.add_argument("--neighbor-count", type=int, default=5)
    parser.add_argument("--candidate-limit", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    left_catalog = read_crater_catalog_csv(args.left_crater_csv, image_id="left")
    right_catalog = read_crater_catalog_csv(args.right_crater_csv, image_id="right")
    coarse = CoarseAlignmentPrior(args.offset_x, args.offset_y, 1.0, 0.0, 1.0)
    result = run_crater_semantic_match(
        left_catalog,
        right_catalog,
        coarse_alignment=coarse,
        radius_px=args.radius_px,
        neighbor_count=args.neighbor_count,
        candidate_limit=args.candidate_limit,
    )
    matches = tuple(result["matches"])
    metrics = None
    if args.ground_truth_json:
        ground_truth = json.loads(Path(args.ground_truth_json).read_text(encoding="utf-8"))
        shadow_by_source = {crater.crater_id: crater.shadow_ratio or 0.0 for crater in left_catalog.craters}
        metrics = summarize_crater_matching(matches=matches, ground_truth=ground_truth, shadow_by_source=shadow_by_source)
    payload_path = write_crater_match_artifacts(
        args.output_json,
        source_catalog=left_catalog,
        target_catalog=right_catalog,
        coarse_alignment=coarse,
        matches=matches,
    )
    payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
    payload["candidate_scores"] = list(result["candidate_scores"])
    payload["metrics"] = metrics
    Path(payload_path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_crater_eval_unit_test -v
```

Expected: PASS with `Ran 2 tests`.

- [ ] **Step 5: Commit**

```bash
git add \
  examples/image_match/crater_semantic_eval.py \
  examples/image_match/crater_semantic_match.py \
  tests/unitTest/image_match_crater_eval_unit_test.py
git commit -m "feat: add crater semantic evaluation cli"
```

## Final Verification Pass

- [ ] **Step 1: Run the focused crater-semantic test suite**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.image_match_crater_catalog_unit_test \
  tests.unitTest.image_match_crater_graph_unit_test \
  tests.unitTest.image_match_crater_constraints_unit_test \
  tests.unitTest.image_match_crater_semantic_match_unit_test \
  tests.unitTest.image_match_crater_eval_unit_test \
  -v
```

Expected: PASS with all crater-semantic tests green.

- [ ] **Step 2: Run one CLI smoke test on synthetic CSV inputs**

```bash
python - <<'PY'
from pathlib import Path
import json

Path("/tmp/left.csv").write_text(
    "crater_id,center_x,center_y,major_axis,minor_axis,angle_deg,confidence,shadow_ratio,dem_height,dem_slope_deg\n"
    "c1,10,20,8,6,0,0.9,0.2,100,5\n",
    encoding="utf-8",
)
Path("/tmp/right.csv").write_text(
    "crater_id,center_x,center_y,major_axis,minor_axis,angle_deg,confidence,shadow_ratio,dem_height,dem_slope_deg\n"
    "d1,16,24,8,6,0,0.9,0.2,100,5\n",
    encoding="utf-8",
)
Path("/tmp/truth.json").write_text(json.dumps({"c1": "d1"}), encoding="utf-8")
PY
```

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/image_match/crater_semantic_match.py \
  --left-crater-csv /tmp/left.csv \
  --right-crater-csv /tmp/right.csv \
  --output-json /tmp/crater_semantic_result.json \
  --ground-truth-json /tmp/truth.json \
  --offset-x 6 \
  --offset-y 4 \
  --radius-px 10
```

Expected: exit code `0` and `/tmp/crater_semantic_result.json` containing `matches` and `metrics`.

- [ ] **Step 3: Commit the final verification update if any test-only edits were needed**

```bash
git add examples/image_match/*.py tests/unitTest/image_match_crater*_unit_test.py
git commit -m "test: verify crater semantic matching workflow"
```
