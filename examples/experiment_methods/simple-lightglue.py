"""Run matching with LightGlue or classic OpenCV SIFT for performance comparison.

Author: Geng Xun
Created: 2026-05-12
Updated: 2026-05-12  Geng Xun added a `--device` CLI option with automatic GPU detection and CPU fallback for the LightGlue example.
Updated: 2026-05-12  Geng Xun added OpenCV match-line visualization output options for the LightGlue example.
Updated: 2026-05-12  Geng Xun added a `--features` CLI option with frontend validation and runtime reporting for the LightGlue example.
Updated: 2026-05-12  Geng Xun updated the output visualization filename to automatically include the selected matching frontend.
Updated: 2026-05-12  Geng Xun expanded tensor-to-BGR image conversion to support grayscale, RGB, and RGBA tensors.
Updated: 2026-05-12  Geng Xun made the left/right images configurable from the CLI, removed the default match-count limit, and added example usage to the help text.
Updated: 2026-05-12  Geng Xun added classic OpenCV SIFT matching method for performance comparison with LightGlue.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch


TESTDIR = "/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test"

DEFAULT_LEFT_IMAGE = TESTDIR + "/REDUCED_scale4_M104311715RE.echo.cal.tif"
DEFAULT_RIGHT_IMAGE = TESTDIR + "/REDUCED_scale4_M104318871RE.echo.cal.tif"

DEFAULT_FEATURES = "superpoint"
SUPPORTED_FEATURES = ("superpoint", "disk", "aliked", "sift", "doghardnet")

DEFAULT_METHOD = "lightglue"
SUPPORTED_METHODS = ("lightglue", "sift")


def parse_args() -> argparse.Namespace:
	help_examples = """Examples:
  python examples/experiment_methods/simple-lightglue.py
  python examples/experiment_methods/simple-lightglue.py --left-image /path/to/left.tif --right-image /path/to/right.tif
  python examples/experiment_methods/simple-lightglue.py --features disk --device auto
  python examples/experiment_methods/simple-lightglue.py --features sift --max-visualized-matches 500 --output-match-image /tmp/lro-matches.png
  python examples/experiment_methods/simple-lightglue.py --method sift --max-features 2048
  python examples/experiment_methods/simple-lightglue.py --method sift --max-features 4096 --ratio-threshold 0.75
  python examples/experiment_methods/simple-lightglue.py --method lightglue --features superpoint --max-features 2048
