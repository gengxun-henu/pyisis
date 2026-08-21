"""Resolve PyISIS GitHub Actions runner profiles into normalized outputs.

Author: Geng Xun
Created: 2026-08-01
Updated: 2026-08-01  Geng Xun extracted testable runner profile resolution.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Sequence


DEFAULTS = {
    "active_profile": "self-hosted-http",
    "fallback_conda_prefix": "/home/gengxun/miniconda3/envs/asp360_new",
}

COMMON_PROFILE_DEFAULTS = {
    "build_jobs": "auto",
    "ccache_max_size": "20G",
    "isis_major": "9",
    "python_abi": "cp312",
}

DEFAULT_PROFILES = {
    "self-hosted-http": {
        "mode": "self-hosted",
        "labels": ["self-hosted"],
        "checkout_transport": "https",
        "environment_strategy": "existing-conda",
        "network_profile": "plain-http",
        "use_watt": False,
        **COMMON_PROFILE_DEFAULTS,
    },
    "self-hosted-watt": {
        "mode": "self-hosted",
        "labels": ["self-hosted"],
        "checkout_transport": "https",
        "environment_strategy": "existing-conda",
        "network_profile": "watt-hosts",
        "use_watt": True,
        **COMMON_PROFILE_DEFAULTS,
    },
    "self-hosted-ssh": {
        "mode": "self-hosted",
        "labels": ["self-hosted"],
        "checkout_transport": "ssh",
        "environment_strategy": "existing-conda",
        "network_profile": "ssh-fallback",
        "use_watt": False,
        **COMMON_PROFILE_DEFAULTS,
    },
    "github-hosted": {
        "mode": "github-hosted",
        "github_hosted_runner": "ubuntu-22.04",
        "checkout_transport": "https",
        "environment_strategy": "micromamba",
        "network_profile": "github-hosted",
        "use_watt": False,
        **COMMON_PROFILE_DEFAULTS,
    },
}

LEGACY_DEFAULTS = {
    "mode": "self-hosted",
    "github_hosted_runner": "ubuntu-22.04",
    "self_hosted_labels": ["self-hosted"],
    "self_hosted_checkout_transport": "ssh",
    "github_hosted_checkout_transport": "https",
    "self_hosted_environment_strategy": "existing-conda",
    "github_hosted_environment_strategy": "micromamba",
    "fallback_conda_prefix": DEFAULTS["fallback_conda_prefix"],
    **COMMON_PROFILE_DEFAULTS,
}


class RunnerResolution:
    """Normalized output values plus non-fatal configuration diagnostics."""

    def __init__(self, outputs: dict[str, str], diagnostics: Sequence[str]) -> None:
        self.outputs = outputs
        self.diagnostics = tuple(diagnostics)


def parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
    if value.startswith("{") or value.startswith(('"', "'")):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def parse_config_file(path: Path) -> tuple[dict[str, object], list[str]]:
    parsed: dict[str, object] = {}
    diagnostics: list[str] = []
    current_section: str | None = None
    current_profile: str | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        uncommented = raw_line.split("#", 1)[0].rstrip()
        if not uncommented.strip():
            continue

        indent = len(uncommented) - len(uncommented.lstrip(" "))
        stripped = uncommented.strip()
        if indent == 0:
            current_profile = None
            if stripped.endswith(":") and ":" not in stripped[:-1]:
                current_section = stripped[:-1].strip()
                if current_section == "profiles":
                    parsed.setdefault("profiles", {})
                continue
            if ":" not in stripped:
                diagnostics.append(f"Ignored malformed line {line_number}: {raw_line.strip()}")
                current_section = None
                continue
            key, value = stripped.split(":", 1)
            parsed[key.strip()] = parse_scalar(value)
            current_section = None
            continue

        if current_section == "profiles":
            profiles = parsed.setdefault("profiles", {})
            if not isinstance(profiles, dict):
                diagnostics.append("profiles must be a mapping")
                continue
            if indent == 2 and stripped.endswith(":") and ":" not in stripped[:-1]:
                current_profile = stripped[:-1].strip()
                profiles.setdefault(current_profile, {})
                continue
            if indent == 4 and current_profile and ":" in stripped:
                key, value = stripped.split(":", 1)
                profile = profiles[current_profile]
                if isinstance(profile, dict):
                    profile[key.strip()] = parse_scalar(value)
                continue

        diagnostics.append(f"Ignored unsupported line {line_number}: {raw_line.strip()}")

    return parsed, diagnostics


def normalize_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "on"}:
            return True
        if lowered in {"false", "no", "0", "off"}:
            return False
    return default


def normalize_labels(value, fallback: list[str], diagnostics: list[str]) -> list[str]:
    labels = value
    if isinstance(labels, str):
        labels = [item.strip() for item in labels.split(",") if item.strip()]
    if not isinstance(labels, list) or not labels:
        diagnostics.append(
            "self-hosted labels were empty or invalid, falling back to [self-hosted]."
        )
        return fallback
    return [str(label) for label in labels]


def _normalize_resources(profile: dict[str, object], diagnostics: list[str]) -> dict[str, str]:
    build_jobs = str(profile.get("build_jobs", "auto")).strip().lower()
    if build_jobs != "auto" and (not build_jobs.isdigit() or int(build_jobs) < 1):
        diagnostics.append(f"Invalid build_jobs '{build_jobs}', falling back to auto.")
        build_jobs = "auto"
    return {
        "build_jobs": build_jobs,
        "ccache_max_size": str(profile.get("ccache_max_size", "20G")).strip() or "20G",
        "isis_major": str(profile.get("isis_major", "9")).strip() or "9",
        "python_abi": str(profile.get("python_abi", "cp312")).strip() or "cp312",
    }


def resolve_config(config_path: Path, profile_override: str = "") -> RunnerResolution:
    if not config_path.exists():
        config: dict[str, object] = {**DEFAULTS, "profiles": DEFAULT_PROFILES.copy()}
        diagnostics = [
            f"Configuration file not found: {config_path}",
            "Falling back to defaults (self-hosted-http profile).",
        ]
    else:
        parsed, diagnostics = parse_config_file(config_path)
        config = {**DEFAULTS, **parsed}

    requested_profile = profile_override.strip()
    profiles = config.get("profiles")
    fallback_conda_prefix = str(
        config.get("fallback_conda_prefix", DEFAULTS["fallback_conda_prefix"])
    ).strip() or DEFAULTS["fallback_conda_prefix"]

    if isinstance(profiles, dict) and profiles:
        merged_profiles = {name: values.copy() for name, values in DEFAULT_PROFILES.items()}
        for profile_name, profile_values in profiles.items():
            if isinstance(profile_values, dict):
                merged = merged_profiles.get(str(profile_name), {}).copy()
                merged.update(profile_values)
                merged_profiles[str(profile_name)] = merged

        active_profile = (
            requested_profile
            or str(config.get("active_profile", DEFAULTS["active_profile"])).strip()
            or DEFAULTS["active_profile"]
        )
        if requested_profile:
            diagnostics.append(f"Applied workflow input profile override: {requested_profile}")
        if active_profile not in merged_profiles:
            source = "profile override" if requested_profile else "active_profile"
            diagnostics.append(
                f"Unknown {source} '{active_profile}', falling back to self-hosted-http."
            )
            active_profile = DEFAULTS["active_profile"]
        selected_profile = merged_profiles[active_profile]
        mode = str(selected_profile.get("mode", "self-hosted")).strip().lower()
        if mode not in {"self-hosted", "github-hosted"}:
            diagnostics.append(
                f"Unsupported mode '{mode}' in profile '{active_profile}', falling back to self-hosted."
            )
            mode = "self-hosted"

        if mode == "self-hosted":
            runs_on_value = normalize_labels(
                selected_profile.get(
                    "labels",
                    selected_profile.get("self_hosted_labels", LEGACY_DEFAULTS["self_hosted_labels"]),
                ),
                LEGACY_DEFAULTS["self_hosted_labels"],
                diagnostics,
            )
            checkout_transport = str(
                selected_profile.get(
                    "checkout_transport", LEGACY_DEFAULTS["self_hosted_checkout_transport"]
                )
            ).strip().lower()
            environment_strategy = str(
                selected_profile.get(
                    "environment_strategy",
                    LEGACY_DEFAULTS["self_hosted_environment_strategy"],
                )
            ).strip().lower()
        else:
            runs_on_value = str(
                selected_profile.get(
                    "github_hosted_runner",
                    selected_profile.get("runner", LEGACY_DEFAULTS["github_hosted_runner"]),
                )
            ).strip() or LEGACY_DEFAULTS["github_hosted_runner"]
            checkout_transport = str(
                selected_profile.get(
                    "checkout_transport", LEGACY_DEFAULTS["github_hosted_checkout_transport"]
                )
            ).strip().lower()
            environment_strategy = str(
                selected_profile.get(
                    "environment_strategy",
                    LEGACY_DEFAULTS["github_hosted_environment_strategy"],
                )
            ).strip().lower()

        runner_profile = active_profile
        network_profile = str(
            selected_profile.get(
                "network_profile", "plain-http" if mode == "self-hosted" else "github-hosted"
            )
        ).strip() or ("plain-http" if mode == "self-hosted" else "github-hosted")
        use_watt = "true" if normalize_bool(
            selected_profile.get("use_watt", network_profile == "watt-hosts")
        ) else "false"
        resources = _normalize_resources(selected_profile, diagnostics)
        fallback_conda_prefix = str(
            selected_profile.get("fallback_conda_prefix", fallback_conda_prefix)
        ).strip() or fallback_conda_prefix
    else:
        mode = str(config.get("mode", LEGACY_DEFAULTS["mode"])).strip().lower()
        if mode not in {"self-hosted", "github-hosted"}:
            diagnostics.append(
                f"Unsupported legacy mode '{mode}', falling back to self-hosted."
            )
            mode = "self-hosted"
        if mode == "self-hosted":
            runs_on_value = normalize_labels(
                config.get("self_hosted_labels", LEGACY_DEFAULTS["self_hosted_labels"]),
                LEGACY_DEFAULTS["self_hosted_labels"],
                diagnostics,
            )
            checkout_transport = str(
                config.get(
                    "self_hosted_checkout_transport",
                    LEGACY_DEFAULTS["self_hosted_checkout_transport"],
                )
            ).strip().lower()
            environment_strategy = str(
                config.get(
                    "self_hosted_environment_strategy",
                    LEGACY_DEFAULTS["self_hosted_environment_strategy"],
                )
            ).strip().lower()
            network_profile = "ssh-fallback" if checkout_transport == "ssh" else "plain-http"
        else:
            runs_on_value = str(
                config.get("github_hosted_runner", LEGACY_DEFAULTS["github_hosted_runner"])
            ).strip() or LEGACY_DEFAULTS["github_hosted_runner"]
            checkout_transport = str(
                config.get(
                    "github_hosted_checkout_transport",
                    LEGACY_DEFAULTS["github_hosted_checkout_transport"],
                )
            ).strip().lower()
            environment_strategy = str(
                config.get(
                    "github_hosted_environment_strategy",
                    LEGACY_DEFAULTS["github_hosted_environment_strategy"],
                )
            ).strip().lower()
            network_profile = "github-hosted"
        runner_profile = "legacy-default"
        use_watt = "false"
        resources = _normalize_resources(config, diagnostics)

    outputs = {
        "runner_profile": runner_profile,
        "runner_mode": mode,
        "runs_on_json": json.dumps(runs_on_value),
        "use_ssh_checkout": "true" if checkout_transport == "ssh" else "false",
        "checkout_transport": checkout_transport,
        "environment_strategy": environment_strategy,
        "needs_dynamic_conda_setup": "true" if environment_strategy == "micromamba" else "false",
        "fallback_conda_prefix": fallback_conda_prefix,
        "network_profile": network_profile,
        "use_watt": use_watt,
        **resources,
    }
    return RunnerResolution(outputs, diagnostics)


def write_github_files(
    result: RunnerResolution, output_path: Path, summary_path: Path
) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in result.outputs.items():
            handle.write(f"{key}={value}\n")

    with summary_path.open("a", encoding="utf-8") as summary:
        summary.write("## Resolved workflow runner configuration\n\n")
        for key, value in result.outputs.items():
            summary.write(f"- {key}: `{value}`\n")
        if result.diagnostics:
            summary.write("\n### Diagnostics\n")
            for item in result.diagnostics:
                summary.write(f"- {item}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", required=True, type=Path)
    parser.add_argument("--profile-override", default="")
    parser.add_argument("--github-output", required=True, type=Path)
    parser.add_argument("--github-step-summary", required=True, type=Path)
    args = parser.parse_args(argv)

    result = resolve_config(args.config_path, args.profile_override)
    write_github_files(result, args.github_output, args.github_step_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
