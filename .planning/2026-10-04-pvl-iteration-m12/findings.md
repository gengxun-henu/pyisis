# Findings: PVL Python Collection Iteration (M12)

## Verified Facts

- `src/base/bind_base_pvl.cpp` already binds `PvlKeyword`, `PvlContainer`, `PvlGroup`, `PvlObject`, and `Pvl`.
- Existing bindings expose `size()`/`keywords()`/`groups()`/`objects()` and indexed accessors, so iteration can be added without new ISIS API dependencies.
- ISIS 9 and ISIS 10 headers both provide indexed accessors and stable counts; Qt iterator types should remain inside C++.
- `tests/unitTest/pvl_unit_test.py` is the focused PVL regression module.

## Evidence-based Inference

- Materializing Python lists from indexed access is the least ABI-sensitive implementation and avoids dangling Qt iterator wrappers after parent mutation.

## Unresolved Items

- None before implementation.

## Decisions

- Expose values, keywords, groups, and nested objects through `__iter__` in their existing order.
- Return copies for `PvlKeyword` and `PvlContainer` iteration; return parent-owned references for `PvlObject` groups/objects with `reference_internal` where needed.
