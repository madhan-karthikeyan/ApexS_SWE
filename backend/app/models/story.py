from __future__ import annotations

import uuid
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class UserStory(Base):
    __tablename__ = "user_stories"

    story_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sprint_id: Mapped[str] = mapped_column(String(36), ForeignKey("sprints.sprint_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    business_value: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    required_skill: Mapped[str | None] = mapped_column(String(50), nullable=True)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="backlog")

    sprint = relationship("Sprint", back_populates="stories")
    explanations = relationship("Explanation", back_populates="story")
