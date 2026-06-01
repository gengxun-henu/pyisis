# Adaptive Routing ControlNet Construction Design

## Goal

Build ControlNet construction flows that can select image matching methods through the existing adaptive routing system while preserving current default behavior.

Adaptive routing remains opt-in. Existing non-adaptive ORI and DOM ControlNet paths must keep working unless users explicitly enable adaptive routing through CLI flags or configuration.

## Scope

This design covers both:

- ORI-to-ControlNet flow: original cube pair matching produces original-image key files and writes a ControlNet.
- DOM-to-ControlNet flow: DOM image pair matching produces DOM key files, converts them back to original-image coordinates, then writes a ControlNet.

Existing `from-dom` and `from-dom-batch` behavior that consumes precomputed DOM key files stays compatible. The new DOM end-to-end path adds matching inside the ControlNet pipeline; it does not remove the precomputed-key workflow.

## Recommended Approach

Use a thin ControlNet orchestration layer.

The ControlNet side passes adaptive routing parameters into existing image matching APIs, consumes their key files and summaries, and writes route audit metadata into pair and batch summaries. The actual matcher selection, cascade execution, fallback ordering, deep preset resolution, and post-match quality gates remain in `examples/image_match/`.

This avoids duplicating routing logic in `examples/controlnet_construct/` and keeps tests focused on integration boundaries.

## Architecture

### ControlNet orchestration

Add or extend helper functions in `examples/controlnet_construct/controlnet_stereopair.py` that normalize matching output creation for ControlNet construction:

- ORI path calls `match_ori_pair_to_key_files()`.
- DOM path calls `match_dom_pair_to_key_files()`, then runs the existing DOM-to-original key conversion before ControlNet writing.
- Both paths pass `enable_adaptive_routing`, `adaptive_routing_profile`, adaptive deep preset/config options, and matcher options without reinterpreting route decisions.

### Image matching ownership

`examples/image_match/` remains the owner of:

- route probes and feature diagnostics
- requested/effective matcher resolution
- initial and final matcher selection
- cascade/fallback step ordering
- deep matcher preset/config selection
- post-match quality gates

ControlNet code treats image matching summary data as the source of truth.

## CLI and API Behavior

Adaptive routing is default-off.

ORI ControlNet matching keeps the existing `from-ori-match` behavior and exposes adaptive routing options there. DOM end-to-end matching should add an explicit `from-dom-match` entry point that accepts the DOM image pair, original cube pair, output key/controlnet paths, and the same adaptive routing options. Existing `from-dom` and `from-dom-batch` commands remain the precomputed DOM-key workflows.

User-facing options should stay consistent with the current naming style:

- `--adaptive-routing`
- `--adaptive-routing-profile`
- `--adaptive-routing-deep-preset`
- `--deep-match-config-path`
- existing matcher/matcher option flags

## Metadata and Audit Trail

Each pair summary should include:

- requested and effective matcher
- adaptive routing profile
- selected initial matcher
- selected final matcher
- fallback/cascade steps
- post-match quality gate result
- deep preset and resolved deep config path
- match count
- generated key file paths
- generated ControlNet path

Batch summaries should aggregate this per-pair metadata so users can audit why a stereo pair used LightGlue, LoFTR, FLANN, BF, or a fallback.

## Error Handling

Do not emit success-shaped outputs after matching failure.

If ORI key generation fails, the flow stops before ControlNet writing. If DOM key generation fails, the flow stops before DOM-to-original coordinate conversion. If adaptive routing exhausts all matchers, the exception or failure summary must surface through the CLI and batch result.

Fallback and cascade behavior should remain delegated to `examples/image_match/`.

## Testing Plan

Use focused unit tests before broader validation:

- ORI path forwards adaptive routing options into `match_ori_pair_to_key_files()`.
- DOM end-to-end path calls `match_dom_pair_to_key_files()` and then existing DOM coordinate conversion.
- Pair and batch summaries include routing audit metadata.
- Default-off adaptive routing preserves old behavior.
- Matching failure prevents downstream conversion and ControlNet success writes.

Environment-heavy ISIS data paths should remain smoke or integration coverage, not required for the default fast unit tests.

## Out of Scope

- Rewriting the adaptive routing algorithm.
- Making adaptive routing the default matcher-selection behavior.
- Removing precomputed DOM key workflows.
- Adding new deep matcher backends.
