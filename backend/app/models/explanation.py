from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Explanation(Base):
    __tablename__ = "explanations"

    explanation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("sprint_plans.plan_id"), nullable=False)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_stories.story_id"), nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    value_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    alignment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan = relationship("SprintPlan", back_populates="explanations")
    story = relationship("UserStory", back_populates="explanations")
