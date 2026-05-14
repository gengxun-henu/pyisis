"""Run LoFTR matching on any two input images.

Author: Geng Xun
Created: 2026-05-12
Updated: 2026-05-12  Geng Xun added a standalone LoFTR example that locates the sibling LoFTR repository, runs two-image matching, writes a visualization image, and optionally exports matched coordinates to CSV.
Updated: 2026-05-12  Geng Xun added optional RANSAC-based homography and fundamental-matrix filtering plus reusable helpers for LoFTR parameter sweeps.
Updated: 2026-05-12  Geng Xun changed preprocessing to prefer zero-padding to the next multiple of 8 with valid-region masks so image geometry is preserved better than direct resizing.
"""

from __future__ import annotations

import argparse
import copy
import csv
import importlib
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F


SUPPORTED_MODEL_TYPES = ("indoor", "outdoor")
SUPPORTED_DEVICES = ("auto", "cpu", "cuda")
SUPPORTED_GEOMETRIC_FILTERS = ("none", "homography", "fundamental")
SUPPORTED_PREPROCESS_MODES = ("pad", "resize")
DIVISIBILITY = 8
DEFAULT_SAMPLE_IMAGES = {
    "indoor": (
        "assets/scannet_sample_images/scene0711_00_frame-001680.jpg",
        "assets/scannet_sample_images/scene0711_00_frame-001995.jpg",
    ),
    "outdoor": (
        "assets/phototourism_sample_images/united_states_capitol_26757027_6717084061.jpg",
        "assets/phototourism_sample_images/united_states_capitol_98169888_3347710852.jpg",
    ),
}


