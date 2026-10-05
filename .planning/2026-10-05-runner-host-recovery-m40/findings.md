# Findings

- Workflow: `runner-host-sanity-check.yml`
- Run: `37266087196`
- Result: failed in `Self-heal stale checkout workspace on self-hosted runner`.
- Runner mode resolved to the self-hosted pyisis host.
- The checkout workspace under `/opt/actions-runner-pyisis/_work/pyisis/pyisis` has stale/corrupt metadata and files owned so the runner account cannot remove them.
- Representative failures were `rm: ... 权限不够` across tracked source files; checkout and later probes were skipped.
- Repository-side workflow diagnostics are working, but host-level ownership/permission repair is still required before self-hosted jobs can run.
