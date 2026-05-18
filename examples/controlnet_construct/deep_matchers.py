"""Model-backed matcher wrappers for deep matcher methods.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example helper modules follow the repository's example-file header convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .deep_frontends import normalize_deep_method


class DeepMatcherError(RuntimeError):
    """Raised for unsupported deep matcher operations."""


def _missing_dependency_error(*, method: str, missing: str, install_hint: str) -> DeepMatcherError:
    return DeepMatcherError(
        f"Deep matcher '{method}' dependency unavailable: missing '{missing}'. Install with `{install_hint}`."
    )


@dataclass(frozen=True, slots=True)
class DeepMatchResult:
    left_keypoints: tuple[Any, ...] = ()
    right_keypoints: tuple[Any, ...] = ()
    matches: tuple[Any, ...] = ()


class SuperGlueMatcher:
    method = "superglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device
        self._model = None

    def _load_model(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch superglue-pretrained-network",
            )

        try:
            from models.matching import Matching  # type: ignore[import-not-found]
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="superglue-pretrained-network",
                install_hint="pip install superglue-pretrained-network",
            )

        if self._model is None:
            self._model = Matching(
                {
                    "superpoint": {"nms_radius": 4, "keypoint_threshold": 0.005, "max_keypoints": 2048},
                    "superglue": {"weights": "outdoor", "sinkhorn_iterations": 20, "match_threshold": 0.2},
                }
            ).eval().to(self.device)
        return torch, self._model

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        torch, model = self._load_model()
        _ = device
        left_keypoints = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_keypoints = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        left_descriptors = np.asarray(
            (features_left or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        right_descriptors = np.asarray(
            (features_right or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )

        if left_keypoints.shape[0] <= 0 or right_keypoints.shape[0] <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        left_scores = np.asarray((features_left or {}).get("scores", np.ones((left_keypoints.shape[0],), dtype=np.float32)), dtype=np.float32).reshape(-1)
        right_scores = np.asarray((features_right or {}).get("scores", np.ones((right_keypoints.shape[0],), dtype=np.float32)), dtype=np.float32).reshape(-1)
        if left_scores.shape[0] != left_keypoints.shape[0]:
            left_scores = np.ones((left_keypoints.shape[0],), dtype=np.float32)
        if right_scores.shape[0] != right_keypoints.shape[0]:
            right_scores = np.ones((right_keypoints.shape[0],), dtype=np.float32)
        match_input = {
            "keypoints0": torch.from_numpy(left_keypoints)[None, :, :].to(self.device),
            "keypoints1": torch.from_numpy(right_keypoints)[None, :, :].to(self.device),
            "descriptors0": torch.from_numpy(left_descriptors.T)[None, :, :].to(self.device),
            "descriptors1": torch.from_numpy(right_descriptors.T)[None, :, :].to(self.device),
            "scores0": torch.from_numpy(left_scores)[None, :].to(self.device),
            "scores1": torch.from_numpy(right_scores)[None, :].to(self.device),
        }

        with torch.no_grad():
            prediction = model(match_input)

        matches0 = prediction["matches0"][0].detach().cpu().numpy()
        scores0 = prediction["matching_scores0"][0].detach().cpu().numpy()
        valid_indices = np.where(matches0 >= 0)[0]
        if valid_indices.size <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        right_indices = matches0[valid_indices].astype(np.int64, copy=False)
        return (
            left_keypoints[valid_indices].astype(np.float32, copy=False),
            right_keypoints[right_indices].astype(np.float32, copy=False),
            scores0[valid_indices].astype(np.float32, copy=False),
        )


class LightGlueMatcher:
    method = "lightglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device
        self._matcher = None

    def _load_matcher(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch lightglue",
            )

        try:
            from lightglue import LightGlue  # type: ignore[import-not-found]
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="lightglue",
                install_hint="pip install lightglue",
            )

        if self._matcher is None:
            self._matcher = LightGlue(features="superpoint").eval().to(self.device)
        return torch, self._matcher

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        torch, matcher = self._load_matcher()
        _ = device
        left_keypoints = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_keypoints = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        left_descriptors = np.asarray(
            (features_left or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        right_descriptors = np.asarray(
            (features_right or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        if left_keypoints.shape[0] <= 0 or right_keypoints.shape[0] <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        inputs = {
            "image0": {
                "keypoints": torch.from_numpy(left_keypoints)[None, :, :].to(self.device),
                "descriptors": torch.from_numpy(left_descriptors)[None, :, :].to(self.device),
            },
            "image1": {
                "keypoints": torch.from_numpy(right_keypoints)[None, :, :].to(self.device),
                "descriptors": torch.from_numpy(right_descriptors)[None, :, :].to(self.device),
            },
        }
        with torch.no_grad():
            prediction = matcher(inputs)

        if "matches0" in prediction and "matching_scores0" in prediction:
            matches0 = prediction["matches0"][0].detach().cpu().numpy()
            scores0 = prediction["matching_scores0"][0].detach().cpu().numpy()
            valid_indices = np.where(matches0 >= 0)[0]
            if valid_indices.size <= 0:
                return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
            right_indices = matches0[valid_indices].astype(np.int64, copy=False)
            return (
                left_keypoints[valid_indices].astype(np.float32, copy=False),
                right_keypoints[right_indices].astype(np.float32, copy=False),
                scores0[valid_indices].astype(np.float32, copy=False),
            )

        if "matches" in prediction:
            matches = prediction["matches"][0].detach().cpu().numpy().astype(np.int64, copy=False)
            scores = prediction.get("scores")
            if scores is None:
                score_array = np.ones((matches.shape[0],), dtype=np.float32)
            else:
                score_array = scores[0].detach().cpu().numpy().astype(np.float32, copy=False)
            if matches.size <= 0:
                return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
            return (
                left_keypoints[matches[:, 0]].astype(np.float32, copy=False),
                right_keypoints[matches[:, 1]].astype(np.float32, copy=False),
                score_array,
            )
        raise DeepMatcherError("LightGlue prediction did not include expected match tensors.")


class LoFTRMatcher:
    method = "loftr"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device
        self._matcher = None

    def _load_matcher(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch kornia",
            )
        try:
            import kornia.feature as kf
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="kornia",
                install_hint="pip install kornia",
            )
        if self._matcher is None:
            self._matcher = kf.LoFTR(pretrained="outdoor").eval().to(self.device)
        return torch, self._matcher

    def match(
        self,
        *,
        left_image: Any,
        right_image: Any,
        left_mask: Any = None,
        right_mask: Any = None,
        device: str = "cpu",
    ):
        torch, matcher = self._load_matcher()
        _ = device
        if left_image is None or right_image is None:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        matcher_inputs = {"image0": left_image.to(self.device), "image1": right_image.to(self.device)}
        if left_mask is not None:
            matcher_inputs["mask0"] = left_mask.to(self.device)
        if right_mask is not None:
            matcher_inputs["mask1"] = right_mask.to(self.device)
        with torch.no_grad():
            output = matcher(matcher_inputs)
        left_points = output["keypoints0"].detach().cpu().numpy().astype(np.float32, copy=False)
        right_points = output["keypoints1"].detach().cpu().numpy().astype(np.float32, copy=False)
        scores = output["confidence"].detach().cpu().numpy().astype(np.float32, copy=False)
        return left_points, right_points, scores


def build_deep_matcher(method: str, *, device: str = "cpu") -> SuperGlueMatcher | LightGlueMatcher | LoFTRMatcher:
    normalized = normalize_deep_method(method)
    if normalized == "superglue":
        return SuperGlueMatcher(device=device)
    if normalized == "lightglue":
        return LightGlueMatcher(device=device)
    if normalized == "loftr":
        return LoFTRMatcher(device=device)
    raise DeepMatcherError(f"Unsupported deep matcher method {method!r}.")