def parse_args() -> argparse.Namespace:
    help_examples = """Examples:
  # Outdoor model with automatic LoFTR repository discovery
  python examples/experiment_methods/simple-loftr.py \
      --left-image /path/to/left.png \
      --right-image /path/to/right.png

  # Indoor model with explicit LoFTR repository path
  python examples/experiment_methods/simple-loftr.py \
      --left-image /path/to/left.png \
      --right-image /path/to/right.png \
      --model-type indoor \
      --loftr-root /home/gengxun/PlanetaryMapping/asp360_new/LoFTR

  # Custom checkpoint and CSV export
  python examples/experiment_methods/simple-loftr.py \
      --left-image /path/to/left.png \
      --right-image /path/to/right.png \
      --checkpoint /path/to/custom.ckpt \
      --output-csv /tmp/loftr_matches.csv

  # Resize before inference, keep the top 1000 confident matches only
  python examples/experiment_methods/simple-loftr.py \
      --left-image /path/to/left.png \
      --right-image /path/to/right.png \
      --resize-width 1024 \
      --resize-height 768 \
      --top-k 10000
"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Run LoFTR detector-free matching on any two images, save a match "
            "visualization image, and optionally export the matched coordinates."
        ),
        epilog=help_examples,
    )
    parser.add_argument(
        "--left-image",
        required=True,
        help="Path to the left input image.",
    )
    parser.add_argument(
        "--right-image",
        required=True,
        help="Path to the right input image.",
    )
    parser.add_argument(
        "--loftr-root",
        default=None,
        help=(
            "Optional path to the LoFTR repository root. When omitted, the script "
            "searches common sibling locations automatically."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=(
            "Optional path to a custom LoFTR checkpoint. When omitted, the script "
            "uses the checkpoint implied by --model-type."
        ),
    )
    parser.add_argument(
        "--model-type",
        choices=SUPPORTED_MODEL_TYPES,
        default="outdoor",
        help="Preset checkpoint family to use when --checkpoint is omitted.",
    )
    parser.add_argument(
        "--temp-bug-fix",
        choices=("auto", "true", "false"),
        default="auto",
        help=(
            "LoFTR positional-encoding compatibility flag. 'auto' uses a practical "
            "default: indoor=true, outdoor=false."
        ),
    )
    parser.add_argument(
        "--coarse-threshold",
        type=float,
        default=None,
        help=(
            "Optional LoFTR coarse matching threshold. When omitted, the checkpoint "
            "default is used."
        ),
    )
    parser.add_argument(
        "--device",
        choices=SUPPORTED_DEVICES,
        default="auto",
        help="Execution device. 'auto' prefers CUDA when available and falls back to CPU.",
    )
    parser.add_argument(
        "--preprocess-mode",
        choices=SUPPORTED_PREPROCESS_MODES,
        default="pad",
        help=(
            "Image alignment strategy before LoFTR inference. 'pad' preserves image geometry "
            "and pads the bottom/right border to the next multiple of 8; 'resize' directly "
            "resizes the inference image to an 8-aligned size. Default: pad."
        ),
    )
    parser.add_argument(
        "--resize-width",
        type=int,
        default=None,
        help=(
            "Optional target width before final 8-alignment. Must be used together with "
            "--resize-height. With --preprocess-mode pad, this is the content size before "
            "zero-padding."
        ),
    )
    parser.add_argument(
        "--resize-height",
        type=int,
        default=None,
        help=(
            "Optional target height before final 8-alignment. Must be used together with "
            "--resize-width. With --preprocess-mode pad, this is the content size before "
            "zero-padding."
        ),
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Optional minimum confidence threshold used to filter LoFTR matches.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Keep only the top-K matches ranked by confidence after filtering.",
    )
    parser.add_argument(
        "--geometric-filter",
        choices=SUPPORTED_GEOMETRIC_FILTERS,
        default="none",
        help=(
            "Optional geometric outlier suppression. 'homography' uses planar RANSAC; "
            "'fundamental' uses epipolar RANSAC."
        ),
    )
    parser.add_argument(
        "--ransac-reproj-threshold",
        type=float,
        default=3.0,
        help="RANSAC reprojection threshold in pixels for homography/fundamental filtering.",
    )
    parser.add_argument(
        "--ransac-confidence",
        type=float,
        default=0.999,
        help="RANSAC confidence target. Default: 0.999.",
    )
    parser.add_argument(
        "--ransac-max-iters",
        type=int,
        default=10000,
        help="Maximum RANSAC iterations. Default: 10000.",
    )
    parser.add_argument(
        "--output-match-image",
        default=None,
        help=(
            "Path to write the visualization image. If omitted, a descriptive path "
            "is auto-generated next to the left image."
        ),
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help=(
            "Optional CSV output path for matched coordinates and confidences. If "
            "omitted, no CSV is written."
        ),
    )
    parser.add_argument(
        "--max-visualized-matches",
        type=int,
        default=None,
        help="Optional upper limit on the number of match lines drawn in the visualization.",
    )
    return parser.parse_args()


def resolve_device(device_option: str) -> torch.device:
    if device_option == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_option == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but no GPU is available.")
    return torch.device(device_option)


def validate_resize_args(resize_width: int | None, resize_height: int | None) -> None:
    if (resize_width is None) != (resize_height is None):
        raise ValueError("--resize-width and --resize-height must be provided together.")
    if resize_width is not None and resize_width <= 0:
        raise ValueError("--resize-width must be positive.")
    if resize_height is not None and resize_height <= 0:
        raise ValueError("--resize-height must be positive.")


def validate_ransac_args(
    geometric_filter: str,
    ransac_reproj_threshold: float,
    ransac_confidence: float,
    ransac_max_iters: int,
) -> None:
    if geometric_filter not in SUPPORTED_GEOMETRIC_FILTERS:
        raise ValueError(
            f"Unsupported geometric filter '{geometric_filter}'. "
            f"Supported values: {', '.join(SUPPORTED_GEOMETRIC_FILTERS)}"
        )
    if ransac_reproj_threshold <= 0:
        raise ValueError("--ransac-reproj-threshold must be positive.")
    if not 0 < ransac_confidence <= 1:
        raise ValueError("--ransac-confidence must be in (0, 1].")
    if ransac_max_iters <= 0:
        raise ValueError("--ransac-max-iters must be positive.")


def find_loftr_root(explicit_root: str | None) -> Path:
    if explicit_root is not None:
        candidate = Path(explicit_root).expanduser().resolve()
        if is_valid_loftr_root(candidate):
            return candidate
        raise FileNotFoundError(f"Invalid LoFTR root: {candidate}")

    script_path = Path(__file__).resolve()
    checked: set[Path] = set()
    for ancestor in [script_path.parent, *script_path.parents]:
        candidates = [ancestor / "LoFTR", ancestor.parent / "LoFTR"]
        for candidate in candidates:
            if candidate in checked:
                continue
            checked.add(candidate)
            if is_valid_loftr_root(candidate):
                return candidate.resolve()

    raise FileNotFoundError(
        "Could not automatically locate the LoFTR repository. "
        "Please pass --loftr-root /path/to/LoFTR."
    )


def is_valid_loftr_root(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "src" / "loftr" / "__init__.py").is_file()


def ensure_loftr_importable(loftr_root: Path) -> None:
    loftr_root_str = str(loftr_root)
    if loftr_root_str not in sys.path:
        sys.path.insert(0, loftr_root_str)


def get_default_sample_images(loftr_root: Path, model_type: str) -> tuple[Path, Path]:
    relative_left, relative_right = DEFAULT_SAMPLE_IMAGES[model_type]
    left_path = (loftr_root / relative_left).resolve()
    right_path = (loftr_root / relative_right).resolve()
    if not left_path.is_file() or not right_path.is_file():
        raise FileNotFoundError(
            f"Default sample image pair for '{model_type}' was not found under {loftr_root}."
        )
    return left_path, right_path


def resolve_checkpoint(checkpoint: str | None, loftr_root: Path, model_type: str) -> Path:
    if checkpoint is not None:
        resolved = Path(checkpoint).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Checkpoint file does not exist: {resolved}")
        return resolved

    checkpoint_candidates = {
        "indoor": [
            loftr_root / "weights" / "indoor.ckpt",
            loftr_root / "weights" / "indoor_ds.ckpt",
            loftr_root / "weights" / "indoor_ds_new.ckpt",
        ],
        "outdoor": [
            loftr_root / "weights" / "outdoor.ckpt",
            loftr_root / "weights" / "outdoor_ds.ckpt",
        ],
    }
    for candidate in checkpoint_candidates[model_type]:
        if candidate.is_file():
            return candidate.resolve()

    candidate_text = "\n  - ".join(str(path) for path in checkpoint_candidates[model_type])
    raise FileNotFoundError(
        f"Could not find a default {model_type} checkpoint. Checked:\n  - {candidate_text}"
    )


def resolve_temp_bug_fix(option: str, model_type: str) -> bool:
    if option == "true":
        return True
    if option == "false":
        return False
    return model_type == "indoor"


def build_loftr_config(default_cfg, temp_bug_fix: bool, coarse_threshold: float | None):
    config = copy.deepcopy(default_cfg)
    config["coarse"]["temp_bug_fix"] = temp_bug_fix
    if coarse_threshold is not None:
        config["match_coarse"]["thr"] = float(coarse_threshold)
    return config


def load_loftr_matcher(
    loftr_root: Path,
    checkpoint_path: Path,
    temp_bug_fix: bool,
    device: torch.device,
    coarse_threshold: float | None = None,
):
    ensure_loftr_importable(loftr_root)
    loftr_module = importlib.import_module("src.loftr")
    LoFTR = loftr_module.LoFTR
    default_cfg = loftr_module.default_cfg

    config = build_loftr_config(default_cfg, temp_bug_fix, coarse_threshold)

    matcher = LoFTR(config=config)
    try:
        state_dict = torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        state_dict = torch.load(checkpoint_path, map_location=device)
    if "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]
    matcher.load_state_dict(state_dict, strict=True)
    return matcher.eval().to(device)


def build_output_path(
    output_path: str | None,
    suffix: str,
    left_image: str,
    right_image: str,
    model_type: str,
    geometric_filter: str = "none",
) -> Path:
    label = f"loftr_{model_type}"
    if geometric_filter != "none":
        label += f"_{geometric_filter}"
    if output_path is None:
        left_path = Path(left_image)
        right_path = Path(right_image)
        return left_path.parent / f"{label}__{left_path.stem}__{right_path.stem}{suffix}"

    requested = Path(output_path)
    if requested.suffix:
        return requested.with_name(f"{label}-{requested.stem}{requested.suffix}")
    return requested.with_name(f"{label}-{requested.name}{suffix}")


def align_size_to_divisible(
    width: int,
    height: int,
    divisor: int,
    mode: str,
) -> tuple[int, int]:
    if mode == "floor":
        adjusted_width = max(divisor, width - (width % divisor))
        adjusted_height = max(divisor, height - (height % divisor))
        return adjusted_width, adjusted_height
    if mode == "ceil":
        adjusted_width = max(divisor, ((width + divisor - 1) // divisor) * divisor)
        adjusted_height = max(divisor, ((height + divisor - 1) // divisor) * divisor)
        return adjusted_width, adjusted_height
    raise ValueError(f"Unsupported alignment mode: {mode}")


def pad_image_bottom_right(
    image: np.ndarray,
    padded_width: int,
    padded_height: int,
) -> tuple[np.ndarray, np.ndarray]:
    if image.ndim != 2:
        raise ValueError(f"Expected grayscale image with shape (H, W), got {image.shape}")
    padded = np.zeros((padded_height, padded_width), dtype=image.dtype)
    padded[: image.shape[0], : image.shape[1]] = image
    mask = np.zeros((padded_height, padded_width), dtype=bool)
    mask[: image.shape[0], : image.shape[1]] = True
    return padded, mask


def read_image_pair(
    image_path: str,
    resize_width: int | None,
    resize_height: int | None,
    preprocess_mode: str,
) -> dict[str, object]:
    path = Path(image_path).expanduser().resolve()
    original_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    original_gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if original_bgr is None or original_gray is None:
        raise FileNotFoundError(f"Cannot read image: {path}")

    original_height, original_width = original_gray.shape[:2]
    content_width = resize_width if resize_width is not None else original_width
    content_height = resize_height if resize_height is not None else original_height

    if (content_width, content_height) != (original_width, original_height):
        interpolation = (
            cv2.INTER_AREA
            if content_width <= original_width and content_height <= original_height
            else cv2.INTER_LINEAR
        )
        content_gray = cv2.resize(original_gray, (content_width, content_height), interpolation=interpolation)
    else:
        content_gray = original_gray

    if preprocess_mode == "pad":
        infer_width, infer_height = align_size_to_divisible(
            content_width,
            content_height,
            DIVISIBILITY,
            mode="ceil",
        )
        infer_gray, infer_mask = pad_image_bottom_right(content_gray, infer_width, infer_height)
    elif preprocess_mode == "resize":
        infer_width, infer_height = align_size_to_divisible(
            content_width,
            content_height,
            DIVISIBILITY,
            mode="floor",
        )
        if (infer_width, infer_height) != (content_width, content_height):
            interpolation = (
                cv2.INTER_AREA
                if infer_width <= content_width and infer_height <= content_height
                else cv2.INTER_LINEAR
            )
            infer_gray = cv2.resize(content_gray, (infer_width, infer_height), interpolation=interpolation)
        else:
            infer_gray = content_gray
        infer_mask = None
        content_width, content_height = infer_width, infer_height
    else:
        raise ValueError(
            f"Unsupported preprocess mode '{preprocess_mode}'. Supported: {', '.join(SUPPORTED_PREPROCESS_MODES)}"
        )

    infer_tensor = torch.from_numpy(infer_gray)[None][None].float() / 255.0
    scale_x = original_width / float(content_width)
    scale_y = original_height / float(content_height)

    return {
        "path": path,
        "original_bgr": original_bgr,
        "original_gray": original_gray,
        "content_gray": content_gray,
        "infer_gray": infer_gray,
        "infer_tensor": infer_tensor,
        "infer_mask": None if infer_mask is None else torch.from_numpy(infer_mask),
        "original_size": (original_width, original_height),
        "content_size": (content_width, content_height),
        "infer_size": (infer_width, infer_height),
        "scale": (scale_x, scale_y),
    }


def build_coarse_mask(valid_mask: torch.Tensor, matcher) -> torch.Tensor:
    if valid_mask.ndim != 2:
        raise ValueError(f"Expected valid mask with shape (H, W), got {tuple(valid_mask.shape)}")
    coarse_divisor = int(matcher.config["resolution"][0])
    coarse_scale = 1.0 / float(coarse_divisor)
    coarse_mask = F.interpolate(
        valid_mask[None, None].float(),
        scale_factor=coarse_scale,
        mode="nearest",
        recompute_scale_factor=False,
    )[0, 0].bool()
    return coarse_mask


def ensure_position_encoding_capacity(
    matcher,
    left: dict[str, object],
    right: dict[str, object],
    device: torch.device,
) -> None:
    current_height = int(matcher.pos_encoding.pe.shape[-2])
    current_width = int(matcher.pos_encoding.pe.shape[-1])

    coarse_divisor = int(matcher.config["resolution"][0])
    max_input_height = max(int(left["infer_size"][1]), int(right["infer_size"][1]))
    max_input_width = max(int(left["infer_size"][0]), int(right["infer_size"][0]))
    required_height = int(math.ceil(max_input_height / float(coarse_divisor)))
    required_width = int(math.ceil(max_input_width / float(coarse_divisor)))

    if required_height <= current_height and required_width <= current_width:
        return

    pos_encoding_cls = matcher.pos_encoding.__class__
    new_height = max(current_height, required_height)
    new_width = max(current_width, required_width)
    matcher.pos_encoding = pos_encoding_cls(
        matcher.config["coarse"]["d_model"],
        max_shape=(new_height, new_width),
        temp_bug_fix=matcher.config["coarse"]["temp_bug_fix"],
    ).to(device)


def run_loftr_matching(matcher, left: dict[str, object], right: dict[str, object], device: torch.device):
    ensure_position_encoding_capacity(matcher, left, right, device)
    batch = {
        "image0": left["infer_tensor"].to(device),
        "image1": right["infer_tensor"].to(device),
    }
    if left["infer_mask"] is not None and right["infer_mask"] is not None:
        batch["mask0"] = build_coarse_mask(left["infer_mask"], matcher)[None].to(device)
        batch["mask1"] = build_coarse_mask(right["infer_mask"], matcher)[None].to(device)
    with torch.inference_mode():
        matcher(batch)

    mkpts0 = batch["mkpts0_f"].detach().cpu().numpy()
    mkpts1 = batch["mkpts1_f"].detach().cpu().numpy()
    mconf = batch["mconf"].detach().cpu().numpy()
    return mkpts0, mkpts1, mconf


def filter_matches(
    mkpts0: np.ndarray,
    mkpts1: np.ndarray,
    mconf: np.ndarray,
    min_confidence: float | None,
    top_k: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if min_confidence is not None:
        keep_mask = mconf >= float(min_confidence)
        mkpts0 = mkpts0[keep_mask]
        mkpts1 = mkpts1[keep_mask]
        mconf = mconf[keep_mask]

    if len(mconf) == 0:
        return mkpts0, mkpts1, mconf

    order = np.argsort(-mconf)
    if top_k is not None and top_k > 0:
        order = order[:top_k]
    return mkpts0[order], mkpts1[order], mconf[order]


def geometric_filter_min_points(method: str) -> int:
    if method == "homography":
        return 4
    if method == "fundamental":
        return 8
    return 0


def _resolve_cv2_geometric_method(method: str) -> int:
    if hasattr(cv2, "USAC_MAGSAC"):
        return cv2.USAC_MAGSAC
    if method == "homography":
        return cv2.RANSAC
    return cv2.FM_RANSAC


def _find_homography_with_ransac(
    points0: np.ndarray,
    points1: np.ndarray,
    reproj_threshold: float,
    confidence: float,
    max_iters: int,
):
    method = _resolve_cv2_geometric_method("homography")
    try:
        return cv2.findHomography(
            points0,
            points1,
            method=method,
            ransacReprojThreshold=float(reproj_threshold),
            confidence=float(confidence),
            maxIters=int(max_iters),
        )
    except TypeError:
        return cv2.findHomography(
            points0,
            points1,
            method=method,
            ransacReprojThreshold=float(reproj_threshold),
            confidence=float(confidence),
        )


def _find_fundamental_with_ransac(
    points0: np.ndarray,
    points1: np.ndarray,
    reproj_threshold: float,
    confidence: float,
    max_iters: int,
):
    method = _resolve_cv2_geometric_method("fundamental")
    try:
        return cv2.findFundamentalMat(
            points0,
            points1,
            method=method,
            ransacReprojThreshold=float(reproj_threshold),
            confidence=float(confidence),
            maxIters=int(max_iters),
        )
    except TypeError:
        return cv2.findFundamentalMat(
            points0,
            points1,
            method=method,
            ransacReprojThreshold=float(reproj_threshold),
            confidence=float(confidence),
        )


def apply_geometric_filter(
    points0: np.ndarray,
    points1: np.ndarray,
    confidences: np.ndarray,
    method: str,
    reproj_threshold: float,
    confidence: float,
    max_iters: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    stats: dict[str, object] = {
        "method": method,
        "status": "not-requested",
        "input_count": int(len(confidences)),
        "output_count": int(len(confidences)),
        "required_points": geometric_filter_min_points(method),
        "model_matrix": None,
    }

    if method == "none":
        stats["status"] = "not-requested"
        return points0, points1, confidences, stats

    if len(confidences) == 0:
        stats["status"] = "skipped-empty"
        return points0, points1, confidences, stats

    required_points = geometric_filter_min_points(method)
    if len(confidences) < required_points:
        stats["status"] = "skipped-insufficient-points"
        return points0, points1, confidences, stats

    estimate_points0 = np.asarray(points0, dtype=np.float64)
    estimate_points1 = np.asarray(points1, dtype=np.float64)
    if method == "homography":
        model_matrix, mask = _find_homography_with_ransac(
            estimate_points0,
            estimate_points1,
            reproj_threshold,
            confidence,
            max_iters,
        )
    else:
        model_matrix, mask = _find_fundamental_with_ransac(
            estimate_points0,
            estimate_points1,
            reproj_threshold,
            confidence,
            max_iters,
        )

    stats["model_matrix"] = model_matrix
    if model_matrix is None or mask is None:
        stats["status"] = "failed"
        empty_points0 = points0[:0]
        empty_points1 = points1[:0]
        empty_conf = confidences[:0]
        stats["output_count"] = 0
        return empty_points0, empty_points1, empty_conf, stats

    keep_mask = mask.reshape(-1).astype(bool)
    if keep_mask.size != len(confidences):
        keep_mask = keep_mask[: len(confidences)]

    filtered_points0 = points0[keep_mask]
    filtered_points1 = points1[keep_mask]
    filtered_confidences = confidences[keep_mask]
    stats["status"] = "applied"
    stats["output_count"] = int(len(filtered_confidences))
    stats["outlier_count"] = int(len(confidences) - len(filtered_confidences))
    return filtered_points0, filtered_points1, filtered_confidences, stats


def scale_points_to_original(points: np.ndarray, scale: tuple[float, float]) -> np.ndarray:
    if len(points) == 0:
        return points.astype(np.float64)
    scaled = points.astype(np.float64).copy()
    scaled[:, 0] *= scale[0]
    scaled[:, 1] *= scale[1]
    return scaled


def confidence_to_bgr(confidence: float, conf_min: float, conf_max: float) -> tuple[int, int, int]:
    if conf_max <= conf_min:
        normalized = 255
    else:
        normalized = int(round(255.0 * (confidence - conf_min) / (conf_max - conf_min)))
    color_map = cv2.applyColorMap(np.array([[normalized]], dtype=np.uint8), cv2.COLORMAP_JET)
    bgr = color_map[0, 0]
    return int(bgr[0]), int(bgr[1]), int(bgr[2])


def draw_match_lines(
    image0_bgr: np.ndarray,
    image1_bgr: np.ndarray,
    points0: np.ndarray,
    points1: np.ndarray,
    confidences: np.ndarray,
    output_path: Path,
    max_visualized_matches: int | None,
) -> None:
    height0, width0 = image0_bgr.shape[:2]
    height1, width1 = image1_bgr.shape[:2]
    canvas_height = max(height0, height1)
    canvas_width = width0 + width1
    canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
    canvas[:height0, :width0] = image0_bgr
    canvas[:height1, width0:width0 + width1] = image1_bgr

    match_count = min(len(points0), len(points1), len(confidences))
    if max_visualized_matches is not None and max_visualized_matches > 0:
        match_count = min(match_count, max_visualized_matches)

    conf_min = float(confidences[:match_count].min()) if match_count else 0.0
    conf_max = float(confidences[:match_count].max()) if match_count else 1.0

    for index in range(match_count):
        left_point_xy = np.round(points0[index]).astype(int)
        right_point_xy = np.round(points1[index]).astype(int)
        left_point = (int(left_point_xy[0]), int(left_point_xy[1]))
        right_point = (int(right_point_xy[0] + width0), int(right_point_xy[1]))
        color = confidence_to_bgr(float(confidences[index]), conf_min, conf_max)
        cv2.circle(canvas, left_point, 4, color, thickness=-1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, right_point, 4, color, thickness=-1, lineType=cv2.LINE_AA)
        cv2.line(canvas, left_point, right_point, color, thickness=1, lineType=cv2.LINE_AA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), canvas):
        raise RuntimeError(f"Failed to write match visualization image to {output_path}")


def save_matches_csv(output_csv: Path, points0: np.ndarray, points1: np.ndarray, confidences: np.ndarray) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["match_index", "x0", "y0", "x1", "y1", "confidence"])
        for index, (point0, point1, confidence) in enumerate(zip(points0, points1, confidences)):
            writer.writerow([
                index,
                f"{float(point0[0]):.6f}",
                f"{float(point0[1]):.6f}",
                f"{float(point1[0]):.6f}",
                f"{float(point1[1]):.6f}",
                f"{float(confidence):.8f}",
            ])


def describe_geometric_filter_stats(stats: dict[str, object]) -> str:
    method = str(stats.get("method", "none"))
    status = str(stats.get("status", "unknown"))
    if method == "none":
        return "none"
    if status == "applied":
        return (
            f"{method} (kept {stats.get('output_count', 0)}/{stats.get('input_count', 0)}, "
            f"removed {stats.get('outlier_count', 0)})"
        )
    if status == "skipped-insufficient-points":
        return (
            f"{method} skipped: insufficient points "
            f"({stats.get('input_count', 0)} < {stats.get('required_points', 0)})"
        )
    if status == "skipped-empty":
        return f"{method} skipped: no matches left after confidence filtering"
    if status == "failed":
        return f"{method} failed: no robust model consensus found"
    return f"{method} status={status}"


def main() -> None:
    args = parse_args()
    validate_resize_args(args.resize_width, args.resize_height)
    validate_ransac_args(
        args.geometric_filter,
        args.ransac_reproj_threshold,
        args.ransac_confidence,
        args.ransac_max_iters,
    )

    device = resolve_device(args.device)
    loftr_root = find_loftr_root(args.loftr_root)
    checkpoint_path = resolve_checkpoint(args.checkpoint, loftr_root, args.model_type)
    temp_bug_fix = resolve_temp_bug_fix(args.temp_bug_fix, args.model_type)

    left = read_image_pair(
        args.left_image,
        args.resize_width,
        args.resize_height,
        args.preprocess_mode,
    )
    right = read_image_pair(
        args.right_image,
        args.resize_width,
        args.resize_height,
        args.preprocess_mode,
    )

    matcher = load_loftr_matcher(
        loftr_root,
        checkpoint_path,
        temp_bug_fix,
        device,
        coarse_threshold=args.coarse_threshold,
    )
    mkpts0, mkpts1, mconf = run_loftr_matching(matcher, left, right, device)
    raw_match_count = int(len(mconf))
    mkpts0, mkpts1, mconf = filter_matches(
        mkpts0,
        mkpts1,
        mconf,
        min_confidence=args.min_confidence,
        top_k=args.top_k,
    )
    post_confidence_count = int(len(mconf))

    scaled_points0 = scale_points_to_original(mkpts0, left["scale"])
    scaled_points1 = scale_points_to_original(mkpts1, right["scale"])
    scaled_points0, scaled_points1, mconf, geometric_stats = apply_geometric_filter(
        scaled_points0,
        scaled_points1,
        mconf,
        method=args.geometric_filter,
        reproj_threshold=args.ransac_reproj_threshold,
        confidence=args.ransac_confidence,
        max_iters=args.ransac_max_iters,
    )

    output_match_image = build_output_path(
        args.output_match_image,
        suffix="-matches.png",
        left_image=args.left_image,
        right_image=args.right_image,
        model_type=args.model_type,
        geometric_filter=args.geometric_filter,
    )
    draw_match_lines(
        left["original_bgr"],
        right["original_bgr"],
        scaled_points0,
        scaled_points1,
        mconf,
        output_match_image,
        args.max_visualized_matches,
    )

    print("=== LoFTR Matching ===")
    print(f"  Device: {device}")
    print(f"  Model type: {args.model_type}")
    print(f"  LoFTR root: {loftr_root}")
    print(f"  Checkpoint: {checkpoint_path}")
    print(f"  temp_bug_fix: {temp_bug_fix}")
    if args.coarse_threshold is not None:
        print(f"  Coarse threshold override: {args.coarse_threshold}")
    print(f"  Preprocess mode: {args.preprocess_mode}")
    print(f"  Left image: {left['path']}")
    print(f"  Right image: {right['path']}")
    print(f"  Left original size: {left['original_size'][0]}x{left['original_size'][1]}")
    print(f"  Right original size: {right['original_size'][0]}x{right['original_size'][1]}")
    print(f"  Left content size: {left['content_size'][0]}x{left['content_size'][1]}")
    print(f"  Right content size: {right['content_size'][0]}x{right['content_size'][1]}")
    print(f"  Left inference size: {left['infer_size'][0]}x{left['infer_size'][1]}")
    print(f"  Right inference size: {right['infer_size'][0]}x{right['infer_size'][1]}")
    print(f"  Raw matched points: {raw_match_count}")
    if args.min_confidence is not None:
        print(f"  Minimum confidence: {args.min_confidence}")
    if args.top_k is not None:
        print(f"  Top-K kept: {args.top_k}")
    print(f"  After confidence/top-k: {post_confidence_count}")
    print(f"  Geometric filter: {describe_geometric_filter_stats(geometric_stats)}")
    print(f"  Final matched points: {len(mconf)}")
    print(f"  Output visualization: {output_match_image}")

    if args.output_csv:
        output_csv = build_output_path(
            args.output_csv,
            suffix="-matches.csv",
            left_image=args.left_image,
            right_image=args.right_image,
            model_type=args.model_type,
            geometric_filter=args.geometric_filter,
        )
        save_matches_csv(output_csv, scaled_points0, scaled_points1, mconf)
        print(f"  Output CSV: {output_csv}")


if __name__ == "__main__":
    main()
