# Roadmap Files Checklist (Current State)

Purpose: track roadmap-expected files and whether they are present in the current repository.

Date updated: 2026-04-10
Source: `files/APEX_S_Architecture_Roadmap.md`

## 1) Backend core files

- [x] `backend/app/main.py`
- [x] `backend/app/api/v1/auth.py`
- [x] `backend/app/api/v1/teams.py`
- [x] `backend/app/api/v1/datasets.py`
- [x] `backend/app/api/v1/sprints.py`
- [x] `backend/app/api/v1/stories.py`
- [x] `backend/app/api/v1/plans.py`
- [x] `backend/app/api/v1/reports.py`
- [x] `backend/app/api/v1/context.py`
- [x] `backend/app/core/config.py`
- [x] `backend/app/core/database.py`
- [x] `backend/app/core/security.py`
- [x] `backend/app/services/context_extractor.py`
- [x] `backend/app/services/weight_learning.py`
- [x] `backend/app/services/optimization_engine.py`
- [x] `backend/app/services/explainability_engine.py`
- [x] `backend/app/workers/celery_app.py`
- [x] `backend/app/workers/planning_task.py`
- [x] `backend/requirements.txt`

## 2) Backend migration and schema support

- [x] `backend/alembic.ini`
- [x] `backend/migrations/`
- [x] `backend/migrations/env.py`
- [x] `backend/migrations/README.md`

## 3) Frontend core files

- [x] `frontend/src/App.tsx`
- [x] `frontend/src/main.tsx`
- [x] `frontend/src/pages/Dashboard.tsx`
- [x] `frontend/src/pages/DatasetUpload.tsx`
- [x] `frontend/src/pages/SprintConfiguration.tsx`
- [x] `frontend/src/pages/OptimizationProcessing.tsx`
- [x] `frontend/src/pages/GeneratedSprintPlan.tsx`
- [x] `frontend/src/pages/ExplainabilityPanel.tsx`
- [x] `frontend/src/pages/SprintPlanApproval.tsx`
- [x] `frontend/src/pages/Reports.tsx`
- [x] `frontend/src/hooks/usePlanStatus.ts`
- [x] `frontend/src/hooks/useDatasetUpload.ts`
- [x] `frontend/src/hooks/useExplanations.ts`
- [x] `frontend/src/store/sprintStore.ts`
- [x] `frontend/src/utils/api.ts`
- [x] `frontend/src/types/index.ts`

## 4) Frontend design system / tooling

- [x] `frontend/src/components/ui/`
- [x] `frontend/tailwind.config.ts`
- [x] `frontend/postcss.config.js`
- [x] `frontend/components.json`
- [x] `frontend/vite.config.ts`

## 5) Test and verification files

- [x] `tests/unit/test_context_extractor.py`
- [x] `tests/unit/test_explainability.py`
- [x] `tests/unit/test_optimization.py`
- [x] `tests/integration/test_plans_api.py`
- [x] `tests/conftest.py`
- [x] `pytest.ini`

## 6) Infrastructure and deployment files

- [x] `docker-compose.yml`
- [x] `docker-compose.prod.yml`
- [x] `deploy/nginx/default.conf`
- [x] `.env.example`
- [x] `docs/deployment.md`

## 7) Missing items from roadmap expectations

- [ ] `.github/workflows/test.yml`
  - Why it matters: roadmap CI section expects automated test workflow on push/PR.
  - Priority: Medium

## 8) Practical conclusion

- Current repository is aligned with roadmap structure for backend, frontend, tests, and deployment.
- Main remaining optional/roadmap gap is CI workflow file creation under `.github/workflows/`.
