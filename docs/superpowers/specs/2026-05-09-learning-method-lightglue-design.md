# Learning-Based Matcher Integration Design (Minimal-Intrusion)

## 1. Problem and Goal

The current controlnet construction workflow is centered on classical matching methods (`bf` / `flann`) and already includes strong downstream stages (geometric checks, controlnet building, CPU RANSAC outlier rejection).  

The goal is to integrate mainstream deep learning matchers with minimal code changes while preserving the existing workflow:

- Add support for `superglue`, `lightglue`, and `loftr`
- Keep existing pipeline shape and default behavior unchanged
- Reuse existing controlnet construction and CPU RANSAC stages
- Support both GPU and CPU execution with automatic same-method fallback from GPU to CPU

## 2. Scope

### In Scope

- Extend `matcher_method` accepted values to include `superglue`, `lightglue`, `loftr`
- Add deep matching adapter path in current tile matching flow
- Add method-specific frontends:
  - `superglue` / `lightglue`: SuperPoint feature extraction + matcher inference
  - `loftr`: detector-free end-to-end matching path
- Normalize outputs into existing match record structure
- Keep downstream controlnet + CPU RANSAC path unchanged
- Add focused unit/integration tests for dispatching, fallback, and compatibility

### Out of Scope

- Refactoring the overall controlnet orchestration architecture
- Replacing existing `bf` / `flann` default logic
- Adding unrelated pipeline changes outside matching integration
- Committing large model weights into repository

## 3. Recommended Approach (Chosen)

Use a **minimal-intrusion adapter approach** centered on the existing matcher dispatch point.

### Why this approach

- Lowest change surface in hot files
- Preserves current pipeline contracts
- Adds deep methods without broad restructuring
- Keeps behavior predictable and rollback simple

### Alternative approaches considered

1. Plugin registry for matchers (better long-term extensibility, larger initial change)
2. Parallel deep/classic dual-path branch (good isolation, higher maintenance complexity)

## 4. Architecture

### 4.1 Entry and Configuration

- Keep `matcher_method` as the single external selector
- Extend allowed values:
  - `bf`
  - `flann`
  - `superglue`
  - `lightglue`
  - `loftr`
- `image_match.py` changes are limited to validation/help text and pass-through

### 4.2 New Components

1. `deep_frontends.py`
   - `SuperPointFrontend` (keypoints + descriptors)
   - `LoFTRFrontend` preprocessing support
   - Device selection helpers (GPU/CPU)

2. `deep_matchers.py`
   - `SuperGlueMatcher`
   - `LightGlueMatcher`
   - Unified inference-facing interfaces

3. `deep_adapter.py`
   - `DeepMatcherAdapter.match_pair(...)`
   - Method routing (`superglue` / `lightglue` / `loftr`)
   - Output normalization to existing match record format

### 4.3 Existing Files with Minimal Edits

- `tile_matching.py`: add one dispatch integration point to call deep adapter when selected
- `image_match.py`: extend matcher method validation and CLI/config docs

## 5. Data Flow

For each tile pair:

1. Read/preprocess tiles (existing behavior retained)
2. Route by `matcher_method`:
   - `superglue` / `lightglue`: SuperPoint extraction -> matcher inference
   - `loftr`: direct detector-free inference path
   - `bf` / `flann`: unchanged existing path
3. Convert deep outputs to existing match record format
4. Reuse existing downstream stages:
   - quality filters
   - geometric checks
   - controlnet construction
   - CPU RANSAC outlier rejection

## 6. Error Handling and Fallback Policy

- Reject unsupported matcher names with explicit error
- Missing dependency/weights: explicit error with actionable message
- GPU unavailable or GPU inference failure: automatically fallback to CPU for the same method
- No silent cross-method fallback (for example, `loftr` does not silently become `bf`)
- Keep tile-level handling aligned with current pipeline behavior (skip/fail according to existing policy)

## 7. Testing Strategy

### 7.1 Unit Tests

- Matcher method validation includes new values
- Dispatch tests verify method-to-adapter routing
- GPU-unavailable tests verify same-method CPU fallback
- Output schema tests verify compatibility with current downstream consumers

### 7.2 Lightweight Integration Tests

- Run small controlnet path using new methods where dependencies are present
- Confirm CPU RANSAC and downstream outputs remain compatible
- Verify existing `bf` / `flann` behavior remains unchanged

### 7.3 Environment Layering

- In environments without deep deps:
  - run mock/dispatch validation tests
- In environments with deep deps:
  - run real inference smoke-level tests

## 8. Dependency and Model Policy

- Prefer existing Python ecosystem packages and public model weights
- Do not vendor large model files into this repository
- Keep installation/use instructions explicit in docs where needed

## 9. Compatibility and Rollout

- Default behavior remains unchanged unless `matcher_method` is set to deep methods
- Deep method integration is additive
- Rollout risk is controlled through method gating and focused test coverage

## 10. Success Criteria

- New matcher methods (`superglue`, `lightglue`, `loftr`) run inside existing controlnet flow
- CPU RANSAC remains the outlier-rejection stage
- GPU-to-CPU same-method fallback works reliably
- No regression in existing `bf` / `flann` default behavior

