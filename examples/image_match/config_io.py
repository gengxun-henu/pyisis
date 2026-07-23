"""Shared JSON configuration helpers for image matching.

Author: Geng Xun
Created: 2026-07-23
Updated: 2026-07-23  Geng Xun extracted config container, coercion, and shell formatting helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


ConfigContainerOrder = Literal["image-match-first", "top-level-first"]


def image_match_config_containers(
    payload: object,
    *,
    container_order: ConfigContainerOrder = "image-match-first",
) -> list[dict[str, object]]:
    """Return config containers in the requested precedence order."""

    if not isinstance(payload, dict):
        raise ValueError("image_match config JSON must decode to an object at the top level.")

    image_match_containers: list[dict[str, object]] = []
    for key in ("ImageMatch", "image_match", "imageMatch"):
        value = payload.get(key)
        if isinstance(value, dict):
            image_match_containers.append(value)

    if container_order == "top-level-first":
        return [payload, *image_match_containers]
    if container_order == "image-match-first":
        return [*image_match_containers, payload]
    raise ValueError(f"Unsupported ImageMatch config container order: {container_order}")


def first_present_config_value(
    containers: list[dict[str, object]],
    candidate_keys: tuple[str, ...],
) -> object | None:
    """Find the first non-empty candidate value across config containers."""

    for container in containers:
        for key in candidate_keys:
            if key not in container:
                continue
            value = container[key]
            if value is None:
                continue
            if isinstance(value, str) and value == "":
                continue
            return value
    return None


def coerce_config_bool(value: object, *, field_name: str) -> bool:
    """Convert common JSON and shell boolean spellings to bool."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field_name} in config JSON must be a boolean-compatible value.")


def coerce_invalid_value_list(value: object) -> list[float]:
    """Normalize one or several invalid pixel values to a float list."""

    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return [float(value)]


def coerce_string_mapping(value: object, *, field_name: str) -> dict[str, str]:
    """Normalize a JSON object to a non-empty string mapping."""

    if not isinstance(value, dict):
        raise ValueError(f"{field_name} in config JSON must be an object.")
    return {
        str(key).strip(): str(item)
        for key, item in value.items()
        if key not in (None, "") and item not in (None, "")
    }


def resolve_config_relative_string_mapping(
    mapping: dict[str, str],
    *,
    config_path: str | Path,
    repo_root: str | Path,
) -> dict[str, str]:
    """Resolve mapping values against the config directory, then repository."""

    config_dir = Path(config_path).parent
    resolved_repo_root = Path(repo_root)
    resolved_mapping: dict[str, str] = {}
    for key, value in mapping.items():
        resolved_value = Path(value).expanduser()
        if resolved_value.is_absolute():
            resolved_mapping[key] = str(resolved_value)
            continue

        config_relative_candidate = config_dir / resolved_value
        if config_relative_candidate.exists():
            resolved_value = config_relative_candidate
        else:
            resolved_value = resolved_repo_root / resolved_value
        resolved_mapping[key] = str(resolved_value)
    return resolved_mapping


def format_image_match_default_for_shell(value: object) -> str:
    """Format a scalar config default for consumption by shell wrappers."""

    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        raise ValueError("List-valued ImageMatch defaults cannot be printed as a single shell scalar.")
    return str(value)
