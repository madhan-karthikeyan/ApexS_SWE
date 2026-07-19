# ApexS — Explainable Sprint Planning Platform: Q&A

## Project Context

ApexS is an **Explainable Sprint Planning** platform that uses **Integer Linear Programming (ILP)** via PuLP to optimally select user stories for a sprint under capacity, risk, skill, and dependency constraints. It adds a **machine learning layer** (scikit-learn LogisticRegression) that learns prioritization weights from historical sprint data, a **context extraction** layer that derives team velocity/completion patterns, and an **explainability engine** that generates per-story natural-language reasons for selection or rejection. The backend is **FastAPI** (async SQLAlchemy 2.0 with `AsyncSession`) with **Celery + Redis** for async job execution (including retry logic with exponential backoff), **MinIO** (S3-compatible) for dataset storage, and **PostgreSQL** for relational data. The frontend is **React + TypeScript** with 9 pages covering the full workflow, including a **drag-and-drop kanban board** for sprint plan approval. Everything is **Docker Compose**-ized (6 services) with **GitHub Actions** CI.

---

## Claim vs Reality Table

| Claim in Resume | Implemented? | Reality |
|---|---|---|
| Retryable Celery + Redis pipeline | ✅ Yes | Celery + Redis with `autoretry_for=(Exception,)`, `max_retries=3`, exponential backoff (5s → 10s → 20s → max 300s), jitter, `task_reject_on_worker_lost=True`, `task_acks_late=True`. Also has thread fallback for dev. |
| Async SQLAlchemy | ✅ Yes | Async SQLAlchemy 2.0: `create_async_engine`, `AsyncSession`, `async_sessionmaker`. All route handlers use `async def` with `await db.execute(select(...))`. Supports both `aiosqlite` (dev) and `asyncpg` (prod). |
| 6 Docker Compose services | ✅ Yes | `db`, `redis`, `minio`, `backend`, `celery_worker`, `frontend` |
| Automated CI | ✅ Yes | `.github/workflows/test.yml` — pytest on push/PR with PG + Redis service containers |
| ILP optimization | ✅ Yes | PuLP MILP with CBC solver; greedy fallback when unavailable |
| Weight learning | ✅ Yes | scikit-learn LogisticRegression with train/test split; context fallback for small datasets |
| Context extraction | ✅ Yes | Derives urgency/value/alignment weights from historical velocity, completion rate, risk tolerance |
| Explainability engine | ✅ Yes | Per-story score breakdown with natural-language reasons |
| Kanban approval | ✅ Yes | Drag-and-drop kanban board with `@dnd-kit/core` and `@dnd-kit/sortable`. 5 columns: Backlog → Selected → In Progress → Review → Approved. Syncs story status on approve. |
| MinIO object storage | ✅ Yes | boto3 S3 client with local-filesystem fallback |
| Alembic migrations | ✅ Yes | Single initial migration with 7 tables |
| Polling-based status API | ✅ Yes | `GET /plans/status/{job_id}` polls Celery AsyncResult or in-memory store |

---

## Keywords to Emphasize

- **ILP / MILP / PuLP** — Mixed-integer linear programming for constrained optimization
- **Celery + Redis** — Async task queue with broker/result backend
- **ML-assisted weight learning** — Logistic regression on historical sprint data
- **Context extraction** — Team velocity, completion rate, skill distribution, risk tolerance
- **Explainability / SHAP-style reasoning** — Per-story objective score breakdown (rule-based, not SHAP)
- **Polling-based status API** — Async job tracking with progress
- **FastAPI + SQLAlchemy** — REST API with PostgreSQL
- **React + TypeScript + TanStack Query** — Frontend with state management
- **Docker Compose** — 6-service microservice architecture
- **MinIO (S3-compatible)** — Dataset storage with local fallback
- **GitHub Actions CI** — Automated testing

---

## Potential Interview Questions

### Architecture & Design

**Q: Why did you choose PuLP over Google OR-Tools or a custom greedy algorithm?**
PuLP provides a declarative MILP formulation with the CBC solver. The code also has a greedy fallback and an OR-Tools import attempt (in `reports.py`). The MILP guarantees optimality for small-to-medium backlogs (<2000 stories), while the greedy fallback ensures the system doesn't break when PuLP is unavailable.

**Q: Why sync SQLAlchemy instead of async?**
The claim in the resume says "async SQLAlchemy" but it's actually sync. Real answer: sync SQLAlchemy is simpler and FastAPI handles sync DB calls in threadpool without blocking the event loop. If asked in an interview, acknowledge this discrepancy — it was a resume embellishment.

**Q: How does the Celery fallback work?**
In `planning_task.py:359-387`, if Celery is unavailable or `use_celery=False`, the code spawns a `threading.Thread` to run the pipeline synchronously, storing state in an in-memory `_JOB_STORE` dict with a `Lock`. The polling API reads from both Celery's `AsyncResult` and this in-memory store.

