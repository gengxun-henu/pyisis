# Progress Maintenance Reference

This reference explains how to keep pybind workflow status aligned with the repository tracking files.

## Primary progress files

Always consider these files during pybind work:

- `pybind_progress_log.md`
- `todo_pybind11.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`
- the relevant `class_bind_methods_details/*_methods.csv`

## What to update

### `pybind_progress_log.md`

Update this file when:

- a new class binding was added
- a meaningful set of missing methods was completed
- new blockers or uncertainties were identified
- validation status changed in a way future work should know about

Recommended note content:

- date
- class or module touched
- binding/test files changed
- validation summary
- blockers or follow-up items

### `todo_pybind11.csv`

Update this file when:

- the pending binding class/function inventory changes
- top-level tracking rows or module/class completion context stored there changes
- a workflow depends on the CSV as an inventory source and the source-of-truth row would otherwise become stale

### Methods inventory CSVs

If the task includes method coverage synchronization:

- inspect the class detail CSV
- reflect newly converted methods accurately
- avoid marking methods complete unless the binding is actually exposed

## Recommended record style

Keep notes concise and operational. Future work should be able to answer:

- what changed
- what was validated
- what remains open
- whether remaining issues are code gaps or environment gaps

## Common mistakes

- finishing a binding task but not updating `pybind_progress_log.md`
- treating `todo_pybind11.csv` as a narrative progress log instead of an inventory/tracking table
- marking CSV status as complete before validating actual exposure
- omitting blockers, forcing future work to rediscover them
