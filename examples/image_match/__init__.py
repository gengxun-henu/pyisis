"""Shared image-matching helpers used by multiple example workflows."""

from __future__ import annotations

from importlib import import_module

from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file

_LAZY_IMAGE_MATCH_EXPORTS = {
    "match_dom_pair_to_key_files",
    "match_ori_pair_to_key_files",
}
_LAZY_MATCH_VIS_EXPORTS = {
    "write_stereo_pair_match_visualization_from_key_files",
}
_LAZY_RANSAC_EXPORTS = {
    "filter_stereo_pair_key_files_with_ransac",
}


def __getattr__(name: str):
    if name in _LAZY_IMAGE_MATCH_EXPORTS:
        module = import_module(".image_match", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_MATCH_VIS_EXPORTS:
        module = import_module(".match_visualization", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_RANSAC_EXPORTS:
        module = import_module(".stereo_ransac", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Keypoint",
    "KeypointFile",
    "filter_stereo_pair_key_files_with_ransac",
    "match_dom_pair_to_key_files",
    "match_ori_pair_to_key_files",
    "read_key_file",
    "write_key_file",
    "write_stereo_pair_match_visualization_from_key_files",
]
