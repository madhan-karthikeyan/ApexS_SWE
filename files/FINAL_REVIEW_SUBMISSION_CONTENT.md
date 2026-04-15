# FINAL REVIEW SUBMISSION CONTENT (30.03.2026 to 15.04.2026)

Project: Explainable Context-Aware Sprint Planning System  
Team: ApexS

Use this document directly for your final review file. Replace placeholders in Section 0 with your exact details.

---

## 0. Title and Team Details

### Title of the Project
Explainable Context-Aware Sprint Planning System

### Team Members (Reg. No. and Name)
- Team Leader: `<REG_NO_1> - <NAME_1>`
- Member 2: `<REG_NO_2> - <NAME_2>`
- Member 3: `<REG_NO_3> - <NAME_3>`
- Member 4: `<REG_NO_4> - <NAME_4>`

---

## 1. Software Requirement Specification (SRS – IEEE Format)

SRS document is attached in repository under:
- `files/Software Engineering Lab Submission 2 (3).doc`

How to present in review:
- Mention that functional requirements F1–F8 are mapped to implemented APIs and tested through integration tests.
- Mention non-functional constraints: async processing, service health, and export correctness.

Evidence mapping (implementation):
- Dataset ingestion and validation: `backend/app/api/v1/datasets.py`
- Planning pipeline trigger: `backend/app/api/v1/plans.py`
- Status tracking: `backend/app/api/v1/plans.py` (`/status/{job_id}`)
- Explainability: `backend/app/services/explainability_engine.py`
- Export: `backend/app/api/v1/plans.py` (`/{plan_id}/export`)

---

## 2. Software Design Specification (SDS)

SDS document is attached in repository under:
- `files/Software Engineering Lab Submission 3 (2).pdf`

Design implementation references:
- API entry and router composition: `backend/app/main.py`
- Layered services:
  - Context extraction: `backend/app/services/context_extractor.py`
  - Weight learning: `backend/app/services/weight_learning.py`
  - Optimization: `backend/app/services/optimization_engine.py`
  - Explainability: `backend/app/services/explainability_engine.py`
- Worker orchestration: `backend/app/workers/planning_task.py`
- UI workflow routing: `frontend/src/App.tsx`

---

## 3. Implementation

### 3.1 100% Completion of Project (Scope-complete)

Implemented end-to-end flow:
1. Upload dataset (`/api/v1/datasets/upload`)
2. Configure sprint (`/api/v1/sprints/`)
3. Generate plan (`/api/v1/plans/generate`)
4. Poll progress (`/api/v1/plans/status/{job_id}`)
5. View plan (`/api/v1/plans/{plan_id}` and `/stories`)
6. View explainability (`/api/v1/plans/{plan_id}/explain`)
7. Approve (`/api/v1/plans/{plan_id}/approve`)
8. Modify and re-run (`/api/v1/plans/{plan_id}/modify`)
9. Export CSV/JSON (`/api/v1/plans/{plan_id}/export`)

### 3.2 Demonstration of Working System

Run commands:
```bash
docker compose up --build
```

Access:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

Demo script (presenter sequence):
1. Open Dashboard.
2. Upload `tmp/converted_sprint_history_dataset_1.csv`.
3. Configure sprint and generate plan.
4. Show live optimization step transitions.
5. Open generated plan and quality checks.
6. Open explainability panel and inspect selected/rejected story reasons.
7. Modify constraints and re-run from plan screen.
8. Approve final plan and export CSV.

---

## 4. Results and Analysis

### 4.1 Results with Graphs

Use these in-built graphs/screenshots:
- Value vs Risk Distribution (Explainability panel)
  - File: `frontend/src/components/ValueRiskChart.tsx`
- Velocity and Value trend charts (Reports page)
  - File: `frontend/src/components/LineBarCharts.tsx`
- Learning Evaluation table (sample count, MAE, R2, feature importance, dataset sources)
  - File: `frontend/src/pages/Reports.tsx`

### 4.2 Proper Interpretation of Outputs

Include this interpretation text:
- Lower risk threshold reduces high-risk story selection.
- Lower capacity reduces selected story count.
- Dependency constraint prevents selection of child stories without parent stories.
- Skill constraints remove stories requiring unavailable skills.
- Explainability reasons are generated per selected and rejected story, with confidence and contribution details.

### 4.3 Outcome – Paper / Patent

Suggested final statement:
- Paper-ready outcome: system demonstrates explainable, constraint-aware sprint planning with reproducible workflow and measurable outputs.
- Patent potential: workflow-level innovation in combining team-historical weight learning, constrained optimization, and human-readable explainability in one planning loop.

---

## 5. Testing

### 5.1 Open Source Testing Tool usage

Primary tool used: `pytest` (open source)

Where tests are located:
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/test_plans_api.py`

Execution:
```bash
pytest -q
```

Current observed result (latest run):
- `20 passed`

### 5.2 Tool details and usage

- `pytest` validates backend and pipeline logic.
- `fastapi.testclient` is used for API integration verification.
- Additional frontend validation via build/type checks:
  - `npm exec tsc --noEmit`
  - `npm run build`

### 5.3 Test Case Report with Graphs

Recommended content block for report:
- Test matrix screenshot: include table from your final report document.
- Pass summary graph: bar chart (Passed vs Failed).
- Stage coverage graph: Stage 0–9 all pass.

Use evidence from:
- `tests/integration/test_plans_api.py` (contains stage flow assertions)
- `tests/unit/test_optimization.py`
- `tests/unit/test_explainability.py`
- `tests/unit/test_context_extractor.py`

---

## 6. References

Technical references (put in submission):
1. FastAPI Documentation – https://fastapi.tiangolo.com/
2. React Documentation – https://react.dev/
3. SQLAlchemy Documentation – https://docs.sqlalchemy.org/
4. PuLP Documentation – https://coin-or.github.io/pulp/
5. OR-Tools Documentation – https://developers.google.com/optimization
6. SHAP Documentation – https://shap.readthedocs.io/
7. FastAPI-Users Documentation – https://fastapi-users.github.io/fastapi-users/
8. Celery Documentation – https://docs.celeryq.dev/
9. Redis Documentation – https://redis.io/docs/
10. MinIO Documentation – https://min.io/docs/

---

## Screenshot Checklist (Mandatory Demo Evidence)

Capture and include these screenshots in final report:
1. Docker services up (`docker compose ps`)
2. Frontend dashboard loaded
3. Dataset upload with preview and valid status
4. Sprint configuration values before generate
5. Optimization processing screen with progress/step
6. Generated sprint plan with quality checks table
7. Explainability panel graph + story reason panel
8. Modify and re-run controls used on plan page
9. Approval page showing approved status
10. Exported CSV opened in spreadsheet editor
11. Reports page graphs + learning evaluation table
12. Test command output (`pytest -q`) showing pass count

---

## Final one-line conclusion for viva

"The system is fully implemented and demonstrated end-to-end with constraint-aware planning, explainability, modify/re-run support, export, and automated test validation."
