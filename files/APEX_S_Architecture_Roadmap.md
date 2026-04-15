# ApexS Single Source of Truth
## Explainable Context-Aware Sprint Planning System
### Team ApexS | BCSE301P | VIT

This document is the implementation-accurate source of truth for the current repository.

It combines the relevant information from:
- `README.md`
- `files/FINAL_REVIEW_SUBMISSION_CONTENT.md`
- `files/idea.txt`
- the actual backend, frontend, worker, script, and test code in this repo

This file keeps only what is implemented now, plus a short section for known gaps. Older roadmap content that described planned work has been removed.

---

## 1. Project Identity

### Project Title
Explainable Context-Aware Sprint Planning System

### Current Positioning
This project is a working full-stack decision-support system for Scrum sprint planning.

The system:
- ingests historical or candidate sprint datasets in CSV form
- extracts team context from historical sprint data
- learns team-specific prioritization weights
- generates sprint plans using constrained optimization
- explains selected and rejected stories
- supports approval, modification, re-run, and export

### Core Novelty That Is Actually Implemented
- Team-specific learned weighting from historical sprint data
- Constraint-aware sprint selection using optimization
- Explainability for both selected and rejected stories
- End-to-end workflow from upload to export

---

## 2. What Is Implemented

### Backend
Implemented in FastAPI with SQLAlchemy models, service layer, and worker orchestration.

Main areas:
- authentication routes
- teams, datasets, sprints, stories, plans, reports, and context APIs
- health endpoint with service checks
- request logging middleware
- planning worker pipeline with progress states

Primary backend entry points:
- `backend/app/main.py`
- `backend/app/api/v1/plans.py`
- `backend/app/api/v1/datasets.py`
- `backend/app/api/v1/reports.py`
- `backend/app/workers/planning_task.py`

### Frontend
Implemented in React + TypeScript under `frontend/`.

Implemented user-facing workflow pages:
- Dashboard
- Dataset Upload
- Sprint Configuration
- Optimization Processing
- Generated Sprint Plan
- Explainability Panel
- Sprint Plan Approval
- Reports

Primary frontend entry points:
- `frontend/src/App.tsx`
- `frontend/src/pages/*`
- `frontend/src/store/sprintStore.ts`
- `frontend/src/utils/api.ts`

### Data Processing
Implemented utility scripts:
- `scripts/convert_dataset.py`
- `scripts/clean_public_jira_dataset.py`
- `scripts/convert_tawos_export.py`

These support:
- column normalization from Jira/Kaggle-like exports
- derivation and cleaning of value/risk/skill/status fields
- conversion of TAWOS `Issue` exports, with optional `Issue_Link` dependency import
- generation of upload-ready planner CSV files
- collision-safe dataset storage paths during upload

### Testing
Implemented automated tests:
- unit tests in `tests/unit/`
- integration tests in `tests/integration/`

Covered areas:
- optimization constraints
- context extraction
- explainability output
- reports payload
- health endpoint
- end-to-end plan generation flow
- approval and export flow
- modify and re-run flow

---

## 3. End-to-End Workflow That Exists Today

The current practical flow is:

1. Upload dataset
2. Create sprint configuration
3. Generate plan
4. Poll async job status
5. View generated plan
6. Inspect explainability
7. Approve plan
8. Export CSV or JSON
9. Modify constraints and re-run if needed

### Stage Checklist
- Stage 0: services up and reachable
- Stage 1: dataset upload works
- Stage 2: sprint config and job creation work
- Stage 3: status progression reaches complete with `plan_id`
- Stage 4: generated plan is retrievable with totals and stories
- Stage 5: quality checks are visible in UI
- Stage 6: explainability panel loads selected and rejected reasons
- Stage 7: approval persists plan state
- Stage 8: CSV and JSON export work
- Stage 9: modify and re-run produce a new plan

---

## 4. High-Level Architecture

The implemented system follows a layered architecture:

### Presentation Layer
- React frontend
- route-driven workflow
- polling for plan status
- visualization of reports and explainability

### API Layer
- FastAPI application
- versioned REST APIs under `/api/v1`
- health endpoint at `/health`

### Service Layer
- `ContextExtractor`
- `WeightLearningModel`
- `OptimizationEngine`
- `ExplainabilityEngine`