"""
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=(
			"Run matching with LightGlue or classic OpenCV SIFT. Use --method to "
			"switch between matching backends for performance comparison."
		),
		epilog=help_examples,
	)
	parser.add_argument(
		"--left-image",
		default=DEFAULT_LEFT_IMAGE,
		help="Path to the left input image. Defaults to the bundled test image.",
	)
	parser.add_argument(
		"--right-image",
		default=DEFAULT_RIGHT_IMAGE,
		help="Path to the right input image. Defaults to the bundled test image.",
	)
	parser.add_argument(
		"--device",
		choices=("auto", "cpu", "cuda"),
		default="auto",
		help=(
			"Execution device. 'auto' prefers CUDA when available and falls back "
			"to CPU when no GPU is detected."
		),
	)
	parser.add_argument(
		"--method",
		choices=SUPPORTED_METHODS,
		default=DEFAULT_METHOD,
		help=(
			"Matching method. 'lightglue' uses the LightGlue neural matcher, "
			"'sift' uses classic OpenCV SIFT with ratio test."
		),
	)
	parser.add_argument(
		"--features",
		choices=SUPPORTED_FEATURES,
		default=DEFAULT_FEATURES,
		help=(
			"Feature frontend to pair with LightGlue (only used when --method "
			"is 'lightglue'). Supported values: "
			+ ", ".join(SUPPORTED_FEATURES)
		),
	)
	parser.add_argument(
		"--max-features",
		type=int,
		default=2048,
		help=(
			"Maximum number of keypoints to detect. Applies to both SIFT "
			"(nfeatures) and LightGlue frontends. Default: 2048."
		),
	)
	parser.add_argument(
		"--ratio-threshold",
		type=float,
		default=0.8,
		help=(
			"Lowe's ratio test threshold for classic SIFT matching. Lower values "
			"are more strict, yielding fewer but more reliable matches. "
			"Default: 0.8."
		),
	)
	parser.add_argument(
		"--match-threshold",
		type=float,
		default=None,
		help=(
			"Maximum distance threshold for SIFT brute-force matching. "
			"When None (default), only the ratio test is applied."
		),
	)
	parser.add_argument(
		"--output-match-image",
		default=None,
		help=(
			"Path to write the OpenCV match-line visualization image. If omitted, "
			"a default name is generated from the left/right image names and the selected method."
		),
	)
	parser.add_argument(
		"--max-visualized-matches",
		type=int,
		default=None,
		help=(
			"Maximum number of match lines to draw into the output visualization. "
			"By default, all matches are drawn."
		),
	)
	return parser.parse_args()


def resolve_device(device_option: str) -> torch.device:
	if device_option == "auto":
		return torch.device("cuda" if torch.cuda.is_available() else "cpu")
	if device_option == "cuda" and not torch.cuda.is_available():
		raise RuntimeError("CUDA was requested, but no GPU is available.")
	return torch.device(device_option)


def build_extractor(features: str, device: torch.device, max_features: int):
	from lightglue import ALIKED, DISK, DoGHardNet, SIFT, SuperPoint

	extractors = {
		"superpoint": SuperPoint(max_num_keypoints=max_features),
		"disk": DISK(max_num_keypoints=max_features).eval(),
		"aliked": ALIKED(max_num_keypoints=max_features).eval(),
		"sift": SIFT(max_num_keypoints=max_features).eval(),
		"doghardnet": DoGHardNet(max_num_keypoints=max_features).eval(),
	}
	if features not in extractors:
		raise ValueError(
			f"Unsupported features frontend '{features}'. Supported values: {', '.join(sorted(extractors))}"
		)
	return extractors[features].to(device)


def tensor_image_to_bgr_uint8(image: torch.Tensor) -> np.ndarray:
	image_cpu = image.detach().cpu()
	if image_cpu.ndim != 3:
		raise ValueError(f"Expected image tensor with shape (C,H,W), got {tuple(image_cpu.shape)}")
	channel_count = int(image_cpu.shape[0])
	image_hwc = image_cpu.permute(1, 2, 0).clamp(0.0, 1.0).numpy()
	image_uint8 = (image_hwc * 255.0).round().astype(np.uint8)
	if channel_count == 1:
		return cv2.cvtColor(image_uint8[..., 0], cv2.COLOR_GRAY2BGR)
	if channel_count == 3:
		return cv2.cvtColor(image_uint8, cv2.COLOR_RGB2BGR)
	if channel_count == 4:
		return cv2.cvtColor(image_uint8, cv2.COLOR_RGBA2BGR)
	raise ValueError(
		f"Expected 1, 3, or 4 channels for image tensor shaped (C,H,W), got {channel_count}"
	)


def build_output_match_image_path(
	output_match_image: str | None,
	method: str,
	features: str | None,
	left_image: str,
	right_image: str,
) -> str:
	label = f"{method}-{features}" if features else method
	if output_match_image is None:
		left_path = Path(left_image)
		right_path = Path(right_image)
		output_path = left_path.parent / f"{left_path.stem}__{right_path.stem}-matches.png"
	else:
		output_path = Path(output_match_image)
	if output_path.suffix:
		return str(output_path.with_name(f"{output_path.stem}-{label}{output_path.suffix}"))
	return str(output_path.with_name(f"{output_path.name}-{label}"))


def match_classic_sift(
	left_path: str,
	right_path: str,
	max_features: int,
	ratio_threshold: float,
	match_threshold: float | None,
) -> tuple[np.ndarray, np.ndarray, int]:
	sift = cv2.SIFT_create(nfeatures=max_features)

	img0 = cv2.imread(left_path, cv2.IMREAD_GRAYSCALE)
	img1 = cv2.imread(right_path, cv2.IMREAD_GRAYSCALE)
	if img0 is None:
		raise FileNotFoundError(f"Cannot read left image: {left_path}")
	if img1 is None:
		raise FileNotFoundError(f"Cannot read right image: {right_path}")

	kps0, descs0 = sift.detectAndCompute(img0, None)
	kps1, descs1 = sift.detectAndCompute(img1, None)

	bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
	raw_matches = bf.knnMatch(descs0, descs1, k=2)

	points0_list = []
	points1_list = []
	for m, n in raw_matches:
		if m.distance < ratio_threshold * n.distance:
			if match_threshold is not None and m.distance > match_threshold:
				continue
			points0_list.append(kps0[m.queryIdx].pt)
			points1_list.append(kps1[m.trainIdx].pt)

	points0 = np.array(points0_list, dtype=np.float64)
	points1 = np.array(points1_list, dtype=np.float64)
	return points0, points1, len(points0)


def draw_match_lines(
	image0_bgr: np.ndarray,
	image1_bgr: np.ndarray,
	points0: np.ndarray,
	points1: np.ndarray,
	output_path: str,
	max_visualized_matches: int | None,
) -> None:
	height0, width0 = image0_bgr.shape[:2]
	height1, width1 = image1_bgr.shape[:2]
	canvas_height = max(height0, height1)
	canvas_width = width0 + width1
	canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
	canvas[:height0, :width0] = image0_bgr
	canvas[:height1, width0:width0 + width1] = image1_bgr

	match_count = min(len(points0), len(points1))
	if max_visualized_matches is not None and max_visualized_matches > 0:
		match_count = min(match_count, max_visualized_matches)
	for index in range(match_count):
		left_point = tuple(np.round(points0[index]).astype(int))
		right_point_xy = np.round(points1[index]).astype(int)
		right_point = (int(right_point_xy[0] + width0), int(right_point_xy[1]))
		color = tuple(int(value) for value in np.random.default_rng(index).integers(0, 256, size=3))
		cv2.circle(canvas, left_point, 4, color, thickness=-1, lineType=cv2.LINE_AA)
		cv2.circle(canvas, right_point, 4, color, thickness=-1, lineType=cv2.LINE_AA)
		cv2.line(canvas, left_point, right_point, color, thickness=1, lineType=cv2.LINE_AA)

	output_file = Path(output_path)
	output_file.parent.mkdir(parents=True, exist_ok=True)
	if not cv2.imwrite(str(output_file), canvas):
		raise RuntimeError(f"Failed to write match visualization image to {output_file}")


def main() -> None:
	args = parse_args()
	left_image = args.left_image
	right_image = args.right_image
	method = args.method

	output_match_image = build_output_match_image_path(
		args.output_match_image,
		method,
		args.features if method == "lightglue" else None,
		left_image,
		right_image,
	)

	if method == "sift":
		print(f"Using method: classic SIFT")
		print(f"Max features: {args.max_features}")
		print(f"Ratio threshold: {args.ratio_threshold}")
		if args.match_threshold is not None:
			print(f"Match distance threshold: {args.match_threshold}")
		print(f"Left image: {left_image}")
		print(f"Right image: {right_image}")

		points0_np, points1_np, match_count = match_classic_sift(
			left_image,
			right_image,
			max_features=args.max_features,
			ratio_threshold=args.ratio_threshold,
			match_threshold=args.match_threshold,
		)

		img0_bgr = cv2.cvtColor(
			cv2.imread(left_image, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR
		)
		img1_bgr = cv2.cvtColor(
			cv2.imread(right_image, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR
		)
		draw_match_lines(
			img0_bgr,
			img1_bgr,
			points0_np,
			points1_np,
			output_match_image,
			args.max_visualized_matches,
		)

		print(f"Matched points: {match_count}")
		print(f"Match visualization written to: {output_match_image}")
		return

	# LightGlue path
	from lightglue import LightGlue
	from lightglue.utils import load_image, rbd

	device = resolve_device(args.device)
	selected_features = args.features
	print(f"Using device: {device}")
	print(f"Using method: LightGlue")
	print(f"Using features frontend: {selected_features}")
	print(f"Max features: {args.max_features}")
	print(f"Left image: {left_image}")
	print(f"Right image: {right_image}")

	extractor = build_extractor(selected_features, device, max_features=args.max_features)
	matcher = LightGlue(features=selected_features).eval().to(device)

	image0 = load_image(left_image).to(device)
	image1 = load_image(right_image).to(device)

	feats0 = extractor.extract(image0)
	feats1 = extractor.extract(image1)

	matches01 = matcher({"image0": feats0, "image1": feats1})
	feats0, feats1, matches01 = [rbd(x) for x in [feats0, feats1, matches01]]
	matches = matches01["matches"]
	points0 = feats0["keypoints"][matches[..., 0]]
	points1 = feats1["keypoints"][matches[..., 1]]
	points0_np = points0.detach().cpu().numpy()
	points1_np = points1.detach().cpu().numpy()

	image0_bgr = tensor_image_to_bgr_uint8(image0)
	image1_bgr = tensor_image_to_bgr_uint8(image1)
	draw_match_lines(
		image0_bgr,
		image1_bgr,
		points0_np,
		points1_np,
		output_match_image,
		args.max_visualized_matches,
	)

	print(f"Matched points: {len(matches)}")
	print(f"points0 shape: {tuple(points0.shape)}")
	print(f"points1 shape: {tuple(points1.shape)}")
	print(f"Match visualization written to: {output_match_image}")


if __name__ == "__main__":
	main()