from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Context(Base):
    __tablename__ = "contexts"

    context_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("scrum_teams.team_id"), nullable=False)
    urgency_weight: Mapped[float] = mapped_column(Float, nullable=False)
    value_weight: Mapped[float] = mapped_column(Float, nullable=False)
    alignment_weight: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team = relationship("ScrumTeam", back_populates="contexts")
