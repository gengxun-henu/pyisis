# Pybind labels guide

Use these labels to manage the GitHub-web pybind task queue.

## Core queue labels

| Label | Purpose | When to add |
|---|---|---|
| `pybind-task` | Marks an issue or PR as a pybind workflow task | Add to every pybind issue and its PR |
| `ready-for-agent` | Task is scoped, documented, and ready to be picked up | Add when the issue template is fully filled and blockers are clear |
| `agent-active` | A GitHub agent or PR is currently working this task | Add when work starts; remove when merged, blocked, or paused |
| `blocked` | Task hit a blocker and should not keep auto-retrying | Add after retry budget is exhausted or a hard blocker is confirmed |
| `needs-human-review` | A person should inspect behavior, design, or CI failure details | Add when automation cannot safely decide the next move |
| `done` | Task is completed and validated | Add after merge or when the PR is accepted as complete |

## Failure classification labels

| Label | Use for |
|---|---|
| `binding-bug` | The pybind layer is wrong or incomplete |
| `test-bug` | The test expectation or lifecycle assumption is wrong |
| `environment-dependent` | Failure depends on missing data, CI environment, or external runtime setup |
| `upstream-behavior` | Upstream ISIS behavior differs from the initial assumption |
| `ci-failure` | Build, dependency, or workflow failure in CI |

## Optional planning labels

| Label | Use for |
|---|---|
| `high-priority` | Best next target for queue pickup |
| `small-slice` | Good candidate for one short binding iteration |
| `progress-update-needed` | Binding surface changed and progress files must be synchronized |

## Recommended lifecycle

1. Open an issue with `pybind-task` + `ready-for-agent`
2. When work starts, add `agent-active`
3. If CI fails, optionally add one classification label such as `binding-bug` or `ci-failure`
4. If retry budget reaches 5 and the task still fails, add `blocked` + `needs-human-review`, remove `ready-for-agent`, and stop
5. When the task is complete, remove transient labels and add `done`

## Notes

- Keep labels small and predictable; do not invent many near-duplicates.
- Prefer one failure classification label at a time unless there is a strong reason to stack them.
- `ready-for-agent` should mean the issue is actually actionable, not merely interesting.