**Q: How does the 6-stage pipeline work?**
The `execute_planning_pipeline` function progresses through: loading dataset (10%) → syncing stories to DB (20%) → loading historical data (35%) → context extraction (50%) → weight learning (65%) → optimization (80%) → explainability (90%) → save plan (100%). Each stage reports progress via a callback that updates both Celery task state and the in-memory store.

### Optimization

**Q: What constraints does the optimization model enforce?**
1. **Capacity** — Sum of selected story points ≤ sprint capacity
2. **Risk** — Stories with risk_score > threshold are excluded
3. **Skills** — Stories requiring skills the team doesn't have are excluded
4. **Dependencies** — If story B depends on story A, A must be selected if B is selected
5. **Status** — Stories with status "done"/"closed"/"resolved"/"completed" are excluded

**Q: What is the objective function?**
Maximizes weighted sum of per-story scores. Each story's score = `urgency_weight * effort_component + value_weight * value_component + alignment_weight * risk_component`, where all components are normalized [0,1].

**Q: How do you handle infeasibility?**
If no feasible stories exist, returns empty result with status `"no-feasible-stories"`. If MILP fails to find optimal solution (timeout, solver error), falls back to greedy heuristic.

### ML & Explainability

**Q: How does weight learning work?**
`WeightLearningModel.train_with_metrics()` trains a LogisticRegression on historical data using `[story_points, business_value, risk_score]` features to predict `sprint_completed`. Coefficients are sign-mapped to [urgency, value, alignment] weights. Falls back to context-derived weights when sample size < 10 or sklearn unavailable.

**Q: What metrics do you track for learning quality?**
MAE, R², accuracy, F1, ROC-AUC on a 80/20 test split. Feature importance (coefficient-based).

**Q: How is explainability different from SHAP?**
It's **rule-based**, not SHAP. Each selected story gets a score breakdown (value contribution, effort contribution, risk contribution) plus rules like "high business value" or "low risk". Rejected stories get a specific rejection reason (risk threshold, skill mismatch, dependency, capacity). The code explicitly says `"shap_enabled": False`.

### Frontend

**Q: What frontend pages exist?**
9 pages: Dashboard → DatasetUpload → SprintConfiguration → OptimizationProcessing → GeneratedSprintPlan → ExplainabilityPanel → SprintPlanApproval → Reports → NotUsed. Full routing in `App.tsx`.

**Q: How does the frontend track async progress?**
`usePlanStatus` hook polls `GET /plans/status/{job_id}` every 2 seconds using TanStack Query's `refetchInterval`, stopping when status is "complete" or "failed". On completion, redirects to the generated plan page.

### DevOps

**Q: What services are in Docker Compose?**
PostgreSQL 15, Redis 7, MinIO (S3-compatible), FastAPI backend, Celery worker, React/Vite frontend. 6 services total.

**Q: What does CI do?**
GitHub Actions runs pytest with PostgreSQL and Redis service containers on push/PR.

---

## What You MUST Know Cold

1. **The PuLP MILP formulation** — be ready to write it on a whiteboard
2. **The pipeline stages** — all 6+ with progress percentages
3. **The weight learning fallback chain** — sklearn available? samples ≥ 10? binary classes?
4. **The explainability algorithm** — score components, rejection reasons
5. **The tech stack** — FastAPI, async SQLAlchemy 2.0, Celery + Redis (with retry), PuLP, scikit-learn, React + TypeScript, Docker Compose, MinIO, GitHub Actions
6. **The DB schema** — 8 tables: scrum_teams, users, contexts, dataset_uploads, sprints, user_stories, sprint_plans, explanations
7. **The frontend architecture** — Zustand store with persist, TanStack Query, 9 pages, Vite build, dnd-kit kanban
8. **The async SQLAlchemy migration** — know `create_async_engine`, `AsyncSession`, `select()`, `scalars()`, async context managers
9. **The Celery retry configuration** — `autoretry_for`, `retry_backoff`, `max_retries=3`, `retry_jitter`, `task_acks_late`, `task_reject_on_worker_lost`
10. **The kanban board** — `@dnd-kit/core` sensors, `SortableContext`, `DragOverlay`, column state management

---

## Red Flags You Should Address Proactively

- **"Async SQLAlchemy is actually sync"** — If asked, say: "The resume says async but it's sync SQLAlchemy. FastAPI runs sync DB calls in a threadpool so there's no performance issue. I should correct that on my resume."
- **"Retryable pipeline"** — "There's no retry mechanism yet. The Celery task fails permanently on error. That's a known improvement area."
- **"Kanban approval"** — "It's a simple approve/export page, not a kanban board. I used 'kanban' loosely in the resume."
