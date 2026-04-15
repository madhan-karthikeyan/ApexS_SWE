# Novelty Implementation Audit Report

Date: 2026-04-10
Scope: Verification of four novelty claims against the current repository implementation.

## Executive Verdict

- Novelty 1 (Explainability on ILP output): Implemented (with one enhancement opportunity)
- Novelty 2 (Team-specific learned weights from history): Implemented
- Novelty 3 (Four-constraint multi-objective ILP): Implemented
- Novelty 4 (Full decision-support loop): Implemented end-to-end

Overall verdict: novelty claims are now implementation-backed for project demonstration and report defense.

## 1) Explainability Layer on ILP Output

### Implemented Evidence

- Explanation generation service: `backend/app/services/explainability_engine.py`
- Explanation persistence model: `backend/app/models/explanation.py`
- API retrieval:
  - `GET /api/v1/plans/{plan_id}/explain`
  - `GET /api/v1/plans/{plan_id}/explain/{story_id}`
- Pipeline integration after optimization:
  - `backend/app/workers/planning_task.py`

### Current Strength

- Both selected and rejected stories get human-readable reasons.
- Contribution and confidence fields are populated for selected stories.
- Rejection causes include risk, skills, dependencies, and capacity/priority logic.

### Enhancement Opportunity

- Rejected stories still use conservative confidence semantics (currently minimal).
- For publication-grade novelty framing, add objective-delta based confidence for rejected candidates.

## 2) Team-Specific Weight Learning from Historical Data

### Implemented Evidence

- Learning module with Ridge regression and normalization:
  - `backend/app/services/weight_learning.py`
- Team-scoped dataset selection in plan generation:
  - `backend/app/api/v1/plans.py`
- Learned weights fed directly into optimizer in pipeline:
  - `backend/app/workers/planning_task.py`

### Verdict

- Implemented and functioning as intended.

## 3) Four-Constraint Multi-Objective Selection

### Implemented Evidence

- Weighted objective function (value + urgency proxy + alignment/risk proxy)
- Capacity constraint
- Risk threshold constraint
- Skill compatibility constraint
- Dependency constraint

Primary implementation: `backend/app/services/optimization_engine.py`

### Verdict

- Implemented with practical constraint enforcement in active runs.

## 4) Full Decision-Support Loop

### Implemented Evidence

- Dataset upload and preview workflow:
  - backend: `backend/app/api/v1/datasets.py`
  - frontend: `frontend/src/pages/DatasetUpload.tsx`
- Sprint configuration and generation:
  - backend: `backend/app/api/v1/sprints.py`, `backend/app/api/v1/plans.py`
  - frontend: `frontend/src/pages/SprintConfiguration.tsx`
- Async processing + status polling:
  - backend: `backend/app/workers/planning_task.py`
  - frontend: `frontend/src/pages/OptimizationProcessing.tsx`
- Plan, explainability, approval, export:
  - frontend pages wired in `frontend/src/App.tsx`
  - backend endpoints in `backend/app/api/v1/plans.py`

### Verification

- Stage-based end-to-end flow is validated in active integration tests and practical run checks.

## Final Assessment Matrix

| Novelty | Implementation Status | Confidence |
|---|---|---|
| Explainability on ILP output | Implemented (enhancement possible) | High |
| Team-specific learned weights | Implemented | High |
| Four-constraint ILP selection | Implemented | High |
| Full decision-support loop | Implemented end-to-end | High |

## Recommendation for Final Report Wording

Use this positioning:

- "All four novelty pillars are implemented in the current system and validated in end-to-end runs."
- "One enhancement area remains for stronger research-grade explainability depth: richer confidence semantics for rejected stories."
