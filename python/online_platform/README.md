# `online_platform` backend prototype

This package is a lightweight backend prototype skeleton for the online planetary photogrammetry platform described in:

- `reference/notes/online_platform_prd.md`
- `reference/notes/online_planetary_photogrammetry_platform_architecture_2026-04-18.md`

## Prototype goals

The current prototype focuses on structure rather than a fully runnable production service. It provides:

1. A FastAPI application factory placeholder
2. Typed API route modules for health, uploads, jobs, and single-scene workflow preview/run
3. Internal domain models for jobs, steps, uploads, and artifacts
4. Service-layer placeholders for job management, storage, and archive workflows
5. Celery/DAG placeholders for future asynchronous orchestration

## Prototype API surface

- `GET /health/`: health check
- `POST /uploads/`: create upload placeholder metadata
- `GET /jobs/`: list in-memory jobs
- `POST /jobs/`: create a generic queued job record
- `GET /jobs/{job_id}`: fetch a specific job
- `POST /jobs/single-scene/preview`: preview the single-scene processing workflow
- `POST /jobs/single-scene/run`: execute an inline prototype single-scene workflow and return generated artifacts/layout

## Suggested next steps

1. Replace in-memory services with PostgreSQL-backed repositories
2. Add real upload persistence and object storage integration
3. Connect worker steps to ISIS CLI and `isis_pybind`
4. Add authentication, authorization, and tenant isolation
5. Add tests for routes, services, and workflow construction
