"""Print and validate the ControlNet construction parameter catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


if __package__ is None or __package__ == "":
    EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
    examples_root = str(EXAMPLES_ROOT)
    sys.path = [entry for entry in sys.path if entry != examples_root]
    sys.path.insert(0, examples_root)
    from controlnet_construct.parameter_catalog import (  # type: ignore[import-not-found]
        GROUP_BY_NAME,
        grouped_parameters_for_entrypoint,
        parameter_catalog_as_dict,
    )
    from controlnet_construct.parameter_validation import validate_parameters  # type: ignore[import-not-found]
else:
    from .parameter_catalog import GROUP_BY_NAME, grouped_parameters_for_entrypoint, parameter_catalog_as_dict
    from .parameter_validation import validate_parameters


def format_grouped_help(entrypoint: str) -> str:
    """Return grouped text help for catalog parameters supported by an entry point."""

    lines = [f"Parameter groups for {entrypoint}"]
    grouped = _grouped_parameters_or_error(entrypoint)
    for group_name, parameters in grouped.items():
        group = GROUP_BY_NAME[group_name]
        lines.extend(("", group.title, group.description))
        for parameter in parameters:
            display_name = parameter.cli_flag or parameter.name
            details = [parameter.help, f"name: {parameter.name}"]
            if parameter.allowed_values is not None:
                allowed_values = ", ".join(str(value) for value in parameter.allowed_values)
                details.append(f"allowed: {allowed_values}")
            if parameter.config_path:
                details.append(f"config: {parameter.config_path}")
            if parameter.default is not None:
                details.append(f"default: {parameter.default}")
            lines.append(f"  {display_name}: {'; '.join(details)}")
    return "\n".join(lines) + "\n"


def _grouped_parameters_or_error(entrypoint: str) -> dict[str, tuple[Any, ...]]:
    grouped = grouped_parameters_for_entrypoint(entrypoint)
    if not grouped:
        raise ValueError(f"unknown entrypoint: {entrypoint}")
    return grouped


def _load_payload(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--validate-json payload must be a JSON object")
    return payload


def _mapping_from_payload(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a JSON object when supplied")
    return value


def _print_messages(prefix: str, messages: tuple[Any, ...]) -> None:
    for message in messages:
        print(f"{prefix}: {message.field}: {message.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrypoint", default="run_pipeline_example")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--validate-json", metavar="PATH")
    parser.add_argument("--shell-assignments", action="store_true")
    args = parser.parse_args(argv)

    if args.validate_json is None:
        try:
            _grouped_parameters_or_error(args.entrypoint)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.format == "json":
            print(json.dumps(parameter_catalog_as_dict(entrypoint=args.entrypoint), indent=2, sort_keys=True))
        else:
            print(format_grouped_help(args.entrypoint), end="")
        return 0

    try:
        payload = _load_payload(args.validate_json)
        entrypoint = str(payload.get("entrypoint") or args.entrypoint)
        result = validate_parameters(
            entrypoint,
            cli_values=_mapping_from_payload(payload, "cli_values"),
            profile_values=_mapping_from_payload(payload, "profile_values"),
            config_values=_mapping_from_payload(payload, "config_values"),
            preset_values=_mapping_from_payload(payload, "preset_values"),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: validate-json: {exc}", file=sys.stderr)
        return 2

    _print_messages("warning", result.warnings)
    if result.errors:
        _print_messages("error", result.errors)
        return 2

    if args.shell_assignments:
        print(result.to_shell_assignments())
    else:
        print(
            json.dumps(
                {
                    "entrypoint": result.entrypoint,
                    "provenance": result.provenance,
                    "values": result.values,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
