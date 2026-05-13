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

DEFAULT_MATCH_METHOD = "lightglue"
SUPPORTED_MATCH_METHODS = ("lightglue", "sift")


def parse_args() -> argparse.Namespace:
	help_examples = """Examples:
  # LightGlue matcher + SuperPoint features (default)
  python examples/experiment_methods/simple-lightglue.py

  # Custom images
  python examples/experiment_methods/simple-lightglue.py --left-image /path/to/left.tif --right-image /path/to/right.tif

  # DISK features on auto device
  python examples/experiment_methods/simple-lightglue.py --feature-method disk --device auto

  # SIFT features, limit visualization to 500 matches
  python examples/experiment_methods/simple-lightglue.py --feature-method sift --max-visualized-matches 500 --output-match-image /tmp/lro-matches.png

  # Classic SIFT matching (no neural network)
  python examples/experiment_methods/simple-lightglue.py --match-method sift --max-features 2048

  # Classic SIFT with stricter ratio test
  python examples/experiment_methods/simple-lightglue.py --match-method sift --max-features 4096 --sift-ratio-threshold 0.75

  # LightGlue matcher + SuperPoint features + explicit keypoint count
  python examples/experiment_methods/simple-lightglue.py --match-method lightglue --feature-method superpoint --max-features 2048
"""
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=(
			"Run feature extraction and image matching. Supports LightGlue neural "
			"matching and classic OpenCV SIFT for performance comparison."
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
		"--feature-method",
		choices=SUPPORTED_FEATURES,
		default=DEFAULT_FEATURES,
		help=(
			"Feature extraction method. Used by both LightGlue and SIFT matching "
			"paths. Supported: " + ", ".join(SUPPORTED_FEATURES)
		),
	)
	parser.add_argument(
		"--match-method",
		choices=SUPPORTED_MATCH_METHODS,
		default=DEFAULT_MATCH_METHOD,
		help=(
			"Matching method. 'lightglue' uses the neural LightGlue matcher paired "
			"with --feature-method; 'sift' uses classic OpenCV SIFT + ratio test "
			"(ignores --feature-method). Supported: " + ", ".join(SUPPORTED_MATCH_METHODS)
		),
	)
	# LightGlue-specific parameters
	parser.add_argument(
		"--lightglue-filter-threshold",
		type=float,
		default=0.05,
		help=(
			"LightGlue: match filtering threshold. Lower values allow more edge "
			"matches through. 0.0 = aggressive (more matches), 0.1+ = conservative. "
			"Default: 0.05."
		),
	)
	parser.add_argument(
		"--lightglue-depth-confidence",
		type=int,
		default=-1,
		help=(
			"LightGlue: depth confidence for early stopping. -1 disables early "
			"stopping, forcing full-depth analysis. Default: -1."
		),
	)
	parser.add_argument(
		"--lightglue-width-confidence",
		type=int,
		default=-1,
		help=(
			"LightGlue: width confidence for token pruning. -1 disables pruning, "
			"ensuring all keypoint pairs are considered. Default: -1."
		),
	)
	parser.add_argument(
		"--lightglue-flash",
		type=lambda x: str(x).lower() in ("true", "1", "yes"),
		default=True,
		help=(
			"LightGlue: enable flash attention for faster inference. "
			"Default: true."
		),
	)
	parser.add_argument(
		"--lightglue-mp",
		type=lambda x: str(x).lower() in ("true", "1", "yes"),
		default=True,
		help=(
			"LightGlue: enable mixed precision (fp16). Requires CUDA device. "
			"Default: true."
		),
	)
	parser.add_argument(
		"--max-features",
		type=int,
		default=2048,
		help=(
			"Maximum number of keypoints to detect. Applies to all feature "
			"extractors and classic SIFT. Default: 2048."
		),
	)
	parser.add_argument(
		"--sift-ratio-threshold",
		type=float,
		default=0.8,
		help=(
			"Lowe's ratio test threshold for classic SIFT matching. Lower values "
			"are more strict, yielding fewer but more reliable matches. "
			"Default: 0.8."
		),
	)
	parser.add_argument(
		"--sift-match-threshold",
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
			"Path to write the match visualization image. If omitted, "
			"auto-generated from input filenames and methods."
		),
	)
	parser.add_argument(
		"--max-visualized-matches",
		type=int,
		default=None,
		help=(
			"Maximum number of match lines to draw. "
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
	feature_method: str,
	match_method: str,
	left_image: str,
	right_image: str,
) -> str:
	label = f"{feature_method}_{match_method}"
	if output_match_image is None:
		left_path = Path(left_image)
		right_path = Path(right_image)
		output_path = left_path.parent / f"{label}__{left_path.stem}__{right_path.stem}-matches.png"
	else:
		output_path = Path(output_match_image)
	if output_path.suffix:
		return str(output_path.with_name(f"{label}-{output_path.stem}{output_path.suffix}"))
	return str(output_path.with_name(f"{label}-{output_path.name}"))


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
	match_method = args.match_method

	output_match_image = build_output_match_image_path(
		args.output_match_image,
		args.feature_method,
		match_method,
		left_image,
		right_image,
	)

	if match_method == "sift":
		print("=== Classic SIFT Matching ===")
		print(f"  Max features: {args.max_features}")
		print(f"  SIFT ratio threshold: {args.sift_ratio_threshold}")
		if args.sift_match_threshold is not None:
			print(f"  SIFT match distance threshold: {args.sift_match_threshold}")
		print(f"  Left image: {left_image}")
		print(f"  Right image: {right_image}")

		points0_np, points1_np, match_count = match_classic_sift(
			left_image,
			right_image,
			max_features=args.max_features,
			ratio_threshold=args.sift_ratio_threshold,
			match_threshold=args.sift_match_threshold,
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

		print(f"  Matched points: {match_count}")
		print(f"  Output: {output_match_image}")
		return

	# LightGlue path
	from lightglue import LightGlue
	from lightglue.utils import load_image, rbd

	device = resolve_device(args.device)
	feature_method = args.feature_method
	print("=== LightGlue Matching ===")
	print(f"  Device: {device}")
	print(f"  Feature method: {feature_method}")
	print(f"  Max features: {args.max_features}")
	print(f"  Filter threshold: {args.lightglue_filter_threshold}")
	print(f"  Depth confidence: {args.lightglue_depth_confidence}")
	print(f"  Width confidence: {args.lightglue_width_confidence}")
	print(f"  Flash attention: {args.lightglue_flash}")
	print(f"  Mixed precision: {args.lightglue_mp}")
	print(f"  Left image: {left_image}")
	print(f"  Right image: {right_image}")

	extractor = build_extractor(feature_method, device, max_features=args.max_features)
	matcher = LightGlue(
		features=feature_method,
		filter_threshold=args.lightglue_filter_threshold,
		depth_confidence=args.lightglue_depth_confidence,
		width_confidence=args.lightglue_width_confidence,
		flash=args.lightglue_flash,
		mp=args.lightglue_mp,
	).eval().to(device)

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

	print(f"  Matched points: {len(matches)}")
	print(f"  Output: {output_match_image}")


if __name__ == "__main__":
	main()