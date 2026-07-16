from __future__ import annotations

from pydantic import BaseModel, Field


class PlanModifyRequest(BaseModel):
    capacity: int | None = None
    risk_threshold: float | None = None
    available_skills: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    format: str = "csv"
