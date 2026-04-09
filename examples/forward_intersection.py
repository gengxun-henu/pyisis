"""
Forward-intersection example based on `Isis::Stereo::elevation`.

This script opens two cubes, sets a conjugate point on the left image, optionally
uses a SHIFT-style correlation match (`MaximumCorrelation`) to refine the right
image point, and then calls `Stereo.elevation(...)` to compute the 3D
intersection.

Author: Geng Xun
Created: 2026-04-09
Updated: 2026-04-09  Geng Xun implemented a reusable forward-intersection example with optional SHIFT-style tie-point matching and pointreg-style right-image seeding.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT / "tests" / "data" / "isisdata" / "mockup"


def _has_leap_second_kernels(data_root: Path) -> bool:
	lsk_dir = data_root / "base" / "kernels" / "lsk"
	return lsk_dir.exists() and any(lsk_dir.glob("naif*.tls"))


def bootstrap_runtime_environment() -> None:
	"""Make the standalone example runnable from the repository checkout."""
	configured_isisdata = os.environ.get("ISISDATA")

	if str(BUILD_PYTHON_DIR) not in sys.path and BUILD_PYTHON_DIR.exists():
		sys.path.insert(0, str(BUILD_PYTHON_DIR))

	if configured_isisdata and _has_leap_second_kernels(Path(configured_isisdata)):
		return

	if _has_leap_second_kernels(WORKSPACE_ISISDATA_MOCKUP):
		os.environ["ISISDATA"] = str(WORKSPACE_ISISDATA_MOCKUP)


bootstrap_runtime_environment()

import isis_pybind as ip


SUCCESS_STATUSES = {
	ip.AutoReg.RegisterStatus.SuccessPixel,
	ip.AutoReg.RegisterStatus.SuccessSubPixel,
}


@dataclass
class TiePointMatchResult:
	left_sample: float
	left_line: float
	right_sample: float
	right_line: float
	right_guess_sample: float
	right_guess_line: float
	status: str
	goodness_of_fit: float


@dataclass
class ForwardIntersectionResult:
	left_cube: str
	right_cube: str
	left_sample: float
	left_line: float
	right_sample: float
	right_line: float
	matched_by_shift: bool
	match_status: Optional[str]
	goodness_of_fit: Optional[float]
	radius_meters: float
	latitude_degrees: float
	longitude_degrees: float
	separation_angle_degrees: float
	error_meters: float
	x_km: float
	y_km: float
	z_km: float


def _enum_name(value) -> str:
	return getattr(value, "name", str(value).split(".")[-1])


def _build_maximum_correlation_pvl(
	*,
	pattern_samples: int = 31,
	pattern_lines: int = 31,
	search_samples: int = 81,
	search_lines: int = 81,
	tolerance: float = 0.70,
	subpixel: bool = True,
) -> ip.Pvl:
	"""Create a minimal PVL registration template for MaximumCorrelation."""
	if pattern_samples <= 0 or pattern_lines <= 0:
		raise ValueError("Pattern chip dimensions must be positive.")

	if search_samples < pattern_samples or search_lines < pattern_lines:
		raise ValueError("Search chip must be at least as large as the pattern chip.")

	pvl = ip.Pvl()
	autoreg_obj = ip.PvlObject("AutoRegistration")

	algorithm_group = ip.PvlGroup("Algorithm")
	algorithm_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
	algorithm_group.add_keyword(ip.PvlKeyword("Tolerance", str(tolerance)))
	if subpixel:
		algorithm_group.add_keyword(ip.PvlKeyword("SubpixelAccuracy", "True"))
	autoreg_obj.add_group(algorithm_group)

	pattern_group = ip.PvlGroup("PatternChip")
	pattern_group.add_keyword(ip.PvlKeyword("Samples", str(pattern_samples)))
	pattern_group.add_keyword(ip.PvlKeyword("Lines", str(pattern_lines)))
	pattern_group.add_keyword(ip.PvlKeyword("ValidPercent", "50"))
	pattern_group.add_keyword(ip.PvlKeyword("MinimumZScore", "1.5"))
	autoreg_obj.add_group(pattern_group)

	search_group = ip.PvlGroup("SearchChip")
	search_group.add_keyword(ip.PvlKeyword("Samples", str(search_samples)))
	search_group.add_keyword(ip.PvlKeyword("Lines", str(search_lines)))
	autoreg_obj.add_group(search_group)

	pvl.add_object(autoreg_obj)
	return pvl


def open_cube(path: str, access: str = "r") -> ip.Cube:
	cube = ip.Cube()
	cube.open(path, access)
	return cube


def estimate_right_point_from_camera_geometry(
	left_cube: ip.Cube,
	right_cube: ip.Cube,
	left_sample: float,
	left_line: float,
) -> Optional[tuple[float, float]]:
	"""
	Use a pointreg-style ground seed to estimate the right-image tie point.

	This follows the ISIS pointreg idea more closely than a plain lat/lon-only
	projection:
	1. call ``left_camera.set_image(sample, line)`` on the left image,
	2. read the resulting surface point's latitude/longitude/radius,
	3. call ``right_camera.set_universal_ground_with_radius(...)`` on the right
	   image to back-project the same ground point.

	That right-image location is used as the default seed for SHIFT/AutoReg
	matching when the user has not supplied an explicit right-image initial guess.
	"""
	left_camera = left_cube.camera()
	right_camera = right_cube.camera()

	if not left_camera.set_image(left_sample, left_line):
		return None

	if not left_camera.has_surface_intersection():
		return None

	surface_point = left_camera.get_surface_point()
	if not surface_point.valid():
		return None

	if not right_camera.set_universal_ground_with_radius(
		surface_point.get_latitude().degrees(),
		surface_point.get_longitude().degrees(),
		surface_point.get_local_radius().meters(),
	):
		return None

	right_sample = right_camera.sample()
	right_line = right_camera.line()
	if not (1 <= right_sample <= right_camera.samples() and 1 <= right_line <= right_camera.lines()):
		return None

	return right_sample, right_line


def match_tie_point_with_shift(
	left_cube: ip.Cube,
	right_cube: ip.Cube,
	left_sample: float,
	left_line: float,
	right_guess_sample: Optional[float] = None,
	right_guess_line: Optional[float] = None,
	*,
	pattern_samples: int = 31,
	pattern_lines: int = 31,
	search_samples: int = 81,
	search_lines: int = 81,
	tolerance: float = 0.70,
	subpixel: bool = True,
) -> TiePointMatchResult:
	"""
	Refine the right-image conjugate point with MaximumCorrelation.

	The left-image point is treated as the known tie point. If no right-image
	initial guess is supplied, this function first tries to estimate one with the
	ISIS pointreg-style ground back-projection described above and falls back to
	the same sample/line as the left image.
	"""
	if right_guess_sample is None or right_guess_line is None:
		estimated_point = estimate_right_point_from_camera_geometry(
			left_cube,
			right_cube,
			left_sample,
			left_line,
		)
		if estimated_point is None:
			if right_guess_sample is None:
				right_guess_sample = left_sample
			if right_guess_line is None:
				right_guess_line = left_line
		else:
			estimated_sample, estimated_line = estimated_point
			if right_guess_sample is None:
				right_guess_sample = estimated_sample
			if right_guess_line is None:
				right_guess_line = estimated_line

	if right_guess_line is None:
		right_guess_line = left_line

	registration_template = _build_maximum_correlation_pvl(
		pattern_samples=pattern_samples,
		pattern_lines=pattern_lines,
		search_samples=search_samples,
		search_lines=search_lines,
		tolerance=tolerance,
		subpixel=subpixel,
	)
	matcher = ip.MaximumCorrelation(registration_template)

	pattern_chip = matcher.pattern_chip()
	pattern_chip.tack_cube(left_sample, left_line)
	pattern_chip.load(left_cube)

	search_chip = matcher.search_chip()
	search_chip.tack_cube(right_guess_sample, right_guess_line)
	search_chip.load(right_cube)

	status = matcher.register()
	status_name = _enum_name(status)

	if status not in SUCCESS_STATUSES or not matcher.success():
		raise RuntimeError(
			"SHIFT/MaximumCorrelation matching failed with status "
			f"{status_name} (goodness_of_fit={matcher.goodness_of_fit():.6f})."
		)

	return TiePointMatchResult(
		left_sample=left_sample,
		left_line=left_line,
		right_sample=matcher.cube_sample(),
		right_line=matcher.cube_line(),
		right_guess_sample=right_guess_sample,
		right_guess_line=right_guess_line,
		status=status_name,
		goodness_of_fit=matcher.goodness_of_fit(),
	)


def _set_camera_image_or_raise(camera: ip.Camera, sample: float, line: float, label: str) -> None:
	if not camera.set_image(sample, line):
		raise RuntimeError(
			f"{label}.camera().set_image({sample}, {line}) failed. "
			"Please check that the point lies on the image and has a valid surface intersection."
		)


def forward_intersection(
	left_cube_path: str,
	right_cube_path: str,
	left_sample: float,
	left_line: float,
	right_sample: Optional[float] = None,
	right_line: Optional[float] = None,
	*,
	use_shift_match: bool = True,
	pattern_samples: int = 31,
	pattern_lines: int = 31,
	search_samples: int = 81,
	search_lines: int = 81,
	tolerance: float = 0.70,
	subpixel: bool = True,
) -> ForwardIntersectionResult:
	"""
	Compute the forward intersection of two cubes with `Stereo.elevation(...)`.

	Workflow:
	1. Open the two cubes.
	2. Use the left image point as the known tie point.
	3. Optionally refine the right image tie point using SHIFT-style correlation matching.
	4. Call `camera().set_image(...)` on both cubes.
	5. Call `Stereo.elevation(...)` to obtain the 3D intersection.
	"""
	left_cube = open_cube(left_cube_path)
	right_cube = open_cube(right_cube_path)

	try:
		match_result: Optional[TiePointMatchResult] = None
		if use_shift_match:
			match_result = match_tie_point_with_shift(
				left_cube,
				right_cube,
				left_sample,
				left_line,
				right_guess_sample=right_sample,
				right_guess_line=right_line,
				pattern_samples=pattern_samples,
				pattern_lines=pattern_lines,
				search_samples=search_samples,
				search_lines=search_lines,
				tolerance=tolerance,
				subpixel=subpixel,
			)
			right_sample = match_result.right_sample
			right_line = match_result.right_line
		else:
			if right_sample is None or right_line is None:
				raise ValueError(
					"When use_shift_match is False, right_sample and right_line must both be provided."
				)

		left_camera = left_cube.camera()
		right_camera = right_cube.camera()

		_set_camera_image_or_raise(left_camera, left_sample, left_line, "left_cube")
		_set_camera_image_or_raise(right_camera, right_sample, right_line, "right_cube")

		success, radius, latitude, longitude, sepang, error = ip.Stereo.elevation(left_camera, right_camera)
		if not success:
			raise RuntimeError("Stereo.elevation(...) returned success=False after camera initialization.")

		x_km, y_km, z_km = ip.Stereo.spherical(latitude, longitude, radius)

		return ForwardIntersectionResult(
			left_cube=left_cube_path,
			right_cube=right_cube_path,
			left_sample=left_sample,
			left_line=left_line,
			right_sample=right_sample,
			right_line=right_line,
			matched_by_shift=match_result is not None,
			match_status=None if match_result is None else match_result.status,
			goodness_of_fit=None if match_result is None else match_result.goodness_of_fit,
			radius_meters=radius,
			latitude_degrees=latitude,
			longitude_degrees=longitude,
			separation_angle_degrees=sepang,
			error_meters=error,
			x_km=x_km,
			y_km=y_km,
			z_km=z_km,
		)
	finally:
		if left_cube.is_open():
			left_cube.close()
		if right_cube.is_open():
			right_cube.close()


def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description=(
			"Open two ISIS cubes, optionally refine the right-image tie point with "
			"SHIFT-style MaximumCorrelation matching, then run Stereo.elevation "
			"for forward intersection."
		)
	)
	parser.add_argument("left_cube", help="Path to the left cube.")
	parser.add_argument("right_cube", help="Path to the right cube.")
	parser.add_argument("left_sample", type=float, help="Known tie-point sample on the left cube.")
	parser.add_argument("left_line", type=float, help="Known tie-point line on the left cube.")
	parser.add_argument(
		"--right-sample",
		type=float,
		default=None,
		help="Initial or final tie-point sample on the right cube. If omitted during SHIFT matching, the script first tries a pointreg-style ground back-projection seed.",
	)
	parser.add_argument(
		"--right-line",
		type=float,
		default=None,
		help="Initial or final tie-point line on the right cube. If omitted during SHIFT matching, the script first tries a pointreg-style ground back-projection seed.",
	)
	parser.add_argument(
		"--no-shift-match",
		action="store_true",
		help="Skip MaximumCorrelation matching and directly use --right-sample/--right-line as the conjugate point.",
	)
	parser.add_argument("--pattern-samples", type=int, default=31, help="Pattern chip width for SHIFT matching.")
	parser.add_argument("--pattern-lines", type=int, default=31, help="Pattern chip height for SHIFT matching.")
	parser.add_argument("--search-samples", type=int, default=81, help="Search chip width for SHIFT matching.")
	parser.add_argument("--search-lines", type=int, default=81, help="Search chip height for SHIFT matching.")
	parser.add_argument("--tolerance", type=float, default=0.70, help="MaximumCorrelation tolerance.")
	parser.add_argument(
		"--pixel-only",
		action="store_true",
		help="Disable sub-pixel matching and keep registration at pixel accuracy.",
	)
	return parser


def main() -> None:
	parser = build_argument_parser()
	args = parser.parse_args()

	result = forward_intersection(
		args.left_cube,
		args.right_cube,
		args.left_sample,
		args.left_line,
		right_sample=args.right_sample,
		right_line=args.right_line,
		use_shift_match=not args.no_shift_match,
		pattern_samples=args.pattern_samples,
		pattern_lines=args.pattern_lines,
		search_samples=args.search_samples,
		search_lines=args.search_lines,
		tolerance=args.tolerance,
		subpixel=not args.pixel_only,
	)

	print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
	main()