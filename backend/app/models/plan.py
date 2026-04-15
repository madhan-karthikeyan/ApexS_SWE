from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class SprintPlan(Base):
    __tablename__ = "sprint_plans"

    plan_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sprint_id: Mapped[str] = mapped_column(String(36), ForeignKey("sprints.sprint_id"), nullable=False)
    selected_stories: Mapped[list] = mapped_column(JSON, default=list)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    total_risk: Mapped[float] = mapped_column(Float, default=0.0)
    capacity_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sprint = relationship("Sprint", back_populates="plans")
    explanations = relationship("Explanation", back_populates="plan", cascade="all, delete-orphan")
