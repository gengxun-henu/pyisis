"""Frontend helpers for model-backed deep matcher pipelines."""

from __future__ import annotations

import numpy as np


SUPPORTED_DEEP_METHODS = ("superglue", "lightglue", "loftr")


class DeepFrontendError(RuntimeError):
    """Raised when deep frontend setup fails."""


class DeepDependencyError(RuntimeError):
    """Raised when deep matcher dependencies are unavailable."""

    def __init__(self, method: str, reason: str) -> None:
        self.method = str(method).strip().lower()
        self.reason = str(reason).strip()
        super().__init__(f"Deep matcher dependency unavailable for '{self.method}': {self.reason}")


def _raise_missing_dependency(*, method: str, missing: str, install_hint: str) -> None:
    raise DeepDependencyError(
        method,
        f"missing optional dependency '{missing}'. Install with `{install_hint}`.",
    )


def _require_kornia_feature(*, method: str, feature_name: str, install_hint: str):
    try:
        import kornia.feature as kf
    except Exception:
        _raise_missing_dependency(
            method=method,
            missing="kornia",
            install_hint=install_hint,
        )

    if not hasattr(kf, feature_name):
        _raise_missing_dependency(
            method=method,
            missing=f"kornia.feature.{feature_name}",
            install_hint=install_hint,
        )
    return kf


class SuperPointFrontend:
    def __init__(self) -> None:
        self._extractor = None

    def extract(self, image, device: str):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="superglue/lightglue",
                missing="torch",
                install_hint="pip install torch kornia",
            )

        kf = _require_kornia_feature(
            method="superglue/lightglue",
            feature_name="SuperPoint",
            install_hint="pip install kornia",
        )

        image_array = np.asarray(image, dtype=np.float32)
        if image_array.size <= 0:
            return {"keypoints": np.zeros((0, 2), dtype=np.float32), "descriptors": np.zeros((0, 256), dtype=np.float32)}

        if image_array.ndim == 0:
            image_plane = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_plane = image_array.reshape(1, -1)
        elif image_array.ndim == 2:
            image_plane = image_array
        else:
            image_plane = np.mean(image_array, axis=-1)

        image_plane = np.nan_to_num(image_plane, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_plane))) if image_plane.size > 0 else 0.0
        if scale > 0.0:
            image_plane = image_plane / scale
        image_tensor = torch.from_numpy(image_plane).to(dtype=torch.float32)[None, None, :, :].to(device)

        if self._extractor is None:
            self._extractor = kf.SuperPoint(pretrained="superpoint_v1")
        self._extractor = self._extractor.to(device).eval()

        with torch.no_grad():
            scores, keypoints, descriptors = self._extractor(image_tensor)
        keypoint_array = keypoints[0].detach().cpu().numpy().astype(np.float32, copy=False)
        descriptor_array = descriptors[0].detach().cpu().numpy().T.astype(np.float32, copy=False)
        _ = scores
        return {"keypoints": keypoint_array, "descriptors": descriptor_array}


class LoFTRFrontend:
    def __init__(self) -> None:
        self._torch = None

    def prepare(self, left_image, right_image, device: str):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="loftr",
                missing="torch",
                install_hint="pip install torch kornia",
            )

        _require_kornia_feature(
            method="loftr",
            feature_name="SuperPoint",
            install_hint="pip install \"kornia[loftr]\"",
        )

        self._torch = torch
        return {
            "left": self._as_tensor(left_image, device=device),
            "right": self._as_tensor(right_image, device=device),
        }

    def _as_tensor(self, image, *, device: str):
        image_array = np.asarray(image, dtype=np.float32)
        if image_array.ndim == 0:
            image_plane = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_plane = image_array.reshape(1, -1)
        elif image_array.ndim == 2:
            image_plane = image_array
        else:
            image_plane = np.mean(image_array, axis=-1)

        image_plane = np.nan_to_num(image_plane, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_plane))) if image_plane.size > 0 else 0.0
        if scale > 0.0:
            image_plane = image_plane / scale
        return self._torch.from_numpy(image_plane).to(dtype=self._torch.float32)[None, None, :, :].to(device)


def normalize_deep_method(method: str) -> str:
    normalized = str(method).strip().lower()
    if normalized not in SUPPORTED_DEEP_METHODS:
        raise DeepFrontendError(f"Unsupported deep matcher method {method!r}. Expected one of {SUPPORTED_DEEP_METHODS}.")
    return normalized


def resolve_torch_device(prefer_gpu: bool) -> str:
    if not prefer_gpu:
        return "cpu"

    try:
        import torch
    except Exception:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"