### Worker Layer
- Celery app integration exists
- planning pipeline is orchestrated in `planning_task.py`
- thread fallback behavior is config-controlled

### Data Layer
- SQLAlchemy-backed relational persistence
- SQLite default local path
- PostgreSQL available in Docker Compose
- MinIO bucket support for uploaded datasets
- Redis support for Celery / health checks

---

## 5. Current Technology Stack

Only technologies present in the repo or backend requirements are listed here.

### Frontend
- React 18
- TypeScript
- Vite
- React Router
- React Query
- Axios
- Zustand
- Recharts
- Tailwind / PostCSS frontend build setup

### Backend
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pydantic Settings
- FastAPI Users
- PuLP
- OR-Tools
- scikit-learn
- SHAP
- Pandas
- NumPy
- Celery
- Redis
- boto3
- python-jose
- passlib

### Runtime / Infra
- Docker Compose
- PostgreSQL service
- Redis service
- MinIO service
- Celery worker service

---

## 6. Current Runtime Model

### Docker Runtime
The intended full-system runtime uses:
- `frontend`
- `backend`
- `db`
- `redis`
- `minio`
- `celery_worker`

### Local Runtime
The backend settings default to SQLite unless environment variables override them.

Important practical detail:
- local code can run against SQLite
- Docker Compose is the closest thing to the intended integrated environment

### Health and Monitoring
Implemented in `backend/app/main.py`:
- `GET /` returns API root message
- `GET /health` returns:
  - overall status
  - database check
  - Redis check
  - MinIO check
  - Celery-enabled flag
  - uptime seconds
  - request count

---

## 7. Backend Module Truth

### App Entry
- `backend/app/main.py`

Responsibilities:
- app creation
- router registration
- CORS setup
- startup schema creation
- default team bootstrap
- request logging middleware
- root and health endpoints

### Security
- `backend/app/core/security.py`

Implemented:
- password hashing and verification
- JWT creation and decode
- current-user dependency
- role guard dependency
- anonymous fallback when auth enforcement is off

### Planning APIs
- `backend/app/api/v1/plans.py`

Implemented endpoints:
- `POST /api/v1/plans/generate`
- `GET /api/v1/plans/status/{job_id}`
- `GET /api/v1/plans/{plan_id}`
- `PUT /api/v1/plans/{plan_id}/approve`
- `POST /api/v1/plans/{plan_id}/export`
- `PUT /api/v1/plans/{plan_id}/modify`
- `GET /api/v1/plans/{plan_id}/explain`
- `GET /api/v1/plans/{plan_id}/explain/{story_id}`
- `GET /api/v1/plans/{plan_id}/stories`

### Dataset APIs
- `backend/app/api/v1/datasets.py`

Implemented:
- upload
- validation
- preview
- listing by team

### Reports APIs
- `backend/app/api/v1/reports.py`

Implemented metrics payload:
- sprint velocity history
- business value history
- selected risk aggregate
- rejected risk aggregate
- weight evolution
- learning sample count
- learning dataset source count
- learning MAE
- learning R2
- learning feature importance
- learning model type

### Context APIs
- `backend/app/api/v1/context.py`

Implemented:
- latest context retrieval
- context extraction trigger path

---

## 8. Planning Pipeline Truth

Main implementation:
- `backend/app/workers/planning_task.py`

### Implemented Pipeline Steps
The worker reports these stages:
- `loading`
- `syncing_stories`
- `loading_history`
- `extracting`
- `learning`
- `optimizing`
- `explaining`
- `done`

### Actual Pipeline Behavior
1. Load latest dataset
2. Upsert dataset stories into sprint stories table
3. Load historical team uploads
4. Extract context
5. Persist context snapshot
6. Learn weights from historical data
7. Load stories for sprint
8. Solve optimization problem
9. Generate explanations
10. Save plan and explanations
11. Return `plan_id`

### Job Execution Modes
Configured in `backend/app/core/config.py` and `planning_task.py`:
- Celery path when available and enabled
- thread fallback only when allowed by config

---

## 9. Core Service Truth

### ContextExtractor
File:
- `backend/app/services/context_extractor.py`

Implemented outputs:
- urgency weight
- value weight
- alignment weight
- velocity
- completion rate
- skill distribution
- average risk tolerance
- value-completion correlation

### WeightLearningModel
File:
- `backend/app/services/weight_learning.py`

