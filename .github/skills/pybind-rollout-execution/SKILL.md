---
name: pybind-rollout-execution
description: 'Run a rolling pybind binding campaign for unfinished ISIS classes in this repository. Use when the user asks to 持续推进未完成类绑定, 一次选 5 个或 10 个类排队处理, 一个类一个类做 pybind + focused unit test + smoke test, 编译失败时持续分析修复, 或在 10 次失败后做台账止损标记.'
argument-hint: '[batch, phase, or queue] e.g. first 5 base classes, Stereo batch, stage-2 utility queue'
user-invocable: true
---

# Pybind Rollout Execution

Use this skill when the task is not just “bind one class”, but to **continuously push a queue of unfinished classes forward** using a controlled campaign workflow.

This skill is a **companion workflow** to `.github/skills/isis-pybind/SKILL.md`.

- Use `isis-pybind` for the detailed mechanics of a normal pybind task.
- Use `pybind-rollout-execution` when you need queue management, per-class closure, retry limits, and blocker bookkeeping across a batch.

All repository paths below are relative to the repository root unless noted otherwise.

## Primary Sources and Ordering References

Before acting, use these inputs with the following priority:

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. the relevant class detail CSV under `class_bind_methods_details/`
4. `pybind_progress_log.md`
5. `reference/notes/base_inventory_rollout_order_2026-04-08.md`

Treat the CSV ledgers as the primary source of truth for what is still pending.

Use the rollout-order note only to constrain:

- which phase should be worked on first
- ordering within a phase when several candidates are still pending

Do not treat the rollout-order note as the only source for identifying unfinished classes.

This skill does **not** replace the repository-wide rules in:

- `.github/copilot-instructions.md`
- `.github/instructions/pybind-testing.instructions.md`
- `.github/instructions/pybind-upstream-source-reading.instructions.md`
- `.github/skills/isis-pybind/SKILL.md`

Follow those in addition to this skill.

## When to Use

Use this skill when the user wants one or more of the following:

- keep binding unfinished classes continuously
- choose a batch of 5 or 10 classes, but execute them one at a time
- require each class to finish a full closure before moving to the next
- automatically analyze compile, link, import, or test failures and retry
- stop after 10 failed repair cycles for a class and record the blocker in ledgers
- maintain a repeatable “campaign mode” across many ISIS classes

Do **not** use this skill when the request is only:

- a one-off method addition
- a small bug fix in an already active binding
- inventory-only cleanup without actual binding work
- general C++ maintenance unrelated to Python exposure

## Core Model

### 1. Queue-based planning, single-class execution

A rollout batch may contain 5 or 10 candidate classes.

However, execution must remain **strictly one class at a time**:

1. choose the active queue
2. work on the first class only
3. finish the full closure for that class
4. then move to the next class in the queue

Do not partially bind several queued classes in parallel.

### 2. Default queue size

Prefer:

- queue size: **5 classes**
- execution unit: **1 class**

Use 10 only when the classes are clearly small, similar, and low risk.

### 3. Candidate classes come from ledgers; order comes from the rollout note

Determine the active candidate set from:

- `todo_pybind11.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`

Then use:

- `reference/notes/base_inventory_rollout_order_2026-04-08.md`

to constrain phase and ordering.

Do not improvise a new global order unless the user explicitly asks or the note is updated.

## Standard Campaign Procedure

### 1. Select the active queue

- Start from `todo_pybind11.csv` and `class_bind_methods_details/methods_inventory_summary.csv`.
- Filter to unfinished, still-actionable classes.
- Use the target class detail CSVs when needed to confirm real open work.
- Then apply `reference/notes/base_inventory_rollout_order_2026-04-08.md` as a phase/order constraint.
- Pick the next 5 or 10 unfinished classes from the current phase.
- Record or restate the queue clearly.
- Mark only one class as the current execution target.

If no explicit batch size is given, default to 5.

### 2. Scope the current class

Before editing code for the current class, inspect:

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. the target `*_methods.csv`
4. `pybind_progress_log.md`
5. similar bindings in `src/`
6. similar tests in `tests/unitTest/`

Then read the upstream ISIS material in the normal repository order:

1. upstream `.h`
2. upstream `.cpp`
3. upstream `unitTest.cpp` or usage examples

Do not bind from header signatures alone when behavior depends on implementation.

Before compiling the current class, explicitly audit these recurring binding hazards:

- Audit member-function qualifiers before wrapping operators or arithmetic helpers.
	- Example: `Quaternion::operator*(const double &)` is **not** `const` in upstream ISIS.
	- Do not bind it with a lambda that takes `const Isis::Quaternion &` and then calls `a * scalar` directly.
	- Prefer copying into a mutable local wrapper/object first, or exposing an equivalent const-safe lambda built from a mutable copy.
