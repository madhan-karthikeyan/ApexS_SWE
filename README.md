# Apex Sprint Planner

Explainable, context-aware sprint planning platform with a FastAPI backend, React frontend, asynchronous planning pipeline, and containerized local setup.

This README documents what has been implemented, how the system works today, and how to run, test, and troubleshoot it.

Last updated: April 10, 2026

## 1) Current Implementation Status

### Completed

- Full backend service scaffold with domain models, API routers, planning services, and worker pipeline.
- Frontend application scaffold with main planning flow pages and reusable components.
- Docker Compose stack for local full-system execution.
- Dataset upload + preview, context extraction, optimization, explainability, and plan export routes.
- Basic unit and integration tests (current suite passing according to verification report).

### Partially Implemented / In Progress

- Frontend plan view, explainability, and approval screens currently include static/demo data in places.
- Celery integration exists, but async jobs currently run through in-process background threads.
- Configuration class defines defaults but does not yet actively bind environment variables via settings loader.

### Verified Baseline

- Backend dependencies install successfully.
- Frontend dependencies install and production build succeed.
- Python tests currently pass (4 tests, with warnings).

See `VERIFICATION_REPORT.md` for the latest recorded verification snapshot.

## 2) System Overview

### Architecture

- **Backend**: FastAPI + SQLAlchemy + service layer.
- **Data Layer**: SQLite by default (`backend/apexs.db`), with Postgres service available in Compose.
- **Object Storage**: MinIO for dataset file storage.
- **Queue/Worker Infra**: Redis + Celery scaffold.
- **Frontend**: React + TypeScript + Vite + React Query + Router.
- **Optimization**: ILP via PuLP/CBC, with greedy fallback.

### High-Level Flow

1. Upload CSV dataset for a team.
2. Create sprint configuration (goal, capacity, risk threshold, skills).
3. Trigger plan generation.
4. Async pipeline performs:
	 - dataset loading
	 - context extraction
	 - weight learning
	 - constrained optimization
	 - explanation generation
	 - plan persistence
5. Poll job status until complete.
6. View plan, inspect explanations, approve/export.

## 3) Repository Layout

```text
backend/      FastAPI app, models, API routes, services, workers
frontend/     Main React TypeScript app (planner UI)
tests/        Root test suite (unit + integration)
backend/tests Additional backend test suite
files/        Documentation assets
docker-compose.yml
README.md
VERIFICATION_REPORT.md
```

## 4) Backend Details

### API Base

- App root: `GET /`
- Versioned API base: `/api/v1`

### Auth Routes

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`

### Team Routes

- `GET /api/v1/teams/`
- `POST /api/v1/teams/`
- `GET /api/v1/teams/{team_id}`

### Dataset Routes

- `POST /api/v1/datasets/upload`
	- Validates required CSV columns: `story_id`, `story_points`, `business_value`, `risk_score`
- `GET /api/v1/datasets/{team_id}`
- `GET /api/v1/datasets/{upload_id}/preview`

### Sprint Routes

- `POST /api/v1/sprints/`
- `GET /api/v1/sprints/{sprint_id}`
- `GET /api/v1/sprints/{sprint_id}/stories`

### Story Routes

- `POST /api/v1/stories/`
- `GET /api/v1/stories/{story_id}`
- `PUT /api/v1/stories/{story_id}`
- `DELETE /api/v1/stories/{story_id}`

### Context Routes

- `POST /api/v1/context/extract`
- `GET /api/v1/context/{team_id}/latest`

### Plan Routes

- `POST /api/v1/plans/generate`
- `GET /api/v1/plans/status/{job_id}`
- `GET /api/v1/plans/{plan_id}`
- `PUT /api/v1/plans/{plan_id}/approve`
- `POST /api/v1/plans/{plan_id}/export?format=csv|json`
- `PUT /api/v1/plans/{plan_id}/modify`
- `GET /api/v1/plans/{plan_id}/explain`
- `GET /api/v1/plans/{plan_id}/explain/{story_id}`
- `GET /api/v1/plans/{plan_id}/stories`

### Reporting Routes

- `GET /api/v1/reports/{team_id}/metrics`

### Backend Pipeline Components

- `ContextExtractor`: computes urgency/value/alignment context weights from historical data.
- `WeightLearningModel`: learns optimization weights from dataset + context.
- `OptimizationEngine`: selects stories with constraints:
	- capacity
	- risk threshold
	- required skills
	- story dependencies
- `ExplainabilityEngine`: generates per-story acceptance/rejection reasons and confidence.
- `planning_task`: async job tracking with progress states (`loading`, `extracting`, `learning`, `optimizing`, `explaining`, `done`).

## 5) Frontend Details

### Main Frontend App

The active product UI is under `frontend/`.

Pages currently implemented:

- Dashboard
- Dataset Upload
- Sprint Configuration
- Optimization Processing
- Generated Sprint Plan
- Explainability Panel
- Sprint Plan Approval

Core frontend stack:

- React 18 + TypeScript
- Vite
- React Router
- React Query
- Axios
- Zustand

### Important Note About Root-Level React Files

The repository also includes a separate root-level Vite/React setup (`main.jsx`, `swe.jsx`) that appears to be an older or unrelated SDLC study UI. The Dockerized product runtime uses the `frontend/` app.

## 6) Data Model Snapshot

Primary entities:

- `User`
- `ScrumTeam`
- `Sprint`
- `UserStory`
- `DatasetUpload`
- `Context`
- `SprintPlan`
- `Explanation`

Notable `UserStory` attributes used in optimization:

- `story_points`
- `business_value`
- `risk_score`
- `required_skill`
- `depends_on`

## 7) Running the Project

## Recommended: Docker Compose

### Prerequisites

- Docker Desktop installed and running.
- Docker daemon reachable (`docker version` shows both Client and Server).

### Start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

### Access

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

### Stop

```powershell
docker compose down
```

## 8) Current Runtime Snapshot (Observed)

The following was verified on April 10, 2026 with Docker Compose running:

- All core services were up: `frontend`, `backend`, `db`, `redis`, `minio`, `celery_worker`.
- Endpoint checks returned `200` for:
	- `http://localhost:5173`
	- `http://localhost:8000`
	- `http://localhost:8000/docs`
	- `http://localhost:9001`