Implemented:
- ridge-regression-based learning when dependencies and enough data exist
- fallback normalized context weights otherwise
- learning diagnostics:
  - sample count
  - MAE
  - R2
  - feature importance
  - model type

### OptimizationEngine
File:
- `backend/app/services/optimization_engine.py`

Implemented constraints:
- sprint capacity
- risk threshold
- skill compatibility
- dependency satisfaction
- non-plannable status filtering

Implemented solver path:
- PuLP/CBC MILP solve
- greedy fallback when MILP execution is unavailable or does not return an optimal solve

Implemented result payload:
- selected stories
- rejected stories
- total value
- total risk
- capacity used
- solver status
- fallback warnings when applicable

### ExplainabilityEngine
File:
- `backend/app/services/explainability_engine.py`

Implemented:
- selected-story reasons
- rejection reasons
- confidence score
- contribution-related fields
- optional SHAP-aware branch when SHAP is installed

Rejection reasons currently supported:
- risk threshold exceeded
- required skill unavailable
- dependency unsatisfied
- capacity would be exceeded
- lower priority under capacity constraints

---

## 10. Frontend Truth

### Routing
File:
- `frontend/src/App.tsx`

Implemented routes:
- `/`
- `/upload`
- `/configure`
- `/optimizing/:jobId`
- `/plan/:planId`
- `/explain/:planId`
- `/approve/:planId`
- `/reports/:teamId`

### Dashboard
File:
- `frontend/src/pages/Dashboard.tsx`

Implemented:
- workflow entry cards
- live `/health` status
- live reports snapshot
- reset workflow action

### Generated Plan Screen
File:
- `frontend/src/pages/GeneratedSprintPlan.tsx`

Implemented:
- KPI summary
- selected story table
- plan quality checks
- modify inputs
- modify and re-run action
- navigate to explainability and approval

### Explainability Panel
File:
- `frontend/src/pages/ExplainabilityPanel.tsx`

Implemented:
- selected and rejected explanation loading
- pagination for rejected explanations
- story selector
- explanation detail card
- value vs risk chart
- rejected-story reason table

### Reports Page
File:
- `frontend/src/pages/Reports.tsx`

Implemented:
- sprint velocity chart
- business value chart
- latest learned weight snapshot
- learning evaluation table
- feature importance table

---

## 11. Data Model Truth

Primary entities present in the implementation:
- `User`
- `ScrumTeam`
- `Sprint`
- `UserStory`
- `DatasetUpload`
- `Context`
- `SprintPlan`
- `Explanation`

Important planning fields on `UserStory`:
- `story_id`
- `sprint_id`
- `title`
- `description`
- `story_points`
- `business_value`
- `risk_score`
- `required_skill`
- `depends_on`
- `status`

---

## 12. Dataset Truth

Primary historical dataset used in project docs and paper work:
- `tmp/converted_sprint_history_dataset_1.csv`

Observed characteristics from repository data:
- 170 stories
- 12 sprints
- 5 skill categories
- risk range 0.05 to 0.95
- business value range 5.0 to 10.0
- completion labels present

Other upload-ready datasets also exist in `tmp/`, but the above file is the main one used for learning, explainability, and reporting demonstrations.

---

## 13. API Truth Summary

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`

### Teams
- `GET /api/v1/teams/`
- `POST /api/v1/teams/`
- `GET /api/v1/teams/{team_id}`

### Datasets
- `POST /api/v1/datasets/upload`
- `GET /api/v1/datasets/{team_id}`
- `GET /api/v1/datasets/{upload_id}/preview`

### Sprints
- `POST /api/v1/sprints/`
- `GET /api/v1/sprints/{sprint_id}`
- `GET /api/v1/sprints/{sprint_id}/stories`

### Stories
- `POST /api/v1/stories/`
- `GET /api/v1/stories/{story_id}`
- `PUT /api/v1/stories/{story_id}`
- `DELETE /api/v1/stories/{story_id}`

### Context
- `POST /api/v1/context/extract`
- `GET /api/v1/context/{team_id}/latest`

### Plans
- `POST /api/v1/plans/generate`
- `GET /api/v1/plans/status/{job_id}`
- `GET /api/v1/plans/{plan_id}`
- `PUT /api/v1/plans/{plan_id}/approve`
- `POST /api/v1/plans/{plan_id}/export`
- `PUT /api/v1/plans/{plan_id}/modify`
- `GET /api/v1/plans/{plan_id}/explain`
- `GET /api/v1/plans/{plan_id}/explain/{story_id}`
- `GET /api/v1/plans/{plan_id}/stories`

### Reports
- `GET /api/v1/reports/{team_id}/metrics`
- `GET /api/v1/reports/{team_id}/capabilities`

### System
- `GET /`
- `GET /health`

---

## 14. Verification Truth

### Verified / Recorded in Project Docs
The project documentation records these practical checks:
- Docker services up:
  - `frontend`
  - `backend`
  - `db`
  - `redis`
  - `minio`
  - `celery_worker`
- endpoint probes:
  - `http://localhost:5173`
  - `http://localhost:8000`
  - `http://localhost:8000/docs`
  - `http://localhost:9001`
  - `http://localhost:8000/health`
