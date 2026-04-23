"""Shared coordinate-basis annotations for DOM matching JSON sidecars.

Author: Geng Xun
Created: 2026-04-17
Updated: 2026-04-17  Geng Xun added reusable coordinate-basis metadata blocks, so JSON sidecars can declare 0-based offsets versus 1-based ISIS sample/line fields consistently.
"""

from __future__ import annotations

from copy import deepcopy


PAIR_PREPARATION_COORDINATE_FIELD_BASES = {
    "left.start_sample": "1-based ISIS sample coordinate in the left DOM image.",
    "left.start_line": "1-based ISIS line coordinate in the left DOM image.",
    "left.offset_sample": "0-based horizontal pixel offset relative to the left DOM array origin.",
    "left.offset_line": "0-based vertical pixel offset relative to the left DOM array origin.",
    "left.width": "Pixel count, not a coordinate index.",
    "left.height": "Pixel count, not a coordinate index.",
    "right.start_sample": "1-based ISIS sample coordinate in the right DOM image.",
    "right.start_line": "1-based ISIS line coordinate in the right DOM image.",
    "right.offset_sample": "0-based horizontal pixel offset relative to the right DOM array origin.",
    "right.offset_line": "0-based vertical pixel offset relative to the right DOM array origin.",
    "right.width": "Pixel count, not a coordinate index.",
    "right.height": "Pixel count, not a coordinate index.",
    "overlap_min_x": "Projected/map X coordinate, not a pixel index.",
    "overlap_max_x": "Projected/map X coordinate, not a pixel index.",
    "overlap_min_y": "Projected/map Y coordinate, not a pixel index.",
    "overlap_max_y": "Projected/map Y coordinate, not a pixel index.",
    "expanded_min_x": "Projected/map X coordinate after overlap expansion, not a pixel index.",
    "expanded_max_x": "Projected/map X coordinate after overlap expansion, not a pixel index.",
    "expanded_min_y": "Projected/map Y coordinate after overlap expansion, not a pixel index.",
    "expanded_max_y": "Projected/map Y coordinate after overlap expansion, not a pixel index.",
    "shared_width": "Pixel count in the matched shared window, not a coordinate index.",
    "shared_height": "Pixel count in the matched shared window, not a coordinate index.",
}


DOM2ORI_COORDINATE_FIELD_BASES = {
    "failures[].sample": "1-based ISIS sample coordinate read from the DOM-space .key file.",
    "failures[].line": "1-based ISIS line coordinate read from the DOM-space .key file.",
    "failures[].projected_sample": "1-based ISIS sample coordinate projected into the original image.",
    "failures[].projected_line": "1-based ISIS line coordinate projected into the original image.",
    "failures[].latitude": "Universal latitude in degrees, not a pixel index.",
    "failures[].longitude": "Universal longitude in degrees, not a pixel index.",
}


CONTROLNET_RESULT_COORDINATE_FIELD_BASES = {
    "match.preparation.left.start_sample": "1-based ISIS sample coordinate in the left DOM image.",
    "match.preparation.left.start_line": "1-based ISIS line coordinate in the left DOM image.",
    "match.preparation.left.offset_sample": "0-based horizontal pixel offset relative to the left DOM array origin.",
    "match.preparation.left.offset_line": "0-based vertical pixel offset relative to the left DOM array origin.",
    "match.preparation.right.start_sample": "1-based ISIS sample coordinate in the right DOM image.",
    "match.preparation.right.start_line": "1-based ISIS line coordinate in the right DOM image.",
    "match.preparation.right.offset_sample": "0-based horizontal pixel offset relative to the right DOM array origin.",
    "match.preparation.right.offset_line": "0-based vertical pixel offset relative to the right DOM array origin.",
    "left_conversion.failures[].sample": "1-based ISIS sample coordinate read from the left DOM-space .key file.",
    "left_conversion.failures[].line": "1-based ISIS line coordinate read from the left DOM-space .key file.",
    "left_conversion.failures[].projected_sample": "1-based ISIS sample coordinate projected into the left original image.",
    "left_conversion.failures[].projected_line": "1-based ISIS line coordinate projected into the left original image.",
    "right_conversion.failures[].sample": "1-based ISIS sample coordinate read from the right DOM-space .key file.",
    "right_conversion.failures[].line": "1-based ISIS line coordinate read from the right DOM-space .key file.",
    "right_conversion.failures[].projected_sample": "1-based ISIS sample coordinate projected into the right original image.",
    "right_conversion.failures[].projected_line": "1-based ISIS line coordinate projected into the right original image.",
    "controlnet.measures[].sample": "1-based ISIS sample coordinate stored in ControlMeasure objects.",
    "controlnet.measures[].line": "1-based ISIS line coordinate stored in ControlMeasure objects.",
}


def annotate_coordinate_payload(
    payload: dict[str, object],
    *,
    context: str,
    field_bases: dict[str, str],
) -> dict[str, object]:
    annotated = deepcopy(payload)
    annotated["coordinate_conventions"] = {
        "context": context,
        "field_bases": dict(field_bases),
        "documentation_hint": "0-based offsets, 1-based ISIS sample/line, and projected/map coordinates are intentionally distinguished here.",
    }
    return annotated