- Do not bind upstream `protected` members directly with pybind lambdas.
	- Example: `PvlFormat::addQuotes(...)`, `PvlFormat::isSingleUnit(...)`, `PvlTranslationTable::hasInputDefault(...)`, `IsAuto(...)`, `IsOptional(...)`, `OutputName(...)`, and `OutputPosition(...)` are protected helpers, not public API.
	- If Python still needs those semantics, expose them through a local helper subclass or wrapper that safely forwards the protected call, or reimplement a stable public-facing wrapper when the behavior is simple and well verified.
	- Before adding such wrappers, verify the behavior against `reference/upstream_isis/...` instead of assuming a declaration is callable from pybind.
- For `AutoReg`-family constructors and factory tests, match upstream PVL shape exactly.
	- `AutoReg(Pvl &)` first calls `pvl.findObject("AutoRegistration")`, then parses nested `Algorithm`, `PatternChip`, and `SearchChip` groups.
	- Do **not** build a flat `PvlGroup("AutoRegistration")` and pass it as the whole config; that will fail with `Unable to find PVL object [AutoRegistration]`.
	- Prefer copying the structure from `reference/upstream_isis/src/base/objs/MinimumDifference/unitTest.cpp` or `reference/upstream_isis/src/base/objs/AutoReg/unitTest.cpp` when adding `MaximumCorrelation`, `MinimumDifference`, `Gruen`, or factory regressions.

### 3. Complete the class closure

For each class, aim for this closure sequence:

1. implement or extend the pybind binding
2. update `python/isis_pybind/__init__.py` if needed
3. add or update the smallest focused unit test
4. build the project with the correct Python interpreter
5. run the smallest focused unit test first
6. run any related grouped tests if justified
7. run `tests/smoke_import.py`
8. update ledgers and progress notes

A class is not considered complete until the code, test, smoke, and ledgers are all synchronized.

### 4. Validate in the correct environment

Prefer the `asp360_new` Python interpreter and matching extension ABI.

Do not report Python-version mismatches or missing external runtime data as binding regressions without confirming the real cause first.

## Failure Handling

### 1. Classify the failure first

Always identify the failure layer before attempting a fix:

1. compile failure
2. link failure
3. import-time undefined symbol
4. focused unit-test failure
5. smoke-test failure
6. environment/runtime-data issue

This prevents wasting retries on the wrong problem.

### 2. One retry means one full repair cycle

Count one attempt only after this full loop:

1. analyze the cause
2. make a code or test fix
3. rebuild
4. rerun the focused test
5. rerun smoke if earlier steps pass

Do not inflate retry counts with partial or trivial non-validation edits.

### 3. Preferred repair patterns for the current class

After classifying the failure layer, prefer these established repair patterns:

- if a method is declared in headers but missing in the linked implementation, avoid binding the raw member-function pointer; consider a lambda wrapper using stable getters
- if the class is abstract or pure-virtual, expose the usable surface without forcing unsafe construction
- if Qt containers or ISIS-specific types are Python-hostile, adapt them to Python-friendly values
- if lifetimes are involved, inspect `keep_alive`, return policies, and temporary object hazards
- if runtime data is missing, treat it as environment-dependent and use stable skips or narrower smoke coverage where appropriate

## Stop-Loss Rule

If the same class reaches **10 full repair cycles** without achieving a stable minimum closure, stop active work on that class for the current campaign.

Then do all of the following before moving on:

1. mark the class as blocked or paused in the ledgers
2. record the date
3. record the accumulated retry count
4. summarize the blocking cause
5. note the likely resume condition or missing dependency
6. continue with the next class in the active queue

Do not let one pathological class stall the entire campaign indefinitely.

Treat stop-loss as a bookkeeping and queue-protection rule, not as a substitute for failure classification. First identify the failure layer and try the standard repair patterns; only then count full repair cycles toward the stop-loss threshold.

## Ledger Maintenance Requirements

After a successful class closure, or after a 10-attempt stop-loss pause, update the relevant records:

- `todo_pybind11.csv`
- the target `class_bind_methods_details/*_methods.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`
- `pybind_progress_log.md`

For blocked classes, include:

- date
- retry count
- failure layer
- concise technical reason
- what would need to change before retrying

## Reporting Expectations

When reporting campaign progress, keep the structure explicit:

- active queue
- current class completed or blocked
- tests run and their outcomes
- ledger files updated
- next class in queue

When a class is blocked after 10 attempts, say so clearly instead of leaving the status ambiguous.

## Completion Checklist

A rollout step is complete when:

- the current class has either been completed or formally paused after stop-loss
- focused validation has been run appropriately
- smoke has been run when relevant
- ledgers are synchronized
- the next class in the queue is clear

## Relationship to Existing Notes

Use this skill together with:

- `reference/notes/base_inventory_rollout_order_2026-04-08.md` for phase and class ordering

The rollout-order note is an ordering aid, not the primary pending-class database.

Prefer the CSV ledgers when deciding what is actually unfinished and actionable.
