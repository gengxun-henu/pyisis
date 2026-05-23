"""Neutral match preset resolution for ControlNet image matching."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import shlex
from typing import Any

try:
    from .deep_match_config import DEEP_MATCHER_METHODS, load_deep_match_config
except ImportError:
    from deep_match_config import DEEP_MATCHER_METHODS, load_deep_match_config


CLASSIC_SIFT_FEATURE_METHOD = "classic_sift"
CLASSIC_SIFT_MATCHER_METHODS = ("bf", "flann")
CLASSIC_SIFT_FEATURE_OPTIONS = {
    "method",
    "max_features",
    "octave_layers",
    "contrast_threshold",
    "edge_threshold",
    "sigma",
}
CLASSIC_SIFT_MATCHER_OPTIONS = {"method", "ratio_test"}
CLASSIC_SIFT_DEEP_ONLY_SECTIONS = ("device", "fallback")


class MatchPresetConfigError(ValueError):
    """Raised when a neutral match preset is invalid."""


@dataclass(frozen=True, slots=True)
class MatchPresetRuntimeConfig:
    """Resolved match preset values consumed by image_match and wrappers."""

    preset_path: str
    matcher_method: str
    is_deep_matcher: bool
    deep_match_config_path: str | None
    image_match_defaults: dict[str, Any]
    raw_config: dict[str, Any]


def _load_json_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise MatchPresetConfigError(f"match preset file not found: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MatchPresetConfigError(f"match preset JSON parse failed: {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MatchPresetConfigError("match preset must be a JSON object.")
    return payload


def _require_mapping(config: dict[str, Any], section_name: str) -> dict[str, Any]:
    section = config.get(section_name)
    if not isinstance(section, dict):
        raise MatchPresetConfigError(f"match preset requires object section '{section_name}'.")
    return section


def _check_unknown_options(section: dict[str, Any], allowed: set[str], section_name: str) -> None:
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise MatchPresetConfigError(
            f"unsupported classic_sift {section_name} option(s): {', '.join(unknown)}"
        )


def _require_finite_number(section: dict[str, Any], field_name: str, section_name: str) -> int | float:
    value = section.get(field_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MatchPresetConfigError(f"{section_name}.{field_name} must be a finite number.")
    return value


def _require_positive_int(section: dict[str, Any], field_name: str, section_name: str) -> int:
    value = _require_finite_number(section, field_name, section_name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MatchPresetConfigError(f"{section_name}.{field_name} must be a positive integer.")
    return value


def _require_positive_number(section: dict[str, Any], field_name: str, section_name: str) -> int | float:
    value = _require_finite_number(section, field_name, section_name)
    if value <= 0:
        raise MatchPresetConfigError(f"{section_name}.{field_name} must be a positive number.")
    return value


def _resolve_classic_sift_config(
    resolved_path: Path,
    config: dict[str, Any],
    feature_extractor: dict[str, Any],
    matcher: dict[str, Any],
) -> MatchPresetRuntimeConfig:
    deep_only_sections = [section for section in CLASSIC_SIFT_DEEP_ONLY_SECTIONS if section in config]
    if deep_only_sections:
        raise MatchPresetConfigError(
            f"classic_sift presets cannot include deep-only section(s): {', '.join(deep_only_sections)}"
        )

    _check_unknown_options(feature_extractor, CLASSIC_SIFT_FEATURE_OPTIONS, "feature_extractor")
    _check_unknown_options(matcher, CLASSIC_SIFT_MATCHER_OPTIONS, "matcher")

    feature_method = str(feature_extractor.get("method", "")).strip().lower()
    if feature_method != CLASSIC_SIFT_FEATURE_METHOD:
        raise MatchPresetConfigError(
            f"classic SIFT presets require feature_extractor.method '{CLASSIC_SIFT_FEATURE_METHOD}'."
        )

    matcher_method = str(matcher.get("method", "")).strip().lower()
    if matcher_method not in CLASSIC_SIFT_MATCHER_METHODS:
        raise MatchPresetConfigError(
            "classic_sift matcher.method must be one of "
            f"{', '.join(CLASSIC_SIFT_MATCHER_METHODS)}."
        )

    ratio_test = _require_finite_number(matcher, "ratio_test", "matcher")
    if ratio_test <= 0 or ratio_test > 1:
        raise MatchPresetConfigError("matcher.ratio_test must be in the range (0, 1].")

    defaults = {
        "match_preset_path": str(resolved_path),
        "matcher_method": matcher_method,
        "deep_match_config_path": None,
        "max_features": _require_positive_int(feature_extractor, "max_features", "feature_extractor"),
        "sift_octave_layers": _require_positive_int(feature_extractor, "octave_layers", "feature_extractor"),
        "sift_contrast_threshold": _require_positive_number(
            feature_extractor, "contrast_threshold", "feature_extractor"
        ),
        "sift_edge_threshold": _require_positive_number(feature_extractor, "edge_threshold", "feature_extractor"),
        "sift_sigma": _require_positive_number(feature_extractor, "sigma", "feature_extractor"),
        "ratio_test": ratio_test,
    }

    return MatchPresetRuntimeConfig(
        preset_path=str(resolved_path),
        matcher_method=matcher_method,
        is_deep_matcher=False,
        deep_match_config_path=None,
        image_match_defaults=defaults,
        raw_config=config,
    )


def resolve_match_preset_runtime_config(config_path: str | Path) -> MatchPresetRuntimeConfig:
    """Resolve a classic or deep match preset into image_match-facing defaults."""

    resolved_path = Path(config_path).resolve()
    config = _load_json_config(resolved_path)
    feature_extractor = _require_mapping(config, "feature_extractor")
    matcher = _require_mapping(config, "matcher")

    matcher_method = str(matcher.get("method", "")).strip().lower()
    if matcher_method in DEEP_MATCHER_METHODS:
        try:
            deep_config = load_deep_match_config(resolved_path)
        except ValueError as exc:
            raise MatchPresetConfigError(str(exc)) from exc
        defaults = {
            "match_preset_path": str(resolved_path),
            "matcher_method": matcher_method,
            "deep_match_config_path": str(resolved_path),
        }
        return MatchPresetRuntimeConfig(
            preset_path=str(resolved_path),
            matcher_method=matcher_method,
            is_deep_matcher=True,
            deep_match_config_path=str(resolved_path),
            image_match_defaults=defaults,
            raw_config=deep_config,
        )

    return _resolve_classic_sift_config(resolved_path, config, feature_extractor, matcher)


def resolve_match_preset_path(
    raw_path: str | Path,
    *,
    config_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> Path:
    """Resolve a match preset path, preferring config-relative and repo-root paths."""

    raw = Path(raw_path).expanduser()

    if config_path is not None:
        config_relative = (Path(config_path).expanduser().resolve().parent / raw).resolve()
        if config_relative.exists():
            return config_relative

    if repo_root is not None:
        repo_relative = (Path(repo_root).expanduser().resolve() / raw).resolve()
        if repo_relative.exists():
            return repo_relative

    return raw.resolve()


def shell_assignments_for_match_preset(config_path: str | Path) -> dict[str, str]:
    """Return shell variable values for a resolved match preset."""

    runtime = resolve_match_preset_runtime_config(config_path)
    return {
        "MATCH_PRESET_PATH": runtime.preset_path,
        "MATCH_PRESET_IS_DEEP": "1" if runtime.is_deep_matcher else "0",
        "MATCHER_METHOD": runtime.matcher_method,
        "DEEP_MATCHER_CONFIG_PATH": runtime.deep_match_config_path or "",
    }


def format_shell_assignments(assignments: dict[str, str]) -> str:
    """Format shell assignments with safely quoted values."""

    return "\n".join(f"{key}={shlex.quote(str(value))}" for key, value in assignments.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preset_path", help="Path to a classic SIFT or deep match preset JSON file.")
    parser.add_argument(
        "--shell-assignments",
        action="store_true",
        help="Print shell assignments for wrapper scripts.",
    )
    args = parser.parse_args(argv)

    if args.shell_assignments:
        print(format_shell_assignments(shell_assignments_for_match_preset(args.preset_path)))
        return 0

    runtime = resolve_match_preset_runtime_config(args.preset_path)
    print(json.dumps(runtime.image_match_defaults, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
