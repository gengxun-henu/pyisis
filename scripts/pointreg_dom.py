#!/usr/bin/env python3
"""DOM-space point registration for ISIS ControlNets.

`pointreg_dom` follows the same high-level role as ISIS `pointreg`, but it
performs the image registration in map-projected DOM space:

1. project each original-image measure to its paired DOM cube;
2. register candidate DOM chips against the reference DOM chip;
3. project the matched DOM coordinate back to the original image;
4. update the original-image ControlNet measure.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class ImagePair:
    original_path: str
    dom_path: str
    serial: str


@dataclass(frozen=True, slots=True)
class DomPoint:
    sample: float
    line: float


@dataclass(slots=True)
class RegistrationSummary:
    updated_measures: int = 0
    failed_measures: int = 0
    skipped_measures: int = 0
    failure_reasons: Counter[str] = field(default_factory=Counter)

    def add_failure(self, reason: str) -> None:
        self.failed_measures += 1
        self.failure_reasons[reason] += 1

    def merge(self, other: "RegistrationSummary") -> None:
        self.updated_measures += other.updated_measures
        self.failed_measures += other.failed_measures
        self.skipped_measures += other.skipped_measures
        self.failure_reasons.update(other.failure_reasons)


class PointregDomFailure(RuntimeError):
    pass


def _read_list(path: str | Path) -> list[str]:
    base = Path(path).resolve().parent
    values: list[str] = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        candidate = Path(line)
        if not candidate.is_absolute():
            candidate = base / candidate
        values.append(str(candidate))
    return values


def validate_paired_image_lists(
    original_images: Iterable[str],
    dom_images: Iterable[str],
    *,
    serial_resolver: Callable[[str], str],
    strict_serial_check: bool = True,
) -> dict[str, ImagePair]:
    originals = list(original_images)
    doms = list(dom_images)
    if len(originals) != len(doms):
        raise ValueError(
            f"Original image list and DOM image list must have the same length: "
            f"{len(originals)} != {len(doms)}."
        )

    pairs: dict[str, ImagePair] = {}
    for index, (original_path, dom_path) in enumerate(zip(originals, doms, strict=True), start=1):
        original_serial = serial_resolver(original_path)
        dom_serial = serial_resolver(dom_path)
        if strict_serial_check and original_serial != dom_serial:
            raise ValueError(
                f"Image pair #{index} serial mismatch: original {original_path} -> "
                f"{original_serial}, DOM {dom_path} -> {dom_serial}."
            )
        if original_serial in pairs:
            raise ValueError(f"Duplicate original image serial in fromlist: {original_serial}.")
        pairs[original_serial] = ImagePair(original_path=original_path, dom_path=dom_path, serial=original_serial)
    return pairs


def _reference_measure_index(point) -> int:
    if hasattr(point, "has_ref_measure") and point.has_ref_measure():
        return int(point.index_of_ref_measure())
    return 0


def _set_registered_measure_type(measure, registered_measure_type) -> None:
    if isinstance(registered_measure_type, str):
        # Unit tests use plain strings. The real CLI passes the pybind enum.
        measure.set_type(registered_measure_type)
    else:
        measure.set_type(registered_measure_type)


def register_control_point_in_dom_space(
    point,
    image_pairs_by_serial: dict[str, ImagePair],
    *,
    original_to_dom: Callable[[ImagePair, float, float], DomPoint],
    dom_to_original: Callable[[ImagePair, float, float], tuple[float, float]],
    match_dom: Callable[[ImagePair, ImagePair, DomPoint, DomPoint], DomPoint],
    registered_measure_type,
    chooser_name: str = "pointreg_dom",
) -> RegistrationSummary:
    summary = RegistrationSummary()
    if point.get_num_measures() <= 1:
        summary.skipped_measures += point.get_num_measures()
        return summary

    ref_index = _reference_measure_index(point)
    ref_measure = point.get_measure(ref_index)
    ref_serial = ref_measure.get_cube_serial_number()
    ref_pair = image_pairs_by_serial.get(ref_serial)
    if ref_pair is None:
        summary.add_failure("reference_serial_not_in_fromlist")
        return summary

    try:
        ref_dom_point = original_to_dom(ref_pair, ref_measure.get_sample(), ref_measure.get_line())
    except PointregDomFailure as exc:
        summary.add_failure(str(exc) or "reference_projection_failed")
        return summary
    except Exception:
        summary.add_failure("reference_processing_exception")
        return summary

    for measure_index in range(point.get_num_measures()):
        if measure_index == ref_index:
            continue

        measure = point.get_measure(measure_index)
        serial = measure.get_cube_serial_number()
        pair = image_pairs_by_serial.get(serial)
        if pair is None:
            summary.add_failure("candidate_serial_not_in_fromlist")
            continue

        original_sample = measure.get_sample()
        original_line = measure.get_line()
        try:
            candidate_dom_guess = original_to_dom(pair, original_sample, original_line)
            matched_dom = match_dom(ref_pair, pair, ref_dom_point, candidate_dom_guess)
            matched_original_sample, matched_original_line = dom_to_original(
                pair,
                matched_dom.sample,
                matched_dom.line,
            )
        except PointregDomFailure as exc:
            summary.add_failure(str(exc) or "candidate_registration_failed")
            continue
        except Exception:
            summary.add_failure("candidate_processing_exception")
            continue

        measure.set_apriori_sample(original_sample)
        measure.set_apriori_line(original_line)
        measure.set_coordinate(matched_original_sample, matched_original_line)
        _set_registered_measure_type(measure, registered_measure_type)
        if hasattr(measure, "set_chooser_name"):
            measure.set_chooser_name(chooser_name)
        summary.updated_measures += 1

    return summary


class PyisisDomRegistrar:
    def __init__(
        self,
        *,
        ip,
        deffile: str | Path,
        dom_band: int = 1,
        original_band: int = 1,
        max_open_cubes: int = 64,
    ) -> None:
        self.ip = ip
        self.dom_band = dom_band
        self.original_band = original_band
        self.max_open_cubes = max_open_cubes
        self.registration_template = ip.Pvl()
        self.registration_template.read(str(deffile))
        self._cube_cache = OrderedDict()

    def close(self) -> None:
        for cube in self._cube_cache.values():
            if cube.is_open():
                cube.close()

    def _cube(self, path: str):
        cube = self._cube_cache.get(path)
        if cube is None:
            cube = self.ip.Cube()
            cube.open(path, "r")
            self._cube_cache[path] = cube
            while len(self._cube_cache) > self.max_open_cubes:
                _, old_cube = self._cube_cache.popitem(last=False)
                if old_cube.is_open():
                    old_cube.close()
        else:
            self._cube_cache.move_to_end(path)
        return cube

    def _ground_map(self, path: str, priority):
        ground_map = self.ip.UniversalGroundMap(self._cube(path), priority)
        if priority == self.ip.UniversalGroundMap.CameraPriority.ProjectionFirst:
            ground_map.set_band(self.dom_band)
        else:
            ground_map.set_band(self.original_band)
        return ground_map

    def serial(self, path: str) -> str:
        return self.ip.SerialNumber.compose(path)

    def original_to_dom(self, pair: ImagePair, sample: float, line: float) -> DomPoint:
        original_map = self._ground_map(
            pair.original_path,
            self.ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        dom_map = self._ground_map(
            pair.dom_path,
            self.ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        if not original_map.set_image(sample, line):
            raise PointregDomFailure("original_to_ground_failed")
        latitude = original_map.universal_latitude()
        longitude = original_map.universal_longitude()
        if not dom_map.set_universal_ground(latitude, longitude):
            raise PointregDomFailure("ground_to_dom_failed")
        return DomPoint(sample=dom_map.sample(), line=dom_map.line())

    def dom_to_original(self, pair: ImagePair, sample: float, line: float) -> tuple[float, float]:
        dom_map = self._ground_map(
            pair.dom_path,
            self.ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        original_map = self._ground_map(
            pair.original_path,
            self.ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        if not dom_map.set_image(sample, line):
            raise PointregDomFailure("dom_to_ground_failed")
        latitude = dom_map.universal_latitude()
        longitude = dom_map.universal_longitude()
        if not original_map.set_universal_ground(latitude, longitude):
            raise PointregDomFailure("ground_to_original_failed")
        return original_map.sample(), original_map.line()

    def match_dom(
        self,
        ref_pair: ImagePair,
        candidate_pair: ImagePair,
        ref_dom_point: DomPoint,
        candidate_dom_guess: DomPoint,
    ) -> DomPoint:
        matcher = self.ip.MaximumCorrelation(self.registration_template)
        pattern_chip = matcher.pattern_chip()
        pattern_chip.tack_cube(ref_dom_point.sample, ref_dom_point.line)
        pattern_chip.load(self._cube(ref_pair.dom_path))

        search_chip = matcher.search_chip()
        search_chip.tack_cube(candidate_dom_guess.sample, candidate_dom_guess.line)
        search_chip.load(self._cube(candidate_pair.dom_path))

        matcher.register()
        if not matcher.success():
            raise PointregDomFailure("dom_registration_failed")
        return DomPoint(sample=matcher.cube_sample(), line=matcher.cube_line())


def run_pointreg_dom(args: argparse.Namespace) -> RegistrationSummary:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "tests" / "unitTest"))
    from _unit_test_support import ip  # Keeps imports aligned with this repo's pyisis test bootstrap.

    original_images = _read_list(args.fromlist)
    dom_images = _read_list(args.domlist)

    registrar = PyisisDomRegistrar(
        ip=ip,
        deffile=args.deffile,
        dom_band=args.dom_band,
        original_band=args.original_band,
        max_open_cubes=args.max_open_cubes,
    )
    try:
        image_pairs = validate_paired_image_lists(
            original_images,
            dom_images,
            serial_resolver=registrar.serial,
            strict_serial_check=not args.skip_serial_check,
        )

        net = ip.ControlNet(str(args.cnet))
        summary = RegistrationSummary()
        registered_type = ip.ControlMeasure.MeasureType.RegisteredSubPixel
        for point_index, point in enumerate(net.get_points(), start=1):
            point_summary = register_control_point_in_dom_space(
                point,
                image_pairs,
                original_to_dom=registrar.original_to_dom,
                dom_to_original=registrar.dom_to_original,
                match_dom=registrar.match_dom,
                registered_measure_type=registered_type,
                chooser_name="pointreg_dom",
            )
            summary.merge(point_summary)
            if point_index % 500 == 0:
                print(
                    f"[pointreg_dom] processed_points={point_index} "
                    f"updated={summary.updated_measures} failed={summary.failed_measures}",
                    file=sys.stderr,
                    flush=True,
                )
        net.write(str(args.onet), args.pvl)
        return summary
    finally:
        registrar.close()


def normalize_isis_style_args(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in argv:
        if token.startswith("--") or "=" not in token:
            normalized.append(token)
            continue
        key, value = token.split("=", 1)
        normalized.extend([f"--{key.strip().lower()}", value])
    return normalized


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Register ISIS ControlNet measures in DOM space.")
    parser.add_argument("--fromlist", required=True, help="Original-image cube list, matching ISIS pointreg fromlist.")
    parser.add_argument("--domlist", required=True, help="DOM cube list aligned one-to-one with --fromlist.")
    parser.add_argument("--cnet", required=True, help="Input ISIS control network.")
    parser.add_argument("--deffile", required=True, help="ISIS AutoReg/pointreg registration template PVL.")
    parser.add_argument("--onet", required=True, help="Output ISIS control network.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band used for DOM projection and matching.")
    parser.add_argument("--original-band", type=int, default=1, help="Band used for original-image camera projection.")
    parser.add_argument("--max-open-cubes", type=int, default=64, help="Maximum number of ISIS cubes kept open at once.")
    parser.add_argument("--skip-serial-check", action="store_true", help="Allow original/DOM list rows with different serial numbers.")
    parser.add_argument("--pvl", action="store_true", help="Write output ControlNet in PVL text format. Default writes binary .net.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(normalize_isis_style_args(argv or sys.argv[1:]))
    summary = run_pointreg_dom(args)
    print(f"Updated measures: {summary.updated_measures}")
    print(f"Failed measures: {summary.failed_measures}")
    print(f"Skipped measures: {summary.skipped_measures}")
    for reason, count in sorted(summary.failure_reasons.items()):
        print(f"  {reason}: {count}")
    return 0 if summary.failed_measures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
