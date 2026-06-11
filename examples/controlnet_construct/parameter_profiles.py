"""Named parameter profiles for ControlNet construction wrappers."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
import shlex


PARAMETER_PROFILES: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "conservative": MappingProxyType(
            {
                "valid_pixel_percent_threshold": 0.08,
                "invalid_pixel_radius": 2,
                "matcher_method": "bf",
                "enable_low_resolution_offset_estimation": True,
                "low_resolution_level": 3,
                "low_resolution_max_mean_reprojection_error_pixels": 2.5,
                "low_resolution_min_retained_match_count": 8,
                "low_resolution_max_mean_projected_offset_meters": 1200,
                "num_worker_parallel_cpu": 8,
            }
        ),
        "balanced": MappingProxyType(
            {
                "valid_pixel_percent_threshold": 0.05,
                "invalid_pixel_radius": 1,
                "matcher_method": "bf",
                "enable_low_resolution_offset_estimation": True,
                "low_resolution_level": 3,
                "low_resolution_max_mean_reprojection_error_pixels": 3.0,
                "low_resolution_min_retained_match_count": 5,
                "low_resolution_max_mean_projected_offset_meters": 2000,
                "num_worker_parallel_cpu": 8,
            }
        ),
        "aggressive": MappingProxyType(
            {
                "valid_pixel_percent_threshold": 0.02,
                "invalid_pixel_radius": 1,
                "matcher_method": "bf",
                "enable_low_resolution_offset_estimation": True,
                "low_resolution_level": 4,
                "low_resolution_max_mean_reprojection_error_pixels": 4.0,
                "low_resolution_min_retained_match_count": 4,
                "low_resolution_max_mean_projected_offset_meters": 3500,
                "num_worker_parallel_cpu": 12,
            }
        ),
    }
)

PARAMETER_PROFILE_NAMES = tuple(PARAMETER_PROFILES)


def parameter_profile_values(profile_name: str) -> dict[str, Any]:
    """Return a mutable copy of the values for a named profile."""

    try:
        return dict(PARAMETER_PROFILES[profile_name])
    except KeyError as exc:
        allowed = ", ".join(PARAMETER_PROFILE_NAMES)
        raise ValueError(f"parameter_profile must be one of: {allowed}.") from exc


def _shell_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def shell_assignments_for_parameter_profile(profile_name: str) -> str:
    """Return shell assignments for wrapper-side profile application."""

    values = parameter_profile_values(profile_name)
    assignments = []
    for name, value in values.items():
        variable_name = "PROFILE_" + name.upper()
        assignments.append(f"{variable_name}={shlex.quote(_shell_value(value))}")
    return "\n".join(assignments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PARAMETER_PROFILE_NAMES)
    parser.add_argument("--shell-assignments", action="store_true")
    args = parser.parse_args(argv)

    if args.shell_assignments:
        print(shell_assignments_for_parameter_profile(args.profile))
        return 0

    for name, value in parameter_profile_values(args.profile).items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