- frontend production build success
- active automated suite recorded as passing in project verification docs

### Current Test Assets in Repo
Important test files:
- `tests/unit/test_optimization.py`
- `tests/unit/test_context_extractor.py`
- `tests/unit/test_explainability.py`
- `tests/integration/test_plans_api.py`

### What the Integration Tests Assert
- health root works
- upload validation works
- missing resource cases return correct errors
- reports endpoint returns metrics payload
- auth enforcement path works
- full planning pipeline can complete
- selected stories respect capacity and risk
- dependency constraints hold
- approval works
- export works
- modify and re-run works

---

## 15. Demo Truth

If presenting the working system, the current clean demo sequence is:

1. Start Docker stack
2. Open dashboard
3. Upload `tmp/converted_sprint_history_dataset_1.csv`
4. Configure sprint goal, capacity, risk threshold, and skills
5. Generate plan
6. Show processing steps and progress
7. Open generated plan and quality checks
8. Open explainability panel and inspect selected and rejected stories
9. Modify constraints and re-run
10. Approve final plan
11. Export CSV/JSON
12. Open reports page for trends and learning diagnostics

---

## 16. Known Gaps and Accuracy Notes

This section records what is not fully complete or where environment-specific caution is needed.

### Known Gaps
- Local runtime defaults may differ from Docker runtime because settings and environment values must match exactly.
- Celery integration exists, but actual execution depends on environment setup and config flags.
- Some reproducibility steps remain environment-sensitive, especially around optional dependencies and local permissions.
- There are duplicate test directories in the repo (`tests/` and `backend/tests/`), which can create maintenance drift.

### Accuracy Notes
- Older docs in the repo may mention incomplete frontend wiring or incomplete settings loading. Some of those statements are now stale.
- Older docs may also mention future CI/deploy plans. Those are not treated here as completed work unless the implementation is present in this repository.
- This file should be treated as the authoritative implementation-state document over older roadmap sections.

---

## 17. What To Say in Viva / Review

Short accurate positioning:

`ApexS is a working explainable sprint-planning system that learns team-specific weights from historical data, applies constraint-aware optimization, explains selected and rejected stories, and supports the full workflow from upload to approval and export.`

Short novelty positioning:

`The implemented novelty is the integration of learned weighting, constrained planning, and human-readable explainability inside one usable end-to-end sprint planning loop.`

---

## 18. Primary Evidence Files

Use these files first when defending implementation:
- `backend/app/main.py`
- `backend/app/api/v1/plans.py`
- `backend/app/api/v1/datasets.py`
- `backend/app/api/v1/reports.py`
- `backend/app/services/context_extractor.py`
- `backend/app/services/weight_learning.py`
- `backend/app/services/optimization_engine.py`
- `backend/app/services/explainability_engine.py`
- `backend/app/workers/planning_task.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/GeneratedSprintPlan.tsx`
- `frontend/src/pages/ExplainabilityPanel.tsx`
- `frontend/src/pages/Reports.tsx`
- `tests/integration/test_plans_api.py`

---

## 19. Final Summary

This repository is no longer just a plan or prototype skeleton. It contains a working implementation of the project’s core idea:
- data-driven sprint planning
- team-context extraction
- learned prioritization weights
- constrained optimization
- explainability
- review, approval, and export

Remaining work is mostly hardening, environment consistency, and documentation cleanup, not missing core system functionality.
