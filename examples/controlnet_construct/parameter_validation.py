"""Catalog-driven validation for ControlNet construction parameters."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import shlex
from typing import Any, Iterable


try:
    from .deep_match_config import DEEP_MATCHER_METHODS, load_deep_match_config
    from .parameter_catalog import PARAMETER_BY_NAME, parameters_for_entrypoint
except ImportError:
    from deep_match_config import DEEP_MATCHER_METHODS, load_deep_match_config
    from parameter_catalog import PARAMETER_BY_NAME, parameters_for_entrypoint


_SOURCE_ORDER = ("config", "preset", "cli")
_BOOL_TRUE_STRINGS = {"1", "true", "yes", "on"}
_BOOL_FALSE_STRINGS = {"0", "false", "no", "off"}
_REDUCED_PREVIEW_FIELDS = (
    "visualization_target_long_edge",
    "max_preview_pixels",
    "preview_crop_margin_pixels",
    "preview_cache_dir",
    "preview_cache_source",
    "preview_force_regenerate",
    "preview_level",
)


@dataclass(frozen=True, slots=True)
class ValidationMessage:
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ParameterValidationResult:
    entrypoint: str
    values: dict[str, Any]
    provenance: dict[str, str]
    warnings: tuple[ValidationMessage, ...]
    errors: tuple[ValidationMessage, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def warning_text(self) -> str:
        return "\n".join(_format_message(message) for message in self.warnings)

    def error_text(self) -> str:
        return "\n".join(_format_message(message) for message in self.errors)

    def to_shell_assignments(self, names: Iterable[str] | None = None) -> str:
        selected_names = list(names) if names is not None else list(self.values)
        assignments = []
        for name in selected_names:
            value = self.values.get(name)
            if isinstance(value, bool):
                rendered = "1" if value else "0"
            elif value is None:
                rendered = ""
            else:
                rendered = str(value)
            assignments.append(f"{name.upper()}={shlex.quote(rendered)}")
        return "\n".join(assignments)


def validate_parameters(
    entrypoint: str,
    *,
    cli_values: dict[str, Any] | None = None,
    preset_values: dict[str, Any] | None = None,
    config_values: dict[str, Any] | None = None,
) -> ParameterValidationResult:
    """Merge and validate parameters for a ControlNet entry point."""

    provided_by_source = {
        "config": dict(config_values or {}),
        "preset": dict(preset_values or {}),
        "cli": dict(cli_values or {}),
    }
    specs = tuple(PARAMETER_BY_NAME[spec.name] for spec in parameters_for_entrypoint(entrypoint))
    spec_by_name = {spec.name: spec for spec in specs}
    values: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    warnings: list[ValidationMessage] = []
    errors: list[ValidationMessage] = []

    for spec in specs:
        value = spec.default
        source = "absent" if _is_absent(spec.default) else "default"
        for candidate_source in _SOURCE_ORDER:
            candidate_value = provided_by_source[candidate_source].get(spec.name)
            if not _is_absent(candidate_value):
                value = candidate_value
                source = candidate_source

        value = _validate_and_normalize_value(spec, value, errors)
        values[spec.name] = value
        provenance[spec.name] = source

    _validate_cli_conflicts(provided_by_source["cli"], errors)
    _validate_deep_match_config(values, spec_by_name, errors)
    _validate_cross_field_rules(entrypoint, values, errors)
    _collect_inactive_parameter_warnings(values, provenance, spec_by_name, warnings)

    if values.get("strict_parameter_validation") is True and warnings:
        for warning in warnings:
            errors.append(
                ValidationMessage(
                    warning.field,
                    f"strict parameter validation promoted warning to error: {warning.message}",
                )
            )

    return ParameterValidationResult(
        entrypoint=entrypoint,
        values=values,
        provenance=provenance,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _format_message(message: ValidationMessage) -> str:
    if message.field:
        return f"{message.field}: {message.message}"
    return message.message


def _is_absent(value: Any) -> bool:
    return value is None or value == ""


def _is_explicit(mapping: dict[str, Any], name: str) -> bool:
    return name in mapping and not _is_absent(mapping.get(name))


def _is_explicit_value(provenance: dict[str, str], name: str) -> bool:
    return provenance.get(name) in _SOURCE_ORDER


def _normalize_choice(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _validate_and_normalize_value(spec: Any, value: Any, errors: list[ValidationMessage]) -> Any:
    if _is_absent(value):
        return None

    if spec.allowed_values is not None:
        normalized_allowed = {_normalize_choice(allowed): allowed for allowed in spec.allowed_values}
        normalized_value = _normalize_choice(value)
        if normalized_value not in normalized_allowed:
            allowed_display = ", ".join(str(allowed) for allowed in spec.allowed_values)
            errors.append(
                ValidationMessage(
                    spec.name,
                    f"unsupported choice {value!r}; expected one of: {allowed_display}",
                )
            )
            return value
        return normalized_allowed[normalized_value]

    if spec.value_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            if normalized_value in _BOOL_TRUE_STRINGS:
                return True
            if normalized_value in _BOOL_FALSE_STRINGS:
                return False
        errors.append(ValidationMessage(spec.name, f"must be a boolean value; got {value!r}"))
        return value

    if spec.value_type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(ValidationMessage(spec.name, f"must be a finite integer; got {value!r}"))
            return value
        return _validate_numeric_range(spec, value, errors)

    if spec.value_type == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(ValidationMessage(spec.name, f"must be a finite number; got {value!r}"))
            return value
        return _validate_numeric_range(spec, value, errors)

    return value


def _validate_numeric_range(spec: Any, value: int | float, errors: list[ValidationMessage]) -> int | float:
    if not math.isfinite(value):
        errors.append(ValidationMessage(spec.name, f"must be finite; got {value!r}"))
        return value
    if spec.min_value is not None and value < spec.min_value:
        errors.append(ValidationMessage(spec.name, f"must be >= {spec.min_value}; got {value!r}"))
    if spec.max_value is not None and value > spec.max_value:
        errors.append(ValidationMessage(spec.name, f"must be <= {spec.max_value}; got {value!r}"))
    return value


def _validate_cli_conflicts(cli_values: dict[str, Any], errors: list[ValidationMessage]) -> None:
    if _is_explicit(cli_values, "match_preset_path") and _is_explicit(cli_values, "matcher_method"):
        errors.append(
            ValidationMessage(
                "match_preset_path",
                "explicit CLI match_preset_path cannot be combined with explicit CLI matcher_method",
            )
        )
    if _is_explicit(cli_values, "match_preset_path") and _is_explicit(cli_values, "deep_match_config_path"):
        errors.append(
            ValidationMessage(
                "match_preset_path",
                "explicit CLI match_preset_path cannot be combined with explicit CLI deep_match_config_path",
            )
        )


def _validate_deep_match_config(values: dict[str, Any], spec_by_name: dict[str, Any], errors: list[ValidationMessage]) -> None:
    if "deep_match_config_path" not in spec_by_name:
        return

    matcher_method = values.get("matcher_method")
    deep_match_config_path = values.get("deep_match_config_path")
    if _is_absent(deep_match_config_path):
        if _normalize_choice(matcher_method or "") in set(DEEP_MATCHER_METHODS):
            errors.append(
                ValidationMessage(
                    "deep_match_config_path",
                    f"deep matcher {matcher_method!r} requires deep_match_config_path",
                )
            )
        return

    resolved_path = Path(str(deep_match_config_path))
    if not resolved_path.exists():
        errors.append(
            ValidationMessage(
                "deep_match_config_path",
                f"deep_match_config_path does not exist: {resolved_path}",
            )
        )
        return
    try:
        load_deep_match_config(resolved_path)
    except ValueError as exc:
        errors.append(ValidationMessage("deep_match_config_path", str(exc)))


def _validate_cross_field_rules(entrypoint: str, values: dict[str, Any], errors: list[ValidationMessage]) -> None:
    if entrypoint == "run_pipeline_example" and values.get("deep_match_mode") == "import":
        if _is_absent(values.get("deep_match_manifest_dir")):
            errors.append(
                ValidationMessage(
                    "deep_match_manifest_dir",
                    "deep_match_mode import requires deep_match_manifest_dir for run_pipeline_example",
                )
            )

    if entrypoint == "image_match" and values.get("deep_match_mode") == "import":
        if _is_absent(values.get("deep_match_manifest")):
            errors.append(
                ValidationMessage(
                    "deep_match_manifest",
                    "deep_match_mode import requires deep_match_manifest for image_match",
                )
            )

    gpu_min_batch_size = values.get("gpu_min_batch_size")
    gpu_max_batch_size = values.get("gpu_max_batch_size")
    if isinstance(gpu_min_batch_size, int) and isinstance(gpu_max_batch_size, int):
        if not isinstance(gpu_min_batch_size, bool) and not isinstance(gpu_max_batch_size, bool):
            if gpu_min_batch_size > gpu_max_batch_size:
                errors.append(
                    ValidationMessage(
                        "gpu_min_batch_size",
                        "gpu_min_batch_size must be less than or equal to gpu_max_batch_size",
                    )
                )

    left_low_resolution_dom = values.get("left_low_resolution_dom")
    right_low_resolution_dom = values.get("right_low_resolution_dom")
    if _is_absent(left_low_resolution_dom) != _is_absent(right_low_resolution_dom):
        errors.append(
            ValidationMessage(
                "left_low_resolution_dom",
                "left_low_resolution_dom and right_low_resolution_dom must be provided together",
            )
        )

    if values.get("skip_final_merge") is True and values.get("post_merge_control_measure") is True:
        errors.append(
            ValidationMessage(
                "post_merge_control_measure",
                "post_merge_control_measure cannot be used with skip_final_merge",
            )
        )


def _collect_inactive_parameter_warnings(
    values: dict[str, Any],
    provenance: dict[str, str],
    spec_by_name: dict[str, Any],
    warnings: list[ValidationMessage],
) -> None:
    if values.get("enable_low_resolution_offset_estimation") is False:
        for name in sorted(spec_by_name):
            if name.startswith("low_resolution_") or name in ("left_low_resolution_dom", "right_low_resolution_dom"):
                if _is_explicit_value(provenance, name):
                    warnings.append(
                        ValidationMessage(
                            name,
                            f"{name} was explicitly set while enable_low_resolution_offset_estimation is false",
                        )
                    )

    if values.get("use_gpu") is False:
        for name in sorted(spec_by_name):
            if name.startswith("gpu_") and _is_explicit_value(provenance, name):
                warnings.append(ValidationMessage(name, f"{name} was explicitly set while use_gpu is false"))

    if values.get("use_parallel_cpu") is False and _is_explicit_value(provenance, "num_worker_parallel_cpu"):
        warnings.append(
            ValidationMessage(
                "num_worker_parallel_cpu",
                "num_worker_parallel_cpu was explicitly set while use_parallel_cpu is false",
            )
        )

    if values.get("deep_match_mode") == "direct":
        for name in (
            "deep_match_temp_root_dir",
            "deep_match_manifest_dir",
            "deep_match_manifest",
            "deep_match_manifest_summary",
        ):
            if name in spec_by_name and _is_explicit_value(provenance, name):
                warnings.append(
                    ValidationMessage(
                        name,
                        f"{name} was explicitly set while deep_match_mode is direct",
                    )
                )

    if values.get("visualization_mode") == "full":
        for name in _REDUCED_PREVIEW_FIELDS:
            if name in spec_by_name and _is_explicit_value(provenance, name):
                warnings.append(
                    ValidationMessage(
                        name,
                        f"{name} was explicitly set while visualization_mode is full",
                    )
                )

    if values.get("post_merge_control_measure") in (False, None, ""):
        for name in ("post_merge_output", "post_merge_decimals"):
            if name in spec_by_name and _is_explicit_value(provenance, name):
                warnings.append(
                    ValidationMessage(
                        name,
                        f"{name} was explicitly set while post_merge_control_measure is false",
                    )
                )
