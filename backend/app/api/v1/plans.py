from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.explanation import Explanation
from app.models.plan import SprintPlan
from app.models.sprint import Sprint
from app.models.story import UserStory
from app.models.dataset_upload import DatasetUpload
from app.schemas.common import PlanGenerateRequest, PlanRead, PlanStatusResponse, ExplanationRead, StoryRead
from app.schemas.planning import PlanModifyRequest
from app.services.explainability_engine import ExplainabilityEngine
from app.services.optimization_engine import OptimizationEngine
from app.services.weight_learning import WeightLearningModel
from app.services.context_extractor import ContextExtractor
from app.workers.planning_task import get_job_state, run_async_job, execute_planning_pipeline

router = APIRouter()


@router.post("/generate")
def generate_plan(payload: PlanGenerateRequest, db: Session = Depends(get_db), _=Depends(require_roles("scrum_master", "product_owner"))):
    sprint = db.query(Sprint).filter(Sprint.sprint_id == payload.sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    dataset = db.query(DatasetUpload).filter(DatasetUpload.team_id == sprint.team_id).order_by(DatasetUpload.uploaded_at.desc()).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="No dataset uploaded for team")
    try:
        job_id = run_async_job(payload.sprint_id, sprint.team_id, dataset.file_path or "", payload.capacity, payload.risk_threshold, payload.available_skills)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"job_id": job_id}


@router.get("/status/{job_id}", response_model=PlanStatusResponse)
def get_plan_status(job_id: str):
    state = get_job_state(job_id)
    return PlanStatusResponse(**state)


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(SprintPlan).filter(SprintPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanRead(plan_id=plan.plan_id, sprint_id=plan.sprint_id, selected_stories=plan.selected_stories or [], total_value=plan.total_value or 0.0, total_risk=plan.total_risk or 0.0, capacity_used=plan.capacity_used or 0, status=plan.status)


@router.put("/{plan_id}/approve")
def approve_plan(plan_id: str, db: Session = Depends(get_db), _=Depends(require_roles("scrum_master", "product_owner"))):
    plan = db.query(SprintPlan).filter(SprintPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "approved"
    db.commit()
    return {"message": "Plan approved"}


@router.post("/{plan_id}/export")
def export_plan(plan_id: str, format: str = "csv", db: Session = Depends(get_db), _=Depends(require_roles("scrum_master", "product_owner"))):
    plan = db.query(SprintPlan).filter(SprintPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    stories = db.query(UserStory).filter(UserStory.story_id.in_(plan.selected_stories or [])).all()
    export_format = format.lower()
    if export_format == "json":
        return {"plan_id": plan.plan_id, "stories": [StoryRead(story_id=s.story_id, sprint_id=s.sprint_id, title=s.title, description=s.description, story_points=s.story_points, business_value=s.business_value, risk_score=s.risk_score, required_skill=s.required_skill, depends_on=s.depends_on or [], status=s.status).model_dump() for s in stories]}
    df = pd.DataFrame([
        {
            "Summary": s.title,
            "Story Points": s.story_points,
            "Priority": "High" if s.business_value >= 7 else "Medium",
            "Labels": s.required_skill,
            "Description": f"Risk: {s.risk_score} | Value: {s.business_value}",
        }
        for s in stories
    ])
    csv_data = df.to_csv(index=False).encode()
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=sprint_plan_{plan_id}.csv"})


@router.put("/{plan_id}/modify")
def modify_plan(plan_id: str, payload: PlanModifyRequest, db: Session = Depends(get_db), _=Depends(require_roles("scrum_master", "product_owner"))):
    plan = db.query(SprintPlan).filter(SprintPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    sprint = db.query(Sprint).filter(Sprint.sprint_id == plan.sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    dataset = db.query(DatasetUpload).filter(DatasetUpload.team_id == sprint.team_id).order_by(DatasetUpload.uploaded_at.desc()).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    capacity = payload.capacity if payload.capacity is not None else sprint.capacity
    risk_threshold = payload.risk_threshold if payload.risk_threshold is not None else 0.7
    available_skills = payload.available_skills or []
    try:
        job_id = run_async_job(sprint.sprint_id, sprint.team_id, dataset.file_path or "", capacity, risk_threshold, available_skills)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"job_id": job_id}


@router.get("/{plan_id}/explain", response_model=list[ExplanationRead])
def get_all_explanations(
    plan_id: str,
    selected: bool | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Explanation).filter(Explanation.plan_id == plan_id)
    if selected is not None:
        query = query.filter(Explanation.is_selected == selected)
    exps = query.offset(offset).limit(limit).all()
    return [ExplanationRead(explanation_id=e.explanation_id, plan_id=e.plan_id, story_id=e.story_id, is_selected=e.is_selected, reason=e.reason, value_weight=e.value_weight, risk_impact=e.risk_impact, alignment_score=e.alignment_score, confidence_score=e.confidence_score, rejection_reason=e.rejection_reason) for e in exps]


@router.get("/{plan_id}/explain/{story_id}", response_model=ExplanationRead)
def get_story_explanation(plan_id: str, story_id: str, db: Session = Depends(get_db)):
    exp = db.query(Explanation).filter(Explanation.plan_id == plan_id, Explanation.story_id == story_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return ExplanationRead(explanation_id=exp.explanation_id, plan_id=exp.plan_id, story_id=exp.story_id, is_selected=exp.is_selected, reason=exp.reason, value_weight=exp.value_weight, risk_impact=exp.risk_impact, alignment_score=exp.alignment_score, confidence_score=exp.confidence_score, rejection_reason=exp.rejection_reason)


@router.get("/{plan_id}/stories", response_model=list[StoryRead])
def get_plan_stories(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(SprintPlan).filter(SprintPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    stories = db.query(UserStory).filter(UserStory.story_id.in_(plan.selected_stories or [])).all()
    return [StoryRead(story_id=s.story_id, sprint_id=s.sprint_id, title=s.title, description=s.description, story_points=s.story_points, business_value=s.business_value, risk_score=s.risk_score, required_skill=s.required_skill, depends_on=s.depends_on or [], status=s.status) for s in stories]
