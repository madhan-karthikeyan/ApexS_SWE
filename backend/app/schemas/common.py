from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "scrum_master"


class UserLogin(BaseModel):
    email: str
    password: str


class TeamCreate(BaseModel):
    name: str
    team_size: int
    capacity: int
    skills: list[str] = Field(default_factory=list)


class TeamRead(TeamCreate):
    team_id: str
    created_at: Optional[datetime] = None


class SprintCreate(BaseModel):
    team_id: str
    goal: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity: int
    status: str = "planning"


class SprintRead(SprintCreate):
    sprint_id: str


class StoryCreate(BaseModel):
    sprint_id: str
    title: str
    description: Optional[str] = None
    story_points: int
    business_value: float
    risk_score: float = 0.0
    required_skill: Optional[str] = None
    depends_on: list[str] = Field(default_factory=list)
    status: str = "backlog"


class StoryRead(StoryCreate):
    story_id: str


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    story_points: Optional[int] = None
    business_value: Optional[float] = None
    risk_score: Optional[float] = None
    required_skill: Optional[str] = None
    depends_on: Optional[list[str]] = None
    status: Optional[str] = None


class DatasetUploadRead(BaseModel):
    upload_id: str
    team_id: str
    filename: Optional[str] = None
    file_path: Optional[str] = None
    row_count: Optional[int] = None
    is_valid: Optional[bool] = None
    uploaded_at: Optional[datetime] = None


class DatasetPreviewResponse(BaseModel):
    upload_id: str
    rows: int
    preview: list[dict[str, Any]]
    columns: list[str]
    is_valid: bool
    errors: list[str] = Field(default_factory=list)


class ContextExtractRequest(BaseModel):
    team_id: str
    upload_id: Optional[str] = None
    team_capacity: Optional[int] = None


class ContextRead(BaseModel):
    team_id: str
    urgency_weight: float
    value_weight: float
    alignment_weight: float
    computed_at: Optional[datetime] = None


class PlanGenerateRequest(BaseModel):
    sprint_id: str
    capacity: int
    risk_threshold: float
    available_skills: list[str] = Field(default_factory=list)


class PlanStatusResponse(BaseModel):
    status: str
    progress: int = 0
    step: str = "Queued"
    plan_id: Optional[str] = None
    error: Optional[str] = None


class PlanRead(BaseModel):
    plan_id: str
    sprint_id: str
    selected_stories: list[str]
    total_value: float
    total_risk: float
    capacity_used: int
    status: str


class ExplanationRead(BaseModel):
    explanation_id: str
    plan_id: str
    story_id: str
    is_selected: bool
    reason: str
    value_weight: Optional[float] = None
    risk_impact: Optional[float] = None
    alignment_score: Optional[float] = None
    confidence_score: float
    rejection_reason: Optional[str] = None


class MetricsRead(BaseModel):
    team_id: str
    sprint_velocity: list[float]
    business_value: list[float]
    risk_selected: float
    risk_rejected: float
    weight_evolution: list[dict[str, float]]
    learning_sample_count: int = 0
    learning_dataset_sources_count: int = 0
    learning_mae: Optional[float] = None
    learning_r2: Optional[float] = None
    learning_feature_importance: dict[str, float] = Field(default_factory=dict)
    learning_model_type: str = "unknown"
