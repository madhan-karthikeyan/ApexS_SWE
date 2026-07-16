# Verification Report

Date: 2026-04-10

## Scope

- Docker service health
- Backend API reachability
- Frontend production build
- Active automated tests
- Stage-by-stage workflow verification
- Celery dispatch path enforcement
- Auth/RBAC basics and monitoring endpoint
- Learning evaluation metrics reporting

## Environment Snapshot

- OS: Windows
- Project root: `D:\VIT2026\SE`
- Runtime profile: Docker Compose local stack

## Stage 0: Environment and Services Up

Status: Pass

- `docker compose ps` shows all required services up:
  - `frontend`
  - `backend`
  - `db`
  - `redis`
  - `minio`
  - `celery_worker`
- Endpoint probes:
  - `http://localhost:5173` -> 200
  - `http://localhost:8000` -> 200
  - `http://localhost:8000/docs` -> 200
  - `http://localhost:9001` -> 200
  - `http://localhost:8000/health` -> 200

## Stage 1: Team and Dataset Upload

Status: Pass

- Upload API returns success payload with:
  - `upload_id`
  - `rows`
  - `preview`
  - `is_valid`
- Team dataset listing is available from `GET /api/v1/datasets/{team_id}`.

## Stage 2: Sprint Configuration

Status: Pass

- Sprint create endpoint works: `POST /api/v1/sprints/`.
- Plan generation endpoint returns `job_id`: `POST /api/v1/plans/generate`.
- Frontend routes to optimization page using returned `job_id`.

## Stage 3: Optimization Processing Status

Status: Pass

- Status polling endpoint operational: `GET /api/v1/plans/status/{job_id}`.
- Observed pipeline step model:
  - `loading`
  - `extracting`
  - `learning`
  - `optimizing`
  - `explaining`
  - `done`
- Completion emits `status=complete`, `progress=100`, and `plan_id`.

## Stage 4: Generated Sprint Plan Page

Status: Pass

- Plan endpoint returns meaningful totals (`total_value`, `capacity_used`, `status`).
- Story table is rendered from `GET /api/v1/plans/{plan_id}/stories`.
- Capacity validation shown in UI against configured capacity.

## Stage 5: Plan Quality Checks

Status: Pass

- UI now computes and displays checks for:
  - risk threshold compliance
  - skill compatibility
  - dependency satisfaction
  - duplicate story IDs
  - total constraint violations
- Backend optimization and explanation logic aligned with these checks.

## Stage 6: Explainability Panel

Status: Pass

- Explanations load from `GET /api/v1/plans/{plan_id}/explain`.
- Selected and rejected explanations are both shown.
- Reason text, confidence, and contribution fields are displayed.

## Stage 7: Approval

Status: Pass

- Approval endpoint functional: `PUT /api/v1/plans/{plan_id}/approve`.
- Re-fetch reflects status transition to `approved`.

## Stage 8: Export

Status: Pass

- Export endpoints functional:
  - `POST /api/v1/plans/{plan_id}/export?format=csv`
  - `POST /api/v1/plans/{plan_id}/export?format=json`
- Export row/object count matches selected stories in plan.

## Stage 9: Regression Checks After Rerun

Status: Pass

- Re-optimization endpoint works: `PUT /api/v1/plans/{plan_id}/modify`.
- New `plan_id` generated on rerun.
- Lower capacity and lower risk threshold produce tighter selections.

## Additional Completion Checks (Requested Items)

Status: Pass

1. Celery + Redis default path hardening
- Celery remains default async path.
- Dispatch failures return explicit 503 instead of silent fallback behavior.

2. Static UI replacement
- Dashboard system overview is now fed by live health/metrics APIs.

3. Learning evaluation metrics
- Reports now include model diagnostics (sample count, MAE, R2, feature importance, model type).

4. Auth/RBAC + logging/monitoring basics
- Added current-user and role guard dependencies.
- Added request logging middleware.
- Added `/health` monitoring endpoint with service checks.

5. Integration and edge tests
- Full stage-flow and edge-constraint tests are present and passing.
- Added checks for health endpoint and auth enforcement path.

## Automated Verification Results

- Python tests (active suite): pass
  - Command: `pytest -q`
  - Result: `20 passed` (targeted integration + unit suite)
- Frontend build: pass
  - Command: `npm run build` (in `frontend`)
  - Result: build success (non-blocking chunk-size warning)

## Notes

- Warnings seen during tests are non-blocking:
  - FastAPI deprecation warning for `on_event`
  - NumPy runtime warning on tiny correlation samples
- A separate legacy backend test folder exists; active root test suite is standardized via `pytest.ini`.

## Verification Summary

- The project now satisfies the end-to-end stage checklist in practical local execution.
- Frontend workflow is fully wired to live backend APIs.
- Core quality gates (health, tests, build, workflow stages) are passing.