This snapshot confirms the stack is runnable end-to-end in local Docker.

## Local Development (Without Docker)

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite proxies `/api/*` requests to backend (`http://localhost:8000` by default, or `VITE_API_PROXY_TARGET` when provided).

## 9) Testing

Run root tests:

```powershell
pytest -q
```

Run backend tests explicitly:

```powershell
pytest -q backend/tests
```

Current repository includes test folders in both:

- `tests/`
- `backend/tests/`

## 10) Dataset Converter

Use the converter script when you have a Jira/Kaggle-style export and want to produce the exact CSV schema the app expects.

```powershell
python scripts\convert_dataset.py input.csv output.csv
```

The script auto-detects common source columns like:

- `story_id` / `key` / `issue key`
- `title` / `summary`
- `points` / `story points` / `estimate`
- `priority` / `severity`
- `status` / `resolution`
- `depends_on` / `blocks` / `parent`

It writes the Apex planner format with these columns:

- `story_id`
- `title`
- `description`
- `story_points`
- `business_value`
- `risk_score`
- `required_skill`
- `sprint_id`
- `sprint_completed`
- `depends_on`
- `status`

## 11) Upload-Ready Datasets in tmp/

The following converted datasets currently exist in `tmp/` and were validated for upload schema integrity.

### Validation Summary

- All files passed:
  - Required columns present
  - No blank required fields
  - Numeric fields parse correctly
  - Risk scores in range `[0, 1]`
  - No duplicate `story_id`
  - No broken `depends_on` references

### File-by-File Guidance

1. `tmp/converted_sprint_history_dataset_1.csv`
	- Best historical dataset for learning and explainability behavior.
	- Strong variety in points, value, risk, skills, and dependencies.
	- Recommended as primary historical upload.

2. `tmp/converted_scrum_candidate.csv`
	- Upload-valid candidate backlog.
	- Low diversity (uniform point/value/risk patterns).
	- Good as candidate input, weak as learning history.

3. `tmp/converted_jira_historical.csv`
	- Upload-valid and high-volume.
	- Limited modeling richness (many blank `required_skill`, all `sprint_completed=0`, narrow score bands).
	- Use after enrichment if you want better weight-learning signal.

## 12) Health Checks

```powershell
curl http://localhost:8000/
curl http://localhost:8000/docs
docker compose ps
```

Expected API root response:

```json
{"message":"Explainable Sprint Planner API"}
```

## 13) Environment and Configuration

Example variables (`.env.example`):

- `DATABASE_URL`
- `REDIS_URL`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Important implementation note:

- The current settings object uses in-code defaults. `DATABASE_URL` in `.env` may not automatically override runtime config until the settings loader is fully wired.

## 14) Known Gaps and Risks

- Some frontend pages still show static/demo data rather than fully wired API responses.
- Async worker uses background threads in current flow; Celery path is scaffolded but not fully primary.
- Postgres service is available in Compose but default backend config points to SQLite.
- Duplicate test directories can cause maintenance drift unless consolidated.

## 15) Troubleshooting

### Docker pipe error on Windows

If you see an error like:

`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

Fix:

1. Start Docker Desktop.
2. Wait for engine to become ready.
3. Confirm with `docker version` (must include Server section).
4. Re-run `docker compose up --build`.

### Frontend container exits with missing tailwindcss

Symptom example:

`Failed to load PostCSS config ... Cannot find module 'tailwindcss'`

Cause:

- Stale anonymous `node_modules` volume in the frontend service.

Fix:

```powershell
docker compose up -d --force-recreate --renew-anon-volumes frontend
```

Then verify:

```powershell
docker compose ps frontend
curl http://localhost:5173
```

### Ports already in use

If startup fails due to ports, check and free these:

- 5173 (frontend)
- 8000 (backend)
- 5432 (Postgres)
- 6379 (Redis)
- 9000/9001 (MinIO)

## 16) Suggested Next Improvements

1. Wire environment-backed settings (`pydantic-settings`) in backend config.
2. Make Celery + Redis the default async execution path.
3. Replace static frontend plan/explainability data with live API data.
4. Consolidate test directories and expand API integration coverage.
5. Add migrations and production profile separation.
